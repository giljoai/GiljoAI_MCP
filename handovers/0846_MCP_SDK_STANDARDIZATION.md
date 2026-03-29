# Handover 0846: MCP SDK Standardization (Series Coordinator)

**Date:** 2026-03-29
**From Agent:** Codex session (user + Claude)
**To Agent:** Next Session (orchestrator-gated chain)
**Priority:** High
**Estimated Complexity:** 3 sessions, ~4-6 hours total
**Status:** Not Started
**Edition Scope:** CE

---

## Task Summary

Replace the custom JSON-RPC 2.0 MCP transport in `api/endpoints/mcp_http.py` (~1,376 lines) with the official Anthropic MCP Python SDK (`FastMCP` + Streamable HTTP). This standardizes the server so `/mcp` tool discovery works natively on Claude Code CLI, Codex CLI, Gemini CLI, and any future MCP client — no custom plumbing.

**Why now:** Pre-release window. Custom transport doesn't advertise tools via standard MCP discovery (`/mcp` shows "Tools: (none)" on Codex CLI). The SDK is MIT-licensed, Anthropic-authored, and the only MCP standard that matters. Standardizing now avoids accumulating more custom transport debt.

**What stays unchanged:** `ToolAccessor` business logic, `MCPSessionManager` PostgreSQL persistence, tenant isolation model, Bearer token auth flow, entity hierarchy, frontend dashboard.

---

## Series Structure (Orchestrator-Gated v3)

| Phase | ID | Title | Color | Est. | Subagents |
|-------|-----|-------|-------|------|-----------|
| 1 | 0846a | FastMCP SDK Transport Replacement | #4CAF50 | 1.5-2h | tdd-implementor |
| 2 | 0846b | Security Re-integration & Old Code Removal | #2196F3 | 1.5-2h | tdd-implementor, backend-integration-tester |
| 3 | 0846c | Documentation, Frontend & Test Updates | #9C27B0 | 1-1.5h | documentation-manager |

**Execution mode:** Orchestrator-Gated (v3). Agents STOP after completing. Orchestrator reviews chain log, adjusts downstream handovers, then spawns next.

**Branch:** `feature/0846-mcp-sdk-standardization`

**Chain log:** `prompts/0846_chain/chain_log.json`

---

## Architecture Decision

### What we're replacing

The current `mcp_http.py` implements a **custom JSON-RPC 2.0 POST endpoint**. It handles `initialize`, `tools/list`, and `tools/call` manually. It works for tool execution but does NOT comply with the MCP Streamable HTTP transport spec:
- Missing `Mcp-Session-Id` header flow
- No GET handler for SSE stream
- No `notifications/initialized` proper handling
- Result: MCP clients connect but can't discover tools via standard protocol

### What we're adopting

The official `mcp` Python SDK (MIT, `pip install mcp`, already in `requirements.txt` as `mcp>=1.23.0`). Specifically:
- `FastMCP` server class with `@mcp.tool()` decorator registration
- `mount_to_fastapi()` or `streamable_http_app()` for FastAPI integration
- Built-in Streamable HTTP transport (handles sessions, SSE, tool discovery)
- Our auth + tenant security wired as middleware BEFORE SDK handles request

### What we're NOT changing

- **Auth model:** Bearer token (JWT or API key) via `Authorization` header — all three CLIs already support this
- **Tenant isolation:** `validate_and_override_tenant_key()` logic preserved, wired as tool middleware
- **Session persistence:** `MCPSessionManager` + PostgreSQL `mcp_sessions` table stays
- **ToolAccessor:** All 30 tool methods untouched — SDK tools delegate to existing accessor
- **Entity hierarchy:** Org → User → Product → Project → Job → Agent unaffected
- **Frontend dashboard:** No UI changes except MCP config command strings if transport type keyword changes

### Mental model

```
┌─────────────────────────────────────────┐
│  MCP Client (Claude/Codex/Gemini CLI)   │
│  sends: Authorization: Bearer <token>   │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│  FastAPI middleware (OUR code, kept)     │
│  Bearer → JWT or API key → user →       │
│  tenant_key → attach to request state   │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│  MCP SDK FastMCP (NEW - replaces JSONRPC│
│  Handles: transport, sessions, routing  │
│  Validates: args against tool schemas   │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│  OUR tool wrappers (NEW thin layer)     │
│  tenant_key injection, arg validation   │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│  ToolAccessor (UNCHANGED)               │
│  Business logic, tenant-filtered queries│
└─────────────────────────────────────────┘
```

---

## Cascading Impact Analysis

### Downstream impact
- **ToolAccessor methods:** Zero change — SDK tool wrappers call the same methods with the same args
- **MCPSessionManager:** Kept. We bridge SDK transport sessions to our PostgreSQL sessions in middleware
- **Database:** No schema changes. `mcp_sessions` table stays as-is
- **Frontend:** Config wizard MCP add commands may need transport type keyword update (e.g., `--transport http` → `--transport streamable-http` if SDK uses different identifier)
- **Tests:** Manual test scripts (`test_mcp_http_manual.sh/.ps1`) need rewrite for new transport. Unit/integration tests for auth stay

### Upstream impact
- **app.py:** Router registration changes (replace `include_router(mcp_http.router)` with SDK app mount)
- **install.py:** No impact — no new dependencies (mcp already in requirements.txt), no schema changes
- **config.yaml:** No impact

### Sibling impact
- **Other API endpoints:** Unaffected — REST API, WebSocket, OAuth endpoints are separate
- **MCP installer endpoint (`mcp_installer.py`):** May need updated example commands

---

## Dependencies

- `mcp>=1.23.0` already in `requirements.txt`
- No new external dependencies
- No database migrations needed

## Rollback Plan

Feature branch. If anything breaks: `git checkout master`. Old endpoint preserved until 0846b confirms new one works.

---

## Success Criteria

1. Codex CLI `/mcp` command lists all 30 giljo-mcp tools (not "Tools: (none)")
2. Claude Code CLI can discover and call tools via standard MCP transport
3. All 30 tools callable with proper tenant isolation
4. Bearer token auth works on all three platforms
5. Zero regression in existing tool behavior
6. `mcp_http.py` reduced from ~1,376 lines to <400 lines
7. All documentation updated to reflect SDK-based transport
