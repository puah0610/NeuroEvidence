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
                "Answer clearly in structured point form (a main topic followed by bullet points of core clinical concepts). "
                "Do not diagnose or prescribe, and state uncertainty. This is the plain-LLM "
                "research baseline: do not invent citations and do not claim to have checked external sources."
            ),
            input=question,
        )
        return self._result(response)

    def generate_grounded(self, question: str, chunks: list[RetrievedChunk]) -> GenerationOutput:
        evidence = "\n\n".join(
            f"[S{index}] [{chunk.layer_name} | {chunk.layer_source}] {chunk.title} — {chunk.section or 'Excerpt'}\n{chunk.excerpt}"
            for index, chunk in enumerate(chunks, start=1)
        )
        response = self.client.responses.create(
            model=self.model_name,
            instructions=(
                "You are an educational neurology research assistant utilizing a 3-Layer Triad Knowledge Base "
                "(Layer 1: Foundational Knowledge from NCBI Bookshelf/StatPearls; Layer 2: Clinical Guidelines "
                "from NICE Guidelines; Layer 3: Empirical Evidence & Trials from PubMed Central/Cochrane). "
                "Answer only from the supplied evidence. Synthesize across foundational pathophysiology, clinical "
                "practice guidelines, and empirical clinical trial evidence where available.\n\n"
                "Format your response in clean point form like ChatGPT:\n"
                "1. Begin with a '### Main Topic: <Condition/Subject Focus>' heading.\n"
                "2. Include a '#### Supporting Clinical Evidence:' section with distinct bullet points (using '• **<Subtopic/Focus>:**').\n"
                "3. Each bullet point must highlight a key clinical finding synthesized from the sources and MUST end with its source marker(s) such as [S1] or [S2].\n"
                "4. Conclude with: 'This answer summarizes the retrieved educational material across the 3-Layer Triad; it does not provide an individual diagnosis or treatment recommendation.'\n"
                "Never cite a marker that is not supplied. If the evidence is incomplete, state clearly what cannot be established. Do not diagnose or prescribe."
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
        lines = [
            f"### Main Topic: {topic} (Baseline Overview)",
            f"{topic} is a neurological condition with multifaceted clinical features and management protocols.",
            "#### Key Clinical Concepts:",
            "• **Pathophysiology & Neurobiology:** Understanding underlying cellular and anatomical alterations.",
            "• **Diagnostic Evaluation:** Clinical semiology, specialist review, and targeted investigation.",
            "• **Therapeutic Approaches:** Multidisciplinary symptomatic and disease-modifying strategies.",
            "This is a simulated plain-model baseline. It has not retrieved or verified evidence, so its factual "
            "claims should not be used for research conclusions or medical decisions.",
        ]
        return GenerationOutput(text="\n\n".join(lines))

    def generate_grounded(self, question: str, chunks: list[RetrievedChunk]) -> GenerationOutput:
        if not chunks:
            return GenerationOutput("The indexed collection does not contain enough evidence to answer this question.")
        topic = _topic_label(question)
        lines: list[str] = [
            f"### Main Topic: {topic} Evidence Overview",
            "#### Supporting Clinical Evidence:",
        ]
        for index, chunk in enumerate(chunks[:3], start=1):
            category = chunk.subtopic or chunk.section or f"Layer {chunk.layer} Evidence"
            layer_short = chunk.layer_name.split(":")[0].strip() if chunk.layer_name else f"Layer {chunk.layer}"
            lines.append(f"• **{category} ({layer_short}):** {chunk.excerpt} [S{index}]")

        lines.append(
            "This answer summarizes the retrieved educational material across the 3-Layer Triad; it does not provide an individual "
            "diagnosis or treatment recommendation."
        )
        return GenerationOutput("\n\n".join(lines))


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
