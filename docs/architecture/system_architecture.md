# Insurance Claims Intelligence Platform (ICIP) — System Architecture

**Classification**: Tier-1 Platform Architecture Document  
**Version**: 1.0.0 (Final Capstone Release)  
**Author**: Uma (Senior / Staff Gen AI Platform Engineer)

---

## 1. High-Level Architecture Topology

```
+---------------------------------------------------------------------------------------------------------+
|                                  ICIP END-TO-END PLATFORM TOPOLOGY                                      |
+---------------------------------------------------------------------------------------------------------+
                                                                                                          
  [External Data Source]                                [AWS Cloud Landing Zone]                         
  +--------------------+                                +-----------------------------------------------+
  |  Mock Claims &     |   tenacity retries / 429 backoff|  Amazon S3 Bucket: raw-claims/                 |
  |  Policy REST API   | =============================> |  - AES-256 Server-Side Encryption             |
  |  (FastAPI :8001)   |                                |  - Strict S3 Public Access Block              |
  +--------------------+                                +-----------------------------------------------+
           |                                                                    |                         
           |                                                        ObjectCreated Event Notification      
           v                                                                    v                         
  +-------------------------------------+                       +-------------------------------+         
  | Resilient Ingestion Engine (ETL)    |                       | Serverless Lambda Ingestor    |         
  | - High-watermark incremental state  |                       | - Free-Tier 128MB Memory      |         
  | - Pydantic schema validation        |                       | - Idempotent S3 Read & Parse  |         
  | - Quarantine dead-letter rejection  |                       +-------------------------------+         
  +-------------------------------------+                                       |                         
           |                                                                    |                         
           +-----------------------------------+--------------------------------+                         
                                               |                                                          
                                               v                                                          
                                 +---------------------------+                                            
                                 |  MySQL 8.4 Warehouse      |                                            
                                 |  - BEFORE INSERT trigger  |                                            
                                 |  - AFTER UPDATE audit log |                                            
                                 |  - Covering indexes       |                                            
                                 |  - Kimball Star-Schema    |                                            
                                 +---------------------------+                                            
                                               |                                                          
                        +----------------------+----------------------+                                   
                        |                                             |                                   
                        v                                             v                                   
  +-----------------------------------------+   +-----------------------------------------------+         
  | Dual-Model ML Adjudication Engine       |   | Policy RAG Hybrid Knowledge Engine            |         
  | 1. TF-IDF + Balanced Logistic Regression|   | 1. Clause-Aware Semantic Chunker (66 Chunks)  |         
  |    - 7 Claim Classes (Auto to Travel)   |   | 2. Dual-Engine FAISS / NumPy Vector Store     |         
  |    - p50 Latency: 1.18ms                |   | 3. Okapi BM25 Lexical + Dense RRF Fusion      |         
  | 2. Unsupervised Isolation Forest        |   | 4. Cross-Encoder Context Reranker             |         
  |    - 10 Engineered Risk Features        |   | 5. Multi-tier LLM Synthesis (Gemini / Ollama) |         
  |    - ROC-AUC: 0.8349                    |   | 6. In-Memory LRU / TTL Semantic Cache         |         
  +-----------------------------------------+   +-----------------------------------------------+         
                        |                                             |                                   
                        +----------------------+----------------------+                                   
                                               |                                                          
                                               v                                                          
                                 +---------------------------+                                            
                                 | FastAPI Core Gateway      |                                            
                                 | - Pure ASGI Timing MW     |                                            
                                 | - Subsystem Probes        |                                            
                                 |   (/health/live, /ready)  |                                            
                                 | - Prometheus Exporter     |                                            
                                 |   (GET /metrics)          |                                            
                                 +---------------------------+                                            
                                               |                                                          
                        +----------------------+----------------------+                                   
                        |                                             |                                   
                        v                                             v                                   
  +-----------------------------------------+   +-----------------------------------------------+         
  | MLOps Governance & Drift Engine         |   | Columnar BI Reporting & Dashboards            |         
  | - Kolmogorov-Smirnov 2-sample test      |   | - 3-Page Executive Tabular Model              |         
  | - Continuous & Categorical PSI          |   | - 73.1% Snappy Parquet Compression            |         
  | - JSON Model Registry (4 Stages)        |   | - SHA-256 Cryptographic Manifests            |         
  | - Automated Retraining Candidate Trigger|   | - Interactive Standalone HTML Report Viewer   |         
  +-----------------------------------------+   +-----------------------------------------------+         
```

---

## 2. Component Subsystems & Design Specifications

### 2.1 Ingestion & Resilience Layer
* **Components**: `etl/extractor.py`, `etl/validator_and_cleanser.py`, `etl/run_pipeline.py`.
* **Resilience Pattern**: Exponential backoff retry via `tenacity` (`stop_after_attempt(5)`, `wait_exponential(multiplier=1, min=2, max=10)`) gracefully absorbing HTTP 429 rate-limiting from external carriers.
* **Dead-Letter Quarantine**: Non-conforming or corrupted claims (e.g. invalid dates, negative amounts) are routed into `claims_rejected` with detailed Pydantic error tracebacks, ensuring 100% data fidelity in the primary analytics tables.

### 2.2 Analytical Warehouse & Semantic Modeling Layer
* **Components**: `database/migrations/`, `powerbi/semantic_model.json`, `powerbi/snapshot_pipeline.py`.
* **Storage Engine**: MySQL 8.4 InnoDB with row-level locking and ACID compliance.
* **Indexing Strategy**: Composite covering index (`idx_claims_perf_covering` on `(status, is_fraud, claim_category, claim_amount, approved_amount)`) eliminating disk lookups for aggregate queries and reducing latency by **88.8%**.
* **Columnar Parquet Engine**: Exports Kimball fact and dimension views into Snappy-compressed Apache Parquet, shrinking storage from 1,066 KB down to 286 KB while enabling instantaneous predicate pushdown.

### 2.3 Machine Learning & Anomaly Scoring Layer
* **Components**: `ml/classification/`, `ml/anomaly_detection/`, `ml/drift_detector.py`, `ml/model_registry/`.
* **NLP Domain Classifier**: TF-IDF n-gram vectorizer (5,000 features) coupled with balanced Logistic Regression. Handles class imbalance (Auto 30.5% vs. Disability 5.2%) with sub-millisecond inference.
* **Isolation Forest Anomaly Engine**: 200 random isolation trees trained on 10 behavioral domain features. Flags high-risk fraud cases ($436$ incidents flagged, protecting **$69.6M** in payouts).
* **Statistical Drift Engine**: Evaluates production batches against reference baselines using two-sample KS tests and Population Stability Index (PSI). Automatically stages candidate models in `ModelStage.STAGING` upon detecting $PSI \ge 0.25$.

### 2.4 Generative AI & Policy RAG Retrieval Layer
* **Components**: `rag_chatbot/chunking/`, `rag_chatbot/vector_store/`, `rag_chatbot/retrieval/`, `api/app/routers/rag.py`.
* **Clause-Aware Chunker**: Ingests official policy contracts, respecting section headings, sub-clauses, and exclusions while injecting breadcrumb metadata (e.g., `Auto > Comprehensive Coverage > Glass Deductibles`).
* **Hybrid Search with RRF**: Combines Okapi BM25 keyword matching with FAISS L2-normalized dense embeddings ($k=60$).
* **Cross-Encoder Reranker**: Filters and re-ranks top-$k$ candidate clauses, injecting structured markdown citations (`[Section 4.2: Deductibles]`) into multi-tier LLM generation (Google Gemini API with local Ollama fallback).

### 2.5 Cloud Infrastructure & FinOps Guardrails
* **Components**: `infrastructure/terraform/`, `infrastructure/cloudformation/`, `monitoring/alerts/`.
* **Terraform IaC**: Declarative provisioning of AWS S3, least-privilege IAM roles, EC2 `t2.micro` instances, and serverless Lambda ingestion.
* **FinOps Protection**: $1.00 USD monthly budget tripwire (`aws_budgets_budget`) with automated email alerts at 80% forecasted and 100% actual spend, ensuring ₹0 budget compliance.
