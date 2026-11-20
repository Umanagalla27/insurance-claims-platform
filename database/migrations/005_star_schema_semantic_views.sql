-- ==============================================================================
-- 005_star_schema_semantic_views.sql — Kimball Dimensional Model for Power BI
-- ==============================================================================
-- Database: MySQL 8.4 Warehouse
-- Purpose: Exposes conformed dimensions and fact views for Executive Analytics,
--          Loss Ratio analysis, Fraud Detection, and Straight-Through-Processing.
-- ==============================================================================

USE insurance_warehouse;

-- ------------------------------------------------------------------------------
-- 1. Dimension View: vw_dim_date
-- Calendar hierarchy covering all claim incident and filing dates
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_dim_date AS
SELECT DISTINCT
    CAST(DATE_FORMAT(calendar_date, '%Y%m%d') AS UNSIGNED) AS date_key,
    calendar_date AS full_date,
    YEAR(calendar_date) AS calendar_year,
    CONCAT('Q', QUARTER(calendar_date)) AS calendar_quarter,
    MONTH(calendar_date) AS month_number,
    DATE_FORMAT(calendar_date, '%M') AS month_name,
    DATE_FORMAT(calendar_date, '%b') AS month_short_name,
    WEEK(calendar_date, 1) AS week_of_year,
    DAYOFWEEK(calendar_date) AS day_of_week,
    DATE_FORMAT(calendar_date, '%W') AS day_name,
    CASE WHEN DAYOFWEEK(calendar_date) IN (1, 7) THEN 1 ELSE 0 END AS is_weekend
FROM (
    SELECT DISTINCT incident_date AS calendar_date FROM claims WHERE incident_date IS NOT NULL
    UNION
    SELECT DISTINCT filing_date AS calendar_date FROM claims WHERE filing_date IS NOT NULL
) dates_union;

-- ------------------------------------------------------------------------------
-- 2. Dimension View: vw_dim_policy
-- Policy attributes, coverage limits, and premium classification bands
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_dim_policy AS
SELECT
    policy_id,
    policy_type,
    status AS policy_status,
    annual_premium,
    coverage_limit,
    deductible,
    CASE 
        WHEN coverage_limit < 25000 THEN 'Basic Coverage (< $25k)'
        WHEN coverage_limit BETWEEN 25000 AND 100000 THEN 'Standard Coverage ($25k-$100k)'
        ELSE 'Premium Coverage (> $100k)'
    END AS coverage_tier,
    CASE 
        WHEN annual_premium < 1000 THEN 'Low (< $1k)'
        WHEN annual_premium BETWEEN 1000 AND 2500 THEN 'Moderate ($1k-$2.5k)'
        ELSE 'High (> $2.5k)'
    END AS premium_band,
    effective_date,
    expiration_date
FROM policies;

-- ------------------------------------------------------------------------------
-- 3. Dimension View: vw_dim_customer
-- Demographic profiles, credit score tiers, and US geographic regions
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_dim_customer AS
SELECT
    customer_id,
    CONCAT(first_name, ' ', last_name) AS full_name,
    email,
    phone,
    city,
    state,
    CASE 
        WHEN state IN ('CT', 'ME', 'MA', 'NH', 'RI', 'VT', 'NJ', 'NY', 'PA') THEN 'Northeast'
        WHEN state IN ('IL', 'IN', 'MI', 'OH', 'WI', 'IA', 'KS', 'MN', 'MO', 'NE', 'ND', 'SD') THEN 'Midwest'
        WHEN state IN ('DE', 'FL', 'GA', 'MD', 'NC', 'SC', 'VA', 'WV', 'AL', 'KY', 'MS', 'TN', 'AR', 'LA', 'OK', 'TX') THEN 'South'
        ELSE 'West'
    END AS us_region,
    credit_score,
    CASE 
        WHEN credit_score >= 800 THEN 'Exceptional (800+)'
        WHEN credit_score BETWEEN 740 AND 799 THEN 'Very Good (740-799)'
        WHEN credit_score BETWEEN 670 AND 739 THEN 'Good (670-739)'
        WHEN credit_score BETWEEN 580 AND 669 THEN 'Fair (580-669)'
        ELSE 'Poor (< 580)'
    END AS credit_tier,
    annual_income,
    DATE_FORMAT(created_at, '%Y-%m-%d') AS customer_since
FROM customers;

-- ------------------------------------------------------------------------------
-- 4. Fact View: vw_fact_claims_adjudication
-- Grain: One record per claim filing
-- Measures: Amounts, payouts, lag, STP flag, fraud flag, and loss avoidance
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_fact_claims_adjudication AS
SELECT
    c.claim_id,
    c.policy_id,
    c.customer_id,
    CAST(DATE_FORMAT(c.filing_date, '%Y%m%d') AS UNSIGNED) AS date_key,
    c.claim_category,
    c.claim_priority,
    c.status AS claim_status,
    c.claim_amount,
    COALESCE(c.approved_amount, 0.00) AS approved_amount,
    ROUND(COALESCE(c.approved_amount, 0.00) / NULLIF(c.claim_amount, 0) * 100, 2) AS payout_ratio_pct,
    DATEDIFF(c.filing_date, c.incident_date) AS filing_lag_days,
    -- Straight-Through Processing (STP): Approved within 3 business days of filing
    CASE 
        WHEN c.status = 'APPROVED' AND DATEDIFF(c.filing_date, c.incident_date) <= 3 THEN 1 
        ELSE 0 
    END AS is_straight_through_approved,
    c.is_fraud,
    c.fraud_reason,
    -- Fraud Loss Avoidance: Financial losses averted by catching fraudulent claims
    CASE 
        WHEN c.is_fraud = 1 AND c.status IN ('REJECTED', 'FLAGGED') THEN c.claim_amount 
        ELSE 0.00 
    END AS fraud_loss_avoidance,
    c.created_at AS claim_timestamp
FROM claims c;

-- ------------------------------------------------------------------------------
-- 5. Fact View: vw_fact_underwriting_portfolio
-- Grain: One record per policy
-- Measures: Earned premium, incurred claims, loss ratio
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_fact_underwriting_portfolio AS
SELECT
    p.policy_id,
    p.customer_id,
    p.policy_type,
    p.annual_premium,
    COUNT(c.claim_id) AS total_claims_count,
    COALESCE(SUM(c.claim_amount), 0.00) AS total_incurred_claims,
    COALESCE(SUM(c.approved_amount), 0.00) AS total_approved_payout,
    -- Industry Loss Ratio: Approved Payout / Annual Premium * 100
    ROUND(COALESCE(SUM(c.approved_amount), 0.00) / NULLIF(p.annual_premium, 0) * 100, 2) AS loss_ratio_pct
FROM policies p
LEFT JOIN claims c ON p.policy_id = c.policy_id
GROUP BY p.policy_id, p.customer_id, p.policy_type, p.annual_premium;
