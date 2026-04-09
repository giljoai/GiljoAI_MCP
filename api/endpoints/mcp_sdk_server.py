# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
MCP SDK Server -- Streamable HTTP transport using official Anthropic MCP Python SDK.

Standard MCP protocol transport using official Anthropic MCP Python SDK (FastMCP).
transport. All tools delegate to the existing ToolAccessor methods. Auth and tenant
isolation are handled by ASGI middleware applied to the Starlette sub-app.

Handover: 0846a (transport replacement), 0846b (security integration)
"""

import inspect
import logging
from typing import Annotated, Any, Literal

from fastapi import HTTPException
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import Field
from starlette.requests import Request as StarletteRequest
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from src.giljo_mcp.auth.jwt_manager import JWTManager


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# MCP Server instance
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name="giljo_mcp",
    instructions="GiljoAI Coding Orchestrator -- AI agent orchestration tools",
    stateless_http=True,
    json_response=True,
    streamable_http_path="/",
    # Disable SDK's built-in DNS rebinding protection — our MCPAuthMiddleware
    # handles auth (Bearer token + tenant isolation). The server binds to
    # 127.0.0.1 (localhost HTTP) or LAN IP (HTTPS only), configured at install.
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


# ---------------------------------------------------------------------------
# Helpers: resolve app-level state inside tool handlers
# ---------------------------------------------------------------------------


def _get_tool_accessor():
    """Lazy import to avoid circular dependency with api.app at module load."""
    from api.app import state

    if not state.tool_accessor:
        raise RuntimeError("Tool accessor not initialized")
    return state.tool_accessor


def _get_tenant_manager():
    from api.app import state

    return state.tenant_manager


def _resolve_tenant(ctx: Context) -> str:
    """Extract tenant_key from ASGI scope state (set by MCPAuthMiddleware)."""
    request: StarletteRequest = ctx.request_context.request
    tenant_key = request.scope.get("state", {}).get("tenant_key")
    if not tenant_key:
        raise RuntimeError("No tenant_key in request state -- auth middleware missing")
    return tenant_key


def _set_tenant_context(tenant_key: str) -> None:
    """Set the current tenant for downstream DB queries."""
    _get_tenant_manager().set_current_tenant(tenant_key)


async def _call_tool(ctx: Context, method_name: str, kwargs: dict[str, Any]) -> Any:
    """
    Central dispatch: resolve tenant, inject tenant_key, call ToolAccessor method.

    Mirrors the security logic from validate_and_override_tenant_key():
    - Inspects method signature to decide whether tenant_key is accepted
    - Always injects session tenant_key (never trust client-supplied value)
    - Strips tenant_key from kwargs if the method doesn't accept it

    After successful execution, auto-clears 'silent' status if the calling
    agent was marked silent (restores to 'working' + updates last_progress_at).
    """
    tenant_key = _resolve_tenant(ctx)
    _set_tenant_context(tenant_key)

    accessor = _get_tool_accessor()
    tool_func = getattr(accessor, method_name)

    # Signature-based tenant_key injection
    sig = inspect.signature(tool_func)
    if "tenant_key" in sig.parameters:
        kwargs["tenant_key"] = tenant_key
    else:
        kwargs.pop("tenant_key", None)

    result = await tool_func(**kwargs)

    # Auto-clear silent status on any successful MCP interaction
    job_id = kwargs.get("job_id")
    if job_id:
        try:
            from api.app import state as app_state
            from src.giljo_mcp.services.silence_detector import auto_clear_silent

            ws_manager = getattr(app_state, "websocket_manager", None)
            async with app_state.db_manager.get_session_async() as db:
                await auto_clear_silent(db, job_id, ws_manager)
        except (OSError, RuntimeError, ValueError, TypeError, AttributeError, KeyError):
            logger.warning("auto_clear_silent failed for job_id=%s (non-blocking)", job_id)

    return result


# ---------------------------------------------------------------------------
# Project Management Tools (4)
# ---------------------------------------------------------------------------


@mcp.tool(
    description=(
        "Create a new project bound to the active product. "
        "Projects are classified by taxonomy: project_type + series_number forming a serial like FE-0001. "
        "Call discovery(category='project_types') first to see valid types. "
        "Project is created as inactive. Use the web dashboard to activate and launch."
    ),
)
async def create_project(
    name: str,
    description: str,
    project_type: str = "",
    series_number: int = 0,
    ctx: Context = None,
) -> dict:
    """Create a new project bound to the active product.

    Args:
        name: Project name (required)
        description: Human-written project description
        project_type: Taxonomy type abbreviation (e.g. FE, BE, INFRA, DOCS).
            Must match a pre-existing category configured in the dashboard.
            If the type is not recognized, the project is created without taxonomy.
            Combined with series_number to form the project serial (e.g. FE-0001).
        series_number: Sequential number within the type series (1-9999).
            Forms serial like TYPE-0001. Use 0 for auto-assign.
    """
    params = {
        "name": name,
        "description": description,
        "project_type": project_type,
    }
    if series_number > 0:
        params["series_number"] = series_number
    return await _call_tool(ctx, "create_project", params)


@mcp.tool(
    description=(
        "Save orchestrator's mission plan to database. Called by: ORCHESTRATOR ONLY "
        "after creating execution strategy (Step 3 of staging workflow). "
        "Persists the OUTPUT of mission planning. "
        "Critical: Project.description = user requirements (INPUT), "
        "Project.mission = orchestrator's plan (OUTPUT you create). "
        "Triggers WebSocket 'project:mission_updated' event for UI updates."
    ),
)
async def update_project_mission(
    project_id: str,
    mission: str,
    ctx: Context = None,
) -> dict:
    """Save orchestrator's mission plan to database."""
    return await _call_tool(
        ctx,
        "update_project_mission",
        {
            "project_id": project_id,
            "mission": mission,
        },
    )


@mcp.tool(
    description=(
        "Update an agent's mission/execution plan. Called by: ORCHESTRATOR during staging "
        "(Step 6) to persist its own execution plan. This allows fresh-session orchestrators "
        "to retrieve their plan via get_agent_mission() during implementation. "
        "Handover 0380: Enables staging -> implementation flow across terminal sessions."
    ),
)
async def update_agent_mission(
    job_id: str,
    mission: str,
    ctx: Context = None,
) -> dict:
    """Update an agent's mission/execution plan."""
    return await _call_tool(
        ctx,
        "update_agent_mission",
        {
            "job_id": job_id,
            "mission": mission,
        },
    )


@mcp.tool(
    description=(
        "Fetch context for orchestrator to CREATE mission plan. Called by: ORCHESTRATOR ONLY "
        "at project start (Step 1 of staging workflow) or during implementation phase to "
        "refresh context (single source of truth). Returns project description (user "
        "requirements), prioritized context fields, and agent_templates list for discovering "
        "specialists. Orchestrator analyzes this INPUT and creates execution plan (does NOT "
        "execute work). Token estimate: ~4,500 with context exclusions applied."
    ),
)
async def get_orchestrator_instructions(
    job_id: str,
    ctx: Context = None,
) -> dict:
    """Fetch context for orchestrator to CREATE mission plan."""
    return await _call_tool(ctx, "get_orchestrator_instructions", {"job_id": job_id})


# ---------------------------------------------------------------------------
# Message Communication Tools (3)
# ---------------------------------------------------------------------------


@mcp.tool(
    description=(
        "Send a message to one or more agents. Use to_agents=['all'] for broadcast. "
        "Set requires_action=true if the recipient must act (rework, review, respond). "
        "Leave false for informational messages (status updates, completion notices). "
        "Only action-required messages trigger reactivation of completed agents."
    ),
)
async def send_message(
    to_agents: Annotated[list[str], Field(description="List of recipient agent_id UUIDs (from get_workflow_status). Use ['all'] for broadcast. NEVER use display names like 'orchestrator' — always UUIDs.")],
    content: Annotated[str, Field(description="Message content. Prefix with BLOCKER:, PROGRESS:, COMPLETE:, READY:, or REQUEST_CONTEXT: to indicate intent.")],
    project_id: str,
    from_agent: Annotated[str, Field(description="Your agent_id UUID (the executor identity, not job_id).")],
    message_type: Annotated[str, Field(description="Message type: 'direct' (to specific agents), 'broadcast' (to all), or 'system' (internal). Default: 'direct'.")] = "direct",
    priority: Annotated[str, Field(description="Priority: 'low', 'normal', 'high', or 'critical'. Default: 'normal'.")] = "normal",
    requires_action: Annotated[bool, Field(description="True if recipient must act (rework, review, respond). False for informational messages. Only action-required messages trigger reactivation of completed agents.")] = False,
    ctx: Context = None,
) -> dict:
    """Send a message to one or more agents."""
    return await _call_tool(
        ctx,
        "send_message",
        {
            "to_agents": to_agents,
            "content": content,
            "project_id": project_id,
            "from_agent": from_agent,
            "message_type": message_type,
            "priority": priority,
            "requires_action": requires_action,
        },
    )


@mcp.tool(
    description=("Receive pending messages for current agent with optional filtering (Handover 0360)"),
)
async def receive_messages(
    agent_id: Annotated[str, Field(description="Your agent_id UUID. Required to receive your messages.")] = "",
    limit: Annotated[int, Field(description="Max messages to return. Default: 10.")] = 10,
    exclude_self: Annotated[bool, Field(description="Exclude messages you sent yourself. Default: true.")] = True,
    exclude_progress: Annotated[bool, Field(description="Exclude auto-generated progress messages. Default: true.")] = True,
    message_types: Annotated[list[str] | None, Field(description="Filter by type: ['direct'], ['broadcast'], ['system']. Omit for all types.")] = None,
    ctx: Context = None,
) -> dict:
    """Receive pending messages with optional filtering. Auto-acknowledges and removes from queue."""
    kwargs: dict[str, Any] = {"limit": limit, "exclude_self": exclude_self, "exclude_progress": exclude_progress}
    if agent_id:
        kwargs["agent_id"] = agent_id
    if message_types is not None:
        kwargs["message_types"] = message_types
    return await _call_tool(ctx, "receive_messages", kwargs)


@mcp.tool(
    description=(
        "List messages with optional filters (read-only, does NOT acknowledge). "
        "Use receive_messages() instead for normal message processing — it auto-acknowledges. "
        "This tool is for inspection only."
    ),
)
async def list_messages(
    agent_id: Annotated[str, Field(description="Filter by recipient agent_id UUID. Optional.")] = "",
    status: Annotated[str, Field(description="Filter by status: 'pending', 'acknowledged', 'completed', 'failed'. Optional.")] = "",
    limit: Annotated[int, Field(description="Max messages to return. Default: 50.")] = 50,
    ctx: Context = None,
) -> dict:
    """List messages with optional filters (read-only)."""
    kwargs: dict[str, Any] = {}
    if agent_id:
        kwargs["agent_id"] = agent_id
    if status:
        kwargs["status"] = status
    if limit:
        kwargs["limit"] = limit
    return await _call_tool(ctx, "list_messages", kwargs)


# ---------------------------------------------------------------------------
# Task & Utility Tools (4)
# ---------------------------------------------------------------------------


@mcp.tool(
    description="Create a new task (technical debt/TODO) bound to the active product. Requires an active product to be set.",
)
async def create_task(
    title: Annotated[str, Field(description="Task title (required). Short, actionable description.")],
    description: Annotated[str, Field(description="Detailed task description (required).")],
    priority: Annotated[str, Field(description="Priority: 'low', 'medium', 'high', or 'critical'. Default: 'medium'.")] = "medium",
    category: Annotated[str, Field(description="Optional category label for grouping.")] = "",
    assigned_to: Annotated[str, Field(description="Optional assignee name.")] = "",
    ctx: Context = None,
) -> dict:
    """Create a new task bound to the active product."""
    kwargs: dict[str, Any] = {"title": title, "description": description, "priority": priority}
    if category:
        kwargs["category"] = category
    if assigned_to:
        kwargs["assigned_to"] = assigned_to
    return await _call_tool(ctx, "create_task", kwargs)


@mcp.tool(description="Check MCP server health status")
async def health_check(ctx: Context = None) -> dict:
    """Check MCP server health status."""
    accessor = _get_tool_accessor()
    return await accessor.health_check()


@mcp.tool(
    description=(
        "Discover available system categories and configuration for the current tenant. "
        "Call this BEFORE creating projects to see valid project_type values. "
        "Valid categories: 'project_types'. Returns items with abbreviation, label, color."
    ),
)
async def discovery(
    category: str,
    ctx: Context = None,
) -> dict:
    """Query available system categories.

    Args:
        category: What to look up. Valid values: 'project_types'.
    """
    return await _call_tool(ctx, "discovery", {"category": category})


@mcp.tool(
    description=(
        "First-time setup: downloads slash commands and agent templates as a ZIP. "
        "Run once after connecting. Installs with default models. "
        "To customize models later, run /gil_get_agents (or $gil-get-agents for Codex). "
        "IMPORTANT: You MUST pass the platform parameter identifying which CLI tool you are. "
        "Use 'claude_code' for Claude Code, 'gemini_cli' for Gemini CLI, 'codex_cli' for Codex CLI."
    ),
)
async def giljo_setup(
    platform: Literal["claude_code", "gemini_cli", "codex_cli", "generic"] = "claude_code",
    ctx: Context = None,
) -> dict:
    """Install slash commands and agent templates for your CLI tool."""
    logger.info("giljo_setup called with platform=%s", platform)

    result = await _call_tool(ctx, "bootstrap_setup", {"platform": platform})

    # Emit setup:bootstrap_complete WebSocket event
    try:
        from api.app import state as app_state

        ws_manager = getattr(app_state, "websocket_manager", None)
        tenant_key = _resolve_tenant(ctx)
        if ws_manager and tenant_key:
            from api.events.schemas import EventFactory

            event = EventFactory.tenant_envelope(
                event_type="setup:bootstrap_complete",
                tenant_key=tenant_key,
                data={"platform": platform},
            )
            await ws_manager.broadcast_event_to_tenant(tenant_key=tenant_key, event=event)
    except (OSError, RuntimeError, ValueError, TypeError, AttributeError, ImportError, KeyError) as e:
        logger.warning(f"setup:bootstrap_complete emission failed: {type(e).__name__}: {e}")

    return result


@mcp.tool(
    description=(
        "Generate a one-time download URL for agent templates or slash commands. Returns a URL valid for 15 minutes."
    ),
)
async def generate_download_token(
    content_type: str,
    platform: str = "claude_code",
    ctx: Context = None,
) -> dict:
    """Generate one-time download URL for agent templates/slash commands."""
    return await _call_tool(
        ctx,
        "generate_download_token",
        {
            "content_type": content_type,
            "platform": platform,
        },
    )


@mcp.tool(
    description=(
        "Export agent templates formatted for the target CLI platform. "
        "Returns pre-assembled files for Claude Code/Gemini or structured data for Codex CLI."
    ),
)
async def get_agent_templates_for_export(
    platform: str,
    ctx: Context = None,
) -> dict:
    """Export agent templates for target CLI platform."""
    result = await _call_tool(ctx, "get_agent_templates_for_export", {"platform": platform})

    # Handover 0855b: Emit setup:agents_downloaded when CLI fetches templates via MCP
    try:
        from api.app import state as app_state

        ws_manager = getattr(app_state, "websocket_manager", None)
        tenant_key = _resolve_tenant(ctx)
        if ws_manager and tenant_key:
            from api.events.schemas import EventFactory

            agent_count = len(result.get("agents", [])) if isinstance(result, dict) else 0
            event = EventFactory.setup_agents_downloaded(
                tenant_key=tenant_key,
                user_id="mcp_tool",
                agent_count=agent_count,
            )
            await ws_manager.broadcast_event_to_tenant(tenant_key=tenant_key, event=event)
            logger.info(f"setup:agents_downloaded emitted for tenant {tenant_key}, {agent_count} agents")
        else:
            logger.warning(
                f"setup:agents_downloaded NOT emitted: ws_manager={ws_manager is not None}, tenant_key={tenant_key}"
            )
    except (OSError, RuntimeError, ValueError, TypeError, AttributeError, ImportError, KeyError) as e:
        logger.warning(f"setup:agents_downloaded emission failed: {type(e).__name__}: {e}")

    return result


# ---------------------------------------------------------------------------
# Agent Coordination Tools (6)
# ---------------------------------------------------------------------------


@mcp.tool(
    description=(
        "Get pending jobs (status='waiting') for a specific agent type. "
        "Used by agents to find work assigned to their role."
    ),
)
async def get_pending_jobs(
    agent_display_name: Annotated[str, Field(description="Agent role to query, e.g. 'implementer', 'tester', 'analyzer'. Matches against job's agent_display_name.")],
    ctx: Context = None,
) -> dict:
    """Get pending jobs for agent type."""
    return await _call_tool(ctx, "get_pending_jobs", {"agent_display_name": agent_display_name})


@mcp.tool(
    description=(
        "Report incremental progress with TODO items. Backend auto-calculates "
        "percent and step counts. Also auto-wakes idle/sleeping/blocked agents "
        "back to 'working' status."
    ),
)
async def report_progress(
    job_id: str,
    todo_items: Annotated[list[dict] | None, Field(description="FULL TODO list (replaces existing). Each item: {content: str, status: 'pending'|'in_progress'|'completed'}. Include ALL items — completed + in_progress + pending. Never a partial list.")] = None,
    todo_append: Annotated[list[dict] | None, Field(description="NEW items to append (does not replace). Same format as todo_items. Use this to add tasks discovered during work without overwriting existing list.")] = None,
    ctx: Context = None,
) -> dict:
    """Report incremental progress."""
    kwargs: dict[str, Any] = {"job_id": job_id}
    if todo_items is not None:
        kwargs["todo_items"] = todo_items
    if todo_append is not None:
        kwargs["todo_append"] = todo_append
    return await _call_tool(ctx, "report_progress", kwargs)


@mcp.tool(
    description=(
        "Mark job as completed with results. Called by: ANY AGENT when all assigned "
        "work is done. System will REJECT if unread messages remain or TODOs are incomplete. "
        "Check receive_messages() and verify all TODOs are completed before calling."
    ),
)
async def complete_job(
    job_id: str,
    result: Annotated[dict, Field(description="Completion result dict. Expected keys: 'summary' (str, what was accomplished), 'files_changed' (list[str], optional), 'decisions_made' (list[str], optional).")],
    ctx: Context = None,
) -> dict:
    """Mark job as completed with results."""
    return await _call_tool(ctx, "complete_job", {"job_id": job_id, "result": result})


@mcp.tool(
    description=(
        "Mark a completed agent job as closed (final acceptance). "
        "Called by: ORCHESTRATOR ONLY after verifying deliverables. "
        "Transition: complete → closed. Closed jobs will not be "
        "auto-reactivated on new messages. Use 'decommissioned' only "
        "for failed/replaced/abandoned agents."
    ),
)
async def close_job(
    job_id: str,
    ctx: Context = None,
) -> dict:
    """Accept completed work and close the job permanently."""
    return await _call_tool(ctx, "close_job", {"job_id": job_id})


@mcp.tool(
    description=(
        "Resume work on a completed job after receiving a follow-up message. "
        "Only works when status is 'blocked' (auto-set when a message arrives "
        "for a completed agent). After reactivating, use report_progress with "
        "todo_append to add new steps - do not overwrite completed steps."
    ),
)
async def reactivate_job(
    job_id: str,
    reason: str = "",
    ctx: Context = None,
) -> dict:
    """Resume work on a completed job."""
    kwargs: dict[str, Any] = {"job_id": job_id}
    if reason:
        kwargs["reason"] = reason
    return await _call_tool(ctx, "reactivate_job", kwargs)


@mcp.tool(
    description=(
        "Acknowledge a post-completion message without resuming work. "
        "Returns you to complete status. Use when the message is informational "
        "and no action is required."
    ),
)
async def dismiss_reactivation(
    job_id: str,
    reason: str = "",
    ctx: Context = None,
) -> dict:
    """Acknowledge post-completion message without resuming."""
    kwargs: dict[str, Any] = {"job_id": job_id}
    if reason:
        kwargs["reason"] = reason
    return await _call_tool(ctx, "dismiss_reactivation", kwargs)


@mcp.tool(
    description=(
        "Set agent resting or blocked status. Valid statuses: 'blocked' (need human help, "
        "shows 'Needs Input'), 'idle' (monitoring, shows 'Monitoring'), 'sleeping' "
        "(periodic auto-check, shows 'Sleeping'). All three auto-wake back to 'working' "
        "when report_progress() is called."
    ),
)
async def set_agent_status(
    job_id: str,
    status: Annotated[str, Field(description="Target status: 'blocked', 'idle', or 'sleeping'. Other statuses are not valid here.")],
    reason: Annotated[str, Field(description="Human-readable reason. REQUIRED for 'blocked' status. Displayed on dashboard.")] = "",
    wake_in_minutes: Annotated[int | None, Field(description="Sleep interval hint for 'sleeping' status. Agent will auto-check-in after this many minutes.")] = None,
    ctx: Context = None,
) -> dict:
    """Set agent resting/blocked status."""
    return await _call_tool(
        ctx,
        "set_agent_status",
        {
            "job_id": job_id,
            "status": status,
            "reason": reason,
            "wake_in_minutes": wake_in_minutes,
        },
    )


# ---------------------------------------------------------------------------
# Orchestration Tools (4)
# ---------------------------------------------------------------------------


_PLACEHOLDER_JOB_IDS = {"unknown", "none", "null", "", "undefined", "placeholder"}


@mcp.tool(
    description=(
        "Fetch agent-specific mission and context. Called by: ANY AGENT immediately after "
        "receiving thin prompt from spawn_agent_job. Agent's first action. Returns targeted "
        "mission for this specific agent (not entire project vision). Part of thin-client "
        "architecture - mission stored in database, not embedded in prompt. Idempotent."
    ),
)
async def get_agent_mission(
    job_id: str,
    ctx: Context = None,
) -> dict:
    """Fetch agent-specific mission and context."""
    if job_id.strip().lower() in _PLACEHOLDER_JOB_IDS:
        return {
            "error": "no_job_context",
            "message": (
                "This agent was launched without orchestration context. "
                "To use GiljoAI orchestration, the orchestrator must call "
                "spawn_agent_job() first, then pass the returned thin prompt "
                "(which contains the real job_id) to this agent. "
                "Without a valid job_id, you can still operate using your "
                "role instructions — just skip the GiljoAI protocol steps."
            ),
        }
    return await _call_tool(ctx, "get_agent_mission", {"job_id": job_id})


@mcp.tool(
    description=(
        "Create specialist agent job for execution. Called by: ORCHESTRATOR ONLY during "
        "staging to delegate work (Step 4 of workflow). Orchestrator breaks down mission "
        "into agent-specific tasks and spawns agents who EXECUTE the work. Returns job_id "
        "and thin prompt (~10 lines). Agent later calls get_agent_mission() to fetch full "
        "mission. Creates database record linking agent to project."
    ),
)
async def spawn_agent_job(
    agent_display_name: Annotated[str, Field(description="Agent role label for UI display, e.g. 'implementer', 'tester', 'analyzer'.")],
    agent_name: Annotated[str, Field(description="Agent template name from agent_templates list, e.g. 'tdd-implementor', 'code-reviewer'.")],
    mission: Annotated[str, Field(description="The specific work assignment for this agent. Be detailed — this becomes the agent's full mission.")],
    project_id: str,
    phase: Annotated[int | None, Field(description="Execution phase number (1, 2, 3...). Phase 1 runs first, phase 2 after phase 1 completes. Must be an integer.")] = None,
    predecessor_job_id: Annotated[str, Field(description="Job ID of predecessor agent whose work this agent continues. Agent can call get_agent_result(predecessor_job_id) to read prior work.")] = "",
    ctx: Context = None,
) -> dict:
    """Create specialist agent job for execution."""
    kwargs: dict[str, Any] = {
        "agent_display_name": agent_display_name,
        "agent_name": agent_name,
        "mission": mission,
        "project_id": project_id,
    }
    if phase is not None:
        kwargs["phase"] = phase
    if predecessor_job_id:
        kwargs["predecessor_job_id"] = predecessor_job_id
    return await _call_tool(ctx, "spawn_agent_job", kwargs)


@mcp.tool(
    description=(
        "Fetch the completion result of a finished agent job. Returns the structured "
        "result dict (summary, artifacts, commits) stored when the agent called "
        "complete_job. Use this to read what a predecessor agent accomplished."
    ),
)
async def get_agent_result(
    job_id: str,
    ctx: Context = None,
) -> dict:
    """Fetch completion result of finished agent job."""
    return await _call_tool(ctx, "get_agent_result", {"job_id": job_id})


@mcp.tool(
    description=(
        "Monitor workflow progress across all project agents. Returns active/completed/"
        "blocked/closed/silent/decommissioned/pending agent counts and progress_percent (0-100). "
        "Use exclude_job_id to omit the calling orchestrator's own job from counts."
    ),
)
async def get_workflow_status(
    project_id: str,
    exclude_job_id: str = "",
    ctx: Context = None,
) -> dict:
    """Monitor workflow progress across all project agents."""
    kwargs: dict[str, Any] = {"project_id": project_id}
    if exclude_job_id:
        kwargs["exclude_job_id"] = exclude_job_id
    return await _call_tool(ctx, "get_workflow_status", kwargs)


# ---------------------------------------------------------------------------
# Context & Closeout Tools (4)
# ---------------------------------------------------------------------------


@mcp.tool(
    description=(
        "Unified context fetcher. Retrieves product/project context by category with "
        "depth control. Categories: product_core (~100 tokens), vision_documents (0-24K), "
        "tech_stack (200-400), architecture (300-1.5K), testing (0-400), memory_360 "
        "(500-5K), git_history (500-5K), agent_templates (400-2.4K), project (~300), "
        "self_identity (agent template content). Single tool replaces 9 individual tools."
    ),
)
async def fetch_context(
    product_id: str,
    project_id: str = "",
    agent_name: Annotated[str, Field(description="Agent template name (e.g. 'tdd-implementor') for self_identity category. Optional.")] = "",
    categories: Annotated[list[str] | None, Field(description="List of categories to fetch: 'product_core', 'vision_documents', 'tech_stack', 'architecture', 'testing', 'memory_360', 'git_history', 'agent_templates', 'project', 'self_identity'. Must be a list, e.g. ['tech_stack', 'architecture']. Pass null/omit for all.")] = None,
    depth_config: Annotated[dict | None, Field(description="Optional depth overrides per category, e.g. {'vision_documents': 'full', 'git_history': 'summary'}.")] = None,
    output_format: Annotated[str, Field(description="Output format: 'structured' (default) or 'flat'.")] = "structured",
    ctx: Context = None,
) -> dict:
    """Unified context fetcher by category with depth control."""
    if isinstance(categories, str):
        categories = [categories]
    kwargs: dict[str, Any] = {"product_id": product_id, "output_format": output_format}
    if project_id:
        kwargs["project_id"] = project_id
    if agent_name:
        kwargs["agent_name"] = agent_name
    if categories is not None:
        kwargs["categories"] = categories
    if depth_config is not None:
        kwargs["depth_config"] = depth_config
    return await _call_tool(ctx, "fetch_context", kwargs)


@mcp.tool(
    description=(
        "Close project and update 360 Memory with sequential history entry. "
        "Called by: ORCHESTRATOR at project completion. Triggers WebSocket "
        "'product_memory_updated' event for UI updates. "
        "All agents MUST be in 'complete', 'closed', or 'decommissioned' status before calling. "
        "If blocked, resolve each agent via report_progress + complete_job first. "
        "IMPORTANT: Before calling, run `git log --oneline` for the project branch "
        "and pass the commits as git_commits. Each entry needs: sha, message, author. "
        "Optional fields: date (ISO 8601), files_changed (int), lines_added (int)."
    ),
)
async def close_project_and_update_memory(
    project_id: str,
    summary: Annotated[str, Field(description="Brief summary of project outcome.")],
    key_outcomes: Annotated[list[str], Field(description="List of key achievements (max 20).")],
    decisions_made: Annotated[list[str], Field(description="List of key decisions with rationale (max 20).")],
    git_commits: Annotated[list[dict] | None, Field(description="Git commits from project branch. Each: {sha: str, message: str, author: str}. Run 'git log --oneline' first.")] = None,
    ctx: Context = None,
) -> dict:
    """Close project and update 360 Memory."""
    kwargs: dict[str, Any] = {
        "project_id": project_id,
        "summary": summary,
        "key_outcomes": key_outcomes,
        "decisions_made": decisions_made,
        "force": False,
    }
    if git_commits is not None:
        kwargs["git_commits"] = git_commits
    return await _call_tool(ctx, "close_project_and_update_memory", kwargs)


@mcp.tool(
    description=(
        "Write a 360 memory entry for project completion or handover. Called by "
        "orchestrator on completion, or by agents on handover. Appends to "
        "Product.product_memory.sequential_history. "
        "IMPORTANT: Before calling, run `git log --oneline` for the project branch "
        "and pass the commits as git_commits. Each entry needs: sha, message, author. "
        "Optional fields: date (ISO 8601), files_changed (int), lines_added (int)."
    ),
)
async def write_360_memory(
    project_id: str,
    summary: Annotated[str, Field(description="Brief summary of what was accomplished or handed over.")],
    key_outcomes: Annotated[list[str], Field(description="List of key outcomes/achievements (max 20).")],
    decisions_made: Annotated[list[str], Field(description="List of key decisions with rationale (max 20).")],
    entry_type: Annotated[str, Field(description="Entry type: 'project_completion' (orchestrator closeout), 'handover_closeout' (agent context exhaustion handover), or 'session_handover' (session continuation).")] = "project_completion",
    author_job_id: Annotated[str, Field(description="Job ID of the authoring agent (usually the orchestrator's job_id).")] = "",
    git_commits: Annotated[list[dict] | None, Field(description="Git commits from project branch. Each entry: {sha: str, message: str, author: str}. Optional: date (ISO 8601), files_changed (int), lines_added (int).")] = None,
    ctx: Context = None,
) -> dict:
    """Write 360 memory entry for project completion/handover."""
    kwargs: dict[str, Any] = {
        "project_id": project_id,
        "summary": summary,
        "key_outcomes": key_outcomes,
        "decisions_made": decisions_made,
        "entry_type": entry_type,
    }
    if author_job_id:
        kwargs["author_job_id"] = author_job_id
    if git_commits is not None:
        kwargs["git_commits"] = git_commits
    return await _call_tool(ctx, "write_360_memory", kwargs)


# ---------------------------------------------------------------------------
# Tuning Tool (1)
# ---------------------------------------------------------------------------


@mcp.tool(
    description=(
        "Submit product context tuning proposals after comparing current product "
        "context against recent project history. Called after analyzing the tuning "
        "comparison prompt."
    ),
)
async def submit_tuning_review(
    product_id: str,
    proposals: list[dict],
    overall_summary: str = "",
    ctx: Context = None,
) -> dict:
    """Submit product context tuning proposals."""
    kwargs: dict[str, Any] = {"product_id": product_id, "proposals": proposals}
    if overall_summary:
        kwargs["overall_summary"] = overall_summary
    return await _call_tool(ctx, "submit_tuning_review", kwargs)


# ---------------------------------------------------------------------------
# Vision Analysis Tools (2)
# ---------------------------------------------------------------------------


@mcp.tool(
    name="gil_get_vision_doc",
    description=(
        "Retrieve a product's vision document with extraction instructions. "
        "Call WITHOUT chunk to get metadata (total_chunks, extraction_instructions). "
        "Then call WITH chunk=1, chunk=2, etc. to retrieve each chunk's content "
        "one at a time. Read ALL chunks before calling gil_write_product."
    ),
)
async def get_vision_doc(
    product_id: str,
    chunk: int | None = None,
    ctx: Context = None,
) -> dict:
    """Retrieve product's vision document."""
    kwargs: dict[str, Any] = {"product_id": product_id}
    if chunk is not None:
        kwargs["chunk"] = chunk
    return await _call_tool(ctx, "get_vision_doc", kwargs)


@mcp.tool(
    name="gil_write_product",
    description=(
        "Write structured product fields extracted from vision document analysis. "
        "Performs merge-write: only updates fields that are provided. Creates child "
        "table rows (tech_stack, architecture, test_config) on first write. "
        "Include summary_33 and summary_66 for AI-generated summaries. "
        "target_platforms must be from: windows, linux, macos, android, ios, web, all."
    ),
)
async def write_product_from_analysis(
    product_id: str,
    product_name: str = "",
    product_description: str = "",
    core_features: str = "",
    programming_languages: str = "",
    frontend_frameworks: str = "",
    backend_frameworks: str = "",
    databases: str = "",
    infrastructure: str = "",
    target_platforms: list[str] | None = None,
    architecture_pattern: str = "",
    design_patterns: str = "",
    api_style: str = "",
    architecture_notes: str = "",
    quality_standards: str = "",
    testing_strategy: str = "",
    testing_frameworks: str = "",
    test_coverage_target: int | None = None,
    summary_33: str = "",
    summary_66: str = "",
    ctx: Context = None,
) -> dict:
    """Write structured product fields from vision document analysis."""
    # Build kwargs with only non-empty values (merge-write semantics)
    kwargs: dict[str, Any] = {"product_id": product_id}
    fields = {
        "product_name": product_name,
        "product_description": product_description,
        "core_features": core_features,
        "programming_languages": programming_languages,
        "frontend_frameworks": frontend_frameworks,
        "backend_frameworks": backend_frameworks,
        "databases": databases,
        "infrastructure": infrastructure,
        "architecture_pattern": architecture_pattern,
        "design_patterns": design_patterns,
        "api_style": api_style,
        "architecture_notes": architecture_notes,
        "quality_standards": quality_standards,
        "testing_strategy": testing_strategy,
        "testing_frameworks": testing_frameworks,
        "summary_33": summary_33,
        "summary_66": summary_66,
    }
    kwargs.update({k: v for k, v in fields.items() if v})
    if target_platforms is not None:
        kwargs["target_platforms"] = target_platforms
    if test_coverage_target is not None:
        kwargs["test_coverage_target"] = test_coverage_target
    return await _call_tool(ctx, "write_product_from_analysis", kwargs)


# ---------------------------------------------------------------------------
# Auth Middleware (ASGI) -- validates Bearer token, injects tenant_key
# ---------------------------------------------------------------------------


class MCPAuthMiddleware:
    """
    ASGI middleware that validates Bearer token (JWT or API key) and injects
    tenant_key into the ASGI scope state before the MCP SDK processes the request.

    Auth flow:
    1. Extract Authorization: Bearer <token> or X-API-Key header
    2. Try JWT validation first (fast, stateless)
    3. Fall back to API key via MCPSessionManager (stateful, PostgreSQL)
    4. Attach tenant_key + user_id to scope["state"]
    """

    def __init__(self, app: ASGIApp):
        self.app = app
        self._notified_keys: set[str] = set()  # Track keys we've already emitted setup:tool_connected for

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = StarletteRequest(scope, receive)

        # Extract credentials from headers
        api_key_value: str | None = request.headers.get("x-api-key")
        bearer_token: str | None = None

        if not api_key_value:
            auth_header = request.headers.get("authorization", "")
            if auth_header.lower().startswith("bearer "):
                bearer_token = auth_header[7:]

        if not api_key_value and not bearer_token:
            resp = JSONResponse(
                {"error": "Authentication required (Authorization: Bearer or X-API-Key)"},
                status_code=401,
            )
            await resp(scope, receive, send)
            return

        # Resolve tenant from credentials
        tenant_key: str | None = None
        user_id: str | None = None
        api_key_id: int | None = None

        # Path 1: JWT token
        if bearer_token and not api_key_value:
            try:
                payload = JWTManager.verify_token(bearer_token)
                tenant_key = payload["tenant_key"]
                user_id = payload["sub"]
            except (ValueError, KeyError, RuntimeError, HTTPException):
                # Not a valid JWT -- treat as API key (backward compatibility)
                api_key_value = bearer_token

        # Path 2: API key (via MCPSessionManager for DB lookup)
        if not tenant_key and api_key_value:
            try:
                from api.app import state
                from api.endpoints.mcp_session import MCPSessionManager

                if not state.db_manager:
                    logger.error("db_manager not available for MCP auth")
                    resp = JSONResponse({"error": "Database not initialized"}, status_code=503)
                    await resp(scope, receive, send)
                    return

                async with state.db_manager.get_session_async() as db:
                    session_mgr = MCPSessionManager(db)
                    session = await session_mgr.get_or_create_session(api_key_value)
                    if session:
                        tenant_key = session.tenant_key
                        user_id = getattr(session, "user_id", None)
                        api_key_id = session.api_key_id

                        # Passive IP logging (non-blocking)
                        if api_key_id:
                            client_ip = request.client.host if request.client else "unknown"
                            try:
                                await session_mgr.log_ip(api_key_id, client_ip)
                            except (OSError, ValueError, KeyError):
                                logger.debug("IP logging failed (non-blocking)")
            except (OSError, ValueError, KeyError, RuntimeError):
                logger.exception("API key authentication failed")

        if not tenant_key:
            resp = JSONResponse({"error": "Invalid credentials"}, status_code=401)
            await resp(scope, receive, send)
            return

        # Inject into ASGI scope state -- accessible in tool handlers via ctx
        if "state" not in scope:
            scope["state"] = {}
        scope["state"]["tenant_key"] = tenant_key
        scope["state"]["user_id"] = user_id

        # Handover 0855b: Emit setup:tool_connected on FIRST MCP auth per key
        # (replaces emission from deleted mcp_http.py after 0846 SDK migration)
        notify_key = f"{tenant_key}:{api_key_id or user_id}"
        if notify_key not in self._notified_keys:
            self._notified_keys.add(notify_key)
            try:
                from api.app import state as app_state

                ws_manager = getattr(app_state, "websocket_manager", None)
                if ws_manager and tenant_key:
                    from api.events.schemas import EventFactory

                    event = EventFactory.setup_tool_connected(
                        tenant_key=tenant_key,
                        user_id=str(user_id) if user_id else "unknown",
                        tool_name="mcp_connected",
                    )
                    await ws_manager.broadcast_event_to_tenant(tenant_key=tenant_key, event=event)
            except (OSError, RuntimeError, ValueError, TypeError, AttributeError, ImportError):
                pass  # Fire-and-forget, non-blocking

        await self.app(scope, receive, send)


# ---------------------------------------------------------------------------
# Build the mountable Starlette app with auth middleware
# ---------------------------------------------------------------------------


def get_mcp_asgi_app():
    """
    Build the MCP ASGI app with auth middleware applied.

    Returns a pure ASGI callable: MCPAuthMiddleware → StreamableHTTPASGIApp.
    Called from app.py via a direct FastAPI route (not app.mount, to avoid
    the 307 trailing-slash redirect).

    Lifecycle: Call start_mcp_session_manager() / stop_mcp_session_manager()
    in the FastAPI lifespan (see app.py).
    """
    # Ensure session manager is created
    if mcp._session_manager is None:
        mcp.streamable_http_app()

    # Build the SDK's ASGI handler directly
    from mcp.server.fastmcp.server import StreamableHTTPASGIApp

    asgi_handler = StreamableHTTPASGIApp(mcp._session_manager)

    # Wrap with auth middleware — pure ASGI chain
    return MCPAuthMiddleware(asgi_handler)


# ---------------------------------------------------------------------------
# Lifecycle management — called from FastAPI lifespan in app.py
# ---------------------------------------------------------------------------

_session_manager_cm = None


async def start_mcp_session_manager():
    """Start the SDK's session manager task group. Call during FastAPI startup."""
    global _session_manager_cm  # noqa: PLW0603
    if not hasattr(mcp, "_session_manager") or mcp._session_manager is None:
        # Force creation by building the app (idempotent if already built)
        mcp.streamable_http_app()
    _session_manager_cm = mcp._session_manager.run()
    await _session_manager_cm.__aenter__()
    logger.info("MCP SDK session manager started")


async def stop_mcp_session_manager():
    """Stop the SDK's session manager task group. Call during FastAPI shutdown."""
    global _session_manager_cm  # noqa: PLW0603
    if _session_manager_cm:
        await _session_manager_cm.__aexit__(None, None, None)
        _session_manager_cm = None
        logger.info("MCP SDK session manager stopped")
