"""Policy Retrieval Service.

Loads indexed policy data and orchestrates BM25, FAISS, and Reranking
into a unified, ready-to-query interface for FastAPI endpoints and chat engines.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from rag_chatbot.retrieval.bm25 import BM25SearchEngine
from rag_chatbot.retrieval.hybrid import HybridRetriever
from rag_chatbot.retrieval.reranker import ContextReranker
from rag_chatbot.vector_store.embeddings import BaseEmbedder, get_default_embedder
from rag_chatbot.vector_store.faiss_store import FAISSVectorStore

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_INDEX_DIR = PROJECT_ROOT / "data" / "vector_store"
DEFAULT_MANIFEST_PATH = Path(__file__).resolve().parent.parent / "data" / "chunks_manifest.json"


class PolicyRetrievalService:
    """Production service for querying policy knowledge base with hybrid search."""

    def __init__(
        self,
        hybrid_retriever: HybridRetriever,
        reranker: ContextReranker,
    ):
        self.retriever = hybrid_retriever
        self.reranker = reranker

    @classmethod
    def from_artifacts(
        cls,
        index_dir: Path = DEFAULT_INDEX_DIR,
        manifest_path: Path = DEFAULT_MANIFEST_PATH,
        embedder: Optional[BaseEmbedder] = None,
    ) -> PolicyRetrievalService:
        """Initialize service from persisted vector store and chunks manifest."""
        embedder = embedder or get_default_embedder()

        # 1. Load Vector Store
        index_bin = index_dir / "faiss_policy_index.bin"
        metadata_json = index_dir / "faiss_metadata.json"
        vector_store = FAISSVectorStore.load(
            index_path=index_bin,
            metadata_path=metadata_json,
            embedder=embedder,
        )

        # 2. Load Manifest & Build BM25 Engine
        if not manifest_path.exists():
            raise FileNotFoundError(f"Chunks manifest not found at: {manifest_path}")

        with open(manifest_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        chunks = raw_data.get("chunks", raw_data) if isinstance(raw_data, dict) else raw_data

        documents = [c.get("text", c.get("chunk_text", "")) for c in chunks]
        metadata = [
            {
                "chunk_id": c.get("chunk_id", ""),
                "document_id": c.get("document_id", ""),
                "policy_type": c.get("policy_type", ""),
                "section_title": c.get("section_title", ""),
                "clause_title": c.get("clause_title", ""),
                "breadcrumb": c.get("breadcrumb", ""),
                **(c.get("metadata") or {}),
            }
            for c in chunks
        ]

        bm25_engine = BM25SearchEngine().fit(documents, metadata)

        # 3. Assemble Hybrid Retriever & Reranker
        hybrid_retriever = HybridRetriever(
            vector_store=vector_store,
            bm25_engine=bm25_engine,
            embedder=embedder,
        )
        reranker = ContextReranker()

        return cls(hybrid_retriever=hybrid_retriever, reranker=reranker)

    def retrieve(
        self,
        query: str,
        policy_type: Optional[str] = None,
        top_k: int = 3,
        candidate_k: int = 8,
    ) -> Dict[str, Any]:
        """Perform end-to-end hybrid retrieval with reranking and formatted context prompt.
        
        Returns:
            Dictionary containing:
            - 'query': original query
            - 'policy_type': applied filter
            - 'chunks': top reranked chunks with citations & scores
            - 'formatted_context': ready-to-inject Markdown context string
        """
        candidates = self.retriever.search(
            query=query,
            top_k=candidate_k,
            policy_type_filter=policy_type,
            mode="rrf",
        )

        reranked = self.reranker.rerank(
            query=query,
            candidates=candidates,
            top_k=top_k,
        )

        formatted_context = self.reranker.format_context_for_prompt(reranked)

        return {
            "query": query,
            "policy_type": policy_type,
            "total_candidates": len(candidates),
            "chunks": reranked,
            "formatted_context": formatted_context,
        }


def main():
    """CLI benchmark query runner."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    service = PolicyRetrievalService.from_artifacts()

    test_queries = [
        ("Is intentional arson or reckless fire covered under home insurance?", "HOMEOWNERS"),
        ("What is the deductible and rideshare exclusion for auto accidents?", "AUTO"),
        ("Does health insurance cover routine dental cleaning or cosmetic surgery?", "HEALTH"),
    ]

    for q, ptype in test_queries:
        res = service.retrieve(q, policy_type=ptype, top_k=2)
        print("\n" + "=" * 60)
        print(f"QUERY: {q} (Filter: {ptype})")
        print("=" * 60)
        for c in res["chunks"]:
            print(f"- [Rank {c['final_rank']}] Score: {c['rerank_score']} | Fused: {c['fused_score']}")
            print(f"  Clause: {c['metadata'].get('section_title')} > {c['metadata'].get('clause_title')}")
            print(f"  Snippet: {c['text'][:120]}...\n")


if __name__ == "__main__":
    main()
