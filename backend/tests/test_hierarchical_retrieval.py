import pytest

from app.config import Settings
from app.demo_corpus import DEMO_CHUNKS
from app.models import ChatMode, ChatRequest
from app.retrieval import DemoRetriever, expand_to_parent_chunks
from app.service import ChatService


def test_demo_chunks_have_breadcrumbs_and_parents():
    for chunk in DEMO_CHUNKS:
        assert chunk.breadcrumb, f"{chunk.chunk_id} missing breadcrumb"
        assert len(chunk.breadcrumb) >= 3
        assert chunk.parent_id, f"{chunk.chunk_id} missing parent_id"
        assert chunk.parent_title, f"{chunk.chunk_id} missing parent_title"


def test_expand_to_parent_chunks():
    sample_chunks = DEMO_CHUNKS[:4]
    expanded = expand_to_parent_chunks(sample_chunks, top_k=3, max_per_document=2)
    assert len(expanded) <= 3
    for chunk in expanded:
        assert "### [" in chunk.excerpt
        assert "**Document:**" in chunk.excerpt
        assert "**Section:**" in chunk.excerpt


@pytest.mark.asyncio
async def test_chat_service_ddi_and_hierarchical_breadcrumbs(settings: Settings, database):
    service = ChatService(settings, database)
    request = ChatRequest(
        session_id="test-ddi-session",
        question="Can a patient on sodium valproate be started on lamotrigine for focal seizures?",
        mode=ChatMode.rag_verified,
    )
    response = await service.chat(request)
    assert response.mode == ChatMode.rag_verified
    assert response.citations
    # Check that citations carry breadcrumb trails
    assert all(len(c.breadcrumb) > 0 for c in response.citations)
    # Check that DDI report was produced
    assert response.ddi_report is not None
    assert response.ddi_report.has_interaction is True
    assert "valproate" in response.ddi_report.drugs_detected
    assert "lamotrigine" in response.ddi_report.drugs_detected
    assert response.ddi_report.highest_severity.value == "major"
