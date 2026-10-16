"""Agentic Live PubMed Retrieval and Neural Reranking Engine.

This module provides real-time fallback retrieval from NCBI PubMed using E-utilities
(esearch.fcgi and efetch.fcgi). It extracts PICO clinical entities, enforces high-precision
clinical pre-rules (clinical trials, systematic reviews, humans, 2015+), and executes
neural cross-encoder re-ranking to target the exact empirical evidence required by the user.
"""

import logging
import re
import xml.etree.ElementTree as ET
from typing import Any

import httpx

from .config import Settings
from .models import RetrievedChunk
from .retrieval import NeuralReranker

logger = logging.getLogger(__name__)

# Mandatory Strategy A Clinical Pre-Rules established for empirical Layer 3 evidence
PRE_RULE_FILTERS = (
    "(clinical trial[Filter] OR systematic review[Filter] OR meta-analysis[Filter] OR practice guideline[Filter]) "
    "AND humans[Filter] AND 2015:3000[dp]"
)

# Known neurological conditions and MeSH representations
CONDITION_MESH_MAP = {
    "parkinson's disease": '"Parkinson Disease"[MeSH Terms]',
    "parkinson disease": '"Parkinson Disease"[MeSH Terms]',
    "parkinson's": '"Parkinson Disease"[MeSH Terms]',
    "parkinson": '"Parkinson Disease"[MeSH Terms]',
    "epilepsy": '"Epilepsy"[MeSH Terms]',
    "seizure": '"Seizures"[MeSH Terms]',
    "seizures": '"Seizures"[MeSH Terms]',
    "stroke": '"Stroke"[MeSH Terms]',
    "multiple sclerosis": '"Multiple Sclerosis"[MeSH Terms]',
}

# Recognized neurology therapeutics for precision entity matching
NEURO_DRUG_NAMES = [
    # Parkinson's therapeutics
    "levodopa", "carbidopa", "benserazide", "pramipexole", "ropinirole",
    "rotigotine", "apomorphine", "amantadine", "rasagiline", "selegiline",
    "safinamide", "entacapone", "opicapone", "tolcapone", "trihexyphenidyl",
    # Epilepsy therapeutics
    "valproate", "sodium valproate", "valproic acid", "lamotrigine", "levetiracetam",
    "carbamazepine", "oxcarbazepine", "eslicarbazepine", "lacosamide", "topiramate",
    "zonisamide", "brivaracetam", "clobazam", "ethosuximide", "phenytoin",
    "phenobarbital", "cannabidiol", "cenobamate", "perampanel", "gabapentin", "pregabalin",
    # Interventional procedures
    "deep brain stimulation", "vagus nerve stimulation", "subthalamic nucleus", "globus pallidus",
]

# Clinical symptom and outcome keywords
CLINICAL_SYMPTOM_KEYWORDS = [
    "dyskinesia", "dyskinesias", "wearing-off", "motor fluctuations", "tremor",
    "freezing of gait", "orthostatic hypotension", "hallucinations", "psychosis",
    "nausea", "focal seizures", "generalized seizures", "absence seizures",
    "myoclonic", "status epilepticus", "drug-resistant", "refractory",
    "monotherapy", "adjunctive", "teratogenicity", "pregnancy", "stevens-johnson",
    "somnolence", "cognitive impairment", "adverse events", "efficacy",
]


def extract_clinical_entities(question: str, topic: str | None = None) -> tuple[str, list[str], list[str]]:
    """Extract condition MeSH terms, intervention names, and clinical outcome terms from query."""
    q_lower = question.lower()

    # 1. Detect condition
    detected_condition = ""
    for cond_key, mesh in CONDITION_MESH_MAP.items():
        if cond_key in q_lower:
            detected_condition = mesh
            break

    if not detected_condition and topic:
        detected_condition = CONDITION_MESH_MAP.get(topic.lower(), f'"{topic}"[MeSH Terms]')

    if not detected_condition:
        detected_condition = '"Nervous System Diseases"[MeSH Terms]'

    # 2. Detect interventions
    interventions: list[str] = []
    for drug in NEURO_DRUG_NAMES:
        pattern = rf"\b{re.escape(drug)}\b"
        if re.search(pattern, q_lower):
            interventions.append(drug)

    # 3. Detect outcomes / symptoms
    outcomes: list[str] = []
    for sym in CLINICAL_SYMPTOM_KEYWORDS:
        pattern = rf"\b{re.escape(sym)}\b"
        if re.search(pattern, q_lower):
            outcomes.append(sym)

    return detected_condition, interventions, outcomes


def build_clinical_pubmed_query(question: str, topic: str | None = None) -> str:
    """Build a structured PubMed boolean search query combining extracted entities and pre-rules."""
    condition_mesh, interventions, outcomes = extract_clinical_entities(question, topic)

    query_parts: list[str] = [condition_mesh]

    # Combine interventions and outcomes
    specific_terms: list[str] = []
    for drug in interventions:
        specific_terms.append(f'"{drug}"[Title/Abstract]')
    for outcome in outcomes:
        specific_terms.append(f'"{outcome}"[Title/Abstract]')

    if specific_terms:
        # Group specific terms with OR or AND depending on density
        if len(specific_terms) == 1:
            query_parts.append(specific_terms[0])
        elif len(interventions) >= 1 and len(outcomes) >= 1:
            # Match drug AND outcome for high targeting precision
            drug_clause = " OR ".join(f'"{d}"[Title/Abstract]' for d in interventions)
            outcome_clause = " OR ".join(f'"{o}"[Title/Abstract]' for o in outcomes)
            query_parts.append(f"({drug_clause})")
            query_parts.append(f"({outcome_clause})")
        else:
            joined = " OR ".join(specific_terms)
            query_parts.append(f"({joined})")
    else:
        # Fallback to key substantive words from question (>3 letters, ignoring stopwords)
        words = re.findall(r"\b[A-Za-z]{4,}\b", question.lower())
        stopwords = {
            "what", "when", "where", "which", "with", "from", "that", "this",
            "have", "been", "patient", "patients", "treatment", "therapy",
            "clinical", "evidence", "guidelines", "disease", "disorder",
        }
        substantive = [w for w in words if w not in stopwords][:3]
        if substantive:
            kw_clause = " OR ".join(f'"{w}"[Title/Abstract]' for w in substantive)
            query_parts.append(f"({kw_clause})")

    # Append mandatory empirical Layer 3 pre-rules
    query_parts.append(PRE_RULE_FILTERS)
    return " AND ".join(query_parts)


def _text(element: ET.Element | None) -> str:
    return "" if element is None else "".join(element.itertext()).strip()


def parse_pubmed_xml_article(article_elem: ET.Element, fallback_topic: str = "neurology") -> RetrievedChunk | None:
    """Parse a single PubmedArticle XML node into a RetrievedChunk object."""
    try:
        medline = article_elem.find(".//MedlineCitation")
        if medline is None:
            return None

        pmid_el = medline.find(".//PMID")
        pmid = _text(pmid_el)
        if not pmid:
            return None

        article = medline.find(".//Article")
        if article is None:
            return None

        title_el = article.find(".//ArticleTitle")
        title = _text(title_el)
        if not title:
            return None

        # Extract abstract paragraphs
        abstract_nodes = article.findall(".//Abstract/AbstractText")
        abstract_parts: list[str] = []
        for ab in abstract_nodes:
            label = ab.attrib.get("Label")
            txt = _text(ab)
            if txt:
                if label:
                    abstract_parts.append(f"{label}: {txt}")
                else:
                    abstract_parts.append(txt)

        if not abstract_parts:
            # Without abstract, cannot be used for clinical RAG verification
            return None

        excerpt = " ".join(abstract_parts)
        excerpt = re.sub(r"\s+", " ", excerpt).strip()

        # Extract Journal & PubDate
        journal_el = article.find(".//Journal/Title")
        if journal_el is None:
            journal_el = article.find(".//Journal/ISOAbbreviation")
        journal = _text(journal_el) or "PubMed Central Clinical Evidence"

        year_el = article.find(".//JournalIssue/PubDate/Year")
        if year_el is None:
            year_el = article.find(".//JournalIssue/PubDate/MedlineDate")
        year_str = _text(year_el)
        year_match = re.search(r"\b(20\d{2}|19\d{2})\b", year_str)
        year = int(year_match.group(0)) if year_match else 2024

        # Extract Authors
        authors: list[str] = []
        for author in article.findall(".//AuthorList/Author"):
            last = _text(author.find("LastName"))
            fore = _text(author.find("ForeName"))
            if last and fore:
                authors.append(f"{last} {fore}")
            elif last:
                authors.append(last)

        # Extract Identifiers (DOI, PMCID)
        doi = None
        pmcid = None
        for art_id in article_elem.findall(".//PubmedData/ArticleIdList/ArticleId"):
            id_type = art_id.attrib.get("IdType", "").lower()
            val = _text(art_id)
            if id_type == "doi":
                doi = val
            elif id_type in ("pmc", "pmcid"):
                pmcid = val if val.upper().startswith("PMC") else f"PMC{val}"

        url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        if pmcid:
            url = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/"

        topic_lower = fallback_topic.lower()
        if "epilep" in topic_lower or "seizure" in topic_lower or "epilep" in title.lower() or "seizure" in title.lower():
            topic_label = "epilepsy"
        else:
            topic_label = "Parkinson's disease"

        chunk_id = f"PUBMED-LIVE-{pmid}"
        return RetrievedChunk(
            chunk_id=chunk_id,
            document_id=chunk_id,
            source_id=chunk_id,
            title=title,
            authors=authors[:5],
            year=year,
            journal=journal,
            topic=topic_label,
            url=url,
            doi=doi,
            pmid=pmid,
            pmcid=pmcid,
            license="Open Access / PubMed NLM",
            section="Clinical Trial Abstract",
            excerpt=excerpt,
            relevance=0.5,
            demo=False,
            layer=3,
            layer_name="Layer 3: Empirical Evidence & Trials",
            layer_source="PubMed Central / Clinical Trials (Live API)",
            subtopic="Live PubMed Discovery",
            parent_id=chunk_id,
            parent_title=title,
            breadcrumb=["Layer 3", topic_label.title(), "Live Empirical Evidence", title[:45] + "..."],
        )
    except Exception as exc:
        logger.debug("Failed to parse PubMed article XML: %s", exc)
        return None


class LivePubMedRetriever:
    """Agentic PubMed Retriever that queries NCBI E-utilities live and applies neural reranking."""

    def __init__(self, settings: Settings, generator: Any = None, reranker: NeuralReranker | None = None):
        self.settings = settings
        self.generator = generator
        self.reranker = reranker or NeuralReranker(settings.reranker_model)
        self._cache: dict[str, list[RetrievedChunk]] = {}
        self._sources_by_id: dict[str, RetrievedChunk] = {}
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        self.headers = {
            "User-Agent": "NeuroEvidence-FYP/0.1 (educational clinical research)",
        }

    async def search_and_rerank(
        self,
        question: str,
        topic: str | None = None,
        top_k: int | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> tuple[list[RetrievedChunk], str | None]:
        """Formulate PubMed query, over-fetch candidate abstracts, and neural re-rank them."""
        target_k = top_k or getattr(self.settings, "live_pubmed_top_k", 3)
        max_candidates = getattr(self.settings, "live_pubmed_max_candidates", 15)
        timeout_sec = getattr(self.settings, "live_pubmed_timeout_seconds", 6.0)

        query = build_clinical_pubmed_query(question, topic=topic)
        cache_key = f"{topic}:{query}".strip()

        if cache_key in self._cache:
            logger.info("Live PubMed cache hit for query: %s", query)
            return self._cache[cache_key][:target_k], query

        candidates: list[RetrievedChunk] = []

        try:
            if client is not None:
                candidates = await self._execute_search_and_fetch(client, query, max_candidates, topic)
            else:
                async with httpx.AsyncClient(timeout=timeout_sec, headers=self.headers, follow_redirects=True) as local_client:
                    candidates = await self._execute_search_and_fetch(local_client, query, max_candidates, topic)
        except Exception as exc:
            logger.warning("Live PubMed E-utilities search failed (%s); proceeding with local evidence.", exc)
            return [], query

        if not candidates:
            # If high-specificity query yielded 0 hits, try a relaxed query without strict outcome constraints
            fallback_cond = CONDITION_MESH_MAP.get(str(topic).lower(), '"Nervous System Diseases"[MeSH Terms]')
            relaxed_query = f"{fallback_cond} AND {PRE_RULE_FILTERS}"
            try:
                if client is not None:
                    candidates = await self._execute_search_and_fetch(client, relaxed_query, 8, topic)
                else:
                    async with httpx.AsyncClient(timeout=timeout_sec, headers=self.headers, follow_redirects=True) as local_client:
                        candidates = await self._execute_search_and_fetch(local_client, relaxed_query, 8, topic)
            except Exception:
                pass

        if not candidates:
            return [], query

        # Neural Re-ranking: evaluate candidate abstracts against user's specific natural query
        reranked = self._rerank_candidates(question, candidates, top_k=target_k)

        # Register in source lookup table
        for c in candidates:
            self._sources_by_id[c.source_id] = c

        # Cache results (limit cache size to 100 items)
        if len(self._cache) > 100:
            self._cache.pop(next(iter(self._cache)))
        self._cache[cache_key] = reranked

        logger.info("Live PubMed search retrieved %d and returned %d reranked chunks.", len(candidates), len(reranked))
        return reranked, query

    def get_source(self, source_id: str) -> RetrievedChunk | None:
        """Retrieve a cached live PubMed source by its unique ID."""
        return self._sources_by_id.get(source_id)

    async def _execute_search_and_fetch(
        self,
        client: httpx.AsyncClient,
        query: str,
        max_results: int,
        topic: str | None,
    ) -> list[RetrievedChunk]:
        # Step 1: E-Search (Get Top PMIDs)
        esearch_url = f"{self.base_url}/esearch.fcgi"
        search_resp = await client.get(
            esearch_url,
            params={
                "db": "pubmed",
                "term": query,
                "retmax": max_results,
                "retmode": "json",
                "sort": "relevance",
            },
        )
        if search_resp.status_code != 200:
            logger.warning("PubMed esearch returned status %d", search_resp.status_code)
            return []

        search_data = search_resp.json().get("esearchresult", {})
        id_list = search_data.get("idlist", [])
        if not id_list:
            return []

        # Step 2: E-Fetch (Get XML abstracts in a single batch)
        efetch_url = f"{self.base_url}/efetch.fcgi"
        fetch_resp = await client.get(
            efetch_url,
            params={
                "db": "pubmed",
                "id": ",".join(id_list),
                "retmode": "xml",
            },
        )
        if fetch_resp.status_code != 200:
            logger.warning("PubMed efetch returned status %d", fetch_resp.status_code)
            return []

        root = ET.fromstring(fetch_resp.text)
        candidates: list[RetrievedChunk] = []
        for article in root.findall(".//PubmedArticle"):
            chunk = parse_pubmed_xml_article(article, fallback_topic=topic or "neurology")
            if chunk:
                candidates.append(chunk)

        return candidates

    def _rerank_candidates(
        self,
        question: str,
        candidates: list[RetrievedChunk],
        top_k: int = 3,
    ) -> list[RetrievedChunk]:
        """Apply neural cross-encoder scoring between user question and abstract contents."""
        if not candidates:
            return []

        try:
            model = NeuralReranker.get_model(self.settings.reranker_model)
            import numpy as np

            pairs = [
                (
                    question,
                    f"Title: {c.title}. Empirical Abstract: {c.excerpt}",
                )
                for c in candidates
            ]
            raw_scores = np.asarray(model.predict(pairs)).astype(float)

            # Map raw logits to calibrated probabilities using sigmoid: 1 / (1 + exp(-x))
            sigmoid_scores = 1.0 / (1.0 + np.exp(-raw_scores))

            scored_candidates: list[RetrievedChunk] = []
            for score, chunk in zip(sigmoid_scores, candidates):
                # Boost confidence if the chunk specifically addresses empirical trial endpoints
                boost = 0.05 if ("randomized" in chunk.excerpt.lower() or "trial" in chunk.excerpt.lower()) else 0.0
                calibrated_score = float(np.clip(score + boost, 0.05, 0.99))
                scored_chunk = chunk.model_copy(update={"relevance": round(calibrated_score, 4)})
                scored_candidates.append(scored_chunk)

            # Sort descending by relevance score
            scored_candidates.sort(key=lambda c: c.relevance, reverse=True)
            return scored_candidates[:top_k]

        except Exception as exc:
            logger.warning("Cross-encoder reranking for live PubMed candidates failed (%s); fallback to native order.", exc)
            return candidates[:top_k]
