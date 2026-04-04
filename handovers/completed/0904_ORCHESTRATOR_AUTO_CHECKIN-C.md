# Handover 0904: Orchestrator Auto Check-in (Multi-Terminal Mode)

**Date:** 2026-04-03
**To Agent:** Next Session
**Priority:** Medium
**Estimated Complexity:** 4-6 hours
**Status:** Not Started
**Edition Scope:** CE

---

## Task Summary

Add an auto check-in toggle and interval slider to the Implementation tab (JobsTab) that injects a self-polling protocol into the orchestrator's instructions. In multi-terminal mode, the orchestrator dispatches agents to separate terminals and currently waits passively for the user to manually prompt it to check on progress. This feature automates that coordination loop.

---

## Context and Background

### The Problem

In multi-terminal execution mode, the orchestrator runs in one terminal while specialist agents (analyzer, implementer, tester, etc.) run in their own isolated terminals. All communication flows through the MCP server's message queue (`send_message` / `receive_messages`).

Today, after the orchestrator dispatches agents, it goes idle and waits for the user to manually say "check on your agents" or similar. The user becomes the polling mechanism. This is friction — the orchestrator has all the tools it needs to self-monitor, it just lacks the instruction to do so.

### The Solution

A UI toggle + interval slider on the Implementation tab that, when enabled, causes a **protocol injection** into the orchestrator's instructions. The orchestrator receives an additional protocol chapter telling it to self-loop: dispatch agents → sleep for N seconds → call `receive_messages()` → assess progress → repeat until completion.

### Why This Works with the Passive Architecture

The MCP server remains passive. No new server-side polling, no cron jobs, no AI logic. The "automation" is purely a prompt instruction — the orchestrator agent (running in the user's terminal) uses its own sleep/wait capability to pace itself, then re-engages with existing MCP tools. The server just stores the setting and injects it into the protocol response.

### Key Architectural Insight: Hot Injection at Play Time

The implementation prompt copied to clipboard at Play time is intentionally thin (~10 lines). The orchestrator's real protocol comes from `get_agent_mission()` / `get_orchestrator_instructions()`, which are fetched **at runtime** via MCP tools. This means the auto check-in setting can be toggled right before clicking Play — no need to set it during staging. The protocol is assembled live from the database.

---

## Technical Details

### Data Model

**Option A (Recommended): New columns on `projects` table**

Two new columns on the `Project` model (`src/giljo_mcp/models/projects.py`):

```python
# Handover 0904: Orchestrator auto check-in settings
auto_checkin_enabled = Column(
    Boolean,
    nullable=False,
    default=False,
    server_default=text("false"),
    comment="Enable orchestrator self-polling in multi-terminal mode",
)
auto_checkin_interval = Column(
    Integer,
    nullable=False,
    default=60,
    server_default=text("60"),
    comment="Auto check-in interval in seconds (30, 60, or 90)",
)
```

Rationale: These are project-level settings (not user-level or product-level). Different projects may want different intervals. Storing on the project keeps it simple and co-located with `execution_mode`.

**Migration:** Incremental Alembic migration with idempotency guards (check column exists before adding).

### Backend Changes

#### 1. Protocol Builder — New CH6 (`src/giljo_mcp/services/protocol_builder.py`)

Add a new function `_build_ch6_auto_checkin()` and wire it into `_build_orchestrator_protocol()`.

The chapter should ONLY be included when:
- `execution_mode == "multi_terminal"` (not CLI subagent modes — those have different coordination)
- `auto_checkin_enabled == True` on the project

**Protocol text (approximate — refine during implementation):**

```
════════════════════════════════════════════════════════════════════════════
                CH6: AUTO CHECK-IN PROTOCOL
════════════════════════════════════════════════════════════════════════════

ORCHESTRATOR SELF-MONITORING MODE (Enabled by user)

After dispatching all agents to their terminals:

1. Set your status: set_agent_status(job_id, status="sleeping", 
   reason="Auto check-in active, interval: {interval}s")

2. Wait {interval} seconds (use your tool's native sleep/pause).

3. Wake and check in:
   a. Call receive_messages() — process any agent reports, questions, or completions
   b. Assess progress: Are agents blocked? Have any completed? Do handoffs need coordinating?
   c. Take action as needed: send coordination messages, spawn next-phase agents, unblock

4. If all agents have completed: proceed to Completion Protocol (CH5).
   If agents are still working: return to step 1.

IMPORTANT:
- Each check-in cycle consumes tokens. The user has chosen this trade-off.
- If an agent reports being blocked, address it immediately rather than sleeping again.
- If you have nothing actionable after a check-in, go back to sleep — do not generate 
  unnecessary messages.

────────────────────────────────────────────────────────────────────────────
```

#### 2. Protocol Builder Wiring (`protocol_builder.py`)

Update `_build_orchestrator_protocol()` signature to accept `auto_checkin_enabled: bool` and `auto_checkin_interval: int` parameters. Add CH6 to the returned dict when enabled:

```python
# In _build_orchestrator_protocol():
if auto_checkin_enabled and not cli_mode:
    ch6 = _build_ch6_auto_checkin(auto_checkin_interval)
else:
    ch6 = ""

return {
    "ch1_your_mission": ch1,
    "ch2_startup_sequence": ch2,
    "ch3_agent_spawning_rules": ch3,
    "ch4_error_handling": ch4,
    "ch5_reference": ch5,
    "ch6_auto_checkin": ch6,  # New
    "navigation_hint": "Reference chapters by name (e.g., 'see CH4 for error handling')",
}
```

#### 3. Mission Service (`src/giljo_mcp/services/mission_service.py`)

In `_build_orchestrator_response()` (line ~993), pass the new fields through to `_build_orchestrator_protocol()`:

```python
# Read from project record
auto_checkin_enabled = getattr(project, "auto_checkin_enabled", False)
auto_checkin_interval = getattr(project, "auto_checkin_interval", 60)

orchestrator_protocol = _build_orchestrator_protocol(
    cli_mode=cli_mode,
    project_id=str(project.id),
    orchestrator_id=job_id,
    tenant_key=tenant_key,
    include_implementation_reference=not is_staging,
    field_toggles=field_toggles,
    depth_config=depth_config,
    product_id=str(product.id) if product else None,
    tool=protocol_tool,
    auto_checkin_enabled=auto_checkin_enabled,      # New
    auto_checkin_interval=auto_checkin_interval,     # New
)
```

#### 4. API Endpoint for Updating Settings

Add a PATCH endpoint (or extend existing project update) to persist the toggle and interval. The frontend needs to write these values before the user clicks Play.

Likely location: `api/endpoints/projects.py` — extend the existing project update endpoint to accept `auto_checkin_enabled` and `auto_checkin_interval` fields in the update payload.

Ensure:
- `auto_checkin_interval` is validated to allowed values: 30, 60, or 90 (seconds)
- `auto_checkin_enabled` requires `execution_mode == "multi_terminal"` (reject if CLI mode)
- Standard auth + tenant_key filtering

### Frontend Changes

#### 1. JobsTab.vue (`frontend/src/components/projects/JobsTab.vue`)

Add UI controls **above the agent table**, visible only when:
- `execution_mode === 'multi_terminal'`
- Staging is complete (`stagingComplete === true`)

**UI Layout:**

```
┌──────────────────────────────────────────────────┐
│ Orchestrator Auto Check-in          [Toggle OFF]  │
│ Check-in every:  ○ 0:30  ● 1:00  ○ 1:30          │
│                                                    │
│ ┌─ Agent Table ─────────────────────────────────┐ │
│ │ Phase | Agent | Status | Actions              │ │
│ │  ...                                          │ │
│ └───────────────────────────────────────────────┘ │
```

- **Toggle:** v-switch or similar, bound to `auto_checkin_enabled`
- **Interval selector:** Radio group or segmented button with three options (30s, 60s, 90s), bound to `auto_checkin_interval`
- **Interval selector disabled** when toggle is OFF
- On change: PATCH project with new values immediately (debounced, no save button)
- Use `.smooth-border` card wrapper, `--text-muted` for labels per design system

#### 2. API Integration

Call the project update endpoint on toggle/slider change. Ensure the values are persisted before the user clicks Play, since Play triggers `get_agent_mission()` which reads them.

### Files to Modify

| File | Change |
|------|--------|
| `src/giljo_mcp/models/projects.py` | Add `auto_checkin_enabled` + `auto_checkin_interval` columns |
| `migrations/versions/xxxx_add_auto_checkin.py` | New incremental migration with idempotency guards |
| `src/giljo_mcp/services/protocol_builder.py` | Add `_build_ch6_auto_checkin()`, update `_build_orchestrator_protocol()` |
| `src/giljo_mcp/services/mission_service.py` | Pass auto-checkin params through `_build_orchestrator_response()` |
| `api/endpoints/projects.py` | Accept auto-checkin fields in project update |
| `frontend/src/components/projects/JobsTab.vue` | Toggle + interval UI above agent table |
| `frontend/src/services/api.js` | Ensure project update call includes new fields |

---

## Implementation Plan

### Phase 1: Backend — Model + Migration (1 hour)

1. Add two columns to `Project` model in `projects.py`
2. Create Alembic migration with idempotency guards
3. Verify migration runs on existing database
4. Update project update endpoint to accept and validate new fields
5. Write backend tests: validation (interval must be 30/60/90), tenant isolation

**Tests:**
- `test_auto_checkin_defaults_to_disabled` — new projects have `auto_checkin_enabled=False`, `auto_checkin_interval=60`
- `test_auto_checkin_interval_validation` — rejects values other than 30, 60, 90
- `test_auto_checkin_requires_multi_terminal` — rejects enable when `execution_mode` is CLI

### Phase 2: Backend — Protocol Injection (1.5 hours)

1. Add `_build_ch6_auto_checkin(interval: int)` to `protocol_builder.py`
2. Update `_build_orchestrator_protocol()` signature and return dict
3. Wire through `mission_service.py:_build_orchestrator_response()`
4. Verify CH6 only appears when enabled + multi-terminal

**Tests:**
- `test_protocol_includes_ch6_when_enabled` — CH6 present with correct interval
- `test_protocol_excludes_ch6_when_disabled` — CH6 absent when toggle off
- `test_protocol_excludes_ch6_in_cli_mode` — CH6 absent for CLI subagent modes
- `test_ch6_interval_substitution` — interval value appears in protocol text

### Phase 3: Frontend — UI Controls (1.5 hours)

1. Add toggle + interval controls to `JobsTab.vue`
2. Conditional visibility: multi-terminal only, staging complete
3. Wire API calls on change (debounced)
4. Disable interval selector when toggle is off
5. Style per design system (`.smooth-border`, `--text-muted`)

**Tests (Vitest):**
- `test_auto_checkin_toggle_hidden_in_cli_mode`
- `test_auto_checkin_toggle_visible_in_multi_terminal`
- `test_interval_selector_disabled_when_toggle_off`
- `test_toggle_change_calls_api`

### Phase 4: Integration Testing (1 hour)

1. End-to-end: enable toggle → click Play → verify orchestrator prompt includes CH6
2. Verify CH6 absent when toggle off
3. Verify interval value flows through correctly
4. Manual test: paste implementation prompt into Claude Code, verify orchestrator self-loops

---

## Testing Requirements

### Unit Tests (Backend)
- Model defaults and validation
- Protocol builder CH6 generation
- Mission service parameter passthrough

### Unit Tests (Frontend)
- Toggle visibility conditions
- Interval selector state management
- API call on change

### Integration Tests
- Full flow: toggle → Play → protocol includes CH6
- Verify existing multi-terminal flow unaffected when toggle off
- Verify CLI modes unaffected

### Manual Testing
1. Create project in multi-terminal mode
2. Complete staging
3. Enable auto check-in, set interval to 0:30
4. Click Play on orchestrator, paste prompt into terminal
5. Verify orchestrator fetches mission with CH6
6. Verify orchestrator attempts to self-loop (agent-dependent behavior — observe, don't assert)

---

## Dependencies and Blockers

**Dependencies:** None. All infrastructure exists:
- `protocol_builder.py` chapter system is extensible
- `mission_service.py` already passes project data to protocol builder
- `JobsTab.vue` already has conditional UI based on execution mode
- `receive_messages`, `set_agent_status`, `send_message` MCP tools all exist

**Blockers:** None identified.

**Platform Consideration:** Different agentic tools handle "sleep for N seconds" differently. Claude Code supports it natively. Codex and Gemini CLI may behave differently — but this feature is multi-terminal only (not CLI subagent mode), so the orchestrator is always a full agentic session. The protocol text should use general language ("wait N seconds" / "pause between cycles") rather than tool-specific sleep syntax.

---

## Success Criteria

- [ ] Toggle and slider visible on Implementation tab in multi-terminal mode only
- [ ] Settings persist to database and survive page refresh
- [ ] Orchestrator protocol includes CH6 when enabled, excludes when disabled
- [ ] CH6 never appears in CLI subagent modes
- [ ] Interval value correctly substituted in protocol text
- [ ] Existing orchestrator flow completely unaffected when toggle is off
- [ ] All new backend + frontend tests pass
- [ ] Migration is idempotent (safe for fresh installs and upgrades)

---

## Rollback Plan

- Revert migration (drop two columns — no data loss, columns are new)
- Revert protocol_builder.py changes (CH6 function + wiring)
- Revert mission_service.py parameter passthrough
- Revert JobsTab.vue UI additions
- Risk: zero — feature is additive, no existing behavior modified
