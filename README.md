# Insurance Claims Intelligence Platform

> **Built by Uma** | Gen AI Engineer Portfolio Project

## 🏢 What is this?

An end-to-end data + AI platform simulating real insurance IT services work.
It ingests claims data from an external system, runs ML classification and anomaly
detection, exposes predictions via a REST API, and provides a Gen AI chatbot
for policy Q&A — all deployed on AWS with CI/CD.

## 🏗️ Architecture

```
External Mock API → ETL Pipeline → MySQL Database → ML Models → REST API → AWS EC2
                                        ↓
                               Power BI Dashboards
                                        ↓
                          RAG Chatbot (Gemini + FAISS)
```

## 🚀 Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/insurance-claims-platform.git
cd insurance-claims-platform

# 2. Create virtual environment and install dependencies
python -m venv venv
.\venv\Scripts\Activate.ps1        # Windows
pip install -r requirements.txt -r requirements-dev.txt

# 3. Set up environment variables
copy .env.example .env
# Edit .env with your values

# 4. Start services with Docker
docker compose --profile core up -d

# 5. Run the ETL pipeline
python etl/run_etl.py

# 6. Access the API
# API docs: http://localhost:8000/docs
# Mock API docs: http://localhost:8001/docs
```

## 📁 Project Structure

| Folder | Purpose |
|--------|---------|
| `mock_api/` | Simulated external claims system API |
| `data_generator/` | Synthetic data generation scripts |
| `etl/` | Extract-Transform-Load pipeline |
| `database/` | MySQL schema, stored procedures, views |
| `ml/` | Classification + anomaly detection models |
| `rag_chatbot/` | LLM chatbot with RAG over policy docs |
| `api/` | Main REST API (FastAPI) |
| `infrastructure/` | Terraform + CloudFormation IaC |
| `jenkins/` | Jenkins CI/CD pipeline |
| `powerbi/` | Power BI dashboard files |
| `monitoring/` | Logging, alerts, incident simulation |
| `docs/` | Architecture, design, runbook, KT docs |

## 🛠️ Tech Stack

**Backend**: Python 3.12, FastAPI, SQLAlchemy, MySQL 8
**ML**: scikit-learn (TF-IDF, LogReg, Isolation Forest), FAISS
**Gen AI**: Google Gemini API, Ollama (local), sentence-transformers
**Infra**: Docker, AWS (EC2, S3, Lambda), Terraform, CloudFormation
**CI/CD**: GitHub Actions, Jenkins
**Reporting**: Power BI, MySQL Views

## 📊 Key Features

- ✅ Incremental ETL with idempotency and error handling
- ✅ Text classification of claim descriptions (category + priority)
- ✅ Anomaly detection for suspicious claims (Isolation Forest)
- ✅ RAG chatbot for policy document Q&A
- ✅ REST API with authentication and Pydantic validation
- ✅ Full CI/CD pipeline (GitHub Actions + Jenkins)
- ✅ AWS deployment with IaC (Terraform + CloudFormation)
- ✅ Audit trail via MySQL triggers
- ✅ Power BI self-service dashboards

## 📝 Documentation

- [Architecture Diagram](docs/architecture/architecture_diagram.md)
- [Technical Design Doc](docs/design/technical_design_doc.md)
- [Deployment Guide](docs/deployment_guide.md)
- [Runbook](docs/runbook.md)
- [KT Document](docs/kt_document.md)

## 🧪 Running Tests

```bash
# All tests
pytest -v

# With coverage
pytest --cov=. --cov-report=term-missing
```

## 👩‍💻 Author

**Uma** — Gen AI Engineer in training
- GitHub: [@YOUR_USERNAME](https://github.com/YOUR_USERNAME)
- LinkedIn: [your-linkedin](https://linkedin.com)

---
*This is a portfolio project using 100% synthetic data. No real customer data is used.*
