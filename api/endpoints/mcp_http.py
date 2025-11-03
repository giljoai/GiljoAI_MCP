"""
MCP HTTP Endpoint - Pure JSON-RPC 2.0 Implementation

CHANGELOG:
- 2025-11-03: Fixed tool catalog mismatch - exposed all 30 orchestration tools
              Previously only 6 tools were advertised in tools/list while 30 were
              callable. Now all tools are properly exposed for MCP clients.

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

    # Complete tool catalog matching ALL methods in tool_map (handle_tools_call)
    # This ensures MCP clients can discover and use all available orchestration tools
    tools = [
        # Project Management Tools
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
        },
        {
            "name": "close_project",
            "description": "Close an active project",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID to close"}
                },
                "required": ["project_id"]
            }
        },
        
        # Orchestrator Tools
        {
            "name": "get_orchestrator_instructions",
            "description": "Fetch orchestrator mission with 70% token reduction (thin client architecture)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "orchestrator_id": {"type": "string", "description": "Orchestrator job UUID"},
                    "tenant_key": {"type": "string", "description": "Tenant isolation key"}
                },
                "required": ["orchestrator_id", "tenant_key"]
            }
        },
        
        # Agent Management Tools
        {
            "name": "spawn_agent",
            "description": "Spawn a new AI agent for the project",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "agent_type": {"type": "string", "description": "Type of agent to spawn"},
                    "project_id": {"type": "string", "description": "Project ID"},
                    "configuration": {"type": "object", "description": "Agent configuration"}
                },
                "required": ["agent_type", "project_id"]
            }
        },
        {
            "name": "list_agents",
            "description": "List all agents in the current project",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"},
                    "status": {"type": "string", "description": "Filter by agent status"}
                }
            }
        },
        {
            "name": "get_agent_status",
            "description": "Get status of a specific agent",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Agent ID"}
                },
                "required": ["agent_id"]
            }
        },
        {
            "name": "update_agent",
            "description": "Update agent configuration or status",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Agent ID"},
                    "status": {"type": "string", "description": "New status"},
                    "configuration": {"type": "object", "description": "Configuration updates"}
                },
                "required": ["agent_id"]
            }
        },
        {
            "name": "retire_agent",
            "description": "Retire an agent from active duty",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Agent ID to retire"}
                },
                "required": ["agent_id"]
            }
        },
        
        # Message Communication Tools
        {
            "name": "send_message",
            "description": "Send a message to another agent",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "to_agent": {"type": "string", "description": "Target agent ID"},
                    "message": {"type": "string", "description": "Message content"},
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                        "description": "Message priority"
                    }
                },
                "required": ["to_agent", "message"]
            }
        },
        {
            "name": "receive_messages",
            "description": "Receive pending messages for current agent",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Receiving agent ID"},
                    "limit": {"type": "integer", "description": "Maximum messages to retrieve"}
                }
            }
        },
        {
            "name": "acknowledge_message",
            "description": "Acknowledge receipt of a message",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "message_id": {"type": "string", "description": "Message ID to acknowledge"}
                },
                "required": ["message_id"]
            }
        },
        {
            "name": "list_messages",
            "description": "List messages with optional filters",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Filter by agent"},
                    "status": {"type": "string", "description": "Filter by message status"},
                    "limit": {"type": "integer", "description": "Maximum messages to retrieve"}
                }
            }
        },
        
        # Task Management Tools
        {
            "name": "create_task",
            "description": "Create a new task",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Task title"},
                    "description": {"type": "string", "description": "Task description"},
                    "assigned_to": {"type": "string", "description": "Agent to assign task to"},
                    "priority": {"type": "string", "description": "Task priority"}
                },
                "required": ["title"]
            }
        },
        {
            "name": "list_tasks",
            "description": "List tasks with optional filters",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "Filter by task status"},
                    "assigned_to": {"type": "string", "description": "Filter by assignee"},
                    "project_id": {"type": "string", "description": "Filter by project"}
                }
            }
        },
        {
            "name": "update_task",
            "description": "Update task details or status",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "status": {"type": "string", "description": "New status"},
                    "updates": {"type": "object", "description": "Updates to apply"}
                },
                "required": ["task_id"]
            }
        },
        {
            "name": "assign_task",
            "description": "Assign task to an agent",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "agent_id": {"type": "string", "description": "Agent to assign to"}
                },
                "required": ["task_id", "agent_id"]
            }
        },
        {
            "name": "complete_task",
            "description": "Mark task as completed",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID to complete"},
                    "result": {"type": "string", "description": "Completion result/notes"}
                },
                "required": ["task_id"]
            }
        },
        
        # Template Management Tools
        {
            "name": "list_templates",
            "description": "List available agent templates",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "get_template",
            "description": "Get a specific agent template",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "template_name": {"type": "string", "description": "Template name"}
                },
                "required": ["template_name"]
            }
        },
        {
            "name": "create_template",
            "description": "Create a new agent template",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Template name"},
                    "content": {"type": "object", "description": "Template content"}
                },
                "required": ["name", "content"]
            }
        },
        {
            "name": "update_template",
            "description": "Update an existing template",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "template_name": {"type": "string", "description": "Template name"},
                    "updates": {"type": "object", "description": "Updates to apply"}
                },
                "required": ["template_name", "updates"]
            }
        },
        
        # Context Discovery Tools
        {
            "name": "discover_context",
            "description": "Discover available context in the project",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"}
                }
            }
        },
        {
            "name": "get_file_context",
            "description": "Get context from a specific file",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to file"}
                },
                "required": ["file_path"]
            }
        },
        {
            "name": "search_context",
            "description": "Search through project context",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "project_id": {"type": "string", "description": "Project ID"},
                    "limit": {"type": "integer", "description": "Maximum results"}
                },
                "required": ["query"]
            }
        },
        {
            "name": "get_context_summary",
            "description": "Get summary of available context",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"}
                }
            }
        },
        
        # Health & Status Tools
        {
            "name": "health_check",
            "description": "Check MCP server health status",
            "inputSchema": {
                "type": "object",
                "properties": {}
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
        "get_orchestrator_instructions": state.tool_accessor.get_orchestrator_instructions,
        "health_check": state.tool_accessor.health_check,
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