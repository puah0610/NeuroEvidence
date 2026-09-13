import re
from dataclasses import dataclass

from .models import Intent


SUPPORTED_TERMS = {
    "parkinson": "Parkinson's disease",
    "parkinson's": "Parkinson's disease",
    "epilepsy": "epilepsy",
    "seizure": "epilepsy",
    "stroke": "stroke",
    "cerebrovascular": "stroke",
    "multiple sclerosis": "multiple sclerosis",
    " ms ": "multiple sclerosis",
    "demyelination": "multiple sclerosis",
    "levodopa": "Parkinson's disease",
    "dopaminergic": "Parkinson's disease",
    "electroencephal": "epilepsy",
    "antiseizure": "epilepsy",
    "thrombolysis": "stroke",
    "ischemic": "stroke",
    "haemorrhagic": "stroke",
    "hemorrhagic": "stroke",
    "optic neuritis": "multiple sclerosis",
}

EMERGENCY_PATTERNS = (
    r"\b(?:face|facial) droop(?:ing)?\b",
    r"\bsudden(?:ly)?[^.]{0,35}(?:cannot speak|speech difficulty|slurred speech)\b",
    r"\bnew (?:one-sided )?weakness\b",
    r"\bsudden (?:severe )?headache\b",
    r"\bseizure.{0,25}(?:five|5) minutes\b",
    r"\bnot (?:breathing|responsive)\b",
    r"\bloss of consciousness\b",
    r"\bcall (?:an )?ambulance\b",
    r"\boverdose\b",
)

PERSONAL_PATTERNS = (
    r"\bdo i have\b",
    r"\bdiagnose me\b",
    r"\bshould i (?:take|stop|increase|decrease)\b",
    r"\bmy (?:dose|medication|prescription|symptoms?)\b",
    r"\bwhat medicine should i\b",
    r"\bam i having\b",
)

PROMPT_ATTACK_PATTERNS = (
    r"\bignore (?:all |the )?(?:previous|earlier|system) instructions\b",
    r"\b(?:show|reveal|print|repeat) (?:the |your )?(?:system prompt|api key|secret)\b",
    r"\bdeveloper message\b",
)


@dataclass(frozen=True)
class SafetyDecision:
    intent: Intent
    topic: str | None
    response: str | None = None


def classify_query(question: str) -> SafetyDecision:
    normalized = f" {question.lower().strip()} "

    if any(re.search(pattern, normalized) for pattern in PROMPT_ATTACK_PATTERNS):
        return SafetyDecision(
            Intent.out_of_scope,
            None,
            "I cannot provide private configuration, credentials, or internal instructions. "
            "Please ask an educational question within one of the supported neurology topics.",
        )

    if any(re.search(pattern, normalized) for pattern in EMERGENCY_PATTERNS):
        return SafetyDecision(
            Intent.emergency,
            None,
            "This may describe a medical emergency. Do not rely on this educational assistant. "
            "Contact your local emergency service now or seek immediate in-person medical care. "
            "If it is safe to do so, stay with the affected person and follow the emergency operator's instructions.",
        )

    topic = next(
        (label for term, label in SUPPORTED_TERMS.items() if term in normalized), None
    )
    if any(re.search(pattern, normalized) for pattern in PERSONAL_PATTERNS):
        return SafetyDecision(
            Intent.personal_medical_advice,
            topic,
            "I can explain neurological concepts and research evidence, but I cannot diagnose symptoms "
            "or recommend an individual treatment. Please discuss your situation with a qualified healthcare "
            "professional. If symptoms are sudden, severe, or worsening, seek urgent care.",
        )

    if topic:
        return SafetyDecision(Intent.educational_in_scope, topic)

    return SafetyDecision(
        Intent.out_of_scope,
        None,
        "This research prototype currently covers educational questions about Parkinson's disease, "
        "epilepsy, stroke, and multiple sclerosis. Please rephrase your question within one of those topics.",
    )
