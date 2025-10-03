#!/usr/bin/env python
"""
GiljoAI MCP - Multi-Agent Orchestrator

This module is for package identification only.
To start the GiljoAI services, use one of the following methods:

1. Windows: Run start_giljo.bat
2. Cross-platform: python start_giljo.py
3. Direct API: python api/run_api.py

For more information, see the documentation at docs/
"""

import sys
from pathlib import Path


def main():
    """Display basic usage information"""
    print("GiljoAI MCP Orchestrator v2.0")
    print("=" * 50)
    print("\nTo start GiljoAI services:")
    print("  - Windows:  start_giljo.bat")
    print("  - Python:   python start_giljo.py")
    print("  - Direct:   python api/run_api.py")
    print("\nFor configuration, edit config.yaml")
    print("For documentation, see docs/")
    print("=" * 50)
    sys.exit(0)


if __name__ == "__main__":
    main()
