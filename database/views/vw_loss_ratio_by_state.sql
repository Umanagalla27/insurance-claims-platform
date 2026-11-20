-- View: vw_loss_ratio_by_state
CREATE OR REPLACE VIEW vw_loss_ratio_by_state AS
SELECT 
    c.state,
    p.policy_type,
    COUNT(DISTINCT c.policy_id) AS active_policies_count,
    COUNT(c.claim_id) AS total_claims_count,
    SUM(c.claim_amount) AS total_claimed_amount,
    SUM(COALESCE(c.approved_amount, 0.00)) AS total_paid_claims,
    SUM(p.annual_premium) AS total_earned_premium,
    ROUND(
        SUM(COALESCE(c.approved_amount, 0.00)) / NULLIF(SUM(p.annual_premium), 0) * 100, 
        2
    ) AS loss_ratio_pct
FROM claims c
JOIN policies p ON c.policy_id = p.policy_id
GROUP BY c.state, p.policy_type;
