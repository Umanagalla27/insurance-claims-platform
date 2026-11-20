"""
Insurance Claims Intelligence Platform — ML NLP Text Preprocessor
Component: ml/classification/preprocess.py

Provides robust, self-contained text normalization, cleaning, and tokenization
optimized for unstructured insurance claim narratives.
"""

from __future__ import annotations

import re
import string
from collections.abc import Sequence

# Curated English stop words list (independent of external NLTK downloads for reliable offline/CI execution)
STANDARD_STOPWORDS: frozenset[str] = frozenset(
    {
        "a",
        "about",
        "above",
        "after",
        "again",
        "against",
        "all",
        "am",
        "an",
        "and",
        "any",
        "are",
        "aren't",
        "as",
        "at",
        "be",
        "because",
        "been",
        "before",
        "being",
        "below",
        "between",
        "both",
        "but",
        "by",
        "can't",
        "cannot",
        "could",
        "couldn't",
        "did",
        "didn't",
        "do",
        "does",
        "doesn't",
        "doing",
        "don't",
        "down",
        "during",
        "each",
        "few",
        "for",
        "from",
        "further",
        "had",
        "hadn't",
        "has",
        "hasn't",
        "have",
        "haven't",
        "having",
        "he",
        "he'd",
        "he'll",
        "he's",
        "her",
        "here",
        "here's",
        "hers",
        "herself",
        "him",
        "himself",
        "his",
        "how",
        "how's",
        "i",
        "i'd",
        "i'll",
        "i'm",
        "i've",
        "if",
        "in",
        "into",
        "is",
        "isn't",
        "it",
        "it's",
        "its",
        "itself",
        "let's",
        "me",
        "more",
        "most",
        "mustn't",
        "my",
        "myself",
        "no",
        "nor",
        "not",
        "of",
        "off",
        "on",
        "once",
        "only",
        "or",
        "other",
        "ought",
        "our",
        "ours",
        "ourselves",
        "out",
        "over",
        "own",
        "same",
        "shan't",
        "she",
        "she'd",
        "she'll",
        "she's",
        "should",
        "shouldn't",
        "so",
        "some",
        "such",
        "than",
        "that",
        "that's",
        "the",
        "their",
        "theirs",
        "them",
        "themselves",
        "then",
        "there",
        "there's",
        "these",
        "they",
        "they'd",
        "they'll",
        "they're",
        "they've",
        "this",
        "those",
        "through",
        "to",
        "too",
        "under",
        "until",
        "up",
        "very",
        "was",
        "wasn't",
        "we",
        "we'd",
        "we'll",
        "we're",
        "we've",
        "were",
        "weren't",
        "what",
        "what's",
        "when",
        "when's",
        "where",
        "where's",
        "which",
        "while",
        "who",
        "who's",
        "whom",
        "why",
        "why's",
        "with",
        "won't",
        "would",
        "wouldn't",
        "you",
        "you'd",
        "you'll",
        "you're",
        "you've",
        "your",
        "yours",
        "yourself",
        "yourselves",
    }
)

PLACEHOLDER_REGEX = re.compile(r"\[NO DESCRIPTION PROVIDED[^\]]*\]", re.IGNORECASE)
CURRENCY_REGEX = re.compile(r"\$\d+(?:,\d+)*(?:\.\d+)?")
DATE_REGEX = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
DIGITS_REGEX = re.compile(r"\b\d+\b")
URL_REGEX = re.compile(r"https?://\S+|www\.\S+")
PUNCT_TRANSLATOR = str.maketrans(string.punctuation, " " * len(string.punctuation))


def clean_claim_text(
    text: str | None,
    remove_stopwords: bool = True,
    normalize_numbers: bool = True,
) -> str:
    """Clean and normalize an insurance claim description.

    Steps:
    1. Handle None, empty strings, and placeholder templates.
    2. Lowercase transformation.
    3. Remove URLs and dates (high variance, zero category signal).
    4. Normalize or remove raw currency amounts ($4,293 -> currency_token or strip).
    5. Replace punctuation with whitespace.
    6. Tokenize on whitespace and optionally remove stop words.
    7. Rejoin into clean normalized string.

    Args:
        text: Raw narrative string.
        remove_stopwords: Whether to filter out standard English stop words.
        normalize_numbers: Whether to convert standalone digits into a token or remove.

    Returns:
        Cleaned, normalized string.
    """
    if text is None:
        return ""

    raw = str(text).strip()
    if not raw or PLACEHOLDER_REGEX.search(raw):
        return ""

    # Lowercase
    cleaned = raw.lower()

    # Strip URLs
    cleaned = URL_REGEX.sub(" ", cleaned)

    # Strip ISO dates (e.g., 2025-10-27)
    cleaned = DATE_REGEX.sub(" ", cleaned)

    # Replace currency amounts with token
    cleaned = CURRENCY_REGEX.sub(" amount_token ", cleaned)

    # Remove punctuation
    cleaned = cleaned.translate(PUNCT_TRANSLATOR)

    # Normalize standalone digits if requested
    if normalize_numbers:
        cleaned = DIGITS_REGEX.sub(" num_token ", cleaned)

    # Tokenize and filter stop words
    tokens = cleaned.split()
    if remove_stopwords:
        tokens = [
            tok for tok in tokens if tok not in STANDARD_STOPWORDS and len(tok) > 1
        ]
    else:
        tokens = [tok for tok in tokens if len(tok) > 1]

    return " ".join(tokens)


def batch_clean_texts(
    texts: Sequence[str | None],
    remove_stopwords: bool = True,
) -> list[str]:
    """Clean an iterable collection of claim description strings."""
    return [clean_claim_text(t, remove_stopwords=remove_stopwords) for t in texts]
