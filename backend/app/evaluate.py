"""Run the locked evaluation CSV against a locally running NeuroEvidence API."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

import httpx


COMPARISON_CATEGORIES = {"answerable", "unanswerable"}


def _resolve_project_path(p: Path) -> Path:
    """Resolve a relative path against the project root if invoked from the backend subdirectory."""
    if not p.is_absolute():
        cwd = Path.cwd()
        if cwd.name.lower() == "backend" and (cwd.parent / "data").exists():
            return cwd.parent / p
    return p


def run(
    questions_path: Path,
    output_path: Path,
    blind_path: Path,
    api_url: str,
    split: str,
) -> None:
    questions_path = _resolve_project_path(questions_path)
    output_path = _resolve_project_path(output_path)
    blind_path = _resolve_project_path(blind_path)

    with questions_path.open("r", encoding="utf-8-sig", newline="") as handle:
        questions = [row for row in csv.DictReader(handle) if row["split"] == split]
    if not questions:
        raise ValueError(f"No questions found for split={split}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    with httpx.Client(base_url=api_url, timeout=120) as client:
        for row in questions:
            modes = ["baseline", "rag_verified"] if row["category"] in COMPARISON_CATEGORIES else ["rag_verified"]
            for mode in modes:
                response = client.post(
                    "/api/chat",
                    json={
                        "session_id": f"evaluation-{split}",
                        "question_id": row["question_id"],
                        "question": row["question"],
                        "mode": mode,
                    },
                )
                response.raise_for_status()
                payload = response.json()
                results.append(
                    {
                        "question_id": row["question_id"],
                        "split": split,
                        "category": row["category"],
                        "topic": row["topic"],
                        "question": row["question"],
                        "mode": mode,
                        "trace_id": payload["trace_id"],
                        "answer": payload["answer"],
                        "citations": payload["citations"],
                        "claim_checks": payload["claim_checks"],
                        "evidence_score": payload["evidence_score"],
                        "warnings": payload["warnings"],
                        "latency_ms": payload["latency_ms"],
                        "model": payload["model"],
                        "input_tokens": payload["input_tokens"],
                        "output_tokens": payload["output_tokens"],
                        "estimated_cost_usd": payload["estimated_cost_usd"],
                    }
                )
                print(f"{row['question_id']} {mode}", flush=True)

    output_path.write_text(
        "\n".join(json.dumps(item, ensure_ascii=False) for item in results),
        encoding="utf-8",
    )
    write_blinded(results, blind_path)


def write_blinded(results: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    blinded = []
    for item in results:
        response_id = hashlib.sha256(
            f"{item['question_id']}|{item['mode']}".encode()
        ).hexdigest()[:12]
        blinded.append(
            {
                "response_id": response_id,
                "question": item["question"],
                "answer": item["answer"],
                "reviewer": "",
                "correctness_0_2": "",
                "unsupported_claims": "",
                "citation_precision_0_1": "",
                "appropriate_abstention_0_1": "",
                "notes": "",
            }
        )
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=blinded[0].keys())
        writer.writeheader()
        writer.writerows(blinded)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, default=Path("data/evaluation_questions.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/evaluation/results.jsonl"))
    parser.add_argument("--blind-output", type=Path, default=Path("data/evaluation/blinded_review.csv"))
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--split", choices=["validation", "test"], default="validation")
    parser.add_argument("--run-judge", action="store_true", help="Automatically run LLM-as-a-Judge on traces")
    parser.add_argument("--judge-output", type=Path, default=Path("data/evaluation/judge_review.csv"), help="Path to judge CSV output")
    parser.add_argument("--judge-summary", type=Path, default=Path("data/evaluation/judge_summary.json"), help="Path to judge summary JSON")
    parser.add_argument("--judge-model", type=str, default=None, help="LLM model to use for the judge (e.g. gemini-2.5-pro)")
    args = parser.parse_args()
    run(args.questions, args.output, args.blind_output, args.api_url, args.split)

    if args.run_judge:
        from .evaluate_judge import format_comparison_table, run_judge

        judged, metrics = run_judge(
            args.output, args.judge_output, args.judge_summary, judge_model=args.judge_model
        )
        print("\n" + "=" * 60)
        print("LLM-AS-A-JUDGE EVALUATION RESULTS")
        print("=" * 60)
        print(format_comparison_table(metrics))
        print(f"\nJudge CSV saved to: {args.judge_output}")
        print(f"Judge Summary saved to: {args.judge_summary}")


if __name__ == "__main__":
    main()
