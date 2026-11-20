-- View: vw_claims_analytics
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
    ROUND(COALESCE(c.approved_amount, 0.00) / NULLIF(p.coverage_limit, 0) * 100, 2) AS payout_to_coverage_pct,
    c.incident_date,
    c.filing_date,
    DATEDIFF(c.filing_date, c.incident_date) AS filing_lag_days,
    c.is_fraud,
    c.fraud_reason,
    c.created_at AS claim_created_at
FROM claims c
JOIN policies p ON c.policy_id = p.policy_id
JOIN customers cust ON c.customer_id = cust.customer_id;
