"""
StdIO -> HTTP MCP proxy for Codex CLI.

This module uses the official `mcp` Python SDK to expose the GiljoAI
HTTP MCP server (/mcp JSON-RPC endpoint) as a stdio MCP server.

Environment:
- GILJO_MCP_SERVER_URL: Base URL of the GiljoAI MCP server (e.g. http://host:7272)
- GILJO_API_KEY: API key for Authorization: Bearer <token>
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import anyio
import httpx
from mcp import types
from mcp.server import InitializationOptions, Server
from mcp.server.stdio import stdio_server


SERVER_URL_ENV = "GILJO_MCP_SERVER_URL"
API_KEY_ENV = "GILJO_API_KEY"


def _get_server_url() -> str:
    url = os.getenv(SERVER_URL_ENV, "").rstrip("/")
    if not url:
        raise RuntimeError("GILJO_MCP_SERVER_URL is not set")
    return url


def _get_api_key() -> Optional[str]:
    return os.getenv(API_KEY_ENV)


def _auth_headers() -> Dict[str, str]:
    api_key = _get_api_key()
    headers: Dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


server = Server("giljo-mcp-stdin-proxy")


@server.list_tools()
async def list_tools() -> List[types.Tool]:
    """Proxy tools/list to HTTP /mcp."""
    server_url = _get_server_url()
    async with httpx.AsyncClient(base_url=server_url, timeout=30.0) as client:
        payload: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {},
        }
        response = await client.post("/mcp", json=payload, headers=_auth_headers())
        response.raise_for_status()
        body = response.json()
        if "error" in body:
            raise RuntimeError(f"Backend MCP error during tools/list: {body['error']}")
        tools_raw = (body.get("result") or {}).get("tools", [])

        tools: List[types.Tool] = []
        for t in tools_raw:
            tools.append(
                types.Tool(
                    name=t["name"],
                    description=t.get("description", ""),
                    inputSchema=t.get("inputSchema", {"type": "object"}),
                )
            )
        return tools


@server.call_tool()
async def call_tool(name: str, arguments: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Proxy tools/call to HTTP /mcp."""
    server_url = _get_server_url()
    async with httpx.AsyncClient(base_url=server_url, timeout=60.0) as client:
        payload: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments or {}},
        }
        response = await client.post("/mcp", json=payload, headers=_auth_headers())
        response.raise_for_status()
        body = response.json()
        if "error" in body:
            raise RuntimeError(f"Backend MCP error during tools/call: {body['error']}")
        result = body.get("result") or {}

        # For the current MCP SDK, @server.call_tool expects a list of Content items
        # (TextContent/ImageContent/AudioContent/etc.). The host wraps these in a
        # CallToolResult on the wire. Therefore we just return the backend's `content`
        # list directly, and let the SDK handle wrapping.
        content = result.get("content", []) or []
        if not isinstance(content, list):
            content = []
        return content


async def _main() -> None:
    """Entry point for `python -m giljo_mcp.mcp_http_stdin_proxy`."""
    init_options = InitializationOptions(
        server_name="giljo-mcp-http-proxy",
        server_version="1.0.2",
        capabilities=types.ServerCapabilities(
            tools=types.ToolsCapability(listChanged=False),
        ),
        instructions=(
            "Thin stdio-to-HTTP proxy for GiljoAI MCP. "
            "All tools are forwarded to the /mcp HTTP endpoint using your API key."
        ),
    )

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, init_options)


if __name__ == "__main__":
    anyio.run(_main)
