# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Shared base for the MCP @mcp.tool wrapper subpackage (BE-6042d).

Holds the single ``FastMCP`` instance every wrapper registers against, the tool
scope registry, and the helpers each domain wrapper module delegates through.
Both the wrapper modules (``mcp_tools/_*_tools.py``) and the transport layer
(``mcp_sdk_server.py``) import from here, which is what keeps the import graph
acyclic: this module imports neither the wrappers nor the transport.

Extracted verbatim from the pre-split ``mcp_sdk_server.py`` — behavior unchanged.
"""

import functools
import inspect
import logging
import re
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import FastMCPError
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import BaseModel
from starlette.requests import Request as StarletteRequest

# Harness + session-capability detection (BE-9035d) lives in the sibling ``_harness``
# module to keep this shared base under the file-size guardrail. Re-exported here so
# the wrapper modules (_job_tools / _setup_tools) keep importing them from ``_base``.
from api.endpoints.mcp_tools._harness import (  # noqa: F401
    _HARNESS_PARAM_DESCRIPTION,
    _detected_harness,
    _persisted_harness,
    _resolve_preset_name,
    get_session_capabilities,
)
from giljo_mcp import __version__ as _giljo_version
from giljo_mcp.exceptions import BaseGiljoError, ValidationError
from giljo_mcp.services.debounce import should_run
from giljo_mcp.services.memory_entry_write_validator import MemoryEntryWriteValidationError
from giljo_mcp.tenant_guard import TenantIsolationError
from giljo_mcp.tools.slash_command_templates import SKILLS_VERSION as _SKILLS_VERSION


# BE-3006d: agent-facing message for a sanitized (unexpected) tool failure. Carries
# no SQL, bind parameters, or traceback — the full detail goes to the server log only.
_SANITIZED_TOOL_ERROR = (
    "The server hit an unexpected internal error handling this request. "
    "Full details were logged server-side (no SQL, parameters, or stack trace are "
    "exposed to agents). Retry the call; if it persists, report the tool name."
)

# BE-3006d (CE-mode fix-forward): a cross-tenant access trips
# giljo_mcp.tenant_guard.TenantIsolationError (a plain RuntimeError). It is a
# KNOWN security-boundary rejection, not an unexpected error — but its str()
# leaks internal guard phrasing + the model name ("...ORM statement touching:
# Project..."). Surface a fixed, clean not-found message instead: production's
# tenant-scoped query simply sees no row, so "not found" is the truthful,
# non-leaking agent-facing contract. The word "not found" must remain present
# (an agent-facing contract the lifecycle tools' tests assert).
_NOT_FOUND_TOOL_ERROR = "The requested resource was not found, or you do not have access to it."

# BE-3006d: exception types that are ALREADY clean, agent-facing 422-style
# rejections and must surface verbatim (never sanitized). pydantic.ValidationError
# subclasses ValueError in v2, so the membership/length validators in
# jsonb_validators.py surface through here. MemoryEntryWriteValidationError is the
# structured memory-write cap rejection (its str() carries only field/size/guidance).
_CLEAN_VALIDATION_ERRORS: tuple[type[Exception], ...] = (
    ValueError,
    TypeError,
    MemoryEntryWriteValidationError,
)

# TSK-9134: defense-in-depth signature for a SQL/bind-param leak riding a plain
# ValueError/TypeError through the _CLEAN_VALIDATION_ERRORS verbatim path (real
# SQLAlchemyError & friends are already sanitized by the catch-all below). Narrow so
# a pydantic v2 message ("[type=.../input_value=...]") passes through UNCHANGED.
# Matches the SQLAlchemy dump ("[SQL: ...] [parameters: ...]") or a naive DML+params wrapper.
_SQL_LEAK_SIGNATURE = re.compile(
    r"\[SQL:"  # SQLAlchemy statement dump
    r"|\[SQL parameters:"  # driver variant
    r"|\[parameters:"  # SQLAlchemy bind-parameter dump
    r"|Background on this error at: https://sqlalche\.me"  # SQLAlchemy DBAPIError help suffix
    r"|(?:INSERT\s+INTO|UPDATE\s+\S+\s+SET|DELETE\s+FROM|SELECT\b.+?\bFROM)"  # DML statement...
    r"\b.*?\b(?:parameters|params|bind[_ ]?params?)\b\s*[=:]",  # ...paired with a params dump
    re.IGNORECASE | re.DOTALL,
)


# ---------------------------------------------------------------------------
# Agent-input length caps (BE-3006d)
#
# Bounded so a runaway agent cannot OOM Postgres TOAST or balloon a JSONB
# column, while staying well above any legitimate value. Surfaced on the
# @mcp.tool wrappers via ``Field(max_length=...)`` so an over-length param is
# rejected at the FastMCP arg-validation boundary (a clean 422-style ToolError)
# rather than reaching the service layer / a DB constraint (a 500). The wrapper
# descriptions cite these same constants so the advertised cap can never drift
# from the enforced one.
# ---------------------------------------------------------------------------
MCP_ID_MAX = 64  # a single UUID-ish identifier (project_id, from_agent, agent_id)
MCP_NAME_MAX = 200  # a name / title / assignee label
MCP_SHORT_TEXT_MAX = 2_000  # a reason / note / short summary line
MCP_MESSAGE_MAX = 20_000  # one inter-agent message body
MCP_DESCRIPTION_MAX = 20_000  # a task/project description blob
MCP_MISSION_MAX = 100_000  # an orchestrator mission / execution plan
MCP_LIST_ITEMS_MAX = 100  # recipients list, etc. (per-call item count)

# BE-9083c: per-tool inline-result size hint advertised on tools/list via the
# FastMCP ``meta`` kwarg (surfaces as ``_meta["anthropic/maxResultSizeChars"]``).
# Claude Code reads it to raise its inline-truncation ceiling for THESE heavy read
# tools (mission/staging/thread-history/projects), so a large-but-legitimate payload
# is delivered whole instead of being tail-truncated (the BE-9083a incident). It is
# a HINT: inert on every other harness (unknown _meta keys are ignored) and never a
# server-side cap. 500K is generous headroom over the largest real payload
# (full_protocol ~25KB + mission up to MCP_MISSION_MAX=100K).
MCP_MAX_RESULT_SIZE_CHARS = 500_000
MCP_HEAVY_TOOL_META: dict[str, int] = {"anthropic/maxResultSizeChars": MCP_MAX_RESULT_SIZE_CHARS}

# BE-6070 (F9): in-process debounce window for the per-call post-hooks
# (silent-clear probe + heartbeat). A looping agent fires many tool calls in a
# burst; only the first within this window pays the DB visit. The first call for
# a job_id always runs (check-and-set), and the silent-clear it would perform is
# already done by that first call -- so a silent->working transition is never
# delayed by the gate (an agent is only 'silent' after 10+ min of no activity).
_POSTHOOK_DEBOUNCE_SECONDS = 30


def _parse_iso_datetime_param(s: str) -> datetime | None:
    """Parse an ISO-8601 string from an MCP boundary param into a tz-aware datetime.

    CE-0034: date-only ISO strings (e.g. "2026-04-17") parse as naive datetimes.
    Coerce to UTC-aware so downstream comparisons against Postgres TIMESTAMPTZ
    don't raise ``TypeError: can't compare offset-naive and offset-aware datetimes``.
    Mirrors ``ProjectService._parse_iso_datetime``.

    Returns None for empty / falsy input. Raises ValidationError on unparseable input.
    """
    if not s:
        return None
    try:
        parsed = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, TypeError) as exc:
        raise ValidationError(f"Invalid ISO-8601 datetime '{s}'. Expected e.g. '2026-01-01T00:00:00Z'.") from exc
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


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

# INF-9115: FastMCP (mcp SDK 1.27.2) has no version= constructor kwarg — without
# this, Server.create_initialization_options() falls back to the installed `mcp`
# PyPI package's own version, so every MCP client's initialize handshake reported
# serverInfo.version=1.27.2 instead of the actual GiljoAI product version. Same
# post-construction access pattern _base.py already uses for mcp._mcp_server
# below (list_tools).
mcp._mcp_server.version = _giljo_version


# ---------------------------------------------------------------------------
# Tool scope registry (API-0021b): scope-aware MCP tool gating
#
# Single source of truth for both list_tools advertise filter and call_tool
# dispatch gate. Three scopes:
#   - mcp:read   : pure-read tools, no DB writes, no agent-state mutation
#   - mcp:write  : writes confined to user-owned product/project/task/memory
#   - mcp:agent  : orchestration primitives (spawn, complete_job, post_to_thread,
#                  status mutations, mission edits, …). Privilege surface.
#                  BE-6168: now grantable through OAuth /authorize (OAuth is the
#                  default auth → parity with an API key), guarded by the
#                  localhost-only redirect-URI allowlist + user consent, NOT by
#                  withholding the scope. Every state-mutating orchestration tool
#                  MUST map here — a mis-map to read/write fails OPEN (an OAuth
#                  read-only token could then mutate). See the BE-6168 guard test.
#                  SEC-9126: a tool with NO entry at all now fails CLOSED (hidden
#                  from tools/list AND rejected at dispatch), and the startup
#                  assert _assert_tool_scope_completeness() (mcp_sdk_server) aborts
#                  boot on any unmapped/orphaned tool. The mis-map-to-wrong-scope
#                  caution above still stands — SEC-9126 gates registry MEMBERSHIP,
#                  it does not police scope VALUES.
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
    # BE-6111c: read-only orchestrator self-healing diagnostic.
    "diagnose_project_state": SCOPE_READ,
    # INF-6049b: project-lifecycle driving tools. mcp:agent because they drive
    # orchestration (stage_project creates the orchestrator job; implement_project
    # exposes the execution prompt gated on agent + launch state).
    "stage_project": SCOPE_AGENT,
    "implement_project": SCOPE_AGENT,
    # BE-6115a: CLI door of the two-door implement gate. mcp:agent (privilege
    # surface) — its dispatch-gate scope + its deliberate exclusion from the
    # orchestrator auto-tool bundle (_canonical_tool_list) mean a spawned agent
    # cannot self-unlock; the MCP permission prompt is the human authorization.
    "launch_implementation": SCOPE_AGENT,
    # BE-6221a: headless chain-start (the dashboard "Run Sequential" equivalent).
    # mcp:agent — it mints the project-less conductor + creates a sequence run
    # (an orchestration mutation), so a read/write-only token must not reach it.
    "start_chain_run": SCOPE_AGENT,
    "update_job_mission": SCOPE_AGENT,
    # BE-6167: was SCOPE_READ, but the BE-5122 CTX self-close path inside
    # get_staging_instructions writes project.status=COMPLETED (a terminal
    # orchestration mutation). A read-only token must NOT be able to complete a
    # project — reclassify to mcp:agent alongside stage/implement_project. It is
    # an orchestration-driving tool, not a pure read.
    "get_staging_instructions": SCOPE_AGENT,
    # BE-6054b: Agent Message Hub (BBS) thread tools. Writes drive the board
    # (agent callers) = mcp:agent; pure reads = mcp:read (mirrors send/get above).
    "create_thread": SCOPE_AGENT,
    "join_thread": SCOPE_AGENT,
    "post_to_thread": SCOPE_AGENT,
    "pass_baton": SCOPE_AGENT,
    "get_my_turn": SCOPE_READ,
    "list_threads": SCOPE_READ,
    "get_thread_history": SCOPE_READ,
    "search_threads": SCOPE_READ,
    "create_task": SCOPE_WRITE,
    "update_task": SCOPE_WRITE,
    "list_tasks": SCOPE_READ,
    "update_roadmap_metadata": SCOPE_WRITE,
    "get_roadmap": SCOPE_READ,
    "request_approval": SCOPE_AGENT,
    "health_check": SCOPE_READ,
    "get_giljo_guide": SCOPE_READ,
    "giljo_setup": SCOPE_WRITE,
    "report_progress": SCOPE_AGENT,
    "complete_job": SCOPE_AGENT,
    "close_job": SCOPE_AGENT,
    # BE-9012b (BE-6225e): reactivate_job + dismiss_reactivation merged into the single
    # resolve_reactivation tool surface. The two names remain in TOOL_DISPATCH below as
    # internal dispatch targets (resolve_reactivation branches to them by action), but
    # they are no longer agent-facing tools — so they carry no TOOL_SCOPES entry.
    "resolve_reactivation": SCOPE_AGENT,
    "set_agent_status": SCOPE_AGENT,
    "get_job_mission": SCOPE_AGENT,
    "spawn_job": SCOPE_AGENT,
    "get_agent_result": SCOPE_AGENT,
    "get_workflow_status": SCOPE_AGENT,
    "get_context": SCOPE_READ,
    # BE-6225b: keyword search over 360 memory. Pure read (no writes, no agent-state
    # mutation) — same scope as get_context, the other 360-memory read.
    "search_memory": SCOPE_READ,
    "write_project_closeout": SCOPE_AGENT,
    "write_memory_entry": SCOPE_AGENT,
    # BE-6225c: renamed from propose_product_context_update (it APPLIES tuning
    # directly, no propose step). Scope unchanged (mcp:write).
    "apply_context_tuning": SCOPE_WRITE,
    "get_vision_doc": SCOPE_READ,
    "update_product_context": SCOPE_WRITE,
    # BE-9201: agent-side product bootstrap (establish the row + write the agent-
    # authored vision doc). Same scope as update_product_context — user-owned
    # product writes confined to the caller's tenant.
    "create_product": SCOPE_WRITE,
    "create_vision_document": SCOPE_WRITE,
}


def _scopes_from_request(request: StarletteRequest | None) -> set[str] | None:
    """Resolve the caller's effective scope set from the ASGI request state.

    Returns:
        - None if the caller authenticated via API key (full bypass). BE-6168:
          OAuth is no longer scope-limited away from mcp:agent — an OAuth token
          granted mcp:agent reaches the same surface; this bypass is just the
          API-key path that skips per-scope filtering entirely.
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
# Tool exposure PROFILES (WO-8003k): a curated tool-name subset evaluated
# ALONGSIDE the 3 auth scopes above, never replacing them. A profile is the
# capability-tier lens (a small/literal model sees a tight, disambiguated
# surface; a full CLI sees everything); the scope filter is the auth boundary.
# The effective visible/dispatchable set is the INTERSECTION: scope-filter ∩
# profile. This is purely additive on the API-0021b plumbing — no new filtering
# architecture (see the reuse map in project BE-8003k).
#
#   core     — the "one tool per intent" guided loop (exact 14 tools, incl.
#              health_check). What a small/literal model needs to run the
#              project→task→closeout loop without tripping over the confusable
#              update_*/messaging/completion clusters the small-model ergonomics
#              audit flagged.
#   standard — core + the Hub/BBS suite, messaging, roadmap, product-context /
#              vision reads+tuning, and the read-only project diagnostic (~30).
#              The JWT default for a session WITHOUT mcp:agent: a capable session
#              that is not the operator's own full-privilege orchestrator.
#   orchestrator — (BE-9017) the FULL surface MINUS launch_implementation. The
#              default for a JWT/OAuth session carrying mcp:agent (Claude Desktop /
#              claude.ai connector / OAuth CLI). Includes get_staging_instructions /
#              spawn_job / update_project_mission / stage_project (the human-ferried
#              flow needs them) but NOT the launch gate.
#   full     — the entire registered surface (sentinel ``None`` == NO profile
#              restriction, so a full session is BYTE-IDENTICAL to pre-profile
#              behavior and a profile can NEVER block a scope-allowed tool for it).
#
# SECURITY (WO-8003k DoD #3): stage_project / implement_project /
# launch_implementation are absent from BOTH core and standard, turning today's
# prompt-side-only advisory implement-gate exclusion into a server-enforced one —
# a core/standard tools/call on them is rejected exactly like an out-of-scope call.
# BE-9017: the orchestrator profile excludes launch_implementation ONLY — the sole
# writer of the human gate flag — so an mcp:agent session cannot self-unlock
# implementation, while implement_project (read-only, already gate-gated) stays
# reachable for the post-gate connector flow.
# ---------------------------------------------------------------------------

PROFILE_CORE = "core"
PROFILE_STANDARD = "standard"
PROFILE_FULL = "full"

# The exact 14-tool guided loop (EM decision, BE-8003k project description; BE-9017
# added ``health_check``). This set is roster-locked by the regression test —
# changing it is a deliberate act.
#
# BE-9017: ``health_check`` belongs in EVERY profile — every rendered prompt's step 1
# calls it as the fresh-connect probe. It was previously in the scope registry only,
# so a core/standard session's tools/list filtered it out and the guided loop broke
# at step 1 (field-confirmed on a Desktop OAuth session). Adding it to core flows it
# up to standard (superset), orchestrator (all-minus-launch — health_check is
# registered, so already included), and full (no restriction).
_CORE_PROFILE_TOOLS: frozenset[str] = frozenset(
    {
        "health_check",
        "get_giljo_guide",
        "get_context",
        "list_projects",
        "create_project",
        "create_task",
        "update_task",
        "list_tasks",
        "search_memory",
        "get_job_mission",
        "report_progress",
        "complete_job",
        "write_project_closeout",
        "post_to_thread",
    }
)

# standard = core + the mid-tier surface. Additions grouped as the WO enumerates
# them: the Hub/BBS thread suite, direct messaging, roadmap, product-context /
# vision, and the read-only project-state diagnostic. Deliberately EXCLUDES the
# orchestration/lifecycle privilege tools (spawn/stage/implement/chains/
# reactivation/mission edits) — those are full-only.
_STANDARD_PROFILE_TOOLS: frozenset[str] = _CORE_PROFILE_TOOLS | frozenset(
    {
        # Hub / BBS thread suite (post_to_thread is already in core)
        "create_thread",
        "join_thread",
        "pass_baton",
        "get_my_turn",
        "list_threads",
        "get_thread_history",
        "search_threads",
        # Roadmap
        "get_roadmap",
        "update_roadmap_metadata",
        # Product context / vision (BE-9201 added the two bootstrap writes: the
        # onboarding prompts run in the same non-agent-scope session tier that
        # already carries update_product_context)
        "get_vision_doc",
        "update_product_context",
        "apply_context_tuning",
        "create_product",
        "create_vision_document",
        # Read-only orchestrator self-healing diagnostic
        "diagnose_project_state",
    }
)

PROFILE_ORCHESTRATOR = "orchestrator"

# BE-9017: the orchestrator profile — the default for an OAuth/JWT session carrying
# the ``mcp:agent`` scope (Claude Desktop / claude.ai connector / OAuth CLI). It is
# the FULL surface MINUS the launch-gate tool(s), so a legitimate orchestrator sees
# everything it needs for the human-ferried flow — health_check, get_staging_
# instructions, spawn_job, update_project_mission, stage_project — but still cannot
# unilaterally LAUNCH implementation from the session.
#
# Excluded = ``launch_implementation`` ONLY: it is the SOLE MCP door that writes
# ``implementation_launched_at`` (the sacred human gate). ``implement_project`` is
# deliberately KEPT IN — it is read-only + already server-gated (returns
# gate_not_passed until the human presses Implement, never sets the flag, no bypass),
# so excluding it would add zero security while breaking the post-gate connector flow.
# ``stage_project`` is reversible prep and stays in (the generic_mcp orchestrator
# needs it). Computed from TOOL_SCOPES so new tools are auto-included (no roster to rot).
_LAUNCH_GATE_TOOLS: frozenset[str] = frozenset({"launch_implementation"})
_ORCHESTRATOR_PROFILE_TOOLS: frozenset[str] = frozenset(TOOL_SCOPES) - _LAUNCH_GATE_TOOLS

# Profile name -> the allowed tool-name set, or ``None`` for "no restriction"
# (the full surface). ``None`` is the sentinel the filter/gate short-circuit on,
# guaranteeing byte-identity for a full session.
TOOL_PROFILES: dict[str, frozenset[str] | None] = {
    PROFILE_CORE: _CORE_PROFILE_TOOLS,
    PROFILE_STANDARD: _STANDARD_PROFILE_TOOLS,
    PROFILE_ORCHESTRATOR: _ORCHESTRATOR_PROFILE_TOOLS,
    PROFILE_FULL: None,
}


def _normalize_scopes(scopes: object) -> set[str]:
    """Normalize a request's stamped scopes to a set of tokens.

    ``state['scopes']`` is stamped as a ``list[str]`` (mcp_sdk_server.py, from
    ``principal.scopes`` or a split raw-scope string), but tolerate a raw
    space-delimited string too so a future auth path can't silently break the
    membership check. Mirrors :func:`_scopes_from_request`'s handling.
    """
    if not scopes:
        return set()
    if isinstance(scopes, str):
        return {s for s in scopes.split() if s}
    return {str(s) for s in scopes}


def _profile_toolset_from_state(state: dict) -> frozenset[str] | None:
    """Resolve the effective tool-profile allow-set from a request's ASGI state.

    Returns the frozenset of tool names the profile permits, or ``None`` for the
    ``full`` profile (NO restriction). ``None`` is reachable ONLY for a declared
    ``full`` profile or an ``api_key`` caller; every other outcome is a bounded
    allow-set, so the profile axis can never *widen* an unrecognized caller to
    the full surface.

    Precedence (WO-8003k DoD #2 — declared always wins):
      1. explicit declared profile — ``state['tool_profile']`` (stamped from the
         (d) client_info capture); honored only when it names a known profile.
      2. auth-derived default (BE-9017 — keys on token SCOPE, not just method):
         * a JWT/OAuth session carrying ``mcp:agent`` ⇒ ``orchestrator`` (Claude
           Desktop / claude.ai connector / OAuth CLI — the human-ferried
           orchestrator surface, minus the launch gate);
         * a JWT/OAuth session WITHOUT ``mcp:agent`` ⇒ ``standard`` (unchanged);
         * an API key ⇒ ``full`` (today's behavior for every existing CLI user,
           unchanged — the only recognized signal that resolves to full).
      3. SEC-9126 fail-CLOSED floor: any unknown/absent ``auth_method`` ⇒ the
         empty allow-set (``frozenset()``) — advertise nothing, dispatch nothing.
         ``api_key`` and ``jwt`` are the only signals the middleware ever stamps,
         so this branch is a dead path on every live HTTP request today; it was
         formerly the fail-OPEN ``full`` default, and is converted here into an
         enforced invariant so a future auth path can never silently inherit the
         full surface.

    ADR-009: the default keys on the token's SCOPE (+ tenant_key elsewhere), never
    on per-user identity.
    """
    declared = state.get("tool_profile")
    if isinstance(declared, str) and declared in TOOL_PROFILES:
        return TOOL_PROFILES[declared]
    if state.get("auth_method") == "jwt":
        # BE-9017: an OAuth/JWT orchestrator token carries mcp:agent by default
        # (DEFAULT_OAUTH_SCOPE). Keying the default on the SCOPE — not the auth
        # method alone — is what stops the blanket jwt→standard downgrade from
        # tool-blocking every legitimate connector orchestrator session.
        if "mcp:agent" in _normalize_scopes(state.get("scopes")):
            return TOOL_PROFILES[PROFILE_ORCHESTRATOR]
        return TOOL_PROFILES[PROFILE_STANDARD]
    # SEC-9126: api_key is the ONLY recognized signal that resolves to full (no
    # restriction) — today's operator/CLI behavior, byte-identical.
    if state.get("auth_method") == "api_key":
        return TOOL_PROFILES[PROFILE_FULL]
    # SEC-9126: fail-closed floor for any unknown/absent auth signal.
    return frozenset()


def _profile_toolset_from_request(request: StarletteRequest | None) -> frozenset[str] | None:
    """Resolve the tool-profile allow-set for an MCP request (``None`` == full).

    Mirrors :func:`_scopes_from_request`: with no HTTP request (the in-memory test
    transport) there is no session/auth state, so ``None`` (full — no profile
    restriction) is returned and behavior is byte-identical to pre-profile. Tests
    that exercise a specific profile monkeypatch this function directly.
    """
    if request is None:
        return None
    state = request.scope.get("state", {}) if hasattr(request, "scope") else {}
    return _profile_toolset_from_state(state)


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


# ---------------------------------------------------------------------------
# Bound-method dispatch registry (BE-3010b)
#
# Maps an MCP tool's dispatch name to a resolver that, given the live
# ToolAccessor, returns the TERMINAL bound service method the @mcp.tool wrapper
# should call. This removes the ToolAccessor mixin's hand-copied signature from
# the parameter path for these "pure" tools: a parameter added to such a tool now
# touches exactly two non-test files (the @mcp.tool wrapper that advertises it +
# the service method that consumes it) — the registry entry is param-agnostic.
#
# Only PURE pass-throughs (forward args straight to one service method, possibly
# with bound construction deps supplied via functools.partial) live here. The ~14
# ADAPTER tools (reshape results, build envelopes, inject deps into standalone
# tool-functions, map params) are deliberately ABSENT: _call_tool falls back to
# ``getattr(accessor, method_name)`` for them, preserving their mixin logic
# verbatim. The ToolAccessor mixins remain as a thin shim for the ~50 test
# importers (deletion deferred per the WO).
#
# The dep-injecting project/task entries use functools.partial to supply the
# bound ``websocket_manager`` / ``db_manager`` the ``*_for_mcp`` methods accept —
# inspect.signature() on the partial still reports ``tenant_key`` so the
# tenant-injection below is unaffected.
# ---------------------------------------------------------------------------

ToolResolver = Callable[[Any], Callable[..., Awaitable[Any]]]

TOOL_DISPATCH: dict[str, ToolResolver] = {
    # Project tools (inject the bound websocket_manager the _for_mcp methods take)
    "create_project": lambda acc: functools.partial(
        acc._project_service.create_project_for_mcp, websocket_manager=acc._websocket_manager
    ),
    "list_projects": lambda acc: functools.partial(
        acc._project_service.list_projects_for_mcp, websocket_manager=acc._websocket_manager
    ),
    "update_project_metadata": lambda acc: functools.partial(
        acc._project_service.update_project_metadata_for_mcp, websocket_manager=acc._websocket_manager
    ),
    # Task tools
    "create_task": lambda acc: functools.partial(
        acc._task_service.create_task_for_mcp,
        db_manager=acc.db_manager,
        websocket_manager=acc._websocket_manager,
    ),
    "update_task": lambda acc: acc._task_service.update_task_for_mcp,
    "list_tasks": lambda acc: acc._task_service.list_tasks_for_mcp,
    # Roadmap tools
    "update_roadmap_metadata": lambda acc: acc._roadmap_service.upsert_metadata,
    "get_roadmap": lambda acc: acc._roadmap_service.get_roadmap,
    # Comm-thread (Agent Message Hub) tools
    "create_thread": lambda acc: acc._comm_thread_service.create_thread,
    "post_to_thread": lambda acc: acc._comm_thread_service.post_to_thread,
    "get_my_turn": lambda acc: acc._comm_thread_service.get_my_turn,
    "pass_baton": lambda acc: acc._comm_thread_service.pass_baton,
    "list_threads": lambda acc: acc._comm_thread_service.list_threads,
    "get_thread_history": lambda acc: acc._comm_thread_service.get_thread_history,
    "search_threads": lambda acc: acc._comm_thread_service.search_threads,
    # Mission / job tools
    "get_staging_instructions": lambda acc: acc._mission_service.get_staging_instructions,
    "get_job_mission": lambda acc: acc._mission_service.get_agent_mission,
    "update_job_mission": lambda acc: acc._mission_service.update_agent_mission,
    "get_workflow_status": lambda acc: acc._workflow_status_service.get_workflow_status,
    "report_progress": lambda acc: acc._progress_service.report_progress,
    "complete_job": lambda acc: acc._job_completion_service.complete_job,
    "close_job": lambda acc: acc._agent_state_service.close_job,
    "reactivate_job": lambda acc: acc._agent_state_service.reactivate_job,
    "dismiss_reactivation": lambda acc: acc._agent_state_service.dismiss_reactivation,
    "spawn_job": lambda acc: acc._orchestration_service.spawn_job,
}


def _resolve_tool_func(accessor: Any, method_name: str) -> Callable[..., Awaitable[Any]]:
    """Resolve the callable for a dispatched tool.

    Pure tools resolve to their terminal bound service method via TOOL_DISPATCH;
    every other (ADAPTER) tool falls back to the ToolAccessor mixin method, exactly
    as before BE-3010b.
    """
    resolver = TOOL_DISPATCH.get(method_name)
    if resolver is not None:
        return resolver(accessor)
    return getattr(accessor, method_name)


async def _call_tool(ctx: Context, method_name: str, kwargs: dict[str, Any]) -> Any:
    """
    Central dispatch: resolve tenant, inject tenant_key, call the tool's bound
    service method (BE-3010b: pure tools dispatch straight to the terminal service
    via TOOL_DISPATCH; adapter tools fall back to the ToolAccessor mixin).

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
    tool_func = _resolve_tool_func(accessor, method_name)

    # Signature-based tenant_key injection
    sig = inspect.signature(tool_func)
    if "tenant_key" in sig.parameters:
        kwargs["tenant_key"] = tenant_key
    else:
        kwargs.pop("tenant_key", None)

    # BE-3006d: sanitizing catch-all at the single dispatch chokepoint.
    #
    # FastMCP's Tool.run wraps ANY exception escaping the wrapper into
    # ``ToolError(f"Error executing tool {name}: {e}")`` and the lowlevel server
    # serialises ``str(e)`` straight onto the wire (isError=True). An unexpected
    # DB error therefore leaks ``[SQL: ...] [parameters: ...]`` to the calling
    # agent. We classify here:
    #   - Curated client errors (BaseGiljoError < 500) carry actionable,
    #     agent-authored context (valid_types, blockers, ...) -> surface verbatim.
    #   - Validation/tool rejections (pydantic.ValidationError is a ValueError in
    #     v2; FastMCPError; the structured memory-write rejection) are already
    #     clean 422-style and never contain SQL -> surface verbatim.
    #   - Server-side BaseGiljoError (>= 500) may embed a raw driver string in
    #     ``.context`` (e.g. OrchestrationError(context={'error': str(db_err)})),
    #     and every other unexpected exception (SQLAlchemyError & friends) carries
    #     SQL text + bind params in ``str()`` -> log full detail server-side and
    #     raise a generic, sanitized ToolError that exposes none of it.
    try:
        result = await tool_func(**kwargs)
    except BaseGiljoError as exc:
        if exc.default_status_code < 500:
            raise
        logger.exception("MCP tool dispatch '%s' failed with a server-side error", method_name)
        raise FastMCPError(_SANITIZED_TOOL_ERROR) from exc
    except FastMCPError:
        raise
    except TenantIsolationError as exc:
        # Cross-tenant access: a known security-boundary rejection. Log the full
        # guard detail server-side, but never surface its str() (it embeds the
        # model name + internal guard phrasing) and never sanitize it to the
        # generic 500 — re-raise the clean, fixed not-found contract instead.
        logger.warning("MCP tool dispatch '%s' blocked by tenant isolation guard", method_name)
        raise FastMCPError(_NOT_FOUND_TOOL_ERROR) from exc
    except _CLEAN_VALIDATION_ERRORS as exc:
        # pydantic ValidationError + clean 422-style rejections surface VERBATIM.
        # TSK-9134: unless the message carries a SQL/bind-param leak signature ->
        # log full detail server-side, sanitize before the wire.
        if _SQL_LEAK_SIGNATURE.search(str(exc)):
            logger.exception(
                "MCP tool dispatch '%s' raised a ValueError/TypeError carrying a "
                "SQL/bind-parameter leak signature; sanitizing before it reaches the agent",
                method_name,
            )
            raise FastMCPError(_SANITIZED_TOOL_ERROR) from exc
        raise
    except Exception as exc:
        logger.exception("MCP tool dispatch '%s' raised an unexpected error", method_name)
        raise FastMCPError(_SANITIZED_TOOL_ERROR) from exc

    # ------------------------------------------------------------------
    # BE-6081: the TWO-TIER MCP-boundary error contract — the single
    # reconciled rule for post-0480 ("all Python layers raise on error,
    # never return {success: False}") vs the BE-5028 structured-response
    # contract. They are NOT in tension; they govern different cases:
    #
    #   Tier 1 — ERRORS RAISE (post-0480). Service-layer failures and any
    #   unexpected tool error propagate as exceptions and are classified by
    #   the try/except above into a FastMCPError -> the SDK serialises them as
    #   isError on the wire. No tool RETURNS {success: False} for an error.
    #
    #   Tier 2 — DELIBERATE domain REJECTIONS RETURN (BE-5028). A few tool
    #   implementations return a structured ``{"success": False, "error":
    #   <CODE>, ...}`` dict for an EXPECTED, agent-actionable declined request
    #   that carries fields the agent needs to self-correct — a *response*,
    #   not an error. No exception is raised, so it flows through the success
    #   path below UNCHANGED and reaches the agent as normal tool content
    #   (NOT isError). Known sites: write_memory_entry (GIT_COMMITS_REQUIRED,
    #   CLOSEOUT_BLOCKED, ORCHESTRATOR_ONLY_ENTRY_TYPE), get_context
    #   (agent-execution not-found), and request_approval
    #   (ORCHESTRATOR_ONLY_APPROVAL — BE-9054 worker rejection).
    #
    # The post-0480 raise-rule governs Tier-1 internal errors ONLY; it does
    # not forbid these intentional Tier-2 rejection responses. Regression:
    # tests/integration/test_be6081_mcp_boundary_contract.py.
    # ------------------------------------------------------------------

    # BE-6070 (F9): post-hooks on any successful MCP interaction -- silent-clear
    # probe + server-side heartbeat. Both pay a DB round-trip every call today.
    # Gate them behind ONE in-process monotonic debounce per job_id (skip BOTH
    # with zero DB touch in the rapid-call common case), and when they DO run,
    # share ONE session for both hooks instead of opening two.
    job_id = kwargs.get("job_id")
    if job_id and should_run("mcp_posthooks", job_id, _POSTHOOK_DEBOUNCE_SECONDS):
        try:
            from api.app_state import state as app_state
            from giljo_mcp.services.heartbeat import touch_heartbeat
            from giljo_mcp.services.silence_detector import auto_clear_silent

            ws_manager = getattr(app_state, "websocket_manager", None)
            async with app_state.db_manager.get_session_async() as db:
                # Auto-clear silent status (mutates only the ~0.1% silent case).
                try:
                    await auto_clear_silent(db, job_id, ws_manager, tenant_key=tenant_key)
                except (OSError, RuntimeError, ValueError, TypeError, AttributeError, KeyError):
                    logger.warning("auto_clear_silent failed for job_id=%s (non-blocking)", job_id)

                # Server-side heartbeat: last_activity_at (its own WHERE-debounce).
                try:
                    await touch_heartbeat(db, job_id, tenant_key=tenant_key)
                except (OSError, RuntimeError, ValueError, TypeError, AttributeError, KeyError):
                    logger.debug("heartbeat update failed for job_id=%s (non-blocking)", job_id)
        except (OSError, RuntimeError, ValueError, TypeError, AttributeError, KeyError):
            logger.debug("post-hooks failed for job_id=%s (non-blocking)", job_id)

    # Wire-contract normalisation: every @mcp.tool wrapper in this module is
    # annotated `-> dict[str, Any]`, but service-layer methods return typed
    # Pydantic response models (MissionResponse, ProgressResult, SpawnResult,
    # SendMessageResult, etc.). FastMCP validates the return against the
    # annotation and rejects Pydantic instances with a DictModel error, which
    # surfaces to MCP clients while server-side state has already been
    # persisted. Normalise here so every tool produces a JSON-safe dict
    # regardless of which service layer it delegates to.
    if isinstance(result, BaseModel):
        result = result.model_dump(mode="json")

    # IMP-6038: echo the server's bundled SKILLS_VERSION on every dict tool
    # response. The installed skills read this from `_meta` and, once per
    # session, advise the user to re-run /giljo_setup if their bundle is older.
    # Single shared response path -- no per-tool hand-editing.
    if isinstance(result, dict):
        meta = result.get("_meta")
        if not isinstance(meta, dict):
            meta = {}
        meta["skills_version"] = _SKILLS_VERSION
        result["_meta"] = meta
    return result
