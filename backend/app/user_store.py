"""Per-user isolated workspace and session file storage under data/users/<user_id>/."""

from __future__ import annotations

import json
import re
from pathlib import Path
from threading import Lock
from typing import Any

SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

DEFAULT_FOLDERS: list[dict[str, Any]] = [
    {"id": "f-general", "name": "General Inquiries", "color": "#0E6B70"},
    {"id": "f-pd", "name": "Parkinson's Disease", "color": "#4F46E5"},
    {"id": "f-epi", "name": "Epilepsy & Seizures", "color": "#059669"},
]


def sanitize_identifier(raw: str, kind: str = "identifier") -> str:
    cleaned = (raw or "").strip()
    if not cleaned or ".." in cleaned or "/" in cleaned or "\\" in cleaned or not SAFE_ID_PATTERN.match(cleaned):
        raise ValueError(f"Invalid {kind}: '{raw}'")
    return cleaned


class UserWorkspaceStore:
    """Stores each user's folders and chat sessions in an isolated directory:
    data/users/<user_id>/
      ├── folders.json
      └── sessions/
            └── <session_id>.json
    """

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def _user_dir(self, user_id: str) -> Path:
        safe_user = sanitize_identifier(user_id.lower(), "user_id")
        user_dir = self.base_dir / safe_user
        sessions_dir = user_dir / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        return user_dir

    def _folders_file(self, user_id: str) -> Path:
        return self._user_dir(user_id) / "folders.json"

    def _session_file(self, user_id: str, session_id: str) -> Path:
        safe_session = sanitize_identifier(session_id, "session_id")
        return self._user_dir(user_id) / "sessions" / f"{safe_session}.json"

    def load_workspace(self, user_id: str) -> dict[str, Any]:
        """Ensure user's folder exists on disk and return their isolated folders + sessions."""
        with self._lock:
            user_dir = self._user_dir(user_id)
            folders_path = user_dir / "folders.json"
            sessions_dir = user_dir / "sessions"

            if folders_path.exists():
                try:
                    folders = json.loads(folders_path.read_text(encoding="utf-8"))
                    if not isinstance(folders, list) or not folders:
                        folders = list(DEFAULT_FOLDERS)
                except Exception:
                    folders = list(DEFAULT_FOLDERS)
            else:
                folders = list(DEFAULT_FOLDERS)
                folders_path.write_text(json.dumps(folders, indent=2, ensure_ascii=False), encoding="utf-8")

            sessions: list[dict[str, Any]] = []
            for path in sessions_dir.glob("*.json"):
                try:
                    item = json.loads(path.read_text(encoding="utf-8"))
                    if isinstance(item, dict) and item.get("id"):
                        sessions.append(item)
                except Exception:
                    continue

            sessions.sort(key=lambda s: s.get("lastUpdated") or s.get("timestamp") or 0, reverse=True)
            return {
                "user_id": user_dir.name,
                "storage_path": f"data/users/{user_dir.name}/",
                "folders": folders,
                "sessions": sessions,
            }

    def save_folders(self, user_id: str, folders: list[dict[str, Any]]) -> list[dict[str, Any]]:
        with self._lock:
            path = self._folders_file(user_id)
            path.write_text(json.dumps(folders, indent=2, ensure_ascii=False), encoding="utf-8")
            return folders

    def save_session(self, user_id: str, session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            path = self._session_file(user_id, session_id)
            record = dict(payload)
            record["id"] = sanitize_identifier(session_id, "session_id")
            path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
            return record

    def delete_session(self, user_id: str, session_id: str) -> bool:
        with self._lock:
            path = self._session_file(user_id, session_id)
            if path.exists():
                path.unlink()
                return True
            return False

    def clear_sessions(self, user_id: str) -> int:
        with self._lock:
            sessions_dir = self._user_dir(user_id) / "sessions"
            deleted = 0
            for path in sessions_dir.glob("*.json"):
                try:
                    path.unlink()
                    deleted += 1
                except Exception:
                    continue
            return deleted
