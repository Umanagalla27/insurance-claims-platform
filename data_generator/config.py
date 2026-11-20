"""
data_generator/config.py
========================
Shared configuration, constants, and templates for all generators.
Keeping config centralized means changing one value updates all generators.

In a real company: these categories/statuses would come from the
client's data dictionary (a document listing all valid field values).
"""

# ── Reproducibility ────────────────────────────────────────────────────────
# CRITICAL: same seed = same data every run.
# Change this only if you deliberately want a different dataset.
RANDOM_SEED = 42

# ── Scale ──────────────────────────────────────────────────────────────────
NUM_CUSTOMERS = 500
NUM_POLICIES = 800  # More policies than customers: some customers have 2+
NUM_CLAIMS = 10_000  # 10k claims against those 800 policies

# ── Domain Values ──────────────────────────────────────────────────────────

CLAIM_CATEGORIES = [
    "Auto",  # Vehicle accidents, damage
    "Medical",  # Illness, injury, hospitalization
    "Property",  # Home/commercial property damage
    "Liability",  # Third-party injury/damage claims
    "Travel",  # Trip cancellation, lost luggage
    "Disability",  # Inability to work claims
    "Life",  # Beneficiary death claims
]

# Realistic distribution: Auto and Medical are most common in real insurance
CATEGORY_WEIGHTS = [0.30, 0.25, 0.20, 0.10, 0.07, 0.05, 0.03]

CLAIM_PRIORITIES = ["Low", "Medium", "High"]

# Priority weights: most claims are Medium
PRIORITY_WEIGHTS = [0.40, 0.45, 0.15]

CLAIM_STATUSES = ["Pending", "Under Review", "Approved", "Rejected", "Closed"]

# Most real claims end up Approved or Closed
STATUS_WEIGHTS = [0.15, 0.20, 0.35, 0.10, 0.20]

POLICY_TYPES = [
    "Comprehensive Auto",
    "Third-Party Auto",
    "Health",
    "Homeowner",
    "Renter",
    "Term Life",
    "Whole Life",
    "Travel",
    "Commercial Property",
    "Professional Liability",
]

POLICY_STATUSES = ["Active", "Expired", "Cancelled", "Suspended"]
POLICY_STATUS_WEIGHTS = [0.70, 0.15, 0.10, 0.05]

US_STATES = [
    "CA",
    "TX",
    "FL",
    "NY",
    "PA",
    "IL",
    "OH",
    "GA",
    "NC",
    "MI",
    "NJ",
    "VA",
    "WA",
    "AZ",
    "MA",
    "TN",
    "IN",
    "MO",
    "MD",
    "WI",
]

# ── Messiness Parameters ───────────────────────────────────────────────────
# These match what real insurance data looks like from legacy systems.

MISSING_VALUE_RATE = 0.08  # 8% chance a nullable field is missing
DUPLICATE_RATE = 0.03  # 3% of claims will be duplicated
WRONG_DATE_FORMAT_RATE = 0.02  # 2% dates will be in MM/DD/YYYY instead of ISO
WRONG_AMOUNT_RATE = 0.01  # 1% amounts will be negative (data entry error)
FRAUD_RATE = 0.05  # 5% claims have suspicious/fraudulent patterns

# ── Amount Ranges by Category ──────────────────────────────────────────────
# (min_claimed, max_claimed, typical_coverage)
AMOUNT_RANGES = {
    "Auto": (500, 85_000, 50_000),
    "Medical": (200, 250_000, 200_000),
    "Property": (1_000, 500_000, 350_000),
    "Liability": (5_000, 300_000, 250_000),
    "Travel": (100, 15_000, 10_000),
    "Disability": (1_000, 60_000, 50_000),
    "Life": (50_000, 2_000_000, 1_500_000),
}

# ── Claim Description Templates ────────────────────────────────────────────
# These mimic real claim narratives. The ML model (Sprint 4) will learn
# to classify new descriptions into these categories using these patterns.
# Each template has {placeholders} filled in by the generator.

DESCRIPTION_TEMPLATES = {
    "Auto": [
        "On {date}, the insured vehicle, a {year} {make} {model}, was involved in a "
        "{collision_type} at {location}. The {damage_part} sustained {damage_level} "
        "damage. {weather} conditions at the time. The other party {fault_detail}. "
        "Estimated repair cost is ${amount:,}. Police report #{report_num} filed.",
        "Vehicle accident reported on {date}. Insured {make} {model} collided with "
        "{collision_party} resulting in {damage_level} damage to the {damage_part}. "
        "{injury_detail} The vehicle was towed to {garage}. Total estimated damage: "
        "${amount:,}. No DUI involved.",
        "The insured's {year} {make} was {vandalism_type} while parked at {location} "
        "on {date}. Damage includes {damage_part}. Security footage {footage_detail}. "
        "Local police report filed. Requesting coverage for repair and {extra_claim}.",
        "Multi-vehicle collision on {date} at {location}. Insured vehicle rear-ended "
        "by {collision_party}. Airbags deployed. {damage_level} front-end damage to "
        "{make} {model}. Medical evaluation {medical_detail}. Witness statements "
        "collected. Repair estimate from {garage}: ${amount:,}.",
    ],
    "Medical": [
        "Insured was hospitalized at {hospital} on {date} for {diagnosis}. Treatment "
        "included {treatment}. Duration of stay: {days} days. Attending physician: "
        "Dr. {doctor}. Total billed amount: ${amount:,}. Pre-authorization reference: "
        "{auth_num}. Discharge date: {discharge_date}.",
        "Emergency medical treatment required on {date} following {incident}. Patient "
        "transported to {hospital} by ambulance. Diagnosis: {diagnosis}. Procedures "
        "performed: {treatment}. ICU stay: {days} days. Total charges including "
        "medication, lab tests, and physician fees: ${amount:,}.",
        "Outpatient surgery performed on {date} at {hospital}. Procedure: {treatment} "
        "for {diagnosis}. Surgeon: Dr. {doctor}. Anesthesia administered. Recovery "
        "room charges included. Post-operative medications prescribed. Total claim "
        "amount: ${amount:,}. Expected recovery: {days} weeks.",
        "Prescription medication claim for {diagnosis}. Monthly supply of {treatment} "
        "as prescribed by Dr. {doctor}. Pharmacy: {pharmacy}. Medication not available "
        "as generic. Prior authorization obtained on {date}. Monthly cost: ${amount:,}. "
        "Chronic condition management plan in place.",
    ],
    "Property": [
        "Property located at {address} sustained {damage_level} damage due to {cause} "
        "on {date}. Affected areas include {rooms}. Structural integrity {structural}. "
        "Emergency repairs costing ${emergency:,} already undertaken to prevent further "
        "damage. Full repair estimate from licensed contractor: ${amount:,}.",
        "Fire incident at {address} on {date} caused by {cause}. Fire department "
        "responded within {response} minutes. {rooms} extensively damaged. Smoke and "
        "water damage throughout the {structure}. Personal property loss estimated at "
        "${personal:,}. Structural repair: ${amount:,}. Temporary accommodation "
        "required for {days} days.",
        "Flood damage reported at {address} following {cause} on {date}. Water level "
        "reached {depth} inches inside the property. {rooms} affected. Mold remediation "
        "required. Appliances and flooring completely destroyed. Contractor assessment: "
        "${amount:,}. Homeowner displaced for estimated {days} weeks.",
        "Burglary and theft at {address} on {date}. Items stolen include {items}. "
        "Point of entry: {entry}. Security system {security_detail}. Police report "
        "filed, case number {report_num}. Replacement value of stolen items: "
        "${amount:,}. No physical damage to structure beyond {damage_part}.",
    ],
    "Liability": [
        "Third-party claim filed by {claimant} following {incident} on {date} at "
        "{location}. Claimant alleges {allegation}. Injuries reported: {injuries}. "
        "Medical expenses incurred: ${medical:,}. Claimant also seeking compensation "
        "for lost wages (${wage_loss:,}/month for {months} months). Total claimed: "
        "${amount:,}. Legal representation retained by claimant.",
        "Slip and fall incident at {location} on {date}. {claimant} sustained {injuries} "
        "and alleges {allegation}. Medical treatment at {hospital}. Insured's property "
        "records show {maintenance_detail}. Witness accounts {witness_detail}. "
        "Total damages sought: ${amount:,} including pain and suffering.",
        "Product liability claim. Claimant {claimant} alleges injury caused by "
        "{product} purchased on {date}. Injury description: {injuries}. Medical "
        "records attached. Product recall status: {recall}. Legal notice received. "
        "Potential class action involvement. Estimated exposure: ${amount:,}.",
    ],
    "Travel": [
        "Trip cancellation claim for travel scheduled on {date} to {destination}. "
        "Reason for cancellation: {cancel_reason}. Non-refundable bookings include "
        "flight (${flight:,}), hotel (${hotel:,}), and tour packages (${tour:,}). "
        "Medical documentation attached where applicable. Total claimed: ${amount:,}.",
        "Lost baggage claim for flight {flight_num} on {date}. {bags} bags checked, "
        "none received at {destination}. Airline reference: {airline_ref}. Contents "
        "valued at ${amount:,} including {items}. Delay inconvenience: {days} days "
        "without luggage. Airline compensation already received: ${airline_comp:,}.",
        "Medical emergency during international travel to {destination} on {date}. "
        "Hospitalized at {hospital} for {days} days. Diagnosis: {diagnosis}. Local "
        "medical costs: ${local:,}. Emergency evacuation: ${evac:,}. Family travel "
        "expenses: ${family:,}. Total claim: ${amount:,}.",
    ],
    "Disability": [
        "Short-term disability claim for {insured} effective {date}. Medical condition: "
        "{diagnosis}. Attending physician: Dr. {doctor} at {hospital}. Estimated "
        "recovery period: {weeks} weeks. Current monthly salary: ${salary:,}. "
        "Benefit amount requested: {benefit_pct}% of salary = ${amount:,}/month. "
        "Return to work date estimated: {return_date}.",
        "Long-term disability claim filed on {date}. Diagnosis: {diagnosis}. "
        "Multiple specialist consultations confirm {prognosis}. {insured} has been "
        "unable to perform occupational duties as {occupation} since {onset_date}. "
        "Monthly benefit: ${amount:,}. Employer sick leave exhausted. Social Security "
        "disability application pending.",
    ],
    "Life": [
        "Death benefit claim filed by beneficiary {beneficiary} following the passing "
        "of insured {insured} on {date}. Cause of death: {cause}. Death certificate "
        "and policy documents attached. Policy face value: ${amount:,}. No "
        "contestability period applicable. Beneficiary relationship: {relationship}. "
        "Payment requested via {payment_method}.",
        "Accidental death benefit claim. Insured {insured} died on {date} due to "
        "{cause}. Coroner report and police report attached. Policy includes double "
        "indemnity for accidental death. Base benefit: ${base:,}. Additional "
        "accidental death benefit: ${add:,}. Total claim: ${amount:,}. Beneficiary: "
        "{beneficiary}.",
    ],
}

# ── Filler values for template placeholders ────────────────────────────────
TEMPLATE_FILLERS = {
    "collision_type": [
        "rear-end collision",
        "head-on collision",
        "side-impact collision",
        "parking lot accident",
        "hit-and-run incident",
    ],
    "damage_level": ["minor", "moderate", "severe", "extensive", "total"],
    "damage_part": [
        "front bumper",
        "rear panel",
        "driver-side door",
        "hood and engine bay",
        "windshield and roof",
        "undercarriage",
    ],
    "weather": ["Clear", "Rainy", "Foggy", "Icy road", "Heavy rain"],
    "fault_detail": [
        "admitted fault at the scene",
        "denied fault but witness corroborates insured",
        "fled the scene",
        "also filed a claim",
        "provided insurance details",
    ],
    "collision_party": [
        "a commercial truck",
        "another private vehicle",
        "a motorcycle",
        "a parked car",
        "a road divider",
    ],
    "garage": [
        "AutoFix Center",
        "City Motors Repair",
        "Quick Lube & Repair",
        "Precision Auto Body",
        "National Auto Care",
    ],
    "vandalism_type": [
        "keyed",
        "broken into",
        "graffitied",
        "had mirrors smashed",
        "had tires slashed",
    ],
    "footage_detail": [
        "captured the incident",
        "was unavailable due to outage",
        "shows partial view only",
    ],
    "extra_claim": [
        "rental car reimbursement",
        "towing charges",
        "personal items damaged inside",
    ],
    "diagnosis": [
        "acute myocardial infarction",
        "appendicitis",
        "severe fracture of the femur",
        "pneumonia requiring ICU care",
        "type 2 diabetes complications",
        "lumbar disc herniation",
        "breast cancer stage II",
        "stroke",
        "severe asthma attack",
        "kidney failure",
    ],
    "treatment": [
        "cardiac catheterization",
        "emergency appendectomy",
        "orthopedic surgery",
        "ventilator support and antibiotics",
        "insulin therapy and dietary management",
        "spinal fusion surgery",
        "chemotherapy cycle",
        "physical therapy",
        "dialysis sessions",
        "laparoscopic surgery",
    ],
    "hospital": [
        "St. Mary's Medical Center",
        "City General Hospital",
        "Regional Healthcare Institute",
        "University Medical Center",
        "Sunrise Community Hospital",
    ],
    "pharmacy": [
        "CVS Pharmacy",
        "Walgreens",
        "Rite Aid",
        "Express Scripts",
        "CostPlus Drugs",
    ],
    "cause": [
        "strong winds during storm",
        "electrical fault",
        "kitchen fire",
        "burst pipe causing flooding",
        "heavy rainfall and poor drainage",
        "accidental ignition",
        "lightning strike",
    ],
    "structure": [
        "single-family home",
        "condominium",
        "commercial building",
        "rental property",
        "garage",
    ],
    "rooms": [
        "kitchen and living room",
        "basement and ground floor",
        "master bedroom suite",
        "entire ground floor",
        "garage and utility room",
    ],
    "structural": [
        "is compromised and requires immediate assessment",
        "appears intact but needs professional inspection",
        "shows no signs of damage beyond surface level",
    ],
    "items": [
        "electronics, jewelry, and cash",
        "power tools and equipment",
        "laptop, camera, and watches",
        "artwork and collectibles",
    ],
    "entry": [
        "broken rear window",
        "forced front door lock",
        "basement window",
        "unlocked garage door",
    ],
    "security_detail": [
        "was disabled prior to entry",
        "triggered but response was delayed",
        "footage captured perpetrator partially",
    ],
    "allegation": [
        "premises were negligently maintained",
        "adequate warning signs were absent",
        "product was defective and caused injury",
    ],
    "injuries": [
        "fractured wrist and bruised ribs",
        "concussion and soft tissue injuries",
        "severe laceration requiring stitches",
        "back injury and neck strain",
    ],
    "claimant": [
        "Jane M. Reyes",
        "Robert P. Kumar",
        "Sarah L. Thompson",
        "Marcus D. Williams",
        "Linda K. Chen",
    ],
    "destination": [
        "Paris, France",
        "Tokyo, Japan",
        "Cancun, Mexico",
        "London, UK",
        "Sydney, Australia",
        "Dubai, UAE",
    ],
    "cancel_reason": [
        "sudden illness of insured requiring hospitalization",
        "death of immediate family member",
        "natural disaster at destination",
        "employer-mandated travel restriction",
        "airline insolvency",
    ],
    "cause_of_death": [
        "natural causes",
        "sudden cardiac arrest",
        "vehicle accident",
        "terminal illness as per attached medical records",
    ],
    "relationship": ["spouse", "child", "parent", "sibling", "domestic partner"],
    "payment_method": [
        "bank wire transfer",
        "certified cheque",
        "electronic funds transfer",
    ],
    "occupation": [
        "software engineer",
        "nurse",
        "construction worker",
        "teacher",
        "truck driver",
        "accountant",
    ],
    "prognosis": [
        "permanent inability to perform physical tasks",
        "chronic pain preventing sedentary work",
        "cognitive impairment affecting all work functions",
    ],
    "make": [
        "Toyota",
        "Honda",
        "Ford",
        "BMW",
        "Chevrolet",
        "Tesla",
        "Hyundai",
        "Nissan",
        "Kia",
        "Volkswagen",
    ],
    "product": [
        "faulty power tool",
        "defective baby crib",
        "contaminated food product",
        "malfunctioning space heater",
        "defective vehicle component",
    ],
    "recall": [
        "no active recall in effect",
        "product under voluntary recall",
        "regulatory investigation pending",
    ],
}
