import re
from dataclasses import dataclass
from typing import Any, Protocol

from openai import OpenAI

from .config import Settings
from .models import RetrievedChunk


class Generator(Protocol):
    model_name: str

    def generate_baseline(self, question: str) -> "GenerationOutput": ...

    def generate_grounded(
        self, question: str, chunks: list[RetrievedChunk], ddi_report: Any = None
    ) -> "GenerationOutput": ...


@dataclass(frozen=True)
class GenerationOutput:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0


class OpenAIAdapter:
    def __init__(self, settings: Settings, model_name: str | None = None):
        self.settings = settings
        self.model_name = model_name or settings.openai_generation_model
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
                "You are an educational neurology clinical assistant for students and researchers. "
                "Answer clearly and directly like an intelligent assistant, providing a direct answer upfront followed by core clinical concepts.\n\n"
                "Formatting Rules:\n"
                "1. Begin with a '### Main Topic: <Condition/Subject Focus>' heading.\n"
                "2. Provide a 1-2 sentence direct answer addressing the user's question upfront (e.g. core distinction, mechanism, or consensus summary).\n"
                "3. Include a '#### Core Clinical Concepts:' section with structured bullet points (using '• **<Concept Title>:** <details and mechanisms>').\n"
                "4. Do not diagnose or prescribe, and state uncertainty. This is the plain-LLM "
                "research baseline: do not invent citations and do not claim to have checked external sources."
            ),
            input=question,
            temperature=self.settings.llm_temperature,
        )
        return self._result(response)

    def generate_grounded(
        self, question: str, chunks: list[RetrievedChunk], ddi_report: Any = None
    ) -> GenerationOutput:
        evidence = "\n\n".join(
            f"[S{index}] [{chunk.layer_name} | {chunk.layer_source}] {chunk.title} — {chunk.section or 'Excerpt'}\n{chunk.excerpt}"
            for index, chunk in enumerate(chunks, start=1)
        )
        ddi_instruction = ""
        if ddi_report and getattr(ddi_report, "has_interaction", False):
            ddi_instruction = (
                f"\n\n[DRUG INTERACTION ALERT]: The query involves interacting medications: {getattr(ddi_report, 'clinical_summary', '')}. "
                "Explicitly describe pharmacokinetic/pharmacodynamic mechanisms, severity risks, and guideline-recommended dosage titration or contraindications."
            )
        response = self.client.responses.create(
            model=self.model_name,
            instructions=(
                "You are an educational neurology clinical assistant utilizing a 3-Layer Triad Knowledge Base "
                "(Layer 1: Foundational Knowledge from NCBI Bookshelf/StatPearls; Layer 2: Clinical Guidelines "
                "from NICE Guidelines; Layer 3: Empirical Evidence & Trials from PubMed Central/Cochrane).\n\n"
                "Synthesize across foundational pathophysiology, clinical practice guidelines, and empirical clinical trial "
                "evidence from the supplied sources to assist the user clearly, conversationally, and authoritatively.\n\n"
                "Format your response with a direct answer upfront, followed by supporting clinical evidence:\n"
                "1. Title: Begin with '### Main Topic: <Condition/Subject Focus>'.\n"
                "2. Direct Answer: Immediately provide a clear, concise 1-2 sentence straight answer addressing the user's "
                "question upfront (e.g. for a comparison query, state the primary clinical distinction immediately; for a "
                "mechanism query, state the primary physiological pathway; for management, state the first-line consensus). "
                "End this direct answer with the supporting source marker(s) (e.g. [S1] or [S1, S2]).\n"
                "3. Supporting Evidence: Include a '#### Supporting Clinical Evidence:' section with 3 to 4 comprehensive, well-structured clinical bullet points (using '• **<Domain/Focus Title>:**').\n"
                "   Dynamically adapt the clinical domains to the nature of the inquiry and the retrieved evidence:\n"
                "   • For Pharmacological Topics: Cover Primary Indications & Efficacy, Mechanism of Action (if described in sources), Guideline Stepwise Line of Therapy, and Safety/Adverse Effects.\n"
                "   • For Diagnostic & Symptom Topics: Cover Clinical Manifestations & Phenotypes, Diagnostic Criteria & Red Flags, and Assessment or Screening Guidelines.\n"
                "   • For Lifestyle, Physical Therapy & Surgical Interventions: Cover Core Modalities, Functional & Physiological Outcomes, and Clinical Recommendations.\n"
                "   Never force or hallucinate an irrelevant dimension (e.g. do not invent a pharmacological mechanism if the query is about clinical symptoms or guidelines). "
                "   If the evidence contains vital extra information such as drug interactions, contraindications, or dosage cautions, dedicate a distinct bullet point to them.\n"
                "   Each bullet point must highlight a key clinical finding synthesized from the sources and MUST end with its source marker(s) such as [S1] or [S2].\n"
                "4. Conclude with: 'This answer summarizes the retrieved educational material across the 3-Layer Triad; it does not provide an individual diagnosis or treatment recommendation.'\n"
                "5. Assistant Persona: Act as a helpful, authoritative clinical assistant. Directly address the user's inquiry rather than "
                "mechanically describing the limitations of search snippets. Never generate robotic meta-text like 'Status within Provided Evidence'.\n"
                "6. Standard Unicode: NEVER use LaTeX syntax or math dollar signs (do NOT write '$\\alpha$' or '$SNpc$'). "
                "Use clean standard Unicode text (e.g. 'alpha-synuclein' or 'α-synuclein', 'SNpc').\n"
                f"{ddi_instruction}\n"
                "Never cite a marker that is not supplied. Do not diagnose or prescribe."
            ),
            input=f"QUESTION\n{question}\n\nEVIDENCE\n{evidence}",
            temperature=self.settings.llm_temperature,
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


class GeminiAdapter:
    def __init__(self, settings: Settings, model_name: str | None = None):
        self.settings = settings
        self.model_name = model_name or settings.gemini_generation_model
        self.client = OpenAI(
            api_key=settings.gemini_api_key,
            base_url=settings.gemini_base_url,
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        import time
        import re

        if not texts:
            return []

        max_retries = 15
        for attempt in range(max_retries):
            try:
                result = self.client.embeddings.create(
                    model=self.settings.gemini_embedding_model, input=texts
                )
                return [item.embedding for item in result.data]
            except Exception as exc:
                err_str = str(exc)
                if "429" in err_str or "quota" in err_str.lower() or "rate" in err_str.lower() or "resource_exhausted" in err_str.lower():
                    # If batch is large and repeatedly hitting rate limits, halve it to fit the token quota
                    if len(texts) > 8 and attempt >= 2:
                        mid = len(texts) // 2
                        print(f"\n[Gemini Free Tier] Splitting batch of {len(texts)} into two smaller batches of {mid} to fit token quota...", flush=True)
                        time.sleep(2.0)
                        return self.embed(texts[:mid]) + self.embed(texts[mid:])

                    delay = 20.0
                    match = re.search(r"retry\s+in\s+([\d\.]+)\s*s", err_str, re.IGNORECASE)
                    if match:
                        try:
                            delay = float(match.group(1)) + 3.0
                        except ValueError:
                            delay = 25.0
                    else:
                        match2 = re.search(r"retryDelay':\s*'(\d+)s'", err_str)
                        if match2:
                            try:
                                delay = float(match2.group(1)) + 3.0
                            except ValueError:
                                delay = 25.0
                    print(f"\n[Gemini Free Tier Quota] Per-minute token limit reached. Pausing {delay:.1f}s for quota window reset ({attempt + 1}/{max_retries})...", flush=True)
                    time.sleep(delay)
                elif "503" in err_str or "500" in err_str or "unavailable" in err_str.lower():
                    time.sleep(3.0 * (attempt + 1))
                else:
                    raise exc
        raise RuntimeError("Failed to compute embeddings after maximum rate limit retries.")

    def _call_with_retry(self, **kwargs):
        import time

        models_to_try = [self.model_name]
        fallback_candidates = (
            ["gemini-2.5-pro", "gemini-1.5-pro", "gemini-3.6-flash"]
            if "pro" in self.model_name.lower()
            else ["gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-3.8-flash"]
        )
        for candidate in fallback_candidates:
            if candidate not in models_to_try:
                models_to_try.append(candidate)

        last_exc = None
        for model in models_to_try:
            kwargs["model"] = model
            for _ in range(2):
                try:
                    response = self.client.chat.completions.create(**kwargs)
                    self.model_name = model
                    return response
                except Exception as exc:
                    last_exc = exc
                    err_msg = str(exc).lower()
                    if "503" in err_msg or "429" in err_msg or "demand" in err_msg or "unavailable" in err_msg:
                        time.sleep(0.8)
                        continue
                    raise exc
        if last_exc:
            raise last_exc

    def generate_baseline(self, question: str) -> GenerationOutput:
        system_instruction = (
            "You are an educational neurology clinical assistant for students and researchers.\n"
            "Answer clearly and directly like an intelligent assistant, providing a direct answer upfront followed by core clinical concepts.\n\n"
            "Formatting Rules:\n"
            "1. Begin with a '### Main Topic: <Condition/Subject Focus>' heading.\n"
            "2. Provide a 1-2 sentence direct answer addressing the user's question upfront (e.g. core distinction, mechanism, or consensus summary).\n"
            "3. Include a '#### Core Clinical Concepts:' section with structured bullet points (using '• **<Concept Title>:** <details and mechanisms>').\n"
            "   If providing sub-points under a concept, indent them clearly under the concept.\n"
            "4. NEVER use LaTeX syntax or math dollar signs (do NOT write '$\\alpha$' or '$SNpc$'). Always use clean standard Unicode text and medical terms (e.g. write 'alpha-synuclein' or 'α-synuclein', 'SNpc', 'TRAP').\n"
            "5. Do not diagnose or prescribe, and state uncertainty. This is the plain-LLM research baseline: do not invent citations and do not claim to have checked external sources."
        )
        response = self._call_with_retry(
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": question},
            ],
            temperature=self.settings.llm_temperature,
        )
        return self._result(response)

    def generate_grounded(
        self, question: str, chunks: list[RetrievedChunk], ddi_report: Any = None
    ) -> GenerationOutput:
        evidence = "\n\n".join(
            f"[S{index}] [{chunk.layer_name} | {chunk.layer_source}] {chunk.title} — {chunk.section or 'Excerpt'}\n{chunk.excerpt}"
            for index, chunk in enumerate(chunks, start=1)
        )
        ddi_instruction = ""
        if ddi_report and getattr(ddi_report, "has_interaction", False):
            ddi_instruction = (
                f"\n\n[DRUG INTERACTION ALERT]: The query involves interacting medications: {getattr(ddi_report, 'clinical_summary', '')}. "
                "Explicitly describe pharmacokinetic/pharmacodynamic mechanisms, severity risks, and guideline-recommended dosage titration or contraindications."
            )
        system_instruction = (
            "You are an educational neurology clinical assistant utilizing a 3-Layer Triad Knowledge Base "
            "(Layer 1: Foundational Knowledge from NCBI Bookshelf/StatPearls; Layer 2: Clinical Guidelines "
            "from NICE Guidelines; Layer 3: Empirical Evidence & Trials from PubMed Central/Cochrane).\n\n"
            "Synthesize across foundational pathophysiology, clinical practice guidelines, and empirical clinical trial "
            "evidence from the supplied sources to assist the user clearly, conversationally, and authoritatively.\n\n"
            "Format your response with a direct answer upfront, followed by supporting clinical evidence:\n"
            "1. Title: Begin with '### Main Topic: <Condition/Subject Focus>'.\n"
            "2. Direct Answer: Immediately provide a clear, concise 1-2 sentence straight answer addressing the user's "
            "question upfront (e.g. for a comparison query, state the primary clinical distinction immediately; for a "
            "mechanism query, state the primary physiological pathway; for management, state the first-line consensus). "
            "End this direct answer with the supporting source marker(s) (e.g. [S1] or [S1, S2]).\n"
            "3. Supporting Evidence: Include a '#### Supporting Clinical Evidence:' section with 3 to 4 comprehensive, well-structured clinical bullet points (using '• **<Domain/Focus Title>:**').\n"
            "   Dynamically adapt the clinical domains to the nature of the inquiry and the retrieved evidence:\n"
            "   • For Pharmacological Topics: Cover Primary Indications & Efficacy, Mechanism of Action (if described in sources), Guideline Stepwise Line of Therapy, and Safety/Adverse Effects.\n"
            "   • For Diagnostic & Symptom Topics: Cover Clinical Manifestations & Phenotypes, Diagnostic Criteria & Red Flags, and Assessment or Screening Guidelines.\n"
            "   • For Lifestyle, Physical Therapy & Surgical Interventions: Cover Core Modalities, Functional & Physiological Outcomes, and Clinical Recommendations.\n"
            "   Never force or hallucinate an irrelevant dimension (e.g. do not invent a pharmacological mechanism if the query is about clinical symptoms or guidelines). "
            "   If the evidence contains vital extra information such as drug interactions, contraindications, or dosage cautions, dedicate a distinct bullet point to them.\n"
            "   Each bullet point must highlight a key clinical finding synthesized from the sources and MUST end with its source marker(s) such as [S1] or [S2].\n"
            "4. Conclude with: 'This answer summarizes the retrieved educational material across the 3-Layer Triad; it does not provide an individual diagnosis or treatment recommendation.'\n"
            "5. Assistant Persona: Act as a helpful, authoritative clinical assistant. Directly address the user's inquiry rather than "
            "mechanically describing the limitations of search snippets. Never generate robotic meta-text like 'Status within Provided Evidence'.\n"
            "6. Standard Unicode: NEVER use LaTeX syntax or math dollar signs (do NOT write '$\\alpha$' or '$SNpc$'). "
            "Use clean standard Unicode text (e.g. 'alpha-synuclein' or 'α-synuclein', 'SNpc').\n"
            f"{ddi_instruction}\n"
            "Never cite a marker that is not supplied. Do not diagnose or prescribe."
        )
        response = self._call_with_retry(
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": f"QUESTION\n{question}\n\nEVIDENCE\n{evidence}"},
            ],
            temperature=self.settings.llm_temperature,
        )
        return self._result(response)

    @staticmethod
    def _result(response) -> GenerationOutput:
        usage = getattr(response, "usage", None)
        raw_text = response.choices[0].message.content or ""
        cleaned_text = clean_medical_text(raw_text).strip()
        return GenerationOutput(
            text=cleaned_text,
            input_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
        )


GREEK_SYMBOLS = {
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε",
    "zeta": "ζ", "eta": "η", "theta": "θ", "iota": "ι", "kappa": "κ",
    "lambda": "λ", "mu": "μ", "nu": "ν", "xi": "ξ", "pi": "π",
    "rho": "ρ", "sigma": "σ", "tau": "τ", "upsilon": "υ", "phi": "φ",
    "chi": "χ", "psi": "ψ", "omega": "ω",
}


def clean_medical_text(text: str) -> str:
    if not text:
        return ""
    cleaned = text
    for name, sym in GREEK_SYMBOLS.items():
        cleaned = re.sub(rf"\$\\{name}\$|\${name}\$|\\{name}\b", sym, cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\$([A-Za-z0-9_\-\+^/]+)\$", r"\1", cleaned)
    return cleaned


def create_llm_adapter(settings: Settings, model_name: str | None = None) -> OpenAIAdapter | GeminiAdapter:
    if settings.llm_provider.lower() == "gemini":
        return GeminiAdapter(settings, model_name=model_name)
    return OpenAIAdapter(settings, model_name=model_name)


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

    def generate_grounded(
        self, question: str, chunks: list[RetrievedChunk], ddi_report: Any = None
    ) -> GenerationOutput:
        if not chunks:
            return GenerationOutput("The indexed collection does not contain enough evidence to answer this question.")
        topic = _topic_label(question)
        lines: list[str] = [
            f"### Main Topic: {topic} Evidence Overview",
            f"{topic} encompasses foundational pathophysiology, established clinical guidelines, and empirical trial outcomes synthesized across the Triad [S1].",
            "#### Supporting Clinical Evidence:",
        ]
        for index, chunk in enumerate(chunks[:3], start=1):
            category = chunk.subtopic or chunk.section or "Clinical Evidence"
            clean_excerpt = chunk.excerpt
            if clean_excerpt.startswith("### ["):
                parts = clean_excerpt.split("\n\n", 1)
                if len(parts) > 1:
                    clean_excerpt = parts[1].strip()
            # Remove any embedded (Layer X) mentions from excerpt
            clean_excerpt = re.sub(r"\s*\(Layer\s*\d+\)", "", clean_excerpt)
            lines.append(f"• **{category}:** {clean_excerpt} [S{index}]")

        if ddi_report and getattr(ddi_report, "has_interaction", False):
            drugs_str = ", ".join(getattr(ddi_report, "drug_names", []))
            lines.append(
                f"• **Pharmacological Interaction Advisory ({drugs_str}):** {getattr(ddi_report, 'clinical_summary', '')} "
                f"{' '.join(getattr(ddi_report, 'actionable_guidance', []))} [S1]"
            )

        lines.append(
            "This answer summarizes the retrieved educational material across the 3-Layer Triad; it does not provide an individual "
            "diagnosis or treatment recommendation."
        )
        return GenerationOutput("\n\n".join(lines))


def _topic_label(question: str) -> str:
    normalized = question.lower()
    if any(
        term in normalized
        for term in (
            "parkinson", "levodopa", "l-dopa", "sinemet", "madopar",
            "carbidopa", "pramipexole", "ropinirole", "selegiline",
            "rasagiline", "entacapone", "metoclopramide", "haloperidol", "dbs", "hoehn"
        )
    ):
        return "Parkinson's disease"
    if any(
        term in normalized
        for term in (
            "epilep", "seizure", "valproate", "lamotrigine", "levetiracetam",
            "keppra", "lamictal", "carbamazepine", "tegretol", "ethosuximide", "ilae", "sanad"
        )
    ):
        return "Epilepsy"
    if "stroke" in normalized:
        return "Stroke"
    if "multiple sclerosis" in normalized or re.search(r"\bms\b", normalized):
        return "Multiple sclerosis"
    return "Clinical Neurology"
