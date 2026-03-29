# Handover 0855b: Setup Wizard — WebSocket Setup Events

**Date:** 2026-03-28
**Edition Scope:** CE
**From Agent:** Planning Session
**To Agent:** tdd-implementor
**Priority:** High
**Estimated Complexity:** 2 hours
**Status:** Not Started
**Series:** 0855a-g (Setup Wizard Redesign)
**Spec:** `handovers/SETUP_WIZARD_REDESIGN.md`

---

## Read First (MANDATORY)

1. `handovers/HANDOVER_INSTRUCTIONS.md` — coding standards, TDD protocol, quality gates
2. `handovers/Reference_docs/QUICK_LAUNCH.txt` — project bootstrap
3. `handovers/Reference_docs/AGENT_FLOW_SUMMARY.md` — agent flow context
4. `handovers/SETUP_WIZARD_REDESIGN.md` — full spec for the wizard redesign

**Search before you build.** Use Serena `find_symbol` / `get_symbols_overview` to check if functionality already exists. Extend existing services — don't create new modules unless justified.

---

## Task Summary

Add 3 new WebSocket event types (`setup:tool_connected`, `setup:commands_installed`, `setup:agents_downloaded`) to the event schema and wire emission points at the MCP health check, bootstrap fetch, and agent export endpoints. These events drive the live status indicators in the setup wizard overlay (Steps 2 and 3).

---

## Context and Background

The existing event system (`api/events/schemas.py`) has 7 event types for project/agent/message domains. The setup wizard needs real-time feedback when:
1. A user's AI coding tool successfully connects and sends a health check
2. Slash commands/skills are fetched (bootstrap prompt executed)
3. Agent templates are downloaded

Events use the existing `EventFactory` pattern with Pydantic validation and broadcast via `WebSocketManager.broadcast_event_to_tenant()`.

---

## Technical Details

### Event Schema Changes

**File:** `api/events/schemas.py`

Add 3 new event models following the existing pattern:

```python
class SetupToolConnectedEvent(BaseWebSocketEvent):
    type: Literal["setup:tool_connected"] = "setup:tool_connected"
    data: SetupToolConnectedData

class SetupToolConnectedData(BaseModel):
    tenant_key: str
    user_id: str
    tool_name: str  # "claude_code", "codex_cli", "gemini_cli"
    connected_at: str  # ISO timestamp

class SetupCommandsInstalledEvent(BaseWebSocketEvent):
    type: Literal["setup:commands_installed"] = "setup:commands_installed"
    data: SetupCommandsInstalledData

class SetupCommandsInstalledData(BaseModel):
    tenant_key: str
    user_id: str
    tool_name: str
    command_count: int

class SetupAgentsDownloadedEvent(BaseWebSocketEvent):
    type: Literal["setup:agents_downloaded"] = "setup:agents_downloaded"
    data: SetupAgentsDownloadedData

class SetupAgentsDownloadedData(BaseModel):
    tenant_key: str
    user_id: str
    agent_count: int
```

Add `EventFactory` methods:

```python
@staticmethod
def setup_tool_connected(tenant_key, user_id, tool_name):
    ...

@staticmethod
def setup_commands_installed(tenant_key, user_id, tool_name, command_count):
    ...

@staticmethod
def setup_agents_downloaded(tenant_key, user_id, agent_count):
    ...
```

### Emission Points (Exact Locations)

**1. `setup:tool_connected`**
- **File:** `api/endpoints/mcp_http.py`
- **Function:** `handle_initialize` (lines 159-190), dispatched from `mcp_endpoint` (lines 1237-1355) when JSON-RPC method is `"initialize"`
- **Logic:** After successful initialize response, emit event with `tool_name` derived from the `client_info` in the initialize request (MCP protocol provides client name/version)
- **Note:** Also check `api/app.py` `health_check` (lines 479-501) at `GET /health` — this is the HTTP health endpoint that AI tools may hit separately

**2. `setup:commands_installed`**
- **File:** `api/endpoints/downloads.py`
- **Function:** `get_bootstrap_prompt` (lines 440-559)
- **Route:** `GET /api/download/bootstrap-prompt?platform=claude_code|gemini_cli|codex_cli`
- **Logic:** After successful response, emit event with `tool_name` from the `platform` query parameter

**3. `setup:agents_downloaded`**
- **File:** `api/endpoints/downloads.py`
- **Function:** `download_agent_templates` (lines 167-346)
- **Route:** `GET /api/download/agent-templates.zip`
- **Logic:** After successful ZIP generation and response, emit event with count of templates in the ZIP

### Cascading Analysis

- **Downstream:** No model changes. Events are fire-and-forget broadcasts.
- **Upstream:** No schema changes needed — events use existing WebSocket infrastructure.
- **Sibling:** Existing 7 event types unaffected. New types are additive.

---

## Implementation Plan

### Phase 1: Event Schemas (TDD)
1. Write tests: each event type validates correctly, EventFactory methods produce valid events
2. Add 3 event models + 3 data models to `schemas.py`
3. Add 3 EventFactory methods
4. Verify tests pass

### Phase 2: Locate Emission Points
1. Use Serena/grep to find: MCP health check handler, slash command fetch endpoint, agent export endpoint
2. Document exact file paths and function names

### Phase 3: Wire Emissions (TDD)
1. Write integration tests: each trigger point emits the correct event type
2. Add `await ws_manager.broadcast_event_to_tenant(event)` calls at each trigger point
3. Ensure emissions don't block the main response (fire-and-forget pattern)
4. Verify tests pass

**Recommended Sub-Agents:** tdd-implementor (tests + wiring)

---

## Testing Requirements

**Unit Tests:**
- Event model validation (all required fields, correct types)
- EventFactory methods return correct event types

**Integration Tests:**
- Health check request → `setup:tool_connected` event emitted
- Slash command fetch → `setup:commands_installed` event emitted
- Agent export fetch → `setup:agents_downloaded` event emitted
- Events target correct tenant_key

---

## Dependencies and Blockers

**Dependencies:** None — can run in parallel with 0855a.
**Blockers:** Need to locate exact emission point files (Phase 2 research).

---

## Success Criteria

- [ ] 3 new event types defined in `api/events/schemas.py`
- [ ] EventFactory methods for all 3 types
- [ ] Events emitted at correct trigger points
- [ ] Events include tenant_key and user_id for targeted delivery
- [ ] Existing event types unaffected (regression check)
- [ ] All new tests passing

---

## Rollback Plan

Remove the 3 event models and the emission calls. No schema changes to revert.

---

## Files to Modify

| File | Change |
|------|--------|
| `api/events/schemas.py` | Add 3 event models + EventFactory methods |
| `api/endpoints/mcp_http.py` (`handle_initialize`, line ~159) | Emit `setup:tool_connected` |
| `api/endpoints/downloads.py` (`get_bootstrap_prompt`, line ~440) | Emit `setup:commands_installed` |
| `api/endpoints/downloads.py` (`download_agent_templates`, line ~167) | Emit `setup:agents_downloaded` |
| `tests/` | New test file for setup events |

---

## Chain Execution Instructions (Orchestrator-Gated v3)

You are session 2 of 7 in the 0855 chain. You are on branch `feature/0855-setup-wizard`. You may be running in PARALLEL with 0855a — do not depend on 0855a's schema changes.

### Step 1: Read Chain Log
Read `prompts/0855_chain/chain_log.json`
- Check `orchestrator_directives` — if STOP, halt immediately
- Check 0855a's `notes_for_next` if it completed before you

### Step 2: Mark Session Started
Update your session in chain_log.json: `"status": "in_progress", "started_at": "<timestamp>"`

### Step 3: Execute Handover Tasks
Follow the Implementation Plan above. Use tdd-implementor subagent. NOTE: If `api/endpoints/mcp_http.py` has been significantly modified by 0846 work, emit `setup:tool_connected` from the health_check endpoint in `api/app.py` instead.

### Step 4: Update Chain Log
Update your session in `prompts/0855_chain/chain_log.json` with:
- `tasks_completed`, `deviations`, `blockers_encountered`
- `notes_for_next`: Critical info for 0855d/0855e. Include exact event type strings, data model class names, EventFactory method signatures. If emission points changed from the handover spec, document the actual locations.
- `cascading_impacts`: Any changes that affect downstream handovers
- `summary`, `status`: "complete", `completed_at`

### Step 5: STOP
**Do NOT spawn the next terminal.** Commit your chain log update and exit.
