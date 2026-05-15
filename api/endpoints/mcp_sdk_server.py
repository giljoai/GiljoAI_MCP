# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
MCP SDK Server -- Streamable HTTP transport using official Anthropic MCP Python SDK.

Standard MCP protocol transport using official Anthropic MCP Python SDK (FastMCP).
transport. All tools delegate to the existing ToolAccessor methods. Auth and tenant
isolation are handled by ASGI middleware applied to the Starlette sub-app.

Handover: 0846a (transport replacement), 0846b (security integration)
"""

import inspect
import json
import logging
from typing import Annotated, Any, Literal

from fastapi import HTTPException
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import BaseModel, Field
from starlette.requests import Request as StarletteRequest
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from giljo_mcp.auth.jwt_manager import JWTAudienceMismatchError, JWTManager
from giljo_mcp.http.url_resolver import get_canonical_mcp_resource_uri_from_scope


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
# Tool scope registry (API-0021b): scope-aware MCP tool gating
#
# Single source of truth for both list_tools advertise filter and call_tool
# dispatch gate. Three scopes:
#   - mcp:read   : pure-read tools, no DB writes, no agent-state mutation
#   - mcp:write  : writes confined to user-owned product/project/task/memory
#   - mcp:agent  : orchestration primitives (spawn, complete_job, send_message,
#                  status mutations, mission edits, …). Privilege-escalation
#                  surface — NEVER grantable through OAuth /authorize.
#
# Defense-in-depth: the dispatch gate enforces server-side. Hiding from
# tools/list alone is insufficient — a JWT caller can still craft tools/call.
# ---------------------------------------------------------------------------

SCOPE_READ = "mcp:read"
SCOPE_WRITE = "mcp:write"
SCOPE_AGENT = "mcp:agent"

TOOL_SCOPES: dict[str, str] = {
    "create_project": SCOPE_WRITE,
    "list_projects": SCOPE_READ,
    "update_project": SCOPE_WRITE,
    "update_project_mission": SCOPE_AGENT,
    "update_agent_mission": SCOPE_AGENT,
    "get_orchestrator_instructions": SCOPE_READ,
    "send_message": SCOPE_AGENT,
    "receive_messages": SCOPE_AGENT,
    "inspect_messages": SCOPE_READ,
    "create_task": SCOPE_WRITE,
    "update_task": SCOPE_WRITE,
    "complete_task": SCOPE_WRITE,
    "list_tasks": SCOPE_READ,
    "request_approval": SCOPE_AGENT,
    "health_check": SCOPE_READ,
    "giljo_setup": SCOPE_WRITE,
    "generate_download_token": SCOPE_WRITE,
    "list_agent_templates": SCOPE_READ,
    "get_pending_jobs": SCOPE_AGENT,
    "report_progress": SCOPE_AGENT,
    "complete_job": SCOPE_AGENT,
    "close_job": SCOPE_AGENT,
    "reactivate_job": SCOPE_AGENT,
    "dismiss_reactivation": SCOPE_AGENT,
    "set_agent_status": SCOPE_AGENT,
    "get_agent_mission": SCOPE_AGENT,
    "spawn_job": SCOPE_AGENT,
    "get_agent_result": SCOPE_AGENT,
    "get_workflow_status": SCOPE_AGENT,
    "fetch_context": SCOPE_READ,
    "close_project_and_update_memory": SCOPE_AGENT,
    "write_360_memory": SCOPE_AGENT,
    "submit_tuning_review": SCOPE_WRITE,
    "get_vision_doc": SCOPE_READ,
    "update_product_fields": SCOPE_WRITE,
}


def _scopes_from_request(request: StarletteRequest | None) -> set[str] | None:
    """Resolve the caller's effective scope set from the ASGI request state.

    Returns:
        - None if the caller authenticated via API key (full bypass — API keys
          remain the only path to mcp:agent tools).
        - set[str] of scope tokens otherwise. Empty set means "no scopes
          granted" (advertise nothing, gate everything).
    """
    if request is None:
        # In-memory test transport has no HTTP request. Tests monkeypatch this
        # function directly when they want scope filtering exercised.
        return None
    state = request.scope.get("state", {}) if hasattr(request, "scope") else {}
    if state.get("auth_method") == "api_key":
        return None
    scopes = state.get("scopes")
    if not scopes:
        return set()
    return set(scopes)


# ---------------------------------------------------------------------------
# Helpers: resolve app-level state inside tool handlers
# ---------------------------------------------------------------------------


def _get_tool_accessor():
    """Lazy import to avoid circular dependency with api.app at module load."""
    from api.app_state import state

    if not state.tool_accessor:
        raise RuntimeError("Tool accessor not initialized")
    return state.tool_accessor


def _get_tenant_manager():
    from api.app_state import state

    return state.tenant_manager


def _resolve_tenant(ctx: Context) -> str:
    """Extract tenant_key from ASGI scope state (set by MCPAuthMiddleware)."""
    request: StarletteRequest = ctx.request_context.request
    tenant_key = request.scope.get("state", {}).get("tenant_key")
    if not tenant_key:
        raise RuntimeError("No tenant_key in request state -- auth middleware missing")
    return tenant_key


def _resolve_user_id(ctx: Context) -> str | None:
    """Extract user_id from ASGI scope state (set by MCPAuthMiddleware).

    Returns None if the request was authenticated by an API key whose session
    has no user_id back-reference (legacy keys). Callers must treat None as
    "skip user-scoped side effects".
    """
    request: StarletteRequest = ctx.request_context.request
    return request.scope.get("state", {}).get("user_id")


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

    # Per-tool MCP call counting (feeds dashboard statistics badge)
    from api.app_state import state as app_state

    app_state.mcp_call_count[tenant_key] = app_state.mcp_call_count.get(tenant_key, 0) + 1

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
            from api.app_state import state as app_state
            from giljo_mcp.services.silence_detector import auto_clear_silent

            ws_manager = getattr(app_state, "websocket_manager", None)
            async with app_state.db_manager.get_session_async() as db:
                await auto_clear_silent(db, job_id, ws_manager, tenant_key=tenant_key)
        except (OSError, RuntimeError, ValueError, TypeError, AttributeError, KeyError):
            logger.warning("auto_clear_silent failed for job_id=%s (non-blocking)", job_id)

        # Server-side heartbeat: update last_activity_at with 30s debounce
        try:
            from api.app_state import state as app_state
            from giljo_mcp.services.heartbeat import touch_heartbeat

            async with app_state.db_manager.get_session_async() as db:
                await touch_heartbeat(db, job_id, tenant_key=tenant_key)
        except (OSError, RuntimeError, ValueError, TypeError, AttributeError, KeyError):
            logger.debug("heartbeat update failed for job_id=%s (non-blocking)", job_id)

    # Wire-contract normalisation: every @mcp.tool wrapper in this module is
    # annotated `-> dict[str, Any]`, but service-layer methods return typed
    # Pydantic response models (MissionResponse, ProgressResult, SpawnResult,
    # SendMessageResult, etc.). FastMCP validates the return against the
    # annotation and rejects Pydantic instances with a DictModel error, which
    # surfaces to MCP clients while server-side state has already been
    # persisted. Normalise here so every tool produces a JSON-safe dict
    # regardless of which service layer it delegates to.
    if isinstance(result, BaseModel):
        return result.model_dump(mode="json")
    return result


# ---------------------------------------------------------------------------
# Project Management Tools (4)
# ---------------------------------------------------------------------------


@mcp.tool(
    description=(
        "Create a new project bound to the active product. "
        "Projects are classified by taxonomy: project_type + series_number forming a serial like FE-0001. "
        "Unknown project_type values are rejected with a ValidationError whose context includes "
        "valid_types: a list of {abbreviation, label} pairs registered for this tenant. "
        "Omitting project_type is allowed; the success response then includes the same hint. "
        "Project is created as inactive. Use the web dashboard to activate and launch."
    ),
)
async def create_project(
    name: str,
    description: str,
    project_type: str = "",
    series_number: int = 0,
    suffix: str = "",
    ctx: Context = None,
) -> dict[str, Any]:
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
        suffix: Single-letter suffix (a-z) for injecting projects into an existing
            series. E.g. series_number=5 + suffix="b" creates FE-0005b.
            Leave empty for no suffix.
    """
    params = {
        "name": name,
        "description": description,
        "project_type": project_type,
    }
    if series_number > 0:
        params["series_number"] = series_number
    if suffix:
        params["subseries"] = suffix
    return await _call_tool(ctx, "create_project", params)


@mcp.tool(
    description=(
        "List projects for the active product with server-side filtering (v1.2.1). "
        "Default returns only projects in active lifecycle (excludes completed, "
        "cancelled, terminated, deleted). The 'hidden' field is per-row UI "
        "declutter and does NOT affect default visibility -- agent sees hidden "
        "and non-hidden alike. Pass include_completed=true to retrieve archived "
        "projects. Pass hidden=true|false to filter explicitly when needed (rare). "
        "Prefer mode=triage|planning|audit|forensic over numeric depth (BE-5042). "
        "Requires an active product to be set."
    ),
)
async def list_projects(
    status: str = "",
    project_type: str = "",
    taxonomy_alias_prefix: str = "",
    created_after: str = "",
    created_before: str = "",
    completed_after: str = "",
    completed_before: str = "",
    include_completed: bool = False,
    hidden: str = "",
    summary_only: bool = True,
    depth: int = 0,
    status_filter: str = "",
    mode: str = "",
    memory_limit: int = 0,
    ctx: Context = None,
) -> dict[str, Any]:
    """List projects for the active product (v1.2.1 server-side filtering).

    Default returns only projects in active lifecycle. Four statuses are
    auto-excluded from the default response: completed, cancelled, terminated,
    deleted. The two returned by default are: active, inactive. The hidden
    column is per-row UI declutter and does NOT affect default visibility --
    agent sees hidden and non-hidden alike. Pass include_completed=true to
    retrieve archived projects. Pass hidden=true|false to filter explicitly
    when needed (rare).

    NOTE: status="deleted" returns soft-deleted rows. The default response
    hides soft-deleted projects (deleted_at IS NULL), but explicitly passing
    status="deleted" flips the soft-delete filter to deleted_at IS NOT NULL,
    so soft-deleted projects are reachable when the agent asks for them by
    status. Frontend StatusBadge enum parity is preserved either way.

    Args:
        status: Filter by status. Single value ("active") or comma-separated list
            ("active,inactive"). Valid values: active, inactive, completed,
            cancelled, terminated, deleted. When set, include_completed is
            ignored -- explicit status arg overrides the default exclusion.
        project_type: Filter by taxonomy type abbreviation. Single value ("BE")
            or comma-separated list ("BE,FE,INF"). Must match a configured type.
        taxonomy_alias_prefix: Prefix-match against taxonomy alias (e.g. "BE-50"
            matches BE-5001..BE-5099 but not BE-5100; "BE-5036" exact-matches one).
        created_after / created_before: ISO-8601 datetimes (e.g. "2026-01-01T00:00:00Z").
        completed_after / completed_before: ISO-8601 datetimes for completion window.
        include_completed: When True, archived projects (completed, cancelled,
            terminated, deleted) are included. Ignored when `status` is explicitly set.
        hidden: "true" / "false" / "" (empty = no filter, default).
        summary_only: When True (default), return only summary fields to minimize payload.
        depth: Detail level 0-3 when summary_only=False:
            0 = summary fields only.
            1 = + description, mission, agent job summary.
            2 = + 360 memory entries, agent job details.
            3 = + message history, git commits from 360 memory.
        status_filter: Legacy parameter -- prefer `status`. Accepts "all" or a single
            status string. Honored only when `status` is unset.
        mode: BE-5042 agent-facing projection (preferred over numeric depth).
            "triage"   = id+name+status+dates (cheapest).
            "planning" = + description, mission, agent counts.
            "audit"    = + memory headlines + agent summaries (default last 5
                         memory entries).
            "forensic" = + full memory bodies, agent results (no cap).
            When set, mode wins over numeric `depth`. Empty string = use depth.
        memory_limit: Cap memory entries returned (audit mode default 5, max 50).
            0 = use mode default. Forensic ignores the cap unless explicitly set.
    """
    # Normalize status -> list[str] | None
    status_arg: list[str] | str | None
    if not status:
        status_arg = None
    elif "," in status:
        status_arg = [s.strip() for s in status.split(",") if s.strip()]
    else:
        status_arg = status.strip()

    pt_arg: list[str] | str | None
    if not project_type:
        pt_arg = None
    elif "," in project_type:
        pt_arg = [s.strip() for s in project_type.split(",") if s.strip()]
    else:
        pt_arg = project_type.strip()

    # Parse hidden tri-state
    hidden_arg: bool | None
    if hidden == "" or hidden is None:
        hidden_arg = None
    elif str(hidden).lower() in ("true", "1", "yes"):
        hidden_arg = True
    elif str(hidden).lower() in ("false", "0", "no"):
        hidden_arg = False
    else:
        hidden_arg = None

    # Parse ISO datetimes
    from datetime import datetime as _dt

    from giljo_mcp.exceptions import ValidationError as _ValidationError

    def _maybe(s: str):
        if not s:
            return None
        try:
            return _dt.fromisoformat(s.replace("Z", "+00:00"))
        except (ValueError, TypeError) as exc:
            raise _ValidationError(f"Invalid ISO-8601 datetime '{s}'. Expected e.g. '2026-01-01T00:00:00Z'.") from exc

    return await _call_tool(
        ctx,
        "list_projects",
        {
            "status_filter": status_filter or None,
            "summary_only": summary_only,
            "depth": depth,
            "status": status_arg,
            "project_type": pt_arg,
            "taxonomy_alias_prefix": taxonomy_alias_prefix or None,
            "created_after": _maybe(created_after),
            "created_before": _maybe(created_before),
            "completed_after": _maybe(completed_after),
            "completed_before": _maybe(completed_before),
            "include_completed": include_completed,
            "hidden": hidden_arg,
            "mode": mode or None,
            "memory_limit": memory_limit or None,
        },
    )


@mcp.tool(
    description=(
        "Update project metadata (name, description, status). "
        "Project must belong to the active product. "
        "Only provided fields are updated — omit fields to leave them unchanged."
    ),
)
async def update_project(
    project_id: str,
    name: str = "",
    description: str = "",
    status: str = "",
    project_type: str = "",
    series_number: int = 0,
    suffix: str = "",
    ctx: Context = None,
) -> dict[str, Any]:
    """Update project metadata fields.

    Args:
        project_id: Project UUID (required).
        name: New project name (max 200 chars). Leave empty to keep current.
        description: New description (max 20000 chars). Leave empty to keep current.
        status: New status — "inactive", "active", "completed", or "cancelled". Leave empty to keep current.
        project_type: Taxonomy type abbreviation (e.g. FE, BE). Leave empty to keep current.
        series_number: Sequential number within the type series (1-9999). Use 0 to keep current.
        suffix: Single-letter suffix (a-z). Leave empty to keep current.
    """
    params: dict = {"project_id": project_id}
    if name:
        params["name"] = name
    if description:
        params["description"] = description
    if status:
        params["status"] = status
    if project_type:
        params["project_type"] = project_type
    if series_number > 0:
        params["series_number"] = series_number
    if suffix:
        params["subseries"] = suffix
    return await _call_tool(ctx, "update_project_metadata", params)


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
) -> dict[str, Any]:
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
) -> dict[str, Any]:
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
) -> dict[str, Any]:
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
    to_agents: Annotated[
        list[str],
        Field(
            description="List of recipient agent_id UUIDs (from get_workflow_status). Use ['all'] for broadcast. NEVER use display names like 'orchestrator' — always UUIDs."
        ),
    ],
    content: Annotated[
        str,
        Field(
            description="Message content. Prefix with BLOCKER:, PROGRESS:, COMPLETE:, READY:, or REQUEST_CONTEXT: to indicate intent."
        ),
    ],
    project_id: str,
    from_agent: Annotated[str, Field(description="Your agent_id UUID (the executor identity, not job_id).")],
    message_type: Annotated[
        str,
        Field(
            description="Message type: 'direct' (to specific agents), 'broadcast' (to all), or 'system' (internal). Default: 'direct'."
        ),
    ] = "direct",
    priority: Annotated[
        str, Field(description="Priority: 'low', 'normal', 'high', or 'critical'. Default: 'normal'.")
    ] = "normal",
    requires_action: Annotated[
        bool,
        Field(
            description="True if recipient must act (rework, review, respond). False for informational messages. Only action-required messages trigger reactivation of completed agents."
        ),
    ] = False,
    ctx: Context = None,
) -> dict[str, Any]:
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
    exclude_progress: Annotated[
        bool, Field(description="Exclude auto-generated progress messages. Default: true.")
    ] = True,
    message_types: Annotated[
        list[str] | None,
        Field(description="Filter by type: ['direct'], ['broadcast'], ['system']. Omit for all types."),
    ] = None,
    ctx: Context = None,
) -> dict[str, Any]:
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
async def inspect_messages(
    agent_id: Annotated[str, Field(description="Filter by recipient agent_id UUID. Optional.")] = "",
    status: Annotated[
        str, Field(description="Filter by status: 'pending', 'acknowledged', 'completed', 'failed'. Optional.")
    ] = "",
    limit: Annotated[int, Field(description="Max messages to return. Default: 50.")] = 50,
    ctx: Context = None,
) -> dict[str, Any]:
    """Inspect messages with optional filters (read-only)."""
    kwargs: dict[str, Any] = {}
    if agent_id:
        kwargs["agent_id"] = agent_id
    if status:
        kwargs["status"] = status
    if limit:
        kwargs["limit"] = limit
    return await _call_tool(ctx, "inspect_messages", kwargs)


# ---------------------------------------------------------------------------
# Task & Utility Tools (4)
# ---------------------------------------------------------------------------


@mcp.tool(
    description=(
        "Create a new task (technical debt/TODO) bound to the active product. "
        "Tasks are classified by task_type, a taxonomy abbreviation (e.g. BE, FE, INF) "
        "that must match a configured taxonomy_types row for the tenant. "
        "Unknown task_type values are rejected with a ValidationError whose context "
        "includes valid_types: a list of {abbreviation, label} pairs. "
        "Omitting task_type is allowed; the success response then includes the same hint. "
        "Requires an active product to be set."
    ),
)
async def create_task(
    title: Annotated[str, Field(description="Task title (required). Short, actionable description.")],
    description: Annotated[str, Field(description="Detailed task description (required).")],
    priority: Annotated[
        str, Field(description="Priority: 'low', 'medium', 'high', or 'critical'. Default: 'medium'.")
    ] = "medium",
    task_type: Annotated[
        str,
        Field(description="Taxonomy type abbreviation (e.g. BE, FE, INF). Must match a configured taxonomy_types row."),
    ] = "",
    assigned_to: Annotated[str, Field(description="Optional assignee name.")] = "",
    ctx: Context = None,
) -> dict[str, Any]:
    """Create a new task bound to the active product."""
    kwargs: dict[str, Any] = {"title": title, "description": description, "priority": priority}
    if task_type:
        kwargs["task_type"] = task_type
    if assigned_to:
        kwargs["assigned_to"] = assigned_to
    return await _call_tool(ctx, "create_task", kwargs)


@mcp.tool(
    description=(
        "Update task metadata (title, description, status, priority, task_type, due_date). "
        "Only provided fields are written; omit fields to leave them unchanged. "
        "Pass empty string for task_type to clear the FK (set to NULL). "
        "Unknown task_type abbreviations are rejected; the ValidationError context "
        "carries valid_types. Tenant-scoped; cross-tenant task_ids return "
        "ResourceNotFoundError."
    ),
)
async def update_task(
    task_id: Annotated[str, Field(description="Task UUID (required).")],
    title: Annotated[str, Field(description="New title; empty string keeps current.")] = "",
    description: Annotated[str, Field(description="New description; empty string keeps current.")] = "",
    status: Annotated[
        str,
        Field(description="New status: pending|in_progress|completed|blocked|cancelled."),
    ] = "",
    priority: Annotated[str, Field(description="New priority: low|medium|high|critical.")] = "",
    task_type: Annotated[str, Field(description="Taxonomy abbreviation (e.g. BE, FE). Empty string clears type.")] = "",
    due_date: Annotated[str, Field(description="ISO 8601 due date; empty string keeps current.")] = "",
    hidden: Annotated[
        str, Field(description="Per-row UI declutter flag: 'true'/'false'/'' (empty keeps current).")
    ] = "",
    ctx: Context = None,
) -> dict[str, Any]:
    """Update task metadata fields. Mirrors update_project."""
    params: dict[str, Any] = {"task_id": task_id}
    if title:
        params["title"] = title
    if description:
        params["description"] = description
    if status:
        params["status"] = status
    if priority:
        params["priority"] = priority
    if task_type:
        params["task_type"] = task_type
    if due_date:
        params["due_date"] = due_date
    if hidden != "":
        h = str(hidden).lower()
        if h in ("true", "1", "yes"):
            params["hidden"] = True
        elif h in ("false", "0", "no"):
            params["hidden"] = False
    return await _call_tool(ctx, "update_task", params)


@mcp.tool(
    description=(
        "Mark a task completed. Sets status=completed and completed_at=now(). "
        "Optional completion_notes are appended to the task description as an "
        "audit trail entry. Tenant-scoped."
    ),
)
async def complete_task(
    task_id: Annotated[str, Field(description="Task UUID (required).")],
    completion_notes: Annotated[str, Field(description="Optional notes appended to the task's audit trail.")] = "",
    ctx: Context = None,
) -> dict[str, Any]:
    """Mark a task completed with optional notes."""
    kwargs: dict[str, Any] = {"task_id": task_id}
    if completion_notes:
        kwargs["completion_notes"] = completion_notes
    return await _call_tool(ctx, "complete_task", kwargs)


@mcp.tool(
    description=(
        "List tasks for the current tenant. Two projection modes: "
        "'summary' (id, title, status, priority, task_type, taxonomy_alias, "
        "series_number, subseries, hidden, due_date, created_at) and 'full' "
        "(every column plus embedded task_type block; description is "
        "truncated to memory_limit chars when set). "
        "Filters: status, priority, task_type (abbreviation), due_before, hidden. "
        "The 'hidden' field is per-row UI declutter and does NOT affect "
        "default visibility -- agents see hidden and non-hidden alike. "
        "Pass hidden=true|false to filter explicitly when needed (rare). "
        "Every query is tenant-scoped."
    ),
)
async def list_tasks(
    mode: Annotated[
        Literal["summary", "full"],
        Field(description="Projection mode. Default 'summary'."),
    ] = "summary",
    status: Annotated[str, Field(description="Filter by exact status (e.g. 'pending').")] = "",
    priority: Annotated[str, Field(description="Filter by priority (low/medium/high/critical).")] = "",
    task_type: Annotated[str, Field(description="Filter by taxonomy abbreviation (e.g. 'BE').")] = "",
    due_before: Annotated[str, Field(description="ISO date; tasks with due_date < value.")] = "",
    hidden: Annotated[str, Field(description="'true'/'false'/'' (empty = no filter, default).")] = "",
    summary_only: Annotated[bool, Field(description="Alias for mode='summary'.")] = False,
    memory_limit: Annotated[int, Field(description="Truncate description in 'full' mode.")] = 0,
    ctx: Context = None,
) -> dict[str, Any]:
    """List tasks for the current tenant."""
    kwargs: dict[str, Any] = {"mode": mode}
    if status:
        kwargs["status"] = status
    if priority:
        kwargs["priority"] = priority
    if task_type:
        kwargs["task_type"] = task_type
    if due_before:
        kwargs["due_before"] = due_before
    if hidden != "":
        h = str(hidden).lower()
        if h in ("true", "1", "yes"):
            kwargs["hidden"] = True
        elif h in ("false", "0", "no"):
            kwargs["hidden"] = False
    if summary_only:
        kwargs["summary_only"] = True
    if memory_limit:
        kwargs["memory_limit"] = memory_limit
    return await _call_tool(ctx, "list_tasks", kwargs)


@mcp.tool(
    description=(
        "Request a user approval before continuing. Creates a user_approvals row "
        "and flips the calling agent to status='awaiting_user' atomically. "
        "Used at HITL gates (closeout with deferred findings, ambiguous decisions). "
        "Replaces the prose user_approval_required boolean. "
        "options is a list of {id, label} dicts presented to the user. "
        "Returns {approval_id, status}. Tenant-scoped. "
        "UI surface: the dashboard shows a passive 'needs input' pill (informational, "
        "NOT a clickable global banner). The actual decide buttons render inside the "
        "project's CloseoutModal via the ApprovalCard component -- users frequently miss "
        "this and respond verbally to the agent instead. "
        "Clearing awaiting_user: ONLY POST /api/approvals/{id}/decide clears the gate "
        "(ApprovalCard calls this). set_agent_status accepts only blocked/idle/sleeping "
        "-- it cannot transition out of awaiting_user. report_progress does not auto-wake "
        "from awaiting_user either. If the user responds verbally, guide them to open "
        "CloseoutModal and click the ApprovalCard option, or to POST to the decide "
        "endpoint directly. The MCP server is passive and will not clear the gate from "
        "conversation alone."
    ),
)
async def request_approval(
    job_id: Annotated[str, Field(description="Calling agent's job_id (UUID).")],
    project_id: Annotated[str, Field(description="Project UUID the approval belongs to.")],
    reason: Annotated[str, Field(description="Plain-English explanation shown to the user (<= 2000 chars).")],
    options: Annotated[
        list[dict],
        Field(description="List of {id, label} option dicts (1-10 items, unique ids)."),
    ],
    context: Annotated[
        dict | None,
        Field(description="Optional structured payload (deferred findings, etc). <= 16 KB serialized."),
    ] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Create a pending user approval. Atomic: insert row + flip status + broadcast."""
    kwargs: dict[str, Any] = {
        "job_id": job_id,
        "project_id": project_id,
        "reason": reason,
        "options": options,
        "context": context,
    }
    return await _call_tool(ctx, "request_approval", kwargs)


@mcp.tool(description="Check MCP server health status")
async def health_check(ctx: Context = None) -> dict[str, Any]:
    """Check MCP server health status."""
    accessor = _get_tool_accessor()
    return await accessor.health_check()


@mcp.tool(
    description=(
        "First-time setup: downloads slash commands/skills as a ZIP. "
        "Run once after connecting. Installs user-level commands only. "
        "After setup, run /gil_get_agents to install product-scoped agent templates. "
        "IMPORTANT: You MUST pass the platform parameter identifying which CLI tool you are. "
        "Use 'claude_code' for Claude Code, 'gemini_cli' for Gemini CLI, 'codex_cli' for Codex CLI."
    ),
)
async def giljo_setup(
    platform: Literal["claude_code", "gemini_cli", "codex_cli", "generic"] = "claude_code",
    ctx: Context = None,
) -> dict[str, Any]:
    """Install slash commands/skills for your CLI tool."""
    logger.info("giljo_setup called with platform=%s", platform)

    # HO 1028: pass authenticated user_id so the staging layer can stamp the
    # installed skills version through UserService (single write path).
    user_id = _resolve_user_id(ctx)
    result = await _call_tool(ctx, "bootstrap_setup", {"platform": platform, "user_id": user_id})

    # Emit setup:bootstrap_complete WebSocket event
    try:
        from api.app_state import state as app_state

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
) -> dict[str, Any]:
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
async def list_agent_templates(
    platform: str,
    ctx: Context = None,
) -> dict[str, Any]:
    """Export agent templates for target CLI platform."""
    kwargs = {"platform": platform}
    result = await _call_tool(ctx, "list_agent_templates", kwargs)

    # Handover 0855b: Emit setup:agents_downloaded when CLI fetches templates via MCP
    try:
        from api.app_state import state as app_state

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
    agent_display_name: Annotated[
        str,
        Field(
            description="Agent role to query, e.g. 'implementer', 'tester', 'analyzer'. Matches against job's agent_display_name."
        ),
    ],
    ctx: Context = None,
) -> dict[str, Any]:
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
    todo_items: Annotated[
        list[dict] | None,
        Field(
            description="FULL TODO list (replaces existing). Each item: {content: str, status: 'pending'|'in_progress'|'completed'}. Include ALL items — completed + in_progress + pending. Never a partial list."
        ),
    ] = None,
    todo_append: Annotated[
        list[dict] | None,
        Field(
            description="NEW items to append (does not replace). Same format as todo_items. Use this to add tasks discovered during work without overwriting existing list."
        ),
    ] = None,
    ctx: Context = None,
) -> dict[str, Any]:
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
        "Check receive_messages() and verify all TODOs are completed before calling. "
        "ORCHESTRATOR CLOSEOUT: pass acknowledge_closeout_todo=True when the closeout "
        "TODO IS this very call (e.g. 'Closeout: complete orchestrator job') — the gate "
        "will auto-complete any TODO whose content matches closeout/complete_job/close_project. "
        "Non-closeout incomplete TODOs still block. STUCK ON UNREAD MESSAGES: pass "
        "acknowledge_messages_on_complete=True to drain (mark acknowledged) all unread "
        "messages addressed to this agent in the project+tenant before evaluating. "
        "Mirror of acknowledge_closeout_todo for the messages gate. The TODOs gate is "
        "independent — neither flag bypasses the other."
    ),
)
async def complete_job(
    job_id: str,
    result: Annotated[
        dict,
        Field(
            description="Completion result dict. Expected keys: 'summary' (str, what was accomplished), 'files_changed' (list[str], optional), 'decisions_made' (list[str], optional)."
        ),
    ],
    acknowledge_closeout_todo: Annotated[
        bool,
        Field(
            description="When True, auto-complete any incomplete TODO whose content describes the closeout itself (matches closeout/complete_job/close_project). Use from orchestrator closeout where the closeout TODO IS this call. Default False."
        ),
    ] = False,
    acknowledge_messages_on_complete: Annotated[
        bool,
        Field(
            description="When True, drain (mark acknowledged) all unread messages addressed to this agent within the project+tenant before evaluating the gate. Mirror of acknowledge_closeout_todo for the messages gate. Use this escape hatch when stuck in a reactivation-on-stale-message loop and unable to close out. The TODOs gate is independent — this flag does NOT bypass incomplete TODOs. Default False."
        ),
    ] = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """Mark job as completed with results."""
    return await _call_tool(
        ctx,
        "complete_job",
        {
            "job_id": job_id,
            "result": result,
            "acknowledge_closeout_todo": acknowledge_closeout_todo,
            "acknowledge_messages_on_complete": acknowledge_messages_on_complete,
        },
    )


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
) -> dict[str, Any]:
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
) -> dict[str, Any]:
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
) -> dict[str, Any]:
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
        "when report_progress() is called. "
        "During staging, this tool is server-locked for the orchestrator "
        "(returns 403 STAGING_LOCK until project.staging_status == 'staging_complete'); "
        "use report_progress to log conversation state and ask the user inline instead. "
        "Spawned non-orchestrator agents bypass the lock."
    ),
)
async def set_agent_status(
    job_id: str,
    status: Annotated[
        str, Field(description="Target status: 'blocked', 'idle', or 'sleeping'. Other statuses are not valid here.")
    ],
    reason: Annotated[
        str, Field(description="Human-readable reason. REQUIRED for 'blocked' status. Displayed on dashboard.")
    ] = "",
    wake_in_minutes: Annotated[
        int | None,
        Field(
            description="Sleep interval hint for 'sleeping' status. Agent will auto-check-in after this many minutes."
        ),
    ] = None,
    ctx: Context = None,
) -> dict[str, Any]:
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
        "receiving thin prompt from spawn_job. Agent's first action. Returns targeted "
        "mission for this specific agent (not entire project vision). Part of thin-client "
        "architecture - mission stored in database, not embedded in prompt. Idempotent."
    ),
)
async def get_agent_mission(
    job_id: str,
    ctx: Context = None,
) -> dict[str, Any]:
    """Fetch agent-specific mission and context."""
    if job_id.strip().lower() in _PLACEHOLDER_JOB_IDS:
        return {
            "error": "no_job_context",
            "message": (
                "This agent was launched without orchestration context. "
                "To use GiljoAI orchestration, the orchestrator must call "
                "spawn_job() first, then pass the returned thin prompt "
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
async def spawn_job(
    agent_display_name: Annotated[
        str, Field(description="Agent role label for UI display, e.g. 'implementer', 'tester', 'analyzer'.")
    ],
    agent_name: Annotated[
        str,
        Field(description="Agent template name from agent_templates list, e.g. 'tdd-implementor', 'code-reviewer'."),
    ],
    mission: Annotated[
        str,
        Field(
            description="The specific work assignment for this agent. Be detailed — this becomes the agent's full mission."
        ),
    ],
    project_id: str,
    phase: Annotated[
        int | None,
        Field(
            description=(
                "Optional ordering metadata. Same phase = parallel siblings; "
                "higher phase = depends on lower phases completing. "
                "In multi_terminal execution mode the dashboard groups Play buttons by phase. "
                "In subagent modes (Claude/Codex/Gemini CLI) the orchestrator manages ordering "
                "via Task() / spawn_agent() / @-syntax invocation order; phase is informational. "
                "Must be an integer."
            )
        ),
    ] = None,
    predecessor_job_id: Annotated[
        str,
        Field(
            description=(
                "Optional job_id of a previous agent whose output this successor needs. The server "
                "reads the predecessor's completion record and renders an appropriate context "
                "preamble into the successor's mission (chain vs replacement is auto-detected from "
                "the predecessor's status). In subagent execution modes the server silently skips "
                "the preamble because your CLI already returned the predecessor result inline."
            )
        ),
    ] = "",
    ctx: Context = None,
) -> dict[str, Any]:
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
    return await _call_tool(ctx, "spawn_job", kwargs)


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
) -> dict[str, Any]:
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
) -> dict[str, Any]:
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
        "depth control. Pass one or more categories in a single call: "
        "categories=['product_core', 'tech_stack', 'architecture']. "
        "Categories: product_core (~100 tokens), vision_documents (0-24K), "
        "tech_stack (200-400), architecture (300-1.5K), testing (0-400), memory_360 "
        "(500-5K), git_history (500-5K), agent_templates (400-2.4K), project (~300), "
        "self_identity (agent template content), tasks (open task list), "
        "todos (TODO content for a job — pass job_id, used for force-recovery)."
    ),
)
async def fetch_context(
    product_id: str,
    project_id: str = "",
    agent_name: Annotated[
        str, Field(description="Agent template name (e.g. 'tdd-implementor') for self_identity category. Optional.")
    ] = "",
    job_id: Annotated[
        str,
        Field(
            description="Agent job UUID. REQUIRED for the 'todos' category (read-back of an agent's TODO list — sequence + content + status). Ignored by other categories."
        ),
    ] = "",
    categories: Annotated[
        list[str] | None,
        Field(
            description="List of categories to fetch: 'product_core', 'vision_documents', 'tech_stack', 'architecture', 'testing', 'memory_360', 'git_history', 'agent_templates', 'project', 'self_identity', 'tasks', 'todos'. Must be a list, e.g. ['tech_stack', 'architecture']. Multiple categories supported in one call. Required (do not pass null)."
        ),
    ] = None,
    depth_config: Annotated[
        dict | None,
        Field(
            description="Optional depth overrides per category, e.g. {'vision_documents': 'full', 'git_history': 'summary'}."
        ),
    ] = None,
    output_format: Annotated[str, Field(description="Output format: 'structured' (default) or 'flat'.")] = "structured",
    ctx: Context = None,
) -> dict[str, Any]:
    """Unified context fetcher by category with depth control."""
    if isinstance(categories, str):
        categories = [categories]
    kwargs: dict[str, Any] = {"product_id": product_id, "output_format": output_format}
    if project_id:
        kwargs["project_id"] = project_id
    if agent_name:
        kwargs["agent_name"] = agent_name
    if job_id:
        kwargs["job_id"] = job_id
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
    summary: Annotated[
        str,
        Field(description="Brief 2-3 sentence headline of project outcome. Max 500 chars (server-enforced)."),
    ],
    key_outcomes: Annotated[
        list[str],
        Field(description="List of key achievements. Max 5 items, each max 200 chars (server-enforced)."),
    ],
    decisions_made: Annotated[
        list[str],
        Field(description="List of key decisions with rationale. Max 5 items, each max 250 chars (server-enforced)."),
    ],
    git_commits: Annotated[
        list[dict] | None,
        Field(
            description="Git commits from project branch. Each: {sha: str, message: str, author: str}. Run 'git log --oneline' first."
        ),
    ] = None,
    tags: Annotated[
        list[str] | None,
        Field(
            description=(
                "REQUIRED-IN-SPIRIT: 1-5 tags from the 16-entry controlled "
                "vocabulary. Change-type axis: feature, bug-fix, refactor, perf, "
                "security, docs, test, chore. Domain axis: frontend, backend, "
                "database, api, infrastructure, ui-ux, integration. Operational: "
                "migration. Pick 1-3 from change-type AND 1-3 from domain. "
                "Invalid tags are rejected with a structured error carrying the "
                "offending tag and the full allowed enum. None or [] persists "
                "with empty tags (no auto-extraction)."
            )
        ),
    ] = None,
    ctx: Context = None,
) -> dict[str, Any]:
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
    if tags is not None:
        kwargs["tags"] = tags
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
    summary: Annotated[
        str,
        Field(
            description="Brief 2-3 sentence headline of what was accomplished or handed over. Max 500 chars (server-enforced)."
        ),
    ],
    key_outcomes: Annotated[
        list[str],
        Field(description="List of key outcomes/achievements. Max 5 items, each max 200 chars (server-enforced)."),
    ],
    decisions_made: Annotated[
        list[str],
        Field(description="List of key decisions with rationale. Max 5 items, each max 250 chars (server-enforced)."),
    ],
    entry_type: Annotated[
        str,
        Field(
            description=(
                "Entry type. Workers may write: "
                "baseline (foundation context); "
                "decision (a specific choice with rationale); "
                "architecture (structural notes); "
                "discovery (surprising finding worth remembering). "
                "Orchestrator-only (rejected with ORCHESTRATOR_ONLY_ENTRY_TYPE for workers): "
                "project_completion (project closeout); "
                "session_handover (orchestrator-to-orchestrator across sessions). "
                "Legacy: handover_closeout (preserved for back-compat). "
                "DEPRECATED: action_required entry_type is no longer accepted -- "
                "use mcp__giljo_mcp__create_task or create_project for deferred follow-ups (INF-5025)."
            )
        ),
    ] = "project_completion",
    author_job_id: Annotated[
        str, Field(description="Job ID of the authoring agent (usually the orchestrator's job_id).")
    ] = "",
    git_commits: Annotated[
        list[dict] | None,
        Field(
            description="Git commits from project branch. Each entry: {sha: str, message: str, author: str}. Optional: date (ISO 8601), files_changed (int), lines_added (int)."
        ),
    ] = None,
    tags: Annotated[
        list[str] | None,
        Field(
            description=(
                "Tags for categorization. Max 8 tags, each from the controlled 16-tag vocabulary "
                "(server-enforced): change-type [feature, bug-fix, refactor, perf, security, docs, test, chore], "
                "domain [frontend, backend, database, api, infrastructure, ui-ux, integration], "
                "operational [migration]. DEPRECATED: do not use 'action_required:description' tag prefixes for new work — create a follow-up task via create_task instead."
            ),
        ),
    ] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Write 360 memory entry for project completion/handover.

    DEPRECATED: do not use `action_required:` tag prefixes or write `action_required` 360 entries for new work. Create a follow-up task via `mcp__giljo_mcp__create_task` (or a project via `mcp__giljo_mcp__create_project` for multi-step work) and cite the returned ID in `decisions_made` at closeout.
    """
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
    if tags is not None:
        kwargs["tags"] = tags
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
    force: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """Submit product context tuning proposals."""
    kwargs: dict[str, Any] = {"product_id": product_id, "proposals": proposals}
    if overall_summary:
        kwargs["overall_summary"] = overall_summary
    if force:
        kwargs["force"] = True
    return await _call_tool(ctx, "submit_tuning_review", kwargs)


# ---------------------------------------------------------------------------
# Vision Analysis Tools (2)
# ---------------------------------------------------------------------------


@mcp.tool(
    name="get_vision_doc",
    description=(
        "Retrieve a product's vision document with extraction instructions. "
        "Call WITHOUT chunk to get metadata (total_chunks, extraction_instructions). "
        "Then call WITH chunk=1, chunk=2, etc. to retrieve each chunk's content "
        "one at a time. Read ALL chunks before calling update_product_fields."
    ),
)
async def get_vision_doc(
    product_id: str,
    chunk: int | None = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Retrieve product's vision document."""
    kwargs: dict[str, Any] = {"product_id": product_id}
    if chunk is not None:
        kwargs["chunk"] = chunk
    return await _call_tool(ctx, "get_vision_doc", kwargs)


@mcp.tool(
    name="update_product_fields",
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
    coding_conventions: str = "",
    brand_guidelines: str = "",
    quality_standards: str = "",
    testing_strategy: str = "",
    testing_frameworks: str = "",
    test_coverage_target: int | None = None,
    force: bool = False,
    summary_33: str = "",
    summary_66: str = "",
    ctx: Context = None,
) -> dict[str, Any]:
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
        "coding_conventions": coding_conventions,
        "brand_guidelines": brand_guidelines,
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
    if force:
        kwargs["force"] = True
    return await _call_tool(ctx, "write_product_from_analysis", kwargs)


# ---------------------------------------------------------------------------
# Auth Middleware (ASGI) -- validates Bearer token, injects tenant_key
# ---------------------------------------------------------------------------


def _build_www_authenticate_header(scope: Scope) -> str:
    """Construct the RFC 6750 WWW-Authenticate value for /mcp 401s.

    Includes the RFC 9728 `resource_metadata` parameter pointing at the
    protected-resource document. Spec-compliant clients (Claude.ai, MCP CLI)
    use it to bootstrap themselves after a 401 instead of failing closed.
    """
    canonical = get_canonical_mcp_resource_uri_from_scope(scope)
    base, _, _ = canonical.rpartition("/mcp")
    metadata_url = f"{base}/.well-known/oauth-protected-resource"
    return f'Bearer realm="MCP", resource_metadata="{metadata_url}"'


def _unauthenticated_response(scope: Scope, error: str, status_code: int = 401) -> JSONResponse:
    """Build a 401/403 JSONResponse with the spec-required WWW-Authenticate header."""
    return JSONResponse(
        {"error": error},
        status_code=status_code,
        headers={"WWW-Authenticate": _build_www_authenticate_header(scope)},
    )


# ---------------------------------------------------------------------------
# API-0021j: MCP-Protocol-Version + Mcp-Session-Id transport-layer helpers
#
# Streamable HTTP spec requires:
#   - Non-initialize requests with an unsupported MCP-Protocol-Version → 400
#     (NOT 401 — clients use this to negotiate; auth is downstream of it).
#   - Initialize responses carry an Mcp-Session-Id; subsequent requests echo
#     it and the server MUST return 404 on unknown / expired / cross-tenant
#     ids (matches SDK behavior at streamable_http.py:498).
#
# Single source of truth: import MCP_SPEC_VERSIONS_SUPPORTED from
# api.endpoints.oauth — locked by tests/api/test_spec_conformance.py. The
# frozenset below is a derived O(1) membership view, not a parallel constant.
# ---------------------------------------------------------------------------

from api.endpoints.oauth import MCP_SPEC_VERSIONS_SUPPORTED  # noqa: E402


_SUPPORTED_VERSIONS: frozenset[str] = frozenset(MCP_SPEC_VERSIONS_SUPPORTED)
_DEFAULT_SPEC_VERSION = "2025-03-26"
_INITIALIZE_METHOD = "initialize"


async def _read_full_body(receive: Receive) -> bytes:
    """Drain the ASGI request body in full.

    Returns the concatenated bytes. The middleware buffers the body once so the
    JSON-RPC method can be peeked before the inner ASGI app is invoked; the
    buffered bytes are then replayed via :func:`_replay_receive`.
    """
    chunks: list[bytes] = []
    while True:
        message = await receive()
        if message["type"] == "http.disconnect":
            break
        if message["type"] != "http.request":
            break
        chunks.append(message.get("body", b""))
        if not message.get("more_body", False):
            break
    return b"".join(chunks)


def _replay_receive(body: bytes) -> Receive:
    """Build a fresh ``receive`` that yields ``body`` once, then disconnect."""
    sent = {"done": False}

    async def _receive() -> dict:
        if sent["done"]:
            return {"type": "http.disconnect"}
        sent["done"] = True
        return {"type": "http.request", "body": body, "more_body": False}

    return _receive


def _peek_jsonrpc_method(body: bytes) -> str | None:
    """Return the JSON-RPC ``method`` if the body decodes cleanly, else ``None``.

    Malformed bodies are tolerated — the inner SDK will respond with the
    canonical JSON-RPC error, and the middleware short-circuits no further
    on its own. Header-version + session-id flows treat missing-method as
    'not initialize' (the safe default).
    """
    if not body:
        return None
    try:
        payload = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        return None
    if isinstance(payload, dict):
        method = payload.get("method")
        return method if isinstance(method, str) else None
    return None


def _unsupported_version_response(version: str) -> JSONResponse:
    """Build the 400 response for an unsupported MCP-Protocol-Version header."""
    return JSONResponse(
        {
            "error": "Unsupported MCP-Protocol-Version",
            "requested": version,
            "supported": list(MCP_SPEC_VERSIONS_SUPPORTED),
        },
        status_code=400,
    )


def _not_found_response(detail: str) -> JSONResponse:
    """Build the 404 response for an invalid / expired / cross-tenant session id."""
    return JSONResponse({"error": detail}, status_code=404)


def _validate_protocol_version(request: StarletteRequest, method: str | None) -> JSONResponse | None:
    """Phase 1 validator. Returns a 400 response if the header is unsupported, else ``None``.

    Initialize requests are exempt because negotiation lives in JSON-RPC
    params (spec 2025-06-18 §Transport). Missing header on non-initialize
    SHOULD-defaults to 2025-03-26 — accepted with a debug log.
    """
    if method == _INITIALIZE_METHOD:
        return None
    version = request.headers.get("mcp-protocol-version")
    if version is None:
        logger.debug(
            "No MCP-Protocol-Version header on %s; defaulting to %s per spec",
            method or "<no-method>",
            _DEFAULT_SPEC_VERSION,
        )
        return None
    if version not in _SUPPORTED_VERSIONS:
        logger.info("Rejecting unsupported MCP-Protocol-Version=%r on method=%r", version, method)
        return _unsupported_version_response(version)
    return None


def _wrap_send_with_session_id(send: Send, session_id: str) -> Send:
    """Return a Send that injects ``Mcp-Session-Id`` into the first response start frame."""

    async def _send(message: dict) -> None:
        if message["type"] == "http.response.start":
            headers = list(message.get("headers", []))
            headers.append((b"mcp-session-id", session_id.encode("ascii")))
            message = {**message, "headers": headers}
        await send(message)

    return _send


# ---------------------------------------------------------------------------
# API-0021b: scope-aware tools/list filter + tools/call dispatch gate
#
# Re-registers the SDK's ListToolsRequest and CallToolRequest handlers so that
# JWT-authenticated callers only see (and can only invoke) tools whose registered
# scope is in the token's scope set. API-key callers bypass entirely.
#
# The lowlevel server captures handler references at FastMCP.__init__ time,
# so re-registration must call the SDK's own decorator (which rebuilds the
# request_handlers entry) rather than monkey-patching `mcp.list_tools`.
# ---------------------------------------------------------------------------


def _request_from_context() -> StarletteRequest | None:
    """Best-effort resolve the StarletteRequest for the active MCP request.

    Returns None when called outside an HTTP request (e.g. the in-memory test
    transport). Tests that exercise the scope filter monkeypatch
    `_scopes_from_request` directly.
    """
    try:
        ctx = mcp.get_context()
        return ctx.request_context.request
    except (LookupError, ValueError, AttributeError):
        return None


_orig_list_tools = mcp.list_tools
_orig_call_tool = mcp.call_tool


async def _scope_filtered_list_tools():
    """Replacement for FastMCP.list_tools that filters by token scope."""
    tools = await _orig_list_tools()
    scopes = _scopes_from_request(_request_from_context())
    if scopes is None:
        return tools
    return [t for t in tools if TOOL_SCOPES.get(t.name) in scopes]


async def _scope_gated_call_tool(name, arguments):
    """Replacement for FastMCP.call_tool that rejects out-of-scope dispatches.

    Defense-in-depth: the tools/list filter hides agent-only tools from the
    advertised list, but a JWT caller can still craft tools/call against a
    hidden name. This gate ensures such calls fail with a transport-layer
    error rather than silently executing.
    """
    scopes = _scopes_from_request(_request_from_context())
    if scopes is not None:
        tool_scope = TOOL_SCOPES.get(name)
        if tool_scope not in scopes:
            from mcp.server.fastmcp.exceptions import ToolError

            raise ToolError(f"Tool '{name}' not authorized for this token's scope")
    return await _orig_call_tool(name, arguments)


# Re-register against the lowlevel MCP server. _setup_handlers() ran during
# FastMCP.__init__ and bound `self.list_tools` / `self.call_tool` into
# request_handlers; calling the SDK decorators again replaces those entries.
mcp._mcp_server.list_tools()(_scope_filtered_list_tools)
mcp._mcp_server.call_tool(validate_input=False)(_scope_gated_call_tool)


class MCPAuthMiddleware:
    """
    ASGI middleware that validates Bearer token (JWT or API key) and injects
    tenant_key into the ASGI scope state before the MCP SDK processes the request.

    Auth flow:
    1. Extract Authorization: Bearer <token> or X-API-Key header
    2. Try JWT validation first (fast, stateless). For Bearer JWTs, the
       canonical MCP URI is supplied as expected_audience — tokens carrying
       a foreign aud claim are rejected outright (RFC 8707 / API-0021a).
       Aud-less JWTs still authenticate during the transition window with a
       deprecation warning.
    3. Fall back to API key via MCPSessionManager (stateful, PostgreSQL)
    4. Attach tenant_key + user_id to scope["state"]

    All 401 responses include `WWW-Authenticate: Bearer realm="MCP",
    resource_metadata="<URL>"` so clients can self-discover the resource
    metadata document (RFC 6750 + RFC 9728).
    """

    def __init__(self, app: ASGIApp):
        self.app = app
        self._notified_keys: set[str] = set()  # Track keys we've already emitted setup:tool_connected for

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # API-0021j: buffer the JSON-RPC body once so the validator + session
        # lifecycle can inspect `method` before auth runs. The buffered bytes
        # are replayed downstream via _replay_receive so the inner SDK sees an
        # unchanged stream.
        buffered_body = await _read_full_body(receive)
        receive = _replay_receive(buffered_body)
        method = _peek_jsonrpc_method(buffered_body)

        request = StarletteRequest(scope, receive)

        # API-0021j Phase 1: MCP-Protocol-Version header validation. MUST
        # precede auth so unsupported clients receive 400, not 401.
        version_error = _validate_protocol_version(request, method)
        if version_error is not None:
            await version_error(scope, receive, send)
            return

        api_key_value: str | None = request.headers.get("x-api-key")
        bearer_token: str | None = None

        if not api_key_value:
            auth_header = request.headers.get("authorization", "")
            if auth_header.lower().startswith("bearer "):
                bearer_token = auth_header[7:]

        if not api_key_value and not bearer_token:
            resp = _unauthenticated_response(scope, "Authentication required (Authorization: Bearer or X-API-Key)")
            await resp(scope, receive, send)
            return

        tenant_key: str | None = None
        user_id: str | None = None
        api_key_id: int | None = None
        auth_method: str | None = None
        token_scopes: list[str] | None = None
        # API-0021j: captured during API-key auth so initialize responses can
        # advertise Mcp-Session-Id without a second DB round-trip.
        mcp_session_id: str | None = None

        # Path 1: JWT token (with audience binding per API-0021a).
        if bearer_token and not api_key_value:
            expected_audience = get_canonical_mcp_resource_uri_from_scope(scope)
            try:
                payload = JWTManager.verify_token(bearer_token, expected_audience=expected_audience)
                tenant_key = payload["tenant_key"]
                user_id = payload["sub"]
                auth_method = "jwt"
                # API-0021b: parse scope claim. Default for legacy/cookie JWTs
                # without a scope claim is mcp:read+mcp:write — covers the
                # dashboard cookie path and pre-API-0021b OAuth-issued tokens.
                # mcp:agent is never granted by default and never grantable via
                # /authorize, so the default is safe to widen to read+write.
                raw_scope = payload.get("scope")
                if raw_scope is None:
                    token_scopes = ["mcp:read", "mcp:write"]
                else:
                    token_scopes = [s for s in str(raw_scope).split() if s]

                # API-0022: RFC 7009 revocation enforcement. A token whose
                # jti has been revoked in this tenant is treated as if it
                # never existed (401 + WWW-Authenticate). Tokens minted
                # before API-0022 lack jti — those rows can't be revoked
                # server-side and roll off when they expire.
                jti = payload.get("jti")
                if jti:
                    from api.app_state import state as _app_state

                    if _app_state.db_manager is not None:
                        from giljo_mcp.services import oauth_revocation_service as _revoke

                        async with _app_state.db_manager.get_session_async() as _rev_db:
                            if await _revoke.is_access_token_jti_revoked(_rev_db, tenant_key=tenant_key, jti=jti):
                                logger.warning(
                                    "Rejecting revoked JWT on /mcp: jti=%s tenant_key=%s",
                                    jti,
                                    tenant_key,
                                )
                                resp = _unauthenticated_response(scope, "Token revoked")
                                await resp(scope, receive, send)
                                return
            except JWTAudienceMismatchError as exc:
                # Token presents a valid signature but for a different resource
                # server, or carries no `aud` at all (API-0022: legacy aud-less
                # tokens no longer accepted). Reject outright — do NOT fall
                # back to API-key path.
                logger.warning("Rejecting JWT on /mcp (audience): %s", exc)
                resp = _unauthenticated_response(scope, "Invalid token audience")
                await resp(scope, receive, send)
                return
            except (ValueError, KeyError, RuntimeError, HTTPException):
                # Not a valid JWT -- treat as API key (backward compatibility).
                api_key_value = bearer_token
                auth_method = None
                token_scopes = None

        # Path 2: API key (via MCPSessionManager for DB lookup)
        if not tenant_key and api_key_value:
            try:
                from api.app_state import state
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
                        auth_method = "api_key"
                        mcp_session_id = session.session_id

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
            resp = _unauthenticated_response(scope, "Invalid credentials")
            await resp(scope, receive, send)
            return

        # Inject into ASGI scope state -- accessible in tool handlers via ctx
        if "state" not in scope:
            scope["state"] = {}
        scope["state"]["tenant_key"] = tenant_key
        scope["state"]["user_id"] = user_id
        # API-0021b: stamp auth discriminator + token scopes for the
        # tools/list filter and tools/call dispatch gate.
        scope["state"]["auth_method"] = auth_method
        if token_scopes is not None:
            scope["state"]["scopes"] = token_scopes

        # Handover 0855b: Emit setup:tool_connected on FIRST MCP auth per key
        # (replaces emission from deleted mcp_http.py after 0846 SDK migration)
        notify_key = f"{tenant_key}:{api_key_id or user_id}"
        if notify_key not in self._notified_keys:
            self._notified_keys.add(notify_key)
            try:
                from api.app_state import state as app_state

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

        # API-0021j Phase 2: Mcp-Session-Id lifecycle.
        send = await self._apply_session_lifecycle(
            scope=scope,
            send=send,
            request=request,
            method=method,
            tenant_key=tenant_key,
            user_id=user_id,
            auth_method=auth_method,
            mcp_session_id=mcp_session_id,
        )
        if send is None:
            # _apply_session_lifecycle already sent a 404; do not invoke inner app.
            return

        await self.app(scope, receive, send)

    async def _apply_session_lifecycle(
        self,
        *,
        scope: Scope,
        send: Send,
        request: StarletteRequest,
        method: str | None,
        tenant_key: str,
        user_id: str | None,
        auth_method: str | None,
        mcp_session_id: str | None,
    ) -> Send | None:
        """Resolve / validate the MCP session per API-0021j Phase 2.

        Returns a (possibly wrapped) ``send`` to use for the inner ASGI app, or
        ``None`` when the lifecycle has already emitted a 404 response (caller
        must short-circuit). Tenant scoping is enforced by
        :meth:`MCPSessionManager.get_session`.
        """
        if method == _INITIALIZE_METHOD:
            session_id = mcp_session_id or await self._ensure_jwt_initialize_session(
                tenant_key=tenant_key, user_id=user_id, auth_method=auth_method
            )
            if not session_id:
                return send
            return _wrap_send_with_session_id(send, session_id)

        header_session_id = request.headers.get("mcp-session-id")
        if not header_session_id:
            # Post-initialize sessions may be ephemeral; spec uses SHOULD here.
            logger.debug("Non-initialize request without Mcp-Session-Id; passthrough")
            return send

        from api.app_state import state
        from api.endpoints.mcp_session import MCPSessionManager

        if not state.db_manager:
            logger.error("db_manager not available for MCP session validation")
            await _not_found_response("Not Found: Invalid or expired session ID")(scope, request.receive, send)
            return None

        async with state.db_manager.get_session_async() as db:
            session_mgr = MCPSessionManager(db)
            session_row = await session_mgr.get_session(header_session_id, tenant_key=tenant_key)
            if session_row is None:
                logger.info(
                    "Rejecting unknown / expired / cross-tenant Mcp-Session-Id=%s on tenant=%s",
                    header_session_id,
                    tenant_key,
                )
                await _not_found_response("Not Found: Invalid or expired session ID")(scope, request.receive, send)
                return None
            session_row.extend_expiration(MCPSessionManager.DEFAULT_SESSION_LIFETIME_HOURS)
            await db.commit()
        return send

    async def _ensure_jwt_initialize_session(
        self,
        *,
        tenant_key: str,
        user_id: str | None,
        auth_method: str | None,
    ) -> str | None:
        """Create / reuse an MCPSession on initialize over a JWT-authenticated request.

        The API-key auth path already mints a session via ``get_or_create_session``;
        for JWT callers we mint one explicitly so the initialize response can
        advertise an Mcp-Session-Id. Returns the session_id, or ``None`` when
        the DB is unavailable.
        """
        if auth_method != "jwt" or not user_id:
            return None
        from api.app_state import state
        from api.endpoints.mcp_session import MCPSessionManager

        if not state.db_manager:
            return None
        async with state.db_manager.get_session_async() as db:
            session_mgr = MCPSessionManager(db)
            session = await session_mgr.get_or_create_session_from_jwt(user_id=user_id, tenant_key=tenant_key)
            return session.session_id


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
