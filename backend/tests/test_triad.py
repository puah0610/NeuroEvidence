import pytest

from app.config import Settings
from app.demo_corpus import DEMO_CHUNKS
from app.models import ChatMode, ChatRequest
from app.retrieval import DemoRetriever
from app.service import ChatService
from app.verification import CitationVerifier


def test_triad_knowledge_base_structure():
    layers = {chunk.layer for chunk in DEMO_CHUNKS}
    assert {1, 2, 3}.issubset(layers)

    epilepsy_chunks = [c for c in DEMO_CHUNKS if c.topic == "epilepsy"]
    pd_chunks = [c for c in DEMO_CHUNKS if c.topic == "Parkinson's disease"]

    # Verify epilepsy covers all 3 layers
    assert {c.layer for c in epilepsy_chunks} == {1, 2, 3}
    # Verify Parkinson's covers all 3 layers
    assert {c.layer for c in pd_chunks} == {1, 2, 3}

    # Verify subtopics in Layer 1, 2, 3
    subtopics = {c.subtopic for c in DEMO_CHUNKS if c.subtopic}
    assert "ILAE Classification" in subtopics
    assert "NICE NG217" in subtopics
    assert "SANAD II RCT" in subtopics
    assert "Hoehn & Yahr Staging" in subtopics
    assert "NICE NG71" in subtopics
    assert "DBS Systematic Review" in subtopics


def test_hybrid_retriever_epilepsy(settings: Settings):
    retriever = DemoRetriever(settings)
    # Query addressing SANAD II trial and NICE NG217 recommendations
    results = retriever.search("What does NICE NG217 recommend and what did SANAD II find for focal seizures?", "epilepsy")
    assert len(results) > 0

    sources = [r.source_id for r in results]
    # Check that high-relevance triad chunks are retrieved
    assert any("TRIAD-EP" in s for s in sources)
    # Check that relevance score is populated between 0 and 1
    assert all(0.0 <= r.relevance <= 1.0 for r in results)


def test_hybrid_retriever_parkinsons(settings: Settings):
    retriever = DemoRetriever(settings)
    # Query addressing Hoehn & Yahr staging and NICE NG71 levodopa guidance
    results = retriever.search("How do Hoehn and Yahr staging and NICE NG71 guide levodopa therapy in Parkinson's disease?", "Parkinson's disease")
    assert len(results) > 0

    sources = [r.source_id for r in results]
    assert any("TRIAD-PD" in s for s in sources)
    # Check layer presence in retrieved chunks
    retrieved_layers = {r.layer for r in results}
    assert len(retrieved_layers) >= 1


@pytest.mark.asyncio
async def test_citation_verifier_triad_metadata(settings: Settings):
    verifier = CitationVerifier(settings)
    triad_chunks = [c for c in DEMO_CHUNKS if c.source_id.startswith("TRIAD-")]
    citations = await verifier.verify([1, 2, 3], triad_chunks)

    assert len(citations) == 3
    for citation in citations:
        assert citation.metadata_valid is True
        assert citation.layer in (1, 2, 3)
        assert citation.layer_name.startswith("Layer")
        assert citation.layer_source != ""


@pytest.mark.asyncio
async def test_chat_service_triad_layer_distribution(settings: Settings, database):
    service = ChatService(settings, database)
    request = ChatRequest(
        session_id="test-triad-session",
        question="What does NICE NG217 recommend for first-line treatment of focal seizures?",
        mode=ChatMode.rag_verified,
    )
    response = await service.chat(request)
    assert response.mode == ChatMode.rag_verified
    assert response.citations
    assert len(response.layer_distribution) > 0
    # Citations should carry layer metadata
    first_citation = response.citations[0]
    assert first_citation.layer in (1, 2, 3)
    assert first_citation.layer_name
    assert first_citation.layer_source
