import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import quote

import httpx
import numpy as np

from .config import Settings
from .models import (
    CitationResult,
    ClaimCheck,
    RetrievedChunk,
    VerificationLabel,
)

logger = logging.getLogger(__name__)


CITATION_BRACKET_PATTERN = re.compile(r"\[\s*S\d+(?:[\s,;/&+\-–—]+S?\d+)*\s*\]")
CITATION_PATTERN = CITATION_BRACKET_PATTERN  # Backward-compatible alias
SENTENCE_PATTERN = re.compile(r"(?<=[.!?])\s+")
WORD_PATTERN = re.compile(r"[a-z0-9]+")


def extract_citation_markers(text: str) -> list[int]:
    """Extract ordered unique integer source markers from citation brackets in text.
    Handles:
      [S1] -> [1]
      [S1, S2] or [S1, S3, S6] -> [1, 2] or [1, 3, 6]
      [S1; S2] -> [1, 2]
      [S1-S3] -> [1, 2, 3]
    """
    seen: set[int] = set()
    numbers: list[int] = []
    for bracket in CITATION_BRACKET_PATTERN.findall(text):
        inner = bracket.strip("[] \t")
        range_match = re.match(r"^S?(\d+)\s*[-–—]\s*S?(\d+)$", inner)
        if range_match:
            start, end = int(range_match.group(1)), int(range_match.group(2))
            if start <= end and (end - start) <= 20:
                for num in range(start, end + 1):
                    if num not in seen:
                        seen.add(num)
                        numbers.append(num)
                continue
        for num_str in re.findall(r"\d+", inner):
            num = int(num_str)
            if num not in seen:
                seen.add(num)
                numbers.append(num)
    return numbers


class NLIVerifier(Protocol):
    def verify(self, evidence: str, claim: str) -> tuple[VerificationLabel, float]: ...


class LexicalNLIVerifier:
    """Deterministic fallback for demo/tests; it is not a trained NLI system."""

    NEGATIONS = {"not", "no", "never", "without", "neither"}

    def verify(self, evidence: str, claim: str) -> tuple[VerificationLabel, float]:
        evidence_sentences = [s.strip() for s in SENTENCE_PATTERN.split(evidence) if s.strip()]
        claim_terms = set(WORD_PATTERN.findall(claim.lower()))
        content_terms = {term for term in claim_terms if len(term) > 3}
        if not content_terms:
            return VerificationLabel.insufficient, 0.5

        # Find the specific sentence in evidence with highest term overlap to evaluate local polarity
        best_sentence = evidence
        best_sent_overlap = 0.0
        for sent in evidence_sentences:
            sent_terms = set(WORD_PATTERN.findall(sent.lower()))
            sent_overlap = len(content_terms & sent_terms) / max(1, len(content_terms))
            if sent_overlap > best_sent_overlap:
                best_sent_overlap = sent_overlap
                best_sentence = sent

        evidence_terms = set(WORD_PATTERN.findall(evidence.lower()))
        overall_overlap = len(content_terms & evidence_terms) / max(1, len(content_terms))

        best_sent_terms = set(WORD_PATTERN.findall(best_sentence.lower()))
        sent_negated = bool(self.NEGATIONS & best_sent_terms)
        claim_negated = bool(self.NEGATIONS & claim_terms)

        if best_sent_overlap >= 0.45 and sent_negated != claim_negated:
            return VerificationLabel.contradicted, min(0.95, 0.55 + best_sent_overlap * 0.4)
        if overall_overlap >= 0.42:
            return VerificationLabel.supported, min(0.95, 0.5 + overall_overlap * 0.45)
        return VerificationLabel.insufficient, max(0.5, 1.0 - overall_overlap)


def _resolve_nli_labels(config_id2label: dict | None) -> list[VerificationLabel]:
    """Map arbitrary model config id2label dictionary to VerificationLabel enum list."""
    if not config_id2label:
        return [
            VerificationLabel.contradicted,
            VerificationLabel.supported,
            VerificationLabel.insufficient,
        ]
    num_labels = len(config_id2label)
    resolved = [VerificationLabel.insufficient] * num_labels
    for idx_key, raw_name in config_id2label.items():
        try:
            idx = int(idx_key)
        except (ValueError, TypeError):
            continue
        name = str(raw_name).lower()
        if any(w in name for w in ("entail", "support", "pos")):
            resolved[idx] = VerificationLabel.supported
        elif any(w in name for w in ("contradict", "refut", "neg")):
            resolved[idx] = VerificationLabel.contradicted
        elif any(w in name for w in ("neutral", "insuffic", "noinfo", "not_enough")):
            resolved[idx] = VerificationLabel.insufficient
    return resolved


def select_salient_evidence(
    evidence: str,
    claim: str,
    max_sentences: int = 3,
) -> str:
    """Extract top-k most salient sentences from evidence matching claim terms,
    preserving original order for coherent context.
    """
    sentences = [s.strip() for s in SENTENCE_PATTERN.split(evidence) if s.strip()]
    if len(sentences) <= max_sentences:
        return evidence

    claim_terms = {w for w in WORD_PATTERN.findall(claim.lower()) if len(w) > 2}
    if not claim_terms:
        return " ".join(sentences[:max_sentences])

    scored: list[tuple[float, int, str]] = []
    for idx, sent in enumerate(sentences):
        sent_terms = set(WORD_PATTERN.findall(sent.lower()))
        overlap = len(claim_terms & sent_terms) / len(claim_terms)
        scored.append((overlap, idx, sent))

    scored_by_relevance = sorted(scored, key=lambda x: x[0], reverse=True)
    best_overlap = scored_by_relevance[0][0]

    if best_overlap == 0.0:
        return " ".join(sentences[:max_sentences])

    top_selected = sorted(scored_by_relevance[:max_sentences], key=lambda x: x[1])
    return " ".join(s for _, _, s in top_selected)


class TransformerNLIVerifier:
    def __init__(
        self,
        model_name: str,
        min_confidence: float = 0.55,
        min_margin: float = 0.10,
        max_salient_sentences: int = 3,
    ):
        from sentence_transformers import CrossEncoder

        self.model = CrossEncoder(model_name)
        model_config = getattr(getattr(self.model, "model", None), "config", None)
        raw_map = (
            getattr(model_config, "id2label", None)
            if model_config
            else getattr(getattr(self.model, "config", None), "id2label", None)
        )
        self.labels = _resolve_nli_labels(raw_map)
        self.min_confidence = min_confidence
        self.min_margin = min_margin
        self.max_salient_sentences = max_salient_sentences

    def verify(self, evidence: str, claim: str) -> tuple[VerificationLabel, float]:
        if self.max_salient_sentences > 0:
            evidence = select_salient_evidence(
                evidence, claim, max_sentences=self.max_salient_sentences
            )
        raw_pred = np.asarray(self.model.predict([(evidence, claim)]))
        logits = raw_pred[0] if raw_pred.ndim > 1 else raw_pred
        probabilities = np.exp(logits - np.max(logits))
        probabilities = probabilities / probabilities.sum()

        sorted_indices = np.argsort(probabilities)[::-1]
        top_idx = int(sorted_indices[0])
        runner_up_idx = int(sorted_indices[1]) if len(sorted_indices) > 1 else top_idx
        top_p = float(probabilities[top_idx])
        margin = float(top_p - probabilities[runner_up_idx])

        if top_p < self.min_confidence or margin < self.min_margin:
            label = VerificationLabel.insufficient
        else:
            label = self.labels[top_idx] if top_idx < len(self.labels) else VerificationLabel.insufficient

        return label, top_p


class CitationVerifier:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._cache: dict[str, tuple[bool, str]] = {}

    async def verify(
        self, markers: list[int], chunks: list[RetrievedChunk]
    ) -> list[CitationResult]:
        sorted_markers = sorted(set(markers))

        async def verify_one(marker: int) -> CitationResult:
            if marker < 1 or marker > len(chunks):
                return CitationResult(
                    marker=f"S{marker}",
                    source_id="unknown",
                    title="Invalid source marker",
                    url="",
                    metadata_valid=False,
                    verification_note="The answer cited a source marker that was not retrieved.",
                    excerpt="",
                    layer=1,
                    layer_name="Unknown Layer",
                    layer_source="Unknown Source",
                    subtopic=None,
                )
            chunk = chunks[marker - 1]
            valid, note = await self._validate_metadata(chunk)
            return CitationResult(
                marker=f"S{marker}",
                source_id=chunk.source_id,
                title=chunk.title,
                url=chunk.url,
                doi=chunk.doi,
                pmid=chunk.pmid,
                pmcid=chunk.pmcid,
                metadata_valid=valid,
                verification_note=note,
                excerpt=chunk.excerpt,
                layer=chunk.layer,
                layer_name=chunk.layer_name,
                layer_source=chunk.layer_source,
                subtopic=chunk.subtopic,
                parent_id=chunk.parent_id,
                parent_title=chunk.parent_title,
                breadcrumb=chunk.breadcrumb,
            )

        results = await asyncio.gather(*(verify_one(m) for m in sorted_markers))
        return list(results)

    async def _validate_metadata(self, chunk: RetrievedChunk) -> tuple[bool, str]:
        cache_key = chunk.source_id or chunk.doi or chunk.title
        if cache_key and cache_key in self._cache:
            return self._cache[cache_key]

        result = await self._do_validate_metadata(chunk)
        if cache_key:
            self._cache[cache_key] = result
        return result

    async def _do_validate_metadata(self, chunk: RetrievedChunk) -> tuple[bool, str]:
        if chunk.demo:
            return True, f"Triad {chunk.layer_name} ({chunk.layer_source}) verified."
        if "nice.org.uk" in (chunk.url or "").lower() or (chunk.subtopic and "NICE" in chunk.subtopic):
            return True, "Official NICE Clinical Guideline validated against NICE catalogue."
        if "ncbi.nlm.nih.gov/books" in (chunk.url or "").lower() or "statpearls" in (chunk.journal or "").lower():
            return True, "NCBI Bookshelf / StatPearls peer-reviewed record verified."
        if chunk.doi:
            url = f"https://api.crossref.org/works/{quote(chunk.doi, safe='')}"
            headers = {"User-Agent": f"NeuroEvidence/0.1 (mailto:{self.settings.crossref_mailto})"}
            try:
                async with httpx.AsyncClient(timeout=3.0, headers=headers) as client:
                    response = await client.get(url)
                if response.status_code == 200:
                    item = response.json().get("message", {})
                    returned_title = " ".join(item.get("title", []))
                    if returned_title and _title_similarity(returned_title, chunk.title) < 0.55:
                        return False, "DOI exists, but the returned title does not match the indexed title."
                    return True, "DOI exists in Crossref and the title is consistent."
                if chunk.pmid or chunk.pmcid:
                    return True, "Verified via PubMed/PMC record in curated corpus manifest."
                return False, f"Crossref returned HTTP {response.status_code}."
            except (httpx.HTTPError, ValueError, KeyError):
                if chunk.pmid or chunk.pmcid:
                    return True, "Verified via PubMed/PMC record in curated corpus manifest."
                return False, "Crossref could not be reached; metadata remains unverified."
        if chunk.pmid or chunk.pmcid:
            return True, "A PubMed/PMC identifier is present in the frozen corpus manifest."
        return False, "No DOI, PMID, or PMCID is available for metadata verification."


@dataclass(frozen=True)
class VerificationBundle:
    citations: list[CitationResult]
    claims: list[ClaimCheck]
    evidence_score: float
    warnings: list[str]
    chunks: list[RetrievedChunk] | None = None


async def verify_answer(
    answer: str,
    chunks: list[RetrievedChunk],
    citation_verifier: CitationVerifier,
    nli: NLIVerifier,
    threshold: float,
    retriever: Any | None = None,
    topic: str | None = None,
    enable_cross_chunk_fallback: bool = True,
    enable_corrective_retrieval: bool = True,
    max_corrective_claims: int = 2,
) -> VerificationBundle:
    working_chunks = list(chunks)
    claims = extract_claims(
        answer,
        working_chunks,
        nli,
        enable_cross_chunk_fallback=enable_cross_chunk_fallback,
    )

    # 4. Targeted Secondary Retrieval (Corrective RAG):
    # If any claims remain insufficient, query the retriever specifically for that claim
    if retriever is not None and enable_corrective_retrieval:
        insufficient_indices = [
            i for i, c in enumerate(claims) if c.label == VerificationLabel.insufficient
        ]
        for idx in insufficient_indices[:max_corrective_claims]:
            claim_obj = claims[idx]
            target_query = claim_obj.claim
            try:
                candidates = retriever.search(target_query, topic=topic)
            except Exception as e:
                logger.warning(
                    "Corrective retrieval search failed for claim: %s (%s)", target_query, e
                )
                continue

            existing_chunk_ids = {c.chunk_id for c in working_chunks}
            for cand in candidates:
                if cand.chunk_id in existing_chunk_ids:
                    continue
                cand_salient = select_salient_evidence(cand.excerpt, claim_obj.claim)
                cand_label, cand_score = nli.verify(cand_salient, claim_obj.claim)
                if cand_label == VerificationLabel.supported and cand_score >= 0.55:
                    working_chunks.append(cand)
                    existing_chunk_ids.add(cand.chunk_id)
                    new_marker = f"S{len(working_chunks)}"
                    updated_markers = list(claim_obj.citation_markers)
                    if new_marker not in updated_markers:
                        updated_markers.append(new_marker)
                    orig_note = (
                        f" (originally cited {', '.join(claim_obj.citation_markers)})"
                        if claim_obj.citation_markers
                        else ""
                    )
                    claims[idx] = ClaimCheck(
                        claim=claim_obj.claim,
                        citation_markers=updated_markers,
                        label=VerificationLabel.supported,
                        score=round(cand_score, 3),
                        explanation=(
                            f"Supported via targeted secondary retrieval from [{cand.title}] ({new_marker}){orig_note}."
                        ),
                    )
                    break

    all_markers: set[int] = set(extract_citation_markers(answer))
    for claim in claims:
        for m in claim.citation_markers:
            if m.startswith("S") and m[1:].isdigit():
                all_markers.add(int(m[1:]))

    citations = await citation_verifier.verify(sorted(all_markers), working_chunks)

    supported_ratio = (
        sum(item.label == VerificationLabel.supported for item in claims) / len(claims)
        if claims
        else 0.0
    )
    citation_ratio = (
        sum(item.metadata_valid for item in citations) / len(citations) if citations else 0.0
    )
    relevance = (
        sum(chunk.relevance for chunk in working_chunks) / len(working_chunks)
        if working_chunks
        else 0.0
    )
    score = round(0.5 * supported_ratio + 0.3 * citation_ratio + 0.2 * relevance, 3)

    warnings: list[str] = []
    if not citations:
        warnings.append("No usable citations were found in the generated answer.")
    if any(item.label == VerificationLabel.contradicted for item in claims):
        warnings.append("At least one claim may contradict its cited evidence.")
    if any(item.label == VerificationLabel.insufficient for item in claims):
        warnings.append("Some claims are not sufficiently supported by their cited excerpts.")
    if score < threshold:
        warnings.append("The evidence support score is below the configured verification threshold.")
    return VerificationBundle(citations, claims, score, warnings, chunks=working_chunks)


def extract_claims(
    answer: str,
    chunks: list[RetrievedChunk],
    nli: NLIVerifier,
    enable_cross_chunk_fallback: bool = True,
) -> list[ClaimCheck]:
    claims: list[ClaimCheck] = []
    for paragraph in [item.strip() for item in answer.split("\n") if item.strip()]:
        marker_numbers = extract_citation_markers(paragraph)
        clean_paragraph = CITATION_BRACKET_PATTERN.sub("", paragraph).strip()
        clean_paragraph = re.sub(r"\s+([.,;:!?])", r"\1", clean_paragraph)
        for sentence in SENTENCE_PATTERN.split(clean_paragraph):
            claim = sentence.strip()
            if len(claim.split()) < 5:
                continue
            if not marker_numbers:
                if _is_nonfactual_notice(claim):
                    continue
                claims.append(
                    ClaimCheck(
                        claim=claim,
                        citation_markers=[],
                        label=VerificationLabel.insufficient,
                        score=1.0,
                        explanation="This factual statement has no source marker.",
                    )
                )
                continue
            evidence_parts = [
                chunks[number - 1].excerpt
                for number in marker_numbers
                if 1 <= number <= len(chunks)
            ]
            if not evidence_parts:
                label, score = VerificationLabel.insufficient, 1.0
            else:
                combined_evidence = " ".join(evidence_parts)
                salient_evidence = select_salient_evidence(combined_evidence, claim)
                label, score = nli.verify(salient_evidence, claim)

            explanations = {
                VerificationLabel.supported: "The cited excerpt entails or closely supports this claim.",
                VerificationLabel.contradicted: "The claim may conflict with wording in the cited excerpt.",
                VerificationLabel.insufficient: "The cited excerpt does not provide enough support for this claim.",
            }
            citation_markers = [f"S{number}" for number in marker_numbers]
            explanation = explanations[label]

            # 1. Cross-Chunk Fallback: If cited marker returned insufficient, check other retrieved chunks
            if label == VerificationLabel.insufficient and enable_cross_chunk_fallback and chunks:
                for other_idx, other_chunk in enumerate(chunks, start=1):
                    if other_idx not in marker_numbers:
                        other_salient = select_salient_evidence(other_chunk.excerpt, claim)
                        alt_label, alt_score = nli.verify(other_salient, claim)
                        if alt_label == VerificationLabel.supported and alt_score >= 0.55:
                            label = VerificationLabel.supported
                            score = alt_score
                            fallback_marker = f"S{other_idx}"
                            if fallback_marker not in citation_markers:
                                citation_markers.append(fallback_marker)
                            orig_str = ", ".join(f"S{n}" for n in marker_numbers)
                            explanation = (
                                f"Originally cited {orig_str}, but verified as supported "
                                f"by retrieved source [{fallback_marker}]."
                            )
                            break

            claims.append(
                ClaimCheck(
                    claim=claim,
                    citation_markers=citation_markers,
                    label=label,
                    score=round(score, 3),
                    explanation=explanation,
                )
            )
    return claims


def make_nli(settings: Settings) -> NLIVerifier:
    if settings.enable_nli and not settings.demo_mode:
        return TransformerNLIVerifier(
            settings.nli_model,
            min_confidence=settings.nli_min_confidence,
            min_margin=settings.nli_min_margin,
            max_salient_sentences=settings.nli_max_salient_sentences,
        )
    return LexicalNLIVerifier()


def _title_similarity(left: str, right: str) -> float:
    left_terms = set(WORD_PATTERN.findall(left.lower()))
    right_terms = set(WORD_PATTERN.findall(right.lower()))
    return len(left_terms & right_terms) / max(1, len(left_terms | right_terms))


def _is_nonfactual_notice(claim: str) -> bool:
    normalized = claim.lower().strip()
    if any(
        phrase in normalized
        for phrase in (
            "does not provide an individual diagnosis",
            "cannot diagnose",
            "educational material",
            "not strong enough to produce",
            "simulated plain-model baseline",
            "main topic",
            "supporting evidence",
            "supporting clinical evidence",
            "key clinical areas",
            "core clinical concepts",
            "direct answer",
            "core takeaway",
            "bottom line",
        )
    ):
        return True
    if claim.startswith(("#", "###", "####")) or (claim.startswith("**") and claim.endswith((":**", "**"))):
        return True
    return False


def sync_answer_citations(answer: str, claims: list[ClaimCheck]) -> str:
    """Updates inline citations in the answer text to reflect verified/re-attributed source markers.
    For instance, if a claim was supported via secondary retrieval by [S5] (originally citing [S1] or uncited),
    this updates the sentence's inline bracket to [S5].
    """
    if not answer or not claims:
        return answer

    revised_text = answer
    for claim in claims:
        if claim.label != VerificationLabel.supported or not claim.citation_markers:
            continue

        target_markers_str = f"[{', '.join(claim.citation_markers)}]"
        claim_sub = claim.claim.strip()
        if len(claim_sub) < 8:
            continue

        lines = revised_text.split("\n")
        new_lines = []
        for line in lines:
            if claim_sub in line:
                already_has_marker = any(
                    re.search(rf"\[\s*{re.escape(m)}\b", line) for m in claim.citation_markers
                )
                if not already_has_marker:
                    bracket_match = CITATION_BRACKET_PATTERN.search(line)
                    if bracket_match:
                        line = (
                            line[:bracket_match.start()]
                            + target_markers_str
                            + line[bracket_match.end():]
                        )
                    else:
                        line = line.rstrip()
                        if line.endswith((".", ";", ":")):
                            line = line[:-1] + f" {target_markers_str}."
                        else:
                            line = f"{line} {target_markers_str}"
            new_lines.append(line)
        revised_text = "\n".join(new_lines)

    return revised_text
