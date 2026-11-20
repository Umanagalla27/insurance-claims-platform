"""
Insurance Claims Intelligence Platform — Unsupervised Isolation Forest Anomaly Trainer
Component: ml/anomaly_detection/train.py

Trains an Isolation Forest ensemble on multidimensional claims risk features
to detect suspicious and fraudulent insurance claims without supervision.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler

from ml.anomaly_detection.features import FEATURE_NAMES, AnomalyFeatureExtractor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ml.anomaly_detection.train")

DEFAULT_ARTIFACT_DIR = Path("ml/artifacts")
MODEL_FILENAME = "isolation_forest_anomaly.joblib"
METRICS_FILENAME = "anomaly_metrics.json"


def train_anomaly_model(
    artifact_dir: Path = DEFAULT_ARTIFACT_DIR,
    n_estimators: int = 200,
    contamination: float = 0.048,
    random_state: int = 42,
) -> tuple[Pipeline, dict[str, Any]]:
    """Train Isolation Forest anomaly model and serialize pipeline artifact."""
    artifact_dir.mkdir(parents=True, exist_ok=True)

    extractor = AnomalyFeatureExtractor()
    X, y, _ = extractor.extract_training_features()

    logger.info("Extracted %d feature rows with %d dimensions: %s", len(X), len(FEATURE_NAMES), FEATURE_NAMES)

    pipeline = Pipeline(
        [
            ("scaler", RobustScaler()),
            (
                "model",
                IsolationForest(
                    n_estimators=n_estimators,
                    contamination=contamination,
                    random_state=random_state,
                    n_jobs=-1,
                ),
            ),
        ]
    )

    fit_start = time.perf_counter()
    pipeline.fit(X)
    fit_duration = time.perf_counter() - fit_start
    logger.info("Isolation Forest fitted in %.2f seconds", fit_duration)

    # Scikit-learn: decision_function returns negative for outliers, positive for inliers
    scaled_X = pipeline.named_steps["scaler"].transform(X)
    raw_scores = -pipeline.named_steps["model"].decision_function(scaled_X)
    raw_preds = pipeline.named_steps["model"].predict(scaled_X)
    y_pred = (raw_preds == -1).astype(int)

    # Calibration parameters for 0-100 Risk Score mapping
    score_p1 = float(np.percentile(raw_scores, 1))
    score_p99 = float(np.percentile(raw_scores, 99))

    # Evaluate against ground-truth fraud flags (unsupervised validation)
    roc_auc = float(roc_auc_score(y, raw_scores))
    conf_mat = confusion_matrix(y, y_pred).tolist()
    prec, rec, f1, _ = precision_recall_fscore_support(y, y_pred, average="binary", zero_division=0)
    clf_dict = classification_report(y, y_pred, output_dict=True, zero_division=0)

    logger.info("Unsupervised Anomaly Model Performance: ROC-AUC=%.4f, Precision=%.4f, Recall=%.4f, F1=%.4f",
                roc_auc, prec, rec, f1)

    metrics = {
        "model_name": "RobustScaler + IsolationForest",
        "trained_at": datetime.now(UTC).isoformat(),
        "total_samples": len(X),
        "ground_truth_anomalies": int(y.sum()),
        "predicted_anomalies": int(y_pred.sum()),
        "hyperparameters": {
            "n_estimators": n_estimators,
            "contamination": contamination,
            "random_state": random_state,
        },
        "score_calibration": {
            "score_min": score_p1,
            "score_max": score_p99,
        },
        "metrics": {
            "roc_auc": round(roc_auc, 4),
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "f1_score": round(float(f1), 4),
        },
        "confusion_matrix": conf_mat,
        "classification_report": clf_dict,
    }

    # Serialization payload
    payload = {
        "pipeline": pipeline,
        "feature_names": FEATURE_NAMES,
        "category_stats": extractor.category_stats.to_dict(),
        "score_calibration": metrics["score_calibration"],
        "metadata": metrics,
    }

    model_path = artifact_dir / MODEL_FILENAME
    metrics_path = artifact_dir / METRICS_FILENAME

    joblib.dump(payload, model_path, compress=3)
    logger.info("Saved serialized anomaly detector to %s (size: %.2f KB)",
                model_path, model_path.stat().st_size / 1024.0)

    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    logger.info("Saved anomaly evaluation metrics to %s", metrics_path)

    return pipeline, metrics


if __name__ == "__main__":
    train_anomaly_model()
