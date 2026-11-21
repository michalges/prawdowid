"""Hybrid retrieval: FTS5 BM25 + vector similarity, fused with Reciprocal Rank Fusion."""

import asyncio
from dataclasses import dataclass

from prawdowid.core.evidence import Evidence
from prawdowid.core.text import get_index_text, get_lexical_overlap
from prawdowid.corpus.models import CorpusChunk
from prawdowid.corpus.store import LoadedCorpus
from prawdowid.providers.embeddings.base import EmbeddingProvider

RRF_K = 60
CANDIDATES_PER_RETRIEVER = 40
LEXICAL_WEIGHT = 0.6
VECTOR_WEIGHT = 0.4


class RetrievalError(Exception):
    pass


@dataclass(frozen=True)
class ScoredChunk:
    chunk: CorpusChunk
    fused_score: float
    relevance: float


def get_fused_ranking(*rankings: list[tuple[int, float]]) -> dict[int, float]:
    fused: dict[int, float] = {}
    for ranking in rankings:
        for rank, (chunk_id, _score) in enumerate(ranking):
            fused[chunk_id] = fused.get(chunk_id, 0.0) + 1.0 / (RRF_K + rank + 1)
    return fused


@dataclass
class HybridRetriever:
    corpus: LoadedCorpus
    embedder: EmbeddingProvider
    min_relevance: float

    @property
    def is_ready(self) -> bool:
        return self.corpus.chunk_count > 0

    async def search(self, query: str, top_k: int) -> list[ScoredChunk]:
        try:
            return await asyncio.to_thread(self._search, query, top_k)
        except Exception as error:
            raise RetrievalError(str(error)) from error

    def _search(self, query: str, top_k: int) -> list[ScoredChunk]:
        lexical = self.corpus.search_fts(get_index_text(query), CANDIDATES_PER_RETRIEVER)
        query_vector = self.embedder.embed([query], "query")[0]
        vector = self.corpus.search_vectors(query_vector, CANDIDATES_PER_RETRIEVER)
        vector_scores = dict(vector)
        fused = get_fused_ranking(lexical, vector)
        ranked_ids = sorted(fused, key=lambda chunk_id: -fused[chunk_id])[: top_k * 3]
        chunks = self.corpus.get_chunks(ranked_ids)
        scored: list[ScoredChunk] = []
        for chunk_id in ranked_ids:
            chunk = chunks.get(chunk_id)
            if chunk is None:
                continue
            relevance = self._get_relevance(query, chunk, vector_scores, query_vector)
            if relevance >= self.min_relevance:
                scored.append(ScoredChunk(chunk, fused[chunk_id], relevance))
        scored.sort(key=lambda item: -item.relevance)
        return scored[:top_k]

    def _get_relevance(
        self, query: str, chunk: CorpusChunk, vector_scores: dict[int, float], query_vector
    ) -> float:
        """Absolute (not rank-based) relevance used by the abstention gate."""
        if chunk.chunk_id in vector_scores:
            similarity = vector_scores[chunk.chunk_id]
        else:
            stored = self.corpus.get_vector(chunk.chunk_id)
            similarity = float(stored @ query_vector) if stored is not None else 0.0
        overlap = get_lexical_overlap(query, f"{chunk.title} {chunk.text}")
        return LEXICAL_WEIGHT * overlap + VECTOR_WEIGHT * max(similarity, 0.0)


def get_evidence(scored_chunks: list[ScoredChunk], start_index: int = 1) -> list[Evidence]:
    return [
        Evidence(
            evidence_id=f"e{start_index + i}",
            text=item.chunk.text,
            title=item.chunk.title,
            publisher=item.chunk.publisher,
            url=item.chunk.url,
            published_at=item.chunk.published_at,
            retrieved_at=item.chunk.retrieved_at,
            source_type=item.chunk.source_type,
            quality_tier=item.chunk.quality_tier,
            source_id=item.chunk.source_id,
            relevance=round(item.relevance, 3),
            time_sensitive=item.chunk.time_sensitive,
            chunk_id=item.chunk.chunk_id,
        )
        for i, item in enumerate(scored_chunks)
    ]
