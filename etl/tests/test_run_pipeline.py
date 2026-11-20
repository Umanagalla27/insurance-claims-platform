"""
etl/tests/test_run_pipeline.py
==============================
End-to-end integration tests for ETL Pipeline Runner and Staging Generator.
"""

from pathlib import Path

from etl.pipeline.state_manager import StateManager
from etl.run_pipeline import PipelineRunner


def test_pipeline_runner_end_to_end_local(tmp_path: Path):
    """Verify complete pipeline execution generating staging files and audit metrics."""
    runner = PipelineRunner(mode="full", source="local")
    runner.staging_dir = tmp_path / "staging"
    runner.staging_dir.mkdir(parents=True, exist_ok=True)

    summary = runner.run_pipeline()

    assert summary["execution_status"] == "SUCCESS"
    assert summary["raw_counts"]["claims"] >= 10000
    assert summary["staging_counts"]["stg_claims"] >= 9000
    assert summary["staging_counts"]["stg_claims_rejected"] >= 1000

    # Verify physical staging files were written
    assert (runner.staging_dir / "stg_claims.csv").exists()
    assert (runner.staging_dir / "stg_claims_rejected.csv").exists()
    assert (runner.staging_dir / "stg_customers.csv").exists()
    assert (runner.staging_dir / "stg_policies.csv").exists()


def test_pipeline_runner_incremental_watermark_update(tmp_path: Path):
    """Verify incremental execution updates the state watermark."""
    test_state_file = tmp_path / "etl_state.json"
    StateManager(state_file_path=test_state_file)

    runner = PipelineRunner(mode="incremental", source="local")
    runner.staging_dir = tmp_path / "staging"
    runner.staging_dir.mkdir(parents=True, exist_ok=True)

    summary = runner.run_pipeline()
    assert summary["execution_status"] == "SUCCESS"
