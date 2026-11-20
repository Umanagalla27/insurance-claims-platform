-- ============================================================
-- Migration: 004_reporting_views.sql
-- Description: Star-Schema Analytical and Reporting Views
-- Formatted specifically for Self-Service Power BI and Executive Reporting
-- Dialect: MySQL 8.x / InnoDB
-- ============================================================

-- ------------------------------------------------------------
-- View 1: vw_claims_analytics
-- Description: Dimensional Star-Schema View joining FactClaims with
-- DimCustomer and DimPolicy. Computes claim lag and payout coverage.
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW vw_claims_analytics AS
SELECT 
    c.claim_id,
    c.policy_id,
    c.customer_id,
    CONCAT(cust.first_name, ' ', cust.last_name) AS customer_name,
    cust.state AS customer_state,
    cust.credit_score,
    p.policy_type,
    p.annual_premium,
    p.coverage_limit,
    p.deductible,
    c.claim_category,
    c.claim_priority,
    c.status AS claim_status,
    c.claim_amount,
    COALESCE(c.approved_amount, 0.00) AS approved_amount,
    -- Financial metric: Payout to Coverage ratio
    ROUND(COALESCE(c.approved_amount, 0.00) / NULLIF(p.coverage_limit, 0) * 100, 2) AS payout_to_coverage_pct,
    c.incident_date,
    c.filing_date,
    -- Operational metric: Filing lag duration in days
    DATEDIFF(c.filing_date, c.incident_date) AS filing_lag_days,
    c.is_fraud,
    c.fraud_reason,
    c.created_at AS claim_created_at
FROM claims c
JOIN policies p ON c.policy_id = p.policy_id
JOIN customers cust ON c.customer_id = cust.customer_id;

-- ------------------------------------------------------------
-- View 2: vw_loss_ratio_by_state
-- Description: Geographic Portfolio Performance and Loss Ratio Analysis.
-- Loss Ratio = (Total Incurred Claims / Total Earned Premium) * 100
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW vw_loss_ratio_by_state AS
SELECT 
    c.state,
    p.policy_type,
    COUNT(DISTINCT c.policy_id) AS active_policies_count,
    COUNT(c.claim_id) AS total_claims_count,
    SUM(c.claim_amount) AS total_claimed_amount,
    SUM(COALESCE(c.approved_amount, 0.00)) AS total_paid_claims,
    SUM(p.annual_premium) AS total_earned_premium,
    -- Actuarial metric: State Loss Ratio
    ROUND(
        SUM(COALESCE(c.approved_amount, 0.00)) / NULLIF(SUM(p.annual_premium), 0) * 100, 
        2
    ) AS loss_ratio_pct
FROM claims c
JOIN policies p ON c.policy_id = p.policy_id
GROUP BY c.state, p.policy_type;

-- ------------------------------------------------------------
-- View 3: vw_fraud_risk_summary
-- Description: Executive Fraud Exposure by Category and Risk Tier
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW vw_fraud_risk_summary AS
SELECT 
    claim_category,
    COUNT(claim_id) AS total_claims,
    SUM(CASE WHEN is_fraud = 1 THEN 1 ELSE 0 END) AS flagged_fraud_claims,
    ROUND(
        SUM(CASE WHEN is_fraud = 1 THEN 1 ELSE 0 END) / COUNT(claim_id) * 100, 
        2
    ) AS fraud_prevalence_pct,
    SUM(CASE WHEN is_fraud = 1 THEN claim_amount ELSE 0.00 END) AS total_fraud_exposure_amount,
    AVG(CASE WHEN is_fraud = 1 THEN claim_amount ELSE NULL END) AS avg_fraud_claim_amount
FROM claims
GROUP BY claim_category;
