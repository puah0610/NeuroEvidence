import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

from .models import ChatResponse, EvaluationSummary, FeedbackRequest


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS traces (
                    trace_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    intent TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    original_answer TEXT,
                    citations_json TEXT NOT NULL,
                    claim_checks_json TEXT NOT NULL,
                    evidence_score REAL,
                    latency_ms INTEGER NOT NULL,
                    model TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL DEFAULT 0,
                    output_tokens INTEGER NOT NULL DEFAULT 0,
                    estimated_cost_usd REAL NOT NULL DEFAULT 0,
                    demo_mode INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_traces_mode ON traces(mode);
                CREATE INDEX IF NOT EXISTS idx_traces_session ON traces(session_id);

                CREATE TABLE IF NOT EXISTS feedback (
                    feedback_id TEXT PRIMARY KEY,
                    trace_id TEXT NOT NULL,
                    helpful INTEGER,
                    issue_type TEXT,
                    comment TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(trace_id) REFERENCES traces(trace_id)
                );
                """
            )
            try:
                connection.execute("ALTER TABLE traces ADD COLUMN subqueries_json TEXT")
            except sqlite3.OperationalError:
                pass

    def save_trace(self, session_id: str, question: str, result: ChatResponse) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO traces(
                    trace_id, session_id, question, mode, intent, answer, original_answer,
                    citations_json, claim_checks_json, subqueries_json, evidence_score, latency_ms, model,
                    input_tokens, output_tokens, estimated_cost_usd, demo_mode, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.trace_id,
                    session_id,
                    question,
                    result.mode.value,
                    result.intent.value,
                    result.answer,
                    result.original_answer,
                    json.dumps([item.model_dump(mode="json") for item in result.citations]),
                    json.dumps([item.model_dump(mode="json") for item in result.claim_checks]),
                    json.dumps([item.model_dump(mode="json") for item in result.subqueries]),
                    result.evidence_score,
                    result.latency_ms,
                    result.model,
                    result.input_tokens,
                    result.output_tokens,
                    result.estimated_cost_usd,
                    int(result.demo_mode),
                    result.created_at.isoformat(),
                ),
            )

    def save_feedback(self, request: FeedbackRequest) -> str:
        feedback_id = str(uuid4())
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO feedback(feedback_id, trace_id, helpful, issue_type, comment, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    feedback_id,
                    request.trace_id,
                    None if request.helpful is None else int(request.helpful),
                    request.issue_type,
                    request.comment,
                    datetime.now(UTC).isoformat(),
                ),
            )
        return feedback_id

    def summary(self) -> EvaluationSummary:
        with self._connect() as connection:
            totals = connection.execute(
                """SELECT COUNT(*) AS total,
                AVG(evidence_score) AS score, AVG(latency_ms) AS latency,
                COALESCE(SUM(input_tokens), 0) AS input_tokens,
                COALESCE(SUM(output_tokens), 0) AS output_tokens,
                COALESCE(SUM(estimated_cost_usd), 0) AS cost FROM traces"""
            ).fetchone()
            modes = connection.execute(
                "SELECT mode, COUNT(*) AS count FROM traces GROUP BY mode"
            ).fetchall()
            intents = connection.execute(
                "SELECT intent, COUNT(*) AS count FROM traces GROUP BY intent"
            ).fetchall()
            feedback = connection.execute(
                """SELECT COUNT(*) AS total,
                AVG(CASE WHEN helpful IS NOT NULL THEN helpful END) AS helpful_rate
                FROM feedback"""
            ).fetchone()

        return EvaluationSummary(
            total_traces=totals["total"],
            by_mode={row["mode"]: row["count"] for row in modes},
            by_intent={row["intent"]: row["count"] for row in intents},
            average_evidence_score=_rounded(totals["score"]),
            average_latency_ms=_rounded(totals["latency"], 1),
            total_input_tokens=int(totals["input_tokens"]),
            total_output_tokens=int(totals["output_tokens"]),
            total_estimated_cost_usd=round(float(totals["cost"]), 6),
            feedback_count=feedback["total"],
            helpful_rate=_rounded(feedback["helpful_rate"]),
        )


def _rounded(value: Any, digits: int = 3) -> float | None:
    return None if value is None else round(float(value), digits)
