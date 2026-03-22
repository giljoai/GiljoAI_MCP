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
    claude mcp add --transport http giljo-mcp https://server:7272/mcp \
      --header "X-API-Key: gk_YOUR_API_KEY_HERE"
"""

import inspect
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.auth.dependencies import get_db_session
from src.giljo_mcp.auth.jwt_manager import JWTManager
from src.giljo_mcp.exceptions import ValidationError
from src.giljo_mcp.services.silence_detector import auto_clear_silent

from .mcp_session import MCPSessionManager


logger = logging.getLogger(__name__)

# ============================================================================
# SECURITY: Tenant Key Validation (Handover 0424 Phase 0)
# ============================================================================


def validate_and_override_tenant_key(
    arguments: dict, session_tenant_key: str, session_user_id: str | None, tool_name: str, tool_func: callable = None
) -> dict:
    """
    SECURITY: Override client-supplied tenant_key with session tenant_key.

    Prevents tenant spoofing by ensuring tools always use the authenticated
    user's tenant_key, not client-supplied values.

    Uses function signature inspection to determine if tool accepts tenant_key.
    Only injects tenant_key for tools that explicitly accept it.

    Args:
        arguments: Tool arguments from client
        session_tenant_key: Authenticated tenant_key from session
        session_user_id: Authenticated user_id for audit logging
        tool_name: Name of the tool being called
        tool_func: The tool function (for signature inspection)

    Returns:
        Modified arguments with session tenant_key (for tools that need it)
    """
    # Check if tool accepts tenant_key by inspecting its signature
    accepts_tenant_key = False
    if tool_func is not None:
        try:
            sig = inspect.signature(tool_func)
            accepts_tenant_key = "tenant_key" in sig.parameters
        except (ValueError, TypeError):
            # If we can't inspect, don't inject tenant_key (safe default)
            accepts_tenant_key = False

    # Skip tenant_key injection for tools that don't accept it
    if not accepts_tenant_key:
        # Remove tenant_key if client accidentally sent it
        arguments.pop("tenant_key", None)
        return arguments

    client_tenant_key = arguments.get("tenant_key")

    # Always override with session tenant_key for tenant-aware tools
    arguments["tenant_key"] = session_tenant_key

    # Log mismatch as security warning
    if client_tenant_key and client_tenant_key != session_tenant_key:
        logger.warning(
            "SECURITY: Tenant key mismatch - client attempted to use different tenant",
            extra={
                "tool_name": tool_name,
                "session_tenant_key": session_tenant_key,
                "client_tenant_key": client_tenant_key,
                "user_id": session_user_id,
                "security_event": "tenant_key_override",
            },
        )

    return arguments


router = APIRouter()

# Pydantic models for JSON-RPC 2.0


class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 request"""

    jsonrpc: str = Field("2.0", description="JSON-RPC version")
    method: str = Field(..., description="Method name")
    params: dict[str, Any | None] = Field(None, description="Method parameters")
    id: str | int | None = Field(None, description="Request ID")


class JSONRPCResponse(BaseModel):
    """JSON-RPC 2.0 success response"""

    jsonrpc: str = Field("2.0", description="JSON-RPC version")
    result: Any = Field(..., description="Result data")
    id: str | int | None = Field(None, description="Request ID")


class JSONRPCError(BaseModel):
    """JSON-RPC 2.0 error object"""

    code: int = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    data: Any | None = Field(None, description="Additional error data")


class JSONRPCErrorResponse(BaseModel):
    """JSON-RPC 2.0 error response"""

    jsonrpc: str = Field("2.0", description="JSON-RPC version")
    error: JSONRPCError = Field(..., description="Error details")
    id: str | int | None = Field(None, description="Request ID")


# MCP Protocol Handlers


async def handle_initialize(
    params: dict[str, Any], session_manager: MCPSessionManager, session_id: str, tenant_key: str | None = None
) -> dict[str, Any]:
    """
    Handle MCP initialize request

    Establishes connection and negotiates capabilities.
    """
    client_info = params.get("client_info", {})
    protocol_version = params.get("protocolVersion", "2025-03-26")
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
        tenant_key=tenant_key,
    )

    logger.info(f"MCP session initialized: {session_id} (client: {client_info.get('name', 'unknown')})")

    # Return server capabilities
    return {
        "protocolVersion": "2025-03-26",
        "serverInfo": {"name": "giljo-mcp", "version": "1.0.0"},
        "capabilities": {"tools": {"listChanged": False}},
    }


# Tools hidden from MCP schema (tools/list). Kept for future use.
# As of Jan 2026, no MCP tools are hidden from schema.
HIDDEN_FROM_SCHEMA_TOOLS: set[str] = set()

# ============================================================================
# SECURITY: Schema-Based Argument Allowlist (Defense-in-Depth)
# ============================================================================
# Only parameters declared in the MCP tool inputSchema.properties are passed
# through to tool functions. This prevents injection of optional Python method
# parameters (e.g., mission, product_id, status) that are valid kwargs but
# NOT exposed in the MCP schema.
#
# IMPORTANT: When adding or modifying tool schemas in handle_tools_list(),
# update this allowlist to match. The allowlist MUST be a subset of the
# Python function's accepted parameters.
#
# tenant_key is always allowed through (handled by validate_and_override_tenant_key).
# ============================================================================
_TOOL_SCHEMA_PARAMS: dict[str, set[str]] = {
    # Project Management
    "create_project": {"name", "description", "tenant_key"},
    "update_project_mission": {"project_id", "mission"},
    "update_agent_mission": {"job_id", "tenant_key", "mission"},
    # Orchestrator Tools
    "get_orchestrator_instructions": {"job_id", "tenant_key"},
    "health_check": set(),
    # Message Communication
    "send_message": {
        "to_agents",
        "content",
        "project_id",
        "message_type",
        "priority",
        "from_agent",
        "tenant_key",
    },
    "receive_messages": {
        "agent_id",
        "limit",
        "exclude_self",
        "exclude_progress",
        "message_types",
        "tenant_key",
    },
    "list_messages": {"agent_id", "status", "limit", "tenant_key"},
    # Task Management
    "create_task": {
        "title",
        "description",
        "priority",
        "category",
        "assigned_to",
        "tenant_key",
    },
    # Agent Coordination
    "get_pending_jobs": {"agent_display_name", "tenant_key"},
    "report_progress": {"job_id", "tenant_key", "todo_items", "todo_append"},
    "complete_job": {"job_id", "result", "tenant_key"},
    "reactivate_job": {"job_id", "reason", "tenant_key"},
    "dismiss_reactivation": {"job_id", "reason", "tenant_key"},
    "report_error": {"job_id", "error", "tenant_key"},
    # Orchestration Tools
    "get_agent_mission": {"job_id", "tenant_key"},
    "spawn_agent_job": {
        "agent_display_name",
        "agent_name",
        "mission",
        "project_id",
        "tenant_key",
        "phase",
        "predecessor_job_id",
    },
    "get_agent_result": {"job_id", "tenant_key"},
    "get_workflow_status": {"project_id", "tenant_key", "exclude_job_id"},
    # Context Tools
    "fetch_context": {
        "product_id",
        "tenant_key",
        "project_id",
        "agent_name",
        "categories",
        "depth_config",
        "format",
    },
    # Project Closeout
    "close_project_and_update_memory": {
        "project_id",
        "summary",
        "key_outcomes",
        "decisions_made",
        "tenant_key",
        "force",
    },
    # 360 Memory
    "write_360_memory": {
        "project_id",
        "tenant_key",
        "summary",
        "key_outcomes",
        "decisions_made",
        "entry_type",
        "author_job_id",
    },
    # Download Tools
    "generate_download_token": {"content_type", "tenant_key"},
    # Product Context Tuning (Handover 0831)
    "submit_tuning_review": {
        "product_id",
        "tenant_key",
        "proposals",
        "overall_summary",
    },
}


def _build_project_tools() -> list[dict[str, Any]]:
    """Build tool definitions for project management and orchestrator instructions."""
    return [
        # Project Management Tools
        {
            "name": "create_project",
            "description": "Create a new project bound to the active product. Project is created as inactive. Use the web dashboard to activate and launch.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Project name/title",
                    },
                    "description": {
                        "type": "string",
                        "description": "Project description - what needs to be done",
                    },
                    "tenant_key": {
                        "type": "string",
                        "description": "Tenant isolation key (automatically injected by MCP security layer)",
                    },
                },
                "required": ["name", "description"],
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
        {
            "name": "update_agent_mission",
            "description": "Update an agent's mission/execution plan. Called by: ORCHESTRATOR during staging (Step 6) to persist its own execution plan. This allows fresh-session orchestrators to retrieve their plan via get_agent_mission() during implementation. Handover 0380: Enables staging -> implementation flow across terminal sessions.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "AgentJob UUID (work order identifier)"},
                    "tenant_key": {"type": "string", "description": "Tenant isolation key"},
                    "mission": {
                        "type": "string",
                        "description": "Execution plan to persist (agent order, dependencies, checkpoints)",
                    },
                },
                "required": ["job_id", "mission"],
            },
        },
        # Orchestrator Tools
        {
            "name": "get_orchestrator_instructions",
            "description": "Fetch context for orchestrator to CREATE mission plan. Called by: ORCHESTRATOR ONLY at project start (Step 1 of staging workflow) or during implementation phase to refresh context (single source of truth). Returns project description (user requirements), prioritized context fields, and agent_templates list for discovering specialists. Orchestrator analyzes this INPUT and creates execution plan (does NOT execute work). Token estimate: ~4,500 with context exclusions applied.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Orchestrator job UUID (work order identifier)"},
                    "tenant_key": {"type": "string", "description": "Tenant isolation key"},
                },
                "required": ["job_id"],
            },
        },
    ]


def _build_message_tools() -> list[dict[str, Any]]:
    """Build tool definitions for inter-agent messaging."""
    return [
        # Message Communication Tools
        # Handover 0500: Document all supported recipient formats (UUIDs, display names, broadcast)
        {
            "name": "send_message",
            "description": "Send a message to one or more agents. Use to_agents=['all'] for broadcast.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "to_agents": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "List of recipient agent_id UUIDs. "
                            "ALWAYS use agent_id UUIDs from your team roster (YOUR TEAM section in mission). "
                            "Format: ['550e8400-e29b-41d4-a716-446655440000']. "
                            "Use ['all'] for broadcast to all active agents (sender excluded). "
                            "Display name resolution exists as fallback but is unreliable during handovers."
                        ),
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
                        "description": "Your agent_id UUID (from YOUR IDENTITY section in mission)",
                    },
                    "tenant_key": {"type": "string", "description": "Tenant key for isolation"},
                },
                "required": ["to_agents", "content", "project_id", "from_agent"],
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
                        "default": 10,
                    },
                    "exclude_self": {
                        "type": "boolean",
                        "description": "Filter out messages from same agent_id (default: true)",
                        "default": True,
                    },
                    "exclude_progress": {
                        "type": "boolean",
                        "description": "Filter out progress-type messages (default: true)",
                        "default": True,
                    },
                    "message_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional allow-list of message types (e.g., ['direct', 'broadcast']). If not provided, all types (except filtered) are included.",
                    },
                    "tenant_key": {"type": "string", "description": "Tenant key for isolation"},
                },
                "required": [],
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
                "required": [],
            },
        },
    ]


def _build_task_and_utility_tools() -> list[dict[str, Any]]:
    """Build tool definitions for task management, health checks, and downloads."""
    return [
        # Task Management Tools (MCP tools retired Dec 2025 - only create_task kept)
        {
            "name": "create_task",
            "description": "Create a new task bound to the active product. Requires an active product to be set.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Task title"},
                    "description": {"type": "string", "description": "Task description"},
                    "priority": {
                        "type": "string",
                        "description": "Task priority (low, medium, high, critical)",
                        "default": "medium",
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional task category (frontend, backend, database, infra, docs, general)",
                    },
                    "assigned_to": {
                        "type": "string",
                        "description": "Optional agent name to assign to (not implemented yet)",
                    },
                    "tenant_key": {
                        "type": "string",
                        "description": "Tenant isolation key (automatically injected by MCP security layer)",
                    },
                },
                "required": ["title", "description"],
            },
        },
        # Health & Status Tools
        {
            "name": "health_check",
            "description": "Check MCP server health status",
            "inputSchema": {"type": "object", "properties": {}},
        },
        # Download Tools (Handover 0384)
        {
            "name": "generate_download_token",
            "description": "Generate a one-time download URL for agent templates or slash commands. Returns a URL valid for 15 minutes.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "content_type": {
                        "type": "string",
                        "enum": ["agent_templates", "slash_commands"],
                        "description": "Type of content to download",
                    },
                    "tenant_key": {"type": "string", "description": "Tenant isolation key"},
                },
                "required": ["content_type"],
            },
        },
    ]


def _build_agent_coordination_tools() -> list[dict[str, Any]]:
    """Build tool definitions for agent coordination and orchestration."""
    return [
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
                "required": ["agent_display_name"],
            },
        },
        {
            "name": "report_progress",
            "description": "Report incremental progress. Simplified: just send todo_items array. Backend calculates percent/steps automatically.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Your work order (identity.job_id)"},
                    "tenant_key": {"type": "string", "description": "Tenant key for isolation"},
                    "todo_items": {
                        "type": "array",
                        "description": "Your task list. Backend derives progress from this.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "string", "description": "Task description"},
                                "status": {
                                    "type": "string",
                                    "enum": ["pending", "in_progress", "completed", "skipped"],
                                },
                            },
                            "required": ["content", "status"],
                        },
                    },
                    "todo_append": {
                        "type": "array",
                        "description": (
                            "Steps to APPEND to existing TODO list. Use instead of todo_items "
                            "when adding work to a reactivated job. Existing completed steps are preserved."
                        ),
                        "items": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "string", "description": "Step description"},
                                "status": {
                                    "type": "string",
                                    "enum": ["pending", "in_progress"],
                                    "default": "pending",
                                },
                            },
                            "required": ["content"],
                        },
                    },
                },
                "required": ["job_id"],
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
                "required": ["job_id", "result"],
            },
        },
        {
            "name": "reactivate_job",
            "description": (
                "Resume work on a completed job after receiving a follow-up message. "
                "Only works when status is 'blocked' (auto-set when a message arrives "
                "for a completed agent). After reactivating, use report_progress with "
                "todo_append to add new steps - do not overwrite completed steps."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Job ID to reactivate"},
                    "reason": {
                        "type": "string",
                        "description": "Why reactivating (e.g., 'fix request from Orchestrator')",
                    },
                    "tenant_key": {"type": "string", "description": "Tenant key for isolation"},
                },
                "required": ["job_id"],
            },
        },
        {
            "name": "dismiss_reactivation",
            "description": (
                "Acknowledge a post-completion message without resuming work. "
                "Returns you to complete status. Use when the message is informational "
                "and no action is required."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Job ID to dismiss"},
                    "reason": {
                        "type": "string",
                        "description": "Why no action needed (e.g., 'FYI message only')",
                    },
                    "tenant_key": {"type": "string", "description": "Tenant key for isolation"},
                },
                "required": ["job_id"],
            },
        },
        {
            "name": "report_error",
            "description": "Report error and pause job for orchestrator review",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Your work order (identity.job_id)"},
                    "error": {"type": "string", "description": "Error message describing what went wrong"},
                    "tenant_key": {"type": "string", "description": "Tenant key for isolation"},
                },
                "required": ["job_id", "error"],
            },
        },
        # Orchestration Tools (Handover 0088)
        {
            "name": "get_agent_mission",
            "description": "Fetch agent-specific mission and context. Called by: ANY AGENT (implementer, tester, analyzer, etc.) immediately after receiving thin prompt from spawn_agent_job. Agent's first action. Returns targeted mission for this specific agent (not entire project vision). Part of thin-client architecture - mission stored in database, not embedded in prompt. Idempotent (safe to call multiple times). Handover 0381: Uses job_id (work order UUID).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Work order UUID (job_id)"},
                    "tenant_key": {"type": "string", "description": "Tenant key"},
                },
                "required": ["job_id"],
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
                    "phase": {
                        "type": "integer",
                        "description": "Execution phase number for multi-terminal ordering (1=first, same number=parallel, higher=later). Only used in multi-terminal mode.",
                    },
                    "predecessor_job_id": {
                        "type": "string",
                        "description": "Optional job_id of a completed predecessor agent whose work needs fixing. Injects predecessor context (summary, commits) into the successor's mission.",
                    },
                },
                "required": ["agent_display_name", "agent_name", "mission", "project_id"],
            },
        },
        {
            "name": "get_agent_result",
            "description": "Fetch the completion result of a finished agent job. Returns the structured result dict (summary, artifacts, commits) stored when the agent called complete_job. Use this to read what a predecessor agent accomplished. Handover 0497e.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Job UUID of the completed agent"},
                    "tenant_key": {"type": "string", "description": "Tenant key"},
                },
                "required": ["job_id"],
            },
        },
        {
            "name": "get_workflow_status",
            "description": "Monitor workflow progress across all project agents. Called by: ANY AGENT between todo item completion or work phases, at same time as sending status updates via MCP message tools. Returns active/completed/blocked/silent/decommissioned/pending agent counts and progress_percent (0-100). Use exclude_job_id to omit the calling orchestrator's own job from counts (avoids self-counting). Use to decide whether to proceed or wait for dependencies. Check if all agents completed (progress_percent == 100), detect blocked agents (blocked_agents > 0 may need unblocking), detect silent agents (silent_agents > 0 may have disconnected).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"},
                    "tenant_key": {"type": "string", "description": "Tenant key"},
                    "exclude_job_id": {
                        "type": "string",
                        "description": "Optional job_id to exclude from counts (e.g., the calling orchestrator's own job_id to avoid self-counting)",
                    },
                },
                "required": ["project_id"],
            },
        },
        # Succession tools removed: create_successor_orchestrator, check_succession_status
        # Handover 0391/0461/0700d: Succession is user-triggered via UI button (simple-handover REST endpoint)
        # or /gil_handover slash command. Agents cannot self-detect context exhaustion (passive HTTP architecture).
        # Handover 0083: core /gil_* commands
        # NOTE: gil_activate, gil_launch, gil_handover removed (0388, 0391) - users perform these via web UI
        # gil_handover removed in 0391: REST API endpoint handles succession, MCP tool had tenant_key bug
    ]


def _build_context_and_closeout_tools() -> list[dict[str, Any]]:
    """Build tool definitions for context fetching, project closeout, and 360 memory."""
    return [
        # Unified Context Tool (Handover 0350a, updated 0430)
        {
            "name": "fetch_context",
            "description": "Unified context fetcher. Retrieves product/project context by category with depth control. Categories: product_core (~100 tokens), vision_documents (0-24K), tech_stack (200-400), architecture (300-1.5K), testing (0-400), memory_360 (500-5K), git_history (500-5K), agent_templates (400-2.4K), project (~300), self_identity (agent template content). Single tool replaces 9 individual tools for 720 token savings in MCP schema overhead.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "Product UUID"},
                    "tenant_key": {"type": "string", "description": "Tenant isolation key"},
                    "project_id": {"type": "string", "description": "Project UUID (required for 'project' category)"},
                    "agent_name": {
                        "type": "string",
                        "description": "Agent template name (e.g., 'orchestrator-coordinator'). Required when category is 'self_identity'.",
                    },
                    "categories": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "product_core",
                                "vision_documents",
                                "tech_stack",
                                "architecture",
                                "testing",
                                "memory_360",
                                "git_history",
                                "agent_templates",
                                "project",
                                "self_identity",
                            ],
                        },
                        "description": "Exactly ONE category per call. To fetch multiple categories, make parallel tool calls — one per category.",
                    },
                    "depth_config": {
                        "type": "object",
                        "description": 'Override depth per category. Example: {"vision_documents": "light"}',
                    },
                    "format": {
                        "type": "string",
                        "enum": ["structured", "flat"],
                        "description": "Response format (default: structured)",
                        "default": "structured",
                    },
                },
                "required": ["product_id"],
            },
        },
        # Project Closeout Tool (Handover 0411)
        {
            "name": "close_project_and_update_memory",
            "description": "Close project and update 360 Memory with sequential history entry. Called by: ORCHESTRATOR at project completion. Updates Product.product_memory.sequential_history with project summary, key outcomes, decisions made, and Git commits (if GitHub integration enabled). Triggers WebSocket 'product_memory_updated' event for UI updates.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "UUID of the project to close"},
                    "summary": {
                        "type": "string",
                        "description": "2-3 paragraph summary of project delivery focusing on outcomes and next steps",
                    },
                    "key_outcomes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of key deliverables and outcomes achieved",
                    },
                    "decisions_made": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of architectural or technical decisions made during the project",
                    },
                    "tenant_key": {"type": "string", "description": "Tenant isolation key"},
                    "force": {
                        "type": "boolean",
                        "description": "If true, auto-decommission active agents and close anyway. Default false — blocks if agents still active.",
                        "default": False,
                    },
                },
                "required": ["project_id", "summary", "key_outcomes", "decisions_made"],
            },
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
                        "description": "3-5 specific achievements",
                    },
                    "decisions_made": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "3-5 architectural/design decisions",
                    },
                    "entry_type": {
                        "type": "string",
                        "enum": ["project_completion", "handover_closeout"],
                        "description": "Type of 360 memory entry",
                        "default": "project_completion",
                    },
                    "author_job_id": {"type": "string", "description": "Job ID of agent writing entry"},
                },
                "required": ["project_id", "summary", "key_outcomes", "decisions_made"],
            },
        },
        # Product Context Tuning Review (Handover 0831)
        {
            "name": "submit_tuning_review",
            "description": "Submit product context tuning proposals after comparing current product context against recent project history. Called after analyzing the tuning comparison prompt.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "Target product UUID"},
                    "tenant_key": {"type": "string", "description": "Tenant isolation key"},
                    "proposals": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "section": {
                                    "type": "string",
                                    "description": "Context section key (e.g., tech_stack, architecture, description)",
                                },
                                "drift_detected": {"type": "boolean", "description": "Whether drift was found"},
                                "current_summary": {
                                    "type": "string",
                                    "description": "Brief description of current value",
                                },
                                "evidence": {"type": "string", "description": "What 360 memory / git shows"},
                                "proposed_value": {"type": "string", "description": "Suggested replacement text"},
                                "confidence": {
                                    "type": "string",
                                    "enum": ["high", "medium", "low"],
                                    "description": "Confidence level",
                                },
                                "reasoning": {"type": "string", "description": "Why the change is recommended"},
                            },
                            "required": ["section", "drift_detected"],
                        },
                        "description": "Per-section tuning proposals",
                    },
                    "overall_summary": {
                        "type": "string",
                        "description": "High-level drift assessment",
                    },
                },
                "required": ["product_id", "proposals"],
            },
        },
    ]


async def handle_tools_list(
    params: dict[str, Any], session_manager: MCPSessionManager, session_id: str, tenant_key: str | None = None
) -> dict[str, Any]:
    """
    Handle tools/list request

    Returns list of available tools with schemas.
    Tools in HIDDEN_FROM_SCHEMA_TOOLS are excluded from the response but remain callable.
    """
    # Get session to extract tenant context
    session = await session_manager.get_session(session_id, tenant_key=tenant_key)
    if not session:
        raise HTTPException(status_code=401, detail="Session expired")

    # Complete tool catalog matching ALL methods in tool_map (handle_tools_call)
    # This ensures MCP clients can discover and use all available orchestration tools
    tools = [
        *_build_project_tools(),
        *_build_message_tools(),
        *_build_task_and_utility_tools(),
        *_build_agent_coordination_tools(),
        *_build_context_and_closeout_tools(),
    ]

    # Filter out hidden tools (still callable, just not advertised)
    visible_tools = [t for t in tools if t["name"] not in HIDDEN_FROM_SCHEMA_TOOLS]

    logger.debug(
        f"Listed {len(visible_tools)} tools for session {session_id} ({len(tools) - len(visible_tools)} hidden)"
    )

    return {"tools": visible_tools}


async def handle_tools_call(
    params: dict[str, Any],
    session_manager: MCPSessionManager,
    session_id: str,
    request: Request,
    tenant_key: str | None = None,
) -> dict[str, Any]:
    """
    Handle tools/call request

    Executes tool and returns result.
    """
    tool_name = params.get("name")
    arguments = params.get("arguments", {})

    if not tool_name:
        raise HTTPException(status_code=400, detail="Tool name required")

    # Get session for tenant context
    session = await session_manager.get_session(session_id, tenant_key=tenant_key)
    if not session:
        raise HTTPException(status_code=401, detail="Session expired")

    # Get tool_accessor from app state (inline import to avoid circular dependency with api.app)
    from api.app import state

    if not state.tool_accessor:
        raise HTTPException(status_code=503, detail="Tool accessor not initialized")

    # Set tenant context
    state.tenant_manager.set_current_tenant(session.tenant_key)

    # Route to appropriate tool method
    tool_map = {
        # Project Management
        "create_project": state.tool_accessor.create_project,
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
        "report_progress": state.tool_accessor.report_progress,
        "complete_job": state.tool_accessor.complete_job,
        "reactivate_job": state.tool_accessor.reactivate_job,
        "dismiss_reactivation": state.tool_accessor.dismiss_reactivation,
        "report_error": state.tool_accessor.report_error,
        # Orchestration Tools (Handover 0088)
        "get_agent_mission": state.tool_accessor.get_agent_mission,
        "spawn_agent_job": state.tool_accessor.spawn_agent_job,
        "get_agent_result": state.tool_accessor.get_agent_result,
        "get_workflow_status": state.tool_accessor.get_workflow_status,
        # Succession tools removed (0391/0461/0700d) - user triggers via UI button or /gil_handover slash command
        # Unified Context Tool (Handover 0350a)
        "fetch_context": state.tool_accessor.fetch_context,
        # Project Closeout (Handover 0411)
        "close_project_and_update_memory": state.tool_accessor.close_project_and_update_memory,
        # 360 Memory Writing (Handover 0412)
        "write_360_memory": state.tool_accessor.write_360_memory,
        # Download Tools (Handover 0384)
        "generate_download_token": state.tool_accessor.generate_download_token,
        # Product Context Tuning (Handover 0831)
        "submit_tuning_review": state.tool_accessor.submit_tuning_review,
    }

    if tool_name not in tool_map:
        raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")

    # Get tool function for signature inspection
    tool_func = tool_map[tool_name]

    # SECURITY FIX: Validate and override tenant_key (Handover 0424 Phase 0)
    # Uses signature inspection to only inject tenant_key for tools that accept it
    arguments = validate_and_override_tenant_key(
        arguments=arguments,
        session_tenant_key=session.tenant_key,
        session_user_id=getattr(session, "user_id", None),
        tool_name=tool_name,
        tool_func=tool_func,
    )

    # SECURITY: Strip arguments not declared in MCP schema (defense-in-depth)
    # Prevents injection of optional Python kwargs (e.g., mission, product_id)
    # that are valid method parameters but NOT exposed in the tool's inputSchema
    allowed_params = _TOOL_SCHEMA_PARAMS.get(tool_name)
    if allowed_params is not None:
        stripped = {k: v for k, v in arguments.items() if k not in allowed_params}
        if stripped:
            logger.warning(
                "SECURITY: Stripped undeclared arguments from %s call: %s (session: %s, tenant: %s)",
                tool_name,
                list(stripped.keys()),
                session_id,
                session.tenant_key,
            )
        arguments = {k: v for k, v in arguments.items() if k in allowed_params}
    else:
        # Tool not in allowlist - log and fall back to signature-based filtering
        # This ensures new tools added to tool_map but not yet in _TOOL_SCHEMA_PARAMS
        # still get basic protection against completely unknown parameters
        import inspect

        try:
            sig = inspect.signature(tool_func)
            accepted = set(sig.parameters.keys()) - {"self"}
            unexpected = {k for k in arguments if k not in accepted}
            if unexpected:
                logger.warning(
                    "SECURITY: Tool %s missing from _TOOL_SCHEMA_PARAMS allowlist; "
                    "stripped signature-invalid arguments: %s (session: %s, tenant: %s)",
                    tool_name,
                    list(unexpected),
                    session_id,
                    session.tenant_key,
                )
                arguments = {k: v for k, v in arguments.items() if k in accepted}
        except (ValueError, TypeError):
            logger.exception(
                "SECURITY: Cannot inspect signature for tool %s and tool missing from "
                "_TOOL_SCHEMA_PARAMS; rejecting call (session: %s)",
                tool_name,
                session_id,
            )
            raise HTTPException(
                status_code=500,
                detail=f"Tool {tool_name} cannot be validated for safe dispatch",
            ) from None

    try:
        # Execute tool
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
            tenant_key=tenant_key,
        )

        logger.info(f"Tool executed successfully: {tool_name} (session: {session_id})")

        # Handover 0491: Auto-clear silent status when agent makes an MCP call
        job_id = arguments.get("job_id")
        if job_id and state.websocket_manager:
            try:
                async with state.db_manager.get_session_async() as silence_session:
                    await auto_clear_silent(
                        session=silence_session,
                        job_id=job_id,
                        ws_manager=state.websocket_manager,
                    )
            except (OSError, RuntimeError, ValueError) as auto_clear_err:
                logger.debug("Auto-clear silent check: %s", auto_clear_err)

        # Return result in MCP format
        # Convert result to JSON string for proper formatting
        # Handover 0731c: Convert Pydantic models to dicts for JSON serialization
        serializable_result = result.model_dump() if isinstance(result, BaseModel) else result
        # Handover 0827c: Include reactivation guidance if present
        if hasattr(result, "_reactivation_guidance"):
            serializable_result["_reactivation_guidance"] = result._reactivation_guidance
        result_text = json.dumps(serializable_result, indent=2, ensure_ascii=False, default=str)

        return {"content": [{"type": "text", "text": result_text}], "isError": False}

    except Exception as e:  # Broad catch: API boundary, converts to HTTP error
        # Suppress expected validation errors from console logs (they're returned to agent)
        if isinstance(e, ValidationError) and "COMPLETION_BLOCKED" in str(e):
            # This is expected behavior - agent tried to complete without finishing TODOs
            # Log at DEBUG level instead of ERROR to avoid console pollution
            logger.debug(f"Agent validation: {tool_name} - {e}")
        else:
            # Log all other errors at ERROR level with traceback
            logger.error(f"Tool execution error: {tool_name} - {e}", exc_info=True)

        # Return error in MCP format (agent still receives the message)
        return {"content": [{"type": "text", "text": f"Error executing {tool_name}: {e!s}"}], "isError": True}


@router.post("/mcp", tags=["MCP"])
async def mcp_endpoint(
    rpc_request: JSONRPCRequest,
    request: Request,
    x_api_key: str | None = Header(None),
    authorization: str | None = Header(None),
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
    # Resolve credentials from supported headers
    api_key_value: str | None = None
    bearer_token: str | None = None

    # Preferred header for this server (backward compatible)
    if x_api_key:
        api_key_value = x_api_key

    # Extract Bearer token from Authorization header
    if not api_key_value and authorization:
        try:
            scheme, _, token = authorization.partition(" ")
            if scheme.lower() == "bearer" and token:
                bearer_token = token
        except (ValueError, KeyError):
            bearer_token = None

    # Validate that some credential was provided
    if not api_key_value and not bearer_token:
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
    session = None

    # For Bearer tokens, try JWT validation first, then fall back to API key
    if bearer_token and not api_key_value:
        try:
            payload = JWTManager.verify_token(bearer_token)
            session = await session_manager.get_or_create_session_from_jwt(
                user_id=payload["sub"],
                tenant_key=payload["tenant_key"],
                username=payload.get("username"),
            )
        except HTTPException:
            # Not a valid JWT -- treat as API key (backward compatibility)
            api_key_value = bearer_token

    # API key authentication path (X-API-Key header or Bearer fallback)
    if not session and api_key_value:
        session = await session_manager.get_or_create_session(api_key_value)

    if not session:
        return JSONRPCErrorResponse(
            error=JSONRPCError(code=-32600, message="Invalid credentials", data={"authenticated": False}),
            id=rpc_request.id,
        )

    # Log IP address for security tracking (passive, non-blocking)
    # Skip for JWT sessions that have no associated API key
    if session.api_key_id:
        client_ip = request.client.host if request.client else "unknown"
        try:
            await session_manager.log_ip(session.api_key_id, client_ip)
        except (OSError, ValueError, KeyError):
            logger.debug("IP logging failed for MCP request (non-blocking)")

    # Route to method handler
    method = rpc_request.method
    params = rpc_request.params or {}

    # MCP notifications (no id, no response expected) -- return 202 Accepted per Streamable HTTP spec
    if method.startswith("notifications/"):
        logger.debug(f"MCP notification received: {method} (session: {session.session_id})")
        return Response(status_code=202)

    try:
        if method == "initialize":
            result = await handle_initialize(params, session_manager, session.session_id, session.tenant_key)
        elif method == "tools/list":
            result = await handle_tools_list(params, session_manager, session.session_id, session.tenant_key)
        elif method == "tools/call":
            result = await handle_tools_call(params, session_manager, session.session_id, request, session.tenant_key)
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
    except Exception:  # Broad catch: API boundary, converts to HTTP error
        logger.exception("Unexpected MCP endpoint error")
        return JSONRPCErrorResponse(error=JSONRPCError(code=-32603, message="Internal server error"), id=rpc_request.id)
