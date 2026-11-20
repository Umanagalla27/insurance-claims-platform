# ==============================================================================
# Dockerfile — Production Multi-Stage Containerization
# Project: Insurance Claims Intelligence Platform (ICIP)
# ==============================================================================
# Security & Performance Standards:
#   1. Multi-Stage Build: Compiles C-extensions in builder stage; discards toolchains.
#   2. Least-Privilege Execution: Runs as non-root user (appuser, UID 10001).
#   3. Minimal Surface Area: Base image python:3.12-slim (<150MB OS footprint).
#   4. Active Healthcheck: Native Docker probe querying /api/v1/health.
#   5. High-Throughput ASGI: Uvicorn multi-worker process management.
# ==============================================================================

# ------------------------------------------------------------------------------
# STAGE 1: Builder (Dependency Compilation & Virtual Environment Isolation)
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install minimal compilation toolchains for native wheels (cryptography, numpy)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create isolated Python virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install production dependencies
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt


# ------------------------------------------------------------------------------
# STAGE 2: Runtime (Hardened Lean Production Image)
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS runner

# Build metadata
LABEL maintainer="Uma <uma@insurance-intelligence.internal>" \
      project="insurance-claims-intelligence-platform" \
      version="1.0.0" \
      description="Production API Gateway for Claims Intelligence & Policy RAG"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8000 \
    ENV=production

# Install only essential runtime packages (curl for healthcheck, ca-certificates for TLS)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Security Hardening: Create non-root system user and group (CIS Docker 4.1)
RUN groupadd -r -g 10001 appgroup && \
    useradd -r -u 10001 -g appgroup -s /sbin/nologin -d /app appuser

WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder --chown=appuser:appgroup /opt/venv /opt/venv

# Copy application source code and pre-trained model/RAG artifacts
COPY --chown=appuser:appgroup api /app/api
COPY --chown=appuser:appgroup ml /app/ml
COPY --chown=appuser:appgroup rag_chatbot /app/rag_chatbot
COPY --chown=appuser:appgroup data/vector_store /app/data/vector_store
COPY --chown=appuser:appgroup database /app/database

# Drop all root privileges
USER appuser

# Expose internal listening port
EXPOSE 8000

# Docker Native Healthcheck Probe (fails container if /health fails 3 times)
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Launch ASGI server with production concurrency
CMD ["uvicorn", "api.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--timeout-keep-alive", "30"]
