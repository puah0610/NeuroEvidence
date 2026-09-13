import pytest

from app.models import ChatMode, ChatRequest, Intent


@pytest.mark.asyncio
async def test_verified_chat_returns_trace_and_citations(service, database) -> None:
    response = await service.chat(
        ChatRequest(
            session_id="test-session",
            question="How do ischemic and hemorrhagic stroke differ?",
            mode=ChatMode.rag_verified,
        )
    )
    assert response.intent == Intent.educational_in_scope
    assert response.citations
    assert response.claim_checks
    assert response.evidence_score is not None
    assert database.summary().total_traces == 1


@pytest.mark.asyncio
async def test_baseline_has_no_verification(service) -> None:
    response = await service.chat(
        ChatRequest(
            session_id="test-session",
            question="What is multiple sclerosis?",
            mode=ChatMode.baseline,
        )
    )
    assert response.citations == []
    assert response.evidence_score is None
    assert "does not retrieve" in response.warnings[0]


@pytest.mark.asyncio
async def test_emergency_is_redirected(service) -> None:
    response = await service.chat(
        ChatRequest(
            session_id="test-session",
            question="My father suddenly has facial drooping and cannot speak. Is this a stroke?",
            mode=ChatMode.rag_verified,
        )
    )
    assert response.intent == Intent.emergency
    assert "emergency" in response.answer.lower()
    assert response.citations == []

