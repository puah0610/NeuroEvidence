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
    modes: list[str] | None = None,
) -> None:
    questions_path = _resolve_project_path(questions_path)
    output_path = _resolve_project_path(output_path)
    blind_path = _resolve_project_path(blind_path)

    with questions_path.open("r", encoding="utf-8-sig", newline="") as handle:
        questions = [row for row in csv.DictReader(handle) if row["split"] == split]
    if not questions:
        raise ValueError(f"No questions found for split={split}")

    active_modes = modes or ["baseline", "rag_verified"]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    completed_keys: set[tuple[str, str]] = set()

    # Resume from existing runs if output_path exists
    if output_path.exists():
        try:
            with output_path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if line.strip():
                        item = json.loads(line)
                        key = (item.get("question_id"), item.get("mode"))
                        completed_keys.add(key)
                        results.append(item)
            if completed_keys:
                print(f"Resuming evaluation: found {len(completed_keys)} previously completed results.", flush=True)
        except Exception:
            pass

    with httpx.Client(base_url=api_url, timeout=300.0) as client:
        for row in questions:
            for mode in active_modes:
                key = (row["question_id"], mode)
                if key in completed_keys:
                    print(f"{row['question_id']} {mode} (already completed)", flush=True)
                    continue

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
                record = {
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
                results.append(record)
                completed_keys.add(key)

                # Persist incrementally so progress is never lost if interrupted
                with output_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(record, ensure_ascii=False) + "\n")

                print(f"{row['question_id']} {mode}", flush=True)

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
    parser.add_argument("--all-modes", action="store_true", help="Evaluate all 4 configurations: baseline, rag_verified, ollama_baseline, ollama_rag")
    parser.add_argument("--modes", type=str, default=None, help="Comma-separated list of modes (e.g. baseline,rag_verified,ollama_baseline,ollama_rag)")
    args = parser.parse_args()

    selected_modes = None
    if args.all_modes:
        selected_modes = ["baseline", "rag_verified", "ollama_baseline", "ollama_rag"]
    elif args.modes:
        selected_modes = [m.strip() for m in args.modes.split(",") if m.strip()]

    run(args.questions, args.output, args.blind_output, args.api_url, args.split, modes=selected_modes)

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
