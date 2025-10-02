#!/bin/bash
# GiljoAI MCP Launcher for Unix/Linux/Mac
# Professional service launcher with error handling

set -e

echo "========================================================"
echo "   GiljoAI MCP Service Launcher"
echo "========================================================"
echo

# Check Python installation
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.9+ from https://www.python.org/"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
REQUIRED_VERSION="3.9"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "ERROR: Python $PYTHON_VERSION is installed, but $REQUIRED_VERSION+ is required"
    exit 1
fi

# Check if config exists
if [ ! -f "config.yaml" ] && [ ! -f ".env" ]; then
    echo "ERROR: No configuration found."
    echo "Please run the installer first:"
    echo "  python3 installer/cli/install.py"
    exit 1
fi

# Check PostgreSQL (optional)
if command -v psql &> /dev/null; then
    echo "PostgreSQL client found: $(psql --version | head -n1)"
else
    echo "WARNING: PostgreSQL client not found"
    echo "Some features may not work properly"
fi

# Launch Python launcher
echo "Starting GiljoAI MCP services..."
echo

python3 start_giljo.py

EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
    echo
    echo "ERROR: Failed to start services (exit code: $EXIT_CODE)"
    echo "Check the logs in: logs/launcher/"
    exit $EXIT_CODE
fi

exit 0