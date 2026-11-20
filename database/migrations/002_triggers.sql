-- ============================================================
-- Migration: 002_triggers.sql
-- Description: Automated Audit Trail and Business Validation Triggers
-- Dialect: MySQL 8.x / InnoDB
-- ============================================================

DELIMITER $$

-- ------------------------------------------------------------
-- 1. Trigger: trg_claims_validate_before_insert
-- Description: Enforces financial and date logic rules at engine level.
-- Raises custom SQLSTATE '45000' exception to abort invalid inserts.
-- ------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_claims_validate_before_insert$$

CREATE TRIGGER trg_claims_validate_before_insert
BEFORE INSERT ON claims
FOR EACH ROW
BEGIN
    -- Rule 1: Claim amount must be strictly greater than 0
    IF NEW.claim_amount <= 0.00 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Business Rule Violation: Claim amount must be strictly positive.';
    END IF;

    -- Rule 2: Filing date cannot precede incident date
    IF NEW.filing_date < NEW.incident_date THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Business Rule Violation: Filing date cannot precede incident date.';
    END IF;

    -- Rule 3: Approved amount cannot exceed claim amount
    IF NEW.approved_amount IS NOT NULL AND NEW.approved_amount > NEW.claim_amount THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Business Rule Violation: Approved amount cannot exceed claimed amount.';
    END IF;
END$$

-- ------------------------------------------------------------
-- 2. Trigger: trg_claims_audit_after_update
-- Description: Automatically writes every status transition or amount change
-- into the immutable claims_audit_log table. Zero application-level logging required.
-- ------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_claims_audit_after_update$$

CREATE TRIGGER trg_claims_audit_after_update
AFTER UPDATE ON claims
FOR EACH ROW
BEGIN
    DECLARE v_action VARCHAR(20);

    -- Only write to audit log if status or amounts changed
    IF (OLD.status <> NEW.status) OR (OLD.claim_amount <> NEW.claim_amount) OR 
       (OLD.approved_amount <=> NEW.approved_amount) = 0 THEN

        IF OLD.status <> NEW.status THEN
            SET v_action = 'STATUS_CHANGE';
        ELSEIF OLD.claim_amount <> NEW.claim_amount THEN
            SET v_action = 'AMOUNT_CHANGE';
        ELSE
            SET v_action = 'PAYOUT_ADJUST';
        END IF;

        INSERT INTO claims_audit_log (
            claim_id,
            action,
            old_status,
            new_status,
            old_amount,
            new_amount,
            changed_by,
            changed_at
        ) VALUES (
            NEW.claim_id,
            v_action,
            OLD.status,
            NEW.status,
            OLD.claim_amount,
            NEW.claim_amount,
            COALESCE(@current_user_id, CURRENT_USER()),
            CURRENT_TIMESTAMP
        );
    END IF;
END$$

DELIMITER ;
