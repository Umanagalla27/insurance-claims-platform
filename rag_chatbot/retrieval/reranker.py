"""Context Reranker and Formatter for RAG Generation.

Takes candidate chunks retrieved by Hybrid Search and performs fine-grained
re-ranking based on exact lexical phrase alignment, section coverage, and
clause reference boosts, producing citation-tagged context for LLM generation.
"""

from __future__ import annotations

import re
from typing import Any


class ContextReranker:
    """Reranks candidate chunks and formats prompt-ready context blocks."""

    def __init__(
        self,
        exact_clause_boost: float = 0.35,
        title_match_boost: float = 0.20,
    ):
        self.exact_clause_boost = exact_clause_boost
        self.title_match_boost = title_match_boost

    def rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """Rerank candidates based on fine-grained lexical and structural features.

        Args:
            query: User's prompt / question.
            candidates: Candidate list from HybridRetriever.
            top_k: Number of highest-priority candidates to retain.
        """
        if not candidates:
            return []

        q_lower = query.lower()
        q_tokens = set(re.findall(r"\b[a-z0-9]+\b", q_lower))

        # Check for specific clause pattern like '3.1', 'clause 2', 'section 4'
        clause_matches = re.findall(r"\b(?:\d+\.\d+|\d+)\b", q_lower)

        reranked = []
        for cand in candidates:
            base_score = cand.get("fused_score", 0.0)
            meta = cand.get("metadata", {})
            text = cand.get("text", "").lower()
            clause_id = meta.get("clause_id", "").lower()
            clause_title = meta.get("clause_title", "").lower()
            section_title = meta.get("section_title", "").lower()

            bonus = 0.0

            # 1. Exact clause/section number match
            for cm in clause_matches:
                if cm in clause_id or cm in clause_title:
                    bonus += self.exact_clause_boost
                    break

            # 2. Title & section keyword overlap
            title_tokens = set(
                re.findall(r"\b[a-z0-9]+\b", f"{clause_title} {section_title}")
            )
            overlap = len(q_tokens & title_tokens)
            if overlap > 0:
                bonus += min(
                    overlap * (self.title_match_boost / 2.0), self.title_match_boost
                )

            # 3. Content token coverage (Jaccard-like bonus)
            body_tokens = set(re.findall(r"\b[a-z0-9]+\b", text))
            if body_tokens:
                coverage = len(q_tokens & body_tokens) / max(len(q_tokens), 1)
                bonus += coverage * 0.15

            final_score = base_score + bonus

            reranked_item = dict(cand)
            reranked_item["rerank_score"] = round(final_score, 4)
            reranked_item["rerank_bonus"] = round(bonus, 4)
            reranked.append(reranked_item)

        # Sort descending by rerank_score
        reranked.sort(key=lambda x: x["rerank_score"], reverse=True)

        for new_rank, item in enumerate(reranked[:top_k], start=1):
            item["final_rank"] = new_rank

        return reranked[:top_k]

    def format_context_for_prompt(self, reranked_chunks: list[dict[str, Any]]) -> str:
        """Format reranked chunks into clean, citation-tagged Markdown context for LLM prompts."""
        if not reranked_chunks:
            return "No relevant policy documents found."

        context_blocks = []
        for idx, chunk in enumerate(reranked_chunks, start=1):
            meta = chunk.get("metadata", {})
            policy_id = meta.get("policy_id", "POLICY")
            section = meta.get("section_title", "Section")
            clause = meta.get("clause_title", "Clause")
            clause_id = meta.get("clause_id", "")
            clause_hdr = f"{clause_id} - {clause}" if clause_id else clause

            header = f"[Source {idx}: {policy_id} | {section} > {clause_hdr}]"
            body = chunk.get("text", "").strip()

            context_blocks.append(f"{header}\n{body}")

        return "\n\n---\n\n".join(context_blocks)
