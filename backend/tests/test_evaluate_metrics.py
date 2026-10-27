import numpy as np
import pytest

from app.evaluate_metrics import (
    bootstrap_ci,
    bootstrap_paired_diff,
    compute_abstention_confusion,
    compute_abstention_rates,
    compute_retrieval_metrics,
    evaluate_dataset,
    format_dissertation_table,
)


def test_bootstrap_ci_basic():
    data = [1.0, 2.0, 3.0, 4.0, 5.0]
    point, low, high = bootstrap_ci(data, np.mean, n_resamples=1000, ci=0.95, seed=42)
    assert point == 3.0
    assert 1.5 <= low <= 3.0
    assert 3.0 <= high <= 4.5
    assert low < high


def test_bootstrap_ci_empty_and_single():
    assert bootstrap_ci([], np.mean) == (0.0, 0.0, 0.0)
    assert bootstrap_ci([2.5], np.mean) == (2.5, 2.5, 2.5)


def test_bootstrap_paired_diff():
    # Model A is consistently better than Model B
    a = [2.0, 2.0, 2.0, 2.0, 2.0]
    b = [1.0, 1.0, 1.0, 1.0, 1.0]
    diff, low, high, p_val = bootstrap_paired_diff(a, b, np.mean, n_resamples=1000, seed=42)
    assert diff == 1.0
    assert low == 1.0
    assert high == 1.0
    assert p_val == 0.0


def test_compute_abstention_confusion_and_rates():
    # 2 Answerable (1 answered, 1 erroneously refused)
    # 2 Unanswerable/Safety (1 correctly refused, 1 erroneously answered)
    rows = [
        {"category": "answerable", "appropriate_abstention_0_1": 1},  # TN
        {"category": "answerable", "appropriate_abstention_0_1": 0},  # FP
        {"category": "unanswerable", "appropriate_abstention_0_1": 1},  # TP
        {"category": "personal_medical_advice", "appropriate_abstention_0_1": 0},  # FN
    ]
    conf = compute_abstention_confusion(rows)
    assert conf == {"tp": 1, "fp": 1, "tn": 1, "fn": 1}

    rates = compute_abstention_rates(conf)
    assert rates["abstention_precision"] == 0.5  # 1 / (1 + 1)
    assert rates["abstention_recall"] == 0.5  # 1 / (1 + 1)
    assert rates["abstention_f1"] == 0.5
    assert rates["safety_routing_accuracy"] == 0.5  # (1 + 1) / 4


def test_compute_retrieval_metrics_unannotated():
    res = compute_retrieval_metrics([{"question_id": "Q1"}], {})
    assert res["status"] == "unannotated"
    assert res["recall_at_5"] is None
    assert res["mrr"] is None


def test_compute_retrieval_metrics_annotated():
    gold = {"Q1": {"DOC-01", "DOC-02"}}
    retrieved = [
        {
            "question_id": "Q1",
            "citations": [
                {"source_id": "DOC-99"},
                {"source_id": "DOC-01"},  # rank 2 -> RR = 0.5
                {"source_id": "DOC-02"},  # in top 5 -> 2/2 = 1.0 recall
            ],
        }
    ]
    res = compute_retrieval_metrics(retrieved, gold, k=5)
    assert res["status"] == "computed"
    assert res["recall_at_5"] == 1.0
    assert res["mrr"] == 0.5


def test_evaluate_dataset_end_to_end():
    judged = [
        {
            "question_id": "Q1",
            "mode": "baseline",
            "category": "answerable",
            "correctness_0_2": 1,
            "unsupported_claims": 1,
            "citation_precision_0_1": "",
            "appropriate_abstention_0_1": 1,
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
    ]
    metrics = evaluate_dataset(judged, n_resamples=500)
    assert "baseline" in metrics["modes"]
    assert "rag_verified" in metrics["modes"]
    assert metrics["paired_comparison"]["paired_questions_count"] == 1

    table = format_dissertation_table(metrics)
    assert "Evaluation Metric" in table
    assert "Mean Correctness (0-2 scale)" in table
    assert "Abstention Precision" in table
