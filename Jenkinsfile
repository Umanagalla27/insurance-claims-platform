// =============================================================================
// Jenkinsfile — Enterprise Declarative CI/CD Pipeline
// Project: Insurance Claims Intelligence Platform (ICIP)
// =============================================================================
// ARCHITECTURAL RATIONALE: WHY BOTH GITHUB ACTIONS AND JENKINS EXIST
// -----------------------------------------------------------------------------
// In top-tier financial technology, insurance, and healthcare enterprises:
//   1. GitHub Actions is deployed for cloud-native product engineering teams:
//      fast feedback loops on pull requests, managed runners, and SaaS agility.
//   2. Jenkins is mandated for internal enterprise data centers, hybrid clouds,
//      and air-gapped VPCs (AWS Outposts, private OpenShift clusters):
//      - Regulatory Compliance (HIPAA, GLBA, ISO 27001): Sensitive insurance
//        claim histories and proprietary actuarial models cannot traverse public
//        cloud SaaS runners.
//      - Custom On-Premise Worker Nodes: Jenkins runs on bare-metal agents with
//        direct hardware access, private HSM key management, and internal LDAP/SAML.
//      - Controlled Artifact Deployment: Regulated deployment gates requiring
//        multi-signature approval and change advisory board (CAB) audit logs.
// =============================================================================

pipeline {
    agent any

    options {
        timeout(time: 30, unit: 'MINUTES')
        timestamps()
        ansiColor('xterm')
        disableConcurrentBuilds()
    }

    environment {
        APP_NAME = 'insurance-claims-platform'
        IMAGE_NAME = 'insurance-claims-api'
        IMAGE_TAG = "${env.BUILD_NUMBER ?: 'latest'}"
        PYTHON_VERSION = '3.12'
        REPORTS_DIR = 'reports'
        VENV_DIR = '.jenkins_venv'
        ENV = 'testing'
        DEBUG = 'false'
        ENABLE_EXTERNAL_LLM = 'false'
    }

    stages {
        // ---------------------------------------------------------------------
        // Stage 1: Source Control Checkout
        // ---------------------------------------------------------------------
        stage('Checkout SCM') {
            steps {
                echo "Checking out repository source code from Git..."
                checkout scm
                sh 'git log -1 --pretty=format:"Commit: %h by %an, %ar - %s"'
            }
        }

        // ---------------------------------------------------------------------
        // Stage 2: Virtual Environment Setup & Dependencies
        // ---------------------------------------------------------------------
        stage('Setup Dependencies') {
            steps {
                echo "Configuring Python ${PYTHON_VERSION} isolated virtual environment..."
                sh '''
                    python3 -m venv ${VENV_DIR}
                    . ${VENV_DIR}/bin/activate
                    pip install --upgrade pip setuptools wheel
                    pip install -r requirements.txt -r requirements-dev.txt
                '''
            }
        }

        // ---------------------------------------------------------------------
        // Stage 3: Static Code Analysis & Formatting Gate
        // ---------------------------------------------------------------------
        stage('Lint & Static Analysis') {
            steps {
                echo "Executing Ruff static analysis and formatting audit..."
                sh '''
                    . ${VENV_DIR}/bin/activate
                    ruff check .
                    ruff format --check .
                '''
            }
        }

        // ---------------------------------------------------------------------
        // Stage 4: Automated Testing & Coverage
        // ---------------------------------------------------------------------
        stage('Unit & Regression Tests') {
            steps {
                echo "Running complete 81-test platform regression suite..."
                sh '''
                    . ${VENV_DIR}/bin/activate
                    mkdir -p ${REPORTS_DIR}
                    pytest -v api/tests/ rag_chatbot/tests/ ml/tests/ \
                        --junitxml=${REPORTS_DIR}/junit-results.xml \
                        --cov=api --cov=ml --cov=rag_chatbot \
                        --cov-report=xml:${REPORTS_DIR}/coverage.xml \
                        --cov-report=term-missing
                '''
            }
        }

        // ---------------------------------------------------------------------
        // Stage 5: Container Packaging & Docker Audit
        // ---------------------------------------------------------------------
        stage('Docker Multi-Stage Build') {
            steps {
                echo "Building hardened production Docker image: ${IMAGE_NAME}:${IMAGE_TAG}..."
                sh '''
                    . ${VENV_DIR}/bin/activate
                    python scripts/verify_docker_setup.py
                    python scripts/verify_docker_compose.py
                    docker build -t ${IMAGE_NAME}:${IMAGE_TAG} -t ${IMAGE_NAME}:latest .
                '''
            }
        }

        // ---------------------------------------------------------------------
        // Stage 6: Container Security Audit
        // ---------------------------------------------------------------------
        stage('Container Security Scan') {
            steps {
                echo "Auditing container non-root enforcement (UID 10001)..."
                sh '''
                    grep -q "USER appuser" Dockerfile || (echo "SECURITY VIOLATION: Root user detected!" && exit 1)
                    grep -q "HEALTHCHECK" Dockerfile || (echo "SECURITY VIOLATION: Missing HEALTHCHECK probe!" && exit 1)
                    echo "Container security verification: PASSED"
                '''
            }
        }
    }

    post {
        always {
            echo "Publishing test results and cleaning up workspace..."
            junit testResults: 'reports/junit-results.xml', allowEmptyResults: true
            archiveArtifacts artifacts: 'reports/coverage.xml,Dockerfile,docker-compose.yml', fingerprint: true, allowEmptyArchive: true
            deleteDir() // Clean up Jenkins workspace to protect agent disk space
        }
        success {
            echo "CI/CD Pipeline SUCCESS: Build #${env.BUILD_NUMBER} passed all quality and security gates."
        }
        failure {
            echo "CI/CD Pipeline FAILED: Build #${env.BUILD_NUMBER} failed. Immediate developer triage required."
        }
    }
}
