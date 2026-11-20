"""
Automated Pytest Suite for CI/CD Pipelines (ICIP-021).
Asserts that GitHub Actions workflows and Jenkinsfile conform to enterprise CI/CD standards.
"""

from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
GHA_PATH = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"
JENKINS_PATH = PROJECT_ROOT / "Jenkinsfile"


class TestCIPipelineSpecifications:
    """Test suite validating GitHub Actions and Jenkinsfile definitions."""

    def test_github_actions_workflow_registered_jobs(self):
        assert GHA_PATH.is_file(), ".github/workflows/ci.yml must exist"
        with open(GHA_PATH, encoding="utf-8") as f:
            workflow = yaml.safe_load(f)

        assert "jobs" in workflow
        jobs = workflow["jobs"]
        assert "lint" in jobs
        assert "test" in jobs
        assert "docker-build-and-audit" in jobs

    def test_github_actions_staged_dependencies(self):
        with open(GHA_PATH, encoding="utf-8") as f:
            workflow = yaml.safe_load(f)

        jobs = workflow["jobs"]
        assert jobs["test"].get("needs") == ["lint"]
        assert jobs["docker-build-and-audit"].get("needs") == ["test"]

    def test_jenkinsfile_declarative_syntax(self):
        assert JENKINS_PATH.is_file(), "Jenkinsfile must exist at project root"
        content = JENKINS_PATH.read_text(encoding="utf-8")

        assert "pipeline {" in content
        assert "agent any" in content or "agent {" in content
        assert "stages {" in content
        assert "post {" in content

    def test_jenkinsfile_contains_quality_gates(self):
        content = JENKINS_PATH.read_text(encoding="utf-8")

        assert "stage('Lint & Static Analysis')" in content
        assert "stage('Unit & Regression Tests')" in content
        assert "stage('Docker Multi-Stage Build')" in content
        assert "stage('Container Security Scan')" in content
        assert "junit" in content
