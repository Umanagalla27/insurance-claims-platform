"""
Policy RAG Generation Service.
Coordinates hybrid retrieval, strict grounding prompts, and multi-tier LLM synthesis
(Google Gemini -> Local Ollama -> Deterministic Grounded Extractor).
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

import httpx

from api.app.schemas.rag import PolicyChunkCitation
from rag_chatbot.retrieval.service import PolicyRetrievalService

logger = logging.getLogger(__name__)

SYSTEM_GROUNDING_PROMPT = """You are the official Insurance Claims Intelligence Platform Policy Assistant.
Your mandate is to provide accurate, strictly grounded answers regarding insurance coverage, deductibles, limits, and exclusions.

CRITICAL RULES:
1. Base your answer EXCLUSIVELY on the provided Policy Context clauses below.
2. If the context does not contain sufficient information to answer the question, state:
   "Based on the provided policy documentation, this scenario is not explicitly covered or addressed. Please contact underwriting for a formal endorsement review."
3. Explicitly cite the Section Title and Clause Title for every policy condition mentioned.
4. Keep the answer professional, objective, and concise. Do NOT speculate or extrapolate outside the contract terms.
"""


class PolicyRAGService:
    """Production RAG orchestrator for policy questions."""

    def __init__(self, retrieval_service: PolicyRetrievalService):
        self.retrieval_service = retrieval_service
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "gemma2:2b")

    def format_citations(
        self, chunks: list[dict[str, Any]]
    ) -> list[PolicyChunkCitation]:
        """Convert reranked raw chunk dictionaries into structured Pydantic citations."""
        citations = []
        for c in chunks:
            meta = c.get("metadata", {})
            raw_text = c.get("text", "")
            # Short preview snippet
            snippet = raw_text[:250].replace("\n", " ").strip()
            if len(raw_text) > 250:
                snippet += "..."

            citations.append(
                PolicyChunkCitation(
                    chunk_id=c.get("chunk_id", meta.get("chunk_id", "N/A")),
                    document_id=c.get("document_id", meta.get("document_id", "N/A")),
                    policy_type=meta.get("policy_type", "GENERAL"),
                    section_title=meta.get("section_title", "General Provisions"),
                    clause_title=meta.get("clause_title", "Terms and Conditions"),
                    breadcrumb=meta.get("breadcrumb", ""),
                    relevance_score=round(
                        c.get("rerank_score", c.get("fused_score", 0.0)), 4
                    ),
                    snippet=snippet,
                )
            )
        return citations

    def _call_gemini(self, prompt: str) -> str | None:
        """Call Google Gemini REST API."""
        if not self.gemini_api_key:
            return None

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_api_key}"
        payload = {
            "contents": [
                {"parts": [{"text": f"{SYSTEM_GROUNDING_PROMPT}\n\n{prompt}"}]}
            ],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 800,
            },
        }

        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts and "text" in parts[0]:
                            return parts[0]["text"].strip()
                logger.warning(
                    "Gemini API non-200 status: %s - %s", resp.status_code, resp.text
                )
        except Exception as e:
            logger.warning("Gemini API call failed: %s", e)

        return None

    def _call_ollama(self, prompt: str) -> str | None:
        """Call local Ollama endpoint."""
        url = f"{self.ollama_url}/api/generate"
        payload = {
            "model": self.ollama_model,
            "prompt": f"{SYSTEM_GROUNDING_PROMPT}\n\n{prompt}",
            "stream": False,
            "options": {"temperature": 0.1},
        }

        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("response", "").strip()
        except Exception as e:
            logger.debug("Ollama local endpoint unavailable: %s", e)

        return None

    def _extractive_synthesis(self, query: str, chunks: list[dict[str, Any]]) -> str:
        """Deterministic, grounded extractive synthesis for zero-latency offline environments."""
        if not chunks:
            return (
                "Based on the provided policy documentation, this scenario is not explicitly "
                "covered or addressed in our repository. Please consult an underwriting specialist."
            )

        bullet_points = []
        for _i, c in enumerate(chunks[:3], 1):
            meta = c.get("metadata", {})
            sec = meta.get("section_title", "Coverage Terms")
            clause = meta.get("clause_title", "Conditions")
            ptype = meta.get("policy_type", "General")
            text = c.get("text", "").strip()

            # Take the first 2-3 sentences of the clause
            sentences = [
                s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()
            ]
            summary_sentences = " ".join(sentences[:2]) if sentences else text[:200]

            bullet_points.append(
                f"- **{sec} — {clause}** ({ptype}): {summary_sentences}"
            )

        context_bullets = "\n\n".join(bullet_points)
        answer = (
            f"According to the official policy terms on record regarding '{query}':\n\n"
            f"{context_bullets}\n\n"
            f"**Conclusion**: Policy application is contingent upon deductible satisfaction, "
            f"timely notice of loss, and strict adherence to the exclusion criteria noted above."
        )
        return answer

    def generate_answer(
        self,
        query: str,
        retrieval_result: dict[str, Any],
    ) -> tuple[str, str, float]:
        """Generate grounded answer using hybrid LLM / fallback cascade.

        Returns:
            Tuple of (answer_text, model_name, confidence_score)
        """
        chunks = retrieval_result.get("chunks", [])
        formatted_context = retrieval_result.get("formatted_context", "")

        # Compute confidence from top chunk score
        if chunks:
            top_score = chunks[0].get(
                "rerank_score", chunks[0].get("fused_score", 0.75)
            )
            confidence = min(0.99, max(0.55, float(top_score)))
        else:
            confidence = 0.30

        prompt = (
            f"### QUESTION\n{query}\n\n"
            f"### RELEVANT POLICY CONTEXT\n{formatted_context}\n\n"
            f"### YOUR AUTHORITATIVE ANSWER:"
        )

        # Check if external LLM generation is enabled (requires network / running daemon)
        enable_external_llm = os.getenv("ENABLE_EXTERNAL_LLM", "false").lower() in (
            "true",
            "1",
            "yes",
        )

        if enable_external_llm:
            # 1. Try Google Gemini API
            gemini_answer = self._call_gemini(prompt)
            if gemini_answer:
                return gemini_answer, "gemini-1.5-flash", round(confidence, 4)

            # 2. Try Local Ollama
            ollama_answer = self._call_ollama(prompt)
            if ollama_answer:
                return (
                    ollama_answer,
                    f"ollama/{self.ollama_model}",
                    round(confidence, 4),
                )

        # 3. Deterministic Grounded Extractive Synthesizer (Instant, offline & 100% reliable)
        extractive_answer = self._extractive_synthesis(query, chunks)
        return (
            extractive_answer,
            "grounded-extractive-synthesizer",
            round(confidence, 4),
        )
