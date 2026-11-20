-- ============================================================
-- Function: fn_calculate_payout.sql
-- Description: Deterministic insurance payout computation function.
-- Accounts for coverage limits and policy deductible subtractions.
-- Dialect: MySQL 8.x
-- ============================================================

DELIMITER $$

DROP FUNCTION IF EXISTS fn_calculate_payout$$

CREATE FUNCTION fn_calculate_payout(
    p_claim_amount      DECIMAL(12, 2),
    p_deductible        DECIMAL(10, 2),
    p_coverage_limit    DECIMAL(12, 2)
)
RETURNS DECIMAL(12, 2)
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE v_payable_amount DECIMAL(12, 2);

    -- Payout cannot exceed coverage limit
    SET v_payable_amount = LEAST(p_claim_amount, p_coverage_limit);

    -- Subtract deductible
    SET v_payable_amount = v_payable_amount - p_deductible;

    -- Payout cannot be negative
    RETURN GREATEST(0.00, v_payable_amount);
END$$

DELIMITER ;
