#!/bin/bash
# Launch GiljoAI Control Panel with sudo while preserving display
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Preserve the current user's display environment
export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}"

cd "$PROJECT_ROOT"

# Prefer isolated devtools venv
if [ -x "$PROJECT_ROOT/dev_tools/venv_devtools/bin/python" ]; then
    exec "$PROJECT_ROOT/dev_tools/venv_devtools/bin/python" "$PROJECT_ROOT/dev_tools/control_panel.py" "$@"
elif [ -x "$PROJECT_ROOT/venv/bin/python" ]; then
    exec "$PROJECT_ROOT/venv/bin/python" "$PROJECT_ROOT/dev_tools/control_panel.py" "$@"
elif [ -x "$PROJECT_ROOT/.venv/bin/python" ]; then
    exec "$PROJECT_ROOT/.venv/bin/python" "$PROJECT_ROOT/dev_tools/control_panel.py" "$@"
else
    echo "Warning: No venv found. Run: python dev_tools/setup_control_panel.py"
    exec python3 "$PROJECT_ROOT/dev_tools/control_panel.py" "$@"
fi
