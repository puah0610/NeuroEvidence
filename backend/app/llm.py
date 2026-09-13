import re
from dataclasses import dataclass
from typing import Protocol

from openai import OpenAI

from .config import Settings
from .models import RetrievedChunk


class Generator(Protocol):
    model_name: str

    def generate_baseline(self, question: str) -> "GenerationOutput": ...

    def generate_grounded(self, question: str, chunks: list[RetrievedChunk]) -> "GenerationOutput": ...


@dataclass(frozen=True)
class GenerationOutput:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0


class OpenAIAdapter:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.model_name = settings.openai_generation_model
        self.client = OpenAI(api_key=settings.openai_api_key)

    def embed(self, texts: list[str]) -> list[list[float]]:
        result = self.client.embeddings.create(
            model=self.settings.openai_embedding_model, input=texts
        )
        return [item.embedding for item in result.data]

    def generate_baseline(self, question: str) -> GenerationOutput:
        response = self.client.responses.create(
            model=self.model_name,
            instructions=(
                "You are an educational neurology assistant for students and researchers. "
                "Answer clearly, do not diagnose or prescribe, and state uncertainty. This is the plain-LLM "
                "research baseline: do not invent citations and do not claim to have checked external sources."
            ),
            input=question,
        )
        return self._result(response)

    def generate_grounded(self, question: str, chunks: list[RetrievedChunk]) -> GenerationOutput:
        evidence = "\n\n".join(
            f"[S{index}] {chunk.title} — {chunk.section or 'Excerpt'}\n{chunk.excerpt}"
            for index, chunk in enumerate(chunks, start=1)
        )
        response = self.client.responses.create(
            model=self.model_name,
            instructions=(
                "You are an educational neurology research assistant. Answer only from the supplied evidence. "
                "Every paragraph containing a factual claim must end with one or more source markers such as "
                "[S1] or [S1][S2]. Never cite a marker that is not supplied. If the evidence is incomplete, "
                "say exactly what cannot be established. Do not diagnose, prescribe, or turn the evidence score "
                "into medical certainty. Use concise prose suitable for university students."
            ),
            input=f"QUESTION\n{question}\n\nEVIDENCE\n{evidence}",
        )
        return self._result(response)

    @staticmethod
    def _result(response) -> GenerationOutput:
        usage = getattr(response, "usage", None)
        return GenerationOutput(
            text=response.output_text.strip(),
            input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
        )


class DemoGenerator:
    model_name = "bundled-demo-generator"

    def generate_baseline(self, question: str) -> GenerationOutput:
        topic = _topic_label(question)
        text = (
            f"{topic} is a neurological topic with varied clinical features and management approaches. "
            "A careful answer normally considers mechanisms, symptoms, diagnosis, and treatment options.\n\n"
            "This is a simulated plain-model baseline. It has not retrieved or verified evidence, so its factual "
            "claims should not be used for research conclusions or medical decisions."
        )
        return GenerationOutput(text=text)

    def generate_grounded(self, question: str, chunks: list[RetrievedChunk]) -> GenerationOutput:
        if not chunks:
            return GenerationOutput("The indexed collection does not contain enough evidence to answer this question.")
        paragraphs: list[str] = []
        for index, chunk in enumerate(chunks[:2], start=1):
            paragraphs.append(f"{chunk.excerpt} [S{index}]")
        paragraphs.append(
            "This answer summarizes the retrieved educational material; it does not provide an individual "
            "diagnosis or treatment recommendation."
        )
        return GenerationOutput("\n\n".join(paragraphs))


def _topic_label(question: str) -> str:
    normalized = question.lower()
    if "parkinson" in normalized:
        return "Parkinson's disease"
    if "epilep" in normalized or "seizure" in normalized:
        return "Epilepsy"
    if "stroke" in normalized:
        return "Stroke"
    if "multiple sclerosis" in normalized or re.search(r"\bms\b", normalized):
        return "Multiple sclerosis"
    return "This condition"
