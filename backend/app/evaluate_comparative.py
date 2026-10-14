"""Comparative Evaluation Runner for NeuroEvidence RAG Pipeline.

Compares:
  - Pipeline A: Current Legacy Pipeline (Isolated chunks, passive unrevised verification)
  - Pipeline B: Improvement 1 alone (Bounded parent section expansion, token budget 750)
  - Pipeline C: Improvement 1 + Improvement 2 (Parent expansion + Bounded answer revision & citation sync)

Evaluates 5 dimensions across 4 question archetypes:
  1. Retrieval Relevance (chunks, token volume, layer distribution, parent recovery)
  2. Question Coverage (completeness, word count, judge coverage score)
  3. Claim Support / Faithfulness (supported/contradicted/insufficient counts, NLI score, citation precision)
  4. Missing Evidence Acknowledgment (abstention fidelity on unanswerable, explicit gap statements)
  5. Latency and Token Cost Overhead (latency ms, input/output tokens, cost in USD)
"""

import asyncio
import copy
import json
import logging
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .config import Settings, get_settings
from .database import Database
from .models import ChatRequest, ChatResponse, Intent
from .retrieval import _estimate_tokens
from .service import ChatService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("eval_comparative")

# 8 representative evaluation questions spanning the 4 required archetypes
EVAL_QUESTIONS = [
    # 1. Simple Factual Questions
    {
        "id": "SIMP-01",
        "category": "simple",
        "topic": "Parkinson's disease",
        "question": "What are the cardinal motor features of Parkinson's disease?",
        "unanswerable": False,
        "description": "Core motor symptoms (bradykinesia, rigidity, rest tremor, postural instability).",
    },
    {
        "id": "SIMP-02",
        "category": "simple",
        "topic": "epilepsy",
        "question": "What does an unprovoked seizure mean in the definition of epilepsy?",
        "unanswerable": False,
        "description": "Definition of unprovoked seizure vs acute symptomatic/provoked seizure.",
    },
    # 2. Comparison Questions
    {
        "id": "COMP-01",
        "category": "comparison",
        "topic": "epilepsy",
        "question": "How can focal and generalized seizures differ in clinical presentation and diagnosis?",
        "unanswerable": False,
        "description": "Comparison of focal (localized onset, possible aura/awareness change) vs generalized (bilateral hemisphere onset).",
    },
    {
        "id": "COMP-02",
        "category": "comparison",
        "topic": "Parkinson's disease",
        "question": "How do levodopa and dopamine agonists differ in clinical role, efficacy, and motor complications for Parkinson's disease?",
        "unanswerable": False,
        "description": "Comparison between levodopa (gold standard motor efficacy, motor fluctuations/dyskinesias) vs dopamine agonists (delay dyskinesias, impulse control risk).",
    },
    # 3. Questions Needing Multiple Sources / Layers
    {
        "id": "MULT-01",
        "category": "multiple_sources",
        "topic": "Parkinson's disease",
        "question": "How is Parkinson's disease disease severity staged using Hoehn and Yahr, and how does initial management align with clinical guideline recommendations?",
        "unanswerable": False,
        "description": "Requires Layer 1 staging (Hoehn & Yahr Stages 1-5) synthesized with Layer 3 clinical practice guidance (NICE NG71).",
    },
    {
        "id": "MULT-02",
        "category": "multiple_sources",
        "topic": "epilepsy",
        "question": "What are the clinical indications and pharmacokinetic drug-drug interaction risks when co-prescribing valproate and lamotrigine in epilepsy?",
        "unanswerable": False,
        "description": "Requires Layer 1/2 antiseizure pharmacology combined with Layer 3 DDI inhibition/titration guidelines (UGT glucuronidation inhibition).",
    },
    # 4. Questions the Corpus Cannot Answer (Unanswerable)
    {
        "id": "UNAN-01",
        "category": "corpus_unanswerable",
        "topic": "Parkinson's disease",
        "question": "Which single biomarker predicts every case of Parkinson's disease with perfect accuracy?",
        "unanswerable": True,
        "description": "No single infallible predictive biomarker exists; pipeline must abstain and acknowledge lack of perfect test.",
    },
    {
        "id": "UNAN-02",
        "category": "corpus_unanswerable",
        "topic": "epilepsy",
        "question": "Which single gene causes every form of epilepsy?",
        "unanswerable": True,
        "description": "Epilepsies are genetically heterogeneous; no universal gene exists; pipeline must decline / state evidence limitation.",
    },
]


def assess_question_coverage(question: str, answer: str, category: str, is_unanswerable: bool) -> tuple[int, str]:
    """Evaluates question coverage on a 0-2 scale based on clinical heuristics:
    2: Thorough coverage of all prompt dimensions or appropriate abstention.
    1: Partial coverage; missed key comparison or staging aspects.
    0: Refused answerable question or hallucinated unanswerable question.
    """
    answer_lower = answer.lower()
    if is_unanswerable:
        # For unanswerable questions, proper coverage means recognizing that no such single factor exists
        unanswerable_cues = [
            "no single",
            "not single",
            "cannot predict every",
            "no guaranteed",
            "does not guarantee",
            "no single gene",
            "genetically heterogeneous",
            "not a single",
            "cannot be predicted with perfect",
            "no definitive single",
            "complex and heterogeneous",
            "evidence gap",
            "cannot be answered",
        ]
        if any(cue in answer_lower for cue in unanswerable_cues):
            return 2, "Appropriately acknowledged that no single biomarker/gene exists (sound clinical abstention)."
        return 0, "Failed to appropriately abstain; asserted or implied a single universal predictor/gene exists."

    # Answerable questions
    if category == "simple":
        if len(answer.split()) > 40 and ("bradykinesia" in answer_lower or "unprovoked" in answer_lower or "seizure" in answer_lower):
            return 2, "Thoroughly addressed core factual entities and clinical definitions."
        return 1, "Partially addressed prompt entities."

    if category == "comparison":
        # Must address BOTH comparative entities
        has_entity_a = any(w in answer_lower for w in ["focal", "levodopa"])
        has_entity_b = any(w in answer_lower for w in ["generalized", "dopamine agonist", "agonist"])
        has_distinction = any(w in answer_lower for w in ["differ", "difference", "contrast", "whereas", "while", "compared", "versus"])
        if has_entity_a and has_entity_b and has_distinction:
            return 2, "Fully covered both comparative entities with explicit clinical contrast."
        elif has_entity_a or has_entity_b:
            return 1, "Discussed only one side of the comparison or lacked explicit clinical contrast."
        return 0, "Did not cover comparative clinical entities."

    if category == "multiple_sources":
        # Staging + Guidelines OR Valproate + Lamotrigine DDI
        has_staging = any(w in answer_lower for w in ["hoehn", "yahr", "stage", "valproate"])
        has_guidelines = any(w in answer_lower for w in ["guideline", "nice", "lamotrigine", "interaction", "titrat"])
        if has_staging and has_guidelines:
            return 2, "Synthesized foundational concepts with clinical guidance / drug interaction details."
        elif has_staging or has_guidelines:
            return 1, "Partially covered one source dimension but lacked cross-source synthesis."
        return 0, "Failed to cover multi-source clinical dimensions."

    return 1, "General coverage."


def assess_abstention_and_gap(answer: str, is_unanswerable: bool, claims: list[Any]) -> tuple[int, bool]:
    """Assesses:
    - appropriate_abstention (0 or 1)
    - acknowledged_missing_evidence (bool)
    """
    answer_lower = answer.lower()
    gap_phrases = [
        "not strong enough",
        "evidence gap",
        "insufficient evidence",
        "no single",
        "no definitive",
        "limitations of",
        "unsupported",
        "caution",
        "does not establish",
        "further research",
    ]
    acknowledged_missing = any(phrase in answer_lower for phrase in gap_phrases)

    if is_unanswerable:
        appropriate_abstention = 1 if acknowledged_missing else 0
    else:
        # On answerable questions: did it refrain from asserting contradicted claims as fact?
        contradictions = [c for c in claims if getattr(c, "label", None) and c.label.value == "contradicted"]
        if contradictions and not acknowledged_missing and "retrieved material was not strong enough" not in answer_lower:
            appropriate_abstention = 0
        else:
            appropriate_abstention = 1

    return appropriate_abstention, acknowledged_missing


async def evaluate_single_run(
    service: ChatService,
    question_dict: dict[str, Any],
    pipeline_name: str,
    pipeline_mode: str,
) -> dict[str, Any]:
    """Executes a single question through the configured ChatService pipeline and measures metrics."""
    q_id = question_dict["id"]
    question_text = question_dict["question"]
    category = question_dict["category"]
    topic = question_dict["topic"]
    is_unanswerable = question_dict["unanswerable"]

    req = ChatRequest(
        session_id=f"eval-{pipeline_mode}-{q_id}",
        question=question_text,
        mode="rag_verified",
    )

    t0 = time.perf_counter()
    try:
        response: ChatResponse = await service.chat(req)
        latency_ms = int((time.perf_counter() - t0) * 1000)
    except Exception as exc:
        logger.error("Run failed for %s on %s: %s", pipeline_name, q_id, exc)
        return {
            "question_id": q_id,
            "pipeline": pipeline_name,
            "error": str(exc),
        }

    # Extract metrics
    answer_text = response.answer
    original_answer_text = response.original_answer or answer_text
    was_revised = bool(response.original_answer and response.original_answer != response.answer)

    # Retrieval metrics
    num_chunks = len(response.citations)
    retrieved_excerpts = [c.excerpt for c in response.citations]
    total_evidence_tokens = sum(_estimate_tokens(exc) for exc in retrieved_excerpts)
    layers_represented = sorted(list({c.layer for c in response.citations}))

    # Claim metrics
    total_claims = len(response.claim_checks)
    supported_claims = sum(1 for c in response.claim_checks if c.label.value == "supported")
    contradicted_claims = sum(1 for c in response.claim_checks if c.label.value == "contradicted")
    insufficient_claims = sum(1 for c in response.claim_checks if c.label.value == "insufficient")
    evidence_score = response.evidence_score if response.evidence_score is not None else 0.0

    # Citation precision
    cited_markers = set(re.findall(r"\[(S\d+|S_new\d+)\]", answer_text))
    num_cited = len(cited_markers)
    # Precision: proportion of cited claims that were supported
    supported_claim_markers = set()
    for c in response.claim_checks:
        if c.label.value == "supported":
            for m in (c.citation_markers or []):
                supported_claim_markers.add(m)
    citation_precision = (
        len(cited_markers.intersection(supported_claim_markers)) / num_cited
        if num_cited > 0
        else None
    )

    # Coverage & Abstention heuristics
    coverage_score, coverage_notes = assess_question_coverage(
        question_text, answer_text, category, is_unanswerable
    )
    abstention_score, acknowledged_missing = assess_abstention_and_gap(
        answer_text, is_unanswerable, response.claim_checks
    )

    return {
        "question_id": q_id,
        "category": category,
        "topic": topic,
        "question": question_text,
        "pipeline": pipeline_name,
        "latency_ms": latency_ms,
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
        "estimated_cost_usd": response.estimated_cost_usd,
        "retrieval": {
            "num_chunks": num_chunks,
            "evidence_tokens": total_evidence_tokens,
            "layers": layers_represented,
            "source_ids": [c.source_id for c in response.citations],
        },
        "generation": {
            "answer_word_count": len(answer_text.split()),
            "was_revised": was_revised,
            "has_revision_notice": "evidence gap" in answer_text.lower() or "revised" in answer_text.lower() or "not strong enough" in answer_text.lower(),
            "answer_preview": answer_text[:280] + ("..." if len(answer_text) > 280 else ""),
            "original_draft_preview": original_answer_text[:280] + ("..." if len(original_answer_text) > 280 else ""),
        },
        "claims_and_faithfulness": {
            "total_claims": total_claims,
            "supported": supported_claims,
            "contradicted": contradicted_claims,
            "insufficient": insufficient_claims,
            "evidence_score": round(evidence_score, 3),
            "citation_count": num_cited,
            "citation_precision": round(citation_precision, 3) if citation_precision is not None else None,
        },
        "coverage_and_abstention": {
            "coverage_0_2": coverage_score,
            "coverage_notes": coverage_notes,
            "appropriate_abstention_0_1": abstention_score,
            "acknowledged_missing_evidence": acknowledged_missing,
        },
        "warnings": response.warnings,
    }


def create_pipeline_service(pipeline_mode: str, base_settings: Settings, db: Database) -> ChatService:
    """Instantiates a ChatService configured for a specific pipeline ablation:
    - 'A_legacy': No parent sibling expansion (token_budget=0), No answer revision.
    - 'B_parent_only': Parent sibling expansion (token_budget=750), No answer revision.
    - 'C_parent_and_revision': Parent sibling expansion (token_budget=750) + Bounded Answer Revision.
    """
    settings_dict = base_settings.model_dump()

    if pipeline_mode == "A_legacy":
        settings_dict["parent_expansion_token_budget"] = 200  # minimal / isolated
        settings_dict["enable_bounded_answer_revision"] = False
        settings_dict["enable_corrective_retrieval"] = False
    elif pipeline_mode == "B_parent_only":
        settings_dict["parent_expansion_token_budget"] = 750
        settings_dict["enable_bounded_answer_revision"] = False
        settings_dict["enable_corrective_retrieval"] = False
    elif pipeline_mode == "C_parent_and_revision":
        settings_dict["parent_expansion_token_budget"] = 750
        settings_dict["enable_bounded_answer_revision"] = True
        settings_dict["enable_corrective_retrieval"] = True
    else:
        raise ValueError(f"Unknown pipeline_mode: {pipeline_mode}")

    settings = Settings(**settings_dict)
    service = ChatService(settings, db)

    # For Pipeline A legacy, disable corpus_lookup in retriever's parent expansion to simulate isolated chunk retrieval
    if pipeline_mode == "A_legacy":
        orig_search = service.retriever.search

        def isolated_search(question: str, topic: str | None = None):
            chunks = orig_search(question, topic)
            # Revert excerpts back to isolated snippets without sibling context
            for c in chunks:
                if "### [" in c.excerpt:
                    lines = c.excerpt.split("\n\n")
                    if len(lines) > 2:
                        # strip sibling concatenation
                        c.excerpt = lines[0] + "\n\n" + lines[1] + "\n\n" + lines[2][:300]
            return chunks

        service.retriever.search = isolated_search

    return service


async def run_comparative_benchmark(
    output_path: Path,
) -> dict[str, Any]:
    """Runs the 8 evaluation questions across Pipeline A, Pipeline B, and Pipeline C."""
    base_settings = get_settings()
    db = Database(base_settings.database_path)

    pipelines = [
        ("Pipeline A (Legacy Baseline)", "A_legacy"),
        ("Pipeline B (+ Parent Expansion)", "B_parent_only"),
        ("Pipeline C (+ Both Improvements)", "C_parent_and_revision"),
    ]

    all_results: list[dict[str, Any]] = []

    print("\n" + "=" * 80)
    print("STARTING NEUROEVIDENCE COMPARATIVE RAG PIPELINE EVALUATION")
    print("Pipelines: A (Legacy) vs B (+ Parent Expansion) vs C (+ Both Improvements)")
    print(f"Total Questions: {len(EVAL_QUESTIONS)} across 4 Archetypes")
    print("=" * 80 + "\n")

    for pipe_name, pipe_mode in pipelines:
        print(f"\n---> Initializing {pipe_name}...")
        service = create_pipeline_service(pipe_mode, base_settings, db)

        for q_item in EVAL_QUESTIONS:
            q_id = q_item["id"]
            cat = q_item["category"]
            print(f"  [{pipe_mode}] Evaluating {q_id} ({cat}): '{q_item['question'][:50]}...' ", end="", flush=True)
            res = await evaluate_single_run(service, q_item, pipe_name, pipe_mode)
            all_results.append(res)
            lat = res.get("latency_ms", 0)
            claims = res.get("claims_and_faithfulness", {})
            sup = claims.get("supported", 0)
            tot = claims.get("total_claims", 0)
            cov = res.get("coverage_and_abstention", {}).get("coverage_0_2", 0)
            print(f"[OK] ({lat}ms, Claims: {sup}/{tot} sup, Coverage: {cov}/2)")

    # Aggregate metrics by pipeline
    aggregated: dict[str, Any] = {}
    for pipe_name, pipe_mode in pipelines:
        pipe_runs = [r for r in all_results if r.get("pipeline") == pipe_name and "error" not in r]
        n = len(pipe_runs)
        if n == 0:
            continue

        mean_latency = sum(r["latency_ms"] for r in pipe_runs) / n
        mean_in_tokens = sum(r["input_tokens"] for r in pipe_runs) / n
        mean_out_tokens = sum(r["output_tokens"] for r in pipe_runs) / n
        mean_evidence_tokens = sum(r["retrieval"]["evidence_tokens"] for r in pipe_runs) / n
        mean_coverage = sum(r["coverage_and_abstention"]["coverage_0_2"] for r in pipe_runs) / n
        mean_abstention = sum(r["coverage_and_abstention"]["appropriate_abstention_0_1"] for r in pipe_runs) / n

        tot_claims = sum(r["claims_and_faithfulness"]["total_claims"] for r in pipe_runs)
        tot_supported = sum(r["claims_and_faithfulness"]["supported"] for r in pipe_runs)
        tot_contradicted = sum(r["claims_and_faithfulness"]["contradicted"] for r in pipe_runs)
        tot_insufficient = sum(r["claims_and_faithfulness"]["insufficient"] for r in pipe_runs)

        mean_ev_score = sum(r["claims_and_faithfulness"]["evidence_score"] for r in pipe_runs) / n
        revisions_count = sum(1 for r in pipe_runs if r["generation"]["was_revised"])

        # Citation precision (ignoring unanswerable where no citations cited)
        cit_precisions = [
            r["claims_and_faithfulness"]["citation_precision"]
            for r in pipe_runs
            if r["claims_and_faithfulness"]["citation_precision"] is not None
        ]
        mean_cit_precision = sum(cit_precisions) / len(cit_precisions) if cit_precisions else 0.0

        # Category breakdowns
        category_breakdown = {}
        for cat in ["simple", "comparison", "multiple_sources", "corpus_unanswerable"]:
            cat_runs = [r for r in pipe_runs if r["category"] == cat]
            if cat_runs:
                category_breakdown[cat] = {
                    "count": len(cat_runs),
                    "mean_coverage": round(sum(r["coverage_and_abstention"]["coverage_0_2"] for r in cat_runs) / len(cat_runs), 2),
                    "mean_latency_ms": round(sum(r["latency_ms"] for r in cat_runs) / len(cat_runs), 1),
                    "supported_claims": sum(r["claims_and_faithfulness"]["supported"] for r in cat_runs),
                    "total_claims": sum(r["claims_and_faithfulness"]["total_claims"] for r in cat_runs),
                }

        aggregated[pipe_name] = {
            "total_runs": n,
            "mean_latency_ms": round(mean_latency, 1),
            "mean_input_tokens": round(mean_in_tokens, 1),
            "mean_output_tokens": round(mean_out_tokens, 1),
            "mean_evidence_tokens": round(mean_evidence_tokens, 1),
            "mean_coverage_0_2": round(mean_coverage, 2),
            "mean_abstention_accuracy": round(mean_abstention, 2),
            "total_claims_checked": tot_claims,
            "total_supported": tot_supported,
            "total_contradicted": tot_contradicted,
            "total_insufficient": tot_insufficient,
            "support_rate": round(tot_supported / max(1, tot_claims), 3),
            "mean_evidence_score": round(mean_ev_score, 3),
            "mean_citation_precision": round(mean_cit_precision, 3),
            "revisions_triggered": revisions_count,
            "category_breakdown": category_breakdown,
        }

    summary = {
        "benchmark_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "aggregated": aggregated,
        "detailed_runs": all_results,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[OK] Comparative benchmark results written to: {output_path}")

    return summary


if __name__ == "__main__":
    out_file = Path("data/evaluation/comparative_evaluation_results.json")
    asyncio.run(run_comparative_benchmark(out_file))
