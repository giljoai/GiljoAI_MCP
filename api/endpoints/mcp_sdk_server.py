"""
MCP SDK Server -- Streamable HTTP transport using official Anthropic MCP Python SDK.

Standard MCP protocol transport using official Anthropic MCP Python SDK (FastMCP).
transport. All tools delegate to the existing ToolAccessor methods. Auth and tenant
isolation are handled by ASGI middleware applied to the Starlette sub-app.

Handover: 0846a (transport replacement), 0846b (security integration)
"""

import inspect
import logging
from typing import Any

from fastapi import HTTPException
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.transport_security import TransportSecuritySettings
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

    return await tool_func(**kwargs)


# ---------------------------------------------------------------------------
# Project Management Tools (4)
# ---------------------------------------------------------------------------


@mcp.tool(
    description=(
        "Create a new project bound to the active product. "
        "Project is created as inactive. Use the web dashboard to activate and launch."
    ),
)
async def create_project(
    name: str,
    description: str,
    project_type: str = "",
    ctx: Context = None,
) -> dict:
    """Create a new project bound to the active product."""
    return await _call_tool(
        ctx,
        "create_project",
        {
            "name": name,
            "description": description,
            "project_type": project_type,
        },
    )


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
    description="Send a message to one or more agents. Use to_agents=['all'] for broadcast.",
)
async def send_message(
    to_agents: list[str],
    content: str,
    project_id: str,
    from_agent: str,
    message_type: str = "direct",
    priority: str = "normal",
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
        },
    )


@mcp.tool(
    description=("Receive pending messages for current agent with optional filtering (Handover 0360)"),
)
async def receive_messages(
    agent_id: str = "",
    limit: int = 10,
    exclude_self: bool = True,
    exclude_progress: bool = True,
    message_types: list[str] | None = None,
    ctx: Context = None,
) -> dict:
    """Receive pending messages with optional filtering."""
    kwargs: dict[str, Any] = {"limit": limit, "exclude_self": exclude_self, "exclude_progress": exclude_progress}
    if agent_id:
        kwargs["agent_id"] = agent_id
    if message_types is not None:
        kwargs["message_types"] = message_types
    return await _call_tool(ctx, "receive_messages", kwargs)


@mcp.tool(description="List messages with optional filters")
async def list_messages(
    agent_id: str = "",
    status: str = "",
    limit: int = 50,
    ctx: Context = None,
) -> dict:
    """List messages with optional filters."""
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
    description="Create a new task bound to the active product. Requires an active product to be set.",
)
async def create_task(
    title: str,
    description: str,
    priority: str = "medium",
    category: str = "",
    assigned_to: str = "",
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
    return await _call_tool(ctx, "get_agent_templates_for_export", {"platform": platform})


# ---------------------------------------------------------------------------
# Agent Coordination Tools (6)
# ---------------------------------------------------------------------------


@mcp.tool(description="Get pending jobs for agent type with multi-tenant isolation")
async def get_pending_jobs(
    agent_display_name: str,
    ctx: Context = None,
) -> dict:
    """Get pending jobs for agent type."""
    return await _call_tool(ctx, "get_pending_jobs", {"agent_display_name": agent_display_name})


@mcp.tool(
    description=(
        "Report incremental progress. Simplified: just send todo_items array. "
        "Backend calculates percent/steps automatically."
    ),
)
async def report_progress(
    job_id: str,
    todo_items: list[dict] | None = None,
    todo_append: list[dict] | None = None,
    ctx: Context = None,
) -> dict:
    """Report incremental progress."""
    kwargs: dict[str, Any] = {"job_id": job_id}
    if todo_items is not None:
        kwargs["todo_items"] = todo_items
    if todo_append is not None:
        kwargs["todo_append"] = todo_append
    return await _call_tool(ctx, "report_progress", kwargs)


@mcp.tool(description="Mark job as completed with results")
async def complete_job(
    job_id: str,
    result: dict,
    ctx: Context = None,
) -> dict:
    """Mark job as completed with results."""
    return await _call_tool(ctx, "complete_job", {"job_id": job_id, "result": result})


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


@mcp.tool(description="Report error and pause job for orchestrator review")
async def report_error(
    job_id: str,
    error: str,
    ctx: Context = None,
) -> dict:
    """Report error and pause job for orchestrator review."""
    return await _call_tool(ctx, "report_error", {"job_id": job_id, "error": error})


# ---------------------------------------------------------------------------
# Orchestration Tools (4)
# ---------------------------------------------------------------------------


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
    agent_display_name: str,
    agent_name: str,
    mission: str,
    project_id: str,
    phase: int | None = None,
    predecessor_job_id: str = "",
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
        "blocked/silent/decommissioned/pending agent counts and progress_percent (0-100). "
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
    agent_name: str = "",
    categories: list[str] | None = None,
    depth_config: dict | None = None,
    output_format: str = "structured",
    ctx: Context = None,
) -> dict:
    """Unified context fetcher by category with depth control."""
    kwargs: dict[str, Any] = {"product_id": product_id, "format": output_format}
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
        "'product_memory_updated' event for UI updates."
    ),
)
async def close_project_and_update_memory(
    project_id: str,
    summary: str,
    key_outcomes: list[str],
    decisions_made: list[str],
    force: bool = False,
    ctx: Context = None,
) -> dict:
    """Close project and update 360 Memory."""
    return await _call_tool(
        ctx,
        "close_project_and_update_memory",
        {
            "project_id": project_id,
            "summary": summary,
            "key_outcomes": key_outcomes,
            "decisions_made": decisions_made,
            "force": force,
        },
    )


@mcp.tool(
    description=(
        "Write a 360 memory entry for project completion or handover. Called by "
        "orchestrator on completion, or by agents on handover. Appends to "
        "Product.product_memory.sequential_history."
    ),
)
async def write_360_memory(
    project_id: str,
    summary: str,
    key_outcomes: list[str],
    decisions_made: list[str],
    entry_type: str = "project_completion",
    author_job_id: str = "",
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
        "Include summary_33 and summary_66 for AI-generated summaries."
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
