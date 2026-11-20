"""
Insurance Claims Intelligence Platform — Dual-Mode Vector Store Engine
Component: rag_chatbot/vector_store/faiss_store.py

Implements production-grade vector store supporting both FAISS IndexFlatIP
and native high-performance NumPy exact cosine similarity with metadata filtering.
Ensures 100% cross-platform resilience across Windows, Linux, and containerized CI/CD.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np
from pydantic import BaseModel, Field

from rag_chatbot.ingestion.chunker import PolicyChunk
from rag_chatbot.vector_store.embeddings import BaseEmbedder, SemanticDenseEmbedder

logger = logging.getLogger("rag_chatbot.vector_store.faiss_store")

# Attempt importing FAISS with graceful fallback
# On Windows, faiss-cpu depends on OpenMP (vcomp140.dll) which can trigger Windows exception 0xc0000008
# in restricted process environments. We use the pure NumPy engine on Windows by default.
FAISS_AVAILABLE = False
if sys.platform != "win32" or os.getenv("ENABLE_WINDOWS_FAISS", "0") == "1":
    try:
        import faiss  # type: ignore

        # Verify C++ SWIG DLL initialization by creating a toy index
        _test_index = faiss.IndexFlatIP(4)
        FAISS_AVAILABLE = True
    except (ImportError, Exception, BaseException) as e:
        logger.info("FAISS binary acceleration unavailable (%s); using NumPy vector engine.", e)
        faiss = None  # type: ignore
else:
    logger.info("Using native NumPy vector similarity engine on Windows platform.")
    faiss = None


class SearchResult(BaseModel):
    """Pydantic model representing a semantic search retrieval hit."""

    chunk_id: str = Field(..., description="Unique chunk identifier")
    document_id: str = Field(..., description="Source policy filename")
    policy_type: str = Field(..., description="Insurance line: Auto, Property, etc.")
    breadcrumb: str = Field(..., description="Hierarchical context breadcrumb")
    section_title: str = Field(..., description="Section header")
    clause_title: str = Field(..., description="Clause heading")
    text: str = Field(..., description="Text content of the retrieved chunk")
    score: float = Field(..., description="Cosine similarity score (0.0 to 1.0)")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata tags")


class FAISSVectorStore:
    """Production vector store supporting FAISS IndexFlatIP with resilient NumPy fallback."""

    def __init__(
        self,
        embedder: BaseEmbedder | None = None,
        force_numpy: bool = False,
    ) -> None:
        self.embedder = embedder or SemanticDenseEmbedder(dimension=384)
        self.dimension = self.embedder.dimension
        self.force_numpy = force_numpy
        self.use_faiss = FAISS_AVAILABLE and not force_numpy

        if self.use_faiss:
            self._faiss_index = faiss.IndexFlatIP(self.dimension)
            self._engine_type = "FAISS_IndexFlatIP"
        else:
            self._faiss_index = None
            self._engine_type = "NumPy_Cosine"

        self._vectors: list[np.ndarray] = []
        self.metadata_store: list[dict[str, Any]] = []
        logger.info("Initialized VectorStore using engine: %s (dimension=%d)",
                    self._engine_type, self.dimension)

    @property
    def total_vectors(self) -> int:
        return len(self.metadata_store)

    @property
    def index(self) -> Any:
        return self._faiss_index

    @property
    def engine_type(self) -> str:
        return self._engine_type

    def add_chunks(self, chunks: list[PolicyChunk], batch_size: int = 64) -> None:
        """Embed and index a list of PolicyChunk objects."""
        if not chunks:
            return

        logger.info("Indexing %d chunks into %s...", len(chunks), self._engine_type)

        texts = [c.get("text", "") if isinstance(c, dict) else c.text for c in chunks]
        embeddings_list = []
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            batch_embs = self.embedder.embed_documents(batch_texts)
            embeddings_list.append(batch_embs)

        all_embeddings = np.vstack(embeddings_list).astype(np.float32)

        # Store in FAISS if active
        if self.use_faiss and self._faiss_index is not None:
            self._faiss_index.add(all_embeddings)

        # Store in NumPy array list
        for vec in all_embeddings:
            self._vectors.append(vec)

        # Store metadata
        for c in chunks:
            if isinstance(c, dict):
                self.metadata_store.append(
                    {
                        "chunk_id": c.get("chunk_id", ""),
                        "document_id": c.get("document_id", ""),
                        "policy_type": c.get("policy_type", ""),
                        "breadcrumb": c.get("breadcrumb", ""),
                        "section_title": c.get("section_title", ""),
                        "clause_title": c.get("clause_title", ""),
                        "text": c.get("text", ""),
                        "char_length": len(c.get("text", "")),
                        "metadata": c.get("metadata", {}),
                    }
                )
            else:
                self.metadata_store.append(
                    {
                        "chunk_id": c.chunk_id,
                        "document_id": c.document_id,
                        "policy_type": c.policy_type,
                        "breadcrumb": c.breadcrumb,
                        "section_title": c.section_title,
                        "clause_title": c.clause_title,
                        "text": c.text,
                        "char_length": c.char_length,
                        "metadata": c.metadata,
                    }
                )

        logger.info("Successfully indexed %d chunks (total vectors: %d)",
                    len(chunks), self.total_vectors)

    def search(
        self,
        query: str,
        top_k: int = 5,
        policy_type_filter: str | None = None,
    ) -> list[SearchResult]:
        """Execute semantic search against indexed policy chunks with optional metadata filtering."""
        if self.total_vectors == 0:
            logger.warning("Vector store is empty. Returning 0 results.")
            return []

        query_vec = self.embedder.embed_query(query).astype(np.float32)

        candidate_k = min(self.total_vectors, top_k * 4 if policy_type_filter else top_k)

        if self.use_faiss and self._faiss_index is not None:
            q_matrix = query_vec.reshape(1, -1)
            distances, indices = self._faiss_index.search(q_matrix, candidate_k)
            retrieved_scores = distances[0]
            retrieved_indices = indices[0]
        else:
            # NumPy exact inner product on normalized vectors = cosine similarity
            matrix = np.vstack(self._vectors).astype(np.float32)
            sim_scores = np.dot(matrix, query_vec)
            retrieved_indices = np.argsort(sim_scores)[-candidate_k:][::-1]
            retrieved_scores = sim_scores[retrieved_indices]

        results: list[SearchResult] = []
        for dist, idx in zip(retrieved_scores, retrieved_indices, strict=True):
            if idx < 0 or idx >= len(self.metadata_store):
                continue

            meta = self.metadata_store[idx]

            # Apply metadata filter
            if policy_type_filter:
                filter_val = policy_type_filter.lower()
                meta_val = meta["policy_type"].lower()
                # Also check common synonyms
                synonyms = {
                    "homeowners": "property",
                    "health": "medical",
                    "commercial": "liability",
                }
                norm_filter = synonyms.get(filter_val, filter_val)
                norm_meta = synonyms.get(meta_val, meta_val)
                if norm_meta != norm_filter:
                    continue

            results.append(
                SearchResult(
                    chunk_id=meta["chunk_id"],
                    document_id=meta["document_id"],
                    policy_type=meta["policy_type"],
                    breadcrumb=meta["breadcrumb"],
                    section_title=meta["section_title"],
                    clause_title=meta["clause_title"],
                    text=meta["text"],
                    score=round(float(dist), 4),
                    metadata=meta.get("metadata", {}),
                )
            )

            if len(results) >= top_k:
                break

        return results

    def save(self, index_path: Path, metadata_path: Path) -> None:
        """Persist vector store index binary and metadata JSON to disk."""
        index_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.parent.mkdir(parents=True, exist_ok=True)

        if self.use_faiss and self._faiss_index is not None:
            faiss.write_index(self._faiss_index, str(index_path))
        else:
            # Save vectors as numpy binary directly to file handle
            matrix = (
                np.vstack(self._vectors).astype(np.float32)
                if self._vectors
                else np.empty((0, self.dimension), dtype=np.float32)
            )
            with open(index_path, "wb") as f:
                np.save(f, matrix)

        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "total_vectors": self.total_vectors,
                    "dimension": self.dimension,
                    "engine_type": self._engine_type,
                    "metadata": self.metadata_store,
                },
                f,
                indent=2,
            )
        logger.info("Saved vector store to %s and metadata to %s", index_path, metadata_path)

    @classmethod
    def load(
        cls,
        index_path: Path,
        metadata_path: Path,
        embedder: BaseEmbedder | None = None,
    ) -> FAISSVectorStore:
        """Load persisted vector store and metadata from disk."""
        if not metadata_path.exists():
            raise FileNotFoundError(f"Vector metadata file not found at {metadata_path}")

        with open(metadata_path, encoding="utf-8") as f:
            data = json.load(f)

        saved_engine = data.get("engine_type", "")
        force_numpy = "NumPy" in saved_engine or not FAISS_AVAILABLE

        store = cls(embedder=embedder, force_numpy=force_numpy)

        if store.use_faiss and store._faiss_index is not None and index_path.exists():
            try:
                store._faiss_index = faiss.read_index(str(index_path))
            except Exception:
                # If faiss read fails, fallback to numpy
                store.use_faiss = False
                store._engine_type = "NumPy_Cosine"

        if not store.use_faiss:
            if index_path.exists():
                try:
                    with open(index_path, "rb") as f:
                        mat = np.load(f)
                        store._vectors = list(mat)
                except Exception:
                    pass

            # If index binary was FAISS C++ binary or unreadable by numpy, re-embed from metadata
            if len(store._vectors) == 0 and len(data.get("metadata", [])) > 0:
                logger.info("Regenerating NumPy vectors from metadata text payloads...")
                texts = [m["text"] for m in data["metadata"]]
                embs = store.embedder.embed_documents(texts)
                store._vectors = list(embs)

        store.metadata_store = data["metadata"]
        logger.info("Loaded vector store with %d vectors (engine: %s)",
                    store.total_vectors, store.engine_type)
        return store
