"""
Unit and Integration Tests for NLP Model Evaluation & Error Analysis
Component: ml/tests/test_evaluation.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ml.classification.evaluate import (
    compute_comprehensive_metrics,
    evaluate_and_export,
    extract_feature_importances,
    format_confusion_matrix_ascii,
    load_model_and_test_data,
    run_boundary_error_analysis,
)


@pytest.fixture(scope="module")
def eval_setup():
    pipeline, classes, X_test, y_test = load_model_and_test_data()
    return pipeline, classes, X_test, y_test


@pytest.mark.integration
class TestEvaluationEngine:
    """Tests covering metric calculation, matrix shapes, and feature explainability."""

    def test_load_model_and_data_contracts(self, eval_setup) -> None:
        pipeline, classes, X_test, y_test = eval_setup
        assert len(classes) == 7
        assert len(X_test) == 1679
        assert len(y_test) == 1679
        assert set(classes) == {
            "Auto",
            "Disability",
            "Liability",
            "Life",
            "Medical",
            "Property",
            "Travel",
        }

    def test_compute_comprehensive_metrics_structure(self, eval_setup) -> None:
        pipeline, classes, X_test, y_test = eval_setup
        metrics = compute_comprehensive_metrics(pipeline, classes, X_test, y_test)

        overall = metrics["overall_metrics"]
        assert 0.0 <= overall["accuracy"] <= 1.0
        assert 0.0 <= overall["macro_f1"] <= 1.0
        assert 0.0 <= overall["ovr_roc_auc"] <= 1.0

        per_class = metrics["per_class_metrics"]
        for cls_name in classes:
            assert cls_name in per_class
            assert per_class[cls_name]["support"] > 0
            assert 0.0 <= per_class[cls_name]["f1_score"] <= 1.0

        conf_mat = metrics["confusion_matrix"]["matrix"]
        assert len(conf_mat) == 7
        assert all(len(row) == 7 for row in conf_mat)
        total_matrix_elements = sum(sum(row) for row in conf_mat)
        assert total_matrix_elements == len(X_test)

    def test_extract_feature_importances_coefficients(self, eval_setup) -> None:
        pipeline, classes, _, _ = eval_setup
        features = extract_feature_importances(pipeline, classes, top_n=5)

        for cls_name in classes:
            assert cls_name in features
            top_pos = features[cls_name]["top_positive_features"]
            top_neg = features[cls_name]["top_negative_features"]
            assert len(top_pos) == 5
            assert len(top_neg) == 5
            # Top positive coefficient should be positive
            assert top_pos[0]["weight"] > 0.0
            assert isinstance(top_pos[0]["token"], str)

    def test_boundary_error_analysis_and_stress_cases(self, eval_setup) -> None:
        pipeline, classes, X_test, y_test = eval_setup
        report = run_boundary_error_analysis(pipeline, classes, X_test, y_test)

        assert "boundary_stress_tests" in report
        stress_cases = report["boundary_stress_tests"]
        assert len(stress_cases) == 4

        for sc in stress_cases:
            assert sc["predicted_category"] in classes
            assert 0.0 < sc["confidence"] <= 1.0
            assert "margin_to_second" in sc
            # Verify stress tests have lower confidence than pristine training samples
            assert sc["confidence"] < 0.90

    def test_ascii_confusion_matrix_formatter(self) -> None:
        labels = ["A", "B"]
        mat = [[10, 2], [1, 15]]
        formatted = format_confusion_matrix_ascii(labels, mat)
        assert "Actual \\ Pred" in formatted
        assert "A" in formatted
        assert "B" in formatted
        assert "10" in formatted
        assert "15" in formatted

    def test_evaluate_and_export_writes_valid_json_files(self, tmp_path: Path) -> None:
        result = evaluate_and_export(artifact_dir=tmp_path)
        assert "metrics" in result
        assert "features" in result
        assert "error_analysis" in result

        metrics_file = tmp_path / "eval_metrics.json"
        features_file = tmp_path / "feature_importances.json"
        error_file = tmp_path / "error_analysis.json"

        assert metrics_file.exists()
        assert features_file.exists()
        assert error_file.exists()

        with open(metrics_file, encoding="utf-8") as f:
            data = json.load(f)
            assert data["total_test_samples"] == 1679
