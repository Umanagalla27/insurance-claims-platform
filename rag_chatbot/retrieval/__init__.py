"""Retrieval module for RAG policy chatbot.
Provides BM25 sparse search, Dense FAISS search, Hybrid Reciprocal Rank Fusion,
and Cross-similarity Reranking.
"""

from rag_chatbot.retrieval.bm25 import BM25SearchEngine
from rag_chatbot.retrieval.hybrid import HybridRetriever
from rag_chatbot.retrieval.reranker import ContextReranker

__all__ = ["BM25SearchEngine", "HybridRetriever", "ContextReranker"]
