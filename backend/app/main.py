from contextlib import asynccontextmanager
from ipaddress import ip_address

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import Database
from .models import (
    ChatRequest,
    ChatResponse,
    EvaluationSummary,
    FeedbackRequest,
    FeedbackResponse,
    HealthResponse,
    SourceRecord,
)
from .service import ChatService


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.langfuse_public_key and settings.langfuse_secret_key:
        import os
        os.environ["LANGFUSE_PUBLIC_KEY"] = settings.langfuse_public_key.strip()
        os.environ["LANGFUSE_SECRET_KEY"] = settings.langfuse_secret_key.strip()
        os.environ["LANGFUSE_HOST"] = settings.langfuse_host.strip()
    database = Database(settings.database_path)
    app.state.settings = settings
    app.state.database = database
    app.state.chat_service = ChatService(settings, database)
    yield


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Educational neurology RAG research API; not a medical device.",
    lifespan=lifespan,
)
cors_origins = list(settings.cors_origin_list)
for o in ("http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "http://127.0.0.1:3000"):
    if o not in cors_origins:
        cors_origins.append(o)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    return await request.app.state.chat_service.chat(payload)


@app.get("/api/sources/{source_id}", response_model=SourceRecord)
async def source(source_id: str, request: Request) -> SourceRecord:
    record = request.app.state.chat_service.get_source(source_id)
    if not record:
        raise HTTPException(status_code=404, detail="Source not found")
    return SourceRecord(**record.model_dump(exclude={"chunk_id", "document_id", "relevance"}))


@app.post("/api/feedback", response_model=FeedbackResponse, status_code=201)
async def feedback(payload: FeedbackRequest, request: Request) -> FeedbackResponse:
    feedback_id = request.app.state.database.save_feedback(payload)
    if payload.trace_id and getattr(request.app.state.settings, "langfuse_enabled", False):
        try:
            from langfuse import get_client
            client = get_client()
            val = 1.0 if payload.rating == "helpful" else 0.0
            client.create_score(
                name="user_feedback",
                value=val,
                trace_id=payload.trace_id,
                comment=payload.comment or None,
                data_type="NUMERIC",
            )
        except Exception as exc:
            import logging
            logging.getLogger(__name__).debug("Langfuse feedback score skipped: %s", exc)
    return FeedbackResponse(feedback_id=feedback_id)


@app.get("/api/evaluation/summary", response_model=EvaluationSummary)
async def evaluation_summary(request: Request) -> EvaluationSummary:
    client_host = request.client.host if request.client else ""
    local = client_host in {"localhost", "testclient"}
    if not local:
        try:
            local = ip_address(client_host).is_loopback or ip_address(client_host).is_private
        except ValueError:
            local = False
    if not local:
        raise HTTPException(status_code=403, detail="This endpoint is restricted to local access")
    return request.app.state.database.summary()


@app.get("/api/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    current = request.app.state.settings
    if current.demo_mode:
        gen_status = "demo"
    elif current.gemini_enabled:
        gen_status = "gemini:configured"
    elif current.openai_enabled:
        gen_status = "openai:configured"
    else:
        gen_status = "missing-key"

    return HealthResponse(
        status="ok" if current.demo_mode or current.active_llm_enabled else "degraded",
        demo_mode=current.demo_mode,
        database="sqlite:ready",
        vector_store="bundled-demo" if current.demo_mode else "chromadb:configured",
        generation=gen_status,
        nli="lexical-demo" if not current.enable_nli else current.nli_model,
    )


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": settings.app_name, "docs": "/docs", "disclaimer": "Educational use only"}
