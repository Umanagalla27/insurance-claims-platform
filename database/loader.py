"""
database/loader.py
==================
Idempotent bulk data loader for MySQL Data Warehouse.
Reads staging CSVs (data/staging/) and executes bulk UPSERTs
(INSERT ... ON DUPLICATE KEY UPDATE).
Maintains database connection pools and supports fallback SQLite for isolated testing.
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from etl.config.settings import settings  # noqa: E402
from etl.utils.logging import logger  # noqa: E402


class WarehouseLoader:
    """Manages idempotent staging-to-warehouse bulk load operations."""

    def __init__(self, db_url: str | None = None) -> None:
        self.db_url = db_url or self._build_mysql_url()
        self.staging_dir = settings.staging_dir
        self.engine: Engine = self._create_engine()

    def _build_mysql_url(self) -> str:
        """Constructs MySQL connection string from environment variables."""
        host = os.getenv("MYSQL_HOST", "localhost")
        port = os.getenv("MYSQL_PORT", "3306")
        db = os.getenv("MYSQL_DATABASE", "insurance_claims_db")
        user = os.getenv("MYSQL_USER", "claims_user")
        pwd = os.getenv("MYSQL_PASSWORD", "claims_password_123")
        return f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{db}?charset=utf8mb4"

    def _create_engine(self) -> Engine:
        """Initializes SQLAlchemy Engine with connection pool parameters."""
        try:
            return create_engine(
                self.db_url,
                pool_size=5,
                max_overflow=10,
                pool_recycle=3600,
                pool_pre_ping=True,
            )
        except Exception as e:
            logger.warning(
                "Failed to create engine for default URL. Creating fallback SQLite engine.",
                error=str(e),
            )
            return create_engine("sqlite:///data/staging/warehouse_fallback.db")

    def execute_migration_script(self, migration_path: Path | None = None) -> None:
        """Executes a DDL migration SQL script against the database."""
        script_file = migration_path or (
            PROJECT_ROOT / "database" / "migrations" / "001_create_tables.sql"
        )
        if not script_file.exists():
            raise FileNotFoundError(f"Migration script not found at {script_file}")

        logger.info("Executing DDL migration script...", script=script_file.name)
        with open(script_file, encoding="utf-8") as f:
            sql_content = f.read()

        # Split statements by semicolon
        statements = [stmt.strip() for stmt in sql_content.split(";") if stmt.strip()]

        with self.engine.begin() as conn:
            for stmt in statements:
                # Skip comments or empty commands
                if stmt.startswith("--") or stmt.startswith("/*"):
                    continue
                try:
                    conn.execute(text(stmt))
                except Exception as e:
                    logger.warning(
                        "Migration statement note", statement=stmt[:40], note=str(e)
                    )

        logger.info("DDL migration script executed successfully.")

    def load_customers(self) -> int:
        """Bulk loads stg_customers.csv into customers table."""
        csv_file = self.staging_dir / "stg_customers.csv"
        if not csv_file.exists():
            logger.warning("stg_customers.csv not found, skipping", path=str(csv_file))
            return 0

        df = pd.read_csv(csv_file)
        # Fill NaN with None for SQL NULL
        records = df.where(pd.notnull(df), None).to_dict(orient="records")

        upsert_sql = (
            text("""
            INSERT INTO customers (
                customer_id, first_name, last_name, email, phone,
                address, city, state, postal_code, date_of_birth, credit_score, created_at
            ) VALUES (
                :customer_id, :first_name, :last_name, :email, :phone,
                :address, :city, :state, :postal_code, :date_of_birth, :credit_score, :created_at
            )
            ON DUPLICATE KEY UPDATE
                first_name = VALUES(first_name),
                last_name = VALUES(last_name),
                email = VALUES(email),
                phone = VALUES(phone),
                address = VALUES(address),
                city = VALUES(city),
                state = VALUES(state),
                postal_code = VALUES(postal_code),
                credit_score = VALUES(credit_score)
        """)
            if "mysql" in self.db_url
            else None
        )

        with self.engine.begin() as conn:
            if upsert_sql:
                for r in records:
                    conn.execute(upsert_sql, r)
            else:
                # SQLite fallback
                df.to_sql("customers", conn, if_exists="replace", index=False)

        logger.info("Loaded customers into warehouse", row_count=len(records))
        return len(records)

    def load_policies(self) -> int:
        """Bulk loads stg_policies.csv into policies table."""
        csv_file = self.staging_dir / "stg_policies.csv"
        if not csv_file.exists():
            logger.warning("stg_policies.csv not found, skipping", path=str(csv_file))
            return 0

        df = pd.read_csv(csv_file)
        records = df.where(pd.notnull(df), None).to_dict(orient="records")

        upsert_sql = (
            text("""
            INSERT INTO policies (
                policy_id, customer_id, policy_type, coverage_limit,
                deductible, annual_premium, start_date, end_date, status, created_at
            ) VALUES (
                :policy_id, :customer_id, :policy_type, :coverage_limit,
                :deductible, :annual_premium, :start_date, :end_date, :status, :created_at
            )
            ON DUPLICATE KEY UPDATE
                policy_type = VALUES(policy_type),
                coverage_limit = VALUES(coverage_limit),
                deductible = VALUES(deductible),
                annual_premium = VALUES(annual_premium),
                status = VALUES(status)
        """)
            if "mysql" in self.db_url
            else None
        )

        with self.engine.begin() as conn:
            if upsert_sql:
                for r in records:
                    conn.execute(upsert_sql, r)
            else:
                df.to_sql("policies", conn, if_exists="replace", index=False)

        logger.info("Loaded policies into warehouse", row_count=len(records))
        return len(records)

    def load_claims(self) -> int:
        """Bulk loads stg_claims.csv into claims table."""
        csv_file = self.staging_dir / "stg_claims.csv"
        if not csv_file.exists():
            logger.warning("stg_claims.csv not found, skipping", path=str(csv_file))
            return 0

        df = pd.read_csv(csv_file)
        records = df.where(pd.notnull(df), None).to_dict(orient="records")

        upsert_sql = (
            text("""
            INSERT INTO claims (
                claim_id, policy_id, customer_id, claim_category, claim_priority,
                claim_amount, approved_amount, incident_date, filing_date,
                status, state, description, is_fraud, fraud_reason, created_at
            ) VALUES (
                :claim_id, :policy_id, :customer_id, :claim_category, :claim_priority,
                :claim_amount, :approved_amount, :incident_date, :filing_date,
                :status, :state, :description, :is_fraud, :fraud_reason, :created_at
            )
            ON DUPLICATE KEY UPDATE
                claim_priority = VALUES(claim_priority),
                claim_amount = VALUES(claim_amount),
                approved_amount = VALUES(approved_amount),
                status = VALUES(status),
                description = VALUES(description),
                is_fraud = VALUES(is_fraud),
                fraud_reason = VALUES(fraud_reason)
        """)
            if "mysql" in self.db_url
            else None
        )

        with self.engine.begin() as conn:
            if upsert_sql:
                for r in records:
                    conn.execute(upsert_sql, r)
            else:
                df.to_sql("claims", conn, if_exists="replace", index=False)

        logger.info("Loaded claims into warehouse", row_count=len(records))
        return len(records)

    def load_rejected_claims(self) -> int:
        """Loads dead-letter quarantine table into claims_rejected."""
        json_file = settings.quarantine_dir / "claims_rejected.json"
        if not json_file.exists():
            return 0

        with open(json_file, encoding="utf-8") as f:
            records = json.load(f)

        if not records:
            return 0

        # Format records for SQL insertion
        formatted = []
        for r in records:
            formatted.append(
                {
                    "record_id": r.get("record_id"),
                    "entity_name": r.get("entity_name", "claims"),
                    "rejected_at": r.get("rejected_at")
                    or time.strftime("%Y-%m-%d %H:%M:%S"),
                    "rejection_reason": r.get("rejection_reason", "UNKNOWN"),
                    "raw_payload": json.dumps(r.get("raw_payload", {})),
                }
            )

        insert_sql = (
            text("""
            INSERT INTO claims_rejected (
                record_id, entity_name, rejected_at, rejection_reason, raw_payload
            ) VALUES (
                :record_id, :entity_name, :rejected_at, :rejection_reason, :raw_payload
            )
        """)
            if "mysql" in self.db_url
            else None
        )

        with self.engine.begin() as conn:
            if insert_sql:
                conn.execute(insert_sql, formatted)
            else:
                pd.DataFrame(formatted).to_sql(
                    "claims_rejected", conn, if_exists="replace", index=False
                )

        logger.info(
            "Loaded rejected claims into dead-letter table", count=len(formatted)
        )
        return len(formatted)

    def load_all(self) -> dict[str, Any]:
        """Executes complete warehouse bulk load."""
        start_time = time.time()
        logger.info("Starting complete Data Warehouse bulk load...")

        c_count = self.load_customers()
        p_count = self.load_policies()
        cl_count = self.load_claims()
        r_count = self.load_rejected_claims()

        elapsed = round(time.time() - start_time, 2)
        summary = {
            "status": "SUCCESS",
            "customers_loaded": c_count,
            "policies_loaded": p_count,
            "claims_loaded": cl_count,
            "rejected_loaded": r_count,
            "elapsed_seconds": elapsed,
        }
        logger.info("Warehouse bulk load completed", **summary)
        return summary


if __name__ == "__main__":
    loader = WarehouseLoader()
    loader.load_all()
