# ============================================================
# Makefile — Shortcut commands for the project
# ============================================================
# Usage:  make <target>
# Example: make setup    →  Creates conda env and installs dependencies
#
# ENVIRONMENT STRATEGY:
#   Local dev  → conda environment (insurance-claims)
#   Docker/CI  → standard pip in container (no conda in production)
#   Why conda? Machine has Anaconda; conda envs are properly isolated
#               on Windows unlike venv+Anaconda combos.
#
# Windows Note: Use "make" after installing it via:
#   winget install GnuWin32.Make
#   OR: just run the commands manually in PowerShell.
# ============================================================

.PHONY: setup install install-dev lint format type-check test test-cov \
        up down up-db run-etl run-api run-mock-api clean help

# ----- Setup -----
setup:
	@echo "Creating conda environment: insurance-claims (Python 3.13)"
	conda create -n insurance-claims python=3.13 -y
	@echo "Installing all dependencies into conda env..."
	conda run -n insurance-claims pip install -r requirements.txt -r requirements-dev.txt
	@echo "Copying .env.example to .env (fill in your values)..."
	if not exist .env copy .env.example .env
	@echo "✅ Setup complete!"
	@echo "Activate with: conda activate insurance-claims"

install:
	# Install production dependencies only
	pip install -r requirements.txt

install-dev:
	# Install all dependencies (prod + dev)
	pip install -r requirements.txt -r requirements-dev.txt

# ----- Code Quality -----
lint:
	# Check for code style issues (does not fix)
	ruff check .

format:
	# Auto-fix formatting issues
	ruff format .
	ruff check . --fix

type-check:
	# Static type checking
	mypy . --ignore-missing-imports

# ----- Testing -----
test:
	# Run all tests (fast, no coverage)
	pytest tests/ -v

test-cov:
	# Run tests with coverage report
	pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html
	@echo "Coverage HTML report at: htmlcov/index.html"

test-module:
	# Run tests for a specific module: make test-module MODULE=etl
	pytest $(MODULE)/tests/ -v

# ----- Docker -----
up:
	# Start core services: MySQL + Mock API + Main API
	docker compose --profile core up -d
	@echo "✅ Services running. API: http://localhost:8000, Mock API: http://localhost:8001"

up-db:
	# Start ONLY MySQL (useful during ETL development)
	docker compose up mysql -d

up-all:
	# Start ALL services including Jenkins (needs more RAM)
	docker compose --profile all up -d

down:
	# Stop all running containers
	docker compose down

down-volumes:
	# Stop all containers AND delete data volumes (fresh start)
	docker compose down -v
	@echo "⚠️  All database data deleted!"

logs:
	# Follow logs from all containers
	docker compose logs -f

# ----- Application -----
run-mock-api:
	# Start the Mock External Claims API (without Docker)
	cd mock_api && uvicorn app.main:app --reload --port 8001

run-api:
	# Start the main API (without Docker)
	cd api && uvicorn app.main:app --reload --port 8000

run-etl:
	# Run the ETL pipeline once
	python etl/run_etl.py

# ----- Data -----
generate-data:
	# Generate synthetic claims data
	python data_generator/generate_claims.py
	python data_generator/generate_policies.py
	python data_generator/generate_customers.py

# ----- ML -----
train-classifier:
	python ml/classification/train.py

train-anomaly:
	python ml/anomaly_detection/train.py

# ----- Cleanup -----
clean:
	# Remove all Python cache files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -name ".coverage" -delete
	@echo "✅ Cleaned up cache files"

# ----- Help -----
help:
	@echo ""
	@echo "Insurance Claims Intelligence Platform — Makefile Commands"
	@echo "==========================================================="
	@echo "  make setup           Create venv + install all deps"
	@echo "  make lint            Check code style"
	@echo "  make format          Auto-fix code style"
	@echo "  make test            Run all tests"
	@echo "  make test-cov        Tests + coverage report"
	@echo "  make up              Start core Docker services"
	@echo "  make up-db           Start MySQL only"
	@echo "  make down            Stop all Docker services"
	@echo "  make run-mock-api    Start Mock API (port 8001)"
	@echo "  make run-api         Start Main API (port 8000)"
	@echo "  make run-etl         Run ETL pipeline once"
	@echo "  make generate-data   Generate synthetic test data"
	@echo "  make clean           Remove Python cache files"
	@echo ""
