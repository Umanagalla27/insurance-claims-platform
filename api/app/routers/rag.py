"""
Policy RAG Chatbot and Query API Router.
Handles contextual policy search, citations, multi-tier LLM answer synthesis, and query caching.
"""

import contextlib
import time
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, status

from api.app.schemas.common import ApiResponse
from api.app.schemas.rag import (
    CacheStatsResponse,
    ClearCacheResponse,
    PolicyAnswerResponse,
    PolicyQueryRequest,
)
from api.app.services.container import get_rag_cache, get_rag_service
from api.app.services.metrics import metrics_collector
from api.app.services.rag_cache import RAGQueryCache
from api.app.services.rag_service import PolicyRAGService

router = APIRouter(prefix="/rag", tags=["Policy RAG & Knowledge Base"])


@router.post(
    "/query",
    response_model=ApiResponse[PolicyAnswerResponse],
    status_code=status.HTTP_200_OK,
    summary="Query Policy Knowledge Base with Citations",
    description=(
        "Performs hybrid vector + BM25 retrieval over official policy contracts, "
        "reranks clauses, checks in-memory cache, and synthesizes a grounded answer "
        "with explicit clause citations."
    ),
)
def query_policy(
    request: PolicyQueryRequest,
    rag_service: PolicyRAGService = Depends(get_rag_service),
    cache: RAGQueryCache = Depends(get_rag_cache),
) -> ApiResponse[PolicyAnswerResponse]:
    start_time = time.perf_counter()

    # 1. Check In-Memory Semantic Cache
    if request.use_cache:
        cached_response = cache.get(
            query=request.query,
            policy_type=request.policy_type,
            top_k=request.top_k,
        )
        if cached_response is not None:
            with contextlib.suppress(Exception):
                metrics_collector.record_rag_query(status="success", cache_hit=True)
            return ApiResponse(
                success=True,
                data=cached_response,
                message="Retrieved answer from in-memory semantic cache.",
            )

    # 2. Hybrid Retrieval & Reranking
    retrieval_start = time.perf_counter()
    retrieval_result = rag_service.retrieval_service.retrieve(
        query=request.query,
        policy_type=request.policy_type,
        top_k=request.top_k,
    )
    retrieval_latency_ms = (time.perf_counter() - retrieval_start) * 1000.0

    # 3. Grounded Answer Synthesis
    gen_start = time.perf_counter()
    answer_text, model_name, confidence = rag_service.generate_answer(
        query=request.query,
        retrieval_result=retrieval_result,
    )
    generation_latency_ms = (time.perf_counter() - gen_start) * 1000.0

    # 4. Format Structured Clause Citations
    citations = rag_service.format_citations(retrieval_result.get("chunks", []))

    total_latency_ms = (time.perf_counter() - start_time) * 1000.0
    now_iso = datetime.now(UTC).isoformat()

    response = PolicyAnswerResponse(
        query=request.query,
        policy_type_filter=request.policy_type,
        answer=answer_text,
        citations=citations,
        confidence_score=confidence,
        model_used=model_name,
        cache_hit=False,
        retrieval_latency_ms=round(retrieval_latency_ms, 2),
        generation_latency_ms=round(generation_latency_ms, 2),
        total_latency_ms=round(total_latency_ms, 2),
        timestamp=now_iso,
    )

    # 5. Populate Cache
    if request.use_cache:
        cache.set(
            query=request.query,
            policy_type=request.policy_type,
            top_k=request.top_k,
            response=response,
        )

    with contextlib.suppress(Exception):
        metrics_collector.record_rag_query(status="success", cache_hit=False)

    return ApiResponse(
        success=True,
        data=response,
        message="Policy query processed successfully.",
    )


@router.get(
    "/cache-stats",
    response_model=ApiResponse[CacheStatsResponse],
    status_code=status.HTTP_200_OK,
    summary="Get RAG Query Cache Statistics",
)
def get_cache_stats(
    cache: RAGQueryCache = Depends(get_rag_cache),
) -> ApiResponse[CacheStatsResponse]:
    return ApiResponse(
        success=True,
        data=cache.stats(),
        message="Cache telemetry retrieved.",
    )


@router.post(
    "/clear-cache",
    response_model=ApiResponse[ClearCacheResponse],
    status_code=status.HTTP_200_OK,
    summary="Invalidate / Clear RAG Query Cache",
)
def clear_cache(
    cache: RAGQueryCache = Depends(get_rag_cache),
) -> ApiResponse[ClearCacheResponse]:
    cleared_count = cache.clear()
    return ApiResponse(
        success=True,
        data=ClearCacheResponse(
            cleared_entries=cleared_count,
            message=f"Successfully cleared {cleared_count} entries from RAG query cache.",
        ),
        message="RAG query cache cleared successfully.",
    )
