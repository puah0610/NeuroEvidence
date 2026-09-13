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
        evidence_terms = set(WORD_PATTERN.findall(evidence.lower()))
        claim_terms = set(WORD_PATTERN.findall(claim.lower()))
        content_terms = {term for term in claim_terms if len(term) > 3}
        overlap = len(content_terms & evidence_terms) / max(1, len(content_terms))
        evidence_negated = bool(self.NEGATIONS & evidence_terms)
        claim_negated = bool(self.NEGATIONS & claim_terms)
        if overlap >= 0.45 and evidence_negated != claim_negated:
            return VerificationLabel.contradicted, min(0.95, 0.55 + overlap * 0.4)
        if overlap >= 0.42:
            return VerificationLabel.supported, min(0.95, 0.5 + overlap * 0.45)
        return VerificationLabel.insufficient, max(0.5, 1.0 - overlap)


class TransformerNLIVerifier:
    def __init__(self, model_name: str):
        from sentence_transformers import CrossEncoder

        self.model = CrossEncoder(model_name)

    def verify(self, evidence: str, claim: str) -> tuple[VerificationLabel, float]:
        logits = np.asarray(self.model.predict([(evidence, claim)]))[0]
        probabilities = np.exp(logits - np.max(logits))
        probabilities = probabilities / probabilities.sum()
        index = int(probabilities.argmax())
        labels = [
            VerificationLabel.contradicted,
            VerificationLabel.supported,
            VerificationLabel.insufficient,
        ]
        return labels[index], float(probabilities[index])


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
                )
            )
        return results

    async def _validate_metadata(self, chunk: RetrievedChunk) -> tuple[bool, str]:
        if chunk.demo:
            return True, "Bundled demo metadata; replace with the frozen PMC research corpus."
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
    normalized = claim.lower()
    return any(
        phrase in normalized
        for phrase in (
            "does not provide an individual diagnosis",
            "cannot diagnose",
            "educational material",
            "not strong enough to produce",
        )
    )
