"""
data_generator/generate_customers.py
====================================
Generates synthetic insurance customers with realistic demographics,
geographical distribution, and controlled messiness.
"""

import random
from datetime import date, datetime, timedelta
from typing import Any

from faker import Faker

from data_generator.config import (
    DUPLICATE_RATE,
    MISSING_VALUE_RATE,
    NUM_CUSTOMERS,
    RANDOM_SEED,
    US_STATES,
)

# Seed for reproducible outputs
fake = Faker("en_US")
Faker.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)


def generate_customers(num_customers: int = NUM_CUSTOMERS) -> list[dict[str, Any]]:
    """
    Generate customer records with realistic personal data and controlled messiness.
    """
    customers: list[dict[str, Any]] = []

    for i in range(1, num_customers + 1):
        cust_id = f"CUST-{i:04d}"
        first_name = fake.first_name()
        last_name = fake.last_name()

        # 8% missing email or phone to simulate dirty CRM/legacy sources
        email = None if random.random() < MISSING_VALUE_RATE else fake.email()
        phone = None if random.random() < MISSING_VALUE_RATE else fake.phone_number()

        # Birth date between 18 and 80 years ago
        age_days = random.randint(18 * 365, 80 * 365)
        dob = (date.today() - timedelta(days=age_days)).isoformat()

        # Registration date between 5 years ago and today
        created_days_ago = random.randint(30, 5 * 365)
        created_at = (datetime.now() - timedelta(days=created_days_ago)).isoformat()

        # Credit score (300 - 850, roughly normal distribution around 680)
        credit_score = int(min(max(random.gauss(680, 70), 300), 850))

        state = random.choice(US_STATES)

        customer = {
            "customer_id": cust_id,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone,
            "address": fake.street_address(),
            "city": fake.city(),
            "state": state,
            "postal_code": fake.zipcode_in_state(state)
            if hasattr(fake, "zipcode_in_state")
            else fake.zipcode(),
            "date_of_birth": dob,
            "credit_score": credit_score,
            "created_at": created_at,
        }
        customers.append(customer)

    # Inject duplicate customers (~3%) to mimic duplicate entries in legacy core systems
    num_duplicates = int(num_customers * DUPLICATE_RATE)
    for _ in range(num_duplicates):
        idx = random.randint(0, len(customers) - 1)
        duplicate_record = dict(customers[idx])
        # Sometimes slight whitespace or case difference
        if random.random() < 0.5:
            duplicate_record["first_name"] = duplicate_record["first_name"].lower()
        customers.append(duplicate_record)

    return customers
