#!/bin/bash
# Launch GiljoAI Control Panel
# Prefers isolated venv_devtools (can delete main venv during resets)
# Falls back to project venv, then system Python
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Prefer isolated devtools venv (recommended - run setup_control_panel.py first)
if [ -x "$PROJECT_ROOT/dev_tools/venv_devtools/bin/python" ]; then
    exec "$PROJECT_ROOT/dev_tools/venv_devtools/bin/python" "$PROJECT_ROOT/dev_tools/control_panel.py" "$@"
# Fallback to project venv
elif [ -x "$PROJECT_ROOT/venv/bin/python" ]; then
    exec "$PROJECT_ROOT/venv/bin/python" "$PROJECT_ROOT/dev_tools/control_panel.py" "$@"
elif [ -x "$PROJECT_ROOT/.venv/bin/python" ]; then
    exec "$PROJECT_ROOT/.venv/bin/python" "$PROJECT_ROOT/dev_tools/control_panel.py" "$@"
else
    echo "Warning: No venv found. Run: python dev_tools/setup_control_panel.py"
    echo "Falling back to system Python (some features may be unavailable)."
    exec python3 "$PROJECT_ROOT/dev_tools/control_panel.py" "$@"
fi
