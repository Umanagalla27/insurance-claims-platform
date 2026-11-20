"""Service Container and Dependency Injection for FastAPI Gateway."""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, Optional
from fastapi import FastAPI, HTTPException, Request, status

from api.app.config import settings
from ml.anomaly_detection.predict import ClaimAnomalyDetector
from ml.classification.predict import ClaimClassifier
from rag_chatbot.retrieval.service import PolicyRetrievalService

logger = logging.getLogger(__name__)


class ServiceContainer:
    """Singleton container managing lifecycle of platform ML models and RAG retrieval services."""

    def __init__(self):
        self.classifier: Optional[ClaimClassifier] = None
        self.anomaly_detector: Optional[ClaimAnomalyDetector] = None
        self.retrieval_service: Optional[PolicyRetrievalService] = None
        self.startup_time: float = 0.0
        self.status_flags: Dict[str, bool] = {
            "classifier": False,
            "anomaly_detector": False,
            "retrieval_service": False,
        }

    def initialize(self) -> None:
        """Pre-load ML models and vector indexes into memory during application startup."""
        self.startup_time = time.time()
        logger.info("Initializing ServiceContainer and pre-loading models...")

        # 1. Text Classification Model
        try:
            if settings.CLASSIFIER_PATH.exists():
                self.classifier = ClaimClassifier(model_path=settings.CLASSIFIER_PATH)
                self.status_flags["classifier"] = True
                logger.info("Loaded ClaimClassifier from %s", settings.CLASSIFIER_PATH)
            else:
                logger.warning("ClaimClassifier artifact missing at %s", settings.CLASSIFIER_PATH)
        except Exception as e:
            logger.error("Failed to load ClaimClassifier: %s", e)

        # 2. Anomaly Detection Model
        try:
            if settings.ANOMALY_MODEL_PATH.exists():
                self.anomaly_detector = ClaimAnomalyDetector(model_path=settings.ANOMALY_MODEL_PATH)
                self.status_flags["anomaly_detector"] = True
                logger.info("Loaded ClaimAnomalyDetector from %s", settings.ANOMALY_MODEL_PATH)
            else:
                logger.warning("ClaimAnomalyDetector artifact missing at %s", settings.ANOMALY_MODEL_PATH)
        except Exception as e:
            logger.error("Failed to load ClaimAnomalyDetector: %s", e)

        # 3. RAG Hybrid Retrieval Service
        try:
            if settings.VECTOR_INDEX_DIR.exists() and settings.CHUNKS_MANIFEST_PATH.exists():
                self.retrieval_service = PolicyRetrievalService.from_artifacts(
                    index_dir=settings.VECTOR_INDEX_DIR,
                    manifest_path=settings.CHUNKS_MANIFEST_PATH,
                )
                self.status_flags["retrieval_service"] = True
                logger.info("Loaded PolicyRetrievalService from %s", settings.VECTOR_INDEX_DIR)
            else:
                logger.warning("RAG artifacts missing (index or manifest)")
        except Exception as e:
            logger.error("Failed to load PolicyRetrievalService: %s", e)

        logger.info("ServiceContainer initialization complete. Status: %s", self.status_flags)

    def shutdown(self) -> None:
        """Clean up resources on server shutdown."""
        logger.info("Shutting down ServiceContainer...")
        self.classifier = None
        self.anomaly_detector = None
        self.retrieval_service = None
        for k in self.status_flags:
            self.status_flags[k] = False


container = ServiceContainer()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """FastAPI lifespan context manager executing pre-load on startup and teardown on shutdown."""
    container.initialize()
    app.state.services = container
    yield
    container.shutdown()


def get_classifier(request: Request) -> ClaimClassifier:
    """Dependency injection provider for ClaimClassifier."""
    services: ServiceContainer = getattr(request.app.state, "services", container)
    if not services.classifier or not services.status_flags.get("classifier"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Claim classification model service is currently unavailable or uninitialized.",
        )
    return services.classifier


def get_anomaly_detector(request: Request) -> ClaimAnomalyDetector:
    """Dependency injection provider for ClaimAnomalyDetector."""
    services: ServiceContainer = getattr(request.app.state, "services", container)
    if not services.anomaly_detector or not services.status_flags.get("anomaly_detector"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Claim anomaly detection model service is currently unavailable or uninitialized.",
        )
    return services.anomaly_detector


def get_retrieval_service(request: Request) -> PolicyRetrievalService:
    """Dependency injection provider for PolicyRetrievalService."""
    services: ServiceContainer = getattr(request.app.state, "services", container)
    if not services.retrieval_service or not services.status_flags.get("retrieval_service"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Policy RAG retrieval service is currently unavailable or uninitialized.",
        )
    return services.retrieval_service
