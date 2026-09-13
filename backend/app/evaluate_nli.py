"""Standalone NLI benchmark runner for biomedical and neurology claim verification."""

import argparse
import csv
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from .config import get_settings
from .models import VerificationLabel
from .verification import LexicalNLIVerifier, NLIVerifier, TransformerNLIVerifier


LABELS = [
    VerificationLabel.supported,
    VerificationLabel.contradicted,
    VerificationLabel.insufficient,
]


@dataclass
class ClassMetrics:
    precision: float
    recall: float
    f1: float
    support: int


@dataclass
class BenchmarkReport:
    benchmark_name: str
    model_name: str
    total_samples: int
    accuracy: float
    macro_f1: float
    weighted_f1: float
    per_class: dict[str, dict]
    confusion_matrix: dict[str, dict[str, int]]
    average_latency_ms: float
    total_duration_seconds: float


def load_dataset(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Benchmark file not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def evaluate_model(
    verifier: NLIVerifier,
    model_name: str,
    benchmark_name: str,
    samples: list[dict[str, str]],
) -> BenchmarkReport:
    predictions: list[VerificationLabel] = []
    gold_labels: list[VerificationLabel] = []
    latencies: list[float] = []

    start_total = time.perf_counter()
    for row in samples:
        evidence = row.get("evidence") or row.get("excerpt") or ""
        claim = row.get("claim", "")
        gold_raw = row.get("gold_label") or row.get("label") or ""

        try:
            gold = VerificationLabel(gold_raw.strip().lower())
        except ValueError:
            print(f"Warning: unrecognized gold label '{gold_raw}', skipping row {row.get('pair_id')}", file=sys.stderr)
            continue

        t0 = time.perf_counter()
        pred_label, _ = verifier.verify(evidence, claim)
        t1 = time.perf_counter()

        predictions.append(pred_label)
        gold_labels.append(gold)
        latencies.append((t1 - t0) * 1000.0)

    total_duration = time.perf_counter() - start_total
    total_n = len(gold_labels)
    if total_n == 0:
        raise ValueError(f"No valid labeled samples in benchmark '{benchmark_name}'")

    # Confusion matrix: matrix[true_label][pred_label]
    matrix: dict[str, dict[str, int]] = {
        label.value: {other.value: 0 for other in LABELS} for label in LABELS
    }
    for gold, pred in zip(gold_labels, predictions):
        matrix[gold.value][pred.value] += 1

    # Per-class metrics
    per_class: dict[str, dict] = {}
    f1_list: list[float] = []
    support_list: list[int] = []

    correct_total = sum(matrix[lbl.value][lbl.value] for lbl in LABELS)
    accuracy = round(correct_total / total_n, 4)

    for lbl in LABELS:
        name = lbl.value
        tp = matrix[name][name]
        fp = sum(matrix[other.value][name] for other in LABELS if other.value != name)
        fn = sum(matrix[name][other.value] for other in LABELS if other.value != name)
        support = sum(matrix[name].values())

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0

        per_class[name] = asdict(
            ClassMetrics(
                precision=round(prec, 4),
                recall=round(rec, 4),
                f1=round(f1, 4),
                support=support,
            )
        )
        f1_list.append(f1)
        support_list.append(support)

    macro_f1 = round(sum(f1_list) / len(f1_list), 4)
    weighted_f1 = round(
        sum(f * s for f, s in zip(f1_list, support_list)) / total_n, 4
    )
    avg_latency = round(sum(latencies) / len(latencies), 2)

    return BenchmarkReport(
        benchmark_name=benchmark_name,
        model_name=model_name,
        total_samples=total_n,
        accuracy=accuracy,
        macro_f1=macro_f1,
        weighted_f1=weighted_f1,
        per_class=per_class,
        confusion_matrix=matrix,
        average_latency_ms=avg_latency,
        total_duration_seconds=round(total_duration, 2),
    )


def print_report(report: BenchmarkReport) -> None:
    print("=" * 72)
    print(f"BENCHMARK: {report.benchmark_name.upper()} | MODEL: {report.model_name}")
    print("=" * 72)
    print(f"Total Evaluated: {report.total_samples}")
    print(f"Overall Accuracy: {report.accuracy * 100:.2f}%")
    print(f"Macro F1 Score:   {report.macro_f1:.4f}")
    print(f"Weighted F1:      {report.weighted_f1:.4f}")
    print(f"Avg Latency:      {report.average_latency_ms:.2f} ms/sample")
    print(f"Total Run Time:   {report.total_duration_seconds:.2f} s")
    print("-" * 72)
    print(f"{'Class':<16} {'Precision':<12} {'Recall':<12} {'F1-Score':<12} {'Support':<8}")
    print("-" * 72)
    for cls_name, metrics in report.per_class.items():
        print(
            f"{cls_name:<16} "
            f"{metrics['precision']:<12.4f} "
            f"{metrics['recall']:<12.4f} "
            f"{metrics['f1']:<12.4f} "
            f"{metrics['support']:<8}"
        )
    print("-" * 72)
    print("Confusion Matrix (Rows: Gold True, Columns: Predicted):")
    row_title = "True / Pred"
    header = f"{row_title:<16}" + "".join(f"{lbl.value:<14}" for lbl in LABELS)
    print(header)
    for true_lbl in LABELS:
        row_str = f"{true_lbl.value:<16}"
        for pred_lbl in LABELS:
            count = report.confusion_matrix[true_lbl.value][pred_lbl.value]
            row_str += f"{count:<14}"
        print(row_str)
    print("=" * 72 + "\n")


def compute_intra_annotator_kappa(samples: list[dict[str, str]]) -> float | None:
    """Compute Cohen's kappa for the 25% test-retest washout sample if retest annotations exist."""
    washout_rows = [r for r in samples if r.get("washout_sample", "").lower() == "yes"]
    if not washout_rows or "retest_label" not in washout_rows[0]:
        return None

    matrix = {lbl.value: {other.value: 0 for other in LABELS} for lbl in LABELS}
    n = 0
    for r in washout_rows:
        g = r.get("gold_label", "").strip().lower()
        t2 = r.get("retest_label", "").strip().lower()
        if g in matrix and t2 in matrix:
            matrix[g][t2] += 1
            n += 1

    if n == 0:
        return None

    po = sum(matrix[lbl.value][lbl.value] for lbl in LABELS) / n
    pe = sum(
        (sum(matrix[lbl.value].values()) / n)
        * (sum(matrix[other.value][lbl.value] for other in LABELS) / n)
        for lbl in LABELS
    )
    if pe >= 1.0:
        return 1.0
    return round((po - pe) / (1.0 - pe), 4)


def run_benchmarks(
    benchmark_choice: str,
    model_name: str,
    scifact_path: Path,
    neurology_path: Path,
    output_path: Path,
    compare_lexical: bool = False,
) -> list[BenchmarkReport]:
    benchmarks_to_run: list[tuple[str, Path]] = []
    if benchmark_choice in {"scifact", "all"}:
        benchmarks_to_run.append(("scifact", scifact_path))
    if benchmark_choice in {"neurology", "all"}:
        benchmarks_to_run.append(("neurology_domain", neurology_path))

    # Initialize models
    verifiers: list[tuple[str, NLIVerifier]] = []
    if compare_lexical or model_name.lower() == "lexical":
        verifiers.append(("lexical_baseline", LexicalNLIVerifier()))

    if model_name.lower() != "lexical":
        print(f"Loading transformer NLI verifier: {model_name}...")
        verifiers.append((model_name, TransformerNLIVerifier(model_name)))

    all_reports: list[BenchmarkReport] = []
    for bench_name, path in benchmarks_to_run:
        print(f"\nLoading {bench_name} from {path}...")
        samples = load_dataset(path)
        for m_name, verifier in verifiers:
            report = evaluate_model(verifier, m_name, bench_name, samples)
            print_report(report)
            all_reports.append(report)

    # Save results to JSON
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_dicts = [asdict(r) for r in all_reports]
    output_path.write_text(json.dumps(report_dicts, indent=2), encoding="utf-8")
    print(f"Saved evaluation results to {output_path}")

    return all_reports


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--benchmark",
        choices=["scifact", "neurology", "all"],
        default="all",
        help="Benchmark suite to evaluate (default: all)",
    )
    parser.add_argument(
        "--model",
        default="lexical",
        help=f"Model identifier or 'lexical' (default: 'lexical'; configured NLI: '{settings.nli_model}')",
    )
    parser.add_argument(
        "--scifact-path",
        type=Path,
        default=Path("data/benchmarks/scifact_eval.csv"),
    )
    parser.add_argument(
        "--neurology-path",
        type=Path,
        default=Path("data/benchmarks/neurology_nli_120.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/evaluation/nli_benchmark_results.json"),
    )
    parser.add_argument(
        "--compare-lexical",
        action="store_true",
        help="Run lexical baseline verifier in parallel for comparison",
    )
    args = parser.parse_args()

    run_benchmarks(
        benchmark_choice=args.benchmark,
        model_name=args.model,
        scifact_path=args.scifact_path,
        neurology_path=args.neurology_path,
        output_path=args.output,
        compare_lexical=args.compare_lexical,
    )


if __name__ == "__main__":
    main()
