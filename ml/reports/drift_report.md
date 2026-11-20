# MLOps Governance: Statistical Data & Prediction Drift Report
**Evaluation Timestamp**: `2026-11-20T18:29:38.522081+00:00`  
**Target Model**: `NLP Claim Domain Classifier`  
**Baseline Dataset**: `claims_clean_baseline` | **Current Batch**: `simulated_inflation_catastrophe_batch`  
**Overall Status**: **ACTION REQUIRED: Retraining Triggered**

---
## 1. Executive Summary
- **Total Features Audited**: 5
- **Drifted Features Count**: 3
- **Critical Drift (PSI >= 0.25)**: 2
- **Moderate Drift (0.10 <= PSI < 0.25)**: 1
- **Retraining Policy Triggered**: `YES`

## 2. Feature Drift Breakdown Table
| Feature Name | Type | PSI Score | p-Value | Test Statistic | Test Name | Severity |
|:---|:---:|:---:|:---:|:---:|:---|:---:|
| `approved_amount` | continuous | 0.0448 | 2.5795e-08 | 0.0919 | Kolmogorov-Smirnov + PSI | **NONE** |
| `claim_amount` | continuous | 0.1184 | 6.9002e-33 | 0.1505 | Kolmogorov-Smirnov + PSI | **MODERATE** |
| `claim_category` | categorical | 0.3742 | 2.5584e-147 | 697.1216 | Chi-Square Contingency + Categorical PSI | **CRITICAL** |
| `claim_priority` | categorical | 6.2004 | 0.0000e+00 | 3397.2893 | Chi-Square Contingency + Categorical PSI | **CRITICAL** |
| `status` | categorical | 0.0005 | 9.2867e-01 | 0.8711 | Chi-Square Contingency + Categorical PSI | **NONE** |

## 3. Governance Policy Decision
- **PSI < 0.10**: Distribution is stable. No model degradation expected.
- **0.10 <= PSI < 0.25**: Moderate drift. System flags warning for monitoring.
- **PSI >= 0.25**: Critical drift. Retraining decision engine immediately stages new candidate weights.

> **Automated Trigger Outcome**: `RETRAIN_TRIGGERED`