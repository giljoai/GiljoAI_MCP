#!/bin/bash
# GiljoAI MCP Unix/Linux/macOS Launcher

set -e

echo "==============================================="
echo "   GiljoAI MCP Launcher"
echo "==============================================="
echo

# Get script directory and change to it
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if we have config
if [ ! -f "config.yaml" ]; then
    echo "Error: config.yaml not found"
    echo "Please run installer first"
    exit 1
fi

# Check Python installation
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 not found"
    echo "Please install Python 3.8+ first"
    exit 1
fi

echo "Starting GiljoAI MCP..."
echo

# Launch the Python launcher from root
python3 start_giljo.py "$@"

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
