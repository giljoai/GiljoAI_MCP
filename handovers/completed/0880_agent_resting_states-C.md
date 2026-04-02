# 0880 — Agent Resting States (idle + sleeping)

**Edition Scope:** CE
**Priority:** High
**Estimated Sessions:** 1
**Branch:** `feature/0880-agent-resting-states`

---

## Problem

Two UX problems in multi-terminal orchestration mode:

1. **False "Working" status.** After the orchestrator spawns agents and dispatches tasks, it sits idle in its terminal — but the dashboard shows "Working". The user must manually bump it to check messages. The UI lies about what the agent is doing.

2. **No periodic check-in state.** Creative users ask the orchestrator to sleep in 10-15 minute intervals and re-check the MCP server. There is no state to represent "sleeping, will wake up and check". The dashboard still shows "Working" during these sleep intervals.

## Solution

### 1. Rename MCP tool: `report_error` → `set_agent_status`

Expand the existing `report_error` MCP tool into a general-purpose status-setting tool. This avoids adding a new tool to an already long tool list (26+ tools). Net tool count change: **zero** (rename, not add).

New signature:
```python
@mcp.tool(description="Set agent status — blocked (need help), idle (monitoring agents), or sleeping (periodic check-in)")
async def set_agent_status(
    job_id: str,
    status: str,                    # "blocked" | "idle" | "sleeping"
    reason: str = "",               # displayed in dashboard
    wake_in_minutes: int | None = None,  # only meaningful for "sleeping"
    ctx: Context = None,
) -> dict:
```

### 2. Two new agent states

| State | Label (UI) | Meaning | Triggered by | Color |
|-------|-----------|---------|-------------|-------|
| `idle` | "Monitoring" | Agent dispatched work, resting until needed | `set_agent_status(status="idle")` | Muted blue-grey |
| `sleeping` | "Sleeping (Nm)" | Agent will wake and re-check in N minutes | `set_agent_status(status="sleeping", wake_in_minutes=N)` | Soft indigo/purple |

### 3. Auto-wake transitions

When an agent in `idle` or `sleeping` calls any active MCP tool (`report_progress`, `receive_messages`, `get_workflow_status`, etc.), the server auto-transitions them back to `working`. Same pattern as existing `blocked → working` on `report_progress()`. **No new tool needed for wake-up.**

### 4. Orchestrator protocol injection (orchestrators only)

Add a short block to the **orchestrator coordination protocol** and the **CH5 implementation phase reference** (staging orchestrator protocol). This instructs orchestrators about idle/sleeping. Worker agents do NOT receive this — it's irrelevant to them.

Injection point in `_generate_orchestrator_protocol()` — after Phase 2 coordination loop, before Phase 3 closeout:

```
### RESTING STATES (between coordination loops)

After completing a coordination loop with no actionable work remaining:

**If waiting for user to start agents (multi-terminal):**
  → `set_agent_status(job_id="{job_id}", status="idle", reason="Monitoring — waiting for agents to start")`
  → Dashboard shows "Monitoring" — user knows you're available but not burning tokens

**If you want periodic auto-check-in:**
  → Ask the user: "Would you like me to periodically check on agents? I can sleep and re-check every N minutes. Note: this increases token consumption."
  → If yes: `set_agent_status(job_id="{job_id}", status="sleeping", wake_in_minutes=15, reason="Auto-monitoring")`
  → Then sleep for the specified interval, wake, run the coordination loop, repeat
  → Any MCP call after waking auto-transitions you back to "working"

**Blocked vs Idle vs Sleeping:**
  - `blocked` = I need human help to continue (shows "Needs Input")
  - `idle` = I'm done dispatching, nothing to do right now (shows "Monitoring")
  - `sleeping` = I'll check back in N minutes automatically (shows "Sleeping")
```

Injection point in `_build_ch5_reference()` — in the IMPLEMENTATION PHASE MONITORING section (line ~1350), update the existing auto-monitor guidance:

```
4. After dispatching agents: `set_agent_status(job_id, "idle", reason="Agents dispatched, monitoring")`
5. If user wants auto-monitoring: `set_agent_status(job_id, "sleeping", wake_in_minutes=15)`
```

## Design Invariant (CRITICAL)

**All MCP tool references live ONLY in `protocol_builder.py` — never in agent templates.**

Verified: `templates.py` model, `template_service.py`, seed data, export flows — zero MCP tool references. Templates carry role/behavioral guidance. Protocol mechanics (tool names, state transitions, lifecycle phases) are injected at mission-fetch time by `protocol_builder.py`.

This handover MUST preserve this invariant. The new `set_agent_status` tool name must appear ONLY in protocol injection code.

## Files to Modify

### Backend (6 files)

| File | Change |
|------|--------|
| `api/endpoints/mcp_sdk_server.py` | Rename `report_error` → `set_agent_status`. Add `status` param (default `"blocked"` for backward compat during rollout). Add `wake_in_minutes` param. Validate `status` ∈ `{"blocked", "idle", "sleeping"}`. |
| `src/giljo_mcp/tools/tool_accessor.py` | Rename `report_error` → `set_agent_status`. Pass `status` through. |
| `src/giljo_mcp/services/orchestration_service.py` | Rename `report_error` → `set_agent_status`. Use `status` param instead of hardcoded `"blocked"`. For `idle`/`sleeping`: set status, store reason in `block_reason` (reuse existing column). For `sleeping`: optionally store `wake_in_minutes` in block_reason JSON or a new lightweight field. WebSocket broadcast already generic — just passes status through. |
| `api/events/schemas.py` | Add `"idle"`, `"sleeping"` to `valid_statuses` set (line 244). |
| `src/giljo_mcp/models/agent_identity.py` | Update `status` column comment to include `idle`, `sleeping` (line 179). |
| `src/giljo_mcp/services/protocol_builder.py` | (1) Orchestrator protocol: add resting states block after Phase 2, before Phase 3. (2) CH5 reference: update implementation monitoring section. (3) Worker protocol Phase 5: rename `report_error` → `set_agent_status(status="blocked")`. (4) CH4 error handling: rename references. (5) Status transition table: add `idle` and `sleeping` transitions. **Orchestrator-only injection:** idle/sleeping instructions go in `_generate_orchestrator_protocol()` and `_build_ch5_reference()` only — NOT in `_generate_agent_protocol()`. |

### Frontend (1 file)

| File | Change |
|------|--------|
| `frontend/src/utils/statusConfig.js` | Add `idle` and `sleeping` entries to both `statusConfig` and `STATUS_CONFIG` objects. |

**statusConfig (JobsTab):**
```javascript
idle: {
  label: 'Monitoring',
  color: '#7a9bb5',     // Muted blue-grey
  italic: true,
  chipColor: 'default',
},
sleeping: {
  label: 'Sleeping',    // Will be enhanced with "(Nm)" if wake_in_minutes available
  color: '#9b89b3',     // Soft indigo
  italic: true,
  chipColor: 'default',
},
```

**STATUS_CONFIG (legacy):**
```javascript
idle: {
  icon: 'mdi-eye-outline',
  color: 'blue-grey',
  label: 'Monitoring',
  description: 'Agent is idle, monitoring for activity',
},
sleeping: {
  icon: 'mdi-sleep',
  color: 'deep-purple-lighten-2',
  label: 'Sleeping',
  description: 'Agent is sleeping, will auto-check in',
},
```

### Docs (2 files)

| File | Change |
|------|--------|
| `docs/architecture/state-transition-diagram.md` | Add `idle` and `sleeping` states + transitions. |
| `handovers/HANDOVER_INSTRUCTIONS.md` | Update valid statuses list (line 193) to include `idle`, `sleeping`. |

### Auto-wake logic

In `orchestration_service.py` `report_progress()` method — extend the existing `blocked → working` auto-transition to also cover `idle → working` and `sleeping → working`. Grep for where `blocked` is checked and auto-transitioned; add `idle` and `sleeping` to the same condition.

Similarly check `receive_messages`, `get_workflow_status`, and any other active tool that should trigger a wake-up. The principle: any tool that indicates the agent is actively doing work should auto-transition from a resting state.

### WebSocket

The `websocket.py` handler (line 529) currently shows `block_reason` for `blocked` and `silent` statuses. Extend to also include `idle` and `sleeping` so the reason text reaches the frontend.

## State Transition Summary (after this handover)

```
waiting ─[get_agent_mission()]─→ working (auto)
working ─[report_progress()]──→ working (updates TODOs)
working ─[set_agent_status("blocked")]──→ blocked
working ─[set_agent_status("idle")]─────→ idle
working ─[set_agent_status("sleeping")]─→ sleeping
working ─[complete_job()]──→ complete
idle ────[report_progress()/receive_messages()/etc.]──→ working (auto)
sleeping─[report_progress()/receive_messages()/etc.]──→ working (auto)
blocked ─[report_progress()]──→ working (auto)
blocked ─[complete_job()]─────→ complete
```

## What NOT to Do

- Do NOT add `idle` or `sleeping` to agent templates — protocol injection only
- Do NOT create a new MCP tool — rename `report_error` to `set_agent_status`
- Do NOT inject idle/sleeping instructions into worker agent protocol (`_generate_agent_protocol`) — orchestrators and handover orchestrators only
- Do NOT add database migration for `wake_in_minutes` — store in `block_reason` as JSON string (e.g., `"Auto-monitoring | wake_in_minutes=15"`) or as structured reason text
- Do NOT add server-side wake timers — the agent manages its own sleep locally

## Testing Checklist

- [ ] `set_agent_status(status="blocked")` behaves identically to old `report_error`
- [ ] `set_agent_status(status="idle")` sets status, broadcasts WebSocket event
- [ ] `set_agent_status(status="sleeping", wake_in_minutes=15)` sets status with reason
- [ ] `report_progress()` auto-wakes from `idle` → `working`
- [ ] `report_progress()` auto-wakes from `sleeping` → `working`
- [ ] `receive_messages()` auto-wakes from `idle`/`sleeping` → `working`
- [ ] Frontend shows "Monitoring" for `idle`, "Sleeping" for `sleeping`
- [ ] Orchestrator protocol contains idle/sleeping instructions
- [ ] Worker protocol does NOT contain idle/sleeping instructions
- [ ] No MCP tool references exist in agent templates (invariant check)
- [ ] Invalid status values rejected with clear error message
