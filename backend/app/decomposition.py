"""Selective Query Decomposition Module for NeuroEvidence 3-Layer Triad Architecture.

Decomposes compound, multi-part clinical questions into 2 or at most 3 focused subqueries
aligned with the 3-Layer Triad:
  - Layer 1: Foundational Knowledge (pathophysiology, etiology, definitions, staging, mechanisms)
  - Layer 2: Clinical Practice Guidelines (NICE guidelines, line of therapy, management recommendations)
  - Layer 3: Empirical Research Evidence (clinical trials, RCTs, meta-analyses, outcomes)

Key Principles:
1. Selective: Simple atomic queries (definitions, single symptoms) are NOT decomposed and retrieve directly.
2. Constraint Preservation: Every generated subquery inherits the original question's condition and scope.
3. Multi-Part Retrieval & Deduplication: Retrieves for each subquery, merges results, removes duplicates.
4. Evidence Coverage & Gap Detection: Checks that every requested subquery has evidence, or explicitly identifies it as unanswered.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from .config import Settings
from .models import RetrievedChunk, SubqueryResult
from .tracing import start_span

try:
    from langfuse import get_client
except ImportError:
    def get_client():
        return None

logger = logging.getLogger(__name__)

# Triad Layer Metadata
LAYER_METADATA = {
    1: ("Layer 1: Foundational Knowledge", "NCBI Bookshelf / StatPearls"),
    2: ("Layer 2: Clinical Guidelines", "NICE Guidelines"),
    3: ("Layer 3: Empirical Evidence & Trials", "PubMed Central / Cochrane"),
}

# Clinical Lexicon for Triad Layer Classification
FOUNDATIONAL_KEYWORDS = frozenset({
    "cause", "causes", "etiology", "pathophysiology", "mechanism", "mechanisms",
    "neuropathology", "neurobiology", "definition", "define", "presentation",
    "present", "symptom", "symptoms", "staging", "stage", "stages", "hoehn",
    "yahr", "semiology", "classification", "phenotype", "dopaminergic",
    "basal ganglia", "synuclein", "seizure type", "unprovoked",
})

GUIDELINE_KEYWORDS = frozenset({
    "guideline", "guidelines", "nice", "recommendation", "recommendations",
    "firstline", "first-line", "second-line", "management", "treatment",
    "treatments", "pharmacotherapy", "prescribe", "titrat", "algorithm",
    "line of therapy", "referral", "pathway", "ilae", "consensus",
})

EVIDENCE_KEYWORDS = frozenset({
    "evidence", "clinical trial", "trial", "trials", "rct", "rcts",
    "study", "studies", "empirical", "meta-analysis", "systematic review",
    "cochrane", "sanad", "leap", "efficacy", "outcomes", "outcome",
    "support", "supports", "long-term", "remission",
})

# Condition / Subject Extraction Keywords
KNOWN_CONDITIONS = [
    "parkinson's disease", "parkinson disease", "parkinson's", "parkinson",
    "epilepsy", "seizure", "seizures", "status epilepticus",
    "levodopa", "dopamine agonist", "dopamine agonists",
    "valproate", "lamotrigine", "carbamazepine", "levetiracetam",
]


@dataclass
class SubquerySpec:
    subquery_id: str
    query_text: str
    intent_description: str
    target_layer: int | None = None
    target_layer_name: str | None = None


@dataclass
class DecompositionPlan:
    original_question: str
    is_decomposed: bool
    subqueries: list[SubquerySpec] = field(default_factory=list)
    rationale: str = ""


class QueryDecomposer:
    """Selective Query Decomposer for Clinical Neurology Inquiries."""

    def __init__(self, settings: Settings, generator: Any = None):
        self.settings = settings
        self.generator = generator

    def decompose(self, question: str, topic: str | None = None) -> DecompositionPlan:
        """Analyzes a question and selectively decomposes multi-part inquiries into 2 or 3 subqueries.
        Preserves clinical constraints (condition, medications) on all subqueries.
        """
        lf_client = get_client()
        with start_span(lf_client, "query_decomposition", as_type="task") as decomp_span:
            plan = self._decompose_internal(question, topic)
            if decomp_span:
                try:
                    decomp_span.update(
                        metadata={
                            "is_decomposed": plan.is_decomposed,
                            "subqueries_count": len(plan.subqueries),
                            "rationale": plan.rationale,
                        }
                    )
                except Exception:
                    pass
            return plan

    def _decompose_internal(self, question: str, topic: str | None = None) -> DecompositionPlan:
        if not getattr(self.settings, "enable_query_decomposition", True):
            return DecompositionPlan(
                original_question=question,
                is_decomposed=False,
                subqueries=[
                    SubquerySpec(
                        subquery_id="SQ-1",
                        query_text=question,
                        intent_description="Direct inquiry",
                        target_layer=None,
                        target_layer_name=None,
                    )
                ],
                rationale="Query decomposition disabled via configuration.",
            )

        # 1. Detect if question is compound vs atomic
        is_compound, detected_facets = self._analyze_query_structure(question)

        if not is_compound or len(detected_facets) <= 1:
            # Single information need: do NOT force decomposition
            target_layer = self._detect_layer_for_single_query(question)
            layer_name = LAYER_METADATA.get(target_layer, (None, None))[0] if target_layer else None
            return DecompositionPlan(
                original_question=question,
                is_decomposed=False,
                subqueries=[
                    SubquerySpec(
                        subquery_id="SQ-1",
                        query_text=question,
                        intent_description="Direct inquiry",
                        target_layer=target_layer,
                        target_layer_name=layer_name,
                    )
                ],
                rationale="Atomic query with single clinical information need; retrieved directly without decomposition.",
            )

        # 2. Decompose compound query into at most 2 or 3 subqueries
        max_sub = getattr(self.settings, "max_decomposition_subqueries", 3)
        subqueries = self._build_subqueries_from_facets(question, detected_facets, topic, max_subqueries=max_sub)

        return DecompositionPlan(
            original_question=question,
            is_decomposed=True,
            subqueries=subqueries,
            rationale=f"Compound query decomposed into {len(subqueries)} focused subqueries across Triad layers.",
        )

    def _extract_primary_condition(self, question: str, topic: str | None = None) -> str:
        """Extracts the clinical condition or subject to ensure constraint preservation."""
        lower_q = question.lower()
        for cond in KNOWN_CONDITIONS:
            if cond in lower_q:
                if "parkinson" in cond:
                    return "Parkinson's disease"
                if "epilep" in cond or "seizure" in cond:
                    return "Epilepsy"
                return cond.capitalize()
        if topic and topic.lower() != "neurology":
            if "parkinson" in topic.lower():
                return "Parkinson's disease"
            if "epilep" in topic.lower():
                return "Epilepsy"
            return topic.capitalize()
        return "Neurology"

    def _analyze_query_structure(self, question: str) -> tuple[bool, list[dict[str, Any]]]:
        """Examines if query contains multiple distinct information needs across Triad layers."""
        lower_q = question.lower()

        # Check for conjunctions that separate clinical clauses
        conjunction_patterns = [
            r",\s*and\s+(?:what|how|which|why|does|is|are|can)\b",
            r"\band\s+(?:what|how|which|why|does|is|are|can)\b",
            r",\s*and\s+",
            r";\s*",
            r"\bas\s+well\s+as\b",
            r"\balong\s+with\b",
            r"\bcompared\s+to\b",
            r"\bversus\b",
            r"\bwhile\b",
            r"\bwhereas\b",
        ]

        has_conjunction = any(re.search(pat, lower_q) for pat in conjunction_patterns)

        # Check multi-layer keyword presence
        has_foundational = any(kw in lower_q for kw in FOUNDATIONAL_KEYWORDS)
        has_guidelines = any(kw in lower_q for kw in GUIDELINE_KEYWORDS)
        has_evidence = any(kw in lower_q for kw in EVIDENCE_KEYWORDS)

        layers_present = sum([bool(has_foundational), bool(has_guidelines), bool(has_evidence)])

        # A question is compound if it has conjunctions + multiple layer needs, or explicit 3-layer triad request
        is_compound = (has_conjunction and layers_present >= 2) or (layers_present >= 3)

        facets = []
        if is_compound:
            if has_foundational:
                facets.append({
                    "layer": 1,
                    "layer_name": LAYER_METADATA[1][0],
                    "intent": "Foundational explanation (pathophysiology, etiology, definitions, staging)",
                })
            if has_guidelines:
                facets.append({
                    "layer": 2,
                    "layer_name": LAYER_METADATA[2][0],
                    "intent": "Clinical guideline recommendations (NICE guidelines, line of therapy)",
                })
            if has_evidence:
                facets.append({
                    "layer": 3,
                    "layer_name": LAYER_METADATA[3][0],
                    "intent": "Supporting research evidence (clinical trials, RCTs, empirical outcomes)",
                })

        return is_compound, facets

    def _detect_layer_for_single_query(self, question: str) -> int | None:
        """Determines target layer for atomic queries if clearly focused on one Triad layer."""
        lower = question.lower()
        has_foundational = any(kw in lower for kw in FOUNDATIONAL_KEYWORDS)
        has_guidelines = any(kw in lower for kw in GUIDELINE_KEYWORDS)
        has_evidence = any(kw in lower for kw in EVIDENCE_KEYWORDS)

        if has_guidelines and not has_foundational and not has_evidence:
            return 2
        if has_evidence and not has_foundational and not has_guidelines:
            return 3
        if has_foundational and not has_guidelines and not has_evidence:
            return 1
        return None

    def _build_subqueries_from_facets(
        self,
        question: str,
        facets: list[dict[str, Any]],
        topic: str | None,
        max_subqueries: int = 3,
    ) -> list[SubquerySpec]:
        """Constructs 2 to 3 constraint-preserving subqueries from detected facets."""
        condition = self._extract_primary_condition(question, topic)
        lower_q = question.lower()

        # Split clauses by conjunctions
        clauses = re.split(r",\s*and\s+|\band\s+|;\s*|\bas\s+well\s+as\b", question)
        clean_clauses = [c.strip() for c in clauses if len(c.strip()) > 5]

        subqueries: list[SubquerySpec] = []
        facets = facets[:max_subqueries]

        for idx, facet in enumerate(facets, start=1):
            target_layer = facet["layer"]
            intent_desc = facet["intent"]

            # Match clause if possible
            matched_clause = None
            for cl in clean_clauses:
                cl_lower = cl.lower()
                if target_layer == 1 and any(kw in cl_lower for kw in FOUNDATIONAL_KEYWORDS):
                    matched_clause = cl
                    break
                elif target_layer == 2 and any(kw in cl_lower for kw in GUIDELINE_KEYWORDS):
                    matched_clause = cl
                    break
                elif target_layer == 3 and any(kw in cl_lower for kw in EVIDENCE_KEYWORDS):
                    matched_clause = cl
                    break

            if matched_clause:
                # Ensure constraint preservation: if the clause doesn't explicitly name the condition, anchor it
                sub_text = matched_clause.strip().rstrip("?.!;, ")
                if condition.lower() not in sub_text.lower():
                    sub_text = f"{sub_text} for {condition}"
                # Ensure it ends with a question mark and starts with uppercase
                if not sub_text.endswith("?"):
                    sub_text += "?"
                sub_text = sub_text[0].upper() + sub_text[1:]
            else:
                # Synthesize constraint-preserving query based on facet and condition
                if target_layer == 1:
                    sub_text = f"What is the foundational pathophysiology, etiology, and presentation of {condition}?"
                elif target_layer == 2:
                    sub_text = f"What are the clinical guideline recommendations and management strategies for {condition}?"
                elif target_layer == 3:
                    sub_text = f"What empirical clinical trial and research evidence supports treatments for {condition}?"
                else:
                    sub_text = f"{question} ({condition})"

            subqueries.append(
                SubquerySpec(
                    subquery_id=f"SQ-{idx}",
                    query_text=sub_text,
                    intent_description=intent_desc,
                    target_layer=target_layer,
                    target_layer_name=facet["layer_name"],
                )
            )

        return subqueries


def retrieve_with_decomposition(
    retriever: Any,
    plan: DecompositionPlan,
    topic: str | None,
    settings: Settings,
) -> tuple[list[RetrievedChunk], list[SubqueryResult]]:
    """Executes multi-part retrieval across subqueries, removes duplicates, ensures balanced
    Triad representation, and checks evidence coverage per requested part.
    """
    subquery_results: list[SubqueryResult] = []
    chunks_by_subquery: dict[str, list[RetrievedChunk]] = {}
    min_evidence_threshold = 0.20

    # 1. Retrieve for each subquery
    for sq in plan.subqueries:
        try:
            candidates = retriever.search(sq.query_text, topic=topic)
        except Exception as exc:
            logger.warning("Retrieval failed for subquery %s (%s): %s", sq.subquery_id, sq.query_text, exc)
            candidates = []

        # If subquery specified a target layer, prioritize matching layer chunks
        if sq.target_layer is not None and candidates:
            layer_matches = [c for c in candidates if c.layer == sq.target_layer]
            other_matches = [c for c in candidates if c.layer != sq.target_layer]
            # Boost target layer matches
            for c in layer_matches:
                c.relevance = min(1.0, c.relevance * 1.15)
            candidates = layer_matches + other_matches

        chunks_by_subquery[sq.subquery_id] = candidates

        # Check evidence coverage
        has_evidence = len(candidates) > 0 and any(c.relevance >= min_evidence_threshold for c in candidates)
        missing_stmt = None
        if not has_evidence:
            missing_stmt = (
                f"No indexed evidence was found in the corpus for requested part '{sq.intent_description}' "
                f"({sq.query_text})."
            )

        subquery_results.append(
            SubqueryResult(
                subquery_id=sq.subquery_id,
                query_text=sq.query_text,
                intent_description=sq.intent_description,
                target_layer=sq.target_layer,
                target_layer_name=sq.target_layer_name,
                has_evidence=has_evidence,
                chunks_found=len(candidates),
                missing_evidence_statement=missing_stmt,
            )
        )

    # 2. Combine and Deduplicate
    seen_chunk_ids: set[str] = set()
    seen_parents: dict[str, RetrievedChunk] = {}
    combined_chunks: list[RetrievedChunk] = []

    # Round-robin selection across subqueries to ensure balanced Triad representation
    max_rounds = max((len(c_list) for c_list in chunks_by_subquery.values()), default=0)
    target_top_k = getattr(settings, "retrieval_top_k", 8)

    for r in range(max_rounds):
        for sq in plan.subqueries:
            sq_list = chunks_by_subquery.get(sq.subquery_id, [])
            if r < len(sq_list):
                cand = sq_list[r]
                # Deduplication check by chunk_id and parent_id
                pid = cand.parent_id or f"{cand.document_id}::{cand.section or 'main'}"

                if cand.chunk_id in seen_chunk_ids:
                    continue
                seen_chunk_ids.add(cand.chunk_id)

                if pid in seen_parents:
                    # Already have parent context from another chunk: update relevance to maximum
                    existing = seen_parents[pid]
                    if cand.relevance > existing.relevance:
                        existing.relevance = cand.relevance
                else:
                    seen_parents[pid] = cand
                    combined_chunks.append(cand)

                if len(combined_chunks) >= target_top_k:
                    break
        if len(combined_chunks) >= target_top_k:
            break

    # If round-robin didn't fill capacity, add remaining distinct candidates
    if len(combined_chunks) < target_top_k:
        for sq in plan.subqueries:
            for cand in chunks_by_subquery.get(sq.subquery_id, []):
                if cand.chunk_id not in seen_chunk_ids:
                    seen_chunk_ids.add(cand.chunk_id)
                    combined_chunks.append(cand)
                    if len(combined_chunks) >= target_top_k:
                        break
            if len(combined_chunks) >= target_top_k:
                break

    # Re-sort final combined pool by relevance
    combined_chunks.sort(key=lambda c: c.relevance, reverse=True)

    return combined_chunks, subquery_results
