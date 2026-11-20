"""
Unit and Integration Tests for ML NLP Text Classifier
Component: ml/tests/test_text_classifier.py
"""

from __future__ import annotations

import pytest
from sklearn.pipeline import Pipeline

from ml.classification.predict import ClaimClassifier, PredictionResult
from ml.classification.preprocess import clean_claim_text
from ml.classification.train import build_pipeline


@pytest.mark.unit
class TestPreprocess:
    """Unit tests for claim narrative preprocessing and cleaning."""

    def test_clean_text_handles_none_and_empty(self) -> None:
        assert clean_claim_text(None) == ""
        assert clean_claim_text("") == ""
        assert clean_claim_text("   \n\t  ") == ""

    def test_clean_text_filters_placeholders(self) -> None:
        placeholder = "[NO DESCRIPTION PROVIDED - PENDING REVIEW]"
        assert clean_claim_text(placeholder) == ""

        partial_placeholder = "[NO DESCRIPTION PROVIDED]"
        assert clean_claim_text(partial_placeholder) == ""

    def test_clean_text_strips_urls_and_dates(self) -> None:
        raw = "Incident report at https://claims.example.com/view happened on 2026-08-23 near junction."
        cleaned = clean_claim_text(raw)
        assert "https" not in cleaned
        assert "2026-08-23" not in cleaned
        assert "incident" in cleaned
        assert "junction" in cleaned

    def test_clean_text_replaces_currency_and_punctuation(self) -> None:
        raw = "Estimated repair cost is $36,658. Airbags deployed, vehicle totaled!"
        cleaned = clean_claim_text(raw)
        assert "$" not in cleaned
        assert "!" not in cleaned
        assert "," not in cleaned
        assert "airbags" in cleaned
        assert "deployed" in cleaned
        assert "totaled" in cleaned

    def test_clean_text_filters_stopwords(self) -> None:
        raw = "The claimant was in their car when it was hit by another vehicle."
        cleaned = clean_claim_text(raw, remove_stopwords=True)
        tokens = cleaned.split()
        for sw in ["the", "was", "in", "their", "when", "it", "by"]:
            assert sw not in tokens
        assert "claimant" in tokens
        assert "car" in tokens
        assert "hit" in tokens
        assert "vehicle" in tokens


@pytest.mark.unit
class TestPipelineArchitecture:
    """Unit tests verifying pipeline construction and component contracts."""

    def test_build_pipeline_structure(self) -> None:
        pipeline = build_pipeline()
        assert isinstance(pipeline, Pipeline)
        assert "tfidf" in pipeline.named_steps
        assert "classifier" in pipeline.named_steps

    def test_pipeline_fits_on_toy_dataset(self) -> None:
        pipeline = build_pipeline()
        # Ensure terms overlap across docs so min_df=2 is satisfied
        texts = [
            "claim incident rear-ended collision car fender bumper repair claim",
            "claim incident car collision bumper damage body shop",
            "claim incident broken water pipe flooded basement property damage",
            "claim incident water flooding burst pipe ceiling repair property damage",
        ]
        labels = ["Auto", "Auto", "Property", "Property"]
        pipeline.fit(texts, labels)

        preds = pipeline.predict(["car collision bumper repair"])
        assert len(preds) == 1
        assert preds[0] in labels


@pytest.fixture(scope="module")
def shared_classifier() -> ClaimClassifier:
    """Module-level fixture to load classifier once across test suite."""
    return ClaimClassifier()


@pytest.mark.integration
class TestInferenceEngine:
    """Integration tests verifying model loading, classification, and edge case fallbacks."""

    def test_model_artifact_loaded(self, shared_classifier: ClaimClassifier) -> None:
        assert len(shared_classifier.classes) == 7
        expected_classes = {"Auto", "Disability", "Liability", "Life", "Medical", "Property", "Travel"}
        assert set(shared_classifier.classes) == expected_classes

    def test_predict_auto_claim(self, shared_classifier: ClaimClassifier) -> None:
        narrative = "Rear-ended collision at highway intersection. Bumper damaged, airbags deployed, towed to body shop."
        result = shared_classifier.predict(narrative)
        assert isinstance(result, PredictionResult)
        assert result.predicted_category == "Auto"
        assert result.confidence > 0.50
        assert not result.is_fallback
        assert sum(result.all_probabilities.values()) == pytest.approx(1.0, abs=0.02)

    def test_predict_property_claim(self, shared_classifier: ClaimClassifier) -> None:
        narrative = "Property sustained extensive damage due to burst pipe causing water flooding throughout ground floor."
        result = shared_classifier.predict(narrative)
        assert result.predicted_category == "Property"
        assert result.confidence > 0.50
        assert not result.is_fallback

    def test_predict_medical_claim(self, shared_classifier: ClaimClassifier) -> None:
        narrative = "Prescription medication and outpatient orthopedic surgery consultation with Dr. Miller at St. Jude Hospital."
        result = shared_classifier.predict(narrative)
        assert result.predicted_category == "Medical"
        assert result.confidence > 0.50

    def test_predict_travel_claim(self, shared_classifier: ClaimClassifier) -> None:
        narrative = "Delayed flight baggage missing at airport international arrivals carousel. Airline reference BAG-9876."
        result = shared_classifier.predict(narrative)
        assert result.predicted_category == "Travel"
        assert result.confidence > 0.50

    def test_fallback_on_empty_and_placeholder(self, shared_classifier: ClaimClassifier) -> None:
        empty_res = shared_classifier.predict("")
        assert empty_res.is_fallback is True
        assert empty_res.confidence == 0.0

        placeholder_res = shared_classifier.predict("[NO DESCRIPTION PROVIDED - PENDING REVIEW]")
        assert placeholder_res.is_fallback is True
        assert placeholder_res.confidence == 0.0

    def test_predict_batch_consistency(self, shared_classifier: ClaimClassifier) -> None:
        batch = [
            "Multi-car collision rear-ended at highway traffic signal",
            "Property sustained extensive water damage from burst plumbing pipe flooding",
            None,
        ]
        results = shared_classifier.predict_batch(batch)
        assert len(results) == 3
        assert results[0].predicted_category == "Auto"
        assert results[1].predicted_category == "Property"
        assert results[2].is_fallback is True
