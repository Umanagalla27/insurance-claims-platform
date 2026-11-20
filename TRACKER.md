# TRACKER.md — Insurance Claims Intelligence Platform
# ============================================================
# Update this file after EVERY step you complete.
# Format: | Sprint | Step | JIRA ID | What was done | Status | Date |
# ============================================================

| Sprint | Step | JIRA ID | What was done | Status | Date |
|--------|------|---------|---------------|--------|------|
| Sprint 0 | 0.1 | — | Project kickoff: clarifying questions, roadmap confirmed, tech stack decisions made | ✅ Done | 2026-11-19 |
| Sprint 1 | 1.1 | ICIP-001 | Repo initialized: 58 dirs, Python 3.12 clean venv, requirements.txt, .gitignore, .env.example, Makefile, ruff.toml, pytest.ini, README, verify_setup.py | ✅ Done | 2026-11-19 |
| Sprint 1 | 1.2 | ICIP-002 | Synthetic data generation: 10,300 claims, 800 policies, 515 customers with realistic messiness & fraud patterns | ✅ Done | 2026-11-19 |
| Sprint 1 | 1.3 | ICIP-003 | Mock External Policy & Claims API: FastAPI, auth, pagination, rate limiting & error simulation (13/13 tests pass) | ✅ Done | 2026-11-19 |
| Sprint 2 | 2.1 | ICIP-004 | Resilient API Extractor: tenacity exponential backoff retries, rate-limiting (429) handler, incremental high-watermark state manager (5/5 tests pass) | ✅ Done | 2026-11-19 |
| Sprint 2 | 2.2 | ICIP-005 | Data Validation, Cleansing & Quarantine Engine: Pydantic + pandas pipeline, dead-letter reject table (9,107 clean vs 1,193 quarantined claims, 10/10 tests pass) | ✅ Done | 2026-11-19 |
| Sprint 2 | 2.3 | ICIP-006 | End-to-End Ingestion Runner & Staging Generator: CLI orchestration, Before-vs-After quality reports, staged warehouse CSVs (12/12 tests pass) | ✅ Done | 2026-11-19 |
| Sprint 3 | 3.1 | ICIP-007 | MySQL Data Warehouse: Docker Compose setup (1GB memory guardrail), production DDL schema, idempotent bulk loader (3/3 tests pass) | ✅ Done | 2026-11-19 |
| Sprint 3 | 3.2 | ICIP-008 | Stored Procedures & Audit Triggers: AFTER UPDATE audit trigger, BEFORE INSERT validation (SIGNAL '45000'), payout function & batch adjudication SP (7/7 tests pass) | ✅ Done | 2026-11-19 |
| Sprint 3 | 3.3 | ICIP-009 | SQL Performance Tuning & Star-Schema Reporting Views: composite covering indexes (8.94x speedup / 88.8% latency reduction), 3 Power BI analytical views (11/11 tests pass) | ✅ Done | 2026-11-19 |
| Sprint 4 | 4.1 | ICIP-010 | NLP Text Classification: Data preprocessing, TF-IDF vectorization, class imbalance handling & baseline classifier (14/14 tests pass, p50=1.18ms latency) | ✅ Done | 2026-11-20 |
| Sprint 4 | 4.2 | ICIP-011 | Advanced Evaluation & Error Analysis: 7x7 confusion matrix, OvR ROC-AUC, feature importance & boundary stress testing (20/20 tests pass) | ✅ Done | 2026-11-20 |
| Sprint 4 | 4.3 | ICIP-012 | Anomaly & Fraud Detection with Isolation Forest: 10-feature unsupervised risk scoring (ROC-AUC: 0.835), 0-100 risk calibrator & explainable risk factors (28/28 tests pass) | ✅ Done | 2026-11-20 |
| Sprint 5 | 5.1 | ICIP-013 | Policy Document Ingestion & Semantic Chunking: 7 policy contracts, clause-aware chunker with contextual breadcrumbs (66 chunks, 33/33 tests pass) | ✅ Done | 2026-11-20 |
| Sprint 5 | 5.2 | ICIP-014 | Vector Embeddings & FAISS Vector Store: Dense semantic indexing, dual-mode FAISS/NumPy engine & metadata filtering (39/39 tests pass) | ✅ Done | 2026-11-20 |
| Sprint 5 | 5.3 | ICIP-015 | Hybrid Search & BM25 / Reranking: Reciprocal Rank Fusion (RRF), Okapi BM25 & Context Reranker with Markdown citations (48/48 tests pass) | ✅ Done | 2026-11-20 |
| Sprint 6 | 6.1 | ICIP-016 | FastAPI Core Architecture & Service Integration: Dependency injection, pure ASGI timing middleware, Pydantic v2 schemas & unified platform gateway (58/58 tests pass) | ✅ Done | 2026-11-20 |
| Sprint 6 | 6.2 | ICIP-017 | Claims Processing & ML Prediction Endpoints: POST /api/v1/claims/analyze multi-model adjudication & explainability (64/64 tests pass) | ✅ Done | 2026-11-20 |
| Sprint 6 | 6.3 | ICIP-018 | Policy RAG Chatbot Endpoint & In-Memory/Redis Caching: Grounded policy queries, citation assembly & cache invalidation (71/71 tests pass) | ✅ Done | 2026-11-20 |
| Sprint 7 | 7.1 | ICIP-019 | Multi-Stage Dockerfile & Container Optimization: Multi-stage build, non-root user (10001), slim Python 3.12, healthchecks & .dockerignore (75/75 tests pass) | ✅ Done | 2026-11-20 |
| Sprint 7 | 7.2 | ICIP-020 | Multi-Service Docker Compose Orchestration: API, MySQL 8.4, Redis, healthcheck dependencies & network isolation (81/81 tests pass) | ✅ Done | 2026-11-20 |
| Sprint 7 | 7.3 | ICIP-021 | Automated CI/CD Pipelines: GitHub Actions & Jenkinsfile for lint, test, container build & push (85/85 tests pass) | ✅ Done | 2026-11-20 |
| Sprint 8 | 8.1 | ICIP-022 | AWS Infrastructure as Code (IaC) with Terraform: Free-Tier S3, IAM roles, security groups & EC2 t2.micro provisioner (90/90 tests pass) | ✅ Done | 2026-11-20 |
| Sprint 8 | 8.2 | ICIP-023 | Event-Driven Serverless ETL Architecture: AWS Lambda ingestion trigger, S3 event notifications & IAM least-privilege role | 🔜 Next | — |

<!-- 
Key decisions logged:
- Python 3.12.6 from C:\Python312 (clean venv, isolated from Anaconda)
- Conda `insurance-claims` env also available but using venv for this project
- ruff v0.17.5 (actual installed), pytest v9.2.0 (actual installed)
- Heavy ML/RAG deps (faiss, sentence-transformers) will be installed in Sprint 4-5
-->
