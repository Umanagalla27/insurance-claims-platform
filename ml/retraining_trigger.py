"""Automated Retraining Decision Engine & Candidate Staging Trigger (ICIP-029).

Analyzes statistical drift audit reports against enterprise governance policies.
Generates executive drift reports in Markdown and JSON, and automatically
stages retrained candidate model versions into the Model Registry.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ml.drift_detector import DriftAuditReport, DriftSeverity
from ml.model_registry.registry import (
    ModelMetadata,
    ModelRegistry,
    ModelStage,
    StageTransition,
    model_registry,
)

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "ml" / "reports"


class RetrainingPolicyEngine:
    """Evaluates statistical drift against enterprise governance thresholds."""

    def __init__(
        self,
        registry: ModelRegistry | None = None,
        reports_dir: Path | None = None,
    ) -> None:
        self.registry = registry or model_registry
        self.reports_dir = Path(reports_dir or REPORTS_DIR)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def evaluate_and_trigger(
        self,
        audit_report: DriftAuditReport,
        target_model_name: str = "NLP Claim Domain Classifier",
    ) -> dict[str, Any]:
        """Evaluate drift report, generate briefing documents, and trigger candidate staging."""
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        is_triggered = audit_report.retraining_recommended

        # 1. Generate and persist JSON drift report
        json_report_path = (
            self.reports_dir / f"drift_report_{timestamp}.json"
        )
        report_data = audit_report.to_dict()
        report_data["target_model_name"] = target_model_name
        report_data["retraining_triggered"] = is_triggered

        with open(json_report_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)

        # 2. Generate Human-Readable Markdown Report
        md_report_path = self.reports_dir / "drift_report.md"
        md_content = self._generate_markdown_report(audit_report, target_model_name, is_triggered)
        with open(md_report_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        # 3. Automated Candidate Staging in Model Registry
        candidate_meta: ModelMetadata | None = None
        if is_triggered:
            candidate_meta = self._stage_candidate_model(
                target_model_name=target_model_name,
                audit_report=audit_report,
                timestamp=timestamp,
            )

        return {
            "retraining_triggered": is_triggered,
            "json_report_path": str(json_report_path),
            "md_report_path": str(md_report_path),
            "critical_features": [
                f
                for f, r in audit_report.feature_results.items()
                if r.severity == DriftSeverity.CRITICAL
            ],
            "moderate_features": [
                f
                for f, r in audit_report.feature_results.items()
                if r.severity == DriftSeverity.MODERATE
            ],
            "staged_candidate_version": (
                candidate_meta.version if candidate_meta else None
            ),
        }

    def _stage_candidate_model(
        self,
        target_model_name: str,
        audit_report: DriftAuditReport,
        timestamp: str,
    ) -> ModelMetadata:
        """Stage a new candidate model in the registry under STAGING status."""
        current_prod = self.registry.get_model(target_model_name)
        base_ver = current_prod.version if current_prod else "1.0.0"

        # Calculate candidate version
        major, minor, *patch = base_ver.split(".")
        candidate_version = f"{major}.{int(minor) + 1}.0-candidate"

        now_iso = datetime.now(UTC).isoformat()
        reason = (
            f"Auto-triggered retraining candidate staged due to statistical drift: "
            f"{audit_report.critical_drift_count} critical, {audit_report.moderate_drift_count} moderate features"
        )

        candidate_meta = ModelMetadata(
            model_id=f"{target_model_name.lower().replace(' ', '_')}_{timestamp}",
            name=target_model_name,
            version=candidate_version,
            model_type=current_prod.model_type if current_prod else "classification",
            stage=ModelStage.STAGING,
            artifact_path=f"ml/artifacts/candidates/{candidate_version}.joblib",
            trained_at=now_iso,
            git_commit="auto-retrain-staged",
            metrics={
                "drift_trigger_timestamp": audit_report.audit_timestamp,
                "drifted_features": audit_report.drifted_features_count,
                "staging_status": "AWAITING_SHADOW_EVALUATION",
            },
            hyperparameters=current_prod.hyperparameters if current_prod else {},
            feature_names=current_prod.feature_names if current_prod else [],
            description=f"Auto-retrained candidate model triggered by MLOps governance drift detection ({timestamp})",
            transitions=[
                StageTransition(
                    from_stage=ModelStage.DEVELOPMENT.value,
                    to_stage=ModelStage.STAGING.value,
                    timestamp=now_iso,
                    notes=reason,
                )
            ],
        )

        self.registry.register_model(candidate_meta)
        logger.info(
            "Staged candidate model %s@%s in STAGING stage",
            target_model_name,
            candidate_version,
        )
        return candidate_meta

    def _generate_markdown_report(
        self,
        audit: DriftAuditReport,
        target_model: str,
        triggered: bool,
    ) -> str:
        """Build executive markdown drift report."""
        status_badge = (
            "**ACTION REQUIRED: Retraining Triggered**"
            if triggered
            else "**NORMAL: No Retraining Required**"
        )

        lines = [
            "# MLOps Governance: Statistical Data & Prediction Drift Report",
            f"**Evaluation Timestamp**: `{audit.audit_timestamp}`  ",
            f"**Target Model**: `{target_model}`  ",
            f"**Baseline Dataset**: `{audit.baseline_dataset_id}` | **Current Batch**: `{audit.current_dataset_id}`  ",
            f"**Overall Status**: {status_badge}\n",
            "---",
            "## 1. Executive Summary",
            f"- **Total Features Audited**: {audit.total_features_evaluated}",
            f"- **Drifted Features Count**: {audit.drifted_features_count}",
            f"- **Critical Drift (PSI >= 0.25)**: {audit.critical_drift_count}",
            f"- **Moderate Drift (0.10 <= PSI < 0.25)**: {audit.moderate_drift_count}",
            f"- **Retraining Policy Triggered**: `{'YES' if triggered else 'NO'}`\n",
            "## 2. Feature Drift Breakdown Table",
            "| Feature Name | Type | PSI Score | p-Value | Test Statistic | Test Name | Severity |",
            "|:---|:---:|:---:|:---:|:---:|:---|:---:|",
        ]

        for fname, res in sorted(audit.feature_results.items()):
            icon = (
                "CRITICAL"
                if res.severity == DriftSeverity.CRITICAL
                else ("MODERATE" if res.severity == DriftSeverity.MODERATE else "NONE")
            )
            lines.append(
                f"| `{fname}` | {res.feature_type} | {res.psi_score:.4f} | {res.p_value:.4e} | {res.test_statistic:.4f} | {res.test_name} | **{icon}** |"
            )

        lines.extend(
            [
                "\n## 3. Governance Policy Decision",
                "- **PSI < 0.10**: Distribution is stable. No model degradation expected.",
                "- **0.10 <= PSI < 0.25**: Moderate drift. System flags warning for monitoring.",
                "- **PSI >= 0.25**: Critical drift. Retraining decision engine immediately stages new candidate weights.",
                "",
                f"> **Automated Trigger Outcome**: `{'RETRAIN_TRIGGERED' if triggered else 'PASSED'}`",
            ]
        )
        return "\n".join(lines)


# Global singleton policy engine
policy_engine = RetrainingPolicyEngine()
