"""
Unit Tests for Dockerfile and Container Specifications (ICIP-019).
Verifies multi-stage build definitions, non-root user enforcement, and healthcheck syntax.
"""

from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DOCKERFILE_PATH = PROJECT_ROOT / "Dockerfile"
DOCKERIGNORE_PATH = PROJECT_ROOT / ".dockerignore"


class TestDockerConfiguration:
    """Automated test assertions for container packaging and security."""

    def test_dockerfile_exists_and_uses_multistage(self):
        assert DOCKERFILE_PATH.is_file(), "Dockerfile must exist at repository root"
        content = DOCKERFILE_PATH.read_text(encoding="utf-8")
        assert "FROM python:3.12-slim AS builder" in content
        assert "FROM python:3.12-slim AS runner" in content
        assert "COPY --from=builder" in content

    def test_dockerfile_enforces_non_root_execution(self):
        content = DOCKERFILE_PATH.read_text(encoding="utf-8")
        assert "useradd" in content
        assert "groupadd" in content
        assert "USER appuser" in content
        assert "--chown=appuser:appgroup" in content

    def test_dockerfile_declares_healthcheck(self):
        content = DOCKERFILE_PATH.read_text(encoding="utf-8")
        assert "HEALTHCHECK" in content
        assert "curl -f http://localhost:8000/api/v1/health" in content

    def test_dockerignore_excludes_heavy_and_sensitive_directories(self):
        assert DOCKERIGNORE_PATH.is_file(), ".dockerignore must exist at repository root"
        content = DOCKERIGNORE_PATH.read_text(encoding="utf-8")
        lines = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")]
        
        assert ".git" in lines
        assert "venv/" in lines
        assert "__pycache__/" in lines
        assert ".pytest_cache/" in lines
        assert "tests/" in lines
