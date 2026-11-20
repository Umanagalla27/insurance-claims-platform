"""
Insurance Claims Intelligence Platform — Policy Vector Store Indexer & Benchmark
Component: rag_chatbot/vector_store/indexer.py

Builds the production FAISS vector index from ingested policy chunks,
serializes index artifacts, and executes real-world semantic retrieval benchmarks.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from rag_chatbot.ingestion.chunker import PolicyChunk
from rag_chatbot.vector_store.faiss_store import FAISSVectorStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("rag_chatbot.vector_store.indexer")

DEFAULT_MANIFEST = Path("rag_chatbot/data/chunks_manifest.json")
DEFAULT_INDEX_PATH = Path("data/vector_store/faiss_policy_index.bin")
DEFAULT_META_PATH = Path("data/vector_store/faiss_metadata.json")


def build_and_save_vector_index(
    manifest_path: Path = DEFAULT_MANIFEST,
    index_path: Path = DEFAULT_INDEX_PATH,
    metadata_path: Path = DEFAULT_META_PATH,
) -> tuple[FAISSVectorStore, dict[str, Any]]:
    """Load chunks manifest, index vectors into FAISS, and serialize to disk."""
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found at {manifest_path}. Run ingestion pipeline first.")

    with open(manifest_path, encoding="utf-8") as f:
        manifest_data = json.load(f)

    raw_chunks = manifest_data["chunks"]
    chunks = [PolicyChunk(**c) for c in raw_chunks]

    logger.info("Loaded %d policy chunks from %s", len(chunks), manifest_path)

    store = FAISSVectorStore()

    start_time = time.perf_counter()
    store.add_chunks(chunks)
    indexing_duration = time.perf_counter() - start_time
    logger.info("Indexed %d chunks in %.3f seconds (%.2f chunks/sec)",
                len(chunks), indexing_duration, len(chunks) / max(indexing_duration, 0.001))

    # Persist artifacts
    store.save(index_path, metadata_path)

    stats = {
        "indexed_chunks_count": len(chunks),
        "embedding_dimension": store.dimension,
        "indexing_duration_seconds": round(indexing_duration, 4),
        "index_file_path": str(index_path),
        "metadata_file_path": str(metadata_path),
        "index_size_bytes": index_path.stat().st_size,
    }
    return store, stats


def benchmark_semantic_retrieval(store: FAISSVectorStore) -> list[dict[str, Any]]:
    """Execute benchmark queries covering key insurance policy scenarios."""
    queries = [
        {
            "scenario": "Auto Collision Deductible",
            "query": "What is the mandatory deductible for collision damage under the auto policy?",
            "expected_policy": "Auto",
            "filter": "Auto",
        },
        {
            "scenario": "Homeowners Water Leak Coverage",
            "query": "Does the broad form property policy cover damage from burst plumbing pipes?",
            "expected_policy": "Property",
            "filter": "Property",
        },
        {
            "scenario": "Health Prior Authorization",
            "query": "What surgical procedures require mandatory prior authorization before treatment?",
            "expected_policy": "Medical",
            "filter": "Medical",
        },
        {
            "scenario": "Commercial Liability Legal Defense",
            "query": "Does the insurer pay legal defense costs outside policy limits?",
            "expected_policy": "Liability",
            "filter": None,
        },
        {
            "scenario": "Term Life Suicide Clause",
            "query": "What is the suicide exclusion contestability period for death benefits?",
            "expected_policy": "Life",
            "filter": "Life",
        },
        {
            "scenario": "Travel Baggage Delay",
            "query": "How many hours must luggage be delayed before airline delay reimbursement applies?",
            "expected_policy": "Travel",
            "filter": "Travel",
        },
        {
            "scenario": "Disability Elimination Period",
            "query": "What is the elimination period for long-term disability monthly income benefits?",
            "expected_policy": "Disability",
            "filter": "Disability",
        },
    ]

    benchmark_results: list[dict[str, Any]] = []

    for q in queries:
        t0 = time.perf_counter()
        results = store.search(q["query"], top_k=3, policy_type_filter=q["filter"])
        latency_ms = (time.perf_counter() - t0) * 1000.0

        top_hit = results[0] if results else None
        benchmark_results.append(
            {
                "scenario": q["scenario"],
                "query": q["query"],
                "policy_filter": q["filter"],
                "latency_ms": round(latency_ms, 3),
                "top_hit_chunk_id": top_hit.chunk_id if top_hit else None,
                "top_hit_policy_type": top_hit.policy_type if top_hit else None,
                "top_hit_score": top_hit.score if top_hit else 0.0,
                "top_hit_breadcrumb": top_hit.breadcrumb if top_hit else None,
                "top_hit_snippet": top_hit.text[:140] + "..." if top_hit else None,
            }
        )

    return benchmark_results


if __name__ == "__main__":
    vector_store, build_stats = build_and_save_vector_index()
    benchmarks = benchmark_semantic_retrieval(vector_store)

    print("\n" + "=" * 75)
    print("      FAISS VECTOR STORE INDEXING & RETRIEVAL BENCHMARK")
    print("=" * 75)
    print(f"Total Chunks Indexed:  {build_stats['indexed_chunks_count']}")
    print(f"Vector Dimensionality: {build_stats['embedding_dimension']}")
    print(f"Index File Size:       {build_stats['index_size_bytes'] / 1024.0:.2f} KB")
    print(f"Indexing Duration:     {build_stats['indexing_duration_seconds']:.4f} seconds")
    print("\nSample Retrieval Hits Across 7 Policy Lines:")
    for b in benchmarks:
        print(f"\n[Scenario: {b['scenario']}] (Latency: {b['latency_ms']:.2f} ms | Score: {b['top_hit_score']})")
        print(f"  Query:      {b['query']}")
        print(f"  Breadcrumb: {b['top_hit_breadcrumb']}")
        print(f"  Snippet:    {b['top_hit_snippet']}")
    print("=" * 75)
