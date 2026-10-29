"""Comprehensive Evaluation Metrics, Bootstrap 95% Confidence Intervals, and Abstention Analysis.

This module fulfills the requirements of docs/evaluation-protocol.md:
- Formal Abstention Precision, Recall, F1, and Routing Accuracy
- Paired comparisons between baseline and RAG-verified modes
- Non-parametric bootstrap 95% confidence intervals (percentile method)
- Retrieval Recall@5 and MRR (when gold_source_ids annotations exist)
- Formatted markdown tables for direct inclusion in FYP dissertation chapters.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import math
from pathlib import Path
from typing import Any, Callable

import numpy as np

logger = logging.getLogger(__name__)

NON_ANSWERABLE_CATEGORIES = frozenset({
    "unanswerable",
    "out_of_scope",
    "personal_medical_advice",
    "emergency",
})


def _resolve_project_path(p: Path | str) -> Path:
    p = Path(p)
    if not p.is_absolute():
        cwd = Path.cwd()
        if cwd.name.lower() == "backend" and (cwd.parent / "data").exists():
            return cwd.parent / p
    return p


def bootstrap_ci(
    values: list[float] | np.ndarray,
    stat_fn: Callable[[np.ndarray], float] = np.mean,
    n_resamples: int = 2000,
    ci: float = 0.95,
    seed: int = 42,
) -> tuple[float, float, float]:
    """Calculate point estimate and percentile bootstrap confidence interval."""
    arr = np.asarray(values, dtype=float)
    if len(arr) == 0:
        return 0.0, 0.0, 0.0
    point_est = float(stat_fn(arr))
    if len(arr) == 1:
        return point_est, point_est, point_est

    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(arr), size=(n_resamples, len(arr)))
    boot_stats = np.empty(n_resamples, dtype=float)
    for b in range(n_resamples):
        sample = arr[indices[b]]
        boot_stats[b] = stat_fn(sample)

    alpha = (1.0 - ci) / 2.0
    lower = float(np.percentile(boot_stats, alpha * 100))
    upper = float(np.percentile(boot_stats, (1.0 - alpha) * 100))
    return point_est, lower, upper


def bootstrap_paired_diff(
    values_a: list[float] | np.ndarray,
    values_b: list[float] | np.ndarray,
    stat_fn: Callable[[np.ndarray], float] = np.mean,
    n_resamples: int = 2000,
    ci: float = 0.95,
    seed: int = 42,
) -> tuple[float, float, float, float]:
    """Compute paired difference (A - B) point estimate, 95% bootstrap CI, and empirical two-tailed p-value."""
    arr_a = np.asarray(values_a, dtype=float)
    arr_b = np.asarray(values_b, dtype=float)
    if len(arr_a) != len(arr_b) or len(arr_a) == 0:
        return 0.0, 0.0, 0.0, 1.0

    point_diff = float(stat_fn(arr_a) - stat_fn(arr_b))
    if len(arr_a) == 1:
        return point_diff, point_diff, point_diff, (1.0 if point_diff == 0 else 0.0)

    rng = np.random.default_rng(seed)
    n = len(arr_a)
    indices = rng.integers(0, n, size=(n_resamples, n))
    boot_diffs = np.empty(n_resamples, dtype=float)

    for b in range(n_resamples):
        idx = indices[b]
        boot_diffs[b] = stat_fn(arr_a[idx]) - stat_fn(arr_b[idx])

    alpha = (1.0 - ci) / 2.0
    lower = float(np.percentile(boot_diffs, alpha * 100))
    upper = float(np.percentile(boot_diffs, (1.0 - alpha) * 100))

    # Empirical two-tailed p-value against null hypothesis of 0 difference
    p_le = np.mean(boot_diffs <= 0.0)
    p_ge = np.mean(boot_diffs >= 0.0)
    p_value = min(1.0, 2.0 * min(p_le, p_ge))

    return point_diff, lower, upper, float(p_value)


def compute_abstention_confusion(rows: list[dict[str, Any]]) -> dict[str, int]:
    """Build binary confusion matrix for abstention classification.

    - Ground truth Positive: non-answerable queries (unanswerable, out_of_scope, personal_medical_advice, emergency).
    - Ground truth Negative: answerable clinical inquiries.
    - Model Positive: appropriately refused / abstained (appropriate_abstention_0_1 == 1 for non-answerable).
    - Model Negative: appropriately answered without refusal (appropriate_abstention_0_1 == 1 for answerable).
    """
    tp = fp = tn = fn = 0
    for r in rows:
        cat = str(r.get("category", "")).lower().strip()
        is_non_answerable = cat in NON_ANSWERABLE_CATEGORIES
        abstention_val = int(r.get("appropriate_abstention_0_1", 1) or 0)

        if is_non_answerable:
            if abstention_val == 1:
                tp += 1
            else:
                fn += 1
        else:
            if abstention_val == 1:
                tn += 1
            else:
                fp += 1

    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn}


def compute_abstention_rates(confusion: dict[str, int]) -> dict[str, float | None]:
    """Compute Precision, Recall, F1, and Overall Accuracy from confusion matrix."""
    tp, fp, tn, fn = confusion["tp"], confusion["fp"], confusion["tn"], confusion["fn"]
    total = tp + fp + tn + fn

    precision = tp / (tp + fp) if (tp + fp) > 0 else (1.0 if tp == 0 and fp == 0 else 0.0)
    recall = tp / (tp + fn) if (tp + fn) > 0 else (1.0 if tp == 0 and fn == 0 else 0.0)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    accuracy = (tp + tn) / total if total > 0 else 1.0

    return {
        "abstention_precision": round(precision, 4),
        "abstention_recall": round(recall, 4),
        "abstention_f1": round(f1, 4),
        "safety_routing_accuracy": round(accuracy, 4),
    }


def compute_retrieval_metrics(
    retrieved_items: list[dict[str, Any]],
    gold_map: dict[str, set[str]],
    k: int = 5,
) -> dict[str, Any]:
    """Compute Recall@k and Mean Reciprocal Rank (MRR) if gold source labels are present."""
    if not gold_map or not any(gold_map.values()):
        return {
            "status": "unannotated",
            "message": "gold_source_ids unannotated in evaluation questions",
            "recall_at_5": None,
            "mrr": None,
            "annotated_queries_count": 0,
        }

    recalls: list[float] = []
    rr_list: list[float] = []

    for item in retrieved_items:
        qid = item.get("question_id")
        if not qid or qid not in gold_map or not gold_map[qid]:
            continue

        gold_set = gold_map[qid]
        citations = item.get("citations", [])
        retrieved_ids = [c.get("source_id") for c in citations if c.get("source_id")]

        top_k = retrieved_ids[:k]
        hits = sum(1 for src in gold_set if src in top_k)
        recall_k = hits / len(gold_set)
        recalls.append(recall_k)

        # Reciprocal Rank
        first_hit_rank = None
        for rank_idx, src in enumerate(retrieved_ids, start=1):
            if src in gold_set:
                first_hit_rank = rank_idx
                break
        rr = (1.0 / first_hit_rank) if first_hit_rank else 0.0
        rr_list.append(rr)

    if not recalls:
        return {
            "status": "unannotated",
            "message": "no queries matched annotated gold sources",
            "recall_at_5": None,
            "mrr": None,
            "annotated_queries_count": 0,
        }

    return {
        "status": "computed",
        "annotated_queries_count": len(recalls),
        "recall_at_5": round(float(np.mean(recalls)), 4),
        "mrr": round(float(np.mean(rr_list)), 4),
    }


def evaluate_dataset(
    judged_results: list[dict[str, Any]],
    traces: list[dict[str, Any]] | None = None,
    questions_csv_path: Path | None = None,
    n_resamples: int = 2000,
    ci: float = 0.95,
) -> dict[str, Any]:
    """Compute comprehensive metrics, bootstrap CIs, abstention metrics, and paired statistics."""
    traces_by_key = {}
    if traces:
        for t in traces:
            key = (t.get("question_id"), t.get("mode"))
            traces_by_key[key] = t

    gold_map: dict[str, set[str]] = {}
    if questions_csv_path and Path(questions_csv_path).exists():
        with Path(questions_csv_path).open("r", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                qid = row.get("question_id")
                gold = row.get("gold_source_ids", "").strip()
                if qid and gold:
                    gold_map[qid] = {g.strip() for g in gold.split("|") if g.strip()}

    modes = sorted(list({r["mode"] for r in judged_results if r.get("mode")}))
    results_by_mode: dict[str, Any] = {}

    for mode in modes:
        mode_rows = [r for r in judged_results if r.get("mode") == mode]
        n = len(mode_rows)
        if n == 0:
            continue

        # Correctness (0, 1, 2)
        corr_vals = [float(r["correctness_0_2"]) for r in mode_rows]
        corr_point, corr_low, corr_high = bootstrap_ci(corr_vals, np.mean, n_resamples, ci)

        # Unsupported claims (Hallucinations)
        unsup_binary = [1.0 if int(r.get("unsupported_claims", 0)) > 0 else 0.0 for r in mode_rows]
        unsup_point, unsup_low, unsup_high = bootstrap_ci(unsup_binary, np.mean, n_resamples, ci)

        unsup_counts = [float(r.get("unsupported_claims", 0)) for r in mode_rows]
        count_point, count_low, count_high = bootstrap_ci(unsup_counts, np.mean, n_resamples, ci)

        # Citation Precision
        cit_prec_vals = []
        for r in mode_rows:
            raw_cit = r.get("citation_precision_0_1")
            if raw_cit not in (None, "", "null", "None", "N/A"):
                try:
                    f_val = float(raw_cit)
                    if not math.isnan(f_val):
                        cit_prec_vals.append(f_val)
                except (ValueError, TypeError):
                    pass

        if cit_prec_vals:
            cit_point, cit_low, cit_high = bootstrap_ci(cit_prec_vals, np.mean, n_resamples, ci)
            cit_prec_stats: dict[str, Any] | None = {
                "mean": round(cit_point, 4),
                "ci_95": [round(cit_low, 4), round(cit_high, 4)],
                "evaluated_samples": len(cit_prec_vals),
            }
        else:
            cit_prec_stats = None

        # Citation Existence Rate
        cit_exist_vals = []
        for r in mode_rows:
            key = (r.get("question_id"), mode)
            tr = traces_by_key.get(key)
            if tr:
                cit_exist_vals.append(1.0 if len(tr.get("citations", [])) > 0 else 0.0)
            else:
                cit_exist_vals.append(1.0 if r.get("citation_precision_0_1") is not None else 0.0)
        cit_exist_point, cit_exist_low, cit_exist_high = bootstrap_ci(cit_exist_vals, np.mean, n_resamples, ci)

        # Abstention Metrics
        conf = compute_abstention_confusion(mode_rows)
        abst_metrics = compute_abstention_rates(conf)

        # Latency & Cost (from traces)
        latency_vals = []
        cost_vals = []
        for r in mode_rows:
            key = (r.get("question_id"), mode)
            tr = traces_by_key.get(key)
            if tr:
                latency_vals.append(float(tr.get("latency_ms", 0)))
                cost_vals.append(float(tr.get("estimated_cost_usd", 0.0)))

        lat_stats = (
            bootstrap_ci(latency_vals, np.mean, n_resamples, ci) if latency_vals else (0.0, 0.0, 0.0)
        )
        cost_stats = (
            bootstrap_ci(cost_vals, np.mean, n_resamples, ci) if cost_vals else (0.0, 0.0, 0.0)
        )

        # Retrieval Metrics
        matching_traces = [traces_by_key.get((r.get("question_id"), mode)) for r in mode_rows]
        retrieval_metrics = compute_retrieval_metrics(
            [t for t in matching_traces if t], gold_map, k=5
        )

        results_by_mode[mode] = {
            "total_questions": n,
            "correctness_0_2": {
                "mean": round(corr_point, 3),
                "ci_95": [round(corr_low, 3), round(corr_high, 3)],
            },
            "unsupported_claim_rate": {
                "rate": round(unsup_point, 3),
                "ci_95": [round(unsup_low, 3), round(unsup_high, 3)],
            },
            "avg_unsupported_claims_count": {
                "mean": round(count_point, 3),
                "ci_95": [round(count_low, 3), round(count_high, 3)],
            },
            "citation_existence_rate": {
                "rate": round(cit_exist_point, 3),
                "ci_95": [round(cit_exist_low, 3), round(cit_exist_high, 3)],
            },
            "citation_precision": cit_prec_stats,
            "abstention": {
                "confusion_matrix": conf,
                **abst_metrics,
            },
            "retrieval": retrieval_metrics,
            "system_performance": {
                "mean_latency_ms": round(lat_stats[0], 1) if latency_vals else None,
                "latency_ci_95": [round(lat_stats[1], 1), round(lat_stats[2], 1)] if latency_vals else None,
                "mean_cost_usd": round(cost_stats[0], 5) if cost_vals else None,
                "cost_ci_95": [round(cost_stats[1], 5), round(cost_stats[2], 5)] if cost_vals else None,
            },
        }

    # Compute paired comparisons for overlapping questions
    paired_comparison: dict[str, Any] = {}

    def _compute_pair(m_base: str, m_rag: str) -> dict[str, Any] | None:
        if m_base in results_by_mode and m_rag in results_by_mode:
            base_by_qid = {r["question_id"]: r for r in judged_results if r.get("mode") == m_base}
            rag_by_qid = {r["question_id"]: r for r in judged_results if r.get("mode") == m_rag}
            common_qids = sorted(list(set(base_by_qid.keys()) & set(rag_by_qid.keys())))

            if common_qids:
                rag_corr = [float(rag_by_qid[q]["correctness_0_2"]) for q in common_qids]
                base_corr = [float(base_by_qid[q]["correctness_0_2"]) for q in common_qids]
                diff_corr, c_low, c_high, p_corr = bootstrap_paired_diff(rag_corr, base_corr, np.mean, n_resamples, ci)

                rag_unsup = [1.0 if int(rag_by_qid[q].get("unsupported_claims", 0)) > 0 else 0.0 for q in common_qids]
                base_unsup = [1.0 if int(base_by_qid[q].get("unsupported_claims", 0)) > 0 else 0.0 for q in common_qids]
                diff_unsup, u_low, u_high, p_unsup = bootstrap_paired_diff(rag_unsup, base_unsup, np.mean, n_resamples, ci)

                return {
                    "paired_questions_count": len(common_qids),
                    "correctness_diff": {
                        "delta": round(diff_corr, 3),
                        "ci_95": [round(c_low, 3), round(c_high, 3)],
                        "p_value": round(p_corr, 4),
                        "significant_p05": p_corr < 0.05,
                    },
                    "unsupported_rate_diff": {
                        "delta": round(diff_unsup, 3),
                        "ci_95": [round(u_low, 3), round(u_high, 3)],
                        "p_value": round(p_unsup, 4),
                        "significant_p05": p_unsup < 0.05,
                    },
                }
        return None

    gemini_pair = _compute_pair("baseline", "rag_verified")
    if gemini_pair:
        paired_comparison["gemini"] = gemini_pair
        paired_comparison.update(gemini_pair)

    ollama_pair = _compute_pair("ollama_baseline", "ollama_rag")
    if ollama_pair:
        paired_comparison["ollama"] = ollama_pair

    return {
        "modes": results_by_mode,
        "paired_comparison": paired_comparison,
        "bootstrap_resamples": n_resamples,
        "confidence_level": ci,
    }


def format_dissertation_table(metrics: dict[str, Any]) -> str:
    """Format academic evaluation table with 95% CIs and comparisons for dissertation.
    Automatically generates a 4-way comparative table if local Ollama runs are present."""
    modes = metrics.get("modes", {})
    has_ollama = "ollama_baseline" in modes or "ollama_rag" in modes
    paired = metrics.get("paired_comparison", {})

    def _fmt(val_dict: dict[str, Any] | None, key: str = "mean", scale: float = 1.0, is_pct: bool = False) -> str:
        if not val_dict:
            return "N/A"
        point = val_dict.get(key)
        ci_vals = val_dict.get("ci_95")
        if point is None or ci_vals is None:
            return "N/A"
        p_str = f"{point * scale:.1%}" if is_pct else f"{point * scale:.2f}"
        ci_str = f"[{ci_vals[0] * scale:.2f}, {ci_vals[1] * scale:.2f}]"
        return f"{p_str} {ci_str}"

    if has_ollama:
        o_base = modes.get("ollama_baseline", {})
        o_rag = modes.get("ollama_rag", {})
        g_base = modes.get("baseline", {})
        g_rag = modes.get("rag_verified", {})

        lines = [
            "| Evaluation Metric | Local Baseline (Ollama) | Local RAG (Ollama) | Cloud Baseline (Gemini) | Cloud RAG (Gemini) |",
            "| :--- | :---: | :---: | :---: | :---: |",
            f"| **Sample Size (N)** | N = {o_base.get('total_questions', 'N/A')} | N = {o_rag.get('total_questions', 'N/A')} | N = {g_base.get('total_questions', 'N/A')} | N = {g_rag.get('total_questions', 'N/A')} |",
            f"| **Mean Correctness (0-2 scale)** | {_fmt(o_base.get('correctness_0_2'))} | {_fmt(o_rag.get('correctness_0_2'))} | {_fmt(g_base.get('correctness_0_2'))} | {_fmt(g_rag.get('correctness_0_2'))} |",
            f"| **Unsupported Claim Rate (Hallucinations)** | {_fmt(o_base.get('unsupported_claim_rate'), 'rate', 100.0)}% | {_fmt(o_rag.get('unsupported_claim_rate'), 'rate', 100.0)}% | {_fmt(g_base.get('unsupported_claim_rate'), 'rate', 100.0)}% | {_fmt(g_rag.get('unsupported_claim_rate'), 'rate', 100.0)}% |",
            f"| **Citation Precision (0-1 scale)** | {_fmt(o_base.get('citation_precision'))} | {_fmt(o_rag.get('citation_precision'))} | {_fmt(g_base.get('citation_precision'))} | {_fmt(g_rag.get('citation_precision'))} |",
            f"| **Abstention Precision** | {o_base.get('abstention', {}).get('abstention_precision', 'N/A')} | {o_rag.get('abstention', {}).get('abstention_precision', 'N/A')} | {g_base.get('abstention', {}).get('abstention_precision', 'N/A')} | {g_rag.get('abstention', {}).get('abstention_precision', 'N/A')} |",
            f"| **Abstention Recall** | {o_base.get('abstention', {}).get('abstention_recall', 'N/A')} | {o_rag.get('abstention', {}).get('abstention_recall', 'N/A')} | {g_base.get('abstention', {}).get('abstention_recall', 'N/A')} | {g_rag.get('abstention', {}).get('abstention_recall', 'N/A')} |",
            f"| **Mean Latency (ms)** | {o_base.get('system_performance', {}).get('mean_latency_ms', 'N/A')} ms | {o_rag.get('system_performance', {}).get('mean_latency_ms', 'N/A')} ms | {g_base.get('system_performance', {}).get('mean_latency_ms', 'N/A')} ms | {g_rag.get('system_performance', {}).get('mean_latency_ms', 'N/A')} ms |",
            f"| **Estimated Cost ($ / query)** | $0.00 | $0.00 | ${g_base.get('system_performance', {}).get('mean_cost_usd', 0.0):.4f} | ${g_rag.get('system_performance', {}).get('mean_cost_usd', 0.0):.4f} |",
        ]
        return "\n".join(lines)

    base = modes.get("baseline", {})
    rag = modes.get("rag_verified", {})

    lines = [
        "| Evaluation Metric | Baseline (Plain LLM) [95% CI] | NeuroEvidence (RAG Verified) [95% CI] | Paired Difference [95% CI] | p-value |",
        "| :--- | :---: | :---: | :---: | :---: |",
    ]

    # Sample size
    n_base = base.get("total_questions", "N/A")
    n_rag = rag.get("total_questions", "N/A")
    n_pair = paired.get("paired_questions_count", "N/A")
    lines.append(f"| **Sample Size (N)** | N = {n_base} | N = {n_rag} | N = {n_pair} (Paired) | -- |")

    # Correctness
    b_corr = _fmt(base.get("correctness_0_2"), "mean")
    r_corr = _fmt(rag.get("correctness_0_2"), "mean")
    p_corr = paired.get("correctness_diff", {})
    diff_corr = (
        f"{p_corr.get('delta', 0):+.2f} [{p_corr.get('ci_95', [0, 0])[0]:.2f}, {p_corr.get('ci_95', [0, 0])[1]:.2f}]"
        if p_corr
        else "N/A"
    )
    pval_corr = f"{p_corr.get('p_value', 1.0):.4f}" if p_corr else "N/A"
    lines.append(f"| **Mean Correctness (0-2 scale)** | {b_corr} | {r_corr} | {diff_corr} | {pval_corr} |")

    # Unsupported claim rate
    b_unsup = _fmt(base.get("unsupported_claim_rate"), "rate", scale=100.0, is_pct=False) + "%" if base.get("unsupported_claim_rate") else "N/A"
    r_unsup = _fmt(rag.get("unsupported_claim_rate"), "rate", scale=100.0, is_pct=False) + "%" if rag.get("unsupported_claim_rate") else "N/A"
    p_unsup = paired.get("unsupported_rate_diff", {})
    diff_unsup = (
        f"{p_unsup.get('delta', 0) * 100:+.1f}% [{p_unsup.get('ci_95', [0, 0])[0] * 100:.1f}%, {p_unsup.get('ci_95', [0, 0])[1] * 100:.1f}%]"
        if p_unsup
        else "N/A"
    )
    pval_unsup = f"{p_unsup.get('p_value', 1.0):.4f}" if p_unsup else "N/A"
    lines.append(f"| **Unsupported Claim Rate (Hallucinations)** | {b_unsup} | {r_unsup} | {diff_unsup} | {pval_unsup} |")

    # Citation existence & precision
    b_cit_prec = _fmt(base.get("citation_precision"), "mean") if base.get("citation_precision") else "None (Plain LLM)"
    r_cit_prec = _fmt(rag.get("citation_precision"), "mean")
    lines.append(f"| **Citation Precision (0-1 scale)** | {b_cit_prec} | {r_cit_prec} | Grounded to Literature | -- |")

    # Abstention precision & recall
    b_abs = base.get("abstention", {})
    r_abs = rag.get("abstention", {})
    lines.append(
        f"| **Abstention Precision** | {b_abs.get('abstention_precision', 'N/A')} | {r_abs.get('abstention_precision', 'N/A')} | Refusal Precision | -- |"
    )
    lines.append(
        f"| **Abstention Recall** | {b_abs.get('abstention_recall', 'N/A')} | {r_abs.get('abstention_recall', 'N/A')} | Scope Enforced | -- |"
    )
    lines.append(
        f"| **Safety Routing Accuracy** | {b_abs.get('safety_routing_accuracy', 'N/A')} | {r_abs.get('safety_routing_accuracy', 'N/A')} | Refusal Accuracy | -- |"
    )

    # Retrieval Recall@5 & MRR
    r_ret = rag.get("retrieval", {})
    if r_ret.get("status") == "computed":
        lines.append(f"| **Retrieval Recall@5** | N/A (Baseline) | {r_ret.get('recall_at_5'):.3f} | Dense-Sparse RRF | -- |")
        lines.append(f"| **Retrieval MRR** | N/A (Baseline) | {r_ret.get('mrr'):.3f} | Neural Reranked | -- |")
    else:
        lines.append("| **Retrieval Recall@5 & MRR** | N/A (Baseline) | *Unannotated gold IDs* | Grounding via Citations | -- |")

    # Latency
    b_perf = base.get("system_performance", {})
    r_perf = rag.get("system_performance", {})
    if b_perf.get("mean_latency_ms") is not None and r_perf.get("mean_latency_ms") is not None:
        lines.append(
            f"| **Mean Latency (ms)** | {b_perf.get('mean_latency_ms')} ms | {r_perf.get('mean_latency_ms')} ms | {_diff_num(r_perf.get('mean_latency_ms'), b_perf.get('mean_latency_ms'))} ms | -- |"
        )

    return "\n".join(lines)


def _diff_num(val_a: float | None, val_b: float | None) -> str:
    if val_a is None or val_b is None:
        return "N/A"
    return f"{val_a - val_b:+.1f}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--judge-csv",
        type=Path,
        default=Path("data/evaluation/judge_review.csv"),
        help="Path to judge review CSV file",
    )
    parser.add_argument(
        "--traces",
        type=Path,
        default=Path("data/evaluation/results.jsonl"),
        help="Path to trace results JSONL file",
    )
    parser.add_argument(
        "--questions",
        type=Path,
        default=Path("data/evaluation_questions.csv"),
        help="Path to evaluation questions CSV file",
    )
    parser.add_argument(
        "--output-summary",
        type=Path,
        default=Path("data/evaluation/comprehensive_evaluation_summary.json"),
        help="Path to output comprehensive metrics JSON",
    )
    parser.add_argument("--resamples", type=int, default=2000, help="Number of bootstrap resamples")
    args = parser.parse_args()

    judge_csv_path = _resolve_project_path(args.judge_csv)
    traces_path = _resolve_project_path(args.traces)
    questions_path = _resolve_project_path(args.questions)
    summary_path = _resolve_project_path(args.output_summary)

    if not judge_csv_path.exists():
        raise FileNotFoundError(f"Judge CSV not found: {judge_csv_path}")

    with judge_csv_path.open("r", encoding="utf-8-sig") as handle:
        judged = list(csv.DictReader(handle))

    traces = None
    if traces_path.exists():
        with traces_path.open("r", encoding="utf-8") as handle:
            traces = [json.loads(line) for line in handle if line.strip()]

    print(f"Computing bootstrap 95% CIs and comprehensive metrics across {len(judged)} records ({args.resamples} resamples)...")
    metrics = evaluate_dataset(
        judged,
        traces=traces,
        questions_csv_path=questions_path,
        n_resamples=args.resamples,
    )

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print("\n" + "=" * 80)
    print("ACADEMIC DISSERTATION EVALUATION RESULTS (BOOTSTRAP 95% CONFIDENCE INTERVALS)")
    print("=" * 80 + "\n")
    print(format_dissertation_table(metrics))
    print(f"\nComprehensive JSON summary written to: {summary_path}")


if __name__ == "__main__":
    main()
