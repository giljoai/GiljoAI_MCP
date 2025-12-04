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
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
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
    params: Dict[str, Any], session_manager: MCPSessionManager, session_id: str
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
            "client_capabilities": capabilities,
        },
    )

    logger.info(f"MCP session initialized: {session_id} (client: {client_info.get('name', 'unknown')})")

    # Return server capabilities
    return {
        "protocolVersion": "2024-11-05",
        "serverInfo": {"name": "giljo-mcp", "version": "3.0.0"},
        "capabilities": {"tools": {"listChanged": False}},
    }


async def handle_tools_list(
    params: Dict[str, Any], session_manager: MCPSessionManager, session_id: str
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
                        "description": "Optional list of agent names to initialize",
                    },
                },
                "required": ["name", "mission"],
            },
        },
        {
            "name": "switch_project",
            "description": "Switch to a different project context",
            "inputSchema": {
                "type": "object",
                "properties": {"project_id": {"type": "string", "description": "Project ID to switch to"}},
                "required": ["project_id"],
            },
        },
        
        {
            "name": "update_project_mission",
            "description": "Save orchestrator's mission plan to database. Called by: ORCHESTRATOR ONLY after creating execution strategy (Step 3 of staging workflow). Persists the OUTPUT of mission planning. Critical: Project.description = user requirements (INPUT), Project.mission = orchestrator's plan (OUTPUT you create). Triggers WebSocket 'project:mission_updated' event for UI updates.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "UUID of the project"},
                    "mission": {"type": "string", "description": "Orchestrator-generated mission plan"},
                },
                "required": ["project_id", "mission"],
            },
        },
        # Orchestrator Tools
        {
            "name": "get_orchestrator_instructions",
            "description": "Fetch context for orchestrator to CREATE mission plan. Called by: ORCHESTRATOR ONLY at project start (Step 1 of staging workflow) or during implementation phase to refresh context (single source of truth). Returns project description (user requirements), prioritized context fields, and reference to get_available_agents() for discovering specialists. Orchestrator analyzes this INPUT and creates execution plan (does NOT execute work). Token estimate: ~4,500 with context exclusions applied.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "orchestrator_id": {"type": "string", "description": "Orchestrator job UUID"},
                    "tenant_key": {"type": "string", "description": "Tenant isolation key"},
                },
                "required": ["orchestrator_id", "tenant_key"],
            },
        },
        # Message Communication Tools
        {
            "name": "send_message",
            "description": "Send a message to one or more agents. Use to_agents=['all'] for broadcast.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "to_agents": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of target agent IDs/types. Use ['all'] for broadcast to all agents.",
                    },
                    "content": {"type": "string", "description": "Message content"},
                    "project_id": {"type": "string", "description": "Project ID for the message"},
                    "message_type": {
                        "type": "string",
                        "enum": ["direct", "broadcast", "system"],
                        "description": "Message type (default: direct)",
                        "default": "direct",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "normal", "high"],
                        "description": "Message priority (default: normal)",
                        "default": "normal",
                    },
                    "from_agent": {
                        "type": "string",
                        "description": "Sender agent ID (default: orchestrator)",
                    },
                },
                "required": ["to_agents", "content", "project_id"],
            },
        },
        {
            "name": "receive_messages",
            "description": "Receive pending messages for current agent",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Receiving agent ID"},
                    "limit": {"type": "integer", "description": "Maximum messages to retrieve"},
                },
            },
        },
        {
            "name": "acknowledge_message",
            "description": "Acknowledge receipt of a message",
            "inputSchema": {
                "type": "object",
                "properties": {"message_id": {"type": "string", "description": "Message ID to acknowledge"}},
                "required": ["message_id"],
            },
        },
        {
            "name": "list_messages",
            "description": "List messages with optional filters",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Filter by agent"},
                    "status": {"type": "string", "description": "Filter by message status"},
                    "limit": {"type": "integer", "description": "Maximum messages to retrieve"},
                },
            },
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
                    "priority": {"type": "string", "description": "Task priority"},
                },
                "required": ["title"],
            },
        },
        {
            "name": "list_tasks",
            "description": "List tasks with optional filters",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "Filter by task status"},
                    "assigned_to": {"type": "string", "description": "Filter by assignee"},
                    "project_id": {"type": "string", "description": "Filter by project"},
                },
            },
        },
        {
            "name": "update_task",
            "description": "Update task details or status",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "status": {"type": "string", "description": "New status"},
                    "updates": {"type": "object", "description": "Updates to apply"},
                },
                "required": ["task_id"],
            },
        },
        {
            "name": "assign_task",
            "description": "Assign task to an agent",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "agent_id": {"type": "string", "description": "Agent to assign to"},
                },
                "required": ["task_id", "agent_id"],
            },
        },
        {
            "name": "complete_task",
            "description": "Mark task as completed",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID to complete"},
                    "result": {"type": "string", "description": "Completion result/notes"},
                },
                "required": ["task_id"],
            },
        },
        # Template Management Tools (read-only via MCP)
        {
            "name": "get_template",
            "description": "Get a specific agent template",
            "inputSchema": {
                "type": "object",
                "properties": {"template_name": {"type": "string", "description": "Template name"}},
                "required": ["template_name"],
            },
        },
        # Health & Status Tools
        {
            "name": "health_check",
            "description": "Check MCP server health status",
            "inputSchema": {"type": "object", "properties": {}},
        },
        # Agent Coordination Tools (Handover 0045)
        {
            "name": "get_pending_jobs",
            "description": "Get pending jobs for agent type with multi-tenant isolation",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "agent_type": {"type": "string", "description": "Agent type (implementer, tester, etc.)"},
                    "tenant_key": {"type": "string", "description": "Tenant isolation key"},
                },
                "required": ["agent_type", "tenant_key"],
            },
        },
        {
            "name": "acknowledge_job",
            "description": "Claim a job (pending → active)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Job ID to acknowledge"},
                    "agent_id": {"type": "string", "description": "Agent identifier"},
                },
                "required": ["job_id", "agent_id"],
            },
        },
        {
            "name": "report_progress",
            "description": "Report incremental progress on active job",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Job ID being worked on"},
                    "progress": {"type": "object", "description": "Progress details"},
                },
                "required": ["job_id", "progress"],
            },
        },
        {
            "name": "get_next_instruction",
            "description": "Check for new instructions from orchestrator",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Job ID to check messages for"},
                    "agent_type": {"type": "string", "description": "Agent type"},
                    "tenant_key": {"type": "string", "description": "Tenant key"},
                },
                "required": ["job_id", "agent_type", "tenant_key"],
            },
        },
        {
            "name": "complete_job",
            "description": "Mark job as completed with results",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Job ID to complete"},
                    "result": {"type": "object", "description": "Completion result/notes"},
                },
                "required": ["job_id", "result"],
            },
        },
        {
            "name": "report_error",
            "description": "Report error and pause job for orchestrator review",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Job ID encountering error"},
                    "error": {"type": "string", "description": "Error message"},
                },
                "required": ["job_id", "error"],
            },
        },
        # Orchestration Tools (Handover 0088)
        {
            "name": "orchestrate_project",
            "description": "Complete project orchestration workflow with context prioritization and orchestration",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"},
                    "tenant_key": {"type": "string", "description": "Tenant key"},
                },
                "required": ["project_id", "tenant_key"],
            },
        },
        {
            "name": "get_agent_mission",
            "description": "Fetch agent-specific mission and context. Called by: ANY AGENT (implementer, tester, analyzer, etc.) immediately after receiving thin prompt from spawn_agent_job. Agent's first action. Returns targeted mission for this specific agent (not entire project vision). Part of thin-client architecture - mission stored in database, not embedded in prompt. Idempotent (safe to call multiple times).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "agent_job_id": {"type": "string", "description": "Agent job UUID"},
                    "tenant_key": {"type": "string", "description": "Tenant key"},
                },
                "required": ["agent_job_id", "tenant_key"],
            },
        },
        {
            "name": "spawn_agent_job",
            "description": "Create specialist agent job for execution. Called by: ORCHESTRATOR ONLY during staging to delegate work (Step 4 of workflow). Orchestrator breaks down mission into agent-specific tasks and spawns agents who EXECUTE the work. Returns agent_job_id and thin prompt (~10 lines). Agent later calls get_agent_mission() to fetch full mission. Creates database record linking agent to project.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "agent_type": {"type": "string", "description": "Type of agent"},
                    "agent_name": {"type": "string", "description": "Agent name"},
                    "mission": {"type": "string", "description": "Agent mission"},
                    "project_id": {"type": "string", "description": "Project ID"},
                    "tenant_key": {"type": "string", "description": "Tenant key"},
                },
                "required": ["agent_type", "agent_name", "mission", "project_id", "tenant_key"],
            },
        },
        {
            "name": "get_workflow_status",
            "description": "Monitor workflow progress across all project agents. Called by: ANY AGENT between todo item completion or work phases, at same time as sending status updates via MCP message tools. Returns active/completed/failed agent counts and progress_percent (0-100). Use to decide whether to proceed or wait for dependencies. Check if all agents completed (progress_percent == 100), detect failures (failed_agents > 0 requires investigation).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"},
                    "tenant_key": {"type": "string", "description": "Tenant key"},
                },
                "required": ["project_id", "tenant_key"],
            },
        },
        # Orchestrator Succession Tools (Handover 0080)
        {
            "name": "create_successor_orchestrator",
            "description": "Create successor orchestrator for context handover",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "current_job_id": {"type": "string", "description": "Current orchestrator job UUID"},
                    "tenant_key": {"type": "string", "description": "Tenant key"},
                    "reason": {
                        "type": "string",
                        "enum": ["context_limit", "manual", "phase_transition"],
                        "description": "Succession reason",
                    },
                },
                "required": ["current_job_id", "tenant_key"],
            },
        },
        {
            "name": "check_succession_status",
            "description": "Check if orchestrator should trigger succession",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Orchestrator job UUID"},
                    "tenant_key": {"type": "string", "description": "Tenant key"},
                },
                "required": ["job_id", "tenant_key"],
            },
        },
        # Slash Command Setup Tool (Handover 0093)
        {
            "name": "setup_slash_commands",
            "description": "Install GiljoAI slash commands to local CLI. Creates .md files in ~/.claude/commands/ for /gil_import_productagents, /gil_import_personalagents, and /gil_handover.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        # Slash Command Handlers (Handover 0084b)
        {
            "name": "gil_import_productagents",
            "description": "Import GiljoAI agent templates to current product's .claude/agents folder. Requires active product with project_path configured.",
            "inputSchema": {
                "type": "object",
                "properties": {"project_id": {"type": "string", "description": "Optional project ID"}},
            },
        },
        {
            "name": "gil_import_personalagents",
            "description": "Import GiljoAI agent templates to personal ~/.claude/agents folder (available across all projects).",
            "inputSchema": {
                "type": "object",
                "properties": {"project_id": {"type": "string", "description": "Optional project ID"}},
            },
        },
        {
            "name": "gil_handover",
            "description": "Trigger orchestrator succession for context handover. Creates successor orchestrator instance.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "current_job_id": {"type": "string", "description": "Current orchestrator job UUID"},
                    "reason": {
                        "type": "string",
                        "enum": ["context_limit", "manual", "phase_transition"],
                        "description": "Succession reason",
                    },
                },
            },
        },
        # Handover 0083: core /gil_* commands
        {"name": "gil_fetch", "description": "Stage agent templates and return download URL", "inputSchema": {"type": "object", "properties": {}}},
        {"name": "gil_activate", "description": "Activate a project and ensure orchestrator exists", "inputSchema": {"type": "object", "properties": {"project_id": {"type": "string"}}, "required": ["project_id"]}},
        {"name": "gil_launch", "description": "Launch project execution after staging", "inputSchema": {"type": "object", "properties": {"project_id": {"type": "string"}}, "required": ["project_id"]}},
    ]

    logger.debug(f"Listed {len(tools)} tools for session {session_id}")

    return {"tools": tools}


async def handle_tools_call(
    params: Dict[str, Any], session_manager: MCPSessionManager, session_id: str, request: Request
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
        # Project Management
        "create_project": state.tool_accessor.create_project,
        "switch_project": state.tool_accessor.switch_project,
        "update_project_mission": state.tool_accessor.update_project_mission,
        # Orchestrator Tools
        "get_orchestrator_instructions": state.tool_accessor.get_orchestrator_instructions,
        "health_check": state.tool_accessor.health_check,
        # Message Communication
        "send_message": state.tool_accessor.send_message,
        "receive_messages": state.tool_accessor.receive_messages,
        "acknowledge_message": state.tool_accessor.acknowledge_message,
        "list_messages": state.tool_accessor.list_messages,
        # Task Management
        "create_task": state.tool_accessor.create_task,
        "list_tasks": state.tool_accessor.list_tasks,
        "update_task": state.tool_accessor.update_task,
        "assign_task": state.tool_accessor.assign_task,
        "complete_task": state.tool_accessor.complete_task,
        # Template Management (read-only via MCP)
        "get_template": state.tool_accessor.get_template,
        # Agent Coordination (Handover 0045)
        "get_pending_jobs": state.tool_accessor.get_pending_jobs,
        "acknowledge_job": state.tool_accessor.acknowledge_job,
        "report_progress": state.tool_accessor.report_progress,
        "get_next_instruction": state.tool_accessor.get_next_instruction,
        "complete_job": state.tool_accessor.complete_job,
        "report_error": state.tool_accessor.report_error,
        # Orchestration Tools (Handover 0088)
        "orchestrate_project": state.tool_accessor.orchestrate_project,
        "get_agent_mission": state.tool_accessor.get_agent_mission,
        "spawn_agent_job": state.tool_accessor.spawn_agent_job,
        "get_workflow_status": state.tool_accessor.get_workflow_status,
        # Succession Tools (Handover 0080)
        "create_successor_orchestrator": state.tool_accessor.create_successor_orchestrator,
        "check_succession_status": state.tool_accessor.check_succession_status,
        # Slash Command Setup Tool (Handover 0093)
        "setup_slash_commands": state.tool_accessor.setup_slash_commands,
        # Slash Command Handlers (Handover 0084b)
        "gil_import_productagents": state.tool_accessor.gil_import_productagents,
        "gil_import_personalagents": state.tool_accessor.gil_import_personalagents,
        "gil_handover": state.tool_accessor.gil_handover,
        # Handover 0083 - core /gil_* commands
        "gil_fetch": state.tool_accessor.gil_fetch,
        "gil_activate": state.tool_accessor.gil_activate,
        "gil_launch": state.tool_accessor.gil_launch,
    }

    if tool_name not in tool_map:
        raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")

    try:
        # Inject API key for download tools (HTTP mode support)
        # These tools need API key to download from server endpoints
        download_tools = {"setup_slash_commands", "gil_import_productagents", "gil_import_personalagents"}
        if tool_name in download_tools:
            # Get API key from request headers
            api_key_value = request.headers.get("x-api-key") or request.headers.get("authorization", "").replace(
                "Bearer ", ""
            )
            arguments["_api_key"] = api_key_value

            # Inject server URL from request (fix for 0.0.0.0 bind address issue)
            # Extract scheme (http/https) and host from incoming request
            scheme = request.url.scheme  # 'http' or 'https'
            host = request.headers.get("host")  # e.g., '10.1.0.164:7272'
            server_url = f"{scheme}://{host}"
            arguments["_server_url"] = server_url

            logger.debug(f"Injected server URL for download tool: {server_url}")

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
                    "success": True,
                }
            },
        )

        logger.info(f"Tool executed successfully: {tool_name} (session: {session_id})")

        # Return result in MCP format
        # Convert result to JSON string for proper formatting
        import json

        result_text = json.dumps(result, indent=2, ensure_ascii=False)

        return {"content": [{"type": "text", "text": result_text}], "isError": False}

    except Exception as e:
        logger.error(f"Tool execution error: {tool_name} - {e}", exc_info=True)

        # Return error in MCP format
        return {"content": [{"type": "text", "text": f"Error executing {tool_name}: {e!s}"}], "isError": True}


@router.post("/mcp", tags=["MCP"])
async def mcp_endpoint(
    rpc_request: JSONRPCRequest,
    request: Request,
    x_api_key: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db_session),
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
    # Resolve API key from supported headers
    api_key_value: Optional[str] = None

    # Preferred header for this server (backward compatible)
    if x_api_key:
        api_key_value = x_api_key

    # Fallback: Authorization: Bearer <token> (for Codex/Gemini URL transports)
    if not api_key_value and authorization:
        try:
            scheme, _, token = authorization.partition(" ")
            if scheme.lower() == "bearer" and token:
                api_key_value = token
        except Exception:
            api_key_value = None

    # Validate API key presence
    if not api_key_value:
        return JSONRPCErrorResponse(
            error=JSONRPCError(
                code=-32600,
                message="Authentication required (X-API-Key or Authorization: Bearer)",
                data={"headers": ["X-API-Key", "Authorization: Bearer <token>"]},
            ),
            id=rpc_request.id,
        )

    # Initialize session manager
    session_manager = MCPSessionManager(db)

    # Get or create session
    session = await session_manager.get_or_create_session(api_key_value)
    if not session:
        return JSONRPCErrorResponse(
            error=JSONRPCError(code=-32600, message="Invalid API key", data={"authenticated": False}), id=rpc_request.id
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
                error=JSONRPCError(code=-32601, message=f"Method not found: {method}", data={"method": method}),
                id=rpc_request.id,
            )

        return JSONRPCResponse(result=result, id=rpc_request.id)

    except HTTPException as e:
        return JSONRPCErrorResponse(
            error=JSONRPCError(code=-32603, message=e.detail, data={"status_code": e.status_code}), id=rpc_request.id
        )
    except Exception as e:
        logger.error(f"MCP endpoint error: {e}", exc_info=True)
        return JSONRPCErrorResponse(
            error=JSONRPCError(code=-32603, message=f"Internal error: {e!s}"), id=rpc_request.id
        )
