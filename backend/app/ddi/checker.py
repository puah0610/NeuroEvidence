"""DDI Engine orchestrator: entity extraction, pairwise matching, and live openFDA integration."""

import asyncio
import re
from functools import lru_cache

from .client import ExternalDDIClient
from .models import DDIInteraction, DDIReport, DDISeverity, DrugEntity
from .registry import DDI_RULES, DRUG_ENTITIES

SEVERITY_ORDER = {
    DDISeverity.contraindicated: 5,
    DDISeverity.major: 4,
    DDISeverity.moderate: 3,
    DDISeverity.minor: 2,
    DDISeverity.info: 1,
}


class DDIChecker:
    """Detects drugs mentioned in clinical queries, evaluates interactions, and fetches FDA warnings."""

    def __init__(self, fda_client: ExternalDDIClient | None = None):
        self.fda_client = fda_client or ExternalDDIClient()
        self._build_alias_patterns()

    def _build_alias_patterns(self) -> None:
        """Compile regex patterns for robust word-boundary matching."""
        self.patterns: list[tuple[re.Pattern, DrugEntity]] = []
        for entity in DRUG_ENTITIES.values():
            for alias in entity.aliases:
                # Word boundary match, case-insensitive
                escaped = re.escape(alias)
                pattern = re.compile(rf"\b{escaped}\b", re.IGNORECASE)
                self.patterns.append((pattern, entity))

    def extract_drugs(self, query: str) -> list[DrugEntity]:
        """Extract all unique drug entities mentioned in the query."""
        found: dict[str, DrugEntity] = {}
        for pattern, entity in self.patterns:
            if pattern.search(query):
                found[entity.canonical_id] = entity
        return list(found.values())

    async def analyze_query(self, query: str, check_live_api: bool = True) -> DDIReport:
        """Scan clinical query for drug interactions, fetching both local guidance and live FDA warnings."""
        drugs = self.extract_drugs(query)
        if len(drugs) < 2:
            # Also check if query mentions 1 drug and mentions "interaction" or "interact" or "contraindicated"
            has_interaction_kw = bool(
                re.search(
                    r"\b(interact\w*|contraindicat\w*|compatib\w*|together|combin\w*|co-prescrib\w*)\b",
                    query,
                    re.IGNORECASE,
                )
            )
            return DDIReport(
                has_interaction=False,
                drugs_detected=[d.canonical_id for d in drugs],
                drug_names=[d.name for d in drugs],
                interactions_found=[],
                clinical_summary=(
                    f"Identified {drugs[0].name} in query. Specify a second medication to check for drug-drug interactions."
                    if drugs and has_interaction_kw
                    else ""
                ),
                actionable_guidance=[],
                source="curated_local",
            )

        interactions_found: list[DDIInteraction] = []
        for i in range(len(drugs)):
            for j in range(i + 1, len(drugs)):
                d1, d2 = drugs[i], drugs[j]
                match = self._find_interaction_rule(d1.canonical_id, d2.canonical_id)
                if match:
                    interactions_found.append(match)

        # Call live openFDA API asynchronously for top pairs
        live_warnings: list[str] = []
        if check_live_api and interactions_found:
            tasks = [
                self.fda_client.fetch_fda_interaction(item.drug_a, item.drug_b)
                for item in interactions_found[:2]
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, dict) and res.get("warning_text"):
                    live_warnings.append(
                        f"FDA Label ({res['drug_a'].title()} + {res['drug_b'].title()}): {res['warning_text']}"
                    )

        has_interaction = len(interactions_found) > 0 or len(live_warnings) > 0

        highest_severity: DDISeverity | None = None
        if interactions_found:
            highest_severity = max(
                (item.severity for item in interactions_found),
                key=lambda s: SEVERITY_ORDER.get(s, 0),
            )

        guidelines = [item.actionable_guidance for item in interactions_found if item.actionable_guidance]
        summary_parts = [item.clinical_effect for item in interactions_found if item.clinical_effect]

        clinical_summary = " ".join(summary_parts)
        if not clinical_summary and has_interaction:
            clinical_summary = f"Detected potential clinical interaction between {', '.join(d.name for d in drugs)}."

        source = "hybrid" if live_warnings else "curated_local"

        return DDIReport(
            has_interaction=has_interaction,
            drugs_detected=[d.canonical_id for d in drugs],
            drug_names=[d.name for d in drugs],
            interactions_found=interactions_found,
            highest_severity=highest_severity,
            clinical_summary=clinical_summary,
            actionable_guidance=guidelines,
            live_fda_warnings=live_warnings,
            source=source,
        )

    def _find_interaction_rule(self, drug_a: str, drug_b: str) -> DDIInteraction | None:
        """Find local rule for pair regardless of argument ordering."""
        for rule in DDI_RULES:
            if (rule.drug_a == drug_a and rule.drug_b == drug_b) or (
                rule.drug_a == drug_b and rule.drug_b == drug_a
            ):
                return rule
        return None


@lru_cache
def get_ddi_checker() -> DDIChecker:
    return DDIChecker()
