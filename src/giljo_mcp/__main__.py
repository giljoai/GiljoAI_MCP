#!/usr/bin/env python
"""
GiljoAI MCP - Main Module

IMPORTANT: Architecture Update (v2.0)
=====================================

The stdio-based MCP server has been retired in favor of a unified HTTP architecture.

Old Architecture (DEPRECATED):
- MCP server on stdio (single connection, session-bound)
- Separate API server on port 8000
- Could not support multiple users

New Architecture (CURRENT):
- Unified HTTP server on port 8000 (persistent, multi-user)
- MCP stdio adapter for Claude compatibility
- Supports multiple concurrent connections

How to use:
-----------
1. Start the server: run start_giljo.bat or python api/run_api.py
2. For Claude: The stdio adapter (mcp_adapter.py) bridges to the HTTP server
3. For API clients: Connect directly to http://localhost:8000

This module now serves as documentation only.
For the actual server, see api/run_api.py
For Claude integration, see mcp_adapter.py
"""

import sys
from pathlib import Path


def main():
    """Display information about the new architecture"""
    print(__doc__)
    print("\n" + "=" * 60)
    print("To start the GiljoAI MCP server:")
    print("  - Windows: Run start_giljo.bat")
    print("  - Direct: python api/run_api.py")
    print("\nTo connect Claude:")
    print("  - Run register_claude.bat (one-time setup)")
    print("  - The adapter will bridge stdio to the HTTP server")
    print("=" * 60)
    print("\nFor more information, see docs/techdebt/stdio_to_server_architecture.md")
    sys.exit(0)


if __name__ == "__main__":
    main()
