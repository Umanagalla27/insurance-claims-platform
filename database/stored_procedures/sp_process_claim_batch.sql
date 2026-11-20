-- ============================================================
-- Stored Procedure: sp_process_claim_batch.sql
-- Description: Batch adjudication and approval of pending claims.
-- Implements Straight-Through Processing (STP) for low-risk claims.
-- Features: Transaction boundary (COMMIT/ROLLBACK), SQLEXCEPTION handler,
-- and automatic audit log generation via triggers.
-- Dialect: MySQL 8.x
-- ============================================================

DELIMITER $$

DROP PROCEDURE IF EXISTS sp_process_claim_batch$$

CREATE PROCEDURE sp_process_claim_batch(
    IN  p_category                  VARCHAR(50),
    IN  p_max_auto_approve_amount   DECIMAL(12, 2),
    OUT p_processed_count           INT,
    OUT p_approved_count            INT,
    OUT p_status_message            VARCHAR(255)
)
proc_block: BEGIN
    -- PL/SQL style error handler: Rolls back transaction on unexpected SQL exceptions
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        GET DIAGNOSTICS CONDITION 1
            @sqlstate = RETURNED_SQLSTATE, 
            @errno = MYSQL_ERRNO, 
            @text = MESSAGE_TEXT;
        ROLLBACK;
        SET p_processed_count = 0;
        SET p_approved_count = 0;
        SET p_status_message = CONCAT('FAILED: [', @sqlstate, '] ', @text);
    END;

    -- Validate input thresholds
    IF p_max_auto_approve_amount <= 0 THEN
        SET p_status_message = 'INVALID_INPUT: Max approval threshold must be strictly positive.';
        LEAVE proc_block;
    END IF;

    -- Initialize output parameters
    SET p_processed_count = 0;
    SET p_approved_count = 0;

    -- Begin Transaction Boundary
    START TRANSACTION;

    -- 1. Identify and count eligible claims
    -- Criteria: Status = 'Pending', is_fraud = 0, amount <= threshold, matching category
    SELECT COUNT(*) INTO p_processed_count
    FROM claims c
    WHERE c.status = 'Pending'
      AND c.is_fraud = 0
      AND c.claim_amount <= p_max_auto_approve_amount
      AND (p_category IS NULL OR c.claim_category = p_category);

    -- 2. Bulk update eligible claims to Approved and compute payout
    -- This update statement fires trg_claims_audit_after_update automatically for each row!
    UPDATE claims c
    JOIN policies p ON c.policy_id = p.policy_id
    SET 
        c.status = 'Approved',
        c.approved_amount = fn_calculate_payout(c.claim_amount, p.deductible, p.coverage_limit),
        c.updated_at = CURRENT_TIMESTAMP
    WHERE c.status = 'Pending'
      AND c.is_fraud = 0
      AND c.claim_amount <= p_max_auto_approve_amount
      AND (p_category IS NULL OR c.claim_category = p_category);

    SET p_approved_count = ROW_COUNT();

    -- Commit transaction
    COMMIT;

    SET p_status_message = CONCAT(
        'SUCCESS: Processed ', p_processed_count, 
        ' claims, auto-approved ', p_approved_count, ' claims.'
    );

END proc_block$$

DELIMITER ;
