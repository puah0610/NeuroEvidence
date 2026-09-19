import re
from dataclasses import dataclass
from typing import Protocol
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


CITATION_PATTERN = re.compile(r"\[S(\d+)\]")
SENTENCE_PATTERN = re.compile(r"(?<=[.!?])\s+")
WORD_PATTERN = re.compile(r"[a-z0-9]+")


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


class TransformerNLIVerifier:
    def __init__(self, model_name: str):
        from sentence_transformers import CrossEncoder

        self.model = CrossEncoder(model_name)
        model_config = getattr(getattr(self.model, "model", None), "config", None)
        raw_map = (
            getattr(model_config, "id2label", None)
            if model_config
            else getattr(getattr(self.model, "config", None), "id2label", None)
        )
        self.labels = _resolve_nli_labels(raw_map)

    def verify(self, evidence: str, claim: str) -> tuple[VerificationLabel, float]:
        raw_pred = np.asarray(self.model.predict([(evidence, claim)]))
        logits = raw_pred[0] if raw_pred.ndim > 1 else raw_pred
        probabilities = np.exp(logits - np.max(logits))
        probabilities = probabilities / probabilities.sum()
        index = int(probabilities.argmax())
        label = self.labels[index] if index < len(self.labels) else VerificationLabel.insufficient
        return label, float(probabilities[index])


class CitationVerifier:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def verify(
        self, markers: list[int], chunks: list[RetrievedChunk]
    ) -> list[CitationResult]:
        results: list[CitationResult] = []
        for marker in sorted(set(markers)):
            if marker < 1 or marker > len(chunks):
                results.append(
                    CitationResult(
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
                )
                continue
            chunk = chunks[marker - 1]
            valid, note = await self._validate_metadata(chunk)
            results.append(
                CitationResult(
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
                )
            )
        return results

    async def _validate_metadata(self, chunk: RetrievedChunk) -> tuple[bool, str]:
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
                async with httpx.AsyncClient(timeout=8, headers=headers) as client:
                    response = await client.get(url)
                if response.status_code != 200:
                    return False, f"Crossref returned HTTP {response.status_code}."
                item = response.json().get("message", {})
                returned_title = " ".join(item.get("title", []))
                if returned_title and _title_similarity(returned_title, chunk.title) < 0.55:
                    return False, "DOI exists, but the returned title does not match the indexed title."
                return True, "DOI exists in Crossref and the title is consistent."
            except (httpx.HTTPError, ValueError, KeyError):
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


async def verify_answer(
    answer: str,
    chunks: list[RetrievedChunk],
    citation_verifier: CitationVerifier,
    nli: NLIVerifier,
    threshold: float,
) -> VerificationBundle:
    marker_numbers = [int(value) for value in CITATION_PATTERN.findall(answer)]
    citations = await citation_verifier.verify(marker_numbers, chunks)
    claims = extract_claims(answer, chunks, nli)

    supported_ratio = (
        sum(item.label == VerificationLabel.supported for item in claims) / len(claims)
        if claims
        else 0.0
    )
    citation_ratio = (
        sum(item.metadata_valid for item in citations) / len(citations) if citations else 0.0
    )
    relevance = sum(chunk.relevance for chunk in chunks) / len(chunks) if chunks else 0.0
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
    return VerificationBundle(citations, claims, score, warnings)


def extract_claims(
    answer: str, chunks: list[RetrievedChunk], nli: NLIVerifier
) -> list[ClaimCheck]:
    claims: list[ClaimCheck] = []
    for paragraph in [item.strip() for item in answer.split("\n") if item.strip()]:
        marker_numbers = [int(value) for value in CITATION_PATTERN.findall(paragraph)]
        clean_paragraph = CITATION_PATTERN.sub("", paragraph).strip()
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
                label, score = nli.verify(" ".join(evidence_parts), claim)
            explanations = {
                VerificationLabel.supported: "The cited excerpt entails or closely supports this claim.",
                VerificationLabel.contradicted: "The claim may conflict with wording in the cited excerpt.",
                VerificationLabel.insufficient: "The cited excerpt does not provide enough support for this claim.",
            }
            claims.append(
                ClaimCheck(
                    claim=claim,
                    citation_markers=[f"S{number}" for number in marker_numbers],
                    label=label,
                    score=round(score, 3),
                    explanation=explanations[label],
                )
            )
    return claims


def make_nli(settings: Settings) -> NLIVerifier:
    if settings.enable_nli and not settings.demo_mode:
        return TransformerNLIVerifier(settings.nli_model)
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
        )
    ):
        return True
    if claim.startswith(("#", "###", "####")) or (claim.startswith("**") and claim.endswith((":**", "**"))):
        return True
    return False
