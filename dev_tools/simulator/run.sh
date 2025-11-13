#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

# Ensure repo root is on PYTHONPATH for `dev_tools` package import
REPO_ROOT="$(cd ../.. && pwd)"
export PYTHONPATH="${REPO_ROOT}:${PYTHONPATH:-}"

if [ ! -d ".venv" ]; then
  echo "Creating venv..."
  python3 -m venv .venv
  . .venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt
else
  . .venv/bin/activate
fi

exec uvicorn dev_tools.simulator.simulator_app:app --host 0.0.0.0 --port 7390
