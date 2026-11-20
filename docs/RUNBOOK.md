# Production Incident Response & Operations Runbook

**System**: Insurance Claims Intelligence Platform (ICIP)  
**Classification**: Tier-1 Production Platform  
**Owner**: SRE, Core Platform, and MLOps Engineering  
**Version**: 1.0.0 (Production Release)  
**Last Updated**: November 2026

---

## 1. Incident Severity Classification & SLA Matrix

| Severity | Definition | Target MTTA (Ack) | Target MTTR (Resolve) | Escalation Channel |
|:---|:---|:---:|:---:|:---|
| **P1 - Blocker** | Entire API Gateway unavailable, database down, or all ML subsystems failing | < 5 mins | < 30 mins | Automated PagerDuty + SRE War Room |
| **P2 - Critical** | High 5xx error rate (> 5%), critical feature drift detected, or Lambda ingestion failing | < 15 mins | < 2 hours | Slack `#alerts-prod-urgent` |
| **P3 - Major** | p99 Latency breach (> 2s), STP approval rate drop, or single model degraded | < 30 mins | < 6 hours | JIRA On-Call Backlog |
| **P4 - Minor** | Non-blocking metric warning, minor documentation discrepancies, routine log cleanup | < 4 hours | < 48 hours | Standard Sprint Backlog |

---

## 2. Standard Diagnostic & Health Verification Procedures

### 2.1 Fast Health Probing (Liveness vs. Readiness)
When diagnosing connectivity or traffic routing issues:

```powershell
# 1. Check Liveness (Is process alive?)
curl -s http://localhost:8000/health/live

# 2. Check Readiness (Are all ML models & vector stores loaded?)
curl -s http://localhost:8000/health/ready

# 3. Check Real-Time Prometheus Metrics
curl -s http://localhost:8000/metrics
```

*Expected Readiness Response (HTTP 200 OK)*:
```json
{
  "success": true,
  "data": {
    "status": "ready",
    "components": [
      {"component": "nlp_text_classifier", "status": "ready", "latency_ms": 1.18},
      {"component": "isolation_forest_anomaly", "status": "ready", "latency_ms": 2.45},
      {"component": "policy_vector_store", "status": "ready", "latency_ms": 3.10}
    ]
  }
}
```

---

## 3. Incident Playbooks & Triage Runbooks

### Playbook 3.1: API Gateway Latency Spike (`HighRequestLatency`)
* **Trigger**: Alert `HighRequestLatency` fires when p99 request latency breaches `2.0s` for 5 consecutive minutes.
* **Potential Causes**:
  1. FAISS vector search or embedding model contention under high concurrent query load.
  2. MySQL connection pool exhaustion or unindexed table scan queries.
  3. External LLM API timeout (Gemini/Ollama).
* **Remediation Steps**:
  1. Inspect container CPU and memory saturation:
     ```powershell
     docker stats insurance-claims-api
     ```
  2. Check endpoint latency breakdown in Prometheus:
     ```promql
     histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, endpoint))
     ```
  3. If `/api/v1/rag/query` is causing the spike:
     - Verify if Redis / In-Memory semantic cache is active:
       ```powershell
       curl -s http://localhost:8000/api/v1/rag/cache-stats
       ```
     - If cache hit rate is low (< 20%), flush and warm cache.
  4. If database queries are slow, check MySQL active processlist:
     ```sql
     SHOW FULL PROCESSLIST;
     ```

---

### Playbook 3.2: HTTP 5xx Server Error Spike (`HighErrorRateSpike`)
* **Trigger**: Alert `HighErrorRateSpike` fires when HTTP 5xx errors exceed 5.0% of total traffic over a 2-minute rolling window.
* **Remediation Steps**:
  1. Tail production API container logs to isolate the exact traceback:
     ```powershell
     docker compose logs --tail=100 -f api
     ```
  2. Check correlation ID from incoming client headers (`x-request-id`) to trace failed transactions.
  3. If `503 Service Unavailable` is returned:
     - Check `/health/ready` to see which specific subsystem is failing:
       ```powershell
       curl -i http://localhost:8000/health/ready
       ```
     - If artifact missing or corrupt, reload models via service container restart:
       ```powershell
       docker compose restart api
       ```

---

### Playbook 3.3: Critical Model Drift & Automated Retraining Failure (`MLSubsystemDown` / Drift)
* **Trigger**: Automated drift audit detects $PSI \ge 0.25$ or model readiness flag drops to `0.0`.
* **Remediation Steps**:
  1. Run manual drift diagnostic audit:
     ```powershell
     .\venv\Scripts\python.exe scripts/run_drift_audit.py
     ```
  2. Inspect the generated Markdown briefing:
     ```powershell
     cat ml/reports/drift_report.md
     ```
  3. Verify staged candidate model in the Model Registry:
     ```powershell
     .\venv\Scripts\python.exe -c "from ml.model_registry.registry import model_registry; print(model_registry.list_models())"
     ```
  4. **Emergency Zero-Downtime Rollback Procedure**:
     If a newly promoted model misbehaves, revert to the previous archived version immediately:
     ```python
     from ml.model_registry.registry import model_registry, ModelStage
     # Rollback to known stable version 1.0.0
     model_registry.transition_stage(
         name="NLP Claim Domain Classifier",
         version="1.0.0",
         new_stage=ModelStage.PRODUCTION,
         notes="Emergency rollback triggered by SRE on-call due to precision degradation"
     )
     ```

---

### Playbook 3.4: Process Memory RSS Warning (`HighMemoryUtilization`)
* **Trigger**: Process memory consumption breaches `1.8 GB` (80% of Docker 2.25 GB limit).
* **Remediation Steps**:
  1. Inspect process memory consumption:
     ```powershell
     curl -s http://localhost:8000/api/v1/metrics/json | jq .data.memory_rss_mb
     ```
  2. Clear in-memory RAG query cache if cache size has grown unbounded:
     ```powershell
     curl -X POST http://localhost:8000/api/v1/rag/clear-cache
     ```
  3. Force garbage collection and thread inspection:
     ```powershell
     docker exec -it insurance-claims-api python -c "import gc; gc.collect(); print('GC Collected')"
     ```

---

### Playbook 3.5: FinOps Free-Tier Budget Tripwire Alert ($1.00 USD Breach)
* **Trigger**: AWS Budgets or CloudWatch billing alarm notifies email subscriber of forecasted spend > $0.80 or actual spend > $1.00.
* **Remediation Steps**:
  1. Immediately inspect active AWS resources via CLI:
     ```powershell
     aws ec2 describe-instances --filters "Name=instance-state-name,Values=running" --query "Reservations[*].Instances[*].[InstanceId,InstanceType]"
     ```
  2. Verify that EC2 instance is strictly `t2.micro` or `t3.micro`.
  3. Run the automated zero-cost infrastructure teardown script to eliminate billing risk:
     ```powershell
     .\venv\Scripts\python.exe scripts/destroy_infrastructure.py --confirm
     ```

---

## 4. Disaster Recovery (DR) & Backup Restoration

### 4.1 MySQL Database Backup & Restoration
* **Automated Daily Dump**:
  ```powershell
  docker exec insurance-claims-db mysqldump -u root -prootpassword insurance_warehouse > backups/warehouse_backup_$(Get-Date -Format 'yyyyMMdd').sql
  ```
* **Point-in-Time Recovery**:
  ```powershell
  docker exec -i insurance-claims-db mysql -u root -prootpassword insurance_warehouse < backups/warehouse_backup_YYYYMMDD.sql
  ```

### 4.2 Vector Store Index Restoration
* If `data/vector_store/faiss_policy_index.bin` becomes corrupted:
  ```powershell
  # Re-embed all 66 policy chunks from manifest
  .\venv\Scripts\python.exe rag_chatbot/vector_store/faiss_store.py
  ```

---

## 5. Deployment Verification Checklist

Before signing off on any production deployment:
- [ ] All 173 unit, integration, and platform tests pass (`pytest api/tests ml/tests rag_chatbot/tests etl/tests -q`).
- [ ] Liveness probe `/health/live` returns HTTP 200.
- [ ] Readiness probe `/health/ready` returns HTTP 200 with all 3 ML subsystems ready.
- [ ] Prometheus metrics `/metrics` is successfully scrapeable.
- [ ] Zero unhandled exception errors in container logs (`docker compose logs api`).
- [ ] Model registry confirms active production models with valid Git commit SHAs.
- [ ] AWS FinOps budget guardrail ($1.00) remains unbreached.
