-- View: vw_fraud_risk_summary
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
