"""Asynchronous client for querying live openFDA Drug Label API."""

import logging
import re
from typing import Any

import httpx

logger = logging.getLogger(__name__)

OPENFDA_LABEL_URL = "https://api.fda.gov/drug/label.json"


class ExternalDDIClient:
    """Queries official FDA drug labels for live drug interaction sections and boxed warnings."""

    def __init__(self, timeout: float = 2.5):
        self.timeout = timeout
        self.headers = {"User-Agent": "NeuroEvidence-Research-Agent/1.0 (educational/FYP)"}

    async def fetch_fda_interaction(self, drug_a: str, drug_b: str) -> dict[str, Any] | None:
        """Fetch FDA label drug interaction text between drug_a and drug_b.

        Returns a dict with extracted excerpt, section name, and source URL if found.
        """
        search_query = f'(openfda.generic_name:"{drug_a}" OR openfda.brand_name:"{drug_a}") AND (drug_interactions:"{drug_b}")'
        params = {
            "search": search_query,
            "limit": 1,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
                response = await client.get(OPENFDA_LABEL_URL, params=params)
                if response.status_code != 200:
                    return None

                data = response.json()
                results = data.get("results", [])
                if not results:
                    return None

                label = results[0]
                interactions = label.get("drug_interactions", [])
                boxed_warnings = label.get("boxed_warning", [])
                contraindications = label.get("contraindications", [])

                combined_texts = []
                for text_list in [boxed_warnings, contraindications, interactions]:
                    if text_list and isinstance(text_list, list):
                        combined_texts.extend(text_list)

                # Search for sentences mentioning drug_b
                relevant_sentences = []
                b_pattern = re.compile(rf"\b{re.escape(drug_b)}\b", re.IGNORECASE)
                for section_text in combined_texts:
                    for sentence in re.split(r"(?<=[.!?])\s+", section_text):
                        if b_pattern.search(sentence) and len(sentence.strip()) > 20:
                            relevant_sentences.append(sentence.strip())
                            if len(relevant_sentences) >= 3:
                                break
                    if len(relevant_sentences) >= 3:
                        break

                if relevant_sentences:
                    set_id = label.get("set_id")
                    openfda = label.get("openfda") if isinstance(label.get("openfda"), dict) else {}
                    brand_names = openfda.get("brand_name") or []
                    generic_names = openfda.get("generic_name") or []
                    brand_name = brand_names[0] if isinstance(brand_names, list) and brand_names else None
                    generic_name = generic_names[0] if isinstance(generic_names, list) and generic_names else None
                    label_url = (
                        f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={set_id}"
                        if set_id
                        else f"https://dailymed.nlm.nih.gov/dailymed/search.cfm?labeltype=all&query={drug_a}"
                    )
                    return {
                        "drug_a": drug_a,
                        "drug_b": drug_b,
                        "warning_text": " ".join(relevant_sentences[:3]),
                        "set_id": set_id,
                        "brand_name": brand_name,
                        "generic_name": generic_name,
                        "label_url": label_url,
                        "source": "openFDA / NIH DailyMed (Official FDA Drug Label)",
                        "has_boxed_warning": bool(boxed_warnings),
                    }
        except (httpx.RequestError, httpx.TimeoutException, Exception) as exc:
            logger.debug(f"openFDA API lookup failed or timed out: {exc}")
            return None

        return None
