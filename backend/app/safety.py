import re
from dataclasses import dataclass

from .models import Intent


SUPPORTED_TERMS = {
    # Parkinson's disease cardinal symptoms & clinical entities
    "parkinson": "Parkinson's disease",
    "parkinson's": "Parkinson's disease",
    "parkinsonian": "Parkinson's disease",
    "parkinsonism": "Parkinson's disease",
    "bradykinesia": "Parkinson's disease",
    "bradykinetic": "Parkinson's disease",
    "hypokinesia": "Parkinson's disease",
    "akinesia": "Parkinson's disease",
    "rigidity": "Parkinson's disease",
    "cogwheel": "Parkinson's disease",
    "lead-pipe": "Parkinson's disease",
    "resting tremor": "Parkinson's disease",
    "rest tremor": "Parkinson's disease",
    "postural instability": "Parkinson's disease",
    "freezing of gait": "Parkinson's disease",
    "festination": "Parkinson's disease",
    "festinating": "Parkinson's disease",
    "micrographia": "Parkinson's disease",
    "dyskinesia": "Parkinson's disease",
    "motor fluctuation": "Parkinson's disease",
    "motor fluctuations": "Parkinson's disease",
    "wearing off": "Parkinson's disease",
    "wearing-off": "Parkinson's disease",
    "levodopa": "Parkinson's disease",
    "carbidopa": "Parkinson's disease",
    "benserazide": "Parkinson's disease",
    "substantia nigra": "Parkinson's disease",
    "striatum": "Parkinson's disease",
    "striatal": "Parkinson's disease",
    "lewy body": "Parkinson's disease",
    "lewy bodies": "Parkinson's disease",
    "alpha-synuclein": "Parkinson's disease",
    "hoehn": "Parkinson's disease",
    "deep brain stimulation": "Parkinson's disease",
    "dbs": "Parkinson's disease",
    "comt": "Parkinson's disease",
    "mao-b": "Parkinson's disease",
    "maob": "Parkinson's disease",
    "ng71": "Parkinson's disease",
    "selegiline": "Parkinson's disease",
    "rasagiline": "Parkinson's disease",
    "safinamide": "Parkinson's disease",
    "entacapone": "Parkinson's disease",
    "opicapone": "Parkinson's disease",
    "tolcapone": "Parkinson's disease",
    "pramipexole": "Parkinson's disease",
    "ropinirole": "Parkinson's disease",
    "rotigotine": "Parkinson's disease",
    "apomorphine": "Parkinson's disease",
    "amantadine": "Parkinson's disease",
    "trihexyphenidyl": "Parkinson's disease",
    "metoclopramide": "Parkinson's disease",
    "haloperidol": "Parkinson's disease",
    "dopamine agonist": "Parkinson's disease",
    "dopaminergic": "Parkinson's disease",

    # Epilepsy cardinal symptoms & clinical entities
    "epilepsy": "epilepsy",
    "epileptic": "epilepsy",
    "seizure": "epilepsy",
    "seizures": "epilepsy",
    "status epilepticus": "epilepsy",
    "absence seizure": "epilepsy",
    "tonic-clonic": "epilepsy",
    "myoclonic": "epilepsy",
    "atonic": "epilepsy",
    "focal seizure": "epilepsy",
    "focal onset": "epilepsy",
    "generalized seizure": "epilepsy",
    "sanad": "epilepsy",
    "ng217": "epilepsy",
    "ilae": "epilepsy",
    "electroencephal": "epilepsy",
    "eeg": "epilepsy",
    "antiseizure": "epilepsy",
    "anticonvulsant": "epilepsy",
    "epileptogenesis": "epilepsy",
    "convulsion": "epilepsy",
    "convulsions": "epilepsy",
    "convulsive": "epilepsy",
    "ictal": "epilepsy",
    "postictal": "epilepsy",
    "interictal": "epilepsy",
    "spasm": "epilepsy",
    "spasms": "epilepsy",
    "infantile spasms": "epilepsy",
    "iess": "epilepsy",
    "levetiracetam": "epilepsy",
    "lamotrigine": "epilepsy",
    "valproate": "epilepsy",
    "carbamazepine": "epilepsy",
    "oxcarbazepine": "epilepsy",
    "ethosuximide": "epilepsy",
    "vigabatrin": "epilepsy",
    "acth": "epilepsy",
    "topiramate": "epilepsy",
    "zonisamide": "epilepsy",
    "clobazam": "epilepsy",
    "lacosamide": "epilepsy",
    "brivaracetam": "epilepsy",
    "cannabidiol": "epilepsy",
    "epidiolex": "epilepsy",
    "dravet": "epilepsy",
    "lennox-gastaut": "epilepsy",
    "west syndrome": "epilepsy",
}


def _term_matches(term: str, text: str) -> bool:
    """Match term in normalized text. Use whole-word regex for short acronyms/terms."""
    if len(term) <= 3:
        return bool(re.search(r"\b" + re.escape(term.strip()) + r"\b", text))
    return term in text


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

FABRICATION_COMMAND_PATTERNS = (
    r"\b(?:invent|fabricate|make up|forge|hallucinate|generate fake|fake)\b.*?\b(?:reference|references|citation|citations|source|sources|study|studies|trial|trials|evidence|data|paper|papers)\b",
    r"\bignore\b.*?\b(?:evidence|grounding|citation|retrieval)\b.*?\b(?:rules?|requirements?|constraints?|instructions?)\b",
    r"\b(?:create|provide|produce)\b.*?\b(?:fake|fictitious|falsified)\b.*?\b(?:references?|citations?|sources?|papers?|study|studies|trials?)\b",
)


@dataclass(frozen=True)
class SafetyDecision:
    intent: Intent
    topic: str | None
    response: str | None = None
    has_adversarial_fabrication: bool = False
    cleaned_educational_query: str | None = None


def extract_educational_inquiry(question: str, topic: str | None) -> str | None:
    """If the question contains an adversarial/fabrication command alongside a legitimate educational inquiry,
    returns the cleaned educational inquiry string.
    Returns None if the request is an explicit fabrication request without educational substance.
    """
    if not topic:
        return None

    cleaned = question
    strip_patterns = [
        r"\bignore\b.*?\b(?:rules?|requirements?|constraints?|instructions?)\b\s*(?:and\s+)?",
        r"\b(?:and\s+)?(?:please\s+)?(?:invent|fabricate|make up|forge|hallucinate|generate fake|fake)\b.*?\b(?:references?|citations?|sources?|papers?|study|studies|trials?|evidence|data)\b\s*",
        r"\b(?:and\s+)?(?:please\s+)?(?:create|provide|produce)\b.*?\b(?:fake|fictitious|falsified)\b.*?\b(?:references?|citations?|sources?|papers?|study|studies|trials?)\b\s*",
        r"\b(?:prove|proving|show|showing)\s+(?:that\s+)?",
        r"\b(?:also\s+)?(?:about\s+it|about\s+this|on\s+it)\b",
        r"^(?:questions?|prompt|user query)\s*[:\-]\s*",
    ]
    for pat in strip_patterns:
        cleaned = re.sub(pat, " ", cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # If all that remains is a trivial prepositional phrase (e.g. "for epilepsy", "about parkinson's") or empty:
    rem_words = [w for w in re.findall(r"[a-z0-9]+", cleaned.lower())]
    trivial_words = {
        "for", "about", "on", "in", "with", "of", "to", "the", "a", "an", "and", "or",
        "s", "regarding", "concerning", "related", "parkinson", "parkinson's", "disease",
        "epilepsy", "seizure", "seizures", "can", "you", "please", "me"
    }
    substantive_words = [w for w in rem_words if len(w) > 1 and w not in trivial_words]

    if not substantive_words:
        return None

    return cleaned


ANAPHORIC_MARKERS = frozenset({
    "that", "this", "these", "those", "it", "they", "them", "which", "their", "its", "same", "such",
    "comparison", "compare", "difference", "differences", "different", "distinction", "distinguish",
    "elaborate", "further", "again", "whose", "neither", "either", "former", "latter",
})

CLINICAL_FOLLOWUP_TERMS = frozenset({
    "guideline", "guidelines", "recommendation", "recommendations", "treatment", "treatments",
    "medication", "medications", "drug", "drugs", "trial", "trials", "study", "studies",
    "evidence", "support", "supports", "mechanism", "mechanisms", "criteria", "classification",
    "contraindication", "contraindications", "prognosis", "remission", "failure", "algorithm",
    "firstline", "first-line", "second-line", "side", "effect", "effects", "adverse", "dosage", "dose",
    "dosing", "efficacy", "safety", "therapy", "therapies", "patient", "patients", "syndrome", "phenotype",
    "semiology", "management",
})


def extract_active_topic_from_history(history: list[dict[str, str]] | None) -> str | None:
    if not history:
        return None
    for msg in reversed(history):
        content = (msg.get("content") or msg.get("text") or "").strip()
        if not content:
            continue
        norm = f" {content.lower()} "
        hist_topic = next(
            (label for term, label in SUPPORTED_TERMS.items() if _term_matches(term, norm)), None
        )
        if hist_topic:
            return hist_topic
    return None


def classify_query(
    question: str, history: list[dict[str, str]] | None = None
) -> SafetyDecision:
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
        (label for term, label in SUPPORTED_TERMS.items() if _term_matches(term, normalized)), None
    )

    # Conversational memory: Inherit active topic for contextual follow-up inquiries
    if not topic and history:
        history_topic = extract_active_topic_from_history(history)
        if history_topic:
            tokens = set(re.findall(r"[a-z0-9\-]+", question.lower()))
            has_followup_signal = bool(
                (tokens & ANAPHORIC_MARKERS) or (tokens & CLINICAL_FOLLOWUP_TERMS)
            )
            if has_followup_signal:
                topic = history_topic

    # Check for adversarial fabrication or constraint-bypass commands
    if any(re.search(pattern, normalized) for pattern in FABRICATION_COMMAND_PATTERNS):
        cleaned_inquiry = extract_educational_inquiry(question, topic)
        if cleaned_inquiry is None:
            # Option 1: Explicit fabrication request without legitimate educational inquiry -> Immediate guardrail refusal
            return SafetyDecision(
                Intent.out_of_scope,
                None,
                "I cannot fabricate citations, invent fictional references, or bypass evidence grounding requirements. "
                "Please ask an educational question about verifiable clinical evidence in Parkinson's disease or epilepsy.",
                has_adversarial_fabrication=True,
            )
        # Option 2: Mixed prompt containing a legitimate educational question alongside fabrication command
        # Allow through to retrieval and generation, with explicit in-answer rejection
        return SafetyDecision(
            Intent.educational_in_scope,
            topic,
            has_adversarial_fabrication=True,
            cleaned_educational_query=cleaned_inquiry,
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
        "This research prototype currently covers educational questions about Parkinson's disease "
        "and epilepsy. Please rephrase your question within one of those topics.",
    )
