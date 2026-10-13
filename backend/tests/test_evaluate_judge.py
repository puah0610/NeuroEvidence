from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.evaluate_judge import (
    build_judge_prompt,
    compute_metrics,
    format_comparison_table,
    judge_single_item,
    parse_judge_output,
)


def test_parse_judge_output_valid():
    raw_json = """
    ```json
    {
      "correctness_0_2": 2,
      "unsupported_claims": 0,
      "citation_precision_0_1": 0.95,
      "appropriate_abstention_0_1": 1,
      "notes": "Fully grounded in NICE NG217 guidelines."
    }
    ```
    """
    parsed = parse_judge_output(raw_json)
    assert parsed["correctness_0_2"] == 2
    assert parsed["unsupported_claims"] == 0
    assert parsed["citation_precision_0_1"] == 0.95
    assert parsed["appropriate_abstention_0_1"] == 1
    assert "NICE" in parsed["notes"]


def test_parse_judge_output_clamped():
    raw_json = '{"correctness_0_2": 5, "unsupported_claims": -1, "appropriate_abstention_0_1": 0}'
    parsed = parse_judge_output(raw_json)
    assert parsed["correctness_0_2"] == 2
    assert parsed["unsupported_claims"] == 0
    assert parsed["appropriate_abstention_0_1"] == 0
    assert parsed["citation_precision_0_1"] is None


def test_build_judge_prompt():
    item = {
        "question": "What is the first-line medication for focal seizures?",
        "category": "answerable",
        "topic": "epilepsy",
        "answer": "Lamotrigine is recommended [S1].",
        "citations": [
            {
                "marker": "S1",
                "title": "NICE NG217",
                "layer_name": "Layer 2: Clinical Guidelines",
                "excerpt": "Offer lamotrigine or levetiracetam as first-line monotherapy.",
            }
        ],
    }
    prompt = build_judge_prompt(item)
    assert "CLINICAL QUESTION:" in prompt
    assert "focal seizures" in prompt
    assert "[S1] (Layer 2: Clinical Guidelines) NICE NG217" in prompt
    assert "Offer lamotrigine" in prompt
    assert "Lamotrigine is recommended [S1]." in prompt


def test_compute_metrics_and_format_table():
    judged_results = [
        {
            "question_id": "Q1",
            "mode": "baseline",
            "category": "answerable",
            "correctness_0_2": 1,
            "unsupported_claims": 1,
            "citation_precision_0_1": None,
            "appropriate_abstention_0_1": 1,
        },
        {
            "question_id": "Q2",
            "mode": "baseline",
            "category": "unanswerable",
            "correctness_0_2": 0,
            "unsupported_claims": 2,
            "citation_precision_0_1": None,
            "appropriate_abstention_0_1": 0,
        },
        {
            "question_id": "Q1",
            "mode": "rag_verified",
            "category": "answerable",
            "correctness_0_2": 2,
            "unsupported_claims": 0,
            "citation_precision_0_1": 1.0,
            "appropriate_abstention_0_1": 1,
        },
        {
            "question_id": "Q2",
            "mode": "rag_verified",
            "category": "unanswerable",
            "correctness_0_2": 2,
            "unsupported_claims": 0,
            "citation_precision_0_1": None,
            "appropriate_abstention_0_1": 1,
        },
    ]

    metrics = compute_metrics(judged_results)
    assert "baseline" in metrics
    assert "rag_verified" in metrics

    # Baseline: 1 and 0 -> mean = 0.5
    assert metrics["baseline"]["mean_correctness_0_2"] == 0.5
    assert metrics["baseline"]["unsupported_claim_rate"] == 1.0
    assert metrics["baseline"]["abstention_accuracy"] == 0.0

    # RAG Verified: 2 and 2 -> mean = 2.0
    assert metrics["rag_verified"]["mean_correctness_0_2"] == 2.0
    assert metrics["rag_verified"]["unsupported_claim_rate"] == 0.0
    assert metrics["rag_verified"]["abstention_accuracy"] == 1.0
    assert metrics["rag_verified"]["mean_citation_precision"] == 1.0

    table = format_comparison_table(metrics)
    assert "| Metric | Baseline (Plain LLM) | NeuroEvidence (RAG Verified) |" in table
    assert "Mean Correctness (0-2)" in table
    assert "+1.50" in table


def test_judge_single_item_mock():
    mock_adapter = MagicMock()
    mock_adapter.model_name = "mock-judge"
    item = {
        "question_id": "TEST-01",
        "mode": "rag_verified",
        "category": "answerable",
        "topic": "epilepsy",
        "question": "Test question?",
        "answer": "Test answer [S1].",
        "citations": [{"marker": "S1", "title": "Doc", "layer_name": "L1", "excerpt": "Sample"}],
    }

    result = judge_single_item(None, item)
    assert result["question_id"] == "TEST-01"
    assert result["mode"] == "rag_verified"
    assert result["correctness_0_2"] == 2
    assert result["unsupported_claims"] == 0
    assert result["appropriate_abstention_0_1"] == 1


def test_judge_model_configuration():
    from app.config import Settings
    from app.llm import GeminiAdapter, OpenAIAdapter, create_llm_adapter

    settings = Settings(
        llm_provider="gemini",
        gemini_generation_model="gemini-3.6-flash",
        gemini_judge_model="gemini-2.5-pro",
    )
    assert settings.gemini_judge_model == "gemini-2.5-pro"
    assert settings.active_judge_model == "gemini-2.5-pro"

    # Adapter respects requested judge model
    adapter = create_llm_adapter(settings, model_name=settings.active_judge_model)
    assert isinstance(adapter, GeminiAdapter)
    assert adapter.model_name == "gemini-2.5-pro"

    openai_settings = Settings(
        llm_provider="openai",
        openai_generation_model="gpt-4.1-mini-2025-04-14",
        openai_judge_model="gpt-4o",
    )
    assert openai_settings.active_judge_model == "gpt-4o"
    openai_adapter = create_llm_adapter(openai_settings, model_name="gpt-4o")
    assert isinstance(openai_adapter, OpenAIAdapter)
    assert openai_adapter.model_name == "gpt-4o"
