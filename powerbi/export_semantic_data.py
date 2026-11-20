"""
Power BI Star-Schema Semantic Data Exporter & Dimensional Transformer (ICIP-025).
Transforms raw staging data into conformed Kimball dimensions and fact datasets
for Power BI, Fabric, or Metabase analytical dashboards.
"""

import json
import logging
import sys
from pathlib import Path

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("semantic_exporter")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STAGING_DIR = PROJECT_ROOT / "data" / "staging"
OUTPUT_DIR = PROJECT_ROOT / "data" / "semantic_layer"


US_REGION_MAP = {
    "Northeast": ["CT", "ME", "MA", "NH", "RI", "VT", "NJ", "NY", "PA"],
    "Midwest": ["IL", "IN", "MI", "OH", "WI", "IA", "KS", "MN", "MO", "NE", "ND", "SD"],
    "South": [
        "DE",
        "FL",
        "GA",
        "MD",
        "NC",
        "SC",
        "VA",
        "WV",
        "AL",
        "KY",
        "MS",
        "TN",
        "AR",
        "LA",
        "OK",
        "TX",
    ],
    "West": [
        "AZ",
        "CO",
        "ID",
        "MT",
        "NV",
        "NM",
        "UT",
        "WY",
        "AK",
        "CA",
        "HI",
        "OR",
        "WA",
    ],
}


def get_us_region(state: str) -> str:
    """Map US state code to geographic region."""
    state_clean = str(state).strip().upper()
    for region, states in US_REGION_MAP.items():
        if state_clean in states:
            return region
    return "Other"


def get_credit_tier(score: float) -> str:
    """Map credit score to industry standard credit tier."""
    try:
        val = float(score)
        if val >= 800:
            return "Exceptional (800+)"
        elif val >= 740:
            return "Very Good (740-799)"
        elif val >= 670:
            return "Good (670-739)"
        elif val >= 580:
            return "Fair (580-669)"
        else:
            return "Poor (< 580)"
    except (ValueError, TypeError):
        return "Unknown"


def get_coverage_tier(limit: float) -> str:
    """Categorize coverage limit into policy tier."""
    try:
        val = float(limit)
        if val < 25000:
            return "Basic Coverage (< $25k)"
        elif val <= 100000:
            return "Standard Coverage ($25k-$100k)"
        else:
            return "Premium Coverage (> $100k)"
    except (ValueError, TypeError):
        return "Standard"


def get_premium_band(premium: float) -> str:
    """Categorize annual premium into cost band."""
    try:
        val = float(premium)
        if val < 1000:
            return "Low (< $1k)"
        elif val <= 2500:
            return "Moderate ($1k-$2.5k)"
        else:
            return "High (> $2.5k)"
    except (ValueError, TypeError):
        return "Moderate"


def build_semantic_model(
    staging_dir: Path = STAGING_DIR, output_dir: Path = OUTPUT_DIR
) -> dict:
    """Read staging CSVs, transform into star-schema tables, and export."""
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Loading staging tables from: %s", staging_dir)

    claims_file = staging_dir / "stg_claims.csv"
    policies_file = staging_dir / "stg_policies.csv"
    customers_file = staging_dir / "stg_customers.csv"

    if not (
        claims_file.is_file() and policies_file.is_file() and customers_file.is_file()
    ):
        raise FileNotFoundError(f"Required staging files missing in: {staging_dir}")

    df_claims = pd.read_csv(claims_file)
    df_policies = pd.read_csv(policies_file)
    df_customers = pd.read_csv(customers_file)

    logger.info(
        "Loaded %d claims, %d policies, %d customers.",
        len(df_claims),
        len(df_policies),
        len(df_customers),
    )

    # --------------------------------------------------------------------------
    # 1. Transform: dim_customer
    # --------------------------------------------------------------------------
    logger.info("Building dim_customer conformed dimension...")
    dim_customer = pd.DataFrame()
    dim_customer["customer_id"] = df_customers["customer_id"]
    dim_customer["full_name"] = (
        df_customers["first_name"] + " " + df_customers["last_name"]
    )
    dim_customer["email"] = df_customers.get("email", "").fillna("")
    dim_customer["phone"] = df_customers.get("phone", "").fillna("")
    dim_customer["city"] = df_customers.get("city", "").fillna("")
    dim_customer["state"] = df_customers.get("state", "").fillna("")
    dim_customer["us_region"] = df_customers["state"].apply(get_us_region)
    dim_customer["credit_score"] = df_customers["credit_score"].fillna(650).astype(int)
    dim_customer["credit_tier"] = dim_customer["credit_score"].apply(get_credit_tier)

    if "annual_income" in df_customers.columns:
        dim_customer["annual_income"] = df_customers["annual_income"].astype(float)
    else:
        # Derived synthetic annual income based on credit score tier
        dim_customer["annual_income"] = (dim_customer["credit_score"] * 115.0).round(2)

    created_col = df_customers.get("created_at", "2024-01-01")
    dim_customer["customer_since"] = pd.to_datetime(
        created_col, errors="coerce"
    ).dt.strftime("%Y-%m-%d")

    # --------------------------------------------------------------------------
    # 2. Transform: dim_policy
    # --------------------------------------------------------------------------
    logger.info("Building dim_policy conformed dimension...")
    dim_policy = pd.DataFrame()
    dim_policy["policy_id"] = df_policies["policy_id"]
    dim_policy["policy_type"] = df_policies["policy_type"]
    dim_policy["policy_status"] = df_policies.get("status", "ACTIVE")
    dim_policy["annual_premium"] = df_policies["annual_premium"].astype(float)
    dim_policy["coverage_limit"] = df_policies["coverage_limit"].astype(float)
    dim_policy["deductible"] = df_policies.get("deductible", 500.0).astype(float)
    dim_policy["coverage_tier"] = dim_policy["coverage_limit"].apply(get_coverage_tier)
    dim_policy["premium_band"] = dim_policy["annual_premium"].apply(get_premium_band)

    eff_date = df_policies.get(
        "effective_date", df_policies.get("start_date", "2025-01-01")
    )
    exp_date = df_policies.get(
        "expiration_date", df_policies.get("end_date", "2026-01-01")
    )
    dim_policy["effective_date"] = pd.to_datetime(
        eff_date, errors="coerce"
    ).dt.strftime("%Y-%m-%d")
    dim_policy["expiration_date"] = pd.to_datetime(
        exp_date, errors="coerce"
    ).dt.strftime("%Y-%m-%d")

    # --------------------------------------------------------------------------
    # 3. Transform: dim_date
    # --------------------------------------------------------------------------
    logger.info("Building dim_date conformed calendar hierarchy...")
    dates_series = (
        pd.concat(
            [
                pd.to_datetime(df_claims["incident_date"], errors="coerce"),
                pd.to_datetime(df_claims["filing_date"], errors="coerce"),
            ]
        )
        .dropna()
        .drop_duplicates()
        .sort_values()
    )

    dim_date = pd.DataFrame({"full_date": dates_series})
    dim_date["date_key"] = dim_date["full_date"].dt.strftime("%Y%m%d").astype(int)
    dim_date["calendar_year"] = dim_date["full_date"].dt.year
    dim_date["calendar_quarter"] = "Q" + dim_date["full_date"].dt.quarter.astype(str)
    dim_date["month_number"] = dim_date["full_date"].dt.month
    dim_date["month_name"] = dim_date["full_date"].dt.strftime("%B")
    dim_date["month_short_name"] = dim_date["full_date"].dt.strftime("%b")
    dim_date["week_of_year"] = dim_date["full_date"].dt.isocalendar().week.astype(int)
    dim_date["day_of_week"] = dim_date["full_date"].dt.day_of_week + 1
    dim_date["day_name"] = dim_date["full_date"].dt.strftime("%A")
    dim_date["is_weekend"] = dim_date["day_of_week"].isin([1, 7]).astype(int)
    dim_date["full_date"] = dim_date["full_date"].dt.strftime("%Y-%m-%d")

    # --------------------------------------------------------------------------
    # 4. Transform: fact_claims_adjudication
    # --------------------------------------------------------------------------
    logger.info("Building fact_claims_adjudication...")
    fact_claims = pd.DataFrame()
    fact_claims["claim_id"] = df_claims["claim_id"]
    fact_claims["policy_id"] = df_claims["policy_id"]
    fact_claims["customer_id"] = df_claims["customer_id"]

    filing_dt = pd.to_datetime(df_claims["filing_date"], errors="coerce")
    incident_dt = pd.to_datetime(df_claims["incident_date"], errors="coerce")

    fact_claims["date_key"] = (
        filing_dt.dt.strftime("%Y%m%d").fillna(20260101).astype(int)
    )
    fact_claims["claim_category"] = (
        df_claims.get("claim_category", "AUTO").astype(str).str.upper()
    )
    fact_claims["claim_priority"] = (
        df_claims.get("claim_priority", "MEDIUM").astype(str).str.upper()
    )
    fact_claims["claim_status"] = (
        df_claims.get("status", "SUBMITTED").astype(str).str.upper()
    )
    fact_claims["claim_amount"] = df_claims["claim_amount"].astype(float)

    # Approved amount: if missing/null in staging, default approved for APPROVED claims, else 0
    raw_approved = df_claims.get("approved_amount")
    if raw_approved is not None:
        approved = raw_approved.fillna(0.0).astype(float)
        # If all approved amounts were empty in raw data, infer based on status
        if approved.sum() == 0.0:
            approved = df_claims.apply(
                lambda r: (
                    float(r["claim_amount"]) * 0.85
                    if str(r.get("status", "")).upper() == "APPROVED"
                    else 0.0
                ),
                axis=1,
            )
    else:
        approved = df_claims.apply(
            lambda r: (
                float(r["claim_amount"]) * 0.85
                if str(r.get("status", "")).upper() == "APPROVED"
                else 0.0
            ),
            axis=1,
        )
    fact_claims["approved_amount"] = approved.round(2)

    # Payout ratio percentage
    fact_claims["payout_ratio_pct"] = (
        (
            (
                fact_claims["approved_amount"]
                / fact_claims["claim_amount"].replace(0, pd.NA)
            )
            * 100.0
        )
        .fillna(0.0)
        .round(2)
    )

    # Filing lag days
    lag_days = (filing_dt - incident_dt).dt.days.fillna(0).astype(int)
    fact_claims["filing_lag_days"] = lag_days

    # Straight-Through-Processing (STP): Approved within 5 days of incident
    is_stp = (fact_claims["claim_status"] == "APPROVED") & (
        fact_claims["filing_lag_days"] <= 5
    )
    fact_claims["is_straight_through_approved"] = is_stp.astype(int)

    # Fraud flag & loss avoidance
    is_fraud = df_claims.get("is_fraud", 0).fillna(0).astype(int)
    fact_claims["is_fraud"] = is_fraud
    fact_claims["fraud_reason"] = df_claims.get("fraud_reason", "").fillna("")

    # Fraud loss avoidance: Dollar amount denied on fraudulent claims
    fraud_savings = fact_claims.apply(
        lambda r: (
            r["claim_amount"]
            if (
                r["is_fraud"] == 1
                and r["claim_status"]
                in ["REJECTED", "FLAGGED", "DENIED", "UNDER REVIEW"]
            )
            else 0.0
        ),
        axis=1,
    )
    fact_claims["fraud_loss_avoidance"] = fraud_savings.round(2)
    fact_claims["claim_timestamp"] = df_claims.get(
        "created_at", df_claims["filing_date"]
    )

    # --------------------------------------------------------------------------
    # 5. Transform: fact_underwriting_portfolio
    # --------------------------------------------------------------------------
    logger.info("Building fact_underwriting_portfolio...")
    claims_by_policy = (
        fact_claims.groupby("policy_id")
        .agg(
            total_claims_count=("claim_id", "count"),
            total_incurred_claims=("claim_amount", "sum"),
            total_approved_payout=("approved_amount", "sum"),
        )
        .reset_index()
    )

    fact_underwriting = pd.merge(
        dim_policy, claims_by_policy, on="policy_id", how="left"
    )
    fact_underwriting["total_claims_count"] = (
        fact_underwriting["total_claims_count"].fillna(0).astype(int)
    )
    fact_underwriting["total_incurred_claims"] = (
        fact_underwriting["total_incurred_claims"].fillna(0.0).round(2)
    )
    fact_underwriting["total_approved_payout"] = (
        fact_underwriting["total_approved_payout"].fillna(0.0).round(2)
    )

    fact_underwriting["loss_ratio_pct"] = (
        (
            (
                fact_underwriting["total_approved_payout"]
                / fact_underwriting["annual_premium"].replace(0, pd.NA)
            )
            * 100.0
        )
        .fillna(0.0)
        .round(2)
    )

    # --------------------------------------------------------------------------
    # 6. Export to CSV & Write Summary Metrics
    # --------------------------------------------------------------------------
    logger.info("Exporting dimensional tables to CSV in %s...", output_dir)
    dim_customer.to_csv(output_dir / "dim_customer.csv", index=False)
    dim_policy.to_csv(output_dir / "dim_policy.csv", index=False)
    dim_date.to_csv(output_dir / "dim_date.csv", index=False)
    fact_claims.to_csv(output_dir / "fact_claims_adjudication.csv", index=False)
    fact_underwriting.to_csv(
        output_dir / "fact_underwriting_portfolio.csv", index=False
    )

    total_claims = len(fact_claims)
    total_incurred = float(fact_claims["claim_amount"].sum())
    total_payout = float(fact_claims["approved_amount"].sum())
    total_premium = float(dim_policy["annual_premium"].sum())
    overall_loss_ratio = (
        round((total_payout / total_premium * 100.0), 2) if total_premium > 0 else 0.0
    )
    stp_count = int(fact_claims["is_straight_through_approved"].sum())
    stp_rate = round((stp_count / total_claims * 100.0), 2) if total_claims > 0 else 0.0
    fraud_count = int(fact_claims["is_fraud"].sum())
    fraud_rate = (
        round((fraud_count / total_claims * 100.0), 2) if total_claims > 0 else 0.0
    )
    fraud_savings_total = round(float(fact_claims["fraud_loss_avoidance"].sum()), 2)
    avg_lag = round(float(fact_claims["filing_lag_days"].mean()), 1)

    summary = {
        "status": "SUCCESS",
        "records_exported": {
            "dim_customer": len(dim_customer),
            "dim_policy": len(dim_policy),
            "dim_date": len(dim_date),
            "fact_claims_adjudication": len(fact_claims),
            "fact_underwriting_portfolio": len(fact_underwriting),
        },
        "kpi_metrics": {
            "total_claims_filed": total_claims,
            "total_incurred_claims_usd": round(total_incurred, 2),
            "total_approved_payout_usd": round(total_payout, 2),
            "total_earned_premium_usd": round(total_premium, 2),
            "overall_loss_ratio_pct": overall_loss_ratio,
            "straight_through_processing_count": stp_count,
            "straight_through_processing_rate_pct": stp_rate,
            "fraud_incidents_detected": fraud_count,
            "fraud_rate_pct": fraud_rate,
            "fraud_loss_avoidance_usd": fraud_savings_total,
            "average_settlement_lag_days": avg_lag,
        },
    }

    metrics_path = output_dir / "summary_metrics.json"
    metrics_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    logger.info("Summary metrics written to: %s", metrics_path)

    return summary


def main() -> int:
    try:
        summary = build_semantic_model()
        print("\n" + "=" * 80)
        print("   Insurance Claims Intelligence — Star-Schema Semantic Layer Summary")
        print("=" * 80)
        for tbl, count in summary["records_exported"].items():
            print(f"   * Table: {tbl:<28} | Rows: {count:>6,}")
        print("-" * 80)
        for kpi, val in summary["kpi_metrics"].items():
            if "usd" in kpi:
                print(f"   * KPI: {kpi:<34} | ${val:>13,.2f}")
            elif "pct" in kpi:
                print(f"   * KPI: {kpi:<34} | {val:>10.2f}%")
            else:
                print(f"   * KPI: {kpi:<34} | {val:>13,}")
        print("=" * 80 + "\n")
        return 0
    except Exception as e:
        logger.error("Failed to build semantic model: %s", e, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
