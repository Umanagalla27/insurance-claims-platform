"""
Insurance Claims Intelligence Platform — Semantic Policy Document Chunker
Component: rag_chatbot/ingestion/chunker.py

Provides hierarchical, clause-aware semantic document chunking for insurance policies.
Implements Contextual Header Prepending to ensure every chunk retains its legal lineage.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class PolicyChunk(BaseModel):
    """Pydantic model representing an ingested semantic policy chunk."""

    chunk_id: str = Field(..., description="Unique deterministic identifier for the chunk")
    document_id: str = Field(..., description="Source policy filename or identifier")
    policy_type: str = Field(..., description="Standardized category: Auto, Property, Medical, etc.")
    breadcrumb: str = Field(..., description="Full hierarchical context (Document > Section > Clause)")
    section_title: str = Field(..., description="Current parent section title")
    clause_title: str = Field(..., description="Specific sub-clause heading if present")
    text: str = Field(..., description="Contextualized chunk text payload")
    char_length: int = Field(..., description="Character count of chunk payload")
    token_estimate: int = Field(..., description="Estimated word/token count (~char_length / 4)")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Custom metadata tags and search filters")


class SemanticPolicyChunker:
    """Hierarchical, clause-aware chunker designed for insurance policy contracts."""

    POLICY_TYPE_MAPPING = {
        "auto": "Auto",
        "homeowners": "Property",
        "property": "Property",
        "health": "Medical",
        "medical": "Medical",
        "liability": "Liability",
        "commercial": "Liability",
        "life": "Life",
        "travel": "Travel",
        "disability": "Disability",
    }

    def __init__(
        self,
        max_chunk_chars: int = 650,
        overlap_chars: int = 120,
    ) -> None:
        self.max_chunk_chars = max_chunk_chars
        self.overlap_chars = overlap_chars

    def infer_policy_type(self, doc_name: str) -> str:
        """Infer standardized policy category from document filename."""
        clean_name = doc_name.lower().replace("-", "_")
        for key, category in self.POLICY_TYPE_MAPPING.items():
            if key in clean_name:
                return category
        return "General"

    def chunk_document(
        self,
        text: str,
        document_id: str,
        custom_metadata: dict[str, Any] | None = None,
    ) -> list[PolicyChunk]:
        """Parse markdown policy text into hierarchical contextualized chunks."""
        policy_type = self.infer_policy_type(document_id)
        metadata = custom_metadata or {}

        # 1. Extract Main Document Title (# Header)
        doc_title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        doc_title = doc_title_match.group(1).strip() if doc_title_match else document_id

        # 2. Split into Major Sections (## Header)
        section_pattern = re.compile(r"(^##\s+.+$)", re.MULTILINE)
        section_splits = section_pattern.split(text)

        chunks: list[PolicyChunk] = []
        chunk_seq = 0

        # Process each section
        current_section = "General Overview"
        i = 1
        while i < len(section_splits):
            header_candidate = section_splits[i].strip()
            if header_candidate.startswith("##"):
                current_section = header_candidate.lstrip("#").strip()
                content = section_splits[i + 1] if i + 1 < len(section_splits) else ""
                i += 2
            else:
                content = section_splits[i]
                i += 1

            if not content.strip():
                continue

            # 3. Split Section into Clauses (### Header)
            clause_pattern = re.compile(r"(^###\s+.+$)", re.MULTILINE)
            clause_splits = clause_pattern.split(content)

            if len(clause_splits) > 1:
                # We have child sub-clauses
                current_clause = "Section Overview"
                c_idx = 1
                while c_idx < len(clause_splits):
                    clause_candidate = clause_splits[c_idx].strip()
                    if clause_candidate.startswith("###"):
                        current_clause = clause_candidate.lstrip("#").strip()
                        clause_body = clause_splits[c_idx + 1] if c_idx + 1 < len(clause_splits) else ""
                        c_idx += 2
                    else:
                        clause_body = clause_splits[c_idx]
                        c_idx += 1

                    sub_chunks = self._generate_sub_chunks(
                        body=clause_body,
                        doc_title=doc_title,
                        section_title=current_section,
                        clause_title=current_clause,
                        document_id=document_id,
                        policy_type=policy_type,
                        start_seq=chunk_seq,
                        metadata=metadata,
                    )
                    chunks.extend(sub_chunks)
                    chunk_seq += len(sub_chunks)
            else:
                # Flat section without ### subclauses
                sub_chunks = self._generate_sub_chunks(
                    body=content,
                    doc_title=doc_title,
                    section_title=current_section,
                    clause_title="General Clause",
                    document_id=document_id,
                    policy_type=policy_type,
                    start_seq=chunk_seq,
                    metadata=metadata,
                )
                chunks.extend(sub_chunks)
                chunk_seq += len(sub_chunks)

        return chunks

    def _generate_sub_chunks(
        self,
        body: str,
        doc_title: str,
        section_title: str,
        clause_title: str,
        document_id: str,
        policy_type: str,
        start_seq: int,
        metadata: dict[str, Any],
    ) -> list[PolicyChunk]:
        """Apply sliding character windowing with breadcrumb context pre-pending."""
        clean_body = re.sub(r"\n{3,}", "\n\n", body).strip()
        if not clean_body:
            return []

        breadcrumb = f"[{policy_type} Policy: {doc_title} > {section_title} > {clause_title}]"

        # If body fits comfortably in one chunk
        if len(clean_body) <= self.max_chunk_chars:
            payload = f"{breadcrumb}\n{clean_body}"
            chunk_id = self._generate_chunk_id(document_id, start_seq)
            return [
                PolicyChunk(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    policy_type=policy_type,
                    breadcrumb=breadcrumb,
                    section_title=section_title,
                    clause_title=clause_title,
                    text=payload,
                    char_length=len(payload),
                    token_estimate=len(payload) // 4,
                    metadata=metadata,
                )
            ]

        # Break on paragraphs or sentences with sliding overlap
        paragraphs = [p.strip() for p in clean_body.split("\n\n") if p.strip()]
        result_chunks: list[PolicyChunk] = []
        current_text = ""
        seq = start_seq

        for p in paragraphs:
            if not current_text:
                current_text = p
            elif len(current_text) + len(p) + 2 <= self.max_chunk_chars:
                current_text += "\n\n" + p
            else:
                payload = f"{breadcrumb}\n{current_text}"
                result_chunks.append(
                    PolicyChunk(
                        chunk_id=self._generate_chunk_id(document_id, seq),
                        document_id=document_id,
                        policy_type=policy_type,
                        breadcrumb=breadcrumb,
                        section_title=section_title,
                        clause_title=clause_title,
                        text=payload,
                        char_length=len(payload),
                        token_estimate=len(payload) // 4,
                        metadata=metadata,
                    )
                )
                seq += 1
                # Sliding overlap: keep end of previous text
                overlap = current_text[-self.overlap_chars:] if len(current_text) > self.overlap_chars else ""
                current_text = (overlap + " ... " + p).strip() if overlap else p

        if current_text:
            payload = f"{breadcrumb}\n{current_text}"
            result_chunks.append(
                PolicyChunk(
                    chunk_id=self._generate_chunk_id(document_id, seq),
                    document_id=document_id,
                    policy_type=policy_type,
                    breadcrumb=breadcrumb,
                    section_title=section_title,
                    clause_title=clause_title,
                    text=payload,
                    char_length=len(payload),
                    token_estimate=len(payload) // 4,
                    metadata=metadata,
                )
            )

        return result_chunks

    def _generate_chunk_id(self, document_id: str, seq: int) -> str:
        clean_doc = Path(document_id).stem.upper()
        h = hashlib.md5(f"{clean_doc}_{seq}".encode()).hexdigest()[:6]
        return f"{clean_doc}_CHK{seq:03d}_{h}"
