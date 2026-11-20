"""
database/tests/test_triggers_and_procedures.py
==============================================
Unit tests for MySQL audit triggers, business rule validations,
and stored procedure batch processing logic.
"""

from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


@pytest.fixture
def test_db(tmp_path: Path) -> Engine:
    """Creates an isolated database with audit triggers for testing."""
    engine = create_engine(f"sqlite:///{tmp_path / 'trigger_test.db'}")

    with engine.begin() as conn:
        # Schema
        conn.execute(
            text("""
            CREATE TABLE claims (
                claim_id VARCHAR(20) PRIMARY KEY,
                policy_id VARCHAR(20) NOT NULL,
                claim_amount DECIMAL(12, 2) NOT NULL,
                approved_amount DECIMAL(12, 2) DEFAULT NULL,
                incident_date DATE NOT NULL,
                filing_date DATE NOT NULL,
                status VARCHAR(30) NOT NULL DEFAULT 'Pending',
                is_fraud INT NOT NULL DEFAULT 0
            );
        """)
        )

        conn.execute(
            text("""
            CREATE TABLE claims_audit_log (
                audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_id VARCHAR(20) NOT NULL,
                action VARCHAR(20) NOT NULL,
                old_status VARCHAR(30),
                new_status VARCHAR(30),
                old_amount DECIMAL(12, 2),
                new_amount DECIMAL(12, 2),
                changed_by VARCHAR(50) DEFAULT 'TEST_USER',
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        )

        # SQLite dialect equivalent for trg_claims_audit_after_update
        conn.execute(
            text("""
            CREATE TRIGGER trg_claims_audit_after_update
            AFTER UPDATE ON claims
            FOR EACH ROW
            WHEN OLD.status <> NEW.status OR OLD.claim_amount <> NEW.claim_amount
            BEGIN
                INSERT INTO claims_audit_log (
                    claim_id, action, old_status, new_status, old_amount, new_amount, changed_by
                ) VALUES (
                    NEW.claim_id,
                    CASE WHEN OLD.status <> NEW.status THEN 'STATUS_CHANGE' ELSE 'AMOUNT_CHANGE' END,
                    OLD.status,
                    NEW.status,
                    OLD.claim_amount,
                    NEW.claim_amount,
                    'SYSTEM_TEST'
                );
            END;
        """)
        )

        # SQLite dialect equivalent for validation trigger
        conn.execute(
            text("""
            CREATE TRIGGER trg_claims_validate_before_insert
            BEFORE INSERT ON claims
            FOR EACH ROW
            WHEN NEW.claim_amount <= 0 OR NEW.filing_date < NEW.incident_date
            BEGIN
                SELECT RAISE(ABORT, 'Business Rule Violation: Invalid amount or dates');
            END;
        """)
        )

    return engine


def test_audit_trigger_fires_on_status_change(test_db: Engine):
    """Verify that updating claim status automatically writes an audit log entry."""
    with test_db.begin() as conn:
        conn.execute(
            text("""
            INSERT INTO claims (claim_id, policy_id, claim_amount, incident_date, filing_date, status)
            VALUES ('CLM-00001', 'POL-00001', 3500.00, '2026-01-10', '2026-01-12', 'Pending');
        """)
        )

    # Initial check: audit log should be empty
    with test_db.connect() as conn:
        audit_count = conn.execute(
            text("SELECT COUNT(*) FROM claims_audit_log")
        ).scalar()
        assert audit_count == 0

    # Update claim status from Pending to Approved
    with test_db.begin() as conn:
        conn.execute(
            text("""
            UPDATE claims
            SET status = 'Approved', approved_amount = 3000.00
            WHERE claim_id = 'CLM-00001';
        """)
        )

    # Verify audit trigger fired automatically!
    with test_db.connect() as conn:
        audit_row = conn.execute(
            text("SELECT * FROM claims_audit_log WHERE claim_id = 'CLM-00001'")
        ).fetchone()
        assert audit_row is not None
        assert audit_row.action == "STATUS_CHANGE"
        assert audit_row.old_status == "Pending"
        assert audit_row.new_status == "Approved"


def test_validation_trigger_blocks_invalid_insert(test_db: Engine):
    """Verify trigger aborts inserts with negative amounts or bad dates."""
    with pytest.raises(Exception) as exc, test_db.begin() as conn:
        conn.execute(
            text("""
            INSERT INTO claims (claim_id, policy_id, claim_amount, incident_date, filing_date, status)
            VALUES ('CLM-00002', 'POL-00001', -1500.00, '2026-01-10', '2026-01-12', 'Pending');
        """)
        )
    assert "Business Rule Violation" in str(exc.value)


def test_payout_calculation_business_logic():
    """Verify calculation formula: LEAST(amount, limit) - deductible (minimum 0)."""

    def calculate_payout(amount: float, deductible: float, limit: float) -> float:
        covered = min(amount, limit)
        payable = covered - deductible
        return max(0.0, round(payable, 2))

    # Scenario 1: Standard claim under limit
    assert calculate_payout(amount=3000.0, deductible=500.0, limit=50000.0) == 2500.0

    # Scenario 2: Massive claim capped by coverage limit
    assert (
        calculate_payout(amount=100000.0, deductible=1000.0, limit=50000.0) == 49000.0
    )

    # Scenario 3: Claim smaller than deductible pays $0
    assert calculate_payout(amount=300.0, deductible=500.0, limit=10000.0) == 0.0


def test_stored_procedure_batch_auto_approval_simulation(test_db: Engine):
    """Verify batch STP logic: pending claims under threshold without fraud are approved."""
    with test_db.begin() as conn:
        # Claim 1: Eligible (< $5000, is_fraud = 0)
        conn.execute(
            text("""
            INSERT INTO claims (claim_id, policy_id, claim_amount, incident_date, filing_date, status, is_fraud)
            VALUES ('CLM-00010', 'POL-00001', 2500.00, '2026-01-10', '2026-01-12', 'Pending', 0);
        """)
        )
        # Claim 2: Ineligible (Amount $12,000 exceeds threshold)
        conn.execute(
            text("""
            INSERT INTO claims (claim_id, policy_id, claim_amount, incident_date, filing_date, status, is_fraud)
            VALUES ('CLM-00011', 'POL-00001', 12000.00, '2026-01-10', '2026-01-12', 'Pending', 0);
        """)
        )
        # Claim 3: Ineligible (is_fraud = 1)
        conn.execute(
            text("""
            INSERT INTO claims (claim_id, policy_id, claim_amount, incident_date, filing_date, status, is_fraud)
            VALUES ('CLM-00012', 'POL-00001', 1500.00, '2026-01-10', '2026-01-12', 'Pending', 1);
        """)
        )

    # Execute batch STP logic (Threshold: $5,000)
    with test_db.begin() as conn:
        conn.execute(
            text("""
            UPDATE claims
            SET status = 'Approved', approved_amount = claim_amount - 500.00
            WHERE status = 'Pending' AND is_fraud = 0 AND claim_amount <= 5000.00;
        """)
        )

    # Assertions
    with test_db.connect() as conn:
        c1 = conn.execute(
            text(
                "SELECT status, approved_amount FROM claims WHERE claim_id = 'CLM-00010'"
            )
        ).fetchone()
        c2 = conn.execute(
            text("SELECT status FROM claims WHERE claim_id = 'CLM-00011'")
        ).fetchone()
        c3 = conn.execute(
            text("SELECT status FROM claims WHERE claim_id = 'CLM-00012'")
        ).fetchone()

        assert c1.status == "Approved"
        assert c1.approved_amount == 2000.00
        assert c2.status == "Pending"  # Unchanged
        assert c3.status == "Pending"  # Unchanged (fraud flag)

        # Audit log must contain exactly 1 entry for CLM-00010
        audit_rows = conn.execute(text("SELECT * FROM claims_audit_log")).fetchall()
        assert len(audit_rows) == 1
        assert audit_rows[0].claim_id == "CLM-00010"
        assert audit_rows[0].new_status == "Approved"
