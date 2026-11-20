"""
Pydantic v2 schemas for Policy RAG Chatbot and Caching endpoints.
"""

from pydantic import BaseModel, Field


class PolicyQueryRequest(BaseModel):
    """Input payload for querying insurance policy contracts via RAG."""

    query: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        json_schema_extra={
            "example": "Is flood damage covered under the standard homeowners policy?"
        },
        description="Natural language question regarding policy terms, clauses, or exclusions.",
    )
    policy_type: str | None = Field(
        default=None,
        json_schema_extra={"example": "HOMEOWNERS"},
        description="Optional filter by policy type: AUTO, HEALTH, HOMEOWNERS, COMMERCIAL, LIFE, DISABILITY, CYBER.",
    )
    top_k: int = Field(
        default=3,
        ge=1,
        le=10,
        json_schema_extra={"example": 3},
        description="Number of most relevant policy clauses to retrieve and cite.",
    )
    use_cache: bool = Field(
        default=True,
        description="Whether to check and update the in-memory semantic query cache.",
    )
    stream: bool = Field(
        default=False,
        description="Whether to stream the generated response tokens (SSE).",
    )


class PolicyChunkCitation(BaseModel):
    """Structured citation referencing a specific contractual clause."""

    chunk_id: str
    document_id: str
    policy_type: str
    section_title: str
    clause_title: str
    breadcrumb: str
    relevance_score: float
    snippet: str


class PolicyAnswerResponse(BaseModel):
    """Consolidated answer with grounding citations and latency telemetry."""

    query: str
    policy_type_filter: str | None = None
    answer: str
    citations: list[PolicyChunkCitation]
    confidence_score: float
    model_used: str
    cache_hit: bool = False
    retrieval_latency_ms: float
    generation_latency_ms: float
    total_latency_ms: float
    timestamp: str


class CacheStatsResponse(BaseModel):
    """Telemetry report for RAG in-memory query cache."""

    total_entries: int
    hits: int
    misses: int
    hit_ratio: float
    evictions: int


class ClearCacheResponse(BaseModel):
    """Response returned upon clearing the RAG query cache."""

    cleared_entries: int
    message: str
