"""
database/tests/test_performance_and_views.py
============================================
Unit and integration tests for Star-Schema reporting views
and SQL performance tuning benchmark engine.
"""

from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from database.loader import WarehouseLoader
from database.performance.benchmark import run_benchmark


@pytest.fixture
def populated_db(tmp_path: Path) -> Engine:
    """Creates a populated test database from staging files with views created."""
    db_file = tmp_path / "views_test.db"
    db_url = f"sqlite:///{db_file}"
    loader = WarehouseLoader(db_url=db_url)
    loader.load_all()

    engine = create_engine(db_url)

    # SQLite compatible view creation
    with engine.begin() as conn:
        conn.execute(
            text("""
            CREATE VIEW IF NOT EXISTS vw_claims_analytics AS
            SELECT
                c.claim_id,
                c.policy_id,
                c.customer_id,
                (cust.first_name || ' ' || cust.last_name) AS customer_name,
                cust.state AS customer_state,
                cust.credit_score,
                p.policy_type,
                p.annual_premium,
                p.coverage_limit,
                c.claim_category,
                c.status AS claim_status,
                c.claim_amount,
                COALESCE(c.approved_amount, 0.0) AS approved_amount,
                c.incident_date,
                c.filing_date,
                c.is_fraud
            FROM claims c
            JOIN policies p ON c.policy_id = p.policy_id
            JOIN customers cust ON c.customer_id = cust.customer_id;
        """)
        )

        conn.execute(
            text("""
            CREATE VIEW IF NOT EXISTS vw_loss_ratio_by_state AS
            SELECT
                c.state,
                p.policy_type,
                COUNT(c.claim_id) AS total_claims_count,
                SUM(c.claim_amount) AS total_claimed_amount,
                SUM(COALESCE(c.approved_amount, 0.0)) AS total_paid_claims,
                SUM(p.annual_premium) AS total_earned_premium
            FROM claims c
            JOIN policies p ON c.policy_id = p.policy_id
            GROUP BY c.state, p.policy_type;
        """)
        )

        conn.execute(
            text("""
            CREATE VIEW IF NOT EXISTS vw_fraud_risk_summary AS
            SELECT
                claim_category,
                COUNT(claim_id) AS total_claims,
                SUM(CASE WHEN is_fraud = 1 THEN 1 ELSE 0 END) AS flagged_fraud_claims,
                SUM(CASE WHEN is_fraud = 1 THEN claim_amount ELSE 0.0 END) AS total_fraud_exposure_amount
            FROM claims
            GROUP BY claim_category;
        """)
        )

    return engine


def test_vw_claims_analytics_querying(populated_db: Engine):
    """Verify vw_claims_analytics returns complete dimensional star-schema records."""
    with populated_db.connect() as conn:
        rows = conn.execute(
            text("SELECT * FROM vw_claims_analytics LIMIT 50;")
        ).fetchall()
        assert len(rows) == 50
        first = rows[0]
        assert first.claim_id.startswith("CLM-")
        assert len(first.customer_name) > 3
        assert first.coverage_limit > 0


def test_vw_loss_ratio_by_state(populated_db: Engine):
    """Verify state loss ratio reporting view aggregates correctly."""
    with populated_db.connect() as conn:
        rows = conn.execute(text("SELECT * FROM vw_loss_ratio_by_state;")).fetchall()
        assert len(rows) > 0
        for r in rows:
            assert r.total_claims_count > 0
            assert r.total_claimed_amount > 0


def test_vw_fraud_risk_summary(populated_db: Engine):
    """Verify fraud risk analytical view aggregates fraud exposure."""
    with populated_db.connect() as conn:
        rows = conn.execute(text("SELECT * FROM vw_fraud_risk_summary;")).fetchall()
        # All 7 categories must be present
        assert len(rows) == 7
        total_fraud = sum(r.flagged_fraud_claims for r in rows)
        assert total_fraud > 0


def test_performance_benchmark_execution(tmp_path: Path):
    """Verify benchmark engine runs and records latency improvements."""
    db_file = tmp_path / "bm_test.db"
    report = run_benchmark(db_url=f"sqlite:///{db_file}", iterations=5)

    assert "baseline_unindexed" in report
    assert "optimized_covering_index" in report
    assert report["rows_scanned"] == 9107
    assert report["baseline_unindexed"]["avg_latency_ms"] > 0
    assert report["optimized_covering_index"]["avg_latency_ms"] > 0
