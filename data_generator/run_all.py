"""
data_generator/run_all.py
=========================
Coordinates generation of all datasets (customers, policies, claims).
Exports data to CSV (for data exploration / ETL) and JSON (for Mock API seed data).
"""

import json
import os
import sys
import time
from pathlib import Path

import pandas as pd

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_generator.generate_claims import generate_claims  # noqa: E402
from data_generator.generate_customers import generate_customers  # noqa: E402
from data_generator.generate_policies import generate_policies  # noqa: E402


def export_data(data: list, name: str, raw_dir: Path, mock_dir: Path) -> None:
    """Exports dataset to both CSV and JSON."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    mock_dir.mkdir(parents=True, exist_ok=True)

    csv_path = raw_dir / f"{name}.csv"
    json_path = mock_dir / f"{name}.json"

    # Export CSV via pandas
    df = pd.DataFrame(data)
    df.to_csv(csv_path, index=False)

    # Export JSON formatted cleanly
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    file_size_mb = os.path.getsize(csv_path) / (1024 * 1024)
    print(
        f"  [EXPORTED] {name:<12} -> {len(data):>6} records | {csv_path.name} ({file_size_mb:.2f} MB)"
    )


def main() -> None:
    print("\n" + "=" * 65)
    print("  Insurance Claims Intelligence Platform — Synthetic Data Generator")
    print("=" * 65 + "\n")

    start_time = time.time()

    raw_dir = PROJECT_ROOT / "data" / "raw"
    mock_dir = PROJECT_ROOT / "mock_api" / "data"

    print("Step 1/3: Generating Customers...")
    customers = generate_customers()
    export_data(customers, "customers", raw_dir, mock_dir)

    print("\nStep 2/3: Generating Policies...")
    # Extract unique customer IDs for policy mapping
    unique_cust_ids = list({c["customer_id"] for c in customers})
    policies = generate_policies(unique_cust_ids)
    export_data(policies, "policies", raw_dir, mock_dir)

    print("\nStep 3/3: Generating Claims with Messiness & Fraud Patterns...")
    claims = generate_claims(policies)
    export_data(claims, "claims", raw_dir, mock_dir)

    elapsed = time.time() - start_time
    print("\n" + "=" * 65)
    print(f"  All datasets generated successfully in {elapsed:.2f} seconds!")
    print(f"  Raw data location:      {raw_dir}")
    print(f"  Mock API seed location: {mock_dir}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
