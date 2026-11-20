"""
Verification and Audit Script for CI/CD Pipelines (ICIP-021).
Validates GitHub Actions YAML workflow structure and Jenkinsfile declarative syntax.
"""

import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GHA_WORKFLOW_FILE = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"
JENKINSFILE = PROJECT_ROOT / "Jenkinsfile"


def audit_github_actions():
    print("[1/2] Auditing GitHub Actions Workflow (.github/workflows/ci.yml)...")
    assert GHA_WORKFLOW_FILE.is_file(), f"Missing {GHA_WORKFLOW_FILE}"

    with open(GHA_WORKFLOW_FILE, encoding="utf-8") as f:
        workflow = yaml.safe_load(f)

    # 1. Triggers
    assert "on" in workflow, "Missing 'on' triggers in GitHub Actions workflow"
    triggers = workflow["on"]
    assert "push" in triggers and "pull_request" in triggers, (
        "Workflow must trigger on push and pull_request"
    )
    print("  -> Triggers (push, pull_request) verified.")

    # 2. Jobs
    assert "jobs" in workflow, "Missing 'jobs' in GitHub Actions workflow"
    jobs = workflow["jobs"]
    required_jobs = ["lint", "test", "docker-build-and-audit"]
    for j in required_jobs:
        assert j in jobs, f"Missing required job '{j}'"
    print(f"  -> Found all required jobs: {list(jobs.keys())}")

    # 3. Pipeline Job Dependencies (Stage Gates)
    assert jobs["test"].get("needs") == ["lint"], (
        "'test' job must declare 'needs: [lint]'"
    )
    assert jobs["docker-build-and-audit"].get("needs") == ["test"], (
        "'docker-build-and-audit' must declare 'needs: [test]'"
    )
    print(
        "  -> Staged pipeline fail-fast dependencies (lint -> test -> docker) verified."
    )

    # 4. Job Step Contents
    lint_steps_text = str(jobs["lint"].get("steps", []))
    assert "ruff check" in lint_steps_text, "Lint job must execute 'ruff check'"
    assert "ruff format --check" in lint_steps_text, (
        "Lint job must execute 'ruff format --check'"
    )

    test_steps_text = str(jobs["test"].get("steps", []))
    assert "pytest" in test_steps_text, "Test job must execute 'pytest'"
    assert "--junitxml" in test_steps_text, "Test job must produce JUnit test reports"

    docker_steps_text = str(jobs["docker-build-and-audit"].get("steps", []))
    assert (
        "docker/build-push-action" in docker_steps_text
        or "docker build" in docker_steps_text
    ), "Docker job must build container image"
    print(
        "  -> Core execution steps (Ruff, Pytest, Docker build) verified in GitHub Actions."
    )


def audit_jenkinsfile():
    print("[2/2] Auditing Enterprise Declarative Jenkinsfile...")
    assert JENKINSFILE.is_file(), f"Missing {JENKINSFILE}"
    content = JENKINSFILE.read_text(encoding="utf-8")

    # 1. Declarative Structure
    assert "pipeline {" in content, (
        "Jenkinsfile must be a declarative pipeline ('pipeline { ... }')"
    )
    assert "agent any" in content or "agent {" in content, (
        "Jenkinsfile must declare an agent"
    )
    assert "stages {" in content, "Jenkinsfile must declare 'stages { ... }'"
    assert "post {" in content, (
        "Jenkinsfile must declare 'post { ... }' lifecycle actions"
    )
    print("  -> Declarative pipeline syntax and blocks verified.")

    # 2. Required Stages
    required_stages = [
        "Checkout SCM",
        "Setup Dependencies",
        "Lint & Static Analysis",
        "Unit & Regression Tests",
        "Docker Multi-Stage Build",
        "Container Security Scan",
    ]
    for stage_name in required_stages:
        assert f"stage('{stage_name}')" in content, (
            f"Missing stage '{stage_name}' in Jenkinsfile"
        )
    print(f"  -> All {len(required_stages)} production Jenkins stages verified.")

    # 3. Execution Commands & Reporting
    assert "ruff check ." in content, "Jenkinsfile must execute ruff check"
    assert "pytest" in content, "Jenkinsfile must execute pytest"
    assert "docker build" in content, "Jenkinsfile must execute docker build"
    assert "junit" in content, "Jenkinsfile post block must publish JUnit test results"
    assert "deleteDir()" in content, "Jenkinsfile post block must clean workspace"
    print(
        "  -> Jenkins toolchain execution, JUnit reporting, and workspace cleanup verified."
    )


def main():
    print(
        "================================================================================"
    )
    print(
        "      Insurance Claims Intelligence Platform — CI/CD Pipeline Audit (ICIP-021)  "
    )
    print(
        "================================================================================"
    )
    try:
        audit_github_actions()
        audit_jenkinsfile()
        print(
            "\n================================================================================"
        )
        print(
            " [SUCCESS] Both GitHub Actions and Jenkinsfile CI/CD pipelines PASSED audit!    "
        )
        print(
            "================================================================================"
        )
    except AssertionError as e:
        print(f"\n[FAIL] Audit failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
