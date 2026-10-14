import pytest

from app.demo_corpus import DEMO_CHUNKS
from app.models import VerificationLabel
from app.verification import (
    CitationVerifier,
    LexicalNLIVerifier,
    _resolve_nli_labels,
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


def test_resolve_nli_labels() -> None:
    # Standard MNLI order
    mnli_mapping = {0: "entailment", 1: "neutral", 2: "contradiction"}
    assert _resolve_nli_labels(mnli_mapping) == [
        VerificationLabel.supported,
        VerificationLabel.insufficient,
        VerificationLabel.contradicted,
    ]

    # DeBERTa order
    deberta_mapping = {0: "contradiction", 1: "entailment", 2: "neutral"}
    assert _resolve_nli_labels(deberta_mapping) == [
        VerificationLabel.contradicted,
        VerificationLabel.supported,
        VerificationLabel.insufficient,
    ]

    # Empty fallback
    assert _resolve_nli_labels(None) == [
        VerificationLabel.contradicted,
        VerificationLabel.supported,
        VerificationLabel.insufficient,
    ]


def test_transformer_nli_calibration_thresholds() -> None:
    from unittest.mock import MagicMock, patch
    import numpy as np
    from app.verification import TransformerNLIVerifier

    with patch("sentence_transformers.CrossEncoder") as mock_encoder_cls:
        mock_instance = MagicMock()
        mock_instance.model.config.id2label = {
            0: "entailment",
            1: "contradiction",
            2: "neutral",
        }
        mock_encoder_cls.return_value = mock_instance
        verifier = TransformerNLIVerifier(
            "dummy-model", min_confidence=0.55, min_margin=0.10
        )

        # Case 1: High confidence, wide margin -> Supported
        mock_instance.predict.return_value = np.array([[3.0, 0.5, 0.0]])
        label, score = verifier.verify("evidence", "claim")
        assert label == VerificationLabel.supported
        assert score > 0.80

        # Case 2: Ambiguous / narrow margin (< 0.10) -> Insufficient
        mock_instance.predict.return_value = np.array([[1.0, 0.9, 0.0]])
        label, score = verifier.verify("evidence", "claim")
        assert label == VerificationLabel.insufficient

        # Case 3: Flat distribution / low confidence (< 0.55) -> Insufficient
        mock_instance.predict.return_value = np.array([[0.5, 0.4, 0.3]])
        label, score = verifier.verify("evidence", "claim")
        assert label == VerificationLabel.insufficient


def test_select_salient_evidence() -> None:
    from app.verification import select_salient_evidence

    # Case 1: Short text (<= 3 sentences) returns verbatim
    short_text = "Levodopa is the primary agent. It is administered with carbidopa."
    assert select_salient_evidence(short_text, "Levodopa dosage", max_sentences=3) == short_text

    # Case 2: Multi-sentence passage with distractor sentences
    long_passage = (
        "Parkinson disease was described in 1817. "  # Distractor 0
        "The incidence increases with age worldwide. "  # Distractor 1
        "Carbidopa prevents peripheral metabolism of levodopa. "  # Match 2
        "Dopamine agonists represent an alternative class. "  # Distractor 3
        "Co-administration of carbidopa significantly elevates central bioavailability."  # Match 4
    )
    claim = "Carbidopa blocks peripheral conversion of levodopa and raises bioavailability."

    salient = select_salient_evidence(long_passage, claim, max_sentences=2)
    # Must pick sentences 2 and 4 in original chronological order
    assert "Carbidopa prevents peripheral metabolism" in salient
    assert "Co-administration of carbidopa significantly elevates" in salient
    assert "described in 1817" not in salient
    assert "increases with age" not in salient


def test_cross_chunk_fallback_recovers_misattributed_citation() -> None:
    # Chunk 1 is Parkinson's overview (DEMO_CHUNKS[0])
    # Chunk 2 is Epilepsy diagnosis (DEMO_CHUNKS[3])
    chunks = [DEMO_CHUNKS[0], DEMO_CHUNKS[3]]
    # LLM incorrectly cites [S1] (Parkinson) for an epilepsy claim
    answer = "A single provoked seizure does not automatically establish epilepsy. [S1]"
    claims = extract_claims(answer, chunks, LexicalNLIVerifier(), enable_cross_chunk_fallback=True)

    assert len(claims) == 1
    # Successfully recovered via cross-chunk fallback to chunk 2 (S2)
    assert claims[0].label == VerificationLabel.supported
    assert "S2" in claims[0].citation_markers
    assert "retrieved source [S2]" in claims[0].explanation


@pytest.mark.asyncio
async def test_corrective_secondary_retrieval(settings) -> None:
    from unittest.mock import MagicMock

    # Initially only chunk 1 (Parkinson) was retrieved
    chunks = [DEMO_CHUNKS[0]]
    # The answer makes a claim about epilepsy diagnosis, citing [S1]
    answer = "A single provoked seizure does not automatically establish epilepsy. [S1]"

    # Mock retriever returns the relevant epilepsy chunk from the knowledge base
    mock_retriever = MagicMock()
    mock_retriever.search.return_value = [DEMO_CHUNKS[3]]

    result = await verify_answer(
        answer,
        chunks,
        CitationVerifier(settings),
        LexicalNLIVerifier(),
        settings.evidence_threshold,
        retriever=mock_retriever,
        topic="epilepsy",
        enable_cross_chunk_fallback=True,
        enable_corrective_retrieval=True,
    )

    # Retriever should have been called for targeted search
    mock_retriever.search.assert_called_once()
    # The claim is now supported via secondary retrieval
    assert result.claims[0].label == VerificationLabel.supported
    assert "S2" in result.claims[0].citation_markers
    assert "targeted secondary retrieval" in result.claims[0].explanation
    # Working chunks in the bundle now include S2
    assert len(result.chunks) == 2
    assert any(c.marker == "S2" for c in result.citations)


def test_extract_citation_markers_variants() -> None:
    from app.verification import extract_citation_markers

    assert extract_citation_markers("Single marker [S1]") == [1]
    assert extract_citation_markers("Multi comma [S1, S2, S3]") == [1, 2, 3]
    assert extract_citation_markers("Multi semicolon [S1; S3; S6]") == [1, 3, 6]
    assert extract_citation_markers("Range marker [S1-S3]") == [1, 2, 3]
    assert extract_citation_markers("Mixed in text [S2, S3] and another [S5].") == [2, 3, 5]


def test_claim_extraction_multi_citation() -> None:
    from app.verification import extract_claims

    # DEMO_CHUNKS[0] is Parkinson, DEMO_CHUNKS[4] is Stroke
    chunks = [DEMO_CHUNKS[0], DEMO_CHUNKS[4]]
    answer = (
        "Parkinson disease causes tremor at rest, muscular rigidity, and slowness of movement. [S1, S2]"
    )
    claims = extract_claims(answer, chunks, LexicalNLIVerifier())
    assert len(claims) == 1
    assert claims[0].citation_markers == ["S1", "S2"]
    assert claims[0].label == VerificationLabel.supported


def test_sync_answer_citations():
    from app.models import ClaimCheck, VerificationLabel
    from app.verification import sync_answer_citations

    draft = (
        "### Main Topic: Epilepsy\n"
        "A single provoked seizure does not automatically establish epilepsy. [S1]\n"
        "Focal seizures may evolve to bilateral tonic-clonic activity."
    )
    claims = [
        ClaimCheck(
            claim="A single provoked seizure does not automatically establish epilepsy",
            citation_markers=["S2"],
            label=VerificationLabel.supported,
            score=0.9,
            explanation="Supported via secondary retrieval from [NICE] (S2) (originally cited S1)",
        ),
        ClaimCheck(
            claim="Focal seizures may evolve to bilateral tonic-clonic activity",
            citation_markers=["S3"],
            label=VerificationLabel.supported,
            score=0.88,
            explanation="Supported by retrieved source [S3]",
        ),
    ]

    synced = sync_answer_citations(draft, claims)
    # The first claim should have updated marker [S2] instead of [S1]
    assert "[S2]" in synced
    assert "[S1]" not in synced
    # The previously uncited claim should now have marker [S3]
    assert "[S3]" in synced





