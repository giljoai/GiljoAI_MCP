#!/bin/bash
# Launch GiljoAI Control Panel using the project's virtual environment
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Use venv Python if available (has psycopg2 and other deps)
if [ -x "$PROJECT_ROOT/venv/bin/python" ]; then
    exec "$PROJECT_ROOT/venv/bin/python" "$PROJECT_ROOT/dev_tools/control_panel.py" "$@"
elif [ -x "$PROJECT_ROOT/.venv/bin/python" ]; then
    exec "$PROJECT_ROOT/.venv/bin/python" "$PROJECT_ROOT/dev_tools/control_panel.py" "$@"
else
    echo "Warning: No project venv found. Using system Python (some features may be unavailable)."
    exec python3 "$PROJECT_ROOT/dev_tools/control_panel.py" "$@"
fi
