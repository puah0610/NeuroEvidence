from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "NeuroEvidence API"
    app_version: str = "0.1.0"
    demo_mode: bool = True
    llm_provider: str = "gemini"
    gemini_api_key: str = ""
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    gemini_generation_model: str = "gemini-3.8-flash"
    gemini_judge_model: str = "gemini-2.5-pro"
    gemini_embedding_model: str = "gemini-embedding-001"
    gemini_input_cost_per_million: float = Field(default=0.0, ge=0)
    gemini_output_cost_per_million: float = Field(default=0.0, ge=0)
    openai_api_key: str = ""
    openai_generation_model: str = "gpt-4.1-mini-2025-04-14"
    openai_judge_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"
    generation_input_cost_per_million: float = Field(default=0.40, ge=0)
    generation_output_cost_per_million: float = Field(default=1.60, ge=0)
    llm_temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    evidence_threshold: float = Field(default=0.65, ge=0, le=1)
    enable_nli: bool = False
    nli_model: str = "pritamdeka/PubMedBERT-MNLI-MedNLI"
    nli_min_confidence: float = Field(default=0.55, ge=0.0, le=1.0)
    nli_min_margin: float = Field(default=0.10, ge=0.0, le=1.0)
    nli_max_salient_sentences: int = Field(default=3, ge=1, le=10)
    enable_cross_chunk_fallback: bool = Field(default=True)
    enable_corrective_retrieval: bool = Field(default=True)
    corrective_retrieval_max_claims: int = Field(default=2, ge=1, le=5)
    database_path: Path = Path("data/app.db")
    chroma_path: Path = Path("data/chroma")
    chroma_collection: str = "neurology_corpus_v1"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    crossref_mailto: str = ""
    retrieval_top_k: int = Field(default=8, ge=1, le=20)
    max_chunks_per_document: int = Field(default=3, ge=1, le=10)
    enable_dense_embeddings: bool = True
    embedding_provider: str = "local"
    dense_model: str = "pritamdeka/S-PubMedBert-MS-MARCO"
    enable_reranker: bool = True
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    reranker_top_n: int = Field(default=20, ge=5, le=50)
    enable_hyde: bool = True
    hyde_max_tokens: int = Field(default=150, ge=30, le=500)
    parent_expansion_token_budget: int = Field(default=750, ge=200, le=2500)
    enable_bounded_answer_revision: bool = Field(default=True)
    enable_query_decomposition: bool = Field(default=True)
    max_decomposition_subqueries: int = Field(default=3, ge=2, le=5)
    enable_live_pubmed_fallback: bool = True
    live_pubmed_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    live_pubmed_max_candidates: int = Field(default=15, ge=5, le=30)
    live_pubmed_top_k: int = Field(default=3, ge=1, le=10)
    live_pubmed_timeout_seconds: float = Field(default=6.0, ge=1.0, le=30.0)
    auto_save_live_pubmed: bool = True

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"), env_file_encoding="utf-8", extra="ignore"
    )

    @field_validator("database_path", "chroma_path", mode="after")
    @classmethod
    def make_parent(cls, value: Path) -> Path:
        if not value.is_absolute():
            cwd = Path.cwd()
            if cwd.name.lower() == "backend" and (cwd.parent / "data").exists():
                value = cwd.parent / value
        value.parent.mkdir(parents=True, exist_ok=True)
        return value

    @property
    def gemini_enabled(self) -> bool:
        return bool(self.gemini_api_key) and not self.demo_mode and self.llm_provider.lower() == "gemini"

    @property
    def openai_enabled(self) -> bool:
        return bool(self.openai_api_key) and not self.demo_mode and self.llm_provider.lower() == "openai"

    @property
    def hyde_llm_available(self) -> bool:
        """HyDE checks the API key independently of demo_mode.
        This allows Gemini to be used for internal query expansion
        even when demo_mode=True (where it is blocked for answer generation)."""
        if not self.enable_hyde:
            return False
        if self.llm_provider.lower() == "gemini":
            return bool(self.gemini_api_key)
        return bool(self.openai_api_key)

    @property
    def smart_demo_enabled(self) -> bool:
        """True when demo_mode=True but an API key is present.
        Enables real LLM answer generation (Gemini/OpenAI) while keeping
        the lightweight DemoRetriever — no ChromaDB required."""
        if not self.demo_mode:
            return False
        if self.llm_provider.lower() == "gemini":
            return bool(self.gemini_api_key)
        return bool(self.openai_api_key)

    @property
    def active_llm_enabled(self) -> bool:
        return self.gemini_enabled if self.llm_provider.lower() == "gemini" else self.openai_enabled

    @property
    def active_input_cost_per_million(self) -> float:
        if self.llm_provider.lower() == "gemini":
            return self.gemini_input_cost_per_million
        return self.generation_input_cost_per_million

    @property
    def active_output_cost_per_million(self) -> float:
        if self.llm_provider.lower() == "gemini":
            return self.gemini_output_cost_per_million
        return self.generation_output_cost_per_million

    @property
    def active_judge_model(self) -> str:
        if self.llm_provider.lower() == "gemini":
            return self.gemini_judge_model
        return self.openai_judge_model

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
