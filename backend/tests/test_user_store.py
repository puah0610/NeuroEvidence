from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.database import Database
from app.main import app
from app.user_store import UserWorkspaceStore


def test_user_workspace_creates_separate_folders_and_isolates_sessions(tmp_path: Path):
    store = UserWorkspaceStore(tmp_path / "users")

    admin_ws = store.load_workspace("admin")
    puah_ws = store.load_workspace("Puah")

    assert (tmp_path / "users" / "admin" / "sessions").is_dir()
    assert (tmp_path / "users" / "admin" / "folders.json").is_file()
    assert (tmp_path / "users" / "puah" / "sessions").is_dir()
    assert (tmp_path / "users" / "puah" / "folders.json").is_file()
    assert admin_ws["sessions"] == []
    assert puah_ws["sessions"] == []

    store.save_session("admin", "session-admin-1", {"title": "Admin Research", "messages": [{"role": "user", "text": "SANAD II"}]})
    store.save_session("puah", "session-puah-1", {"title": "Clinician Case", "messages": [{"role": "user", "text": "Levodopa"}]})

    admin_after = store.load_workspace("admin")
    puah_after = store.load_workspace("puah")

    assert [s["id"] for s in admin_after["sessions"]] == ["session-admin-1"]
    assert [s["id"] for s in puah_after["sessions"]] == ["session-puah-1"]

    assert store.clear_sessions("puah") == 1
    assert store.load_workspace("puah")["sessions"] == []
    assert [s["id"] for s in store.load_workspace("admin")["sessions"]] == ["session-admin-1"]


def test_user_workspace_rejects_path_traversal(tmp_path: Path):
    store = UserWorkspaceStore(tmp_path / "users")
    with pytest.raises(ValueError):
        store.load_workspace("../escape")
    with pytest.raises(ValueError):
        store.save_session("admin", "../../evil", {"title": "bad"})


def test_database_auth_register_and_login(tmp_path: Path):
    db = Database(tmp_path / "test.db")

    # Seeded accounts work out of the box
    admin = db.authenticate_user("admin", "admin123")
    assert admin is not None and admin["account_role"] == "admin"

    puah = db.authenticate_user("Puah", "puah123")
    assert puah is not None and puah["account_role"] == "clinician"

    assert db.authenticate_user("admin", "wrong") is None

    # Register a brand-new clinician account
    created = db.register_user(
        username="alex_tan",
        email="alex@hospital.edu",
        password="secret123",
        full_name="Dr. Alex Tan",
    )
    assert created["user_id"] == "alex_tan"
    assert created["account_role"] == "clinician"
    assert created["profile"]["name"] == "Dr. Alex Tan"

    # Login by username OR email works
    assert db.authenticate_user("alex_tan", "secret123")["user_id"] == "alex_tan"
    assert db.authenticate_user("ALEX@HOSPITAL.EDU", "secret123")["user_id"] == "alex_tan"
    assert db.authenticate_user("alex_tan", "wrongpass") is None

    # Duplicate username or email rejected
    with pytest.raises(ValueError, match="username"):
        db.register_user(username="ALEX_TAN", email="other@hospital.edu", password="secret123")
    with pytest.raises(ValueError, match="email"):
        db.register_user(username="new_user", email="alex@hospital.edu", password="secret123")


def test_auth_api_register_creates_user_folder_and_saves_session(tmp_path: Path, monkeypatch):
    test_db = Database(tmp_path / "app.db")
    test_store = UserWorkspaceStore(tmp_path / "users")

    with TestClient(app) as client:
        app.state.database = test_db
        app.state.user_store = test_store

        # Register new user
        reg = client.post(
            "/api/auth/register",
            json={
                "username": "dr_maya",
                "email": "maya@clinic.org",
                "password": "maya123",
                "full_name": "Dr. Maya Lim",
            },
        )
        assert reg.status_code == 201
        data = reg.json()
        assert data["user_id"] == "dr_maya"
        assert data["account_role"] == "clinician"
        assert data["storage_path"] == "data/users/dr_maya/"
        assert (tmp_path / "users" / "dr_maya" / "sessions").is_dir()

        # Save a session under the new user
        save_res = client.put(
            "/api/users/dr_maya/sessions/session-maya-1",
            json={"id": "session-maya-1", "title": "Epilepsy Study", "folderId": "f-epi", "messages": []},
        )
        assert save_res.status_code == 200
        assert (tmp_path / "users" / "dr_maya" / "sessions" / "session-maya-1.json").is_file()

        # Login with new account and verify workspace contains her session (and admin does not see it)
        login = client.post("/api/auth/login", json={"identifier": "dr_maya", "password": "maya123"})
        assert login.status_code == 200
        assert login.json()["account_role"] == "clinician"

        ws_maya = client.get("/api/users/dr_maya/workspace").json()
        ws_admin = client.get("/api/users/admin/workspace").json()
        assert [s["id"] for s in ws_maya["sessions"]] == ["session-maya-1"]
        assert ws_admin["sessions"] == []
