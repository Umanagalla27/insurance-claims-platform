"""
data_generator/generate_policies.py
===================================
Generates synthetic insurance policies associated with existing customers.
Includes realistic coverage limits, deductibles, dates, and statuses.
"""

import random
from datetime import date, datetime, timedelta
from typing import Any

from faker import Faker

from data_generator.config import (
    NUM_POLICIES,
    POLICY_STATUS_WEIGHTS,
    POLICY_STATUSES,
    POLICY_TYPES,
    RANDOM_SEED,
)

fake = Faker("en_US")
Faker.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)

POLICY_COVERAGE_MAP = {
    "Comprehensive Auto": (25_000, 100_000, 500, 2_000),
    "Third-Party Auto": (15_000, 50_000, 250, 1_000),
    "Health": (50_000, 500_000, 500, 5_000),
    "Homeowner": (100_000, 1_000_000, 1_000, 5_000),
    "Renter": (10_000, 50_000, 250, 1_000),
    "Term Life": (100_000, 2_000_000, 0, 0),
    "Whole Life": (250_000, 3_000_000, 0, 0),
    "Travel": (5_000, 50_000, 100, 500),
    "Commercial Property": (200_000, 2_000_000, 2_500, 10_000),
    "Professional Liability": (500_000, 5_000_000, 5_000, 25_000),
}


def generate_policies(
    customer_ids: list[str], num_policies: int = NUM_POLICIES
) -> list[dict[str, Any]]:
    """
    Generate policy records mapped to a pool of customer IDs.
    """
    policies: list[dict[str, Any]] = []

    for i in range(1, num_policies + 1):
        policy_id = f"POL-{i:05d}"
        customer_id = random.choice(customer_ids)
        policy_type = random.choice(POLICY_TYPES)

        min_cov, max_cov, min_ded, max_ded = POLICY_COVERAGE_MAP[policy_type]
        coverage_limit = round(random.uniform(min_cov, max_cov), -3)
        deductible = round(random.uniform(min_ded, max_ded), -2) if max_ded > 0 else 0.0

        # Annual premium is typically 1% - 5% of coverage limit
        annual_premium = round(coverage_limit * random.uniform(0.012, 0.045), 2)

        # Policy start date between 3 years ago and 60 days in future
        start_days_ago = random.randint(-60, 3 * 365)
        start_dt = date.today() - timedelta(days=start_days_ago)
        # 1-year policy term
        end_dt = start_dt + timedelta(days=365)

        status = random.choices(POLICY_STATUSES, weights=POLICY_STATUS_WEIGHTS)[0]
        # Align status realistically with dates
        if end_dt < date.today() and status == "Active":
            status = "Expired"
        elif start_dt > date.today() and status == "Active":
            status = "Suspended"

        created_at = (
            datetime.combine(start_dt, datetime.min.time())
            - timedelta(days=random.randint(1, 14))
        ).isoformat()

        policy = {
            "policy_id": policy_id,
            "customer_id": customer_id,
            "policy_type": policy_type,
            "coverage_limit": float(coverage_limit),
            "deductible": float(deductible),
            "annual_premium": float(annual_premium),
            "start_date": start_dt.isoformat(),
            "end_date": end_dt.isoformat(),
            "status": status,
            "created_at": created_at,
        }
        policies.append(policy)

    return policies
