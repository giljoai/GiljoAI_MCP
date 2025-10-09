#!/usr/bin/env python
"""
GiljoAI MCP - Multi-Agent Orchestrator

Entry point for the MCP stdio adapter when invoked as 'python -m giljo_mcp'
This allows Claude Code to communicate with the GiljoAI backend via MCP protocol.
"""

import asyncio


def main():
    """Main entry point for the MCP adapter"""
    # Import here to avoid circular imports
    from giljo_mcp.mcp_adapter import main as adapter_main

    # Run the MCP adapter
    asyncio.run(adapter_main())


if __name__ == "__main__":
    main()
