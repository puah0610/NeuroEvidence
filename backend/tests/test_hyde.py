from unittest.mock import MagicMock, patch

from app.config import Settings
from app.llm import GenerationOutput
from app.retrieval import DemoRetriever, HyDEExpander


def test_hyde_settings_defaults():
    settings = Settings(gemini_api_key="", openai_api_key="")
    assert settings.enable_hyde is True
    assert settings.hyde_max_tokens == 150
    assert settings.hyde_llm_available is False

    # Gemini key enables hyde even in demo_mode
    gemini_settings = Settings(
        demo_mode=True,
        llm_provider="gemini",
        gemini_api_key="test-gemini-key",
    )
    assert gemini_settings.hyde_llm_available is True
    # while active_llm_enabled remains False in demo_mode
    assert gemini_settings.active_llm_enabled is False

    # OpenAI key enables hyde
    openai_settings = Settings(
        demo_mode=True,
        llm_provider="openai",
        openai_api_key="test-openai-key",
    )
    assert openai_settings.hyde_llm_available is True

    # Disabling enable_hyde disables hyde_llm_available
    disabled_settings = Settings(
        enable_hyde=False,
        gemini_api_key="test-gemini-key",
    )
    assert disabled_settings.hyde_llm_available is False


def test_hyde_expander_fallback_when_disabled():
    settings = Settings(
        enable_hyde=False,
        gemini_api_key="test-gemini-key",
    )
    expander = HyDEExpander(settings)
    question = "What is the first-line medication for focal seizures?"
    assert expander.expand(question) == question


def test_hyde_expander_fallback_when_no_api_key():
    settings = Settings(
        enable_hyde=True,
        gemini_api_key="",
        openai_api_key="",
    )
    expander = HyDEExpander(settings)
    question = "What is the mechanism of action of levetiracetam?"
    assert expander.expand(question) == question


def test_hyde_expander_success():
    settings = Settings(
        enable_hyde=True,
        llm_provider="gemini",
        gemini_api_key="test-gemini-key",
    )
    expander = HyDEExpander(settings)
    hypothetical_passage = (
        "Levodopa combined with carbidopa or benserazide represents the most effective "
        "dopaminergic replacement therapy for Parkinson's disease motor symptom management."
    )

    mock_adapter = MagicMock()
    mock_adapter.generate_baseline.return_value = GenerationOutput(text=hypothetical_passage)

    with patch.object(expander, "_get_adapter", return_value=mock_adapter):
        expanded = expander.expand("Parkinson treatment")
        assert expanded == hypothetical_passage
        mock_adapter.generate_baseline.assert_called_once()
        call_arg = mock_adapter.generate_baseline.call_args[0][0]
        assert "Parkinson treatment" in call_arg
        assert HyDEExpander._SYSTEM_PROMPT in call_arg


def test_hyde_expander_short_response_fallback():
    settings = Settings(
        enable_hyde=True,
        llm_provider="gemini",
        gemini_api_key="test-gemini-key",
    )
    expander = HyDEExpander(settings)

    mock_adapter = MagicMock()
    mock_adapter.generate_baseline.return_value = GenerationOutput(text="Too short.")

    with patch.object(expander, "_get_adapter", return_value=mock_adapter):
        question = "What are the indications for DBS?"
        expanded = expander.expand(question)
        assert expanded == question


def test_hyde_expander_error_resilience():
    settings = Settings(
        enable_hyde=True,
        llm_provider="gemini",
        gemini_api_key="test-gemini-key",
    )
    expander = HyDEExpander(settings)

    mock_adapter = MagicMock()
    mock_adapter.generate_baseline.side_effect = RuntimeError("API connection timeout")

    with patch.object(expander, "_get_adapter", return_value=mock_adapter):
        question = "Explain stroke thrombolysis window."
        expanded = expander.expand(question)
        assert expanded == question


def test_demo_retriever_uses_hyde():
    settings = Settings(
        enable_hyde=True,
        llm_provider="gemini",
        gemini_api_key="test-gemini-key",
        enable_reranker=False,
    )
    retriever = DemoRetriever(settings)
    assert retriever._hyde is not None

    mock_passage = (
        "Levodopa combined with carbidopa remains the gold standard first-line symptomatic "
        "pharmacotherapy for Parkinson's disease bradykinesia and rigidity."
    )
    with patch.object(retriever._hyde, "expand", return_value=mock_passage) as mock_expand:
        results = retriever.search("What is the first-line pharmacotherapy for Parkinson's?")
        mock_expand.assert_called_once_with("What is the first-line pharmacotherapy for Parkinson's?")
        assert len(results) > 0
        top_chunk = results[0]
        assert "Parkinson" in top_chunk.topic or "parkinson" in top_chunk.excerpt.lower()


def test_demo_retriever_hyde_disabled():
    settings = Settings(
        enable_hyde=False,
        enable_reranker=False,
    )
    retriever = DemoRetriever(settings)
    assert retriever._hyde is None
    results = retriever.search("What is the first-line pharmacotherapy for Parkinson's?")
    assert len(results) > 0
