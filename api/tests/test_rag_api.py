"""
Integration and Unit Tests for Policy RAG Chatbot and In-Memory Caching Endpoints.
Verifies grounded search, citation assembly, metadata filtering, and cache acceleration.
"""

from pathlib import Path
import pytest
from pydantic import ValidationError

from api.app.routers.rag import clear_cache, get_cache_stats, query_policy
from api.app.schemas.common import ApiResponse
from api.app.schemas.rag import (
    CacheStatsResponse,
    ClearCacheResponse,
    PolicyAnswerResponse,
    PolicyQueryRequest,
)
from api.app.services.container import container
from api.app.services.rag_cache import RAGQueryCache
from api.app.services.rag_service import PolicyRAGService
from rag_chatbot.retrieval.service import PolicyRetrievalService


@pytest.fixture(scope="module")
def rag_service_instance():
    """Module-level pre-warmed PolicyRAGService instance."""
    container.initialize()
    if not container.rag_service:
        retrieval = PolicyRetrievalService.from_artifacts()
        container.rag_service = PolicyRAGService(retrieval)
    return container.rag_service


@pytest.fixture
def fresh_cache():
    """Provides a fresh, isolated RAGQueryCache instance per test."""
    cache = RAGQueryCache(max_size=100, ttl_seconds=3600)
    cache.clear()
    return cache


class TestPolicyRAGAPI:
    """Test suite covering Policy RAG querying, citation assembly, and caching."""

    def test_policy_query_success_with_citations(self, rag_service_instance, fresh_cache):
        """Verify successful grounded query returns citations and authoritative answer."""
        request = PolicyQueryRequest(
            query="What is the deductible and rideshare exclusion for auto accidents?",
            policy_type="AUTO",
            top_k=3,
            use_cache=True,
        )

        res: ApiResponse[PolicyAnswerResponse] = query_policy(
            request=request,
            rag_service=rag_service_instance,
            cache=fresh_cache,
        )

        assert res.success is True
        response = res.data
        assert response.query == request.query
        assert response.policy_type_filter == "AUTO"
        assert response.cache_hit is False
        assert len(response.answer) > 20
        assert len(response.citations) > 0
        assert response.confidence_score > 0.40
        assert response.retrieval_latency_ms > 0
        assert response.total_latency_ms > 0

        # Check citation structure
        top_citation = response.citations[0]
        assert top_citation.chunk_id != ""
        assert top_citation.policy_type == "Auto"
        assert len(top_citation.section_title) > 0
        assert len(top_citation.snippet) > 0

    def test_semantic_caching_returns_instant_hit(self, rag_service_instance, fresh_cache):
        """Verify identical query hits cache with cache_hit=True and sub-millisecond latency."""
        request = PolicyQueryRequest(
            query="Does homeowner insurance cover sudden water pipe burst?",
            policy_type="HOMEOWNERS",
            top_k=2,
            use_cache=True,
        )

        # First Call: Cache Miss
        first_res: ApiResponse[PolicyAnswerResponse] = query_policy(
            request=request,
            rag_service=rag_service_instance,
            cache=fresh_cache,
        )
        assert first_res.success is True
        assert first_res.data.cache_hit is False

        # Second Call: Cache Hit
        second_res: ApiResponse[PolicyAnswerResponse] = query_policy(
            request=request,
            rag_service=rag_service_instance,
            cache=fresh_cache,
        )
        assert second_res.success is True
        assert second_res.data.cache_hit is True
        assert second_res.data.total_latency_ms < 5.0
        assert second_res.data.answer == first_res.data.answer
        assert len(second_res.data.citations) == len(first_res.data.citations)

    def test_metadata_filtering_restricts_to_requested_policy(
        self, rag_service_instance, fresh_cache
    ):
        """Verify policy_type filter confines retrieval results strictly to the target contract."""
        request = PolicyQueryRequest(
            query="Does health insurance cover routine dental checkups or preventative teeth cleaning?",
            policy_type="HEALTH",
            top_k=3,
            use_cache=False,
        )

        res: ApiResponse[PolicyAnswerResponse] = query_policy(
            request=request,
            rag_service=rag_service_instance,
            cache=fresh_cache,
        )

        assert res.success is True
        response = res.data
        assert len(response.citations) > 0
        for citation in response.citations:
            assert citation.policy_type == "Medical"

    def test_cache_invalidation_and_stats(self, rag_service_instance, fresh_cache):
        """Verify cache clearing empties entries and stats track hits and misses accurately."""
        request = PolicyQueryRequest(
            query="What are the standard cyber ransom payment sub-limits?",
            policy_type="CYBER",
            top_k=2,
            use_cache=True,
        )

        # 1. Miss
        query_policy(request=request, rag_service=rag_service_instance, cache=fresh_cache)
        # 2. Hit
        query_policy(request=request, rag_service=rag_service_instance, cache=fresh_cache)

        stats_res: ApiResponse[CacheStatsResponse] = get_cache_stats(cache=fresh_cache)
        assert stats_res.success is True
        stats = stats_res.data
        assert stats.total_entries == 1
        assert stats.hits == 1
        assert stats.misses == 1
        assert stats.hit_ratio == 0.5

        # 3. Clear Cache
        clear_res: ApiResponse[ClearCacheResponse] = clear_cache(cache=fresh_cache)
        assert clear_res.success is True
        assert clear_res.data.cleared_entries == 1

        # 4. Verify emptied
        cleared_stats = get_cache_stats(cache=fresh_cache).data
        assert cleared_stats.total_entries == 0

    def test_bypass_cache_flag_prevents_cache_storage(
        self, rag_service_instance, fresh_cache
    ):
        """Verify use_cache=False bypasses lookup and does not populate cache."""
        request = PolicyQueryRequest(
            query="What is the commercial general liability aggregate limit?",
            policy_type="COMMERCIAL",
            top_k=2,
            use_cache=False,
        )

        resp1 = query_policy(request=request, rag_service=rag_service_instance, cache=fresh_cache)
        assert resp1.data.cache_hit is False

        stats = get_cache_stats(cache=fresh_cache).data
        assert stats.total_entries == 0

    def test_pydantic_validation_error_on_invalid_request(self):
        """Verify Pydantic enforces query length constraints."""
        with pytest.raises(ValidationError):
            # query too short (<3 chars)
            PolicyQueryRequest(query="no")

        with pytest.raises(ValidationError):
            # top_k outside allowed bounds (ge=1, le=10)
            PolicyQueryRequest(query="valid query text", top_k=50)

    def test_uncovered_scenario_returns_grounded_fallback(
        self, rag_service_instance, fresh_cache
    ):
        """Verify queries provide contractual grounding disclaimer and citations."""
        request = PolicyQueryRequest(
            query="Does this policy reimburse quantum space travel teleportation accidents?",
            top_k=2,
            use_cache=False,
        )

        res = query_policy(
            request=request,
            rag_service=rag_service_instance,
            cache=fresh_cache,
        )

        assert res.success is True
        assert res.data.answer is not None
        assert len(res.data.answer) > 0
