"""
Insurance Claims Intelligence Platform — ML NLP Text Classifier Inference Engine
Component: ml/classification/predict.py

Provides production inference wrapper for loading the serialized model artifact
and classifying arbitrary claim narratives with confidence scores.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import joblib
from pydantic import BaseModel, Field

from ml.classification.preprocess import clean_claim_text

logger = logging.getLogger("ml.classification.predict")

DEFAULT_MODEL_PATH = Path("ml/artifacts/claim_classifier_tfidf_logreg.joblib")


class PredictionResult(BaseModel):
    """Pydantic model representing a single text classification result."""

    predicted_category: str = Field(..., description="Top predicted claim category")
    confidence: float = Field(..., description="Confidence probability for predicted category [0.0 - 1.0]")
    all_probabilities: dict[str, float] = Field(..., description="Probabilities across all categories")
    cleaned_text: str = Field(..., description="Normalized text analyzed by model")
    is_fallback: bool = Field(default=False, description="True if input had no signal and triggered fallback")


class ClaimClassifier:
    """Production inference engine for insurance claim category classification."""

    def __init__(self, model_path: Path | str = DEFAULT_MODEL_PATH) -> None:
        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model artifact not found at {self.model_path}")

        payload = joblib.load(self.model_path)
        if isinstance(payload, dict) and "pipeline" in payload:
            self.pipeline = payload["pipeline"]
            self.classes: list[str] = payload["classes"]
            self.metadata: dict[str, Any] = payload.get("metadata", {})
        else:
            self.pipeline = payload
            self.classes = sorted(self.pipeline.classes_)
            self.metadata = {}

        logger.info("ClaimClassifier initialized with %d classes from %s", len(self.classes), self.model_path)

    def predict(self, raw_text: str | None) -> PredictionResult:
        """Classify a single claim text narrative.

        Handles edge cases:
        - None or empty text: returns fallback prediction with lowest confidence.
        - Text with no valid tokens: returns fallback.
        - Valid text: computes softmax class probabilities.
        """
        cleaned = clean_claim_text(raw_text)

        if not cleaned:
            # Fallback for empty/uninformative descriptions
            equal_prob = round(1.0 / len(self.classes), 4)
            return PredictionResult(
                predicted_category="General",
                confidence=0.0,
                all_probabilities=dict.fromkeys(self.classes, equal_prob),
                cleaned_text="",
                is_fallback=True,
            )

        # Scikit-learn pipeline inference
        probabilities = self.pipeline.predict_proba([cleaned])[0]
        prob_dict = {
            cls_name: round(float(prob), 4)
            for cls_name, prob in zip(self.classes, probabilities, strict=True)
        }

        top_idx = int(probabilities.argmax())
        top_category = self.classes[top_idx]
        top_confidence = round(float(probabilities[top_idx]), 4)

        return PredictionResult(
            predicted_category=top_category,
            confidence=top_confidence,
            all_probabilities=prob_dict,
            cleaned_text=cleaned,
            is_fallback=False,
        )

    def predict_batch(self, raw_texts: list[str | None]) -> list[PredictionResult]:
        """Classify a list of claim narratives efficiently."""
        return [self.predict(t) for t in raw_texts]
