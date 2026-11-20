"""
data_generator/tests/test_generator.py
======================================
Unit tests for synthetic data generator.
"""

from data_generator.generate_claims import generate_claims
from data_generator.generate_customers import generate_customers
from data_generator.generate_policies import generate_policies


def test_customer_generation():
    customers = generate_customers(num_customers=50)
    assert len(customers) >= 50
    first = customers[0]
    assert "customer_id" in first
    assert "first_name" in first
    assert "last_name" in first


def test_policy_generation():
    cust_ids = ["CUST-0001", "CUST-0002", "CUST-0003"]
    policies = generate_policies(customer_ids=cust_ids, num_policies=30)
    assert len(policies) == 30
    first = policies[0]
    assert first["customer_id"] in cust_ids
    assert first["coverage_limit"] > 0
    assert first["annual_premium"] > 0


def test_claims_generation_and_integrity():
    cust_ids = ["CUST-0001"]
    policies = generate_policies(customer_ids=cust_ids, num_policies=5)
    claims = generate_claims(policies=policies, num_claims=100)
    assert len(claims) >= 100
    first = claims[0]
    assert "claim_id" in first
    assert "claim_category" in first
    assert "is_fraud" in first
