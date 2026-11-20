-- ============================================================
-- Migration: 001_create_tables.sql
-- Description: Core Schema for Insurance Claims Intelligence Platform
-- Dialect: MySQL 8.x / InnoDB
-- ============================================================

-- Set character set and strict SQL mode
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ------------------------------------------------------------
-- 1. Table: customers
-- Description: Master policyholder customer demographic registry
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS customers (
    customer_id     VARCHAR(20)     NOT NULL,
    first_name      VARCHAR(50)     NOT NULL,
    last_name       VARCHAR(50)     NOT NULL,
    email           VARCHAR(100)    DEFAULT NULL,
    phone           VARCHAR(50)     DEFAULT NULL,
    address         VARCHAR(200)    DEFAULT NULL,
    city            VARCHAR(50)     DEFAULT NULL,
    state           VARCHAR(2)      NOT NULL,
    postal_code     VARCHAR(20)     DEFAULT NULL,
    date_of_birth   DATE            NOT NULL,
    credit_score    INT             DEFAULT NULL,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (customer_id),
    INDEX idx_cust_state (state),
    INDEX idx_cust_credit (credit_score)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- 2. Table: policies
-- Description: Insurance policy contracts bound to customers
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS policies (
    policy_id       VARCHAR(20)     NOT NULL,
    customer_id     VARCHAR(20)     NOT NULL,
    policy_type     VARCHAR(50)     NOT NULL,
    coverage_limit  DECIMAL(12, 2)  NOT NULL,
    deductible      DECIMAL(10, 2)  NOT NULL,
    annual_premium  DECIMAL(10, 2)  NOT NULL,
    start_date      DATE            NOT NULL,
    end_date        DATE            NOT NULL,
    status          VARCHAR(20)     NOT NULL DEFAULT 'Active',
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (policy_id),
    CONSTRAINT fk_pol_cust FOREIGN KEY (customer_id) 
        REFERENCES customers (customer_id) 
        ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX idx_pol_cust (customer_id),
    INDEX idx_pol_status (status),
    INDEX idx_pol_type (policy_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- 3. Table: claims
-- Description: Core insurance claims transactional warehouse table
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS claims (
    claim_id        VARCHAR(20)     NOT NULL,
    policy_id       VARCHAR(20)     NOT NULL,
    customer_id     VARCHAR(20)     NOT NULL,
    claim_category  VARCHAR(50)     NOT NULL,
    claim_priority  VARCHAR(20)     NOT NULL DEFAULT 'Medium',
    claim_amount    DECIMAL(12, 2)  NOT NULL,
    approved_amount DECIMAL(12, 2)  DEFAULT NULL,
    incident_date   DATE            NOT NULL,
    filing_date     DATE            NOT NULL,
    status          VARCHAR(30)     NOT NULL DEFAULT 'Pending',
    state           VARCHAR(2)      NOT NULL,
    description     TEXT            NOT NULL,
    is_fraud        TINYINT(1)      NOT NULL DEFAULT 0,
    fraud_reason    VARCHAR(255)    DEFAULT NULL,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (claim_id),
    CONSTRAINT fk_clm_pol FOREIGN KEY (policy_id) 
        REFERENCES policies (policy_id) 
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_clm_cust FOREIGN KEY (customer_id) 
        REFERENCES customers (customer_id) 
        ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX idx_clm_status (status),
    INDEX idx_clm_cat (claim_category),
    INDEX idx_clm_incident (incident_date),
    INDEX idx_clm_filing (filing_date),
    INDEX idx_clm_fraud (is_fraud)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- 4. Table: claims_rejected
-- Description: Dead-letter quarantine table for audit & triage
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS claims_rejected (
    rejection_id        INT AUTO_INCREMENT  NOT NULL,
    record_id           VARCHAR(50)         DEFAULT NULL,
    entity_name         VARCHAR(50)         DEFAULT 'claims',
    rejected_at         TIMESTAMP           DEFAULT CURRENT_TIMESTAMP,
    rejection_reason    VARCHAR(500)        NOT NULL,
    raw_payload         JSON                NOT NULL,
    PRIMARY KEY (rejection_id),
    INDEX idx_rej_record (record_id),
    INDEX idx_rej_date (rejected_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- 5. Table: claims_audit_log
-- Description: Immutable audit trail tracking lifecycle changes
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS claims_audit_log (
    audit_id            INT AUTO_INCREMENT  NOT NULL,
    claim_id            VARCHAR(20)         NOT NULL,
    action              VARCHAR(20)         NOT NULL,
    old_status          VARCHAR(30)         DEFAULT NULL,
    new_status          VARCHAR(30)         DEFAULT NULL,
    old_amount          DECIMAL(12, 2)      DEFAULT NULL,
    new_amount          DECIMAL(12, 2)      DEFAULT NULL,
    changed_by          VARCHAR(50)         DEFAULT 'SYSTEM_ETL',
    changed_at          TIMESTAMP           DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (audit_id),
    INDEX idx_audit_claim (claim_id),
    INDEX idx_audit_action (action),
    INDEX idx_audit_time (changed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
