#!/usr/bin/env bash
# deploy.sh — Validate the AXIOM-60 codebase then confirm it is ready to ship.
#
# Usage:
#   chmod +x deploy.sh && ./deploy.sh
#
# What it does:
#   1. Installs / upgrades dependencies
#   2. Runs flake8 (fatal-error pass + warnings pass)
#   3. Runs the full pytest suite
#   4. Prints the Railway start command so you know what will run in production
#
# After this script exits 0, you can:
#   git add -A && git commit -m "AXIOM-60: production deploy" && git push
# Railway will detect the push, build the image, and start:
#   uvicorn api.main:app --host 0.0.0.0 --port $PORT

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${REPO_ROOT}"

echo "=== AXIOM-60 production deploy check ==="
echo "Repo root: ${REPO_ROOT}"

# ── 1. Dependencies ────────────────────────────────────────────────────────
echo ""
echo "=== Installing dependencies ==="
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
python3 -m pip install flake8 pytest

# ── 2. Lint ────────────────────────────────────────────────────────────────
echo ""
echo "=== Lint — fatal errors (E9, F63, F7, F82) ==="
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

echo ""
echo "=== Lint — style warnings (complexity ≤ 10, line length ≤ 127) ==="
flake8 . --count --max-complexity=10 --max-line-length=127 --statistics

# ── 3. Tests ───────────────────────────────────────────────────────────────
echo ""
echo "=== Tests ==="
pytest -v

# ── 4. Summary ────────────────────────────────────────────────────────────
echo ""
echo "=== All checks passed — ready to deploy ==="
echo ""
echo "Next steps:"
echo "  git add -A && git commit -m 'AXIOM-60: production deploy' && git push"
echo ""
echo "Railway will start the API with:"
echo "  uvicorn api.main:app --host 0.0.0.0 --port \$PORT"
echo ""
echo "Remember to set AXIOM_API_KEY in your Railway environment variables."
