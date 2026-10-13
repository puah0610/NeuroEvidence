from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class ChatMode(str, Enum):
    baseline = "baseline"
    rag_verified = "rag_verified"


class Intent(str, Enum):
    educational_in_scope = "educational_in_scope"
    out_of_scope = "out_of_scope"
    personal_medical_advice = "personal_medical_advice"
    emergency = "emergency"


class VerificationLabel(str, Enum):
    supported = "supported"
    contradicted = "contradicted"
    insufficient = "insufficient"


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    question: str = Field(min_length=2, max_length=4000)
    mode: ChatMode = ChatMode.rag_verified


from .ddi.models import DDIReport


class SourceRecord(BaseModel):
    source_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    journal: str | None = None
    topic: str
    url: str
    doi: str | None = None
    pmid: str | None = None
    pmcid: str | None = None
    license: str | None = None
    section: str | None = None
    excerpt: str
    demo: bool = False
    layer: int = 1
    layer_name: str = "Layer 1: Foundational Knowledge"
    layer_source: str = "NCBI Bookshelf / StatPearls"
    subtopic: str | None = None
    parent_id: str | None = None
    parent_title: str | None = None
    breadcrumb: list[str] = Field(default_factory=list)


class RetrievedChunk(SourceRecord):
    chunk_id: str
    document_id: str
    relevance: float = Field(ge=0, le=1)


class CitationResult(BaseModel):
    marker: str
    source_id: str
    title: str
    url: str
    doi: str | None = None
    pmid: str | None = None
    pmcid: str | None = None
    metadata_valid: bool
    verification_note: str
    excerpt: str
    layer: int = 1
    layer_name: str = "Layer 1: Foundational Knowledge"
    layer_source: str = "NCBI Bookshelf / StatPearls"
    subtopic: str | None = None
    parent_id: str | None = None
    parent_title: str | None = None
    breadcrumb: list[str] = Field(default_factory=list)


class ClaimCheck(BaseModel):
    claim: str
    citation_markers: list[str] = Field(default_factory=list)
    label: VerificationLabel
    score: float = Field(ge=0, le=1)
    explanation: str


class ChatResponse(BaseModel):
    trace_id: str
    intent: Intent
    mode: ChatMode
    answer: str
    original_answer: str | None = None
    citations: list[CitationResult] = Field(default_factory=list)
    claim_checks: list[ClaimCheck] = Field(default_factory=list)
    evidence_score: float | None = Field(default=None, ge=0, le=1)
    evidence_threshold: float | None = None
    warnings: list[str] = Field(default_factory=list)
    layer_distribution: dict[str, int] = Field(default_factory=dict)
    ddi_report: DDIReport | None = None
    latency_ms: int
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    demo_mode: bool
    created_at: datetime


class FeedbackRequest(BaseModel):
    trace_id: str = Field(min_length=1, max_length=100)
    helpful: bool | None = None
    issue_type: Literal[
        "citation_issue", "unsupported_answer", "safety_issue", "other"
    ] | None = None
    comment: str | None = Field(default=None, max_length=2000)


class FeedbackResponse(BaseModel):
    feedback_id: str
    saved: bool = True


class EvaluationSummary(BaseModel):
    total_traces: int
    by_mode: dict[str, int]
    by_intent: dict[str, int]
    average_evidence_score: float | None
    average_latency_ms: float | None
    total_input_tokens: int
    total_output_tokens: int
    total_estimated_cost_usd: float
    feedback_count: int
    helpful_rate: float | None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    demo_mode: bool
    database: str
    vector_store: str
    generation: str
    nli: str
