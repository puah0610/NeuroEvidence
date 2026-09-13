from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

from .config import Settings
from .database import Database
from .llm import DemoGenerator, Generator, OpenAIAdapter
from .models import ChatRequest, ChatResponse, Intent
from .retrieval import ChromaRetriever, DemoRetriever
from .safety import classify_query
from .verification import CitationVerifier, make_nli, verify_answer


class ChatService:
    def __init__(self, settings: Settings, database: Database):
        self.settings = settings
        self.database = database
        if not settings.demo_mode and not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required when DEMO_MODE=false")
        if settings.openai_enabled:
            adapter = OpenAIAdapter(settings)
            self.generator: Generator = adapter
            self.retriever = ChromaRetriever(settings, adapter)
        else:
            self.generator = DemoGenerator()
            self.retriever = DemoRetriever(settings)
        self.citation_verifier = CitationVerifier(settings)
        self.nli = make_nli(settings)

    async def chat(self, request: ChatRequest) -> ChatResponse:
        started = perf_counter()
        trace_id = str(uuid4())
        decision = classify_query(request.question)

        if decision.intent != Intent.educational_in_scope:
            result = ChatResponse(
                trace_id=trace_id,
                intent=decision.intent,
                mode=request.mode,
                answer=decision.response or "This question cannot be answered by the current system.",
                warnings=["Safety or scope guardrail applied."],
                latency_ms=_elapsed_ms(started),
                model="safety-rules-v1",
                demo_mode=self.settings.demo_mode,
                created_at=datetime.now(UTC),
            )
            self.database.save_trace(request.session_id, request.question, result)
            return result

        if request.mode.value == "baseline":
            generation = self.generator.generate_baseline(request.question)
            answer = generation.text
            result = ChatResponse(
                trace_id=trace_id,
                intent=decision.intent,
                mode=request.mode,
                answer=answer,
                warnings=["Baseline mode does not retrieve or verify evidence."],
                latency_ms=_elapsed_ms(started),
                model=self.generator.model_name,
                input_tokens=generation.input_tokens,
                output_tokens=generation.output_tokens,
                estimated_cost_usd=self._cost(generation.input_tokens, generation.output_tokens),
                demo_mode=self.settings.demo_mode,
                created_at=datetime.now(UTC),
            )
            self.database.save_trace(request.session_id, request.question, result)
            return result

        chunks = self.retriever.search(request.question, decision.topic)
        if not chunks:
            answer = (
                "The indexed collection does not contain enough evidence to answer this question. "
                "Try a narrower question within the supported topic."
            )
            result = ChatResponse(
                trace_id=trace_id,
                intent=decision.intent,
                mode=request.mode,
                answer=answer,
                evidence_score=0.0,
                evidence_threshold=self.settings.evidence_threshold,
                warnings=["Retrieval returned no usable evidence."],
                latency_ms=_elapsed_ms(started),
                model=self.generator.model_name,
                demo_mode=self.settings.demo_mode,
                created_at=datetime.now(UTC),
            )
            self.database.save_trace(request.session_id, request.question, result)
            return result

        generation = self.generator.generate_grounded(request.question, chunks)
        original_answer = generation.text
        verification = await verify_answer(
            original_answer,
            chunks,
            self.citation_verifier,
            self.nli,
            self.settings.evidence_threshold,
        )
        answer = original_answer
        if verification.evidence_score < self.settings.evidence_threshold or any(
            item.label.value == "contradicted" for item in verification.claims
        ):
            answer = (
                "The retrieved material was not strong enough to produce a fully verified answer. "
                "The draft and its verification details are retained below for research inspection.\n\n"
                + original_answer
            )

        result = ChatResponse(
            trace_id=trace_id,
            intent=decision.intent,
            mode=request.mode,
            answer=answer,
            original_answer=original_answer if answer != original_answer else None,
            citations=verification.citations,
            claim_checks=verification.claims,
            evidence_score=verification.evidence_score,
            evidence_threshold=self.settings.evidence_threshold,
            warnings=verification.warnings,
            latency_ms=_elapsed_ms(started),
            model=self.generator.model_name,
            input_tokens=generation.input_tokens,
            output_tokens=generation.output_tokens,
            estimated_cost_usd=self._cost(generation.input_tokens, generation.output_tokens),
            demo_mode=self.settings.demo_mode,
            created_at=datetime.now(UTC),
        )
        self.database.save_trace(request.session_id, request.question, result)
        return result

    def get_source(self, source_id: str):
        return self.retriever.get_source(source_id)

    def _cost(self, input_tokens: int, output_tokens: int) -> float:
        value = (
            input_tokens * self.settings.generation_input_cost_per_million
            + output_tokens * self.settings.generation_output_cost_per_million
        ) / 1_000_000
        return round(value, 6)


def _elapsed_ms(started: float) -> int:
    return max(1, round((perf_counter() - started) * 1000))
