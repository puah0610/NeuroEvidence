import pytest

from app.models import ChatMode, ChatRequest, Intent


@pytest.mark.asyncio
async def test_verified_chat_returns_trace_and_citations(service, database) -> None:
    response = await service.chat(
        ChatRequest(
            session_id="test-session",
            question="What are the key movement features of Parkinson's disease?",
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
            question="What is Parkinson's disease?",
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


@pytest.mark.asyncio
async def test_bounded_answer_revision_workflow(service, database) -> None:
    request = ChatRequest(
        session_id="test-revision-session",
        question="What are the diagnostic features and pharmacotherapy for focal seizures?",
        mode=ChatMode.rag_verified,
    )
    response = await service.chat(request)
    assert response.mode == ChatMode.rag_verified
    assert response.citations
    assert response.claim_checks


@pytest.mark.asyncio
async def test_ollama_baseline_operates_without_retrieval(service, database) -> None:
    response = await service.chat(
        ChatRequest(
            session_id="test-ollama-session",
            question="What is Parkinson's disease?",
            mode=ChatMode.ollama_baseline,
        )
    )
    assert response.mode == ChatMode.ollama_baseline
    assert response.citations == []
    assert response.evidence_score is None
    assert "Ollama" in response.warnings[0]
    assert response.estimated_cost_usd == 0.0
    assert "Main Topic:" in response.answer
    if response.original_answer is not None:
        assert response.answer != response.original_answer
        assert len(response.original_answer) > 0
    assert database.summary().total_traces >= 1


@pytest.mark.asyncio
async def test_ollama_rag_operates_with_retrieval_and_citations(service, database) -> None:
    response = await service.chat(
        ChatRequest(
            session_id="test-ollama-rag-session",
            question="What are the key movement features of Parkinson's disease?",
            mode=ChatMode.ollama_rag,
        )
    )
    assert response.mode == ChatMode.ollama_rag
    assert response.citations
    assert response.claim_checks
    assert response.evidence_score is not None
    assert response.estimated_cost_usd == 0.0


