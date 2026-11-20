"""Model Governance, Versioning & Lifecycle Registry (ICIP-029).

Tracks lineage, training metrics, hyperparameters, Git commit SHAs,
and deployment stages (DEVELOPMENT, STAGING, PRODUCTION, ARCHIVED).
Persisted deterministically in JSON format.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_REGISTRY_PATH = PROJECT_ROOT / "ml" / "artifacts" / "model_registry.json"


class ModelStage(StrEnum):
    """Lifecycle stages for enterprise machine learning models."""

    DEVELOPMENT = "DEVELOPMENT"
    STAGING = "STAGING"
    PRODUCTION = "PRODUCTION"
    ARCHIVED = "ARCHIVED"


@dataclass
class StageTransition:
    """Record of a model promotion or demotion."""

    from_stage: str
    to_stage: str
    timestamp: str
    notes: str = ""


@dataclass
class ModelMetadata:
    """Governance record for an ML model version."""

    model_id: str
    name: str
    version: str
    model_type: str  # "classification", "anomaly_detection", "rag_retrieval"
    stage: ModelStage
    artifact_path: str
    trained_at: str
    git_commit: str
    metrics: dict[str, Any]
    hyperparameters: dict[str, Any]
    feature_names: list[str]
    description: str = ""
    transitions: list[StageTransition] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "name": self.name,
            "version": self.version,
            "model_type": self.model_type,
            "stage": self.stage.value,
            "artifact_path": self.artifact_path,
            "trained_at": self.trained_at,
            "git_commit": self.git_commit,
            "metrics": self.metrics,
            "hyperparameters": self.hyperparameters,
            "feature_names": self.feature_names,
            "description": self.description,
            "transitions": [asdict(t) for t in self.transitions],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelMetadata:
        transitions = [
            StageTransition(**t) for t in data.get("transitions", [])
        ]
        return cls(
            model_id=data["model_id"],
            name=data["name"],
            version=data["version"],
            model_type=data["model_type"],
            stage=ModelStage(data["stage"]),
            artifact_path=data["artifact_path"],
            trained_at=data["trained_at"],
            git_commit=data["git_commit"],
            metrics=data.get("metrics", {}),
            hyperparameters=data.get("hyperparameters", {}),
            feature_names=data.get("feature_names", []),
            description=data.get("description", ""),
            transitions=transitions,
        )


class ModelRegistry:
    """Central repository governing ML model artifacts, stages, and audits."""

    def __init__(self, registry_path: Path | str | None = None) -> None:
        self.registry_path = Path(registry_path or DEFAULT_REGISTRY_PATH)
        self.models: dict[str, ModelMetadata] = {}
        if self.registry_path.is_file():
            self.load()
        else:
            self._seed_production_models()
            self.save()

    def _seed_production_models(self) -> None:
        """Seed registry with currently deployed Sprint 4 production models."""
        now_iso = datetime.now(UTC).isoformat()

        # 1. Production NLP Text Classifier (TF-IDF + LogisticRegression)
        clf_meta = ModelMetadata(
            model_id="claim_classifier_v1",
            name="NLP Claim Domain Classifier",
            version="1.0.0",
            model_type="classification",
            stage=ModelStage.PRODUCTION,
            artifact_path="ml/artifacts/claim_classifier_tfidf_logreg.joblib",
            trained_at="2026-11-20T00:10:00Z",
            git_commit="e4b52ab",
            metrics={
                "accuracy": 1.0,
                "macro_f1": 1.0,
                "weighted_f1": 1.0,
                "p50_latency_ms": 1.18,
            },
            hyperparameters={
                "vectorizer": "TfidfVectorizer(max_features=5000, ngram_range=(1,2))",
                "classifier": "LogisticRegression(C=1.0, class_weight='balanced')",
            },
            feature_names=["claim_text_tfidf"],
            description="Production TF-IDF multi-class text categorization model for insurance claims.",
            transitions=[
                StageTransition(
                    from_stage=ModelStage.DEVELOPMENT.value,
                    to_stage=ModelStage.PRODUCTION.value,
                    timestamp=now_iso,
                    notes="Sprint 4 initial deployment to production",
                )
            ],
        )
        self.models[f"{clf_meta.name}@{clf_meta.version}"] = clf_meta

        # 2. Production Isolation Forest Anomaly Detector
        anom_meta = ModelMetadata(
            model_id="isolation_forest_anomaly_v1",
            name="Isolation Forest Fraud Anomaly Detector",
            version="1.0.0",
            model_type="anomaly_detection",
            stage=ModelStage.PRODUCTION,
            artifact_path="ml/artifacts/isolation_forest_anomaly.joblib",
            trained_at="2026-11-20T06:40:00Z",
            git_commit="89c1df3",
            metrics={
                "roc_auc": 0.8349,
                "precision": 0.4178,
                "recall": 0.4197,
                "f1_score": 0.4188,
                "accuracy": 0.9442,
            },
            hyperparameters={
                "n_estimators": 200,
                "contamination": 0.048,
                "random_state": 42,
            },
            feature_names=[
                "claim_amount",
                "days_to_file",
                "policy_tenure_days",
                "claim_to_coverage_ratio",
                "credit_score",
                "category_risk_weight",
                "weekend_incident",
                "round_amount_flag",
                "quick_filing_flag",
                "suspicious_timing_flag",
            ],
            description="Production unsupervised Isolation Forest for early insurance fraud risk scoring.",
            transitions=[
                StageTransition(
                    from_stage=ModelStage.DEVELOPMENT.value,
                    to_stage=ModelStage.PRODUCTION.value,
                    timestamp=now_iso,
                    notes="Sprint 4 initial deployment to production",
                )
            ],
        )
        self.models[f"{anom_meta.name}@{anom_meta.version}"] = anom_meta

    def register_model(self, metadata: ModelMetadata) -> ModelMetadata:
        """Register a new model version into the governance registry."""
        key = f"{metadata.name}@{metadata.version}"
        self.models[key] = metadata
        self.save()
        logger.info("Registered model %s into registry", key)
        return metadata

    def get_model(
        self, name: str, version: str | None = None
    ) -> ModelMetadata | None:
        """Retrieve model metadata by name and optional version."""
        if version:
            return self.models.get(f"{name}@{version}")

        # If version not specified, find production or latest version
        matches = [m for m in self.models.values() if m.name == name]
        prod_matches = [m for m in matches if m.stage == ModelStage.PRODUCTION]
        if prod_matches:
            return prod_matches[0]
        return matches[-1] if matches else None

    def get_production_model(self, name: str) -> ModelMetadata | None:
        """Retrieve the active PRODUCTION model metadata for a given model name."""
        matches = [
            m
            for m in self.models.values()
            if m.name == name and m.stage == ModelStage.PRODUCTION
        ]
        return matches[0] if matches else None

    def list_models(
        self, stage: ModelStage | None = None
    ) -> list[ModelMetadata]:
        """List all models in the registry, optionally filtered by lifecycle stage."""
        if stage is None:
            return list(self.models.values())
        return [m for m in self.models.values() if m.stage == stage]

    def transition_stage(
        self,
        name: str,
        version: str,
        new_stage: ModelStage,
        notes: str = "",
    ) -> ModelMetadata:
        """Promote or demote a model between lifecycle stages."""
        key = f"{name}@{version}"
        if key not in self.models:
            raise KeyError(f"Model {key} not found in registry")

        model = self.models[key]
        old_stage = model.stage

        # If promoting to PRODUCTION, archive existing production models of the same name
        if new_stage == ModelStage.PRODUCTION:
            for other in self.models.values():
                if (
                    other.name == name
                    and other.version != version
                    and other.stage == ModelStage.PRODUCTION
                ):
                    other.stage = ModelStage.ARCHIVED
                    other.transitions.append(
                        StageTransition(
                            from_stage=ModelStage.PRODUCTION.value,
                            to_stage=ModelStage.ARCHIVED.value,
                            timestamp=datetime.now(UTC).isoformat(),
                            notes=f"Auto-archived upon promotion of {version}",
                        )
                    )

        model.stage = new_stage
        model.transitions.append(
            StageTransition(
                from_stage=old_stage.value,
                to_stage=new_stage.value,
                timestamp=datetime.now(UTC).isoformat(),
                notes=notes,
            )
        )
        self.save()
        logger.info(
            "Model %s transitioned from %s to %s",
            key,
            old_stage.value,
            new_stage.value,
        )
        return model

    def save(self) -> None:
        """Persist registry state to disk."""
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "last_updated": datetime.now(UTC).isoformat(),
            "total_models": len(self.models),
            "models": {k: v.to_dict() for k, v in self.models.items()},
        }
        with open(self.registry_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    def load(self) -> None:
        """Load registry state from disk."""
        with open(self.registry_path, encoding="utf-8") as f:
            data = json.load(f)
        self.models = {
            k: ModelMetadata.from_dict(v)
            for k, v in data.get("models", {}).items()
        }


# Global singleton registry
model_registry = ModelRegistry()
