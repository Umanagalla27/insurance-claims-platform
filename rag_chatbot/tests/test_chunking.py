"""
Unit and Integration Tests for RAG Policy Document Chunker & Ingestion
Component: rag_chatbot/tests/test_chunking.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from rag_chatbot.ingestion.chunker import PolicyChunk, SemanticPolicyChunker
from rag_chatbot.ingestion.pipeline import ingest_policy_documents


@pytest.mark.unit
class TestSemanticChunker:
    """Unit tests verifying chunking rules, breadcrumb injection, and sizing."""

    def test_infer_policy_type_mapping(self) -> None:
        chunker = SemanticPolicyChunker()
        assert chunker.infer_policy_type("POL_AUTO_COMPREHENSIVE.md") == "Auto"
        assert chunker.infer_policy_type("POL_HOMEOWNERS_PROPERTY.md") == "Property"
        assert chunker.infer_policy_type("POL_HEALTH_MEDICAL.md") == "Medical"
        assert chunker.infer_policy_type("POL_COMMERCIAL_LIABILITY.md") == "Liability"
        assert chunker.infer_policy_type("POL_TERM_LIFE.md") == "Life"
        assert chunker.infer_policy_type("POL_TRAVEL_GUARD.md") == "Travel"
        assert chunker.infer_policy_type("POL_DISABILITY_INCOME.md") == "Disability"
        assert chunker.infer_policy_type("UNKNOWN_FILE.md") == "General"

    def test_chunk_document_hierarchy(self) -> None:
        chunker = SemanticPolicyChunker(max_chunk_chars=300)
        sample_doc = """# SAMPLE APEX AUTO CONTRACT

## Section 1: Liability Coverage

### 1.1 Bodily Injury
We pay compensatory damages for bodily injury caused by an accident.

### 1.2 Property Damage
We pay property damage liability up to fifty thousand dollars.

## Section 2: Exclusions

### 2.1 Intentional Harm
We do not cover intentional damage caused by the insured.
"""
        chunks = chunker.chunk_document(sample_doc, document_id="sample_auto.md")
        assert len(chunks) >= 3

        # Verify breadcrumbs
        assert any("Bodily Injury" in c.clause_title for c in chunks)
        assert any("Property Damage" in c.clause_title for c in chunks)
        assert any("Intentional Harm" in c.clause_title for c in chunks)

        for c in chunks:
            assert isinstance(c, PolicyChunk)
            assert c.policy_type == "Auto"
            assert c.text.startswith(c.breadcrumb)
            assert c.char_length > 0
            assert c.token_estimate > 0

    def test_chunk_deterministic_ids(self) -> None:
        chunker = SemanticPolicyChunker()
        doc = "# POLICY TEST\n\n## Section 1: Intro\n\n### 1.1 Details\nTest sentence."
        chunks1 = chunker.chunk_document(doc, document_id="TEST_POLICY.md")
        chunks2 = chunker.chunk_document(doc, document_id="TEST_POLICY.md")
        assert chunks1[0].chunk_id == chunks2[0].chunk_id


@pytest.mark.integration
class TestIngestionPipeline:
    """Integration tests verifying full batch ingestion across sample policy documents."""

    def test_ingest_sample_docs_end_to_end(self, tmp_path: Path) -> None:
        output_file = tmp_path / "test_manifest.json"
        chunks, manifest = ingest_policy_documents(output_manifest=output_file)

        assert manifest["total_documents"] == 7
        assert manifest["total_chunks"] == 66
        assert len(chunks) == 66
        assert output_file.exists()

        # Validate file contents
        with open(output_file, encoding="utf-8") as f:
            data = json.load(f)
            assert len(data["chunks"]) == 66
            assert data["manifest_version"] == "1.0"

        # Check coverage across all 7 categories
        categories = {c.policy_type for c in chunks}
        expected_cats = {
            "Auto",
            "Property",
            "Medical",
            "Liability",
            "Life",
            "Travel",
            "Disability",
        }
        assert categories == expected_cats

    def test_chunks_manifest_schema_consistency(self) -> None:
        manifest_path = Path("rag_chatbot/data/chunks_manifest.json")
        assert manifest_path.exists()

        with open(manifest_path, encoding="utf-8") as f:
            data = json.load(f)

        for c_dict in data["chunks"]:
            chunk = PolicyChunk(**c_dict)
            assert chunk.chunk_id != ""
            assert chunk.text != ""
            assert len(chunk.text) == chunk.char_length
            assert chunk.policy_type in [
                "Auto",
                "Property",
                "Medical",
                "Liability",
                "Life",
                "Travel",
                "Disability",
            ]
