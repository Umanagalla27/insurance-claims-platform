-- ============================================================
-- Migration: 003_performance_indexes.sql
-- Description: Composite and Covering Indexes for Analytical Workloads
-- Dialect: MySQL 8.x / InnoDB
-- ============================================================

-- 1. Composite Covering Index for Date-Range Category Analytics
-- Eliminates table lookups and filesort for claims reporting
CREATE INDEX idx_clm_perf_cat_stat_date 
    ON claims (claim_category, status, incident_date, claim_amount);

-- 2. Composite Index for Policy Aggregations and Loss Ratio
CREATE INDEX idx_clm_pol_amt 
    ON claims (policy_id, claim_amount, status);

-- 3. Composite Covering Index for Fraud Risk Investigation
CREATE INDEX idx_clm_fraud_state_amt 
    ON claims (is_fraud, state, claim_amount);

-- 4. Composite Index for Customer Geographic Analytics
CREATE INDEX idx_cust_state_city 
    ON customers (state, city);
