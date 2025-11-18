#!/usr/bin/env python
"""
DEPRECATED: MCP Stdio Adapter placeholder

This project is now HTTP-only. Use JSON-RPC over HTTP at /mcp (api/endpoints/mcp_http.py).
This placeholder exists for backward-compatibility so imports and file lookups
do not fail abruptly. Any attempt to execute stdio routines will raise a clear
error with migration guidance.
"""

from typing import Any, Dict, Optional


class MCPAdapter:
    """Compatibility shim – no stdio support."""

    def __init__(self, server_url: Optional[str] = None, api_key: Optional[str] = None):
        self.server_url = server_url
        self.api_key = api_key

    async def run_stdio(self) -> None:
        raise NotImplementedError(
            "Stdio adapter has been removed. Use HTTP JSON-RPC at /mcp with X-API-Key."
        )

    async def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError(
            "Stdio adapter has been removed. Use HTTP JSON-RPC /mcp methods (initialize, tools/list, tools/call)."
        )


def main() -> None:
    raise SystemExit(
        "Stdio adapter removed. Configure your MCP client to use HTTP JSON-RPC:"
        " POST http://<server>:7272/mcp with X-API-Key."
    )

