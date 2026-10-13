"""Reproducible PMC Open Access ingestion and Chroma indexing CLI."""

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from pathlib import Path
from time import sleep

import httpx

from .config import get_settings
from .llm import OpenAIAdapter, create_llm_adapter


PREPROCESSING_VERSION = "jats-v1"
TOKEN_PATTERN = re.compile(r"\S+")
DISCOVERY_QUERIES = {
    "Parkinson's disease": '"Parkinson Disease"[MeSH Terms] AND open access[filter] AND 2015:3000[dp]',
    "epilepsy": '"Epilepsy"[MeSH Terms] AND open access[filter] AND 2015:3000[dp]',
    "stroke": '"Stroke"[MeSH Terms] AND open access[filter] AND 2015:3000[dp]',
    "multiple sclerosis": '"Multiple Sclerosis"[MeSH Terms] AND open access[filter] AND 2015:3000[dp]',
}
CLINICAL_DISCOVERY_QUERIES = {
    "Parkinson's disease": (
        '"Parkinson Disease"[MeSH Terms] '
        'AND (clinical trial[Filter] OR systematic review[Filter] OR meta-analysis[Filter] OR practice guideline[Filter]) '
        'AND humans[Filter] AND pubmed pmc[Filter] AND 2015:3000[dp]'
    ),
    "epilepsy": (
        '"Epilepsy"[MeSH Terms] '
        'AND (clinical trial[Filter] OR systematic review[Filter] OR meta-analysis[Filter] OR practice guideline[Filter]) '
        'AND humans[Filter] AND pubmed pmc[Filter] AND 2015:3000[dp]'
    ),
    "stroke": (
        '"Stroke"[MeSH Terms] '
        'AND (clinical trial[Filter] OR systematic review[Filter] OR meta-analysis[Filter] OR practice guideline[Filter]) '
        'AND humans[Filter] AND pubmed pmc[Filter] AND 2015:3000[dp]'
    ),
    "multiple sclerosis": (
        '"Multiple Sclerosis"[MeSH Terms] '
        'AND (clinical trial[Filter] OR systematic review[Filter] OR meta-analysis[Filter] OR practice guideline[Filter]) '
        'AND humans[Filter] AND pubmed pmc[Filter] AND 2015:3000[dp]'
    ),
}
TOPIC_CODES = {
    "Parkinson's disease": "PD",
    "epilepsy": "EP",
    "stroke": "ST",
    "multiple sclerosis": "MS",
}
DEFAULT_DISCOVERY_TOPICS = ["Parkinson's disease", "epilepsy"]


CORE_MANIFEST_COLUMNS = {
    "source_id",
    "pmcid",
    "pmid",
    "doi",
    "title",
    "authors",
    "year",
    "journal",
    "topic",
    "url",
    "license",
    "included",
}


@dataclass(frozen=True)
class ManifestRecord:
    source_id: str
    pmcid: str
    pmid: str
    doi: str
    title: str
    authors: str
    year: str
    journal: str
    topic: str
    url: str
    license: str
    included: str
    abstract: str = ""
    layer: str = "1"
    layer_name: str = "Layer 1: Foundational Knowledge"
    layer_source: str = "NCBI Bookshelf / StatPearls"
    subtopic: str = ""


@dataclass
class Chunk:
    chunk_id: str
    document_id: str
    source_id: str
    text: str
    section: str
    paragraph_start: int
    paragraph_end: int
    metadata: dict[str, str]


def read_manifest(path: Path) -> list[ManifestRecord]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = CORE_MANIFEST_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Manifest is missing columns: {', '.join(sorted(missing))}")
        records = [
            ManifestRecord(**{key: row.get(key, "").strip() for key in ManifestRecord.__annotations__})
            for row in reader
        ]
    return [record for record in records if record.included.lower() in {"yes", "true", "1"}]


def fetch_articles(manifest_path: Path, raw_dir: Path, delay_seconds: float = 0.4) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    records = read_manifest(manifest_path)
    headers = {"User-Agent": "NeuroEvidence-FYP/0.1 (educational research)"}
    with httpx.Client(timeout=45, headers=headers, follow_redirects=True) as client:
        for record in records:
            if not record.pmcid:
                print(f"skip {record.source_id}: PMCID is required", file=sys.stderr)
                continue
            output = raw_dir / f"{record.pmcid.upper()}.xml"
            if output.exists():
                print(f"exists {output}")
                continue
            numeric_id = record.pmcid.upper().removeprefix("PMC")
            url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            response = client.get(url, params={"db": "pmc", "id": numeric_id, "retmode": "xml"})
            response.raise_for_status()
            if "<article" not in response.text:
                raise RuntimeError(f"PMC did not return JATS XML for {record.pmcid}")
            output.write_text(response.text, encoding="utf-8")
            print(f"saved {output}")
            sleep(delay_seconds)


def _collect_known_identifiers(*paths: Path | None) -> tuple[set[str], set[str], set[str], set[str]]:
    known_pmcids: set[str] = set()
    known_pmids: set[str] = set()
    known_dois: set[str] = set()
    known_titles: set[str] = set()

    for path in paths:
        if not path or not path.exists():
            continue
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    pmcid = row.get("pmcid", "").strip().upper()
                    if pmcid:
                        known_pmcids.add(pmcid)
                        known_pmcids.add(pmcid.removeprefix("PMC"))
                    pmid = row.get("pmid", "").strip()
                    if pmid:
                        known_pmids.add(pmid)
                    doi = row.get("doi", "").strip().lower()
                    if doi:
                        known_dois.add(doi)
                    title = row.get("title", "").strip().lower()
                    if title:
                        norm_title = re.sub(r"\W+", "", title)
                        if norm_title:
                            known_titles.add(norm_title)
        except Exception as exc:
            print(f"Warning: could not read existing records from {path}: {exc}", file=sys.stderr)

    return known_pmcids, known_pmids, known_dois, known_titles


def _get_next_source_id_start(existing_rows: list[dict[str, str]], topic_code: str) -> int:
    max_id = 0
    pattern = re.compile(rf"^{re.escape(topic_code)}-(\d+)$", re.IGNORECASE)
    for row in existing_rows:
        src = row.get("source_id", "").strip()
        match = pattern.match(src)
        if match:
            try:
                val = int(match.group(1))
                if val > max_id:
                    max_id = val
            except ValueError:
                pass
    return max_id + 1


def _get_with_retry(
    client: httpx.Client,
    url: str,
    params: dict,
    max_retries: int = 4,
    backoff_factor: float = 1.5,
) -> httpx.Response:
    """Make HTTP GET with retries and backoff, handling transient NCBI 500/502/503/429 errors."""
    last_exc: Exception | None = None
    curr_params = dict(params)
    for attempt in range(max_retries):
        try:
            resp = client.get(url, params=curr_params)
            resp.raise_for_status()
            return resp
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            last_exc = exc
            # If NCBI returns 500 and sort was included, try dropping sort
            if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 500 and "sort" in curr_params:
                curr_params.pop("sort", None)
            if attempt < max_retries - 1:
                sleep(backoff_factor * (attempt + 1))
    if last_exc:
        raise last_exc
    raise RuntimeError(f"Request failed after {max_retries} attempts: {url}")


def discover_candidates(
    output_path: Path,
    per_topic: int = 30,
    manifest_path: Path = Path("data/corpus_manifest.csv"),
    topics: list[str] | None = None,
    overwrite: bool = False,
    clinical_filter: bool = True,
    auto_accept: bool = False,
) -> None:
    """Discover PMC Open Access candidates, avoiding duplicate articles and preserving existing candidate data."""
    target_topics = topics or DEFAULT_DISCOVERY_TOPICS
    queries_dict = CLINICAL_DISCOVERY_QUERIES if clinical_filter else DISCOVERY_QUERIES
    search_db = "pubmed" if clinical_filter else "pmc"

    existing_rows: list[dict[str, str]] = []
    if output_path.exists() and not overwrite:
        with output_path.open("r", encoding="utf-8-sig", newline="") as handle:
            existing_rows = list(csv.DictReader(handle))
        if existing_rows:
            backup_path = output_path.with_suffix(".bak.csv")
            try:
                shutil.copy2(output_path, backup_path)
                print(f"Preserving existing candidates: backed up {len(existing_rows)} rows to {backup_path}")
            except Exception as exc:
                print(f"Warning: unable to create backup: {exc}", file=sys.stderr)

    # Collect known identifiers from existing candidates (if preserving) and existing manifest
    known_pmcids, known_pmids, known_dois, known_titles = _collect_known_identifiers(
        output_path if not overwrite else None,
        manifest_path,
    )

    new_rows: list[dict[str, str]] = []
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    headers = {"User-Agent": "NeuroEvidence-FYP/0.1 (educational research)"}

    filter_label = "Strategy A Clinical Filter (Human Trials & Reviews)" if clinical_filter else "Broad PMC Search"
    print(f"Candidate Discovery Mode: {filter_label}")

    with httpx.Client(timeout=45, headers=headers, follow_redirects=True) as client:
        for topic in target_topics:
            query = queries_dict.get(topic)
            if not query:
                print(f"Warning: no query defined for topic '{topic}', skipping.", file=sys.stderr)
                continue

            topic_code = TOPIC_CODES.get(topic, topic[:2].upper())
            next_idx = _get_next_source_id_start(existing_rows + new_rows, topic_code)
            topic_new_count = 0
            retstart = 0
            page_batch_size = max(per_topic * 2, 60)
            max_pages = 10

            for page in range(max_pages):
                if topic_new_count >= per_topic:
                    break

                search = _get_with_retry(
                    client,
                    f"{base}/esearch.fcgi",
                    params={
                        "db": search_db,
                        "term": query,
                        "retstart": retstart,
                        "retmax": page_batch_size,
                        "retmode": "json",
                        "sort": "date",
                    },
                )
                search_data = search.json().get("esearchresult", {})
                ids = search_data.get("idlist", [])
                total_found = int(search_data.get("count", 0))

                if not ids:
                    break

                # Filter out IDs already known before making summary calls
                if search_db == "pubmed":
                    unseen_ids = [uid for uid in ids if uid not in known_pmids]
                else:
                    unseen_ids = [
                        uid for uid in ids
                        if f"PMC{uid}" not in known_pmcids and uid not in known_pmcids
                    ]

                needed = per_topic - topic_new_count
                ids_to_fetch = unseen_ids[: needed * 2]

                if ids_to_fetch:
                    summary = _get_with_retry(
                        client,
                        f"{base}/esummary.fcgi",
                        params={"db": search_db, "id": ",".join(ids_to_fetch), "retmode": "json"},
                    )
                    result = summary.json().get("result", {})

                    for uid in ids_to_fetch:
                        if topic_new_count >= per_topic:
                            break
                        item = result.get(uid)
                        if not item:
                            continue

                        if search_db == "pubmed":
                            pmid = str(uid).strip()
                            pmcid = ""
                            doi = ""
                            for a in item.get("articleids", []):
                                idtype = a.get("idtype", "").lower()
                                if idtype in ("pmc", "pmcid"):
                                    m = re.search(r"PMC\d+", a.get("value", ""))
                                    if m:
                                        pmcid = m.group(0)
                                elif idtype == "doi":
                                    doi = a.get("value", "").strip()

                            if not pmcid:
                                # Require open-access PMCID for full text
                                continue
                        else:
                            identifiers = {
                                entry.get("idtype", "").lower(): entry.get("value", "")
                                for entry in item.get("articleids", [])
                            }
                            pmcid = identifiers.get("pmcid") or f"PMC{uid}"
                            pmid = identifiers.get("pmid", "")
                            doi = identifiers.get("doi", "")

                        title = clean_text(item.get("title", ""))
                        norm_title = re.sub(r"\W+", "", title.lower())

                        # Full deduplication check across PMCID, PMID, DOI, and normalized title
                        if (
                            pmcid.upper() in known_pmcids
                            or pmcid.removeprefix("PMC") in known_pmcids
                            or (pmid and pmid in known_pmids)
                            or (doi and doi.lower() in known_dois)
                            or (norm_title and norm_title in known_titles)
                        ):
                            continue

                        license_name = _fetch_oa_license(client, pmcid)
                        pubdate = item.get("pubdate", "")
                        year_match = re.search(r"\b(?:19|20)\d{2}\b", pubdate)

                        new_rows.append(
                            {
                                "source_id": f"{topic_code}-{next_idx:03d}",
                                "pmcid": pmcid,
                                "pmid": pmid,
                                "doi": doi,
                                "title": title,
                                "authors": "|".join(author.get("name", "") for author in item.get("authors", [])),
                                "year": year_match.group(0) if year_match else "",
                                "journal": item.get("fulljournalname", ""),
                                "topic": topic,
                                "url": f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/",
                                "license": license_name,
                                "included": "no",
                            }
                        )

                        known_pmcids.add(pmcid.upper())
                        known_pmcids.add(pmcid.removeprefix("PMC"))
                        if pmid:
                            known_pmids.add(pmid)
                        if doi:
                            known_dois.add(doi.lower())
                        if norm_title:
                            known_titles.add(norm_title)

                        next_idx += 1
                        topic_new_count += 1
                        sleep(0.12)

                retstart += len(ids)
                if retstart >= total_found:
                    break

            print(f"Discovered {topic_new_count} new candidate(s) for {topic} (scanned {retstart} records in {search_db}).")

    all_rows = existing_rows + new_rows
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(ManifestRecord.__annotations__.keys()), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"Total candidates in {output_path}: {len(all_rows)} ({len(new_rows)} newly added, {len(existing_rows)} previously existing)")

    if auto_accept and manifest_path is not None:
        print("\n[Option 1: Auto-Accept] Promoting candidates directly into corpus manifest (bypassing ASReview)...")
        if new_rows:
            accept_candidates(manifest_path=manifest_path, records=new_rows)
        else:
            accept_candidates(
                manifest_path=manifest_path,
                candidates_path=output_path,
                limit=per_topic,
            )


def _fetch_oa_license(client: httpx.Client, pmcid: str) -> str:
    try:
        response = client.get("https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi", params={"id": pmcid})
        response.raise_for_status()
        record = ET.fromstring(response.text).find(".//record")
        return record.attrib.get("license", "REVIEW_REQUIRED") if record is not None else "REVIEW_REQUIRED"
    except (httpx.HTTPError, ET.ParseError):
        return "REVIEW_REQUIRED"


def parse_jats(xml_path: Path, record: ManifestRecord) -> list[Chunk]:
    root = ET.parse(xml_path).getroot()
    sections: list[tuple[str, list[str]]] = []
    body = root.find(".//body")
    if body is None:
        return []
    for section in body.findall(".//sec"):
        title_element = section.find("./title")
        section_title = _text(title_element) if title_element is not None else "Untitled section"
        if section_title.lower() in {"references", "acknowledgements", "supplementary material"}:
            continue
        paragraphs = [_text(element) for element in section.findall("./p")]
        paragraphs = [clean_text(item) for item in paragraphs if clean_text(item)]
        if paragraphs:
            sections.append((section_title, paragraphs))

    chunks: list[Chunk] = []
    for sec_idx, (section_title, paragraphs) in enumerate(sections):
        chunks.extend(chunk_paragraphs(record, section_title, paragraphs, sec_idx=sec_idx))
    return chunks


def chunk_paragraphs(
    record: ManifestRecord,
    section: str,
    paragraphs: list[str],
    target_tokens: int = 500,
    overlap_tokens: int = 100,
    sec_idx: int = 0,
) -> list[Chunk]:
    joined = "\n".join(paragraphs)
    tokens = TOKEN_PATTERN.findall(joined)
    if not tokens:
        return []
    step = max(1, target_tokens - overlap_tokens)
    chunks: list[Chunk] = []
    for chunk_idx, start in enumerate(range(0, len(tokens), step)):
        end = min(start + target_tokens, len(tokens))
        text = " ".join(tokens[start:end])
        digest_input = f"{record.source_id}|{section}|{sec_idx}|{chunk_idx}|{start}|{end}|{PREPROCESSING_VERSION}"
        chunk_id = hashlib.sha256(digest_input.encode()).hexdigest()[:24]
        metadata = {
            "document_id": record.source_id,
            "source_id": record.source_id,
            "title": record.title,
            "authors": record.authors,
            "year": record.year,
            "journal": record.journal,
            "topic": record.topic,
            "url": record.url,
            "doi": record.doi,
            "pmid": record.pmid,
            "pmcid": record.pmcid,
            "license": record.license,
            "section": section,
            "preprocessing_version": PREPROCESSING_VERSION,
            "layer": str(getattr(record, "layer", "1") or "1"),
            "layer_name": getattr(record, "layer_name", "Layer 1: Foundational Knowledge") or "Layer 1: Foundational Knowledge",
            "layer_source": getattr(record, "layer_source", "NCBI Bookshelf / StatPearls") or "NCBI Bookshelf / StatPearls",
            "subtopic": getattr(record, "subtopic", "") or "",
            "parent_id": f"{record.source_id}::{section}",
            "parent_title": f"{record.title} - {section}",
            "breadcrumb": f"Layer {getattr(record, 'layer', '1')} > {record.topic.title()} > {getattr(record, 'subtopic', '') or section} > {record.title}",
        }
        chunks.append(
            Chunk(
                chunk_id=chunk_id,
                document_id=record.source_id,
                source_id=record.source_id,
                text=text,
                section=section,
                paragraph_start=start,
                paragraph_end=end,
                metadata=metadata,
            )
        )
        if end == len(tokens):
            break
    return chunks


def index_articles(
    manifest_path: Path,
    raw_dir: Path,
    export_path: Path,
    embedder_type: str | None = None,
    reset: bool = False,
) -> None:
    settings = get_settings()
    active_embedder_type = (embedder_type or settings.embedding_provider).lower()

    if active_embedder_type == "local":
        from .retrieval import TransformerDenseEmbedder

        embedder = TransformerDenseEmbedder(settings.dense_model)
        active_embedding_model = settings.dense_model
    elif active_embedder_type == "gemini":
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is required to build the research embedding index with Gemini")
        embedder = create_llm_adapter(settings)
        active_embedding_model = settings.gemini_embedding_model
    elif active_embedder_type == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required to build the research embedding index with OpenAI")
        embedder = create_llm_adapter(settings)
        active_embedding_model = settings.openai_embedding_model
    else:
        raise ValueError(
            f"Unsupported embedder type: {active_embedder_type}. Choose 'local', 'gemini', or 'openai'."
        )

    from .demo_corpus import DEMO_CHUNKS

    records = read_manifest(manifest_path)
    all_chunks: list[Chunk] = []
    for record in records:
        if not record.pmcid:
            # Layer 1 & 2 guidelines and textbooks (e.g. NICE, StatPearls) are pre-bundled in demo_corpus
            triad_matches = [c for c in DEMO_CHUNKS if c.source_id == record.source_id]
            for c in triad_matches:
                meta = {
                    "document_id": c.document_id,
                    "source_id": c.source_id,
                    "title": c.title,
                    "authors": "|".join(c.authors) if isinstance(c.authors, list) else str(c.authors),
                    "year": str(c.year) if c.year else "",
                    "journal": c.journal or "",
                    "topic": c.topic,
                    "url": c.url,
                    "doi": c.doi or "",
                    "pmid": c.pmid or "",
                    "pmcid": "",
                    "license": c.license or "",
                    "section": c.section or "Clinical Guidance",
                    "preprocessing_version": PREPROCESSING_VERSION,
                    "layer": str(c.layer),
                    "layer_name": c.layer_name,
                    "layer_source": c.layer_source,
                    "subtopic": c.subtopic or "",
                    "parent_id": c.parent_id or f"{c.document_id}::{c.section or 'main'}",
                    "parent_title": c.parent_title or f"{c.title} - {c.section or 'Main'}",
                    "breadcrumb": " > ".join(c.breadcrumb) if c.breadcrumb else f"Layer {c.layer} > {c.topic.title()} > {c.title}",
                }
                all_chunks.append(
                    Chunk(
                        chunk_id=c.chunk_id,
                        document_id=c.document_id,
                        source_id=c.source_id,
                        text=c.excerpt,
                        section=c.section or "Clinical Guidance",
                        paragraph_start=0,
                        paragraph_end=len(TOKEN_PATTERN.findall(c.excerpt)),
                        metadata=meta,
                    )
                )
            continue

        xml_path = raw_dir / f"{record.pmcid.upper()}.xml"
        if not xml_path.exists():
            print(f"Warning: XML file not found for {record.source_id} ({record.pmcid}), skipping.", file=sys.stderr)
            continue
        all_chunks.extend(parse_jats(xml_path, record))

    # Ensure all chunk IDs are strictly unique across the corpus
    seen_ids: dict[str, int] = {}
    for chunk in all_chunks:
        if chunk.chunk_id in seen_ids:
            seen_ids[chunk.chunk_id] += 1
            chunk.chunk_id = f"{chunk.chunk_id}_{seen_ids[chunk.chunk_id]}"
        else:
            seen_ids[chunk.chunk_id] = 0

    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text(
        "\n".join(json.dumps(asdict(chunk), ensure_ascii=False) for chunk in all_chunks),
        encoding="utf-8",
    )

    import chromadb
    from chromadb.config import Settings as ChromaSettings

    client = chromadb.PersistentClient(
        path=str(settings.chroma_path),
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    if reset:
        try:
            client.delete_collection(settings.chroma_collection)
            print(f"Reset: Deleted existing collection '{settings.chroma_collection}'.", flush=True)
        except Exception:
            pass

    collection = client.get_or_create_collection(
        settings.chroma_collection, metadata={"hnsw:space": "cosine"}
    )
    batch_size = 64 if active_embedder_type == "local" else 16

    # Resume capability: check what is already indexed so we don't re-embed from scratch
    existing_ids = set()
    try:
        existing_ids = set(collection.get(include=[])["ids"])
        if existing_ids:
            print(f"ChromaDB collection already contains {len(existing_ids)} indexed chunks. Resuming...", flush=True)
    except Exception:
        pass

    for start in range(0, len(all_chunks), batch_size):
        batch = all_chunks[start : start + batch_size]
        unindexed_batch = [c for c in batch if c.chunk_id not in existing_ids]

        if unindexed_batch:
            embeddings = embedder.embed([chunk.text for chunk in unindexed_batch])
            collection.upsert(
                ids=[chunk.chunk_id for chunk in unindexed_batch],
                documents=[chunk.text for chunk in unindexed_batch],
                metadatas=[chunk.metadata for chunk in unindexed_batch],
                embeddings=embeddings,
            )
            for c in unindexed_batch:
                existing_ids.add(c.chunk_id)
            if active_embedder_type != "local":
                sleep(1.0)

        print(f"indexed {min(start + batch_size, len(all_chunks))}/{len(all_chunks)}", flush=True)

    version = {
        "collection": settings.chroma_collection,
        "documents": len(records),
        "chunks": len(all_chunks),
        "preprocessing_version": PREPROCESSING_VERSION,
        "embedding_provider": active_embedder_type,
        "embedding_model": active_embedding_model,
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
    }
    (export_path.parent / "corpus_version.json").write_text(
        json.dumps(version, indent=2), encoding="utf-8"
    )


def clean_text(value: str) -> str:
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"\[[0-9,\-– ]+\]", "", value)
    return value.strip()


def _text(element: ET.Element | None) -> str:
    return "" if element is None else "".join(element.itertext())


def _fetch_pubmed_abstracts_batch(pmids: list[str], chunk_size: int = 40) -> dict[str, str]:
    """Fetch abstracts for PubMed IDs in batches using NCBI E-utilities."""
    abstracts: dict[str, str] = {}
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    headers = {"User-Agent": "NeuroEvidence-FYP/0.1 (educational research)"}
    with httpx.Client(timeout=30, headers=headers) as client:
        for i in range(0, len(pmids), chunk_size):
            chunk = [p for p in pmids[i : i + chunk_size] if p]
            if not chunk:
                continue
            try:
                resp = client.get(base, params={"db": "pubmed", "id": ",".join(chunk), "retmode": "xml"})
                if resp.status_code == 200:
                    root = ET.fromstring(resp.text)
                    for article in root.findall(".//PubmedArticle"):
                        pmid_el = article.find(".//MedlineCitation/PMID")
                        if pmid_el is None or not pmid_el.text:
                            continue
                        pmid_val = pmid_el.text.strip()
                        abstract_texts = article.findall(".//Article/Abstract/AbstractText")
                        combined = " ".join(_text(el) for el in abstract_texts)
                        if combined:
                            abstracts[pmid_val] = clean_text(combined)
            except Exception as exc:
                print(f"Warning: could not fetch abstracts for batch {i}: {exc}", file=sys.stderr)
            sleep(0.2)
    return abstracts


def export_asreview(
    candidates_path: Path,
    output_path: Path,
    fetch_abstracts: bool = True,
    topic: str | None = None,
) -> None:
    """Export candidate records into an ASReview-ready CSV with title, abstract, and metadata."""
    if not candidates_path.exists():
        raise FileNotFoundError(f"Candidates file not found: {candidates_path}")

    with candidates_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = list(csv.DictReader(handle))

    if topic:
        target = topic.strip().lower()
        code_to_topic = {
            "pd": "parkinson's disease",
            "ep": "epilepsy",
            "st": "stroke",
            "ms": "multiple sclerosis",
        }
        target = code_to_topic.get(target, target)
        reader = [r for r in reader if r.get("topic", "").strip().lower() == target]

    if not reader:
        print(f"No candidates found to export (topic filter: {topic or 'all'}).", file=sys.stderr)
        return

    pmid_map: dict[str, str] = {}
    if fetch_abstracts:
        pmids_to_fetch = [row["pmid"] for row in reader if row.get("pmid") and not row.get("abstract")]
        if pmids_to_fetch:
            print(f"Fetching abstracts for {len(pmids_to_fetch)} candidate records from PubMed...")
            pmid_map = _fetch_pubmed_abstracts_batch(pmids_to_fetch)

    asreview_rows = []
    for row in reader:
        pmid = row.get("pmid", "")
        abstract = row.get("abstract", "") or pmid_map.get(pmid, "")
        if not abstract:
            abstract = (
                f"Neurological research article on {row.get('topic', 'neurology')}. "
                f"Full text available at {row.get('url', '')}."
            )
        asreview_rows.append(
            {
                "source_id": row.get("source_id", ""),
                "title": row.get("title", ""),
                "abstract": clean_text(abstract),
                "doi": row.get("doi", ""),
                "topic": row.get("topic", ""),
                "authors": row.get("authors", ""),
                "year": row.get("year", ""),
                "journal": row.get("journal", ""),
                "url": row.get("url", ""),
                "pmcid": row.get("pmcid", ""),
                "pmid": pmid,
                "license": row.get("license", ""),
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "source_id",
        "title",
        "abstract",
        "doi",
        "topic",
        "authors",
        "year",
        "journal",
        "url",
        "pmcid",
        "pmid",
        "license",
    ]
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(asreview_rows)

    print(f"Exported {len(asreview_rows)} candidate records to ASReview pool at {output_path}")


def sync_asreview(
    asreview_path: Path,
    manifest_path: Path,
    candidates_path: Path,
) -> None:
    """Synchronize ASReview screening labels (included=1 / asreview_label=1) into corpus_manifest.csv."""
    if not asreview_path.exists():
        raise FileNotFoundError(f"ASReview export file not found: {asreview_path}")

    with asreview_path.open("r", encoding="utf-8-sig", newline="") as handle:
        raw_asreview_rows = list(csv.DictReader(handle))

    asreview_rows = [
        {k.strip().replace('"', '').replace('\ufeff', ''): v for k, v in r.items() if k}
        for r in raw_asreview_rows
    ]

    included_identifiers: set[str] = set()
    included_asreview_rows: list[dict[str, str]] = []
    for row in asreview_rows:
        incl_val = str(
            row.get("included")
            or row.get("final_included")
            or row.get("asreview_label")
            or ("1" if "relevant" in asreview_path.name.lower() else "")
        ).strip().lower()
        if incl_val in {"1", "1.0", "yes", "true"}:
            included_asreview_rows.append(row)
            for key in ("source_id", "doi", "pmcid", "title"):
                val = row.get(key, "").strip().lower()
                if val:
                    included_identifiers.add(val)

    if not included_identifiers and not included_asreview_rows:
        print("No included articles found in the provided ASReview export.", file=sys.stderr)
        return

    candidates: list[dict[str, str]] = []
    if candidates_path.exists():
        with candidates_path.open("r", encoding="utf-8-sig", newline="") as handle:
            raw_candidates = list(csv.DictReader(handle))
            candidates = [
                {k.strip().replace('"', '').replace('\ufeff', ''): v for k, v in r.items() if k}
                for r in raw_candidates
            ]

    manifest_records: list[dict[str, str]] = []
    if manifest_path.exists():
        with manifest_path.open("r", encoding="utf-8-sig", newline="") as handle:
            manifest_records = list(csv.DictReader(handle))

    def _find_in_manifest(row: dict[str, str]) -> int | None:
        row_src = row.get("source_id", "").strip().lower()
        row_pmcid = row.get("pmcid", "").strip().upper()
        row_pmid = row.get("pmid", "").strip()
        row_doi = row.get("doi", "").strip().lower()
        row_title = re.sub(r"\W+", "", row.get("title", "").strip().lower())
        for idx, r in enumerate(manifest_records):
            if row_src and r.get("source_id", "").strip().lower() == row_src:
                return idx
            r_pmcid = r.get("pmcid", "").strip().upper()
            if row_pmcid and (r_pmcid == row_pmcid or r_pmcid.removeprefix("PMC") == row_pmcid.removeprefix("PMC")):
                return idx
            if row_pmid and r.get("pmid", "").strip() == row_pmid:
                return idx
            if row_doi and r.get("doi", "").strip().lower() == row_doi:
                return idx
            r_title = re.sub(r"\W+", "", r.get("title", "").strip().lower())
            if row_title and r_title == row_title:
                return idx
        return None

    synced_count = 0
    synced_pmcids = set()

    for candidate in candidates:
        cand_matches = any(
            candidate.get(k, "").strip().lower() in included_identifiers
            for k in ("source_id", "doi", "pmcid", "title")
            if candidate.get(k)
        )
        if cand_matches:
            matched_row = dict(candidate)
            matched_row["included"] = "yes"
            if not matched_row.get("layer"):
                matched_row["layer"] = "3"
            if not matched_row.get("layer_name"):
                matched_row["layer_name"] = "Layer 3: Empirical Evidence & Trials"
            if not matched_row.get("layer_source"):
                matched_row["layer_source"] = "PubMed Central / Clinical Trials"

            found_idx = _find_in_manifest(matched_row)
            if found_idx is not None:
                manifest_records[found_idx]["included"] = "yes"
            else:
                manifest_records.append(matched_row)
            synced_count += 1
            if matched_row.get("pmcid"):
                synced_pmcids.add(matched_row["pmcid"].strip().upper())

    # In case articles in the ASReview export were not in the candidates pool file
    for a_row in included_asreview_rows:
        pmcid = a_row.get("pmcid", "").strip().upper()
        if pmcid and pmcid not in synced_pmcids:
            found_idx = _find_in_manifest(a_row)
            if found_idx is not None:
                manifest_records[found_idx]["included"] = "yes"
            else:
                new_row = dict(a_row)
                new_row["included"] = "yes"
                if not new_row.get("layer"):
                    new_row["layer"] = "3"
                if not new_row.get("layer_name"):
                    new_row["layer_name"] = "Layer 3: Empirical Evidence & Trials"
                if not new_row.get("layer_source"):
                    new_row["layer_source"] = "PubMed Central / Clinical Trials"
                manifest_records.append(new_row)
                synced_count += 1
                synced_pmcids.add(pmcid)

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(ManifestRecord.__annotations__.keys())
    with manifest_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(manifest_records)

    print(f"Successfully synced {synced_count} included records into {manifest_path} (total manifest size: {len(manifest_records)} articles)")


def accept_candidates(
    manifest_path: Path,
    candidates_path: Path | None = None,
    records: list[dict[str, str]] | None = None,
    topic: str | None = None,
    limit: int | None = None,
) -> int:
    """Promote candidate records directly into corpus_manifest.csv with included='yes', bypassing ASReview."""
    source_records: list[dict[str, str]] = []
    if records is not None:
        source_records = list(records)
    elif candidates_path is not None:
        if not candidates_path.exists():
            raise FileNotFoundError(f"Candidates file not found: {candidates_path}")
        with candidates_path.open("r", encoding="utf-8-sig", newline="") as handle:
            raw_records = list(csv.DictReader(handle))
            source_records = [
                {k.strip().replace('"', '').replace('\ufeff', ''): v for k, v in r.items() if k}
                for r in raw_records
            ]
    else:
        raise ValueError("Either candidates_path or records must be provided to accept_candidates.")

    if not source_records:
        print("No candidates provided to accept.", file=sys.stderr)
        return 0

    target_topic = None
    if topic:
        code_to_topic = {
            "pd": "parkinson's disease",
            "ep": "epilepsy",
            "st": "stroke",
            "ms": "multiple sclerosis",
        }
        target_topic = code_to_topic.get(topic.strip().lower(), topic.strip().lower())

    manifest_records: list[dict[str, str]] = []
    if manifest_path.exists():
        with manifest_path.open("r", encoding="utf-8-sig", newline="") as handle:
            manifest_records = list(csv.DictReader(handle))

    # Collect known identifiers in manifest to avoid duplicates
    known_pmcids, known_pmids, known_dois, known_titles = _collect_known_identifiers(manifest_path)

    accepted_count = 0
    topic_accepted_counts: dict[str, int] = {}

    for cand in source_records:
        cand_topic = cand.get("topic", "").strip().lower()
        if target_topic and cand_topic != target_topic:
            continue

        if limit is not None:
            current_topic_count = topic_accepted_counts.get(cand_topic, 0)
            if current_topic_count >= limit:
                continue

        pmcid = cand.get("pmcid", "").strip().upper()
        if not pmcid:
            # Full text XML cannot be fetched without PMCID
            continue

        pmid = cand.get("pmid", "").strip()
        doi = cand.get("doi", "").strip().lower()
        title = cand.get("title", "").strip().lower()
        norm_title = re.sub(r"\W+", "", title) if title else ""

        if (
            pmcid in known_pmcids
            or pmcid.removeprefix("PMC") in known_pmcids
            or (pmid and pmid in known_pmids)
            or (doi and doi in known_dois)
            or (norm_title and norm_title in known_titles)
        ):
            continue

        new_record = dict(cand)
        new_record["included"] = "yes"
        if not new_record.get("layer"):
            new_record["layer"] = "3"
        if not new_record.get("layer_name"):
            new_record["layer_name"] = "Layer 3: Empirical Evidence & Trials"
        if not new_record.get("layer_source"):
            new_record["layer_source"] = "PubMed Central / Clinical Trials"

        manifest_records.append(new_record)
        known_pmcids.add(pmcid)
        known_pmcids.add(pmcid.removeprefix("PMC"))
        if pmid:
            known_pmids.add(pmid)
        if doi:
            known_dois.add(doi)
        if norm_title:
            known_titles.add(norm_title)

        accepted_count += 1
        topic_accepted_counts[cand_topic] = topic_accepted_counts.get(cand_topic, 0) + 1

    if accepted_count > 0:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = list(ManifestRecord.__annotations__.keys())
        with manifest_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(manifest_records)
        print(f"Successfully accepted {accepted_count} candidate records into {manifest_path} (total manifest size: {len(manifest_records)} articles).")
    else:
        print("No new candidates were accepted (all were already present in manifest or lacked PMCIDs).")

    return accepted_count


def _resolve_project_path(p: Path) -> Path:
    """Resolve a relative path against the project root if invoked from the backend subdirectory."""
    if not p.is_absolute():
        cwd = Path.cwd()
        if cwd.name.lower() == "backend" and (cwd.parent / "data").exists():
            return cwd.parent / p
    return p


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=["discover", "fetch", "index", "export-asreview", "sync-asreview", "accept-candidates"],
    )
    parser.add_argument("--manifest", type=Path, default=Path("data/corpus_manifest.csv"))
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--export", type=Path, default=Path("data/processed/chunks.jsonl"))
    parser.add_argument("--candidate-output", type=Path, default=Path("data/corpus_candidates.csv"))
    parser.add_argument("--candidates", type=Path, default=Path("data/corpus_candidates.csv"))
    parser.add_argument("--asreview-pool", type=Path, default=Path("data/asreview_corpus_pool.csv"))
    parser.add_argument("--asreview-file", type=Path, default=Path("data/asreview_export.csv"))
    parser.add_argument("--no-fetch-abstracts", action="store_true", default=False)
    parser.add_argument("--per-topic", type=int, default=30)
    parser.add_argument(
        "--topics",
        type=str,
        default="Parkinson's disease,epilepsy",
        help="Comma-separated topics for candidate discovery (default: 'Parkinson\\'s disease,epilepsy'). Use 'all' for all topics.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        default=False,
        help="Overwrite existing candidate file instead of preserving and appending to it.",
    )
    parser.add_argument(
        "--no-clinical-filter",
        action="store_true",
        default=False,
        help="Disable high-precision clinical filter and use broad PMC search.",
    )
    parser.add_argument(
        "--auto-accept",
        action="store_true",
        default=False,
        help="Automatically promote candidates into corpus manifest with included='yes', bypassing ASReview.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of candidates accepted per topic when running accept-candidates.",
    )
    parser.add_argument(
        "--topic",
        type=str,
        default=None,
        help="Optional topic filter for export-asreview or accept-candidates (e.g. 'pd', 'ep', 'Parkinson\\'s disease', 'epilepsy').",
    )
    parser.add_argument(
        "--embedder",
        type=str,
        default=None,
        choices=["local", "gemini", "openai"],
        help="Embedding provider for indexing: 'local' (offline S-PubMedBert, default), 'gemini', or 'openai'.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        default=False,
        help="Delete existing ChromaDB collection before indexing to ensure a clean vector index.",
    )
    args = parser.parse_args()

    # Automatically resolve paths to project root if command is executed from inside backend/
    args.manifest = _resolve_project_path(args.manifest)
    args.raw_dir = _resolve_project_path(args.raw_dir)
    args.export = _resolve_project_path(args.export)
    args.candidate_output = _resolve_project_path(args.candidate_output)
    args.candidates = _resolve_project_path(args.candidates)
    args.asreview_pool = _resolve_project_path(args.asreview_pool)
    args.asreview_file = _resolve_project_path(args.asreview_file)

    if args.command == "discover":
        if args.topics.strip().lower() == "all":
            selected_topics = list(DISCOVERY_QUERIES.keys())
        else:
            selected_topics = [t.strip() for t in args.topics.split(",") if t.strip()]
        discover_candidates(
            output_path=args.candidate_output,
            per_topic=args.per_topic,
            manifest_path=args.manifest,
            topics=selected_topics,
            overwrite=args.overwrite,
            clinical_filter=not args.no_clinical_filter,
            auto_accept=args.auto_accept,
        )
    elif args.command == "fetch":
        fetch_articles(args.manifest, args.raw_dir)
    elif args.command == "index":
        index_articles(
            args.manifest,
            args.raw_dir,
            args.export,
            embedder_type=args.embedder,
            reset=args.reset,
        )
    elif args.command == "export-asreview":
        export_asreview(
            args.candidates,
            args.asreview_pool,
            fetch_abstracts=not args.no_fetch_abstracts,
            topic=args.topic,
        )
    elif args.command == "sync-asreview":
        sync_asreview(
            args.asreview_file,
            args.manifest,
            args.candidates,
        )
    elif args.command == "accept-candidates":
        accept_candidates(
            manifest_path=args.manifest,
            candidates_path=args.candidates,
            topic=args.topic,
            limit=args.limit or args.per_topic,
        )


if __name__ == "__main__":
    main()

