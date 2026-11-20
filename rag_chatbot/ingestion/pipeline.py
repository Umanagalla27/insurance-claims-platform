"""
Insurance Claims Intelligence Platform — Policy Document Ingestion Runner
Component: rag_chatbot/ingestion/pipeline.py

Orchestrates batch ingestion, semantic chunking, and metadata manifest generation
across all enterprise insurance policy contracts.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rag_chatbot.ingestion.chunker import PolicyChunk, SemanticPolicyChunker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("rag_chatbot.ingestion.pipeline")

DEFAULT_DOCS_DIR = Path("rag_chatbot/documents/sample_policy_docs")
DEFAULT_OUTPUT_MANIFEST = Path("rag_chatbot/data/chunks_manifest.json")
BACKUP_MANIFEST = Path("data/rag/chunks_manifest.json")


def ingest_policy_documents(
    docs_dir: Path = DEFAULT_DOCS_DIR,
    output_manifest: Path = DEFAULT_OUTPUT_MANIFEST,
    max_chunk_chars: int = 650,
    overlap_chars: int = 120,
) -> tuple[list[PolicyChunk], dict[str, Any]]:
    """Scan documents directory, execute semantic chunking, and persist manifest."""
    if not docs_dir.exists():
        raise FileNotFoundError(f"Policy documents directory not found at {docs_dir}")

    doc_files = sorted(docs_dir.glob("*.md"))
    if not doc_files:
        raise ValueError(f"No markdown policy files found in {docs_dir}")

    logger.info("Found %d policy contracts in %s", len(doc_files), docs_dir)

    chunker = SemanticPolicyChunker(max_chunk_chars=max_chunk_chars, overlap_chars=overlap_chars)
    all_chunks: list[PolicyChunk] = []
    doc_stats: list[dict[str, Any]] = []

    start_time = time.perf_counter()

    for doc_path in doc_files:
        with open(doc_path, encoding="utf-8") as f:
            content = f.read()

        doc_chunks = chunker.chunk_document(
            text=content,
            document_id=doc_path.name,
            custom_metadata={"file_size_bytes": doc_path.stat().st_size},
        )
        all_chunks.extend(doc_chunks)

        policy_type = chunker.infer_policy_type(doc_path.name)
        doc_stats.append(
            {
                "document_name": doc_path.name,
                "policy_type": policy_type,
                "file_size_bytes": doc_path.stat().st_size,
                "chunks_generated": len(doc_chunks),
                "total_characters": sum(c.char_length for c in doc_chunks),
            }
        )
        logger.info("Ingested %s (%s): %d chunks", doc_path.name, policy_type, len(doc_chunks))

    duration_ms = (time.perf_counter() - start_time) * 1000.0

    manifest_payload = {
        "manifest_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "total_documents": len(doc_files),
        "total_chunks": len(all_chunks),
        "ingestion_duration_ms": round(duration_ms, 2),
        "chunking_config": {
            "max_chunk_chars": max_chunk_chars,
            "overlap_chars": overlap_chars,
        },
        "documents": doc_stats,
        "chunks": [c.model_dump() for c in all_chunks],
    }

    # Write primary manifest
    output_manifest.parent.mkdir(parents=True, exist_ok=True)
    with open(output_manifest, "w", encoding="utf-8") as f:
        json.dump(manifest_payload, f, indent=2)
    logger.info("Saved chunks manifest to %s (size: %.2f KB)",
                output_manifest, output_manifest.stat().st_size / 1024.0)

    # Write backup manifest to data/rag/
    BACKUP_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with open(BACKUP_MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest_payload, f, indent=2)

    return all_chunks, manifest_payload


if __name__ == "__main__":
    chunks, manifest = ingest_policy_documents()
    print("\n" + "=" * 70)
    print("      POLICY DOCUMENT INGESTION & CHUNKING SUMMARY")
    print("=" * 70)
    print(f"Total Documents Ingested: {manifest['total_documents']}")
    print(f"Total Semantic Chunks:   {manifest['total_chunks']}")
    print(f"Execution Duration:       {manifest['ingestion_duration_ms']:.2f} ms")
    print("\nPer-Document Breakdown:")
    for d in manifest["documents"]:
        print(f"- {d['document_name']:<32} | Type: {d['policy_type']:<10} | Chunks: {d['chunks_generated']:>2}")
    print("=" * 70)
