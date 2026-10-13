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
                    return {
                        "drug_a": drug_a,
                        "drug_b": drug_b,
                        "warning_text": " ".join(relevant_sentences[:3]),
                        "source": "openFDA Drug Label API (Official FDA Label)",
                        "has_boxed_warning": bool(boxed_warnings),
                    }
        except (httpx.RequestError, httpx.TimeoutException, Exception) as exc:
            logger.debug(f"openFDA API lookup failed or timed out: {exc}")
            return None

        return None
