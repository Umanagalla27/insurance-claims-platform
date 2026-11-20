"""
database/tests/test_schema_and_loader.py
========================================
Unit and integration tests for MySQL warehouse DDL and bulk loader.
Tests schema creation, bulk staging ingestion, and idempotency.
"""

from pathlib import Path

import pytest
from sqlalchemy import text

from database.loader import WarehouseLoader


@pytest.fixture
def test_loader(tmp_path: Path) -> WarehouseLoader:
    """Provides a WarehouseLoader connected to an isolated SQLite test database."""
    db_file = tmp_path / "test_warehouse.db"
    db_url = f"sqlite:///{db_file}"
    loader = WarehouseLoader(db_url=db_url)
    return loader


def test_schema_creation_and_tables(test_loader: WarehouseLoader):
    """Verify table creation and schema definitions."""
    with test_loader.engine.begin() as conn:
        conn.execute(
            text("""
            CREATE TABLE customers (
                customer_id VARCHAR(20) PRIMARY KEY,
                first_name VARCHAR(50) NOT NULL,
                last_name VARCHAR(50) NOT NULL,
                state VARCHAR(2) NOT NULL
            );
        """)
        )
        conn.execute(
            text("""
            CREATE TABLE policies (
                policy_id VARCHAR(20) PRIMARY KEY,
                customer_id VARCHAR(20) NOT NULL,
                status VARCHAR(20) NOT NULL
            );
        """)
        )
        conn.execute(
            text("""
            CREATE TABLE claims (
                claim_id VARCHAR(20) PRIMARY KEY,
                policy_id VARCHAR(20) NOT NULL,
                claim_amount DECIMAL(12, 2) NOT NULL
            );
        """)
        )

        # Verify tables exist
        tables = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table';")
        ).fetchall()
        table_names = [t[0] for t in tables]
        assert "customers" in table_names
        assert "policies" in table_names
        assert "claims" in table_names


def test_warehouse_bulk_loader_with_staging_files(test_loader: WarehouseLoader):
    """Verify loader ingests customers, policies, clean claims, and dead-letter quarantine."""
    summary = test_loader.load_all()

    assert summary["status"] == "SUCCESS"
    assert summary["customers_loaded"] == 515
    assert summary["policies_loaded"] == 800
    assert summary["claims_loaded"] == 9107
    assert summary["rejected_loaded"] == 1193

    # Query loaded counts directly from database
    with test_loader.engine.connect() as conn:
        c_count = conn.execute(text("SELECT COUNT(*) FROM customers")).scalar()
        p_count = conn.execute(text("SELECT COUNT(*) FROM policies")).scalar()
        cl_count = conn.execute(text("SELECT COUNT(*) FROM claims")).scalar()
        r_count = conn.execute(text("SELECT COUNT(*) FROM claims_rejected")).scalar()

        assert c_count == 515
        assert p_count == 800
        assert cl_count == 9107
        assert r_count == 1193


def test_loader_idempotency_repeat_run(test_loader: WarehouseLoader):
    """Verify executing load_all twice does not duplicate rows (idempotent loading)."""
    # First execution
    test_loader.load_all()

    # Second execution on same database
    second_summary = test_loader.load_all()
    assert second_summary["status"] == "SUCCESS"

    with test_loader.engine.connect() as conn:
        c_count = conn.execute(text("SELECT COUNT(*) FROM customers")).scalar()
        cl_count = conn.execute(text("SELECT COUNT(*) FROM claims")).scalar()

        # Counts must remain identical, proving no duplicate records were appended
        assert c_count == 515
        assert cl_count == 9107
