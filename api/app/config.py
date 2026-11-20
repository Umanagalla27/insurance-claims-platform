"""Configuration settings for Insurance Claims Intelligence Platform API Gateway."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List


class Settings:
    """Application runtime settings driven by environment variables."""

    # Project Information
    PROJECT_NAME: str = "Insurance Claims Intelligence Platform - API Gateway"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    ENV: str = os.getenv("ENV", "development").lower()
    DEBUG: bool = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

    # Host & Port
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # CORS
    CORS_ORIGINS: List[str] = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "*").split(",")
        if origin.strip()
    ]

    # Project Directories
    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent

    # ML Artifact Paths
    CLASSIFIER_PATH: Path = (
        PROJECT_ROOT / "ml" / "artifacts" / "claim_classifier_tfidf_logreg.joblib"
    )
    ANOMALY_MODEL_PATH: Path = (
        PROJECT_ROOT / "ml" / "artifacts" / "isolation_forest_anomaly.joblib"
    )
    ANOMALY_STATS_PATH: Path = (
        PROJECT_ROOT / "ml" / "artifacts" / "category_stats.json"
    )

    # RAG / Vector Store Paths
    VECTOR_INDEX_DIR: Path = PROJECT_ROOT / "data" / "vector_store"
    CHUNKS_MANIFEST_PATH: Path = (
        PROJECT_ROOT / "rag_chatbot" / "data" / "chunks_manifest.json"
    )

    # Database Settings (MySQL Warehouse)
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "claims_app")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "SecureClaims2026!")
    DB_NAME: str = os.getenv("DB_NAME", "insurance_dw")


settings = Settings()
