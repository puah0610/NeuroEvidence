from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field


class DDISeverity(str, Enum):
    contraindicated = "contraindicated"
    major = "major"
    moderate = "moderate"
    minor = "minor"
    info = "info"


class InteractionMechanism(str, Enum):
    pharmacokinetic = "pharmacokinetic"
    pharmacodynamic = "pharmacodynamic"
    unknown = "unknown"


class DrugEntity(BaseModel):
    canonical_id: str
    name: str
    drug_class: str
    condition: str
    aliases: list[str] = Field(default_factory=list)


class DDIInteraction(BaseModel):
    drug_a: str
    drug_b: str
    drug_a_name: str
    drug_b_name: str
    severity: DDISeverity
    mechanism_type: InteractionMechanism
    mechanism_detail: str
    clinical_effect: str
    actionable_guidance: str
    source: str = "NICE Guidelines / BNF"
    evidence_layer: int = 2


class DDIReport(BaseModel):
    has_interaction: bool = False
    drugs_detected: list[str] = Field(default_factory=list)
    drug_names: list[str] = Field(default_factory=list)
    interactions_found: list[DDIInteraction] = Field(default_factory=list)
    highest_severity: DDISeverity | None = None
    clinical_summary: str = ""
    actionable_guidance: list[str] = Field(default_factory=list)
    live_fda_warnings: list[str] = Field(default_factory=list)
    source: Literal["openfda_live", "curated_local", "hybrid"] = "curated_local"
