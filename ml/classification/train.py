"""
Insurance Claims Intelligence Platform — ML NLP Text Classification Baseline
Component: ml/classification/train.py

Trains a production baseline NLP classifier using TF-IDF + Balanced Logistic Regression
on staged insurance claim narratives. Serializes the fitted pipeline and evaluation metrics.
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
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from ml.classification.preprocess import clean_claim_text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ml.classification.train")

DEFAULT_STAGING_PATH = Path("data/staging/stg_claims.csv")
DEFAULT_ARTIFACT_DIR = Path("ml/artifacts")
MODEL_FILENAME = "claim_classifier_tfidf_logreg.joblib"
METRICS_FILENAME = "baseline_metrics.json"


def load_and_prepare_dataset(
    csv_path: Path,
) -> tuple[pd.Series, pd.Series, pd.DataFrame]:
    """Load staged claims CSV and filter out placeholder or empty narratives."""
    if not csv_path.exists():
        raise FileNotFoundError(f"Staged claims dataset not found at {csv_path}")

    logger.info("Loading staged claims from %s", csv_path)
    df = pd.read_csv(csv_path)
    total_records = len(df)

    # Pre-clean text narratives
    df["cleaned_narrative"] = df["description"].apply(clean_claim_text)

    # Filter out empty or placeholder rows
    valid_mask = df["cleaned_narrative"].str.strip() != ""
    valid_df = df[valid_mask].copy()

    logger.info(
        "Extracted %d valid narratives from %d total claims (filtered out %d placeholder claims)",
        len(valid_df),
        total_records,
        total_records - len(valid_df),
    )

    X = valid_df["description"]
    y = valid_df["claim_category"]
    return X, y, valid_df


def build_pipeline() -> Pipeline:
    """Construct an end-to-end scikit-learn Pipeline with custom text cleaner."""
    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    preprocessor=clean_claim_text,
                    ngram_range=(1, 2),
                    max_features=5000,
                    min_df=2,
                    sublinear_tf=True,
                ),
            ),
            (
                "classifier",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=1000,
                    random_state=42,
                    solver="lbfgs",
                ),
            ),
        ]
    )


def benchmark_inference_latency(
    pipeline: Pipeline,
    sample_texts: list[str],
    iterations: int = 500,
) -> dict[str, float]:
    """Benchmark inference latency (p50 and p95 in milliseconds)."""
    latencies_ms: list[float] = []
    num_samples = len(sample_texts)

    for i in range(iterations):
        sample = [sample_texts[i % num_samples]]
        start = time.perf_counter()
        _ = pipeline.predict(sample)
        latencies_ms.append((time.perf_counter() - start) * 1000.0)

    p50 = float(np.percentile(latencies_ms, 50))
    p95 = float(np.percentile(latencies_ms, 95))
    mean_lat = float(np.mean(latencies_ms))

    logger.info(
        "Inference Latency Benchmark (%d iterations): p50=%.3f ms, p95=%.3f ms, mean=%.3f ms",
        iterations,
        p50,
        p95,
        mean_lat,
    )
    return {
        "p50_ms": round(p50, 4),
        "p95_ms": round(p95, 4),
        "mean_ms": round(mean_lat, 4),
        "iterations": iterations,
    }


def train_model(
    staging_path: Path = DEFAULT_STAGING_PATH,
    artifact_dir: Path = DEFAULT_ARTIFACT_DIR,
    test_size: float = 0.20,
    random_state: int = 42,
) -> tuple[Pipeline, dict[str, Any]]:
    """Execute end-to-end model training, validation, and serialization."""
    artifact_dir.mkdir(parents=True, exist_ok=True)

    X, y, _ = load_and_prepare_dataset(staging_path)

    # Stratified 80/20 train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=y,
    )
    logger.info(
        "Dataset split: Train=%d, Test=%d (Stratified across %d classes)",
        len(X_train),
        len(X_test),
        y.nunique(),
    )

    # Build and fit pipeline
    pipeline = build_pipeline()
    train_start = time.perf_counter()
    pipeline.fit(X_train, y_train)
    train_duration = time.perf_counter() - train_start
    logger.info("Model pipeline fitted in %.2f seconds", train_duration)

    # Evaluate on test partition
    y_pred = pipeline.predict(X_test)
    pipeline.predict_proba(X_test)

    acc = float(accuracy_score(y_test, y_pred))
    prec_macro, rec_macro, f1_macro, _ = precision_recall_fscore_support(
        y_test, y_pred, average="macro", zero_division=0
    )
    prec_weighted, rec_weighted, f1_weighted, _ = precision_recall_fscore_support(
        y_test, y_pred, average="weighted", zero_division=0
    )

    classes = sorted(pipeline.classes_)
    conf_mat = confusion_matrix(y_test, y_pred, labels=classes).tolist()
    clf_report = classification_report(
        y_test, y_pred, output_dict=True, zero_division=0
    )

    # Latency benchmark
    sample_pool = X_test.tolist()[:50]
    latency_metrics = benchmark_inference_latency(pipeline, sample_pool, iterations=500)

    # Vocabulary insights
    vocab_size = len(pipeline.named_steps["tfidf"].vocabulary_)

    metrics = {
        "model_name": "TfidfVectorizer + LogisticRegression (Balanced)",
        "trained_at": datetime.now(UTC).isoformat(),
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "vocabulary_size": vocab_size,
        "classes": classes,
        "test_metrics": {
            "accuracy": round(acc, 4),
            "macro_precision": round(float(prec_macro), 4),
            "macro_recall": round(float(rec_macro), 4),
            "macro_f1": round(float(f1_macro), 4),
            "weighted_f1": round(float(f1_weighted), 4),
        },
        "latency_benchmark": latency_metrics,
        "classification_report": clf_report,
        "confusion_matrix": {
            "labels": classes,
            "matrix": conf_mat,
        },
    }

    # Serialize joblib artifact
    artifact_payload = {
        "pipeline": pipeline,
        "classes": classes,
        "metadata": {
            "trained_at": metrics["trained_at"],
            "accuracy": metrics["test_metrics"]["accuracy"],
            "macro_f1": metrics["test_metrics"]["macro_f1"],
            "vocabulary_size": vocab_size,
        },
    }

    model_path = artifact_dir / MODEL_FILENAME
    metrics_path = artifact_dir / METRICS_FILENAME

    joblib.dump(artifact_payload, model_path, compress=3)
    logger.info(
        "Saved serialized model artifact to %s (size: %.2f KB)",
        model_path,
        model_path.stat().st_size / 1024.0,
    )

    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    logger.info("Saved baseline evaluation report to %s", metrics_path)

    return pipeline, metrics


if __name__ == "__main__":
    trained_pipeline, eval_metrics = train_model()
    print("\n" + "=" * 60)
    print("  NLP BASELINE CLASSIFIER TRAINING COMPLETE")
    print("=" * 60)
    print(f"Artifact: {DEFAULT_ARTIFACT_DIR / MODEL_FILENAME}")
    print(f"Vocabulary: {eval_metrics['vocabulary_size']} features")
    print(f"Accuracy:   {eval_metrics['test_metrics']['accuracy'] * 100:.2f}%")
    print(f"Macro F1:   {eval_metrics['test_metrics']['macro_f1'] * 100:.2f}%")
    print(
        f"Latency:    p50={eval_metrics['latency_benchmark']['p50_ms']}ms, p95={eval_metrics['latency_benchmark']['p95_ms']}ms"
    )
    print("=" * 60)
