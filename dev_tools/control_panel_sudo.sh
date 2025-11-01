#!/bin/bash
# Wrapper script to run the GiljoAI Control Panel with sudo while preserving display

# Preserve the current user's display environment
export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}"

# Run the control panel with the virtual environment Python
cd /media/patrik/F/projects/GiljoAI_MCP
exec /media/patrik/F/projects/GiljoAI_MCP/venv/bin/python /media/patrik/F/projects/GiljoAI_MCP/dev_tools/control_panel.py "$@"