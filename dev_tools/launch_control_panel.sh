#!/bin/bash
# ============================================================
# Launch Control Panel using isolated devtools environment
# Auto-creates venv_devtools if missing (self-bootstrapping)
# Validates venv integrity via pyvenv.cfg before use
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$PROJECT_ROOT/dev_tools/venv_devtools"

cd "$PROJECT_ROOT"

# ── Check isolated devtools venv (preferred) ─────────────────
if [ -f "$VENV_DIR/pyvenv.cfg" ] && [ -x "$VENV_DIR/bin/python" ]; then
    exec "$VENV_DIR/bin/python" "$PROJECT_ROOT/dev_tools/control_panel.py" "$@"
fi

# ── venv_devtools missing or corrupted -- auto-bootstrap ─────
echo ""
echo "  Developer Control Panel - Auto Setup"
echo "  ====================================="
echo "  Isolated venv_devtools not found. Creating it now..."
echo ""

# Find a working system Python
SYS_PYTHON=""
for candidate in python3 python; do
    if command -v "$candidate" &>/dev/null; then
        # Verify it's Python 3.10+
        version=$("$candidate" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
        major=$(echo "$version" | cut -d. -f1)
        minor=$(echo "$version" | cut -d. -f2)
        if [ "$major" = "3" ] && [ "$minor" -ge 10 ]; then
            SYS_PYTHON="$candidate"
            break
        fi
    fi
done

if [ -z "$SYS_PYTHON" ]; then
    echo "  [FAIL] No Python 3.10+ found. Install Python and re-run."
    exit 1
fi

echo "  [OK] Found system Python: $SYS_PYTHON ($version)"

# Clean up corrupted venv_devtools if it exists without pyvenv.cfg
if [ -d "$VENV_DIR" ]; then
    echo "  [..] Removing corrupted venv_devtools..."
    rm -rf "$VENV_DIR"
fi

# Create the venv
echo "  [..] Creating dev_tools/venv_devtools..."
"$SYS_PYTHON" -m venv "$VENV_DIR"
if [ $? -ne 0 ]; then
    echo "  [FAIL] Failed to create virtual environment."
    echo "         On Debian/Ubuntu, try: sudo apt install python3-venv"
    exit 1
fi
echo "  [OK] Virtual environment created"

# Install dependencies
echo "  [..] Installing dependencies (psutil, psycopg2-binary, pyyaml)..."
"$VENV_DIR/bin/pip" install --upgrade pip -q >/dev/null 2>&1
if [ -f "$PROJECT_ROOT/dev_tools/requirements.txt" ]; then
    "$VENV_DIR/bin/pip" install -r "$PROJECT_ROOT/dev_tools/requirements.txt" -q
else
    "$VENV_DIR/bin/pip" install psutil psycopg2-binary pyyaml -q
fi
if [ $? -ne 0 ]; then
    echo "  [FAIL] Failed to install dependencies."
    exit 1
fi
echo "  [OK] Dependencies installed"
echo ""
echo "  Setup complete. Launching control panel..."
echo ""

exec "$VENV_DIR/bin/python" "$PROJECT_ROOT/dev_tools/control_panel.py" "$@"
