#!/bin/bash
# ============================================================
# GiljoAI MCP Minimal Installation Script for Linux/macOS
# Version 3.0 - Minimal Setup (Configuration via Web Wizard)
# ============================================================

set -e  # Exit on error

echo ""
echo "============================================================"
echo "    GiljoAI MCP Minimal Installer v3.0"
echo "    Simplified Setup - Configuration via Web Wizard"
echo "============================================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.11 or higher"
    echo ""
    echo "Ubuntu/Debian: sudo apt-get install python3"
    echo "macOS: brew install python@3.11"
    echo "Fedora: sudo dnf install python3"
    exit 1
fi

# Check Python version
python_version=$(python3 --version | cut -d' ' -f2)
python_major=$(echo "$python_version" | cut -d'.' -f1)
python_minor=$(echo "$python_version" | cut -d'.' -f2)

if [ "$python_major" -lt 3 ] || ([ "$python_major" -eq 3 ] && [ "$python_minor" -lt 11 ]); then
    echo "ERROR: Python $python_version detected"
    echo "Python 3.11 or higher required"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "installer/cli/minimal_installer.py" ]; then
    echo "ERROR: Installation files not found!"
    echo "Please run this script from the GiljoAI MCP root directory"
    exit 1
fi

# Launch the minimal installer
echo "Starting GiljoAI MCP Minimal Installer..."
echo ""
echo "This installer will:"
echo "  1. Detect Python and PostgreSQL"
echo "  2. Create virtual environment"
echo "  3. Install dependencies"
echo "  4. Create minimal configuration"
echo "  5. Start backend service"
echo "  6. Open browser to setup wizard"
echo ""
echo "All configuration is handled via the web wizard."
echo ""

python3 installer/cli/minimal_installer.py

# Check if installation was successful
if [ $? -eq 0 ]; then
    echo ""
    echo "============================================================"
    echo "Minimal installation completed!"
    echo ""
    echo "Next step: Complete setup wizard in your browser"
    echo "URL: http://localhost:7274/setup"
    echo "============================================================"
else
    echo ""
    echo "Installation encountered an error."
    echo "Please check the error messages above."
    echo ""
    echo "Common issues:"
    echo "- Python 3.11+ not installed"
    echo "- PostgreSQL 18 not installed or not running"
    echo "- Missing installation files"
    exit 1
fi
