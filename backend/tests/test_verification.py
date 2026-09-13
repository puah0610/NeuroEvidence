import pytest

from app.demo_corpus import DEMO_CHUNKS
from app.models import VerificationLabel
from app.verification import (
    CitationVerifier,
    LexicalNLIVerifier,
    extract_claims,
    verify_answer,
)


def test_claim_extraction_preserves_marker() -> None:
    answer = "An ischemic stroke interrupts blood flow to brain tissue. [S1]"
    claims = extract_claims(answer, [DEMO_CHUNKS[4]], LexicalNLIVerifier())
    assert len(claims) == 1
    assert claims[0].citation_markers == ["S1"]
    assert claims[0].label == VerificationLabel.supported


@pytest.mark.asyncio
async def test_verification_score_and_invalid_marker(settings) -> None:
    answer = "An ischemic stroke interrupts blood flow to brain tissue. [S1] Invalid marker. [S9]"
    result = await verify_answer(
        answer,
        [DEMO_CHUNKS[4]],
        CitationVerifier(settings),
        LexicalNLIVerifier(),
        settings.evidence_threshold,
    )
    assert any(not item.metadata_valid for item in result.citations)
    assert 0 <= result.evidence_score <= 1


def test_lexical_contradiction_signal() -> None:
    label, score = LexicalNLIVerifier().verify(
        "A single provoked seizure does not automatically establish epilepsy.",
        "A single provoked seizure automatically establishes epilepsy.",
    )
    assert label == VerificationLabel.contradicted
    assert score >= 0.5


def test_uncited_factual_claim_is_flagged() -> None:
    claims = extract_claims(
        "Stroke can affect language and movement.",
        [DEMO_CHUNKS[4]],
        LexicalNLIVerifier(),
    )
    assert claims[0].label == VerificationLabel.insufficient
    assert claims[0].citation_markers == []
