"""
MCP HTTP Endpoint - Pure JSON-RPC 2.0 Implementation

Implements the MCP (Model Context Protocol) over HTTP using JSON-RPC 2.0.
This endpoint enables Claude Code, Codex CLI, and other MCP clients to connect
via HTTP transport with zero client dependencies.

Protocol Compliance:
- JSON-RPC 2.0 specification (https://www.jsonrpc.org/specification)
- MCP protocol specification (https://modelcontextprotocol.io/introduction)
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

Example Usage (Claude Code):
    claude mcp add --transport http giljo-mcp http://server:7272/mcp \
      --header "X-API-Key: gk_YOUR_API_KEY_HERE"
"""

import logging
from typing import Any, Dict, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Header, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.auth.dependencies import get_db_session
from .mcp_session import MCPSessionManager

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic models for JSON-RPC 2.0

class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 request"""
    jsonrpc: str = Field("2.0", description="JSON-RPC version")
    method: str = Field(..., description="Method name")
    params: Optional[Dict[str, Any]] = Field(None, description="Method parameters")
    id: Optional[str | int] = Field(None, description="Request ID")


class JSONRPCResponse(BaseModel):
    """JSON-RPC 2.0 success response"""
    jsonrpc: str = Field("2.0", description="JSON-RPC version")
    result: Any = Field(..., description="Result data")
    id: Optional[str | int] = Field(None, description="Request ID")


class JSONRPCError(BaseModel):
    """JSON-RPC 2.0 error object"""
    code: int = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    data: Optional[Any] = Field(None, description="Additional error data")


class JSONRPCErrorResponse(BaseModel):
    """JSON-RPC 2.0 error response"""
    jsonrpc: str = Field("2.0", description="JSON-RPC version")
    error: JSONRPCError = Field(..., description="Error details")
    id: Optional[str | int] = Field(None, description="Request ID")


# MCP Protocol Handlers

async def handle_initialize(
    params: Dict[str, Any],
    session_manager: MCPSessionManager,
    session_id: str
) -> Dict[str, Any]:
    """
    Handle MCP initialize request

    Establishes connection and negotiates capabilities.
    """
    client_info = params.get("client_info", {})
    protocol_version = params.get("protocolVersion", "2024-11-05")
    capabilities = params.get("capabilities", {})

    # Store initialization data in session
    await session_manager.update_session_data(
        session_id,
        {
            "initialized": True,
            "client_info": client_info,
            "protocol_version": protocol_version,
            "client_capabilities": capabilities
        }
    )

    logger.info(f"MCP session initialized: {session_id} (client: {client_info.get('name', 'unknown')})")

    # Return server capabilities
    return {
        "protocolVersion": "2024-11-05",
        "serverInfo": {
            "name": "giljo-mcp",
            "version": "3.0.0"
        },
        "capabilities": {
            "tools": {
                "listChanged": False
            }
        }
    }


async def handle_tools_list(
    params: Dict[str, Any],
    session_manager: MCPSessionManager,
    session_id: str
) -> Dict[str, Any]:
    """
    Handle tools/list request

    Returns list of available tools with schemas.
    """
    # Get session to extract tenant context
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Session expired")

    # Tool catalog (from existing tool_accessor methods)
    tools = [
        {
            "name": "create_project",
            "description": "Create a new project with mission and optional agent sequence",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Project name"},
                    "mission": {"type": "string", "description": "Project mission statement"},
                    "agents": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of agent names to initialize"
                    }
                },
                "required": ["name", "mission"]
            }
        },
        {
            "name": "list_projects",
            "description": "List all projects with optional status filter",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["active", "completed", "archived"],
                        "description": "Optional status filter"
                    }
                }
            }
        },
        {
            "name": "get_project",
            "description": "Get detailed project information",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"}
                },
                "required": ["project_id"]
            }
        },
        {
            "name": "switch_project",
            "description": "Switch to a different project context",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID to switch to"}
                },
                "required": ["project_id"]
            }
        }
    ]

    logger.debug(f"Listed {len(tools)} tools for session {session_id}")

    return {"tools": tools}


async def handle_tools_call(
    params: Dict[str, Any],
    session_manager: MCPSessionManager,
    session_id: str,
    request: Request
) -> Dict[str, Any]:
    """
    Handle tools/call request

    Executes tool and returns result.
    """
    tool_name = params.get("name")
    arguments = params.get("arguments", {})

    if not tool_name:
        raise HTTPException(status_code=400, detail="Tool name required")

    # Get session for tenant context
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Session expired")

    # Get tool_accessor from app state
    from api.app import state

    if not state.tool_accessor:
        raise HTTPException(status_code=503, detail="Tool accessor not initialized")

    # Set tenant context
    state.tenant_manager.set_current_tenant(session.tenant_key)

    # Route to appropriate tool method
    tool_map = {
        "create_project": state.tool_accessor.create_project,
        "list_projects": state.tool_accessor.list_projects,
        "get_project": state.tool_accessor.get_project,
        "switch_project": state.tool_accessor.switch_project,
        "close_project": state.tool_accessor.close_project,
        "spawn_agent": state.tool_accessor.spawn_agent,
        "list_agents": state.tool_accessor.list_agents,
        "get_agent_status": state.tool_accessor.get_agent_status,
        "update_agent": state.tool_accessor.update_agent,
        "retire_agent": state.tool_accessor.retire_agent,
        "send_message": state.tool_accessor.send_message,
        "receive_messages": state.tool_accessor.receive_messages,
        "acknowledge_message": state.tool_accessor.acknowledge_message,
        "list_messages": state.tool_accessor.list_messages,
        "create_task": state.tool_accessor.create_task,
        "list_tasks": state.tool_accessor.list_tasks,
        "update_task": state.tool_accessor.update_task,
        "assign_task": state.tool_accessor.assign_task,
        "complete_task": state.tool_accessor.complete_task,
        "list_templates": state.tool_accessor.list_templates,
        "get_template": state.tool_accessor.get_template,
        "create_template": state.tool_accessor.create_template,
        "update_template": state.tool_accessor.update_template,
        "discover_context": state.tool_accessor.discover_context,
        "get_file_context": state.tool_accessor.get_file_context,
        "search_context": state.tool_accessor.search_context,
        "get_context_summary": state.tool_accessor.get_context_summary,
    }

    if tool_name not in tool_map:
        raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")

    try:
        # Execute tool
        tool_func = tool_map[tool_name]
        result = await tool_func(**arguments)

        # Record tool call in session history
        await session_manager.update_session_data(
            session_id,
            {
                "last_tool_call": {
                    "tool": tool_name,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "success": True
                }
            }
        )

        logger.info(f"Tool executed successfully: {tool_name} (session: {session_id})")

        # Return result in MCP format
        return {
            "content": [
                {
                    "type": "text",
                    "text": str(result)
                }
            ],
            "isError": False
        }

    except Exception as e:
        logger.error(f"Tool execution error: {tool_name} - {e}", exc_info=True)

        # Return error in MCP format
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Error executing {tool_name}: {str(e)}"
                }
            ],
            "isError": True
        }


@router.post("/mcp", tags=["MCP"])
async def mcp_endpoint(
    rpc_request: JSONRPCRequest,
    request: Request,
    x_api_key: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Pure MCP JSON-RPC 2.0 over HTTP endpoint

    Accepts JSON-RPC 2.0 requests and routes to appropriate MCP method handler.
    Requires X-API-Key header for authentication.

    Args:
        rpc_request: JSON-RPC 2.0 request
        request: FastAPI request
        x_api_key: API key from X-API-Key header
        db: Database session

    Returns:
        JSON-RPC 2.0 response (success or error)
    """
    # Validate API key header
    if not x_api_key:
        return JSONRPCErrorResponse(
            error=JSONRPCError(
                code=-32600,
                message="X-API-Key header required",
                data={"header": "X-API-Key"}
            ),
            id=rpc_request.id
        )

    # Initialize session manager
    session_manager = MCPSessionManager(db)

    # Get or create session
    session = await session_manager.get_or_create_session(x_api_key)
    if not session:
        return JSONRPCErrorResponse(
            error=JSONRPCError(
                code=-32600,
                message="Invalid API key",
                data={"authenticated": False}
            ),
            id=rpc_request.id
        )

    # Route to method handler
    method = rpc_request.method
    params = rpc_request.params or {}

    try:
        if method == "initialize":
            result = await handle_initialize(params, session_manager, session.session_id)
        elif method == "tools/list":
            result = await handle_tools_list(params, session_manager, session.session_id)
        elif method == "tools/call":
            result = await handle_tools_call(params, session_manager, session.session_id, request)
        else:
            return JSONRPCErrorResponse(
                error=JSONRPCError(
                    code=-32601,
                    message=f"Method not found: {method}",
                    data={"method": method}
                ),
                id=rpc_request.id
            )

        return JSONRPCResponse(
            result=result,
            id=rpc_request.id
        )

    except HTTPException as e:
        return JSONRPCErrorResponse(
            error=JSONRPCError(
                code=-32603,
                message=e.detail,
                data={"status_code": e.status_code}
            ),
            id=rpc_request.id
        )
    except Exception as e:
        logger.error(f"MCP endpoint error: {e}", exc_info=True)
        return JSONRPCErrorResponse(
            error=JSONRPCError(
                code=-32603,
                message=f"Internal error: {str(e)}"
            ),
            id=rpc_request.id
        )