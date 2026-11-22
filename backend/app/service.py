from contextlib import contextmanager
from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

try:
    from langfuse import get_client, observe
except ImportError:
    def observe(*args, **kwargs):
        def decorator(f):
            return f
        return decorator

    def get_client():
        return None

from .config import Settings
from .database import Database
from .ddi.checker import get_ddi_checker
import re
from .decomposition import QueryDecomposer, retrieve_with_decomposition
from .llm import DemoGenerator, Generator, OllamaAdapter, create_llm_adapter
from .live_pubmed import LivePubMedRetriever
from .models import ChatRequest, ChatResponse, Intent
from .retrieval import ChromaRetriever, DemoRetriever, TransformerDenseEmbedder
from .safety import classify_query
from .verification import CitationVerifier, make_nli, verify_answer


def contextualize_query_for_retrieval(
    question: str, history: list[dict[str, str]] | None, topic: str | None
) -> str:
    if not history:
        return question

    lower_q = question.lower()
    anaphoric_markers = (
        "that", "this", "these", "those", "it", "they", "them", "which", "their", "its", "same", "such",
        "comparison", "compare", "difference", "differences", "guideline", "guidelines", "trial", "trials",
        "evidence", "support", "supports", "why", "how so", "elaborate", "further", "again", "whose"
    )
    has_anaphora = any(re.search(rf"\b{m}\b", lower_q) for m in anaphoric_markers)
    has_explicit_condition = any(
        term in lower_q for term in ("parkinson", "epilep", "seizure", "seizures", "levodopa", "tremor")
    )

    if not has_anaphora and has_explicit_condition:
        return question

    prev_user_queries = [
        msg.get("content", "").strip()
        for msg in history
        if msg.get("role") == "user" and msg.get("content", "").strip()
    ]
    if not prev_user_queries:
        return question

    last_user_query = prev_user_queries[-1]
    if last_user_query.lower() == question.lower():
        if len(prev_user_queries) > 1:
            last_user_query = prev_user_queries[-2]
        else:
            return question

    context_prefix = " ".join(prev_user_queries[-2:])
    return f"{question} Context: {context_prefix}"


@contextmanager
def null_span():
    yield None


def start_span(client, name: str, as_type: str = "span"):
    if client:
        try:
            return client.start_as_current_observation(name=name, as_type=as_type)
        except Exception:
            pass
    return null_span()


class ChatService:
    def __init__(self, settings: Settings, database: Database):
        self.settings = settings
        self.database = database
        self.ddi_checker = get_ddi_checker()
        if not settings.demo_mode:
            if settings.llm_provider.lower() == "gemini" and not settings.gemini_api_key:
                raise RuntimeError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini and DEMO_MODE=false")
            if settings.llm_provider.lower() == "openai" and not settings.openai_api_key:
                raise RuntimeError("OPENAI_API_KEY is required when LLM_PROVIDER=openai and DEMO_MODE=false")

        def _get_embedder(adapter):
            if settings.embedding_provider.lower() == "local":
                return TransformerDenseEmbedder(settings.dense_model)
            return adapter

        if settings.active_llm_enabled:
            # Full production: ChromaDB retrieval + real LLM generation
            adapter = create_llm_adapter(settings)
            self.generator: Generator = adapter
            self.retriever = ChromaRetriever(settings, _get_embedder(adapter))
        elif settings.smart_demo_enabled:
            # Smart demo: real LLM generation
            # If ChromaDB collection has chunks, utilize ChromaRetriever; otherwise in-memory DemoRetriever
            adapter = create_llm_adapter(settings)
            self.generator: Generator = adapter
            chroma = ChromaRetriever(settings, _get_embedder(adapter))
            self.retriever = chroma if chroma.collection.count() > 0 else DemoRetriever(settings)
        else:
            # Pure demo: no API key — template DemoGenerator + in-memory DemoRetriever
            self.generator = DemoGenerator()
            self.retriever = DemoRetriever(settings)
        self.citation_verifier = CitationVerifier(settings)
        self.nli = make_nli(settings)
        self.decomposer = QueryDecomposer(settings, self.generator)
        self.live_pubmed = LivePubMedRetriever(settings, self.generator)
        self.ollama_adapter = OllamaAdapter(settings)

    @observe(name="chat_pipeline")
    async def chat(self, request: ChatRequest) -> ChatResponse:
        started = perf_counter()
        lf_client = get_client() if getattr(self.settings, "langfuse_enabled", False) else None
        trace_id = (lf_client.get_current_trace_id() if lf_client else None) or str(uuid4())
        if lf_client:
            try:
                lf_client.update_current_span(
                    metadata={
                        "session_id": request.session_id,
                        "question_id": request.question_id,
                        "pipeline_version": getattr(self.settings, "pipeline_version", "triad-rag-v2.1"),
                        "mode": request.mode.value,
                        "demo_mode": self.settings.demo_mode,
                        "llm_provider": self.settings.llm_provider,
                    }
                )
            except Exception:
                pass
        history = request.history or self.database.get_session_history(request.session_id, limit=6)
        decision = classify_query(request.question, history=history)

        if decision.intent != Intent.educational_in_scope:
            if lf_client:
                try:
                    lf_client.update_current_span(
                        metadata={
                            "question_id": request.question_id,
                            "pipeline_version": getattr(self.settings, "pipeline_version", "triad-rag-v2.1"),
                            "model": "safety-rules-v1",
                            "decision": "abstained",
                            "nli_action": "safety_abstention",
                            "retrieved_source_ids": [],
                        }
                    )
                except Exception:
                    pass
            result = ChatResponse(
                trace_id=trace_id,
                intent=decision.intent,
                mode=request.mode,
                answer=decision.response or "This question cannot be answered by the current system.",
                warnings=["Safety or scope guardrail applied."],
                latency_ms=_elapsed_ms(started),
                model="safety-rules-v1",
                demo_mode=self.settings.demo_mode,
                created_at=datetime.now(UTC),
            )
            self.database.save_trace(request.session_id, request.question, result, user_id=request.user_id)
            return result

        if request.mode.value == "baseline":
            generation = self.generator.generate_baseline(request.question)
            answer = generation.text
            if lf_client:
                try:
                    lf_client.update_current_span(
                        metadata={
                            "question_id": request.question_id,
                            "pipeline_version": getattr(self.settings, "pipeline_version", "triad-rag-v2.1"),
                            "model": self.generator.model_name,
                            "decision": "answered",
                            "nli_action": "baseline_unverified",
                            "retrieved_source_ids": [],
                        }
                    )
                except Exception:
                    pass
            result = ChatResponse(
                trace_id=trace_id,
                intent=decision.intent,
                mode=request.mode,
                answer=answer,
                warnings=["Baseline mode does not retrieve or verify evidence."],
                latency_ms=_elapsed_ms(started),
                model=self.generator.model_name,
                input_tokens=generation.input_tokens,
                output_tokens=generation.output_tokens,
                estimated_cost_usd=self._cost(generation.input_tokens, generation.output_tokens),
                demo_mode=self.settings.demo_mode,
                created_at=datetime.now(UTC),
            )
            self.database.save_trace(request.session_id, request.question, result, user_id=request.user_id)
            return result

        if request.mode.value == "ollama_baseline":
            generation = self.ollama_adapter.generate_baseline(request.question)
            answer = generation.text
            if lf_client:
                try:
                    lf_client.update_current_span(
                        metadata={
                            "question_id": request.question_id,
                            "pipeline_version": getattr(self.settings, "pipeline_version", "triad-rag-v2.1"),
                            "model": self.ollama_adapter.model_name,
                            "decision": "answered",
                            "nli_action": "ollama_baseline_unverified",
                            "retrieved_source_ids": [],
                        }
                    )
                except Exception:
                    pass
            result = ChatResponse(
                trace_id=trace_id,
                intent=decision.intent,
                mode=request.mode,
                answer=answer,
                warnings=["Local Ollama baseline operates on-device without retrieval verification."],
                latency_ms=_elapsed_ms(started),
                model=self.ollama_adapter.model_name,
                input_tokens=generation.input_tokens,
                output_tokens=generation.output_tokens,
                estimated_cost_usd=0.0,
                demo_mode=self.settings.demo_mode,
                created_at=datetime.now(UTC),
            )
            self.database.save_trace(request.session_id, request.question, result, user_id=request.user_id)
            return result

        # Scan query for drug interactions (combining local rules & live openFDA API)
        with start_span(lf_client, "ddi_analysis", as_type="span") as ddi_span:
            ddi_report = await self.ddi_checker.analyze_query(request.question)
            if ddi_span:
                try:
                    ddi_span.update(
                        output={
                            "has_interaction": getattr(ddi_report, "has_interaction", False),
                            "drugs_detected": getattr(ddi_report, "drugs_detected", []),
                        }
                    )
                except Exception:
                    pass

        # Step 1: Selective Query Decomposition & Triad Retrieval
        effective_query = (
            decision.cleaned_educational_query
            if (decision.has_adversarial_fabrication and decision.cleaned_educational_query)
            else request.question
        )
        retrieval_query = contextualize_query_for_retrieval(effective_query, history, decision.topic)
        with start_span(lf_client, "triad_retrieval", as_type="retriever") as retrieval_span:
            decomp_plan = self.decomposer.decompose(retrieval_query, topic=decision.topic)
            chunks, subquery_results = retrieve_with_decomposition(
                self.retriever, decomp_plan, decision.topic, self.settings
            )
            if retrieval_span:
                try:
                    retrieval_span.update(
                        metadata={
                            "topic": decision.topic,
                            "chunks_found": len(chunks),
                            "layer_counts": {
                                f"Layer {lvl}": sum(1 for c in chunks if c.layer == lvl) for lvl in (1, 2, 3)
                            },
                        }
                    )
                except Exception:
                    pass

        unanswered_parts = [
            sq.missing_evidence_statement
            for sq in subquery_results
            if not sq.has_evidence and sq.missing_evidence_statement
        ]

        # Agentic Fallback Bridge: Check if Live PubMed search is requested or needed
        live_pubmed_triggered = False
        live_pubmed_query = None
        is_live_allowed = getattr(self.settings, "enable_live_pubmed_fallback", True) and (request.enable_live_pubmed is not False)
        layer_3_chunks = [c for c in chunks if c.layer == 3]

        # Check target drug entity coverage in local Layer 3 evidence
        from .live_pubmed import extract_clinical_entities
        import re
        _, interventions, _ = extract_clinical_entities(request.question, decision.topic)
        primary_drugs = [
            d for d in interventions
            if not re.search(rf"\b{re.escape(d)}-induced\b", request.question.lower())
        ]

        target_entity_missing = False
        if primary_drugs and layer_3_chunks:
            # Check if any Layer 3 chunk mentions any of the primary queried drugs
            has_matching_drug = any(
                any(re.search(rf"\b{re.escape(d)}\b", f"{c.title} {c.excerpt}".lower()) for d in primary_drugs)
                for c in layer_3_chunks
            )
            if not has_matching_drug:
                target_entity_missing = True

        needs_fallback = (
            not chunks
            or not layer_3_chunks
            or target_entity_missing
            or any(sq.target_layer == 3 and not sq.has_evidence for sq in subquery_results)
            or max(c.relevance for c in layer_3_chunks) < getattr(self.settings, "live_pubmed_threshold", 0.45)
        )
        should_trigger_live_pubmed = (
            bool(getattr(request, "force_live_pubmed", False))
            or (is_live_allowed and needs_fallback)
        )

        if should_trigger_live_pubmed:
            with start_span(lf_client, "live_pubmed_search", as_type="tool") as live_span:
                try:
                    live_chunks, live_query = await self.live_pubmed.search_and_rerank(
                        effective_query,
                        topic=decision.topic,
                        top_k=getattr(self.settings, "live_pubmed_top_k", 3),
                    )
                    if live_span:
                        try:
                            live_span.update(
                                metadata={
                                    "query": live_query,
                                    "results_count": len(live_chunks) if live_chunks else 0,
                                }
                            )
                        except Exception:
                            pass
                    if live_chunks:
                        live_pubmed_triggered = True
                        live_pubmed_query = live_query
                        existing_chunk_ids = {c.chunk_id for c in chunks}
                        for lc in live_chunks:
                            if hasattr(self.live_pubmed, "_sources_by_id"):
                                self.live_pubmed._sources_by_id[lc.source_id] = lc
                            if lc.chunk_id not in existing_chunk_ids:
                                chunks.append(lc)
                                existing_chunk_ids.add(lc.chunk_id)

                        # Dynamic Knowledge Base Expansion: auto-save newly fetched live PubMed chunks into ChromaDB
                        if getattr(self.settings, "auto_save_live_pubmed", True):
                            try:
                                if hasattr(self.retriever, "add_chunks"):
                                    saved_count = self.retriever.add_chunks(live_chunks)
                                    if saved_count > 0:
                                        import logging
                                        logging.getLogger(__name__).info(
                                            "Auto-saved %d live PubMed chunks into ChromaDB knowledge base.", saved_count
                                        )
                            except Exception as save_err:
                                import logging
                                logging.getLogger(__name__).warning("Failed to auto-save live PubMed chunks: %s", save_err)

                        for sq in subquery_results:
                            if sq.target_layer == 3 and not sq.has_evidence:
                                sq.has_evidence = True
                                sq.chunks_found = len(live_chunks)
                                sq.missing_evidence_statement = None

                        unanswered_parts = [
                            sq.missing_evidence_statement
                            for sq in subquery_results
                            if not sq.has_evidence and sq.missing_evidence_statement
                        ]
                except Exception as exc:
                    import logging
                    logging.getLogger(__name__).warning("Live PubMed fallback execution error: %s", exc)

        # Check for real-time, zero-day, or specific recent timeframe constraints in query
        temporal_match = re.search(
            r"\b(this\s+morning|today|yesterday|this\s+week|past\s+few\s+hours|breaking\s+news|just\s+published)\b",
            request.question,
            re.IGNORECASE,
        )
        if temporal_match:
            timeframe_phrase = temporal_match.group(1).lower()
            temporal_unanswered = (
                f"Publication timeframe '{timeframe_phrase}': No retrieved source is verified from this real-time timeframe. "
                "Indexed knowledge base and literature retrieval systems operate with an indexing and publication lag."
            )
            if temporal_unanswered not in unanswered_parts:
                unanswered_parts.append(temporal_unanswered)

        active_generator = self.ollama_adapter if request.mode.value == "ollama_rag" else self.generator

        if not chunks:
            if lf_client:
                try:
                    lf_client.update_current_span(
                        metadata={
                            "question_id": request.question_id,
                            "pipeline_version": getattr(self.settings, "pipeline_version", "triad-rag-v2.1"),
                            "model": active_generator.model_name,
                            "decision": "abstained",
                            "nli_action": "abstained_no_evidence",
                            "retrieved_source_ids": [],
                        }
                    )
                except Exception:
                    pass
            answer = (
                "The indexed collection does not contain enough evidence to answer this question. "
                "Try a narrower question within the supported topic."
            )
            result = ChatResponse(
                trace_id=trace_id,
                intent=decision.intent,
                mode=request.mode,
                answer=answer,
                subqueries=subquery_results,
                evidence_score=0.0,
                evidence_threshold=self.settings.evidence_threshold,
                warnings=["Retrieval returned no usable evidence."],
                ddi_report=ddi_report if (ddi_report.has_interaction or len(ddi_report.drugs_detected) >= 2) else None,
                live_pubmed_triggered=live_pubmed_triggered,
                live_pubmed_query=live_pubmed_query,
                latency_ms=_elapsed_ms(started),
                model=active_generator.model_name,
                demo_mode=self.settings.demo_mode,
                created_at=datetime.now(UTC),
            )
            self.database.save_trace(request.session_id, request.question, result, user_id=request.user_id)
            return result

        active_generator = self.ollama_adapter if request.mode.value == "ollama_rag" else self.generator
        generation = active_generator.generate_grounded(
            request.question,
            chunks,
            ddi_report=ddi_report,
            unanswered_parts=unanswered_parts,
            has_adversarial_fabrication=decision.has_adversarial_fabrication,
            history=history,
        )
        original_answer = generation.text
        total_input_tokens = generation.input_tokens
        total_output_tokens = generation.output_tokens

        # Step 2: Primary claim verification + Step 3: Targeted Secondary Retrieval (1 pass)
        with start_span(lf_client, "nli_verification", as_type="evaluator") as nli_span:
            verification = await verify_answer(
                original_answer,
                chunks,
                self.citation_verifier,
                self.nli,
                self.settings.evidence_threshold,
                retriever=self.retriever,
                topic=decision.topic,
                enable_cross_chunk_fallback=self.settings.enable_cross_chunk_fallback,
                enable_corrective_retrieval=self.settings.enable_corrective_retrieval,
                max_corrective_claims=self.settings.corrective_retrieval_max_claims,
            )
            if nli_span:
                try:
                    nli_span.update(
                        metadata={
                            "evidence_score": verification.evidence_score,
                            "claims_count": len(verification.claims),
                            "supported": sum(1 for c in verification.claims if c.label.value == "supported"),
                            "contradicted": sum(1 for c in verification.claims if c.label.value == "contradicted"),
                            "insufficient": sum(1 for c in verification.claims if c.label.value == "insufficient"),
                        }
                    )
                except Exception:
                    pass
        if verification.chunks:
            chunks = verification.chunks
        answer = original_answer

        initial_evidence_score = verification.evidence_score
        initial_claims = list(verification.claims)

        # Determine if Bounded Answer Revision is required:
        has_contradiction = any(item.label.value == "contradicted" for item in verification.claims)
        has_insufficient = any(item.label.value == "insufficient" for item in verification.claims)
        has_citation_updates = any(
            "targeted secondary retrieval" in (item.explanation or "") or "originally cited" in (item.explanation or "")
            for item in verification.claims
        )
        below_threshold = verification.evidence_score < self.settings.evidence_threshold

        needs_revision = (
            getattr(self.settings, "enable_bounded_answer_revision", True)
            and (has_contradiction or has_insufficient or has_citation_updates or below_threshold)
        )

        nli_action = "accepted_unmodified"
        if not getattr(self.settings, "enable_bounded_answer_revision", True) and (has_contradiction or has_insufficient or below_threshold):
            nli_action = "warning_only"

        if needs_revision:
            # Step 4: Revise unsupported claims and inline citations
            revision_generation = active_generator.revise_grounded(
                request.question,
                original_answer,
                verification.claims,
                chunks,
                ddi_report=ddi_report,
                unanswered_parts=unanswered_parts,
                has_adversarial_fabrication=decision.has_adversarial_fabrication,
                history=history,
            )
            revised_draft = revision_generation.text
            total_input_tokens += revision_generation.input_tokens
            total_output_tokens += revision_generation.output_tokens

            # Step 5: Verify again (bounded: corrective retrieval disabled to prevent infinite loops)
            with start_span(lf_client, "revised_nli_verification", as_type="evaluator") as rev_span:
                revised_verification = await verify_answer(
                    revised_draft,
                    chunks,
                    self.citation_verifier,
                    self.nli,
                    self.settings.evidence_threshold,
                    retriever=None,
                    topic=decision.topic,
                    enable_cross_chunk_fallback=self.settings.enable_cross_chunk_fallback,
                    enable_corrective_retrieval=False,
                )
                supp_count = sum(1 for c in revised_verification.claims if c.label.value == "supported")
                contra_count = sum(1 for c in revised_verification.claims if c.label.value == "contradicted")
                insuff_count = sum(1 for c in revised_verification.claims if c.label.value == "insufficient")
                resolved_claims = max(
                    0,
                    sum(1 for c in initial_claims if c.label.value != "supported")
                    - (contra_count + insuff_count),
                )
                if rev_span:
                    try:
                        rev_span.update(
                            metadata={
                                "pre_revision_evidence_score": initial_evidence_score,
                                "post_revision_evidence_score": revised_verification.evidence_score,
                                "claims_count": len(revised_verification.claims),
                                "supported": supp_count,
                                "contradicted": contra_count,
                                "insufficient": insuff_count,
                                "unsupported_claims_resolved": resolved_claims,
                                "claims_checked": [
                                    {
                                        "claim": c.claim[:120],
                                        "label": c.label.value,
                                        "citations": c.citation_markers,
                                    }
                                    for c in revised_verification.claims[:5]
                                ],
                            }
                        )
                    except Exception:
                        pass

            answer = revised_draft
            verification = revised_verification

            # Step 6: Return supported content or explicitly state remaining evidence gap
            if verification.evidence_score < self.settings.evidence_threshold or any(
                item.label.value == "contradicted" for item in verification.claims
            ):
                nli_action = "revised_with_evidence_gap_warning"
                if "evidence gap" not in answer.lower():
                    answer = (
                        "The retrieved clinical material was not strong enough to produce a fully verified answer. "
                        "The revised draft and its verification details are retained below for research inspection.\n\n"
                        + answer
                    )
            else:
                nli_action = "revised_and_verified"

        is_abstention = (
            "cannot be answered" in answer.lower()
            or "not strong enough" in answer.lower()
            or "no indexed evidence" in answer.lower()
            or decision.intent != Intent.educational_in_scope
        )
        decision_label = "abstained" if is_abstention else "answered"

        layer_dist: dict[str, int] = {}
        for citation in verification.citations:
            layer_key = f"Layer {citation.layer}"
            layer_dist[layer_key] = layer_dist.get(layer_key, 0) + 1

        warnings = list(verification.warnings)
        if live_pubmed_triggered:
            warnings.append(
                "Agentic Live PubMed fallback active: retrieved and cross-encoder reranked recent empirical clinical trials."
            )
        for sq in subquery_results:
            if not sq.has_evidence:
                warnings.append(f"Subquery '{sq.intent_description}' lacked direct evidence in indexed corpus.")

        if lf_client:
            try:
                lf_client.update_current_span(
                    metadata={
                        "question_id": request.question_id,
                        "pipeline_version": getattr(self.settings, "pipeline_version", "triad-rag-v2.1"),
                        "model": self.generator.model_name,
                        "retrieved_source_ids": [c.source_id for c in chunks],
                        "decision": decision_label,
                        "nli_action": nli_action,
                        "evidence_score": verification.evidence_score,
                        "live_pubmed_triggered": live_pubmed_triggered,
                    }
                )
                lf_client.score_current_trace(
                    name="evidence_score",
                    value=verification.evidence_score,
                    comment=f"Evidence Threshold: {self.settings.evidence_threshold} | Action: {nli_action}",
                    data_type="NUMERIC",
                )
            except Exception:
                pass

        result = ChatResponse(
            trace_id=trace_id,
            intent=decision.intent,
            mode=request.mode,
            answer=answer,
            original_answer=original_answer if answer != original_answer else None,
            citations=verification.citations,
            claim_checks=verification.claims,
            subqueries=subquery_results,
            evidence_score=verification.evidence_score,
            evidence_threshold=self.settings.evidence_threshold,
            warnings=warnings,
            layer_distribution=layer_dist,
            ddi_report=ddi_report if (ddi_report.has_interaction or len(ddi_report.drugs_detected) >= 2) else None,
            live_pubmed_triggered=live_pubmed_triggered,
            live_pubmed_query=live_pubmed_query,
            latency_ms=_elapsed_ms(started),
            model=active_generator.model_name,
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            estimated_cost_usd=0.0 if (request.mode.value == "ollama_rag" or active_generator is self.ollama_adapter) else self._cost(total_input_tokens, total_output_tokens),
            demo_mode=self.settings.demo_mode,
            created_at=datetime.now(UTC),
        )
        self.database.save_trace(request.session_id, request.question, result, user_id=request.user_id)
        return result

    def get_source(self, source_id: str):
        if source_id.startswith("PUBMED-LIVE-") and hasattr(self, "live_pubmed"):
            live_src = self.live_pubmed.get_source(source_id)
            if live_src:
                return live_src
        return self.retriever.get_source(source_id)

    def _cost(self, input_tokens: int, output_tokens: int) -> float:
        value = (
            input_tokens * self.settings.active_input_cost_per_million
            + output_tokens * self.settings.active_output_cost_per_million
        ) / 1_000_000
        return round(value, 6)


def _elapsed_ms(started: float) -> int:
    return max(1, round((perf_counter() - started) * 1000))
