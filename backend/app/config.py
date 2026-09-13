from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "NeuroEvidence API"
    app_version: str = "0.1.0"
    demo_mode: bool = True
    openai_api_key: str = ""
    openai_generation_model: str = "gpt-4.1-mini-2025-04-14"
    openai_embedding_model: str = "text-embedding-3-small"
    generation_input_cost_per_million: float = Field(default=0.40, ge=0)
    generation_output_cost_per_million: float = Field(default=1.60, ge=0)
    evidence_threshold: float = Field(default=0.65, ge=0, le=1)
    enable_nli: bool = False
    nli_model: str = "pritamdeka/PubMedBERT-MNLI-MedNLI"
    database_path: Path = Path("data/app.db")
    chroma_path: Path = Path("data/chroma")
    chroma_collection: str = "neurology_corpus_v1"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    crossref_mailto: str = ""
    retrieval_top_k: int = Field(default=8, ge=1, le=20)
    max_chunks_per_document: int = Field(default=3, ge=1, le=10)

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @field_validator("database_path", "chroma_path", mode="after")
    @classmethod
    def make_parent(cls, value: Path) -> Path:
        value.parent.mkdir(parents=True, exist_ok=True)
        return value

    @property
    def openai_enabled(self) -> bool:
        return bool(self.openai_api_key) and not self.demo_mode

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
