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


# Tools hidden from MCP schema (tools/list). Kept for future use.
# As of Jan 2026, no MCP tools are hidden from schema.
HIDDEN_FROM_SCHEMA_TOOLS: set[str] = set()


async def handle_tools_list(
    params: Dict[str, Any], session_manager: MCPSessionManager, session_id: str
) -> Dict[str, Any]:
    """
    Handle tools/list request

    Returns list of available tools with schemas.
    Tools in HIDDEN_FROM_SCHEMA_TOOLS are excluded from the response but remain callable.
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
        {
            "name": "update_agent_mission",
            "description": "Update an agent's mission/execution plan. Called by: ORCHESTRATOR during staging (Step 6) to persist its own execution plan. This allows fresh-session orchestrators to retrieve their plan via get_agent_mission() during implementation. Handover 0380: Enables staging -> implementation flow across terminal sessions.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "AgentJob UUID (work order identifier)"},
                    "tenant_key": {"type": "string", "description": "Tenant isolation key"},
                    "mission": {"type": "string", "description": "Execution plan to persist (agent order, dependencies, checkpoints)"},
                },
                "required": ["job_id", "tenant_key", "mission"],
            },
        },
        # Orchestrator Tools
        {
            "name": "get_orchestrator_instructions",
            "description": "Fetch context for orchestrator to CREATE mission plan. Called by: ORCHESTRATOR ONLY at project start (Step 1 of staging workflow) or during implementation phase to refresh context (single source of truth). Returns project description (user requirements), prioritized context fields, and reference to get_available_agents() for discovering specialists. Orchestrator analyzes this INPUT and creates execution plan (does NOT execute work). Token estimate: ~4,500 with context exclusions applied.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Orchestrator job UUID (work order identifier)"},
                    "tenant_key": {"type": "string", "description": "Tenant isolation key"},
                },
                "required": ["job_id", "tenant_key"],
            },
        },
        # Message Communication Tools
        # Handover 0405: UUID Normalization - Use agent_id UUIDs for precise identification
        {
            "name": "send_message",
            "description": "Send a message to one or more agents. Use to_agents=['all'] for broadcast.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "to_agents": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of target agent_id UUIDs. Use ['all'] for broadcast to all agents.",
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
                        "description": "Your identity (identity.agent_id)",
                    },
                    "tenant_key": {"type": "string", "description": "Tenant key for isolation"},
                },
                "required": ["to_agents", "content", "project_id", "tenant_key", "from_agent"],
            },
        },
        {
            "name": "receive_messages",
            "description": "Receive pending messages for current agent with optional filtering (Handover 0360)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Your identity (identity.agent_id)"},
                    "limit": {
                        "type": "integer",
                        "description": "Maximum messages to retrieve (default: 10)",
                        "default": 10
                    },
                    "exclude_self": {
                        "type": "boolean",
                        "description": "Filter out messages from same agent_id (default: true)",
                        "default": True
                    },
                    "exclude_progress": {
                        "type": "boolean",
                        "description": "Filter out progress-type messages (default: true)",
                        "default": True
                    },
                    "message_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional allow-list of message types (e.g., ['direct', 'broadcast']). If not provided, all types (except filtered) are included."
                    },
                    "tenant_key": {"type": "string", "description": "Tenant key for isolation"},
                },
                "required": ["tenant_key"],
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
                    "tenant_key": {"type": "string", "description": "Tenant key for isolation"},
                },
                "required": ["tenant_key"],
            },
        },
        # Task Management Tools (MCP tools retired Dec 2025 - only create_task kept)
        {
            "name": "create_task",
            "description": "Create a new task",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Task title"},
                    "description": {"type": "string", "description": "Task description"},
                    "priority": {"type": "string", "description": "Task priority"},
                },
                "required": ["title"],
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
                    "agent_display_name": {"type": "string", "description": "Agent type (implementer, tester, etc.)"},
                    "tenant_key": {"type": "string", "description": "Tenant isolation key"},
                },
                "required": ["agent_display_name", "tenant_key"],
            },
        },
        {
            "name": "acknowledge_job",
            "description": "Claim a job (pending → active)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Your work order (identity.job_id)"},
                    "agent_id": {"type": "string", "description": "Your identity (identity.agent_id)"},
                    "tenant_key": {"type": "string", "description": "Tenant key for isolation"},
                },
                "required": ["job_id", "agent_id", "tenant_key"],
            },
        },
        {
            "name": "report_progress",
            "description": "Report incremental progress on active job",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Your work order (identity.job_id)"},
                    "progress": {"type": "object", "description": "Progress details"},
                    "tenant_key": {"type": "string", "description": "Tenant key for isolation"},
                },
                "required": ["job_id", "progress", "tenant_key"],
            },
        },
        {
            "name": "complete_job",
            "description": "Mark job as completed with results",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Your work order (identity.job_id)"},
                    "result": {"type": "object", "description": "Completion result/notes"},
                    "tenant_key": {"type": "string", "description": "Tenant key for isolation"},
                },
                "required": ["job_id", "result", "tenant_key"],
            },
        },
        {
            "name": "report_error",
            "description": "Report error and pause job for orchestrator review",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Your work order (identity.job_id)"},
                    "error": {"type": "string", "description": "Error message"},
                    "tenant_key": {"type": "string", "description": "Tenant key for isolation"},
                },
                "required": ["job_id", "error", "tenant_key"],
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
            "description": "Fetch agent-specific mission and context. Called by: ANY AGENT (implementer, tester, analyzer, etc.) immediately after receiving thin prompt from spawn_agent_job. Agent's first action. Returns targeted mission for this specific agent (not entire project vision). Part of thin-client architecture - mission stored in database, not embedded in prompt. Idempotent (safe to call multiple times). Handover 0381: Uses job_id (work order UUID).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Work order UUID (job_id)"},
                    "tenant_key": {"type": "string", "description": "Tenant key"},
                },
                "required": ["job_id", "tenant_key"],
            },
        },
        {
            "name": "spawn_agent_job",
            "description": "Create specialist agent job for execution. Called by: ORCHESTRATOR ONLY during staging to delegate work (Step 4 of workflow). Orchestrator breaks down mission into agent-specific tasks and spawns agents who EXECUTE the work. Returns job_id and thin prompt (~10 lines). Agent later calls get_agent_mission() to fetch full mission. Creates database record linking agent to project.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "agent_display_name": {"type": "string", "description": "Type of agent"},
                    "agent_name": {"type": "string", "description": "Agent name"},
                    "mission": {"type": "string", "description": "Agent mission"},
                    "project_id": {"type": "string", "description": "Project ID"},
                    "tenant_key": {"type": "string", "description": "Tenant key"},
                },
                "required": ["agent_display_name", "agent_name", "mission", "project_id", "tenant_key"],
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
        {
            "name": "gil_handover",
            "description": "Trigger orchestrator succession for context handover. Creates successor orchestrator instance.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Current orchestrator job UUID"},
                    "reason": {
                        "type": "string",
                        "enum": ["context_limit", "manual", "phase_transition"],
                        "description": "Succession reason",
                    },
                    "tenant_key": {"type": "string", "description": "Tenant key for isolation"},
                },
                "required": ["tenant_key"],
            },
        },
        # Handover 0083: core /gil_* commands
        # NOTE: gil_activate, gil_launch removed (0388) - users perform these via web UI, not CLI
        # Unified Context Tool (Handover 0350a)
        {
            "name": "fetch_context",
            "description": "Unified context fetcher. Retrieves product/project context by category with depth control. Categories: product_core (~100 tokens), vision_documents (0-24K), tech_stack (200-400), architecture (300-1.5K), testing (0-400), memory_360 (500-5K), git_history (500-5K), agent_templates (400-2.4K), project (~300). Use apply_user_config=true to respect user's saved settings. Single tool replaces 9 individual tools for 720 token savings in MCP schema overhead.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "Product UUID"},
                    "tenant_key": {"type": "string", "description": "Tenant isolation key"},
                    "project_id": {"type": "string", "description": "Project UUID (required for 'project' category)"},
                    "categories": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["all", "product_core", "vision_documents", "tech_stack",
                                     "architecture", "testing", "memory_360", "git_history",
                                     "agent_templates", "project"]
                        },
                        "description": "Categories to fetch. ['all'] for everything.",
                        "default": ["all"]
                    },
                    "depth_config": {
                        "type": "object",
                        "description": "Override depth per category. Example: {\"vision_documents\": \"light\"}"
                    },
                    "apply_user_config": {
                        "type": "boolean",
                        "description": "Apply user's saved settings (default: true)",
                        "default": True
                    },
                    "format": {
                        "type": "string",
                        "enum": ["structured", "flat"],
                        "description": "Response format (default: structured)",
                        "default": "structured"
                    }
                },
                "required": ["product_id", "tenant_key"]
            }
        },
        # File Utilities (Handover 0360 Feature 3)
        {
            "name": "file_exists",
            "description": "Check whether a file or directory exists within the allowed workspace. Prevents token waste from reading entire files just to check existence. Returns exists, is_file, is_dir flags. Respects workspace sandbox - blocks path traversal attacks.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to check (relative or absolute within workspace)"
                    },
                    "tenant_key": {
                        "type": "string",
                        "description": "Tenant isolation key"
                    },
                    "workspace_root": {
                        "type": "string",
                        "description": "Optional workspace root (defaults to product workspace)"
                    }
                },
                "required": ["path", "tenant_key"]
            }
        },
        # Project Closeout Tool (Handover 0411)
        {
            "name": "close_project_and_update_memory",
            "description": "Close project and update 360 Memory with sequential history entry. Called by: ORCHESTRATOR at project completion. Updates Product.product_memory.sequential_history with project summary, key outcomes, decisions made, and Git commits (if GitHub integration enabled). Triggers WebSocket 'product_memory_updated' event for UI updates.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "UUID of the project to close"},
                    "summary": {"type": "string", "description": "2-3 paragraph summary of project delivery focusing on outcomes and next steps"},
                    "key_outcomes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of key deliverables and outcomes achieved"
                    },
                    "decisions_made": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of architectural or technical decisions made during the project"
                    },
                    "tenant_key": {"type": "string", "description": "Tenant isolation key"}
                },
                "required": ["project_id", "summary", "key_outcomes", "decisions_made", "tenant_key"]
            }
        },
        # 360 Memory Writing Tool (Handover 0412)
        {
            "name": "write_360_memory",
            "description": "Write a 360 memory entry for project completion or handover. Called by orchestrator on completion, or by agents on handover. Appends to Product.product_memory.sequential_history.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project UUID"},
                    "tenant_key": {"type": "string", "description": "Tenant isolation key"},
                    "summary": {"type": "string", "description": "2-3 paragraph summary of work accomplished"},
                    "key_outcomes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "3-5 specific achievements"
                    },
                    "decisions_made": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "3-5 architectural/design decisions"
                    },
                    "entry_type": {
                        "type": "string",
                        "enum": ["project_completion", "handover_closeout"],
                        "description": "Type of 360 memory entry",
                        "default": "project_completion"
                    },
                    "author_job_id": {"type": "string", "description": "Job ID of agent writing entry"}
                },
                "required": ["project_id", "tenant_key", "summary", "key_outcomes", "decisions_made"]
            }
        },
    ]

    # Filter out hidden tools (still callable, just not advertised)
    visible_tools = [t for t in tools if t["name"] not in HIDDEN_FROM_SCHEMA_TOOLS]

    logger.debug(f"Listed {len(visible_tools)} tools for session {session_id} ({len(tools) - len(visible_tools)} hidden)")

    return {"tools": visible_tools}


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
        "update_project_mission": state.tool_accessor.update_project_mission,
        "update_agent_mission": state.tool_accessor.update_agent_mission,  # Handover 0380
        # Orchestrator Tools
        "get_orchestrator_instructions": state.tool_accessor.get_orchestrator_instructions,
        "health_check": state.tool_accessor.health_check,
        # Message Communication
        "send_message": state.tool_accessor.send_message,
        "receive_messages": state.tool_accessor.receive_messages,
        "list_messages": state.tool_accessor.list_messages,
        # Task Management (MCP tools retired Dec 2025 - only create_task kept)
        "create_task": state.tool_accessor.create_task,
        # Agent Coordination (Handover 0045)
        "get_pending_jobs": state.tool_accessor.get_pending_jobs,
        "acknowledge_job": state.tool_accessor.acknowledge_job,
        "report_progress": state.tool_accessor.report_progress,
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
        "gil_handover": state.tool_accessor.gil_handover,
        # Handover 0083 - core /gil_* commands
        # NOTE: gil_activate, gil_launch removed (0388) - users perform these via web UI
        # Unified Context Tool (Handover 0350a)
        "fetch_context": state.tool_accessor.fetch_context,
        # File Utilities (Handover 0360 Feature 3)
        "file_exists": state.tool_accessor.file_exists,
        # Project Closeout (Handover 0411)
        "close_project_and_update_memory": state.tool_accessor.close_project_and_update_memory,
        # 360 Memory Writing (Handover 0412)
        "write_360_memory": state.tool_accessor.write_360_memory,
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
