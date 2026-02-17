#!/bin/bash
# Launch GiljoAI Control Panel with sudo, preserving display for GUI
cd /media/patrik/Work/GiljoAI_MCP
sudo -E python3 /media/patrik/Work/GiljoAI_MCP/dev_tools/control_panel.py "$@"
