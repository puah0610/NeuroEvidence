from pathlib import Path

import pytest

from app.config import Settings
from app.database import Database
from app.service import ChatService


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        demo_mode=True,
        database_path=tmp_path / "test.db",
        chroma_path=tmp_path / "chroma",
        evidence_threshold=0.65,
    )


@pytest.fixture
def database(settings: Settings) -> Database:
    return Database(settings.database_path)


@pytest.fixture
def service(settings: Settings, database: Database) -> ChatService:
    return ChatService(settings, database)

