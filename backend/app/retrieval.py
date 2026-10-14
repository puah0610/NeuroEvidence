import logging
import math
import re
from collections import Counter, defaultdict
from typing import Protocol, Any, Callable

from .config import Settings
from .demo_corpus import DEMO_CHUNKS
from .models import RetrievedChunk

logger = logging.getLogger(__name__)



TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

# Words with vital clinical or semantic significance in neurology that should NEVER be stripped
# to avoid sentence meaning distortion (e.g. negations, movement disorder states, lines of therapy)
CLINICAL_PROTECTED_WORDS = frozenset({
    "not", "no", "without",    # Clinical negations (e.g. "not recommended", "without aura")
    "off",                     # Movement disorder phenomena (e.g. "wearing-off", "off periods")
    "first",                   # Guideline lines of therapy (e.g. "first-line pharmacotherapy")
    "side",                    # Safety profiles (e.g. "side effects")
    "against",                 # Drug indications (e.g. "active against focal seizures")
    "well",                    # Tolerability (e.g. "well tolerated")
})

# Production stopword set: Standard scikit-learn English corpus with protected clinical terminology
STOPWORDS = frozenset(ENGLISH_STOP_WORDS - CLINICAL_PROTECTED_WORDS)

SYNONYM_EXPANSIONS = {
    "medication": ["pharmacotherapy", "pharmacology", "pharmacologic", "treatment", "drug", "medicine"],
    "medications": ["pharmacotherapy", "pharmacology", "pharmacologic", "treatment", "drugs", "medicines"],
    "medicine": ["pharmacotherapy", "pharmacology", "pharmacologic", "treatment", "drug", "medication"],
    "medicines": ["pharmacotherapy", "pharmacology", "pharmacologic", "treatment", "drugs", "medications"],
    "drug": ["pharmacotherapy", "pharmacology", "pharmacologic", "treatment", "medication", "medicine"],
    "drugs": ["pharmacotherapy", "pharmacology", "pharmacologic", "treatment", "medications", "medicines"],
    "treatment": ["pharmacotherapy", "management", "therapy", "firstline"],
    "control": ["manage", "management", "treatment", "pharmacotherapy"],
    "reason": ["pathophysiology", "mechanism", "neuropathology", "neurobiology", "dopaminergic"],
    "reasons": ["pathophysiology", "mechanism", "neuropathology", "neurobiology", "dopaminergic"],
    "why": ["pathophysiology", "mechanism", "neuropathology", "neurobiology", "dopaminergic"],
}

# Clinical semantic concept clusters for dense proxy retrieval in demo mode
SEMANTIC_CLINICAL_CLUSTERS = {
    "ilae": {"classification", "focal", "generalized", "seizure", "awareness", "motor", "epilepsy", "ilae"},
    "semiology": {"aura", "ictal", "postictal", "paroxysmal", "hypersynchronous", "discharge", "automatisms"},
    "mechanisms": {
        "sodium", "channel", "gaba", "sv2a", "calcium", "levetiracetam", "lamotrigine",
        "valproate", "carbamazepine", "ethosuximide", "asm", "asms", "antiseizure",
        "aed", "pharmacology", "monotherapy", "medication", "medicine", "drug"
    },
    "ng217": {
        "nice", "guideline", "ng217", "firstline", "first", "line", "monotherapy",
        "valproate", "teratogenicity", "pregnancy", "prevent", "treatment", "medication", "drug"
    },
    "sanad": {"sanad", "trial", "rct", "remission", "failure", "lancet", "comparative", "levetiracetam", "valproate", "lamotrigine"},
    "pathophysiology": {
        "substantia", "nigra", "dopamine", "dopaminergic", "synuclein", "lewy",
        "striatal", "putamen", "basal", "ganglia", "neuropathology", "snpc",
        "reason", "cause", "mechanism", "neurodegeneration", "pathophysiology"
    },
    "hoehn": {"hoehn", "yahr", "staging", "stage", "stages", "unilateral", "bilateral", "postural", "instability", "pull", "test", "progression"},
    "pharmacology": {
        "levodopa", "carbidopa", "benserazide", "agonist", "agonists", "pramipexole",
        "ropinirole", "rotigotine", "maob", "rasagiline", "selegiline", "safinamide",
        "comt", "entacapone", "opicapone", "medication", "medications", "medicine",
        "medicines", "drug", "drugs", "pharmacotherapy", "pharmacology", "pharmacologic",
        "treatment", "therapy", "firstline", "control", "prescribe"
    },
    "firstline_pd": {
        "firstline", "first", "line", "quality", "life", "levodopa", "agonist", "maob",
        "pharmacotherapy", "treatment", "medication", "medications", "control", "somnolence", "impulse"
    },
    "ng71": {"nice", "ng71", "guideline", "diagnosis", "brain", "bank", "datscan", "specialist", "referral", "assessment"},
    "dbs": {"dbs", "deep", "brain", "stimulation", "stn", "gpi", "subthalamic", "pallidus", "longterm", "efficacy", "updrs", "surgery", "surgical"},
    "fluctuations": {"wearing", "fluctuations", "dyskinesia", "comt", "maob", "entacapone", "opicapone", "rasagiline", "safinamide", "adjuvant"},
    "ddi_epilepsy": {"interaction", "polytherapy", "ugt", "ugt2b7", "sjs", "stevens", "johnson", "lamotrigine", "valproate", "enzyme", "inducer", "contraceptive", "polypharmacy"},
    "ddi_parkinson": {"metoclopramide", "haloperidol", "antagonist", "contraindicated", "chelation", "iron", "serotonin", "syndrome", "ssri", "hypertensive", "interaction", "antiemetic"},
}


class HyDEExpander:
    """Hypothetical Document Embeddings (HyDE) query expander.

    Calls the LLM to generate a short hypothetical clinical passage that
    would answer the user's question, then returns it for embedding.
    This passage is NEVER shown to the user — it is purely an internal
    retrieval signal to bridge the vocabulary gap between short queries
    and long clinical document chunks.

    Falls back silently to the original query if the LLM is unavailable
    or the call fails.
    """

    _SYSTEM_PROMPT = (
        "You are a biomedical retrieval assistant. "
        "Write exactly one short clinical passage (2-3 sentences, no bullet points, no headings) "
        "that directly and factually answers the following neurology question. "
        "Use precise clinical terminology (drug names, anatomical terms, guideline names). "
        "Do NOT diagnose or prescribe. Do NOT add citations or source labels."
    )

    def __init__(self, settings: Settings):
        self.settings = settings
        self._adapter: Any = None  # Lazy-loaded on first call

    def _get_adapter(self):
        """Lazy-load the LLM adapter only when HyDE is actually needed."""
        if self._adapter is None:
            from .llm import create_llm_adapter

            self._adapter = create_llm_adapter(self.settings)
        return self._adapter

    def expand(self, question: str) -> str:
        """Return a hypothetical clinical passage for the question, or the
        original question string if HyDE is unavailable or fails."""
        if not getattr(self.settings, "hyde_llm_available", False):
            return question
        try:
            adapter = self._get_adapter()
            output = adapter.generate_baseline(
                f"{self._SYSTEM_PROMPT}\n\nQuestion: {question}"
            )
            hypothetical = output.text.strip()
            # Safety check: if the LLM returns something very short or empty, fall back
            if len(hypothetical) > 30:
                logger.debug("HyDE generated hypothetical clinical passage for query: %s...", question[:40])
                return hypothetical
            return question
        except Exception as exc:
            logger.warning("HyDE query expansion failed; falling back to original question: %s", exc)
            return question  # Always fall back gracefully


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class TransformerDenseEmbedder:
    """Biomedical Dense Bi-Encoder utilizing Sentence-Transformers (pritamdeka/S-PubMedBert-MS-MARCO)."""

    _instance: Any = None
    _cached_model_name: str | None = None
    _demo_embeddings_cache: dict[str, Any] = {}

    def __init__(self, model_name: str = "pritamdeka/S-PubMedBert-MS-MARCO"):
        self.model_name = model_name

    @classmethod
    def get_model(cls, model_name: str):
        if cls._instance is None or cls._cached_model_name != model_name:
            from sentence_transformers import SentenceTransformer

            cls._instance = SentenceTransformer(model_name)
            cls._cached_model_name = model_name
        return cls._instance

    def embed(self, texts: list[str]) -> list[list[float]]:
        model = self.get_model(self.model_name)
        embs = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return embs.tolist()

    def get_demo_chunk_embeddings(self, candidates: list[RetrievedChunk]):
        import numpy as np

        model = self.get_model(self.model_name)
        cache_key = f"{self.model_name}::{len(candidates)}"
        if cache_key not in self._demo_embeddings_cache:
            texts = [
                f"Topic: {c.topic}. Document: {c.title}. Section: {c.section or c.subtopic or ''}. Excerpt: {c.excerpt}"
                for c in candidates
            ]
            embs = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
            self._demo_embeddings_cache[cache_key] = embs
        return self._demo_embeddings_cache[cache_key]

    def score_candidates(
        self, query: str, candidates: list[RetrievedChunk]
    ) -> list[tuple[float, RetrievedChunk]]:
        import numpy as np

        if not candidates:
            return []
        model = self.get_model(self.model_name)
        q_emb = model.encode([query], convert_to_numpy=True, normalize_embeddings=True)[0]
        cand_embs = self.get_demo_chunk_embeddings(candidates)
        # Cosine similarity is dot product because vectors are normalized
        sims = np.dot(cand_embs, q_emb)
        return [
            (float(sim) * (1.15 if chunk.chunk_id.startswith("TRIAD-") else 1.0), chunk)
            for sim, chunk in zip(sims, candidates)
        ]


class NeuralReranker:
    """Cross-Encoder Transformer for deep contextual and syntactic query-passage reranking."""

    _instance: Any = None
    _cached_model_name: str | None = None

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name

    @classmethod
    def get_model(cls, model_name: str):
        if cls._instance is None or cls._cached_model_name != model_name:
            from sentence_transformers import CrossEncoder

            cls._instance = CrossEncoder(model_name)
            cls._cached_model_name = model_name
        return cls._instance

    def rerank(
        self, query: str, candidates: list[RetrievedChunk], top_k: int
    ) -> list[RetrievedChunk]:
        if not candidates:
            return []
        import numpy as np

        try:
            model = self.get_model(self.model_name)
            pairs = [
                (
                    query,
                    (
                        f"Topic: {c.topic}. Document: {c.title}. "
                        f"Section: {c.section or c.subtopic or 'Clinical Guidance'}. "
                        f"Hierarchy: {' > '.join(c.breadcrumb) if c.breadcrumb else c.topic}. "
                        f"Content: {c.excerpt}"
                    ),
                )
                for c in candidates
            ]
            raw_scores = np.asarray(model.predict(pairs)).astype(float)

            ce_scored: list[tuple[float, RetrievedChunk]] = []
            for score, chunk in zip(raw_scores, candidates):
                triad_boost = 3.0 if chunk.chunk_id.startswith("TRIAD-") else 0.0
                ce_scored.append((float(score) + triad_boost, chunk))

            # Two-Stage RRF: fuse Stage 1 (Biomedical S-PubMedBert + BM25) with Stage 2 (Cross-Encoder syntax)
            s1_scored = [(chunk.relevance, chunk) for chunk in candidates]
            two_stage_fused = _reciprocal_rank_fusion(
                s1_scored,
                ce_scored,
                k=60,
                alpha=0.30,  # 70% Stage 1 (Biomedical) + 30% Stage 2 (Cross-Encoder syntax)
            )
            return two_stage_fused[:top_k]
        except Exception:
            return candidates[:top_k]


class DemoRetriever:
    """Two-Stage Hybrid Dense + Sparse Retriever with Neural Cross-Encoder Reranking."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._hyde = (
            HyDEExpander(settings)
            if getattr(settings, "enable_hyde", True)
            else None
        )
        self._embedder = (
            TransformerDenseEmbedder(settings.dense_model)
            if getattr(settings, "enable_dense_embeddings", True)
            else None
        )
        self._reranker = (
            NeuralReranker(settings.reranker_model)
            if getattr(settings, "enable_reranker", True)
            else None
        )

    def search(self, question: str, topic: str | None = None) -> list[RetrievedChunk]:
        dense_query = self._hyde.expand(question) if self._hyde else question
        query_tokens = _tokens(question)
        sparse_query = _expand_sparse_tokens(query_tokens)
        candidates = [
            chunk for chunk in DEMO_CHUNKS
            if not topic or chunk.topic == topic
        ]
        if not candidates:
            return []

        N = len(candidates)
        avg_len = sum(len(_tokens(c.excerpt)) for c in candidates) / max(1, N)

        # Precompute document tokens with field weights (headers get 2x weight) and document frequencies
        doc_tokens_list: list[tuple[RetrievedChunk, Counter[str], int]] = []
        doc_freqs: Counter[str] = Counter()
        for chunk in candidates:
            header_tokens = _tokens(f"{chunk.title} {chunk.subtopic or ''} {chunk.section or ''}")
            body_tokens = _tokens(chunk.excerpt)
            combined = Counter(body_tokens)
            for ht, cnt in header_tokens.items():
                combined[ht] += cnt * 2
            doc_tokens_list.append((chunk, combined, len(body_tokens)))
            for t in set(combined.keys()):
                doc_freqs[t] += 1

        # 1. Sparse BM25 / token scoring with IDF and field weighting
        sparse_scores: list[tuple[float, RetrievedChunk]] = []
        for chunk, combined, body_len in doc_tokens_list:
            bm25 = _bm25_score(sparse_query, combined, avg_len, body_len, doc_freqs, N)
            if chunk.chunk_id.startswith("TRIAD-"):
                bm25 *= 1.35
            sparse_scores.append((bm25, chunk))

        # 2. Dense semantic similarity: Transformer Bi-Encoder (S-PubMedBert) with fallback
        dense_scores: list[tuple[float, RetrievedChunk]] = []
        if self._embedder is not None:
            try:
                dense_scores = self._embedder.score_candidates(dense_query, candidates)
            except Exception:
                dense_scores = []

        if not dense_scores:
            dense_tokens = _tokens(dense_query)
            expanded_query = _expand_clinical_concepts(dense_tokens)
            for chunk, combined, _ in doc_tokens_list:
                expanded_doc = _expand_clinical_concepts(combined)
                semantic_sim = _cosine_counter(expanded_query, expanded_doc)
                if chunk.chunk_id.startswith("TRIAD-"):
                    semantic_sim *= 1.1
                dense_scores.append((semantic_sim, chunk))

        # 3. Reciprocal Rank Fusion (RRF) -> Candidate Pool
        fused = _reciprocal_rank_fusion(sparse_scores, dense_scores, k=60, alpha=0.5)

        # 4. Neural Cross-Encoder Reranking
        candidate_pool = fused[: getattr(self.settings, "reranker_top_n", 20)]
        if self._reranker is not None:
            reranked = self._reranker.rerank(
                question, candidate_pool, top_k=self.settings.retrieval_top_k * 2
            )
        else:
            reranked = candidate_pool

        # 5. Small-to-Big Parent Section Expansion
        return expand_to_parent_chunks(
            reranked,
            self.settings.retrieval_top_k,
            self.settings.max_chunks_per_document,
            corpus_lookup=self._demo_parent_lookup,
            token_budget=getattr(self.settings, "parent_expansion_token_budget", 750),
        )

    def _demo_parent_lookup(self, target_chunk: RetrievedChunk) -> list[RetrievedChunk]:
        pid = target_chunk.parent_id or f"{target_chunk.document_id}::{target_chunk.section or 'main'}"
        return [
            c for c in DEMO_CHUNKS
            if (c.parent_id == pid or (c.document_id == target_chunk.document_id and c.section == target_chunk.section))
        ]

    def get_source(self, source_id: str) -> RetrievedChunk | None:
        return next((item for item in DEMO_CHUNKS if item.source_id == source_id), None)


class ChromaRetriever:
    """Hybrid Dense + Sparse Retriever using ChromaDB dense embeddings, BM25 sparse ranking, and Neural Reranking."""

    def __init__(self, settings: Settings, embedder: Embedder):
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        self.settings = settings
        self.embedder = embedder
        self._hyde = (
            HyDEExpander(settings)
            if getattr(settings, "enable_hyde", True)
            else None
        )
        self.client = chromadb.PersistentClient(
            path=str(settings.chroma_path),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=settings.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )
        self._reranker = (
            NeuralReranker(settings.reranker_model)
            if getattr(settings, "enable_reranker", True)
            else None
        )

    def search(self, question: str, topic: str | None = None) -> list[RetrievedChunk]:
        if self.collection.count() == 0:
            return DemoRetriever(self.settings).search(question, topic)

        dense_query = self._hyde.expand(question) if self._hyde else question
        query_embedding = self.embedder.embed([dense_query])[0]
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
        if not result["ids"] or not result["ids"][0]:
            return DemoRetriever(self.settings).search(question, topic)

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
        sparse_query = _expand_sparse_tokens(query_tokens)
        N = len(dense_list)
        avg_len = sum(len(_tokens(c.excerpt)) for _, c in dense_list) / max(1, N)

        doc_tokens_list: list[tuple[RetrievedChunk, Counter[str], int]] = []
        doc_freqs: Counter[str] = Counter()
        for _, chunk in dense_list:
            header_tokens = _tokens(f"{chunk.title} {chunk.subtopic or ''} {chunk.section or ''}")
            body_tokens = _tokens(chunk.excerpt)
            combined = Counter(body_tokens)
            for ht, cnt in header_tokens.items():
                combined[ht] += cnt * 2
            doc_tokens_list.append((chunk, combined, len(body_tokens)))
            for t in set(combined.keys()):
                doc_freqs[t] += 1

        sparse_list: list[tuple[float, RetrievedChunk]] = []
        for chunk, combined, body_len in doc_tokens_list:
            score = _bm25_score(sparse_query, combined, avg_len, body_len, doc_freqs, N)
            if chunk.chunk_id.startswith("TRIAD-"):
                score *= 1.35
            sparse_list.append((score, chunk))

        # Reciprocal Rank Fusion
        fused = _reciprocal_rank_fusion(sparse_list, dense_list, k=60, alpha=0.5)

        # Neural Cross-Encoder Reranking
        candidate_pool = fused[: getattr(self.settings, "reranker_top_n", 20)]
        if self._reranker is not None:
            reranked = self._reranker.rerank(
                question, candidate_pool, top_k=self.settings.retrieval_top_k * 2
            )
        else:
            reranked = candidate_pool

        parent_expanded = expand_to_parent_chunks(
            reranked,
            self.settings.retrieval_top_k,
            self.settings.max_chunks_per_document,
            corpus_lookup=self._chroma_parent_lookup,
            token_budget=getattr(self.settings, "parent_expansion_token_budget", 750),
        )
        return parent_expanded if parent_expanded else DemoRetriever(self.settings).search(question, topic)

    def _chroma_parent_lookup(self, target_chunk: RetrievedChunk) -> list[RetrievedChunk]:
        pid = target_chunk.parent_id or f"{target_chunk.document_id}::{target_chunk.section or 'main'}"
        if self.collection.count() > 0:
            try:
                res = self.collection.get(
                    where={"parent_id": pid},
                    include=["documents", "metadatas"],
                )
                if res["ids"]:
                    return [
                        _build_chunk(cid, doc, meta, 0.0)
                        for cid, doc, meta in zip(res["ids"], res["documents"], res["metadatas"])
                    ]
            except Exception as e:
                logger.debug("ChromaDB parent lookup error: %s", e)
        return [
            c for c in DEMO_CHUNKS
            if (c.parent_id == pid or (c.document_id == target_chunk.document_id and c.section == target_chunk.section))
        ]

    def get_source(self, source_id: str) -> RetrievedChunk | None:
        if self.collection.count() > 0:
            result = self.collection.get(
                where={"source_id": source_id}, limit=1, include=["documents", "metadatas"]
            )
            if result["ids"]:
                metadata = result["metadatas"][0]
                return _build_chunk(result["ids"][0], result["documents"][0], metadata, 0.0)
        return next((item for item in DEMO_CHUNKS if item.source_id == source_id), None)


def _estimate_tokens(text: str) -> int:
    return len(re.findall(r"\S+", text))


def _assemble_bounded_parent_excerpt(
    target_chunk: RetrievedChunk,
    siblings: list[RetrievedChunk],
    token_budget: int = 750,
) -> str:
    """Assembles a bounded parent section around target_chunk using siblings up to token_budget.
    Recovers preceding definitions/qualifications and following study context without overwhelming context.
    """
    if not siblings:
        return target_chunk.excerpt

    def _clean_txt(item: RetrievedChunk) -> str:
        txt = item.excerpt.strip()
        if txt.startswith("### ["):
            parts = txt.split("\n\n", 1)
            if len(parts) > 1:
                txt = parts[1].strip()
        return txt

    if len(siblings) == 1:
        return _clean_txt(siblings[0])

    clean_siblings = [(s, _clean_txt(s)) for s in siblings]

    target_idx = -1
    for i, (s, _) in enumerate(clean_siblings):
        if s.chunk_id == target_chunk.chunk_id:
            target_idx = i
            break

    if target_idx == -1:
        target_raw = _clean_txt(target_chunk)
        for i, (_, txt) in enumerate(clean_siblings):
            if target_raw in txt or txt in target_raw:
                target_idx = i
                break

    if target_idx == -1:
        assembled = [_clean_txt(target_chunk)]
        curr_tokens = _estimate_tokens(assembled[0])
        for _, txt in clean_siblings:
            tokens = _estimate_tokens(txt)
            if txt not in assembled[0] and (curr_tokens + tokens) <= token_budget:
                assembled.append(txt)
                curr_tokens += tokens
        return "\n\n".join(assembled)

    selected_indices = [target_idx]
    curr_tokens = _estimate_tokens(clean_siblings[target_idx][1])
    left_ptr = target_idx - 1
    right_ptr = target_idx + 1

    while (left_ptr >= 0 or right_ptr < len(clean_siblings)) and curr_tokens < token_budget:
        if left_ptr >= 0:
            left_txt = clean_siblings[left_ptr][1]
            left_tok = _estimate_tokens(left_txt)
            if curr_tokens + left_tok <= token_budget:
                selected_indices.insert(0, left_ptr)
                curr_tokens += left_tok
                left_ptr -= 1
            else:
                left_ptr = -1

        if right_ptr < len(clean_siblings):
            right_txt = clean_siblings[right_ptr][1]
            right_tok = _estimate_tokens(right_txt)
            if curr_tokens + right_tok <= token_budget:
                selected_indices.append(right_ptr)
                curr_tokens += right_tok
                right_ptr += 1
            else:
                right_ptr = len(clean_siblings)

        if left_ptr < 0 and right_ptr >= len(clean_siblings):
            break

    assembled_parts = [clean_siblings[i][1] for i in selected_indices if clean_siblings[i][1]]
    return "\n\n".join(assembled_parts)


def expand_to_parent_chunks(
    fused: list[RetrievedChunk],
    top_k: int,
    max_per_document: int = 3,
    corpus_lookup: Callable[[RetrievedChunk], list[RetrievedChunk]] | None = None,
    token_budget: int = 750,
) -> list[RetrievedChunk]:
    """Hierarchical Small-to-Big expansion:
    Maps matched child chunks to their direct Parent Section context with breadcrumbs,
    fetching neighboring sibling chunks within a token budget to recover omitted definitions
    and study qualifications, while consolidating multi-chunk matches from the same parent.
    """
    seen_parents: dict[str, RetrievedChunk] = {}
    doc_counts: defaultdict[str, int] = defaultdict(int)
    results: list[RetrievedChunk] = []

    for chunk in fused:
        pid = chunk.parent_id or f"{chunk.document_id}::{chunk.section or 'main'}"
        if pid not in seen_parents:
            if doc_counts[chunk.document_id] >= max_per_document:
                continue

            breadcrumb_str = " > ".join(chunk.breadcrumb) if chunk.breadcrumb else chunk.title

            if corpus_lookup is not None:
                try:
                    siblings = corpus_lookup(chunk)
                except Exception as e:
                    logger.debug("Corpus lookup failed for chunk %s: %s", chunk.chunk_id, e)
                    siblings = [chunk]
                assembled_excerpt = _assemble_bounded_parent_excerpt(chunk, siblings, token_budget=token_budget)
            else:
                assembled_excerpt = chunk.excerpt

            parent_excerpt = (
                f"### [{breadcrumb_str}]\n"
                f"**Document:** {chunk.title}\n"
                f"**Section:** {chunk.section or chunk.subtopic or 'Clinical Guidance'}\n\n"
                f"{assembled_excerpt}"
            )
            parent_chunk = chunk.model_copy(update={
                "excerpt": parent_excerpt,
                "relevance": chunk.relevance,
                "parent_id": pid,
            })
            seen_parents[pid] = parent_chunk
            results.append(parent_chunk)
            doc_counts[chunk.document_id] += 1
        else:
            existing = seen_parents[pid]
            clean_chunk_excerpt = chunk.excerpt
            if clean_chunk_excerpt.startswith("### ["):
                parts = clean_chunk_excerpt.split("\n\n", 1)
                if len(parts) > 1:
                    clean_chunk_excerpt = parts[1].strip()
            if clean_chunk_excerpt not in existing.excerpt:
                if _estimate_tokens(existing.excerpt) + _estimate_tokens(clean_chunk_excerpt) <= int(token_budget * 1.5):
                    existing.excerpt = f"{existing.excerpt}\n\n{clean_chunk_excerpt}"

        if len(results) >= top_k:
            break

    return results


def _build_chunk(chunk_id: str, text: str, metadata: dict, distance: float) -> RetrievedChunk:
    authors = str(metadata.get("authors", "")).split("|") if metadata.get("authors") else []
    layer = int(metadata.get("layer", 1)) if metadata.get("layer") else 1
    layer_name = str(metadata.get("layer_name", "Layer 1: Foundational Knowledge"))
    layer_source = str(metadata.get("layer_source", "NCBI Bookshelf / StatPearls"))
    subtopic = str(metadata.get("subtopic", "")) if metadata.get("subtopic") else None

    raw_breadcrumbs = metadata.get("breadcrumb")
    if isinstance(raw_breadcrumbs, list):
        breadcrumb = raw_breadcrumbs
    elif isinstance(raw_breadcrumbs, str) and raw_breadcrumbs:
        breadcrumb = [b.strip() for b in raw_breadcrumbs.split(">")]
    else:
        breadcrumb = [
            layer_name.split(":")[0],
            str(metadata.get("topic", "neurology")).title(),
            subtopic or "Clinical Principles",
            str(metadata.get("title", "Untitled")),
        ]

    parent_id = str(metadata.get("parent_id", f"{metadata.get('document_id', chunk_id)}::{metadata.get('section', 'main')}"))
    parent_title = str(metadata.get("parent_title", f"{metadata.get('title', 'Untitled')} - {metadata.get('section', 'Section')}"))

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
        parent_id=parent_id,
        parent_title=parent_title,
        breadcrumb=breadcrumb,
    )


def _tokens(text: str, remove_stopwords: bool = True) -> Counter[str]:
    raw = TOKEN_PATTERN.findall(text.lower())
    if remove_stopwords:
        return Counter(t for t in raw if t not in STOPWORDS)
    return Counter(raw)


def _expand_sparse_tokens(tokens: Counter[str]) -> Counter[str]:
    expanded = Counter(tokens)
    for token in tokens:
        if token in SYNONYM_EXPANSIONS:
            for syn in SYNONYM_EXPANSIONS[token]:
                if syn not in STOPWORDS:
                    expanded[syn] += 0.7
    return expanded


def _bm25_score(
    query_tokens: Counter[str],
    doc_tokens: Counter[str],
    avg_len: float,
    doc_len: int,
    doc_freqs: Counter[str] | None = None,
    num_docs: int = 1,
    k1: float = 1.2,
    b: float = 0.75,
) -> float:
    score = 0.0
    for token, q_count in query_tokens.items():
        if token in doc_tokens:
            tf = doc_tokens[token]
            df = doc_freqs.get(token, 1) if doc_freqs else 1
            idf = math.log(1.0 + (num_docs - df + 0.5) / (df + 0.5)) if (doc_freqs and num_docs > 1) else 1.0
            denom = tf + k1 * (1.0 - b + b * (doc_len / max(1.0, avg_len)))
            score += idf * (tf * (k1 + 1.0) / max(0.001, denom)) * q_count
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
