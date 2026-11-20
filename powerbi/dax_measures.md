# Power BI DAX Measures & Semantic Layer Reference Guide

## Insurance Claims Intelligence Platform (ICIP)
**Author**: Uma (Platform & Gen AI Engineer)  
**Architecture**: Kimball Star-Schema Semantic Model  
**Target Environments**: Microsoft Power BI Desktop, Microsoft Fabric Semantic Models, Azure Analysis Services  

---

## 1. Executive Summary & Architecture Principles

In modern Property & Casualty (P&C) insurance, business intelligence must be governed by a **single source of truth**. Rather than allowing report creators to write ad-hoc aggregations on raw staging tables, all enterprise metrics are centralized as certified DAX measures.

### Core DAX Design Standards
1. **Zero Division-by-Zero Exceptions**: Raw division (`/`) is strictly prohibited. All ratios utilize `DIVIDE(Numerator, Denominator, AlternateResult)` with a default fallback of `0`.
2. **Explicit Filtering Context**: All conditional aggregates explicitly leverage `CALCULATE()` with boolean filter predicates.
3. **Single-Direction Relationship Enforcement**: All cross-filtering flows strictly from 1 (`dim_*`) to Many (`fact_*`), preventing ambiguous filter paths and VertiPaq memory bloat.

---

## 2. Certified DAX Measures Catalog

| Measure Name | Category | DAX Formula | Business Definition | Format String | Target Benchmark |
|---|---|---|---|---|---|
| **[Total Claims Filed]** | Volume | `COUNTROWS(fact_claims_adjudication)` | Total volume of claims submitted across all channels | `#,##0` | — |
| **[Total Incurred Claims]** | Financial | `SUM(fact_claims_adjudication[claim_amount])` | Total initial claimed financial liability incurred | `$#,##0.00` | — |
| **[Total Approved Payout]** | Financial | `SUM(fact_claims_adjudication[approved_amount])` | Total settlement dollars paid out to policyholders | `$#,##0.00` | — |
| **[Total Earned Premium]** | Underwriting | `SUM(dim_policy[annual_premium])` | Gross written/earned premium across in-force policies | `$#,##0.00` | — |
| **[Average Claim Amount]** | Financial | `AVERAGE(fact_claims_adjudication[claim_amount])` | Mean gross amount per claim transaction | `$#,##0.00` | Under $15,000 for standard P&C |
| **[Loss Ratio %]** | Underwriting | `DIVIDE([Total Approved Payout], [Total Earned Premium], 0)` | Primary profitability KPI: ratio of paid losses to earned premiums | `0.00%` | **60% - 75%** (Healthy) |
| **[Payout Ratio %]** | Financial | `DIVIDE([Total Approved Payout], [Total Incurred Claims], 0)` | Proportion of claimed dollar volume approved for payout | `0.00%` | 50% - 70% |
| **[STP Claims Count]** | Operations | `CALCULATE(COUNTROWS(fact_claims_adjudication), fact_claims_adjudication[is_straight_through_approved] = 1)` | Count of claims touchlessly approved by AI/rules engine | `#,##0` | — |
| **[STP Rate %]** | Operations | `DIVIDE([STP Claims Count], [Total Claims Filed], 0)` | Straight-Through Processing rate: approved in <= 5 days without manual adjustor review | `0.00%` | **> 15.0%** |
| **[Approval Rate %]** | Operations | `DIVIDE(CALCULATE(COUNTROWS(fact_claims_adjudication), fact_claims_adjudication[claim_status] = "APPROVED"), [Total Claims Filed], 0)` | Overall percentage of filed claims approved | `0.00%` | 70% - 85% |
| **[Average Filing Lag Days]** | Operations | `AVERAGE(fact_claims_adjudication[filing_lag_days])` | Mean calendar days between incident occurrence and filing | `0.0 Days` | **< 15.0 Days** |
| **[Fraud Incident Count]** | Fraud | `CALCULATE(COUNTROWS(fact_claims_adjudication), fact_claims_adjudication[is_fraud] = 1)` | Total count of fraudulent claims detected by ML/rules | `#,##0` | — |
| **[Fraud Rate %]** | Fraud | `DIVIDE([Fraud Incident Count], [Total Claims Filed], 0)` | Percentage of total filed claims identified as fraudulent | `0.00%` | **< 5.0%** |
| **[Fraud Loss Avoidance $]** | Fraud | `SUM(fact_claims_adjudication[fraud_loss_avoidance])` | Hard dollar savings protected by denying fraudulent claims | `$#,##0.00` | Maximum possible |
| **[Claims Previous Month]** | Trend | `CALCULATE([Total Claims Filed], DATEADD(dim_date[full_date], -1, MONTH))` | Claim volume in the preceding calendar month | `#,##0` | — |
| **[Claims MoM Growth %]** | Trend | `DIVIDE([Total Claims Filed] - [Claims Previous Month], [Claims Previous Month], 0)` | Month-over-month percentage change in claim volume | `0.00%` | Track spikes |

---

## 3. Power BI Page Mapping & Visual Architecture

### Page 1: Executive Claims & Portfolio Overview
- **Audience**: Chief Executive Officer, Chief Risk Officer, VP of Underwriting.
- **Visuals**:
  1. 5 KPI Cards: `[Total Incurred Claims]`, `[Total Approved Payout]`, `[Total Earned Premium]`, `[Loss Ratio %]`, `[Total Claims Filed]`.
  2. Combo Chart: Monthly Incurred Claims (Columns) vs Loss Ratio % (Line).
  3. Donut Chart: Claims Breakdown by Category (Auto, Property, Health, Liability, Life).
  4. Bar Chart: Loss Ratio & Paid Claims by US Region (Northeast, Midwest, South, West).
  5. Matrix Table: Underwriting Portfolio Performance by Coverage Tier & Premium Band.

### Page 2: Fraud Detection & Risk Loss Avoidance
- **Audience**: Head of Special Investigation Unit (SIU), Fraud Analytics Lead.
- **Visuals**:
  1. 4 KPI Cards: `[Fraud Incident Count]`, `[Fraud Rate %]`, `[Fraud Loss Avoidance $]`, `[Critical Anomaly Claims]`.
  2. Treemap: Loss Avoidance ($) segmented by Fraud Reason.
  3. Clustered Column Chart: Fraud Incidence Rate % across Customer Credit Tiers.
  4. SIU Audit Table: Top 10 High-Risk Claims with Claim ID, Customer, Category, Claim Amount, and Reason.

### Page 3: Operational Efficiency & AI Platform Telemetry
- **Audience**: VP of Claims Operations, Customer Experience Director, AI Engineering Lead.
- **Visuals**:
  1. 4 KPI Cards: `[STP Rate %]`, `[STP Claims Count]`, `[Average Filing Lag Days]`, `[Approval Rate %]`.
  2. Funnel Chart: Claims Lifecycle Adjudication Funnel.
  3. Bar Chart: STP Touchless Approval Rate by Claim Priority (Low, Medium, High, Urgent).
  4. Trend Chart: Filing Lag Days Distribution over Calendar Months.
