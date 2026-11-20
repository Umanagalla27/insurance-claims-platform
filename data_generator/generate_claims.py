"""
data_generator/generate_claims.py
=================================
Generates 10,000 synthetic insurance claims with rich text narratives,
realistic amounts, intentional messiness, and fraud indicators.
"""

import random
from datetime import date, datetime, timedelta
from typing import Any

from faker import Faker

from data_generator.config import (
    AMOUNT_RANGES,
    CATEGORY_WEIGHTS,
    CLAIM_CATEGORIES,
    CLAIM_PRIORITIES,
    CLAIM_STATUSES,
    DESCRIPTION_TEMPLATES,
    DUPLICATE_RATE,
    FRAUD_RATE,
    MISSING_VALUE_RATE,
    NUM_CLAIMS,
    PRIORITY_WEIGHTS,
    RANDOM_SEED,
    STATUS_WEIGHTS,
    TEMPLATE_FILLERS,
    US_STATES,
    WRONG_AMOUNT_RATE,
    WRONG_DATE_FORMAT_RATE,
)

fake = Faker("en_US")
Faker.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)


def _render_description(category: str, date_str: str, amount: int) -> str:
    """Generate a realistic domain-specific narrative using templates."""
    templates = DESCRIPTION_TEMPLATES.get(category, DESCRIPTION_TEMPLATES["Auto"])
    template = random.choice(templates)

    # Build context dictionary filling all possible placeholders
    context = {
        "date": date_str,
        "amount": max(amount, 100),
        "year": random.randint(2015, 2024),
        "make": random.choice(TEMPLATE_FILLERS["make"]),
        "model": "Sedan" if random.random() < 0.5 else "SUV",
        "collision_type": random.choice(TEMPLATE_FILLERS["collision_type"]),
        "location": f"{fake.street_name()} and {fake.street_name()}",
        "damage_part": random.choice(TEMPLATE_FILLERS["damage_part"]),
        "damage_level": random.choice(TEMPLATE_FILLERS["damage_level"]),
        "weather": random.choice(TEMPLATE_FILLERS["weather"]),
        "fault_detail": random.choice(TEMPLATE_FILLERS["fault_detail"]),
        "collision_party": random.choice(TEMPLATE_FILLERS["collision_party"]),
        "injury_detail": "No injuries were sustained."
        if random.random() < 0.7
        else "Minor driver injuries reported.",
        "garage": random.choice(TEMPLATE_FILLERS["garage"]),
        "vandalism_type": random.choice(TEMPLATE_FILLERS["vandalism_type"]),
        "footage_detail": random.choice(TEMPLATE_FILLERS["footage_detail"]),
        "extra_claim": random.choice(TEMPLATE_FILLERS["extra_claim"]),
        "medical_detail": "Conducted on site by paramedics.",
        "report_num": f"PR-{random.randint(100000, 999999)}",
        "hospital": random.choice(TEMPLATE_FILLERS["hospital"]),
        "diagnosis": random.choice(TEMPLATE_FILLERS["diagnosis"]),
        "treatment": random.choice(TEMPLATE_FILLERS["treatment"]),
        "days": random.randint(1, 14),
        "doctor": fake.last_name(),
        "auth_num": f"AUTH-{random.randint(10000, 99999)}",
        "discharge_date": (
            date.today() - timedelta(days=random.randint(1, 30))
        ).isoformat(),
        "incident": "workplace accident"
        if random.random() < 0.5
        else "acute health episode",
        "pharmacy": random.choice(TEMPLATE_FILLERS["pharmacy"]),
        "address": fake.street_address(),
        "cause": random.choice(TEMPLATE_FILLERS["cause"]),
        "rooms": random.choice(TEMPLATE_FILLERS["rooms"]),
        "structural": random.choice(TEMPLATE_FILLERS["structural"]),
        "emergency": random.randint(500, 5000),
        "response": random.randint(4, 18),
        "structure": random.choice(TEMPLATE_FILLERS["structure"]),
        "personal": random.randint(1000, 20000),
        "depth": random.randint(2, 36),
        "items": random.choice(TEMPLATE_FILLERS["items"]),
        "entry": random.choice(TEMPLATE_FILLERS["entry"]),
        "security_detail": random.choice(TEMPLATE_FILLERS["security_detail"]),
        "claimant": random.choice(TEMPLATE_FILLERS["claimant"]),
        "allegation": random.choice(TEMPLATE_FILLERS["allegation"]),
        "injuries": random.choice(TEMPLATE_FILLERS["injuries"]),
        "medical": random.randint(2000, 25000),
        "wage_loss": random.randint(2500, 8000),
        "months": random.randint(1, 6),
        "maintenance_detail": "Inspection log verified within 30 days.",
        "witness_detail": "Two bystander accounts documented in incident log.",
        "product": random.choice(TEMPLATE_FILLERS["product"]),
        "recall": random.choice(TEMPLATE_FILLERS["recall"]),
        "destination": random.choice(TEMPLATE_FILLERS["destination"]),
        "cancel_reason": random.choice(TEMPLATE_FILLERS["cancel_reason"]),
        "flight": random.randint(400, 3000),
        "hotel": random.randint(500, 4500),
        "tour": random.randint(200, 2000),
        "flight_num": f"FL-{random.randint(100, 999)}",
        "bags": random.randint(1, 3),
        "airline_ref": f"BAG-{random.randint(10000, 99999)}",
        "airline_comp": random.choice([0, 250, 500]),
        "local": random.randint(800, 6000),
        "evac": random.randint(5000, 25000),
        "family": random.randint(1000, 4000),
        "insured": fake.name(),
        "weeks": random.randint(2, 26),
        "salary": random.randint(4000, 15000),
        "benefit_pct": 60,
        "return_date": (
            date.today() + timedelta(days=random.randint(15, 90))
        ).isoformat(),
        "prognosis": random.choice(TEMPLATE_FILLERS["prognosis"]),
        "occupation": random.choice(TEMPLATE_FILLERS["occupation"]),
        "onset_date": (
            date.today() - timedelta(days=random.randint(30, 180))
        ).isoformat(),
        "beneficiary": fake.name(),
        "relationship": random.choice(TEMPLATE_FILLERS["relationship"]),
        "payment_method": random.choice(TEMPLATE_FILLERS["payment_method"]),
        "base": max(amount - 50000, 25000),
        "add": 50000,
    }

    try:
        return template.format(**context)
    except KeyError:
        return f"Insurance claim filed for {category} incident on {date_str}. Total estimated loss ${amount:,}."


def generate_claims(
    policies: list[dict[str, Any]], num_claims: int = NUM_CLAIMS
) -> list[dict[str, Any]]:
    """
    Generates realistic claims with messiness and intentional fraud patterns.
    """
    claims: list[dict[str, Any]] = []

    # Map policy_id -> policy dict for fast lookup
    policy_map = {p["policy_id"]: p for p in policies}
    policy_ids = list(policy_map.keys())

    for i in range(1, num_claims + 1):
        claim_id = f"CLM-{i:05d}"
        policy_id = random.choice(policy_ids)
        policy = policy_map[policy_id]
        customer_id = policy["customer_id"]

        category = random.choices(CLAIM_CATEGORIES, weights=CATEGORY_WEIGHTS)[0]
        priority = random.choices(CLAIM_PRIORITIES, weights=PRIORITY_WEIGHTS)[0]
        status = random.choices(CLAIM_STATUSES, weights=STATUS_WEIGHTS)[0]

        # Calculate dates
        # Incident occurred in the last 2 years
        incident_days_ago = random.randint(5, 730)
        incident_dt = date.today() - timedelta(days=incident_days_ago)
        # Filing happens 0 to 45 days after incident
        filing_delay = random.randint(0, 45)
        filing_dt = incident_dt + timedelta(days=filing_delay)

        # Standard amount calculation
        min_amt, max_amt, _ = AMOUNT_RANGES[category]
        base_amt = round(random.uniform(min_amt, max_amt), 2)

        # Fraud injection (~5%)
        is_fraud = 1 if random.random() < FRAUD_RATE else 0
        fraud_reason = None

        if is_fraud:
            fraud_type = random.choice(
                [
                    "early_filing",  # Claim within 3 days of policy start
                    "exceeds_coverage",  # Claim amount far exceeds policy limit
                    "round_number",  # Unnaturally round high number
                    "excessive_amount",  # Massive outlier amount
                ]
            )
            if fraud_type == "early_filing":
                policy_start = date.fromisoformat(policy["start_date"])
                incident_dt = policy_start + timedelta(days=random.randint(0, 3))
                filing_dt = incident_dt + timedelta(days=1)
                fraud_reason = "Claim filed immediately after policy inception"
            elif fraud_type == "exceeds_coverage":
                base_amt = policy["coverage_limit"] * random.uniform(1.4, 2.5)
                fraud_reason = "Claim amount exceeds policy coverage limit"
            elif fraud_type == "round_number":
                base_amt = float(random.choice([25000, 50000, 75000, 100000, 250000]))
                fraud_reason = "Suspiciously round figure claim amount"
            elif fraud_type == "excessive_amount":
                base_amt = max_amt * random.uniform(1.8, 3.5)
                fraud_reason = "Statistical anomaly: extreme claim amount"

        claim_amount = round(base_amt, 2)

        # Approved amount based on status
        if status in ["Approved", "Closed"]:
            # Pay between 75% and 100% of claimed amount (deductible subtraction)
            deductible = policy.get("deductible", 500.0)
            approved_amount = max(
                0.0, round(claim_amount * random.uniform(0.80, 1.0) - deductible, 2)
            )
        elif status == "Rejected":
            approved_amount = 0.0
        else:
            approved_amount = None

        # Render realistic claim narrative
        description = _render_description(
            category, incident_dt.isoformat(), int(claim_amount)
        )

        state = random.choice(US_STATES)

        # ── Introduce Messiness ──
        # 1. Date formatting variation: ~2% wrong date format (MM/DD/YYYY)
        incident_date_str = incident_dt.isoformat()
        filing_date_str = filing_dt.isoformat()
        if random.random() < WRONG_DATE_FORMAT_RATE:
            incident_date_str = incident_dt.strftime("%m/%d/%Y")

        # 2. Negative or zero amount error (~1%)
        if random.random() < WRONG_AMOUNT_RATE:
            claim_amount = -abs(claim_amount) if random.random() < 0.6 else 0.0

        # 3. Missing values (~8% across nullable fields)
        if random.random() < MISSING_VALUE_RATE:
            description = None if random.random() < 0.5 else ""
        if random.random() < MISSING_VALUE_RATE:
            state = None

        claim = {
            "claim_id": claim_id,
            "policy_id": policy_id,
            "customer_id": customer_id,
            "claim_category": category,
            "claim_priority": priority,
            "claim_amount": claim_amount,
            "approved_amount": approved_amount,
            "incident_date": incident_date_str,
            "filing_date": filing_date_str,
            "status": status,
            "state": state,
            "description": description,
            "is_fraud": is_fraud,
            "fraud_reason": fraud_reason,
            "created_at": datetime.combine(filing_dt, datetime.min.time()).isoformat(),
        }
        claims.append(claim)

    # Inject duplicate records (~3%)
    num_duplicates = int(num_claims * DUPLICATE_RATE)
    for _ in range(num_duplicates):
        idx = random.randint(0, len(claims) - 1)
        duplicate_record = dict(claims[idx])
        claims.append(duplicate_record)

    return claims
