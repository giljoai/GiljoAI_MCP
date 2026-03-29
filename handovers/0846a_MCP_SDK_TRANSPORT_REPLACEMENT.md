# Handover 0846a: FastMCP SDK Transport Replacement

**Date:** 2026-03-29
**From Agent:** Codex session (orchestrator)
**To Agent:** Next Session
**Priority:** High
**Estimated Complexity:** 1.5-2 hours
**Status:** Not Started
**Edition Scope:** CE

---

## Pre-Work Reading (MANDATORY)

1. `handovers/HANDOVER_INSTRUCTIONS.md` — golden rules, quality gates, code discipline
2. `handovers/Reference_docs/QUICK_LAUNCH.txt` — TDD discipline, test patterns
3. `handovers/0846_MCP_SDK_STANDARDIZATION.md` — series coordinator, architecture decision
4. `CLAUDE.md` — project conventions

---

## Task Summary

Create a new FastMCP-based MCP server alongside the existing custom endpoint. Register all 30 tools. Mount in `app.py`. Verify transport discovery works. Do NOT remove the old endpoint yet — that's 0846b.

---

## Context

The current `api/endpoints/mcp_http.py` implements a custom JSON-RPC 2.0 POST endpoint (~1,376 lines). It works for tool execution but doesn't comply with MCP Streamable HTTP transport, so clients like Codex CLI can't discover tools. The `mcp` Python SDK (`mcp>=1.23.0`) is already in `requirements.txt`.

### Key files to read before coding

- `api/endpoints/mcp_http.py` — current implementation (lines 1-50 for overview, 1015-1047 for tools/list, 1083-1125 for tool_map)
- `api/app.py` — router registration (line 444)
- `src/giljo_mcp/tools/tool_accessor.py` — the 30 tool methods (your delegation target)
- `api/startup/core_services.py` — how `state.tool_accessor` is initialized

---

## Implementation Plan

### Step 1: Research FastMCP Integration Pattern

Before writing code, verify how the SDK mounts into an existing FastAPI app. Check:
- `from mcp.server.fastmcp import FastMCP` — class API
- `FastMCP.streamable_http_app()` or `mount_to_fastapi()` — how to mount
- How to pass per-request context (auth, tenant) to tool handlers
- How tool input schemas are defined with the SDK

Use web search if needed to check the latest `mcp` SDK documentation for Streamable HTTP + FastAPI integration patterns.

### Step 2: Create the FastMCP Server Module

Create `api/endpoints/mcp_sdk_server.py` (new file). This is the SDK-based replacement.

**Structure:**
```python
"""
MCP SDK Server — Streamable HTTP transport using official Anthropic MCP SDK.

Replaces custom JSON-RPC 2.0 implementation (mcp_http.py) with standard
MCP protocol transport. Tools delegate to existing ToolAccessor methods.
"""

from mcp.server.fastmcp import FastMCP

# Create the MCP server instance
mcp = FastMCP("giljo-mcp", version="1.0.0")

# Register all 30 tools with @mcp.tool() decorator
# Each tool is a thin wrapper that:
# 1. Extracts tenant context from the request
# 2. Delegates to state.tool_accessor.<method>()
# 3. Returns the result
```

**Tool registration pattern** (repeat for all 30 tools):
```python
@mcp.tool()
async def create_project(name: str, description: str = "", project_type: str = "feature") -> dict:
    """Create a new project in the active product."""
    # Get tenant context (injected by auth middleware)
    accessor = get_tool_accessor()
    tenant_key = get_current_tenant_key()
    return await accessor.create_project(
        name=name, description=description,
        project_type=project_type, tenant_key=tenant_key
    )
```

**Critical:** The exact tool names, parameter names, and descriptions must match the current `_build_*_tools()` schemas in `mcp_http.py`. Copy them exactly — clients depend on these names.

### Step 3: Map All 30 Tools

Reference the `tool_map` in `mcp_http.py` (lines 1083-1125) and the `_build_*_tools()` functions (lines 338-1012) for exact parameter schemas. Every tool must be registered.

Tool groups to map:
1. **Project Management** (3): `create_project`, `update_project_mission`, `update_agent_mission`
2. **Orchestrator** (2): `get_orchestrator_instructions`, `health_check`
3. **Messages** (3): `send_message`, `receive_messages`, `list_messages`
4. **Tasks** (1): `create_task`
5. **Agent Coordination** (6): `get_pending_jobs`, `report_progress`, `complete_job`, `reactivate_job`, `dismiss_reactivation`, `report_error`
6. **Orchestration** (4): `get_agent_mission`, `spawn_agent_job`, `get_agent_result`, `get_workflow_status`
7. **Context & Closeout** (5): `fetch_context`, `close_project_and_update_memory`, `write_360_memory`, `generate_download_token`, `get_agent_templates_for_export`
8. **Tuning** (1): `submit_tuning_review`
9. **Vision Analysis** (2): `gil_get_vision_doc`, `gil_write_product`
10. **Export** (1): `get_agent_templates_for_export`

**Note:** Some tools have complex input schemas (e.g., `fetch_context` has `sections` as a comma-separated string, `spawn_agent_job` has many optional params). Match schemas exactly from the `_build_*_tools()` functions.

### Step 4: Mount in app.py

In `api/app.py`, mount the new SDK server at a path (e.g., `/mcp/v2` temporarily) alongside the old endpoint. This allows testing without breaking the existing flow.

```python
# Temporary dual-mount for migration
from api.endpoints.mcp_sdk_server import mcp as mcp_server
app.mount("/mcp/v2", mcp_server.streamable_http_app())
```

**Important:** Research the exact mount API. It may be `app.mount()` with a Starlette/ASGI app, or a different pattern. The SDK docs will clarify.

### Step 5: Write Tests

**TDD approach — write tests FIRST:**

Create `tests/integration/test_mcp_sdk_transport.py`:

1. **Test tool discovery:** Send `initialize` + `tools/list` via the SDK transport, verify 30 tools returned
2. **Test tool call:** Call `health_check` via SDK transport, verify response
3. **Test Streamable HTTP compliance:** Verify `Mcp-Session-Id` header in response
4. **Test notification handling:** Send `notifications/initialized`, verify 202 or proper SSE ack

Use the `mcp` SDK's client library if available, or raw HTTP requests matching the Streamable HTTP spec.

### Step 6: Verify with Codex CLI

Manual verification (document in chain log):
1. Start the server with the new `/mcp/v2` mount
2. Configure Codex CLI to point to the new endpoint
3. Run `/mcp` in Codex CLI — should list all 30 tools
4. Call `health_check` tool — should return success

---

## Files to Create/Modify

| File | Action | Notes |
|------|--------|-------|
| `api/endpoints/mcp_sdk_server.py` | **CREATE** | New FastMCP server with 30 tool registrations |
| `api/app.py` | MODIFY | Add temporary mount at `/mcp/v2` (line ~444) |
| `tests/integration/test_mcp_sdk_transport.py` | **CREATE** | Transport discovery + tool call tests |

**Files to READ (not modify):**
- `api/endpoints/mcp_http.py` — tool schemas, tool_map, parameter definitions
- `src/giljo_mcp/tools/tool_accessor.py` — method signatures
- `api/startup/core_services.py` — accessor initialization

---

## Key Constraints

- Tool names must match exactly (clients may have hardcoded names)
- Tool parameter names and types must match current schemas
- Tool descriptions should match (used by LLMs for tool selection)
- The `HIDDEN_FROM_SCHEMA_TOOLS` set is currently empty — no filtering needed
- Do NOT touch `mcp_http.py` — it stays functional until 0846b removes it
- Do NOT implement auth/tenant injection yet — use placeholder/TODO for now. 0846b handles security

---

## Success Criteria

- [ ] `mcp_sdk_server.py` created with all 30 tools registered via `@mcp.tool()`
- [ ] Server starts without errors with both old and new endpoints mounted
- [ ] `tools/list` via SDK transport returns all 30 tools with correct schemas
- [ ] At least one tool callable via SDK transport (health_check)
- [ ] Integration test passes for tool discovery
- [ ] Chain log updated with notes for 0846b (exact mount path, any SDK quirks found)

---

## Chain Execution Instructions

### Step 1: Read Chain Log
Read `prompts/0846_chain/chain_log.json`
- Check `orchestrator_directives` — if STOP, halt immediately
- This is the first session — no previous `notes_for_next` to check

### Step 2: Mark Session Started
Update your session: `"status": "in_progress", "started_at": "<timestamp>"`

### Step 3: Execute Handover Tasks
Follow the implementation plan above. Use TDD discipline.

### Step 4: Update Chain Log
Update your session with:
- `tasks_completed`, `deviations`, `blockers_encountered`
- `notes_for_next`: **Critical info for 0846b** — exact SDK mount pattern used, how per-request context works in FastMCP, any SDK API surprises
- `cascading_impacts`: Changes that affect 0846b or 0846c
- `summary`, `status`: "complete", `completed_at`

### Step 5: STOP
**Do NOT spawn the next terminal.** The orchestrator will review your results, adjust downstream handovers if needed, and spawn the next session. Commit your chain log update and exit.
