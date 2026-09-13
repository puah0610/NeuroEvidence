import math
import re
from collections import Counter, defaultdict
from typing import Protocol

from .config import Settings
from .demo_corpus import DEMO_CHUNKS
from .models import RetrievedChunk


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class DemoRetriever:
    def __init__(self, settings: Settings):
        self.settings = settings

    def search(self, question: str, topic: str | None = None) -> list[RetrievedChunk]:
        query_tokens = _tokens(question)
        scored: list[RetrievedChunk] = []
        for chunk in DEMO_CHUNKS:
            if topic and chunk.topic != topic:
                continue
            score = _cosine_counter(query_tokens, _tokens(chunk.excerpt + " " + chunk.title))
            scored.append(chunk.model_copy(update={"relevance": round(score, 4)}))
        return _limit_per_document(
            sorted(scored, key=lambda item: item.relevance, reverse=True),
            self.settings.retrieval_top_k,
            self.settings.max_chunks_per_document,
        )

    def get_source(self, source_id: str) -> RetrievedChunk | None:
        return next((item for item in DEMO_CHUNKS if item.source_id == source_id), None)


class ChromaRetriever:
    def __init__(self, settings: Settings, embedder: Embedder):
        import chromadb

        self.settings = settings
        self.embedder = embedder
        self.client = chromadb.PersistentClient(path=str(settings.chroma_path))
        self.collection = self.client.get_or_create_collection(
            name=settings.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )

    def search(self, question: str, topic: str | None = None) -> list[RetrievedChunk]:
        if self.collection.count() == 0:
            return []
        query_embedding = self.embedder.embed([question])[0]
        where = {"topic": topic} if topic else None
        query_options = {
            "query_embeddings": [query_embedding],
            "n_results": min(self.settings.retrieval_top_k * 3, self.collection.count()),
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            query_options["where"] = where
        result = self.collection.query(**query_options)
        chunks: list[RetrievedChunk] = []
        for chunk_id, text, metadata, distance in zip(
            result["ids"][0],
            result["documents"][0],
            result["metadatas"][0],
            result["distances"][0],
            strict=True,
        ):
            authors = str(metadata.get("authors", "")).split("|") if metadata.get("authors") else []
            chunks.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    document_id=str(metadata["document_id"]),
                    source_id=str(metadata["source_id"]),
                    title=str(metadata["title"]),
                    authors=authors,
                    year=int(metadata["year"]) if metadata.get("year") else None,
                    journal=metadata.get("journal"),
                    topic=str(metadata["topic"]),
                    url=str(metadata["url"]),
                    doi=metadata.get("doi"),
                    pmid=metadata.get("pmid"),
                    pmcid=metadata.get("pmcid"),
                    license=metadata.get("license"),
                    section=metadata.get("section"),
                    excerpt=text,
                    relevance=max(0.0, min(1.0, 1.0 - float(distance))),
                )
            )
        return _limit_per_document(
            chunks, self.settings.retrieval_top_k, self.settings.max_chunks_per_document
        )

    def get_source(self, source_id: str) -> RetrievedChunk | None:
        result = self.collection.get(where={"source_id": source_id}, limit=1, include=["documents", "metadatas"])
        if not result["ids"]:
            return None
        metadata = result["metadatas"][0]
        return RetrievedChunk(
            chunk_id=result["ids"][0],
            document_id=str(metadata["document_id"]),
            source_id=str(metadata["source_id"]),
            title=str(metadata["title"]),
            authors=str(metadata.get("authors", "")).split("|") if metadata.get("authors") else [],
            year=int(metadata["year"]) if metadata.get("year") else None,
            journal=metadata.get("journal"),
            topic=str(metadata["topic"]),
            url=str(metadata["url"]),
            doi=metadata.get("doi"),
            pmid=metadata.get("pmid"),
            pmcid=metadata.get("pmcid"),
            license=metadata.get("license"),
            section=metadata.get("section"),
            excerpt=result["documents"][0],
            relevance=1.0,
        )


def _tokens(text: str) -> Counter[str]:
    return Counter(TOKEN_PATTERN.findall(text.lower()))


def _cosine_counter(left: Counter[str], right: Counter[str]) -> float:
    numerator = sum(count * right[token] for token, count in left.items())
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    return numerator / (left_norm * right_norm) if left_norm and right_norm else 0.0


def _limit_per_document(
    chunks: list[RetrievedChunk], top_k: int, per_document: int
) -> list[RetrievedChunk]:
    counts: defaultdict[str, int] = defaultdict(int)
    selected: list[RetrievedChunk] = []
    for chunk in chunks:
        if counts[chunk.document_id] >= per_document:
            continue
        selected.append(chunk)
        counts[chunk.document_id] += 1
        if len(selected) == top_k:
            break
    return selected
