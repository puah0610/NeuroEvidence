from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.config import Settings
from app.database import Database
from app.llm import GeminiAdapter, OpenAIAdapter, create_llm_adapter
from app.models import RetrievedChunk
from app.service import ChatService


def test_gemini_settings_defaults():
    settings = Settings(_env_file=None, demo_mode=True)
    assert settings.llm_provider == "gemini"
    assert settings.gemini_generation_model == "gemini-3.8-flash"
    assert settings.gemini_embedding_model == "gemini-embedding-001"
    assert settings.gemini_input_cost_per_million == 0.0
    assert settings.gemini_output_cost_per_million == 0.0
    assert settings.llm_temperature == 0.0
    assert not settings.gemini_enabled  # because demo_mode=True and key=""
    assert not settings.active_llm_enabled


def test_gemini_settings_enabled():
    settings = Settings(
        _env_file=None,
        demo_mode=False,
        llm_provider="gemini",
        gemini_api_key="test-key",
    )
    assert settings.gemini_enabled
    assert settings.active_llm_enabled
    assert not settings.openai_enabled
    assert settings.active_input_cost_per_million == 0.0


def test_create_llm_adapter_factory():
    gemini_settings = Settings(_env_file=None, llm_provider="gemini", gemini_api_key="test-key")
    adapter = create_llm_adapter(gemini_settings)
    assert isinstance(adapter, GeminiAdapter)
    assert adapter.model_name == "gemini-3.8-flash"

    openai_settings = Settings(_env_file=None, llm_provider="openai", openai_api_key="test-key")
    openai_adapter = create_llm_adapter(openai_settings)
    assert isinstance(openai_adapter, OpenAIAdapter)


def test_gemini_adapter_generation_mock():
    settings = Settings(llm_provider="gemini", gemini_api_key="test-key")
    adapter = GeminiAdapter(settings)

    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="### Main Topic: Parkinson's\n• Finding [S1]"))
    ]
    mock_response.usage = MagicMock(prompt_tokens=40, completion_tokens=15)

    with patch.object(adapter.client.chat.completions, "create", return_value=mock_response):
        baseline_out = adapter.generate_baseline("What is Parkinson?")
        assert baseline_out.text == "### Main Topic: Parkinson's\n• Finding [S1]"
        assert baseline_out.input_tokens == 40
        assert baseline_out.output_tokens == 15

        test_chunk = RetrievedChunk(
            chunk_id="c1",
            document_id="d1",
            source_id="s1",
            title="Parkinson Disease",
            authors=["Smith J"],
            year=2023,
            journal=None,
            topic="Parkinson's disease",
            url="https://example.com",
            doi=None,
            pmid=None,
            pmcid=None,
            license=None,
            section="Pathophysiology",
            excerpt="Dopaminergic loss in substantia nigra.",
            relevance=0.9,
            layer=1,
            layer_name="Layer 1: Foundational Knowledge",
            layer_source="StatPearls",
            subtopic="Pathophysiology",
        )
        grounded_out = adapter.generate_grounded("What causes Parkinson?", [test_chunk])
        assert grounded_out.text == "### Main Topic: Parkinson's\n• Finding [S1]"
        assert grounded_out.input_tokens == 40


def test_chat_service_validates_provider_keys(tmp_path: Path):
    db = Database(tmp_path / "test.db")

    # Gemini selected but key missing
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY is required"):
        ChatService(
            Settings(
                demo_mode=False,
                llm_provider="gemini",
                gemini_api_key="",
                database_path=tmp_path / "test.db",
                chroma_path=tmp_path / "chroma",
            ),
            db,
        )

    # OpenAI selected but key missing
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is required"):
        ChatService(
            Settings(
                demo_mode=False,
                llm_provider="openai",
                openai_api_key="",
                database_path=tmp_path / "test.db",
                chroma_path=tmp_path / "chroma",
            ),
            db,
        )


def test_clean_medical_text():
    from app.llm import clean_medical_text

    raw = r"Intracellular $\alpha$-synuclein in ($SNpc$) with $\beta$-amyloid and $TRAP$."
    cleaned = clean_medical_text(raw)
    assert "α-synuclein" in cleaned
    assert "β-amyloid" in cleaned
    assert "($SNpc$)" not in cleaned
    assert "(SNpc)" in cleaned
    assert "TRAP" in cleaned
    assert "$" not in cleaned
