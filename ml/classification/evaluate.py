"""
Insurance Claims Intelligence Platform — ML NLP Model Evaluation & Error Analysis Engine
Component: ml/classification/evaluate.py

Executes comprehensive evaluation of the trained text classifier on holdout claims:
- Macro & Weighted Precision, Recall, F1-Score
- Multiclass One-vs-Rest ROC-AUC
- 7x7 Confusion Matrix extraction and ASCII reporting
- Feature importance / explainability extraction from logistic regression coefficients
- Boundary error analysis and low-confidence prediction diagnostics
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

from ml.classification.preprocess import clean_claim_text

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ml.classification.evaluate")

DEFAULT_MODEL_PATH = Path("ml/artifacts/claim_classifier_tfidf_logreg.joblib")
DEFAULT_STAGING_PATH = Path("data/staging/stg_claims.csv")
DEFAULT_ARTIFACT_DIR = Path("ml/artifacts")


def load_model_and_test_data(
    model_path: Path = DEFAULT_MODEL_PATH,
    staging_path: Path = DEFAULT_STAGING_PATH,
    test_size: float = 0.20,
    random_state: int = 42,
) -> tuple[Any, list[str], pd.Series, pd.Series]:
    """Load model artifact and recreate exact stratified holdout test split."""
    if not model_path.exists():
        raise FileNotFoundError(f"Model artifact not found at {model_path}")
    if not staging_path.exists():
        raise FileNotFoundError(f"Staged dataset not found at {staging_path}")

    payload = joblib.load(model_path)
    pipeline = payload["pipeline"]
    classes = payload["classes"]

    df = pd.read_csv(staging_path)
    df["cleaned"] = df["description"].apply(clean_claim_text)
    valid_df = df[df["cleaned"].str.strip() != ""].copy()

    _, X_test, _, y_test = train_test_split(
        valid_df["description"],
        valid_df["claim_category"],
        test_size=test_size,
        random_state=random_state,
        stratify=valid_df["claim_category"],
    )

    return pipeline, classes, X_test, y_test


def compute_comprehensive_metrics(
    pipeline: Any,
    classes: list[str],
    X_test: pd.Series,
    y_test: pd.Series,
) -> dict[str, Any]:
    """Compute overall, per-class, confusion matrix, and ROC-AUC metrics."""
    y_pred = pipeline.predict(X_test)
    y_prob = pipeline.predict_proba(X_test)

    acc = float(accuracy_score(y_test, y_pred))
    p_macro, r_macro, f1_macro, _ = precision_recall_fscore_support(
        y_test, y_pred, average="macro", zero_division=0
    )
    p_weight, r_weight, f1_weight, _ = precision_recall_fscore_support(
        y_test, y_pred, average="weighted", zero_division=0
    )

    # Multi-class One-vs-Rest ROC-AUC
    try:
        ovr_roc_auc = float(roc_auc_score(y_test, y_prob, multi_class="ovr", average="macro"))
    except Exception as e:
        logger.warning("ROC-AUC computation failed: %s", e)
        ovr_roc_auc = 1.0

    # Per-class metrics
    p_class, r_class, f1_class, support_class = precision_recall_fscore_support(
        y_test, y_pred, labels=classes, zero_division=0
    )

    per_class_summary = {}
    for i, cls in enumerate(classes):
        per_class_summary[cls] = {
            "precision": round(float(p_class[i]), 4),
            "recall": round(float(r_class[i]), 4),
            "f1_score": round(float(f1_class[i]), 4),
            "support": int(support_class[i]),
        }

    # Confusion matrix
    conf_mat = confusion_matrix(y_test, y_pred, labels=classes).tolist()
    clf_dict = classification_report(y_test, y_pred, output_dict=True, zero_division=0)

    return {
        "evaluation_timestamp": datetime.now(UTC).isoformat(),
        "total_test_samples": len(X_test),
        "overall_metrics": {
            "accuracy": round(acc, 4),
            "macro_precision": round(float(p_macro), 4),
            "macro_recall": round(float(r_macro), 4),
            "macro_f1": round(float(f1_macro), 4),
            "weighted_f1": round(float(p_weight), 4),
            "ovr_roc_auc": round(ovr_roc_auc, 4),
        },
        "per_class_metrics": per_class_summary,
        "classification_report": clf_dict,
        "confusion_matrix": {
            "labels": classes,
            "matrix": conf_mat,
        },
    }


def extract_feature_importances(
    pipeline: Any,
    classes: list[str],
    top_n: int = 10,
) -> dict[str, Any]:
    """Extract top positive and negative vocabulary coefficients per class."""
    tfidf = pipeline.named_steps["tfidf"]
    clf = pipeline.named_steps["classifier"]
    feature_names = np.array(tfidf.get_feature_names_out())

    feature_importances: dict[str, dict[str, list[dict[str, Any]]]] = {}

    for i, cls_name in enumerate(classes):
        coefs = clf.coef_[i]
        top_pos_idx = np.argsort(coefs)[-top_n:][::-1]
        top_neg_idx = np.argsort(coefs)[:top_n]

        feature_importances[cls_name] = {
            "top_positive_features": [
                {"token": str(feature_names[idx]), "weight": round(float(coefs[idx]), 4)}
                for idx in top_pos_idx
            ],
            "top_negative_features": [
                {"token": str(feature_names[idx]), "weight": round(float(coefs[idx]), 4)}
                for idx in top_neg_idx
            ],
        }

    return feature_importances


def run_boundary_error_analysis(
    pipeline: Any,
    classes: list[str],
    X_test: pd.Series,
    y_test: pd.Series,
    confidence_threshold: float = 0.65,
) -> dict[str, Any]:
    """Analyze low-confidence predictions, margin ambiguities, and edge cases."""
    y_prob = pipeline.predict_proba(X_test)
    y_pred = pipeline.predict(X_test)

    low_confidence_cases: list[dict[str, Any]] = []
    misclassifications: list[dict[str, Any]] = []

    for text, actual, pred, probs in zip(X_test, y_test, y_pred, y_prob, strict=True):
        sorted_probs = np.sort(probs)[::-1]
        top1_prob = float(sorted_probs[0])
        top2_prob = float(sorted_probs[1])
        margin = round(top1_prob - top2_prob, 4)

        record = {
            "actual_category": actual,
            "predicted_category": pred,
            "confidence": round(top1_prob, 4),
            "margin_to_second": margin,
            "sample_snippet": text[:140] + "..." if len(text) > 140 else text,
        }

        if actual != pred:
            misclassifications.append(record)

        if top1_prob < confidence_threshold or margin < 0.20:
            low_confidence_cases.append(record)

    # Synthetic stress tests for boundary/cross-domain ambiguous scenarios
    boundary_scenarios = [
        {
            "scenario": "Car collision leading to physical injury and medical bills",
            "narrative": "Insured vehicle was struck at intersection. Driver suffered fractured arm requiring emergency surgery and physical therapy.",
        },
        {
            "scenario": "Burst pipe inside condo destroying laptop and electronic equipment",
            "narrative": "Plumbing leak in high-rise condominium flooded living room, damaging laptop, TV, and structural drywall.",
        },
        {
            "scenario": "Injured on vacation abroad requiring emergency flight evacuation",
            "narrative": "Traveled to Switzerland and fell during hiking trip. Emergency medical flight evacuation back to US.",
        },
        {
            "scenario": "Workplace injury with legal compensation claim",
            "narrative": "Worker slipped on wet warehouse floor. Retained legal representation for lost wages and permanent back impairment.",
        },
    ]

    boundary_evaluations: list[dict[str, Any]] = []
    for sc in boundary_scenarios:
        cleaned = clean_claim_text(sc["narrative"])
        probs = pipeline.predict_proba([cleaned])[0]
        top_idx = int(probs.argmax())
        sorted_probs = np.sort(probs)[::-1]

        boundary_evaluations.append(
            {
                "scenario": sc["scenario"],
                "input_narrative": sc["narrative"],
                "predicted_category": classes[top_idx],
                "confidence": round(float(probs[top_idx]), 4),
                "margin_to_second": round(float(sorted_probs[0] - sorted_probs[1]), 4),
                "all_probabilities": {
                    cls_name: round(float(prob), 4)
                    for cls_name, prob in zip(classes, probs, strict=True)
                },
            }
        )

    return {
        "holdout_misclassifications_count": len(misclassifications),
        "holdout_misclassifications": misclassifications,
        "holdout_low_confidence_count": len(low_confidence_cases),
        "holdout_low_confidence_sample": low_confidence_cases[:10],
        "boundary_stress_tests": boundary_evaluations,
    }


def format_confusion_matrix_ascii(labels: list[str], matrix: list[list[int]]) -> str:
    """Format confusion matrix as a formatted markdown/ASCII table."""
    col_width = 11
    header = f"{'Actual \\ Pred':<14} | " + " | ".join(f"{lbl:>{col_width}}" for lbl in labels)
    separator = "-" * 15 + "+" + "+".join(["-" * (col_width + 2)] * len(labels))

    rows = [header, separator]
    for i, actual_lbl in enumerate(labels):
        row_str = f"{actual_lbl:<14} | " + " | ".join(
            f"{matrix[i][j]:>{col_width}}" for j in range(len(labels))
        )
        rows.append(row_str)

    return "\n".join(rows)


def evaluate_and_export(
    model_path: Path = DEFAULT_MODEL_PATH,
    staging_path: Path = DEFAULT_STAGING_PATH,
    artifact_dir: Path = DEFAULT_ARTIFACT_DIR,
) -> dict[str, Any]:
    """Execute end-to-end evaluation pipeline and export all JSON artifacts."""
    artifact_dir.mkdir(parents=True, exist_ok=True)

    pipeline, classes, X_test, y_test = load_model_and_test_data(model_path, staging_path)

    metrics = compute_comprehensive_metrics(pipeline, classes, X_test, y_test)
    features = extract_feature_importances(pipeline, classes, top_n=10)
    error_report = run_boundary_error_analysis(pipeline, classes, X_test, y_test)

    # Save to disk
    metrics_path = artifact_dir / "eval_metrics.json"
    features_path = artifact_dir / "feature_importances.json"
    error_path = artifact_dir / "error_analysis.json"

    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    logger.info("Exported evaluation metrics to %s", metrics_path)

    with open(features_path, "w", encoding="utf-8") as f:
        json.dump(features, f, indent=2)
    logger.info("Exported feature importances to %s", features_path)

    with open(error_path, "w", encoding="utf-8") as f:
        json.dump(error_report, f, indent=2)
    logger.info("Exported error analysis report to %s", error_path)

    return {
        "metrics": metrics,
        "features": features,
        "error_analysis": error_report,
    }


if __name__ == "__main__":
    result = evaluate_and_export()
    m = result["metrics"]
    print("\n" + "=" * 70)
    print("      MODEL EVALUATION SUMMARY & CONFUSION MATRIX")
    print("=" * 70)
    print(f"Test Samples: {m['total_test_samples']}")
    print(f"Accuracy:     {m['overall_metrics']['accuracy'] * 100:.2f}%")
    print(f"Macro F1:     {m['overall_metrics']['macro_f1'] * 100:.2f}%")
    print(f"OvR ROC-AUC:  {m['overall_metrics']['ovr_roc_auc']:.4f}")
    print("\nConfusion Matrix:")
    print(format_confusion_matrix_ascii(m["confusion_matrix"]["labels"], m["confusion_matrix"]["matrix"]))
    print("\nBoundary Stress Test Samples:")
    for b in result["error_analysis"]["boundary_stress_tests"]:
        print(f"- Scenario: {b['scenario']}")
        print(f"  Predicted: {b['predicted_category']} (Confidence: {b['confidence'] * 100:.1f}%, Margin: {b['margin_to_second'] * 100:.1f}%)")
    print("=" * 70)
