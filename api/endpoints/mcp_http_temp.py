"""
MCP HTTP Endpoint - Pure JSON-RPC 2.0 Implementation

Implements the MCP (Model Context Protocol) over HTTP using JSON-RPC 2.0.
This endpoint enables Claude Code, Codex CLI, and other MCP clients to connect
via HTTP transport with zero client dependencies.

Protocol Compliance:
- JSON-RPC 2.0 specification
- MCP protocol specification
- Stateful session management with PostgreSQL persistence
- Multi-tenant isolation via API key authentication

Supported Methods:
- initialize: Handshake and capability negotiation
- tools/list: List available tools
- tools/call: Execute tool with arguments

Authentication:
- X-API-Key header required for all requests
- Session persistence across multiple tool calls
- Automatic tenant/project context resolution
"""

import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models for JSON-RPC 2.0


class JSONRPCRequest(BaseModel):
    jsonrpc: str = Field("2.0", description="JSON-RPC version")
    method: str = Field(..., description="Method name")
    params: dict[str, Any | None] = Field(None, description="Method parameters")
    id: str | int | None = Field(None, description="Request ID")


class JSONRPCResponse(BaseModel):
    jsonrpc: str = Field("2.0", description="JSON-RPC version")
    result: Any = Field(..., description="Result data")
    id: str | int | None = Field(None, description="Request ID")


class JSONRPCError(BaseModel):
    code: int = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    data: Any | None = Field(None, description="Additional error data")


class JSONRPCErrorResponse(BaseModel):
    jsonrpc: str = Field("2.0", description="JSON-RPC version")
    error: JSONRPCError = Field(..., description="Error details")
    id: str | int | None = Field(None, description="Request ID")
