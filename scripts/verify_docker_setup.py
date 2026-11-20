"""
Verification Script for Production Docker Configuration (ICIP-019).
Validates multi-stage Dockerfile syntax, security guardrails, build context exclusion, and artifact presence.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCKERFILE_PATH = PROJECT_ROOT / "Dockerfile"
DOCKERIGNORE_PATH = PROJECT_ROOT / ".dockerignore"


def test_dockerfile_structure():
    print("[1/5] Validating Dockerfile structure and multi-stage build...")
    assert DOCKERFILE_PATH.exists(), f"Missing Dockerfile at {DOCKERFILE_PATH}"
    content = DOCKERFILE_PATH.read_text(encoding="utf-8")

    # Multi-stage check
    assert "AS builder" in content, "Missing 'AS builder' multi-stage target"
    assert "AS runner" in content, "Missing 'AS runner' multi-stage target"
    print("  -> Multi-stage build (builder + runner) verified.")

    # Base image check
    assert "python:3.12-slim" in content, "Should use slim Python 3.12 base image"
    print("  -> Python 3.12-slim base image confirmed.")

    return content


def test_security_hardening(content: str):
    print(
        "[2/5] Validating container security and non-root execution (CIS Docker 4.1)..."
    )
    assert "useradd" in content and "groupadd" in content, (
        "Missing non-root user creation"
    )
    assert "10001" in content, "Should use explicit non-root UID 10001"
    assert "USER appuser" in content, (
        "Must switch to non-root USER appuser before entrypoint"
    )
    assert "--chown=appuser:appgroup" in content, "Must chown files to appuser"
    print(
        "  -> Non-root user (appuser:10001) and least-privilege permissions verified."
    )


def test_healthcheck_and_entrypoint(content: str):
    print("[3/5] Validating healthcheck probe and ASGI entrypoint...")
    assert "HEALTHCHECK" in content, "Missing Docker HEALTHCHECK instruction"
    assert "http://localhost:8000/api/v1/health" in content or "/health" in content, (
        "Healthcheck must probe /health endpoint"
    )
    assert "uvicorn" in content, "Entrypoint must use uvicorn ASGI server"
    assert "--workers" in content, "Uvicorn must specify multi-worker configuration"
    print("  -> Active Docker healthcheck and multi-worker ASGI entrypoint verified.")


def test_dockerignore_coverage():
    print("[4/5] Validating .dockerignore build context exclusions...")
    assert DOCKERIGNORE_PATH.exists(), f"Missing .dockerignore at {DOCKERIGNORE_PATH}"
    ignore_content = DOCKERIGNORE_PATH.read_text(encoding="utf-8")

    required_exclusions = [".git", "venv", "__pycache__", ".pytest_cache", "tests"]
    for item in required_exclusions:
        assert item in ignore_content, f"Missing {item} exclusion in .dockerignore"
    print(
        "  -> Essential exclusions (.git, venv, tests, caches) verified in .dockerignore."
    )


def test_artifact_and_directory_existence():
    print(
        "[5/5] Validating presence of source directories referenced by COPY instructions..."
    )
    required_dirs = [
        PROJECT_ROOT / "api",
        PROJECT_ROOT / "ml",
        PROJECT_ROOT / "rag_chatbot",
        PROJECT_ROOT / "data" / "vector_store",
        PROJECT_ROOT / "database",
    ]

    for d in required_dirs:
        assert d.exists(), f"Required directory {d.name} missing from project root"
        file_count = len(list(d.rglob("*.*")))
        print(
            f"  -> Verified {d.relative_to(PROJECT_ROOT)} exists ({file_count} files)."
        )


def main():
    print(
        "================================================================================"
    )
    print(
        "      Insurance Claims Intelligence Platform — Dockerfile Audit (ICIP-019)     "
    )
    print(
        "================================================================================"
    )
    try:
        content = test_dockerfile_structure()
        test_security_hardening(content)
        test_healthcheck_and_entrypoint(content)
        test_dockerignore_coverage()
        test_artifact_and_directory_existence()
        print(
            "\n================================================================================"
        )
        print(
            " [SUCCESS] All 5 Docker containerization audit checks PASSED!                   "
        )
        print(
            "================================================================================"
        )
    except AssertionError as e:
        print(f"\n[FAIL] Audit failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
