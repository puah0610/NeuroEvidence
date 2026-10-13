import pytest
from app.config import Settings
from app.demo_corpus import DEMO_CHUNKS
from app.retrieval import DemoRetriever, NeuralReranker


def test_cross_encoder_preposition_sensitivity():
    """Verify that the Cross-Encoder model distinguishes prepositional nuances."""
    reranker = NeuralReranker("cross-encoder/ms-marco-MiniLM-L-6-v2")

    q_in = "Weakness in the left arm"
    q_from = "Weakness from the left arm"

    # Synthetic candidate chunks testing anatomical localization vs radiation
    passage_focal = (
        "Acute ischemic stroke localized to the right motor cortex presenting with "
        "contralateral hemiparesis and focal motor weakness in the left arm and face."
    )
    passage_radicular = (
        "Cervical radiculopathy secondary to C6 nerve root compression causing shooting pain "
        "and motor weakness radiating from the left arm and neck."
    )

    pairs = [
        (q_in, passage_focal),
        (q_in, passage_radicular),
        (q_from, passage_focal),
        (q_from, passage_radicular),
    ]

    model = reranker.get_model("cross-encoder/ms-marco-MiniLM-L-6-v2")
    scores = model.predict(pairs)

    score_in_to_focal = scores[0]
    score_in_to_radicular = scores[1]
    score_from_to_focal = scores[2]
    score_from_to_radicular = scores[3]

    # "Weakness in the left arm" should score higher on focal arm weakness
    assert score_in_to_focal > score_in_to_radicular, (
        f"'Weakness in' should favor focal localization: {score_in_to_focal} vs {score_in_to_radicular}"
    )

    # "Weakness from the left arm" should score higher on radiating weakness
    assert score_from_to_radicular > score_from_to_focal, (
        f"'Weakness from' should favor radiating origin: {score_from_to_radicular} vs {score_from_to_focal}"
    )


def test_two_stage_retriever_parkinsons_pharmacotherapy(settings: Settings):
    """Verify that the Two-Stage Retriever prioritizes first-line pharmacotherapy and core pharmacology."""
    retriever = DemoRetriever(settings)
    query = "What kind of medication should I use to control parkinson disease and the reason behind it"
    results = retriever.search(query, "Parkinson's disease")

    assert len(results) >= 3
    top_chunk_ids = [r.chunk_id for r in results[:3]]

    # First-line pharmacotherapy (NICE NG71) and Core Pharmacology principles must be in top 3
    assert any("TRIAD-PD-L2-02" in cid or "firstline" in cid for cid in top_chunk_ids)
    assert any("TRIAD-PD-L1-03" in cid or "pharm" in cid for cid in top_chunk_ids)

    # All returned chunks must have calibrated relevance scores
    assert all(0.0 <= r.relevance <= 1.0 for r in results)


def test_retriever_fallback_when_reranker_disabled(settings: Settings):
    """Verify that retrieval works smoothly when the neural reranker is toggled off."""
    fallback_settings = settings.model_copy(update={"enable_reranker": False})
    retriever = DemoRetriever(fallback_settings)
    assert retriever._reranker is None

    results = retriever.search("How is Parkinson's disease diagnosed?", "Parkinson's disease")
    assert len(results) > 0
    assert any("TRIAD-PD" in r.chunk_id for r in results)
