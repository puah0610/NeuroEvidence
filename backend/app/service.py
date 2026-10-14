from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

from .config import Settings
from .database import Database
from .ddi.checker import get_ddi_checker
from .decomposition import QueryDecomposer, retrieve_with_decomposition
from .llm import DemoGenerator, Generator, create_llm_adapter
from .models import ChatRequest, ChatResponse, Intent
from .retrieval import ChromaRetriever, DemoRetriever, TransformerDenseEmbedder
from .safety import classify_query
from .verification import CitationVerifier, make_nli, verify_answer


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

    async def chat(self, request: ChatRequest) -> ChatResponse:
        started = perf_counter()
        trace_id = str(uuid4())
        decision = classify_query(request.question)

        if decision.intent != Intent.educational_in_scope:
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
            self.database.save_trace(request.session_id, request.question, result)
            return result

        if request.mode.value == "baseline":
            generation = self.generator.generate_baseline(request.question)
            answer = generation.text
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
            self.database.save_trace(request.session_id, request.question, result)
            return result

        # Scan query for drug interactions (combining local rules & live openFDA API)
        ddi_report = await self.ddi_checker.analyze_query(request.question)

        # Step 1: Selective Query Decomposition & Triad Retrieval
        decomp_plan = self.decomposer.decompose(request.question, topic=decision.topic)
        chunks, subquery_results = retrieve_with_decomposition(
            self.retriever, decomp_plan, decision.topic, self.settings
        )

        unanswered_parts = [
            sq.missing_evidence_statement
            for sq in subquery_results
            if not sq.has_evidence and sq.missing_evidence_statement
        ]

        if not chunks:
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
                latency_ms=_elapsed_ms(started),
                model=self.generator.model_name,
                demo_mode=self.settings.demo_mode,
                created_at=datetime.now(UTC),
            )
            self.database.save_trace(request.session_id, request.question, result)
            return result

        generation = self.generator.generate_grounded(
            request.question, chunks, ddi_report=ddi_report, unanswered_parts=unanswered_parts
        )
        original_answer = generation.text
        total_input_tokens = generation.input_tokens
        total_output_tokens = generation.output_tokens

        # Step 2: Primary claim verification + Step 3: Targeted Secondary Retrieval (1 pass)
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
        if verification.chunks:
            chunks = verification.chunks
        answer = original_answer

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

        if needs_revision:
            # Step 4: Revise unsupported claims and inline citations
            revision_generation = self.generator.revise_grounded(
                request.question,
                original_answer,
                verification.claims,
                chunks,
                ddi_report=ddi_report,
                unanswered_parts=unanswered_parts,
            )
            revised_draft = revision_generation.text
            total_input_tokens += revision_generation.input_tokens
            total_output_tokens += revision_generation.output_tokens

            # Step 5: Verify again (bounded: corrective retrieval disabled to prevent infinite loops)
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

            answer = revised_draft
            verification = revised_verification

            # Step 6: Return supported content or explicitly state remaining evidence gap
            if verification.evidence_score < self.settings.evidence_threshold or any(
                item.label.value == "contradicted" for item in verification.claims
            ):
                if "evidence gap" not in answer.lower():
                    answer = (
                        "The retrieved clinical material was not strong enough to produce a fully verified answer. "
                        "The revised draft and its verification details are retained below for research inspection.\n\n"
                        + answer
                    )

        layer_dist: dict[str, int] = {}
        for citation in verification.citations:
            layer_key = f"Layer {citation.layer}"
            layer_dist[layer_key] = layer_dist.get(layer_key, 0) + 1

        warnings = list(verification.warnings)
        for sq in subquery_results:
            if not sq.has_evidence:
                warnings.append(f"Subquery '{sq.intent_description}' lacked direct evidence in indexed corpus.")

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
            latency_ms=_elapsed_ms(started),
            model=self.generator.model_name,
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            estimated_cost_usd=self._cost(total_input_tokens, total_output_tokens),
            demo_mode=self.settings.demo_mode,
            created_at=datetime.now(UTC),
        )
        self.database.save_trace(request.session_id, request.question, result)
        return result

    def get_source(self, source_id: str):
        return self.retriever.get_source(source_id)

    def _cost(self, input_tokens: int, output_tokens: int) -> float:
        value = (
            input_tokens * self.settings.active_input_cost_per_million
            + output_tokens * self.settings.active_output_cost_per_million
        ) / 1_000_000
        return round(value, 6)


def _elapsed_ms(started: float) -> int:
    return max(1, round((perf_counter() - started) * 1000))
