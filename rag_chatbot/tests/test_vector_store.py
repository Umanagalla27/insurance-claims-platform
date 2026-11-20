"""
Unit and Integration Tests for FAISS Vector Store and Embeddings
Component: rag_chatbot/tests/test_vector_store.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from rag_chatbot.ingestion.chunker import PolicyChunk
from rag_chatbot.vector_store.embeddings import SemanticDenseEmbedder
from rag_chatbot.vector_store.faiss_store import FAISSVectorStore, SearchResult


@pytest.fixture(scope="module")
def sample_chunks() -> list[PolicyChunk]:
    return [
        PolicyChunk(
            chunk_id="CHK_AUTO_01",
            document_id="POL_AUTO.md",
            policy_type="Auto",
            breadcrumb="[Auto Policy > Coverage A > Liability]",
            section_title="Coverage A",
            clause_title="Liability",
            text="[Auto Policy > Coverage A > Liability]\nBodily injury liability capped at $100,000 per person.",
            char_length=95,
            token_estimate=23,
            metadata={"category": "Auto"},
        ),
        PolicyChunk(
            chunk_id="CHK_PROPERTY_01",
            document_id="POL_HOME.md",
            policy_type="Property",
            breadcrumb="[Property Policy > Coverage 1 > Dwelling]",
            section_title="Coverage 1",
            clause_title="Dwelling",
            text="[Property Policy > Coverage 1 > Dwelling]\nWater pipe burst damage covered subject to $1,000 deductible.",
            char_length=105,
            token_estimate=26,
            metadata={"category": "Property"},
        ),
        PolicyChunk(
            chunk_id="CHK_MEDICAL_01",
            document_id="POL_HEALTH.md",
            policy_type="Medical",
            breadcrumb="[Medical Policy > Section 2 > Prior Auth]",
            section_title="Section 2",
            clause_title="Prior Auth",
            text="[Medical Policy > Section 2 > Prior Auth]\nElective spine surgeries require mandatory prior authorization.",
            char_length=110,
            token_estimate=27,
            metadata={"category": "Medical"},
        ),
    ]


@pytest.mark.unit
class TestEmbeddings:
    """Unit tests for dense vector embedding generation."""

    def test_embedder_dimension_and_normalization(self) -> None:
        embedder = SemanticDenseEmbedder(dimension=384)
        assert embedder.dimension == 384

        query_vec = embedder.embed_query("Auto insurance collision deductible")
        assert query_vec.shape == (384,)
        assert np.linalg.norm(query_vec) == pytest.approx(1.0, abs=1e-4)

        docs = [
            "Homeowners insurance burst plumbing leak",
            "Term life insurance beneficiary designation",
        ]
        doc_vecs = embedder.embed_documents(docs)
        assert doc_vecs.shape == (2, 384)
        for v in doc_vecs:
            assert np.linalg.norm(v) == pytest.approx(1.0, abs=1e-4)

    def test_empty_document_embedding(self) -> None:
        embedder = SemanticDenseEmbedder(dimension=384)
        empty_res = embedder.embed_documents([])
        assert empty_res.shape == (0, 384)


@pytest.mark.integration
class TestFAISSVectorStore:
    """Integration tests for FAISS index creation, query retrieval, and persistence."""

    def test_faiss_add_and_search(self, sample_chunks: list[PolicyChunk]) -> None:
        store = FAISSVectorStore()
        store.add_chunks(sample_chunks)
        assert store.total_vectors == 3

        results = store.search("bodily injury liability", top_k=2)
        assert len(results) == 2
        assert isinstance(results[0], SearchResult)
        assert results[0].policy_type == "Auto"
        assert results[0].score > 0.0

    def test_metadata_filtering(self, sample_chunks: list[PolicyChunk]) -> None:
        store = FAISSVectorStore()
        store.add_chunks(sample_chunks)

        # Query mentions 'surgery' and 'deductible', but filtered strictly to Medical
        results = store.search(
            "deductible surgery", top_k=3, policy_type_filter="Medical"
        )
        assert len(results) == 1
        assert results[0].policy_type == "Medical"
        assert results[0].chunk_id == "CHK_MEDICAL_01"

    def test_empty_index_search(self) -> None:
        store = FAISSVectorStore()
        results = store.search("any query", top_k=5)
        assert len(results) == 0

    def test_save_and_load_persistence(
        self, sample_chunks: list[PolicyChunk], tmp_path: Path
    ) -> None:
        index_file = tmp_path / "test_index.bin"
        meta_file = tmp_path / "test_meta.json"

        store = FAISSVectorStore()
        store.add_chunks(sample_chunks)
        store.save(index_file, meta_file)

        assert index_file.exists()
        assert meta_file.exists()

        # Load into new instance
        loaded_store = FAISSVectorStore.load(index_file, meta_file)
        assert loaded_store.total_vectors == 3
        assert len(loaded_store.metadata_store) == 3

        # Verify search works identically
        results = loaded_store.search("water pipe burst", top_k=1)
        assert len(results) == 1
        assert results[0].policy_type == "Property"
        assert results[0].chunk_id == "CHK_PROPERTY_01"
