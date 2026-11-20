#!/usr/bin/env bash
# ==============================================================================
# scripts/destroy_infrastructure.sh — Bash Wrapper for FinOps Teardown Guardrail
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== Insurance Claims Platform — Automated Infrastructure Teardown ==="

if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo "ERROR: Python is required to run destroy_infrastructure.py"
    exit 1
fi

"$PYTHON_CMD" "$PROJECT_ROOT/scripts/destroy_infrastructure.py" "$@"
