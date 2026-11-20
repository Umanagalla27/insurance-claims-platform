"""
Insurance Claims Intelligence Platform — Dense Vector Embedding Engine
Component: rag_chatbot/vector_store/embeddings.py

Provides pluggable dense vector embedding providers for semantic search:
- SemanticDenseEmbedder: Self-contained, deterministic 384-dimensional dense semantic embedder
  utilizing n-gram feature hashing and orthogonal projection (100% offline, zero-network).
- GeminiDenseEmbedder: High-dimensional (768-D) embeddings via Google Gemini text-embedding-004.
"""

from __future__ import annotations

import abc
import hashlib
import os
import re
from collections.abc import Sequence

import numpy as np


class BaseEmbedder(abc.ABC):
    """Abstract Base Class for text embedding providers."""

    @property
    @abc.abstractmethod
    def dimension(self) -> int:
        """Embedding vector dimensionality."""
        pass

    @abc.abstractmethod
    def embed_documents(self, texts: Sequence[str]) -> np.ndarray:
        """Embed a list of document strings into an (N, D) float32 L2-normalized array."""
        pass

    @abc.abstractmethod
    def embed_query(self, text: str) -> np.ndarray:
        """Embed a single query string into a (D,) float32 L2-normalized vector."""
        pass


class SemanticDenseEmbedder(BaseEmbedder):
    """Deterministic, self-contained 384-D dense semantic embedder.

    Uses sub-word and token n-gram feature hashing with stable orthogonal projection
    (Johnson-Lindenstrauss lemma) followed by L2-normalization.
    Guarantees consistent semantic embeddings offline with zero external network downloads.
    """

    def __init__(self, dimension: int = 384, seed: int = 42) -> None:
        self._dim = dimension
        self._seed = seed
        self._num_features = 8192

        # Generate fixed pseudo-random projection matrix
        rng = np.random.RandomState(seed)
        gaussian_matrix = rng.randn(self._num_features, self._dim).astype(np.float32)
        # Gram-Schmidt / QR orthogonalization for distortion-free projection
        q, _ = np.linalg.qr(gaussian_matrix)
        self._projection_matrix = q.astype(np.float32)

    @property
    def dimension(self) -> int:
        return self._dim

    def _tokenize_to_sparse_bow(self, text: str) -> np.ndarray:
        """Convert text into a normalized sparse feature hash vector."""
        tokens = re.findall(r"\b[a-zA-Z0-9_\-]{2,}\b", text.lower())
        vec = np.zeros(self._num_features, dtype=np.float32)

        for tok in tokens:
            # Word token feature
            idx = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16) % self._num_features
            vec[idx] += 1.0

            # Sub-word char 3-grams for typo and morphological robustness
            if len(tok) >= 4:
                for j in range(len(tok) - 2):
                    tri = tok[j : j + 3]
                    tri_idx = int(hashlib.md5(tri.encode("utf-8")).hexdigest(), 16) % self._num_features
                    vec[tri_idx] += 0.35

        # Sublinear scaling: 1 + log(tf)
        non_zero = vec > 0
        vec[non_zero] = 1.0 + np.log(vec[non_zero])

        # L2 normalize sparse vector
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec

    def embed_documents(self, texts: Sequence[str]) -> np.ndarray:
        """Embed a collection of documents."""
        n = len(texts)
        if n == 0:
            return np.empty((0, self._dim), dtype=np.float32)

        sparse_matrix = np.vstack([self._tokenize_to_sparse_bow(t) for t in texts])
        dense_embeddings = np.dot(sparse_matrix, self._projection_matrix).astype(np.float32)

        # Row-wise L2 normalization
        norms = np.linalg.norm(dense_embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        dense_embeddings /= norms
        return dense_embeddings

    def embed_query(self, text: str) -> np.ndarray:
        """Embed a search query."""
        sparse_vec = self._tokenize_to_sparse_bow(text)
        dense_vec = np.dot(sparse_vec, self._projection_matrix).astype(np.float32)
        norm = np.linalg.norm(dense_vec)
        if norm > 0:
            dense_vec /= norm
        return dense_vec


class GeminiDenseEmbedder(BaseEmbedder):
    """Remote embedding provider using Google Gemini's text-embedding-004 (768-D)."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self._dim = 768

    @property
    def dimension(self) -> int:
        return self._dim

    def embed_documents(self, texts: Sequence[str]) -> np.ndarray:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            results = []
            for t in texts:
                emb = genai.embed_content(
                    model="models/text-embedding-004",
                    content=t,
                    task_type="retrieval_document",
                )
                results.append(emb["embedding"])
            arr = np.array(results, dtype=np.float32)
            norms = np.linalg.norm(arr, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            return arr / norms
        except Exception as e:
            raise RuntimeError(f"Gemini embedding API call failed: {e}") from e

    def embed_query(self, text: str) -> np.ndarray:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            emb = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_query",
            )
            vec = np.array(emb["embedding"], dtype=np.float32)
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec /= norm
            return vec
        except Exception as e:
            raise RuntimeError(f"Gemini query embedding API call failed: {e}") from e


def get_default_embedder() -> BaseEmbedder:
    """Factory selecting Gemini if configured, otherwise high-performance offline embedder."""
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key and api_key.startswith("AIza"):
        try:
            return GeminiDenseEmbedder(api_key=api_key)
        except Exception:
            pass
    return SemanticDenseEmbedder(dimension=384)
