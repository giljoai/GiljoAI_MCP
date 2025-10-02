#!/bin/bash
# GiljoAI MCP Unix/Linux/macOS Launcher
# Provides a convenient wrapper for the Python launcher

set -e

echo "==============================================="
echo "   GiljoAI MCP Launcher"
echo "==============================================="
echo

# Check if we're in the correct directory
if [ ! -f "config.yaml" ]; then
    echo "Error: config.yaml not found"
    echo "Please run this script from the GiljoAI MCP installation directory"
    exit 1
fi

# Check Python installation
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 not found"
    echo "Please install Python 3.8+ first"
    exit 1
fi

# Check if launchers directory exists
if [ ! -f "launchers/start_giljo.py" ]; then
    echo "Error: Launcher script not found"
    echo "Please ensure installation is complete"
    exit 1
fi

echo "Starting GiljoAI MCP..."
echo

# Launch the Python launcher
python3 launchers/start_giljo.py "$@"

# Check exit code
if [ $? -ne 0 ]; then
    echo
    echo "Launch failed. Please check the error messages above."
    echo
    echo "Troubleshooting:"
    echo "  1. Ensure PostgreSQL is running"
    echo "  2. Check that all required ports are available"
    echo "  3. Review logs in the logs/ directory"
    echo "  4. Verify .env and config.yaml are present"
    echo
    exit 1
fi
