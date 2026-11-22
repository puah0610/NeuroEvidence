import hashlib
import hmac
import json
import re
import secrets
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

from .models import ChatResponse, EvaluationSummary, FeedbackRequest

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,39}$")


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000).hex()
    return f"pbkdf2_sha256${salt}${digest}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        scheme, salt, expected = stored_hash.split("$", 2)
        if scheme != "pbkdf2_sha256":
            return False
        computed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000).hex()
        return hmac.compare_digest(computed, expected)
    except Exception:
        return False


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

                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    account_role TEXT NOT NULL DEFAULT 'clinician',
                    full_name TEXT NOT NULL,
                    role_title TEXT NOT NULL DEFAULT 'Clinician / Medical Learner',
                    institution TEXT NOT NULL DEFAULT 'Neurology Teaching Hospital',
                    specialty TEXT NOT NULL DEFAULT 'Neurology',
                    created_at TEXT NOT NULL
                );
                """
            )
            try:
                connection.execute("ALTER TABLE traces ADD COLUMN subqueries_json TEXT")
            except sqlite3.OperationalError:
                pass
            try:
                connection.execute("ALTER TABLE traces ADD COLUMN user_id TEXT")
            except sqlite3.OperationalError:
                pass
            self._seed_default_users(connection)

    def _seed_default_users(self, connection: sqlite3.Connection) -> None:
        defaults = [
            (
                "admin",
                "admin",
                "admin@neuroevidence.edu",
                "admin123",
                "admin",
                "Daniel Puah",
                "Researcher / Developer (Admin)",
                "NeuroEvidence Research Lab",
                "Clinical Informatics & Neurology",
            ),
            (
                "puah",
                "Puah",
                "puah@neuroevidence.edu",
                "puah123",
                "clinician",
                "Puah",
                "Clinician / Medical Learner",
                "Neurology Teaching Hospital",
                "Movement Disorders & Epilepsy",
            ),
        ]
        now = datetime.now(UTC).isoformat()
        for uid, uname, email, raw_pw, acc_role, full_name, role_title, inst, spec in defaults:
            existing = connection.execute(
                "SELECT user_id FROM users WHERE user_id = ? OR LOWER(username) = LOWER(?)",
                (uid, uname),
            ).fetchone()
            if not existing:
                connection.execute(
                    """
                    INSERT INTO users(
                        user_id, username, email, password_hash, account_role,
                        full_name, role_title, institution, specialty, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (uid, uname, email, hash_password(raw_pw), acc_role, full_name, role_title, inst, spec, now),
                )

    @staticmethod
    def _row_to_user_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "user_id": row["user_id"],
            "username": row["username"],
            "account_role": "admin" if row["account_role"] == "admin" else "clinician",
            "profile": {
                "name": row["full_name"],
                "role": row["role_title"],
                "email": row["email"],
                "specialty": row["specialty"],
                "institution": row["institution"],
            },
        }

    def register_user(
        self,
        username: str,
        email: str,
        password: str,
        full_name: str | None = None,
        institution: str | None = None,
        specialty: str | None = None,
    ) -> dict[str, Any]:
        clean_username = (username or "").strip()
        clean_email = (email or "").strip().lower()
        clean_password = (password or "").strip()

        if not USERNAME_PATTERN.match(clean_username):
            raise ValueError(
                "Username must be 2–40 characters and contain only letters, numbers, '.', '_', or '-'."
            )
        if "@" not in clean_email or "." not in clean_email.split("@")[-1]:
            raise ValueError("Please enter a valid email address.")
        if len(clean_password) < 4:
            raise ValueError("Password must be at least 4 characters.")

        user_id = clean_username.lower()
        display_name = (full_name or "").strip() or clean_username
        inst = (institution or "").strip() or "Neurology Teaching Hospital"
        spec = (specialty or "").strip() or "Neurology"
        now = datetime.now(UTC).isoformat()

        with self._lock, self._connect() as connection:
            dup_user = connection.execute(
                "SELECT 1 FROM users WHERE user_id = ? OR LOWER(username) = LOWER(?)",
                (user_id, clean_username),
            ).fetchone()
            if dup_user:
                raise ValueError("That username is already registered.")

            dup_email = connection.execute(
                "SELECT 1 FROM users WHERE LOWER(email) = LOWER(?)",
                (clean_email,),
            ).fetchone()
            if dup_email:
                raise ValueError("That email address is already registered.")

            connection.execute(
                """
                INSERT INTO users(
                    user_id, username, email, password_hash, account_role,
                    full_name, role_title, institution, specialty, created_at
                ) VALUES (?, ?, ?, ?, 'clinician', ?, 'Clinician / Medical Learner', ?, ?, ?)
                """,
                (user_id, clean_username, clean_email, hash_password(clean_password), display_name, inst, spec, now),
            )
            row = connection.execute(
                "SELECT * FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            return self._row_to_user_dict(row)

    def authenticate_user(self, identifier: str, password: str) -> dict[str, Any] | None:
        clean_id = (identifier or "").strip()
        clean_pw = (password or "").strip()
        if not clean_id or not clean_pw:
            return None
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM users
                WHERE LOWER(username) = LOWER(?) OR LOWER(email) = LOWER(?)
                """,
                (clean_id, clean_id),
            ).fetchone()
        if not row or not verify_password(clean_pw, row["password_hash"]):
            return None
        return self._row_to_user_dict(row)

    def update_user_profile(self, user_id: str, profile: dict[str, Any]) -> dict[str, Any] | None:
        clean_uid = (user_id or "").strip().lower()
        with self._lock, self._connect() as connection:
            existing = connection.execute(
                "SELECT * FROM users WHERE user_id = ?",
                (clean_uid,),
            ).fetchone()
            if not existing:
                return None

            new_email = (profile.get("email") or existing["email"]).strip().lower()
            conflict = connection.execute(
                "SELECT user_id FROM users WHERE LOWER(email) = LOWER(?) AND user_id != ?",
                (new_email, clean_uid),
            ).fetchone()
            if conflict:
                raise ValueError("Email address is already used by another account.")

            connection.execute(
                """
                UPDATE users
                SET full_name = ?, role_title = ?, email = ?, institution = ?, specialty = ?
                WHERE user_id = ?
                """,
                (
                    (profile.get("name") or existing["full_name"]).strip(),
                    (profile.get("role") or existing["role_title"]).strip(),
                    new_email,
                    (profile.get("institution") or existing["institution"]).strip(),
                    (profile.get("specialty") or existing["specialty"]).strip(),
                    clean_uid,
                ),
            )
            updated = connection.execute(
                "SELECT * FROM users WHERE user_id = ?",
                (clean_uid,),
            ).fetchone()
            return self._row_to_user_dict(updated)

    def save_trace(
        self,
        session_id: str,
        question: str,
        result: ChatResponse,
        user_id: str | None = None,
    ) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO traces(
                    trace_id, session_id, user_id, question, mode, intent, answer, original_answer,
                    citations_json, claim_checks_json, subqueries_json, evidence_score, latency_ms, model,
                    input_tokens, output_tokens, estimated_cost_usd, demo_mode, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.trace_id,
                    session_id,
                    user_id,
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

    def get_session_history(self, session_id: str, limit: int = 6) -> list[dict[str, str]]:
        """Retrieve recent conversation turns for session_id in chronological order."""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT question, answer
                FROM traces
                WHERE session_id = ?
                ORDER BY created_at ASC
                """,
                (session_id,),
            ).fetchall()

        history: list[dict[str, str]] = []
        for row in rows:
            q = (row["question"] or "").strip()
            a = (row["answer"] or "").strip()
            if q:
                history.append({"role": "user", "content": q})
            if a:
                history.append({"role": "assistant", "content": a})

        return history[-limit:] if limit > 0 else history

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
