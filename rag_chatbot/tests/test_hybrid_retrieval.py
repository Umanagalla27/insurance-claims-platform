"""Unit and Integration Tests for Hybrid Retrieval, BM25, and Reranking (ICIP-015)."""

import pytest
from rag_chatbot.retrieval.bm25 import BM25SearchEngine, normalize_policy_type, tokenize
from rag_chatbot.retrieval.hybrid import HybridRetriever
from rag_chatbot.retrieval.reranker import ContextReranker
from rag_chatbot.retrieval.service import PolicyRetrievalService
from rag_chatbot.vector_store.embeddings import SemanticDenseEmbedder
from rag_chatbot.vector_store.faiss_store import FAISSVectorStore


class TestBM25SearchEngine:
    """Test suite for BM25 Sparse Search Engine."""

    def test_tokenize_preserves_clause_numbers(self):
        tokens = tokenize("See Section 3.1(b) for Uber rideshare exclusions!")
        assert "3.1" in tokens
        assert "uber" in tokens
        assert "rideshare" in tokens
        assert "exclusions" in tokens

    def test_normalize_policy_type_synonyms(self):
        assert normalize_policy_type("homeowners") == "Property"
        assert normalize_policy_type("health") == "Medical"
        assert normalize_policy_type("auto") == "Auto"
        assert normalize_policy_type(None) is None

    def test_bm25_fit_and_search_exact_match(self):
        corpus = [
            "Coverage for commercial rideshare including Uber and Lyft is strictly excluded under 3.1.",
            "Water damage caused by burst plumbing pipes is covered under Section 2.",
            "Routine dental cleanings and cosmetic surgeries are not covered by medical plan.",
        ]
        meta = [
            {"chunk_id": "c1", "policy_type": "Auto", "clause_id": "3.1"},
            {"chunk_id": "c2", "policy_type": "Property", "clause_id": "2.2"},
            {"chunk_id": "c3", "policy_type": "Medical", "clause_id": "3.1"},
        ]

        engine = BM25SearchEngine().fit(corpus, meta)
        results = engine.search("Uber rideshare 3.1", top_k=2)

        assert len(results) > 0
        assert results[0]["metadata"]["chunk_id"] == "c1"
        assert results[0]["score"] > 0.0

    def test_bm25_metadata_filter(self):
        corpus = [
            "Exclusion 3.1 applies to commercial auto driving.",
            "Exclusion 3.1 applies to cosmetic medical surgery.",
        ]
        meta = [
            {"chunk_id": "auto_31", "policy_type": "Auto"},
            {"chunk_id": "med_31", "policy_type": "Medical"},
        ]
        engine = BM25SearchEngine().fit(corpus, meta)

        results = engine.search("3.1 exclusion", policy_type_filter="Medical")
        assert len(results) == 1
        assert results[0]["metadata"]["chunk_id"] == "med_31"


class TestHybridRetriever:
    """Test suite for Hybrid Dense + Sparse Search Engine."""

    @pytest.fixture
    def setup_retriever(self):
        embedder = SemanticDenseEmbedder(dimension=64)
        vstore = FAISSVectorStore(embedder=embedder, force_numpy=True)

        chunks = [
            {
                "chunk_id": "c_auto",
                "document_id": "doc_auto",
                "policy_type": "Auto",
                "breadcrumb": "[Auto > Sec 3 > 3.1 Rideshare]",
                "section_title": "Sec 3",
                "clause_title": "3.1 Rideshare",
                "text": "Vehicles used for rideshare like Uber or Lyft are excluded from collision coverage.",
            },
            {
                "chunk_id": "c_prop",
                "document_id": "doc_prop",
                "policy_type": "Property",
                "breadcrumb": "[Property > Sec 2 > Hail Peril]",
                "section_title": "Sec 2",
                "clause_title": "Hail Peril",
                "text": "Windstorm and hail damage to roof shingles is covered subject to a $500 deductible.",
            },
        ]

        vstore.add_chunks(chunks)

        bm25 = BM25SearchEngine().fit(
            documents=[c["text"] for c in chunks],
            metadata=[{"chunk_id": c["chunk_id"], "policy_type": c["policy_type"]} for c in chunks],
        )

        return HybridRetriever(vector_store=vstore, bm25_engine=bm25, embedder=embedder)

    def test_rrf_retrieval_returns_fused_ranks(self, setup_retriever):
        retriever = setup_retriever
        results = retriever.search("uber rideshare exclusion", top_k=2, mode="rrf")

        assert len(results) == 2
        top_hit = results[0]
        assert top_hit["metadata"]["chunk_id"] == "c_auto"
        assert top_hit["fused_score"] > 0.0
        assert top_hit["dense_rank"] is not None
        assert top_hit["sparse_rank"] is not None

    def test_convex_fusion_returns_valid_scores(self, setup_retriever):
        retriever = setup_retriever
        results = retriever.search("hail storm roof shingles", top_k=1, mode="convex", alpha=0.5)

        assert len(results) == 1
        assert results[0]["metadata"]["chunk_id"] == "c_prop"
        assert 0.0 <= results[0]["fused_score"] <= 1.0


class TestContextReranker:
    """Test suite for Context Reranker and Prompt Formatter."""

    def test_reranker_exact_clause_boost(self):
        reranker = ContextReranker(exact_clause_boost=0.5)
        candidates = [
            {
                "text": "General liability policy introduction.",
                "fused_score": 0.03,
                "metadata": {"clause_id": "1.0", "clause_title": "Intro", "section_title": "Overview"},
            },
            {
                "text": "Specific exclusion for rideshare under 3.1.",
                "fused_score": 0.02,  # Lower base score
                "metadata": {"clause_id": "3.1", "clause_title": "Rideshare", "section_title": "Exclusions"},
            },
        ]

        reranked = reranker.rerank(query="Does clause 3.1 apply to Uber?", candidates=candidates, top_k=2)

        # Clause 3.1 candidate should leapfrog to rank 1 due to exact boost
        assert reranked[0]["metadata"]["clause_id"] == "3.1"
        assert reranked[0]["final_rank"] == 1
        assert reranked[0]["rerank_score"] > reranked[1]["rerank_score"]

    def test_format_context_for_prompt_markdown_citations(self):
        reranker = ContextReranker()
        chunks = [
            {
                "text": "Hail damage is covered up to $250,000.",
                "metadata": {
                    "policy_id": "POL_PROPERTY",
                    "section_title": "Perils",
                    "clause_title": "Hail Peril",
                    "clause_id": "2.1",
                },
            }
        ]
        context = reranker.format_context_for_prompt(chunks)
        assert "[Source 1: POL_PROPERTY | Perils > 2.1 - Hail Peril]" in context
        assert "Hail damage is covered up to $250,000." in context


class TestPolicyRetrievalServiceIntegration:
    """Integration test suite loading real persisted index and manifest."""

    def test_service_end_to_end_query(self):
        service = PolicyRetrievalService.from_artifacts()
        res = service.retrieve(
            query="rideshare commercial exclusion for auto drivers",
            policy_type="AUTO",
            top_k=2,
        )

        assert res["query"] == "rideshare commercial exclusion for auto drivers"
        assert len(res["chunks"]) == 2
        assert "3.1" in res["chunks"][0]["metadata"].get("clause_title", "")
        assert "[Source 1:" in res["formatted_context"]
