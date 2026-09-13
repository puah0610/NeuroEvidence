"""Reproducible PMC Open Access ingestion and Chroma indexing CLI."""

import argparse
import csv
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from pathlib import Path
from time import sleep

import httpx

from .config import get_settings
from .llm import OpenAIAdapter


PREPROCESSING_VERSION = "jats-v1"
TOKEN_PATTERN = re.compile(r"\S+")
DISCOVERY_QUERIES = {
    "Parkinson's disease": '"Parkinson Disease"[MeSH Terms] AND open access[filter] AND 2015:3000[dp]',
    "epilepsy": '"Epilepsy"[MeSH Terms] AND open access[filter] AND 2015:3000[dp]',
    "stroke": '"Stroke"[MeSH Terms] AND open access[filter] AND 2015:3000[dp]',
    "multiple sclerosis": '"Multiple Sclerosis"[MeSH Terms] AND open access[filter] AND 2015:3000[dp]',
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


@dataclass(frozen=True)
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
        required = set(ManifestRecord.__annotations__)
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Manifest is missing columns: {', '.join(sorted(missing))}")
        records = [ManifestRecord(**{key: row.get(key, "").strip() for key in required}) for row in reader]
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


def discover_candidates(output_path: Path, per_topic: int = 30) -> None:
    """Create a 120-record candidate manifest; every row remains excluded pending human review."""
    rows: list[dict[str, str]] = []
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    headers = {"User-Agent": "NeuroEvidence-FYP/0.1 (educational research)"}
    with httpx.Client(timeout=45, headers=headers, follow_redirects=True) as client:
        for topic, query in DISCOVERY_QUERIES.items():
            search = client.get(
                f"{base}/esearch.fcgi",
                params={"db": "pmc", "term": query, "retmax": per_topic, "retmode": "json", "sort": "date"},
            )
            search.raise_for_status()
            ids = search.json()["esearchresult"]["idlist"]
            if not ids:
                print(f"No candidates returned for {topic}", file=sys.stderr)
                continue
            summary = client.get(
                f"{base}/esummary.fcgi",
                params={"db": "pmc", "id": ",".join(ids), "retmode": "json"},
            )
            summary.raise_for_status()
            result = summary.json()["result"]
            for index, uid in enumerate(ids, start=1):
                item = result[uid]
                identifiers = {
                    entry.get("idtype", "").lower(): entry.get("value", "")
                    for entry in item.get("articleids", [])
                }
                pmcid = identifiers.get("pmcid") or f"PMC{uid}"
                license_name = _fetch_oa_license(client, pmcid)
                topic_code = {"Parkinson's disease": "PD", "epilepsy": "EP", "stroke": "ST", "multiple sclerosis": "MS"}[topic]
                pubdate = item.get("pubdate", "")
                year_match = re.search(r"\b(?:19|20)\d{2}\b", pubdate)
                rows.append(
                    {
                        "source_id": f"{topic_code}-{index:03d}",
                        "pmcid": pmcid,
                        "pmid": identifiers.get("pmid", ""),
                        "doi": identifiers.get("doi", ""),
                        "title": clean_text(item.get("title", "")),
                        "authors": "|".join(author.get("name", "") for author in item.get("authors", [])),
                        "year": year_match.group(0) if year_match else "",
                        "journal": item.get("fulljournalname", ""),
                        "topic": topic,
                        "url": f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/",
                        "license": license_name,
                        "included": "no",
                    }
                )
                sleep(0.12)
            print(f"discovered {len(ids)} candidates for {topic}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ManifestRecord.__annotations__.keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} excluded candidates to {output_path}")


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
    for section_title, paragraphs in sections:
        chunks.extend(chunk_paragraphs(record, section_title, paragraphs))
    return chunks


def chunk_paragraphs(
    record: ManifestRecord,
    section: str,
    paragraphs: list[str],
    target_tokens: int = 500,
    overlap_tokens: int = 100,
) -> list[Chunk]:
    joined = "\n".join(paragraphs)
    tokens = TOKEN_PATTERN.findall(joined)
    if not tokens:
        return []
    step = max(1, target_tokens - overlap_tokens)
    chunks: list[Chunk] = []
    for start in range(0, len(tokens), step):
        end = min(start + target_tokens, len(tokens))
        text = " ".join(tokens[start:end])
        digest_input = f"{record.source_id}|{section}|{start}|{end}|{PREPROCESSING_VERSION}"
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


def index_articles(manifest_path: Path, raw_dir: Path, export_path: Path) -> None:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required to build the research embedding index")
    records = read_manifest(manifest_path)
    all_chunks: list[Chunk] = []
    for record in records:
        xml_path = raw_dir / f"{record.pmcid.upper()}.xml"
        if not xml_path.exists():
            raise FileNotFoundError(f"Run the fetch command first: {xml_path}")
        all_chunks.extend(parse_jats(xml_path, record))

    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text(
        "\n".join(json.dumps(asdict(chunk), ensure_ascii=False) for chunk in all_chunks),
        encoding="utf-8",
    )

    import chromadb

    adapter = OpenAIAdapter(settings)
    client = chromadb.PersistentClient(path=str(settings.chroma_path))
    collection = client.get_or_create_collection(
        settings.chroma_collection, metadata={"hnsw:space": "cosine"}
    )
    batch_size = 64
    for start in range(0, len(all_chunks), batch_size):
        batch = all_chunks[start : start + batch_size]
        embeddings = adapter.embed([chunk.text for chunk in batch])
        collection.upsert(
            ids=[chunk.chunk_id for chunk in batch],
            documents=[chunk.text for chunk in batch],
            metadatas=[chunk.metadata for chunk in batch],
            embeddings=embeddings,
        )
        print(f"indexed {min(start + batch_size, len(all_chunks))}/{len(all_chunks)}")

    version = {
        "collection": settings.chroma_collection,
        "documents": len(records),
        "chunks": len(all_chunks),
        "preprocessing_version": PREPROCESSING_VERSION,
        "embedding_model": settings.openai_embedding_model,
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["discover", "fetch", "index"])
    parser.add_argument("--manifest", type=Path, default=Path("data/corpus_manifest.csv"))
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--export", type=Path, default=Path("data/processed/chunks.jsonl"))
    parser.add_argument("--candidate-output", type=Path, default=Path("data/corpus_candidates.csv"))
    parser.add_argument("--per-topic", type=int, default=30)
    args = parser.parse_args()
    if args.command == "discover":
        discover_candidates(args.candidate_output, args.per_topic)
    elif args.command == "fetch":
        fetch_articles(args.manifest, args.raw_dir)
    else:
        index_articles(args.manifest, args.raw_dir, args.export)


if __name__ == "__main__":
    main()
