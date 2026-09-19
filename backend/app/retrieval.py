import math
import re
from collections import Counter, defaultdict
from typing import Protocol

from .config import Settings
from .demo_corpus import DEMO_CHUNKS
from .models import RetrievedChunk


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

# Clinical semantic concept clusters for dense proxy retrieval in demo mode
SEMANTIC_CLINICAL_CLUSTERS = {
    "ilae": {"classification", "focal", "generalized", "seizure", "awareness", "motor", "epilepsy", "ilae"},
    "semiology": {"aura", "ictal", "postictal", "paroxysmal", "hypersynchronous", "discharge", "automatisms"},
    "mechanisms": {"sodium", "channel", "gaba", "sv2a", "calcium", "levetiracetam", "lamotrigine", "valproate", "carbamazepine", "ethosuximide"},
    "ng217": {"nice", "guideline", "ng217", "first", "line", "monotherapy", "valproate", "teratogenicity", "pregnancy", "prevent"},
    "sanad": {"sanad", "trial", "rct", "remission", "failure", "lancet", "comparative", "levetiracetam", "valproate", "lamotrigine"},
    "pathophysiology": {"substantia", "nigra", "dopamine", "dopaminergic", "synuclein", "lewy", "striatal", "putamen", "basal", "ganglia"},
    "hoehn": {"hoehn", "yahr", "staging", "stage", "unilateral", "bilateral", "postural", "instability", "pull", "test"},
    "pharmacology": {"levodopa", "carbidopa", "benserazide", "agonist", "pramipexole", "ropinirole", "maob", "rasagiline", "selegiline"},
    "ng71": {"nice", "ng71", "guideline", "diagnosis", "brain", "bank", "datscan", "quality", "of", "life", "first"},
    "dbs": {"dbs", "deep", "brain", "stimulation", "stn", "gpi", "subthalamic", "pallidus", "longterm", "efficacy", "updrs"},
    "fluctuations": {"wearing", "off", "fluctuations", "dyskinesia", "comt", "maob", "entacapone", "opicapone", "rasagiline", "safinamide"},
}


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class DemoRetriever:
    """Hybrid Dense + Sparse Retriever for the 3-Layer Triad Knowledge Base."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def search(self, question: str, topic: str | None = None) -> list[RetrievedChunk]:
        query_tokens = _tokens(question)
        candidates = [
            chunk for chunk in DEMO_CHUNKS
            if not topic or chunk.topic == topic
        ]
        if not candidates:
            return []

        avg_len = sum(len(_tokens(c.excerpt)) for c in candidates) / max(1, len(candidates))

        # 1. Sparse BM25 / token scoring
        sparse_scores: list[tuple[float, RetrievedChunk]] = []
        for chunk in candidates:
            field_text = f"{chunk.title} {chunk.subtopic or ''} {chunk.section or ''} {chunk.excerpt}"
            doc_tokens = _tokens(field_text)
            doc_len = len(_tokens(chunk.excerpt))
            bm25 = _bm25_score(query_tokens, doc_tokens, avg_len, doc_len)
            sparse_scores.append((bm25, chunk))

        # 2. Dense semantic similarity (concept overlap + semantic cosine)
        dense_scores: list[tuple[float, RetrievedChunk]] = []
        expanded_query = _expand_clinical_concepts(query_tokens)
        for chunk in candidates:
            field_text = f"{chunk.title} {chunk.subtopic or ''} {chunk.section or ''} {chunk.excerpt}"
            expanded_doc = _expand_clinical_concepts(_tokens(field_text))
            semantic_sim = _cosine_counter(expanded_query, expanded_doc)
            dense_scores.append((semantic_sim, chunk))

        # 3. Reciprocal Rank Fusion (RRF)
        fused = _reciprocal_rank_fusion(sparse_scores, dense_scores, k=60, alpha=0.5)

        return _limit_per_document(
            fused,
            self.settings.retrieval_top_k,
            self.settings.max_chunks_per_document,
        )

    def get_source(self, source_id: str) -> RetrievedChunk | None:
        return next((item for item in DEMO_CHUNKS if item.source_id == source_id), None)


class ChromaRetriever:
    """Hybrid Dense + Sparse Retriever using ChromaDB dense embeddings and BM25 sparse ranking."""

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
        n_dense = min(self.settings.retrieval_top_k * 4, self.collection.count())
        query_options = {
            "query_embeddings": [query_embedding],
            "n_results": n_dense,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            query_options["where"] = where
        result = self.collection.query(**query_options)

        dense_list: list[tuple[float, RetrievedChunk]] = []
        for chunk_id, text, metadata, distance in zip(
            result["ids"][0],
            result["documents"][0],
            result["metadatas"][0],
            result["distances"][0],
            strict=True,
        ):
            chunk = _build_chunk(chunk_id, text, metadata, distance)
            dense_list.append((max(0.0, 1.0 - float(distance)), chunk))

        # Sparse scoring on retrieved candidate pool
        query_tokens = _tokens(question)
        avg_len = sum(len(_tokens(c.excerpt)) for _, c in dense_list) / max(1, len(dense_list))
        sparse_list: list[tuple[float, RetrievedChunk]] = []
        for _, chunk in dense_list:
            field_text = f"{chunk.title} {chunk.subtopic or ''} {chunk.section or ''} {chunk.excerpt}"
            doc_tokens = _tokens(field_text)
            score = _bm25_score(query_tokens, doc_tokens, avg_len, len(_tokens(chunk.excerpt)))
            sparse_list.append((score, chunk))

        # Reciprocal Rank Fusion
        fused = _reciprocal_rank_fusion(sparse_list, dense_list, k=60, alpha=0.5)

        return _limit_per_document(
            fused, self.settings.retrieval_top_k, self.settings.max_chunks_per_document
        )

    def get_source(self, source_id: str) -> RetrievedChunk | None:
        result = self.collection.get(
            where={"source_id": source_id}, limit=1, include=["documents", "metadatas"]
        )
        if not result["ids"]:
            return None
        metadata = result["metadatas"][0]
        return _build_chunk(result["ids"][0], result["documents"][0], metadata, 0.0)


def _build_chunk(chunk_id: str, text: str, metadata: dict, distance: float) -> RetrievedChunk:
    authors = str(metadata.get("authors", "")).split("|") if metadata.get("authors") else []
    layer = int(metadata.get("layer", 1)) if metadata.get("layer") else 1
    layer_name = str(metadata.get("layer_name", "Layer 1: Foundational Knowledge"))
    layer_source = str(metadata.get("layer_source", "NCBI Bookshelf / StatPearls"))
    subtopic = str(metadata.get("subtopic", "")) if metadata.get("subtopic") else None

    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id=str(metadata.get("document_id", chunk_id)),
        source_id=str(metadata.get("source_id", chunk_id)),
        title=str(metadata.get("title", "Untitled")),
        authors=authors,
        year=int(metadata["year"]) if metadata.get("year") else None,
        journal=metadata.get("journal"),
        topic=str(metadata.get("topic", "neurology")),
        url=str(metadata.get("url", "")),
        doi=metadata.get("doi"),
        pmid=metadata.get("pmid"),
        pmcid=metadata.get("pmcid"),
        license=metadata.get("license"),
        section=metadata.get("section"),
        excerpt=text,
        relevance=max(0.0, min(1.0, 1.0 - float(distance))),
        layer=layer,
        layer_name=layer_name,
        layer_source=layer_source,
        subtopic=subtopic,
    )


def _tokens(text: str) -> Counter[str]:
    return Counter(TOKEN_PATTERN.findall(text.lower()))


def _bm25_score(
    query_tokens: Counter[str],
    doc_tokens: Counter[str],
    avg_len: float,
    doc_len: int,
    k1: float = 1.2,
    b: float = 0.75,
) -> float:
    score = 0.0
    for token, q_count in query_tokens.items():
        if token in doc_tokens:
            tf = doc_tokens[token]
            denom = tf + k1 * (1.0 - b + b * (doc_len / max(1.0, avg_len)))
            score += (tf * (k1 + 1.0) / max(0.001, denom)) * q_count
    return score


def _expand_clinical_concepts(tokens: Counter[str]) -> Counter[str]:
    expanded = Counter(tokens)
    for token in tokens:
        for key, cluster in SEMANTIC_CLINICAL_CLUSTERS.items():
            if token in cluster or token == key:
                for synonym in cluster:
                    expanded[synonym] += 0.5
    return expanded


def _cosine_counter(left: Counter[str], right: Counter[str]) -> float:
    numerator = sum(count * right[token] for token, count in left.items())
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    return numerator / (left_norm * right_norm) if left_norm and right_norm else 0.0


def _reciprocal_rank_fusion(
    sparse_scored: list[tuple[float, RetrievedChunk]],
    dense_scored: list[tuple[float, RetrievedChunk]],
    k: int = 60,
    alpha: float = 0.5,
) -> list[RetrievedChunk]:
    sparse_sorted = sorted(sparse_scored, key=lambda x: x[0], reverse=True)
    dense_sorted = sorted(dense_scored, key=lambda x: x[0], reverse=True)

    sparse_ranks = {chunk.chunk_id: rank for rank, (_, chunk) in enumerate(sparse_sorted)}
    dense_ranks = {chunk.chunk_id: rank for rank, (_, chunk) in enumerate(dense_sorted)}
    chunk_map = {chunk.chunk_id: chunk for _, chunk in sparse_scored}

    rrf_scores: dict[str, float] = {}
    for chunk_id, chunk in chunk_map.items():
        s_rank = sparse_ranks.get(chunk_id, len(sparse_sorted))
        d_rank = dense_ranks.get(chunk_id, len(dense_sorted))
        rrf = (1.0 - alpha) / (k + s_rank) + alpha / (k + d_rank)
        rrf_scores[chunk_id] = rrf

    # Normalize RRF scores to [0.0, 1.0] for relevance metric
    max_rrf = max(rrf_scores.values()) if rrf_scores else 1.0
    min_rrf = min(rrf_scores.values()) if rrf_scores else 0.0
    diff = max_rrf - min_rrf if max_rrf > min_rrf else 1.0

    scored_chunks: list[RetrievedChunk] = []
    for chunk_id, rrf in sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True):
        norm_score = (rrf - min_rrf) / diff
        scaled_relevance = round(0.5 + 0.5 * norm_score, 4)
        chunk = chunk_map[chunk_id]
        scored_chunks.append(chunk.model_copy(update={"relevance": scaled_relevance}))

    return scored_chunks


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
