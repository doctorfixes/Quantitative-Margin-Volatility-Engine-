#!/usr/bin/env bash
# setup_api.sh — Bootstrap the AXIOM-60 development environment.
# Usage: chmod +x setup_api.sh && ./setup_api.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== AXIOM-60 setup ==="
echo "Repo root: ${REPO_ROOT}"

# Ensure pip is up to date
python3 -m pip install --upgrade pip

# Install project dependencies
python3 -m pip install -r "${REPO_ROOT}/requirements.txt"

# Install development / test tooling
python3 -m pip install flake8 pytest

echo ""
echo "=== Lint (fatal errors only) ==="
flake8 "${REPO_ROOT}" --count --select=E9,F63,F7,F82 --show-source --statistics

echo ""
echo "=== Running tests ==="
pytest -v "${REPO_ROOT}"

echo ""
echo "=== Setup complete ==="
echo ""
echo "To start the Base44 integration API server:"
echo "  uvicorn api.main:app --reload --port 8000"
echo ""
echo "Interactive docs are then available at http://localhost:8000/docs"
