"""Okapi BM25 Sparse Keyword Search Engine.

Implements standard Okapi BM25 ranking algorithm with Robertson-Spärck Jones IDF:
    Score(D, Q) = sum_{q in Q} IDF(q) * (f(q, D) * (k1 + 1)) / (f(q, D) + k1 * (1 - b + b * (|D| / avgdl)))
    where IDF(q) = ln( (N - n(q) + 0.5) / (n(q) + 0.5) + 1.0 )
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, Dict, List, Optional


POLICY_TYPE_ALIASES = {
    "auto": "Auto",
    "automobile": "Auto",
    "vehicle": "Auto",
    "homeowners": "Property",
    "property": "Property",
    "home": "Property",
    "health": "Medical",
    "medical": "Medical",
    "liability": "Liability",
    "commercial": "Liability",
    "life": "Life",
    "travel": "Travel",
    "disability": "Disability",
}


def normalize_policy_type(ptype: Optional[str]) -> Optional[str]:
    """Map user-provided policy type synonyms to canonical category."""
    if not ptype:
        return None
    cleaned = ptype.strip().lower()
    return POLICY_TYPE_ALIASES.get(cleaned, cleaned.capitalize())


def tokenize(text: str) -> List[str]:
    """Tokenize text into lowercase alphanumeric tokens.
    
    Preserves numbers and clause identifiers (e.g., '3.1', '2a').
    """
    if not text:
        return []
    # Match words, numbers, and section numbers like 3.1
    tokens = re.findall(r"[a-zA-Z0-9]+(?:\.[a-zA-Z0-9]+)*", text.lower())
    return tokens


class BM25SearchEngine:
    """Okapi BM25 index for policy document chunks.
    
    Parameters:
        k1: Term frequency saturation parameter (typical: 1.2 to 2.0).
        b: Document length normalization parameter (typical: 0.75).
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = float(k1)
        self.b = float(b)
        self.corpus_size: int = 0
        self.avg_doc_len: float = 0.0
        self.doc_lengths: List[int] = []
        self.doc_token_counts: List[Counter] = []
        self.doc_frequencies: Dict[str, int] = {}
        self.idf_cache: Dict[str, float] = {}
        self.metadata: List[Dict[str, Any]] = []
        self.documents: List[str] = []

    def fit(self, documents: List[str], metadata: Optional[List[Dict[str, Any]]] = None) -> BM25SearchEngine:
        """Build the inverted index and compute BM25 statistics from raw texts.
        
        Args:
            documents: List of document strings (chunks).
            metadata: Parallel list of chunk metadata dictionaries.
        """
        self.corpus_size = len(documents)
        self.documents = list(documents)
        self.metadata = list(metadata) if metadata else [{} for _ in documents]

        if self.corpus_size == 0:
            self.avg_doc_len = 0.0
            return self

        self.doc_lengths = []
        self.doc_token_counts = []
        self.doc_frequencies = {}

        total_length = 0
        for doc in documents:
            tokens = tokenize(doc)
            length = len(tokens)
            self.doc_lengths.append(length)
            total_length += length

            counts = Counter(tokens)
            self.doc_token_counts.append(counts)

            for token in counts.keys():
                self.doc_frequencies[token] = self.doc_frequencies.get(token, 0) + 1

        self.avg_doc_len = total_length / self.corpus_size if self.corpus_size > 0 else 0.0

        # Precompute RSJ IDF
        self.idf_cache = {}
        for token, df in self.doc_frequencies.items():
            # Standard Okapi IDF with floor at 0.0
            # IDF = ln( (N - df + 0.5) / (df + 0.5) + 1.0 )
            val = math.log(((self.corpus_size - df + 0.5) / (df + 0.5)) + 1.0)
            self.idf_cache[token] = max(val, 0.0)

        return self

    def search(
        self,
        query: str,
        top_k: int = 5,
        policy_type_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Score all documents against query using BM25 and return top_k matches.
        
        Args:
            query: User's search prompt.
            top_k: Number of highest-ranked documents to return.
            policy_type_filter: Optional string filter (e.g. 'AUTO', 'HEALTH').
        """
        if self.corpus_size == 0:
            return []

        q_tokens = tokenize(query)
        if not q_tokens:
            return []

        # Filter query tokens to those present in vocab
        active_tokens = [t for t in q_tokens if t in self.idf_cache]
        if not active_tokens:
            return []

        scores: List[tuple[int, float]] = []

        k1 = self.k1
        b = self.b
        avgdl = self.avg_doc_len if self.avg_doc_len > 0 else 1.0

        for doc_idx in range(self.corpus_size):
            meta = self.metadata[doc_idx]

            # Apply metadata filter
            if policy_type_filter:
                norm_filter = normalize_policy_type(policy_type_filter)
                doc_policy = normalize_policy_type(meta.get("policy_type", ""))
                if doc_policy != norm_filter:
                    continue

            d_len = self.doc_lengths[doc_idx]
            counts = self.doc_token_counts[doc_idx]

            doc_score = 0.0
            len_penalty = k1 * (1.0 - b + b * (d_len / avgdl))

            for t in active_tokens:
                tf = counts.get(t, 0)
                if tf > 0:
                    idf = self.idf_cache[t]
                    numerator = tf * (k1 + 1.0)
                    denominator = tf + len_penalty
                    doc_score += idf * (numerator / denominator)

            if doc_score > 0.0:
                scores.append((doc_idx, doc_score))

        # Sort descending by score
        scores.sort(key=lambda x: x[1], reverse=True)
        top_matches = scores[:top_k]

        results = []
        for rank, (doc_idx, score) in enumerate(top_matches, start=1):
            results.append({
                "rank": rank,
                "score": float(score),
                "text": self.documents[doc_idx],
                "metadata": self.metadata[doc_idx],
            })

        return results
