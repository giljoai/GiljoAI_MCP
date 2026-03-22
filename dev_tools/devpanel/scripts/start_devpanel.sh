#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

PYTHON_BOOT="${PYTHON:-}"
if [[ -z "$PYTHON_BOOT" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BOOT=python3
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BOOT=python
  else
    echo "[DevPanel] Python interpreter not found. Install Python 3." >&2
    exit 1
  fi
fi

VENV_DIR="$REPO_ROOT/dev_tools/devpanel/.venv"
VENV_PY="$VENV_DIR/bin/python"
SETUP_SENTINEL="$VENV_DIR/devpanel_setup_done.txt"

if [[ ! -x "$VENV_PY" ]]; then
  echo "[DevPanel] Creating isolated virtual environment..."
  "$PYTHON_BOOT" -m venv "$VENV_DIR" || {
    echo "[DevPanel] Failed to create virtual environment." >&2
    exit 1
  }
fi

if [[ ! -f "$SETUP_SENTINEL" ]]; then
  echo "[DevPanel] Installing project dependencies into isolated venv..."
  "$VENV_PY" -m pip install --upgrade pip
  "$VENV_PY" -m pip install -e .[dev] || {
    echo "[DevPanel] Dependency installation failed." >&2
    exit 1
  }
  "$VENV_PY" -m pip install -r requirements.txt
  if [[ -f dev-requirements.txt ]]; then
    "$VENV_PY" -m pip install -r dev-requirements.txt
  fi
  echo "setup" > "$SETUP_SENTINEL"
fi

echo "[DevPanel] Ensuring runtime utilities are present (watchdog, rich, aiohttp, tiktoken, aiofiles, packaging)..."
"$VENV_PY" -m pip install watchdog rich aiohttp tiktoken aiofiles packaging >/dev/null 2>&1

cd "$REPO_ROOT"

echo "[DevPanel] Generating inventories (Phase 1001)..."
"$VENV_PY" dev_tools/devpanel/scripts/devpanel_index.py --out temp/devpanel/index || {
  echo "[DevPanel] Inventory generation failed." >&2
  exit 1
}

echo "[DevPanel] Launching backend on http://127.0.0.1:8283 ..."
ENABLE_DEVPANEL=true "$VENV_PY" dev_tools/devpanel/run_backend.py &
BACKEND_PID=$!

cleanup() {
  if kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
    echo "[DevPanel] Stopping backend (pid $BACKEND_PID)"
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

echo "[DevPanel] Launching frontend server on http://127.0.0.1:5173 ..."
"$VENV_PY" dev_tools/devpanel/scripts/start_frontend_server.py &
FRONTEND_PID=$!

sleep 2
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "http://127.0.0.1:5173/index.html" >/dev/null 2>&1 || true
elif command -v open >/dev/null 2>&1; then
  open "http://127.0.0.1:5173/index.html" >/dev/null 2>&1 || true
else
  echo "[DevPanel] Open http://127.0.0.1:5173/index.html manually (no opener found)." >&2
fi

echo "[DevPanel] Backend running (PID $BACKEND_PID). Press Ctrl+C to stop."
wait "$BACKEND_PID"
