"""Hybrid Retrieval Engine combining Dense Vector Search and Sparse BM25.

Supports:
1. Reciprocal Rank Fusion (RRF):
   RRF_Score(d) = sum_{m in {dense, sparse}} (w_m / (k + rank_m(d)))
   where k = 60 (standard Cormack et al. constant).
2. Convex Combination (Score Normalization + Alpha Weighting):
   Score(d) = alpha * DenseNorm(d) + (1 - alpha) * SparseNorm(d)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from rag_chatbot.retrieval.bm25 import BM25SearchEngine
from rag_chatbot.vector_store.embeddings import BaseEmbedder
from rag_chatbot.vector_store.faiss_store import FAISSVectorStore

logger = logging.getLogger(__name__)


def _normalize_hit(hit: Any) -> Dict[str, Any]:
    """Normalize SearchResult dataclass or dict into uniform dictionary."""
    if isinstance(hit, dict):
        meta = hit.get("metadata", {})
        cid = hit.get("chunk_id") or meta.get("chunk_id") or str(hash(hit.get("text", "")))
        return {
            "chunk_id": cid,
            "score": float(hit.get("score", 0.0)),
            "text": hit.get("text", ""),
            "metadata": meta if meta else {
                "chunk_id": cid,
                "policy_type": hit.get("policy_type", ""),
                "section_title": hit.get("section_title", ""),
                "clause_title": hit.get("clause_title", ""),
                "breadcrumb": hit.get("breadcrumb", ""),
            },
        }
    else:
        cid = getattr(hit, "chunk_id", str(hash(getattr(hit, "text", ""))))
        meta = getattr(hit, "metadata", {}) or {}
        combined_meta = {
            "chunk_id": cid,
            "policy_type": getattr(hit, "policy_type", ""),
            "section_title": getattr(hit, "section_title", ""),
            "clause_title": getattr(hit, "clause_title", ""),
            "breadcrumb": getattr(hit, "breadcrumb", ""),
            **meta,
        }
        return {
            "chunk_id": cid,
            "score": float(getattr(hit, "score", 0.0)),
            "text": getattr(hit, "text", ""),
            "metadata": combined_meta,
        }


class HybridRetriever:
    """Combines Dense Vector and Sparse BM25 retrieval for high-precision RAG."""

    def __init__(
        self,
        vector_store: FAISSVectorStore,
        bm25_engine: BM25SearchEngine,
        embedder: Optional[BaseEmbedder] = None,
    ):
        self.vector_store = vector_store
        self.bm25_engine = bm25_engine
        self.embedder = embedder or getattr(vector_store, "embedder", None)

    def search(
        self,
        query: str,
        top_k: int = 5,
        policy_type_filter: Optional[str] = None,
        mode: str = "rrf",
        alpha: float = 0.5,
        rrf_k: int = 60,
        candidate_multiplier: int = 3,
    ) -> List[Dict[str, Any]]:
        """Execute hybrid search combining dense and sparse results."""
        candidate_k = max(top_k * candidate_multiplier, 10)

        # 1. Sparse BM25 Search
        raw_sparse_hits = self.bm25_engine.search(
            query=query,
            top_k=candidate_k,
            policy_type_filter=policy_type_filter,
        )
        sparse_hits = [_normalize_hit(h) for h in raw_sparse_hits]

        # 2. Dense Vector Search
        raw_dense_hits = self.vector_store.search(
            query=query,
            top_k=candidate_k,
            policy_type_filter=policy_type_filter,
        )
        dense_hits = [_normalize_hit(h) for h in raw_dense_hits]

        if mode == "convex":
            return self._convex_fusion(dense_hits, sparse_hits, alpha=alpha, top_k=top_k)
        else:
            return self._rrf_fusion(dense_hits, sparse_hits, rrf_k=rrf_k, top_k=top_k)

    def _rrf_fusion(
        self,
        dense_hits: List[Dict[str, Any]],
        sparse_hits: List[Dict[str, Any]],
        rrf_k: int,
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """Reciprocal Rank Fusion: RRF(d) = sum( 1 / (k + rank) )."""
        fused_scores: Dict[str, float] = {}
        items_by_id: Dict[str, Dict[str, Any]] = {}
        dense_ranks: Dict[str, int] = {}
        sparse_ranks: Dict[str, int] = {}
        dense_scores: Dict[str, float] = {}
        sparse_scores: Dict[str, float] = {}

        for rank, hit in enumerate(dense_hits, start=1):
            chunk_id = hit["metadata"].get("chunk_id", str(hash(hit["text"])))
            dense_ranks[chunk_id] = rank
            dense_scores[chunk_id] = hit.get("score", 0.0)
            items_by_id[chunk_id] = hit
            fused_scores[chunk_id] = fused_scores.get(chunk_id, 0.0) + (1.0 / (rrf_k + rank))

        for rank, hit in enumerate(sparse_hits, start=1):
            chunk_id = hit["metadata"].get("chunk_id", str(hash(hit["text"])))
            sparse_ranks[chunk_id] = rank
            sparse_scores[chunk_id] = hit.get("score", 0.0)
            if chunk_id not in items_by_id:
                items_by_id[chunk_id] = hit
            fused_scores[chunk_id] = fused_scores.get(chunk_id, 0.0) + (1.0 / (rrf_k + rank))

        sorted_ids = sorted(fused_scores.keys(), key=lambda cid: fused_scores[cid], reverse=True)
        results = []

        for final_rank, cid in enumerate(sorted_ids[:top_k], start=1):
            hit = items_by_id[cid]
            results.append({
                "rank": final_rank,
                "fused_score": round(fused_scores[cid], 6),
                "dense_rank": dense_ranks.get(cid),
                "sparse_rank": sparse_ranks.get(cid),
                "dense_score": round(dense_scores.get(cid, 0.0), 4),
                "sparse_score": round(sparse_scores.get(cid, 0.0), 4),
                "text": hit["text"],
                "metadata": hit["metadata"],
            })

        return results

    def _convex_fusion(
        self,
        dense_hits: List[Dict[str, Any]],
        sparse_hits: List[Dict[str, Any]],
        alpha: float,
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """Convex linear fusion with min-max normalization."""
        # Normalize dense scores
        dense_map = {}
        if dense_hits:
            d_scores = [h["score"] for h in dense_hits]
            min_d, max_d = min(d_scores), max(d_scores)
            span_d = (max_d - min_d) if (max_d - min_d) > 1e-6 else 1.0
            for h in dense_hits:
                cid = h["metadata"].get("chunk_id", str(hash(h["text"])))
                dense_map[cid] = {
                    "norm": (h["score"] - min_d) / span_d,
                    "raw": h["score"],
                    "hit": h,
                }

        # Normalize sparse scores
        sparse_map = {}
        if sparse_hits:
            s_scores = [h["score"] for h in sparse_hits]
            min_s, max_s = min(s_scores), max(s_scores)
            span_s = (max_s - min_s) if (max_s - min_s) > 1e-6 else 1.0
            for h in sparse_hits:
                cid = h["metadata"].get("chunk_id", str(hash(h["text"])))
                sparse_map[cid] = {
                    "norm": (h["score"] - min_s) / span_s,
                    "raw": h["score"],
                    "hit": h,
                }

        all_cids = set(dense_map.keys()) | set(sparse_map.keys())
        scored: List[tuple[str, float]] = []

        for cid in all_cids:
            d_norm = dense_map[cid]["norm"] if cid in dense_map else 0.0
            s_norm = sparse_map[cid]["norm"] if cid in sparse_map else 0.0
            score = (alpha * d_norm) + ((1.0 - alpha) * s_norm)
            scored.append((cid, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        results = []

        for rank, (cid, score) in enumerate(scored[:top_k], start=1):
            hit = dense_map[cid]["hit"] if cid in dense_map else sparse_map[cid]["hit"]
            results.append({
                "rank": rank,
                "fused_score": round(score, 4),
                "dense_score": round(dense_map[cid]["raw"], 4) if cid in dense_map else 0.0,
                "sparse_score": round(sparse_map[cid]["raw"], 4) if cid in sparse_map else 0.0,
                "text": hit["text"],
                "metadata": hit["metadata"],
            })

        return results
