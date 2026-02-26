# Handover 0498: Early Termination Protocol + Jobs Dashboard Reduction

**Date:** 2026-02-26
**From Agent:** Investigation Session (Claude Code CLI)
**To Agent:** Next Session (tdd-implementor recommended)
**Priority:** High
**Estimated Complexity:** 1 day
**Status:** Not Started

---

## Task Summary

When a user asks the orchestrator to terminate an agent early and close a project, the current `force=true` close path is destructive: it sets agents to "decommissioned" without draining their lifecycle (messages, TODOs, status). This leaves the project in an unrecoverable state where `can_close_project` says "closeable" but the project was never properly marked `completed`.

This handover implements: (A) a smart early termination protocol, (B) a new "skipped" status for audit trail, and (C) a Jobs dashboard column reduction from 9 to 5 columns.

---

## Context and Background

### What Happened (Alpha Test - 2026-02-26)

Project "fred showcase alpha test" (ID: 628f54bf) had 6 specialist agents + orchestrator. One agent (`marathon-implementer`) was running a 15-minute sleep test. User asked the orchestrator to end early and close the project. The orchestrator called `close_project_and_update_memory(force=true)` which:

1. Decommissioned 2 active agents (set status to "decommissioned")
2. Wrote a product memory entry
3. **Did NOT** mark the project as `completed` (that's `_complete_project_transaction()`'s job)
4. **Did NOT** mark unread messages as read
5. **Did NOT** handle incomplete TODO items
6. **Did NOT** call `complete_job()` for the affected agents

Result: `project.status = "active"`, `project.completed_at = null`. The "Close Project" button is gated on `can_close_project` which returns `true` (no active agents), but the project is stuck in limbo.

### Root Cause

The orchestrator had no protocol for handling early termination. It didn't know how to:
- Take over a cancelled agent's identity to drain its lifecycle
- Mark TODO items as skipped (not completed - for audit trail)
- Mark messages as read with a prefix indicating they were skipped
- Properly complete the agent before closing the project

### Design Decisions Made

All decisions below were discussed and approved by the user:

1. **No new MCP tool** - Too risky for ad-hoc misuse. Instead, make `force=true` smart.
2. **"skipped" status** for `AgentTodoItem` - Not "completed" (audit trail matters).
3. **Message prefix** `[SKIPPED - early termination]` for messages marked read during force close.
4. **Orchestrator protocol injection** - Add early termination protocol to both CLI and multi-terminal orchestrator instructions (CH5 of `_build_orchestrator_protocol`).
5. **Dashboard reduction** - Remove 4 columns from Jobs table (Agent ID, Job Acknowledged, Messages Sent, Messages Read). Keep: Agent Name, Agent Status, Duration, Steps, Messages Waiting + action icons.
6. **Steps notation** - Show `completed(skipped)/total` format, e.g., `5(1)/6`. Parentheses signal "aside/qualifier" (not contribution like `+` would). Skipped count in orange/red.

---

## Technical Details

### Phase 1: Database Schema - Add "skipped" to AgentTodoItem

**File:** `src/giljo_mcp/models/agent_identity.py` (line 374)

Current constraint:
```python
CheckConstraint(
    "status IN ('pending', 'in_progress', 'completed')",
    name="ck_agent_todo_item_status",
)
```

Change to:
```python
CheckConstraint(
    "status IN ('pending', 'in_progress', 'completed', 'skipped')",
    name="ck_agent_todo_item_status",
)
```

Also update the column comment at line 352 to include `skipped`.

**Migration:** Create a new Alembic migration file in `migrations/versions/`. Follow the idempotent pattern from `b8d2f3a4e567_0491_agent_status_simplification.py`:

```python
def upgrade() -> None:
    conn = op.get_bind()
    if _constraint_exists(conn, "ck_agent_todo_item_status"):
        op.drop_constraint("ck_agent_todo_item_status", "agent_todo_items", type_="check")
    op.create_check_constraint(
        "ck_agent_todo_item_status",
        "agent_todo_items",
        "status IN ('pending', 'in_progress', 'completed', 'skipped')",
    )
```

The `down_revision` must chain from the latest migration: `a1b2c3d4e567` (0497b). This covers both fresh installs (`install.py` runs `alembic upgrade head`) and upgrades.

### Phase 2: Smart Force Close in `_force_decommission_agents`

**File:** `src/giljo_mcp/tools/project_closeout.py` (lines 275-307)

Current behavior: Simply sets `execution.status = "decommissioned"` for all active executions. Does NOT touch TODOs or messages.

New behavior (replace `_force_decommission_agents`):

1. For each active execution:
   a. **Mark pending/in_progress TODO items as "skipped"** - Query `AgentTodoItem` by `job_id` where status in (`pending`, `in_progress`), set status to `skipped`.
   b. **Mark unread messages as read with prefix** - Query `Message` table where `project_id` matches, `to_agents` contains this agent's ID, `acknowledged_by` is NULL. Set `acknowledged_by` to the agent's ID, `acknowledged_at` to now, and prepend `[SKIPPED - early termination] ` to `content` (or `subject` if content is empty).
   c. **Set execution.status to "decommissioned"** (existing behavior).

Key models to query (add imports as needed):
- `AgentTodoItem` (agent_identity.py line 309) - filter by `job_id`, status in active states
- `Message` (tasks.py line 118) - filter by `project_id`, `to_agents` contains agent_id, `acknowledged_by IS NULL`
- `AgentExecution` (agent_identity.py line 148) - the execution being decommissioned

### Phase 3: Apply same smart drain to `ProjectService.close_out_project`

**File:** `src/giljo_mcp/services/project_service.py` (lines 848-939)

The `close_out_project` method is the UI-facing "Close Out Project" button handler. It already sets `project.status = "completed"` and `project.completed_at`, but its decommission loop (lines 907-928) has the **same destructive pattern** as `_force_decommission_agents` -- it just sets `execution.status = "decommissioned"` without draining TODOs/messages.

Apply the same smart drain logic from Phase 2 to this decommission loop. Consider extracting a shared `_drain_agent_lifecycle()` helper to avoid code duplication between the two call sites.

The MCP tool `close_project_and_update_memory` (project_closeout.py line 31) does NOT set project status. It only writes memory and decommissions. The orchestrator should NOT be calling this directly for early termination. Instead:

- Add early termination protocol to orchestrator instructions (Phase 4)
- The orchestrator should use `complete_job()` for each agent after draining lifecycle
- Then call `write_360_memory()` and `complete_job()` for itself
- Then the user clicks "Close Out Project" in the UI

### Phase 4: Orchestrator Protocol - Early Termination Instructions

**File:** `src/giljo_mcp/services/orchestration_service.py` (function `_build_orchestrator_protocol`, line ~889)

Add to CH5 (Implementation Phase Reference) a new section **before** the COMPLETION PROTOCOL (which starts at line ~937):

```
── EARLY TERMINATION PROTOCOL ─────────────────────────────────────────────
If the user requests early termination of one or more agents:

1. For each agent to terminate:
   a. Call report_progress(job_id=AGENT_JOB_ID,
          status_update="Early termination requested by user")
   b. Mark remaining TODO items as skipped:
      Call report_progress(job_id=AGENT_JOB_ID,
          todo_updates=[{sequence: N, status: "skipped"} for each pending item])
   c. Read and acknowledge any unread messages for the agent
   d. Call complete_job(job_id=AGENT_JOB_ID,
          result={"summary": "Early termination by user request",
                  "status": "terminated_early"})

2. After all agents are terminated, proceed to COMPLETION PROTOCOL above.

CRITICAL: Do NOT call close_project_and_update_memory(force=true).
          Follow this protocol step by step instead.
```

This applies to both CLI mode and multi-terminal mode. For multi-terminal mode, add equivalent guidance noting that the orchestrator should send messages to active agents asking them to gracefully terminate, then follow the protocol above for any that don't respond.

Also add to `template_seeder.py` `_get_orchestrator_messaging_protocol_section()` (line 902) so the seeded orchestrator template includes this protocol.

### Phase 5: `report_progress` - Support "skipped" TODO status

**File:** `src/giljo_mcp/services/orchestration_service.py` (method `OrchestrationService.report_progress`, lines 2175-2441)

The TODO status validation is at line ~2383:
```python
if status not in ("pending", "in_progress", "completed"):
    status = "pending"
```

Add `"skipped"` to the allowed status set:
```python
if status not in ("pending", "in_progress", "completed", "skipped"):
    status = "pending"
```

**ALSO:** Update the MCP tool schema enum in `api/endpoints/mcp_http.py` line 562:
```python
# Current:
"status": {"type": "string", "enum": ["pending", "in_progress", "completed"]},
# Change to:
"status": {"type": "string", "enum": ["pending", "in_progress", "completed", "skipped"]},
```

Without this schema change, the MCP layer will reject "skipped" status before it reaches the service.

### Phase 6: Add skipped count to steps API response

**Backend steps aggregation** lives in `orchestration_service.py` lines 2959-2981 (inside `_list_jobs_by_project`). Currently builds:
```python
steps_summary = {"total": total_steps, "completed": completed_steps}
```

Two paths need updating:

**Path A - From job_metadata (line 2972):** Add skipped count. Note: `todo_steps` in metadata currently only stores `total_steps` and `completed_steps`. Add `skipped_steps` to the metadata dict in the `report_progress` method (line ~2326) and read it back here.

**Path B - Fallback from todo_items (line 2977-2981):**
```python
if not steps_summary and job.todo_items:
    total = len(job.todo_items)
    completed = sum(1 for item in job.todo_items if item.status == "completed")
    skipped = sum(1 for item in job.todo_items if item.status == "skipped")
    if total > 0:
        steps_summary = {"total": total, "completed": completed, "skipped": skipped}
```

**Frontend store** `frontend/src/stores/agentJobsStore.js` lines 286-305 also builds `steps` from WebSocket `todo_steps` payloads. Both the array format (line 289) and object format (line 298) handlers need to count skipped items and pass `steps.skipped` to the UI. Without this, real-time WebSocket updates won't show skipped counts.

### Phase 7: Frontend - Dashboard Column Reduction

**File:** `frontend/src/components/projects/JobsTab.vue`

Remove columns (currently lines 27-34 in `<thead>`):
- Column 2: `Agent ID` (line 27, redundant with Agent Name)
- Column 5: `Job Acknowledged` (line 30, internal lifecycle detail)
- Column 7: `Messages Sent` (line 32, low value, visible in message modal)
- Column 9: `Messages Read` (line 34, low value, visible in message modal)

Keep columns (5 total):
1. `Agent Name` (with play button + avatar)
2. `Agent Status`
3. `Duration`
4. `Steps`
5. `Messages` (rename from "Messages waiting")
6. Action icons column (existing, no header)

Also remove the corresponding `<td>` cells in the `<tbody>` row template.

### Phase 8: Frontend - Steps Column Skipped Notation

**File:** `frontend/src/components/projects/JobsTab.vue`

Current steps display (line 189): `{{ agent.steps.completed }} / {{ agent.steps.total }}`

New display logic:
```html
{{ agent.steps.completed }}<span v-if="agent.steps.skipped" class="steps-skipped">({{ agent.steps.skipped }})</span> / {{ agent.steps.total }}
```

With CSS:
```css
.steps-skipped {
  color: #e65100;  /* orange-red for visibility */
  font-size: 0.85em;
}
```

---

## Key Files Reference

| File | Lines | What |
|------|-------|------|
| `src/giljo_mcp/models/agent_identity.py` | 309-387 | AgentTodoItem model, constraint at 374 |
| `src/giljo_mcp/models/agent_identity.py` | 148-288 | AgentExecution model |
| `src/giljo_mcp/models/tasks.py` | 118-162 | Message model |
| `src/giljo_mcp/tools/project_closeout.py` | 275-307 | `_force_decommission_agents` (main target) |
| `src/giljo_mcp/tools/project_closeout.py` | 231-272 | `_check_agent_readiness` |
| `src/giljo_mcp/tools/project_closeout.py` | 31+ | `close_project_and_update_memory` MCP tool |
| `src/giljo_mcp/services/project_service.py` | 848-939 | `close_out_project` (UI close button) |
| `src/giljo_mcp/services/project_service.py` | 703-788 | `_complete_project_transaction` |
| `src/giljo_mcp/services/project_service.py` | 1584-1703 | `can_close_project` + `_build_can_close_response` |
| `src/giljo_mcp/services/orchestration_service.py` | 577-986 | `_build_orchestrator_protocol` (CH1-CH5) |
| `src/giljo_mcp/services/orchestration_service.py` | 2175-2441 | `report_progress` (TODO status validation at ~2383) |
| `src/giljo_mcp/services/orchestration_service.py` | 2959-2981 | Steps aggregation in `_list_jobs_by_project` |
| `src/giljo_mcp/template_seeder.py` | 902+ | `_get_orchestrator_messaging_protocol_section` |
| `api/endpoints/mcp_http.py` | 548-569 | `report_progress` MCP schema (enum at 562) |
| `frontend/src/components/projects/JobsTab.vue` | 24-36 | Table headers (9 columns) |
| `frontend/src/components/projects/JobsTab.vue` | 180-192 | Steps cell rendering |
| `frontend/src/stores/agentJobsStore.js` | 286-305 | WebSocket → steps object transform |
| `migrations/versions/b8d2f3a4e567_*` | all | Reference migration pattern (0491) |
| `migrations/versions/a1b2c3d4e567_*` | all | Latest migration (chain `down_revision` from this) |

---

## Implementation Plan

### Step 1: Schema + Migration (Phase 1)
- Add "skipped" to `AgentTodoItem` CheckConstraint in model
- Create Alembic migration in `migrations/versions/` (chain from `a1b2c3d4e567`)
- Test: Verify constraint allows "skipped" status

### Step 2: Smart Force Decommission (Phases 2+3)
- Refactor `_force_decommission_agents` to drain lifecycle before decommissioning
- Apply same logic to `ProjectService.close_out_project` decommission loop
- Consider shared `_drain_agent_lifecycle()` helper
- Test: Force close marks TODOs as "skipped", messages as read with prefix

### Step 3: report_progress + MCP Schema (Phase 5)
- Add `"skipped"` to allowed status set in `orchestration_service.py` line ~2383
- Add `"skipped"` to MCP schema enum in `mcp_http.py` line 562
- Test: Orchestrator can mark TODO items as "skipped" via report_progress MCP tool

### Step 4: Steps Aggregation Backend (Phase 6)
- Add `skipped` count to `steps_summary` dict in `orchestration_service.py` lines 2959-2981
- Add `skipped_steps` to `todo_steps` metadata in `report_progress` (line ~2326)
- Update `agentJobsStore.js` (lines 286-305) to count skipped items from WebSocket
- Test: Steps API response includes skipped count via both REST and WebSocket

### Step 5: Orchestrator Protocol (Phase 4)
- Add Early Termination Protocol section to `_build_orchestrator_protocol` CH5
- Add equivalent to `_get_orchestrator_messaging_protocol_section` in template_seeder
- Test: Protocol text appears in get_orchestrator_instructions response

### Step 6: Frontend Column Reduction (Phase 7)
- Remove 4 columns from JobsTab.vue (Agent ID, Job Acknowledged, Messages Sent, Messages Read)
- Remove corresponding `<td>` cells
- Rename "Messages waiting" to "Messages"
- Test: Table renders with 5 columns + action icons

### Step 7: Frontend Steps Notation (Phase 8)
- Display `completed(skipped)/total` in Steps cell
- Style skipped count in orange (#e65100)
- Test: Steps show skipped notation when applicable

---

## Testing Requirements

### Unit Tests
- `AgentTodoItem` accepts "skipped" status (model + migration)
- `_force_decommission_agents` marks TODOs as skipped
- `_force_decommission_agents` marks messages as read with prefix
- `report_progress` allows skipped status via MCP tool
- Steps aggregation includes skipped count (both metadata and fallback paths)
- `agentJobsStore.js` transforms skipped count from WebSocket payload

### Integration Tests
- Full force-close flow: active agents -> lifecycle drained -> decommissioned
- Orchestrator early termination: agent TODOs skipped -> agent completed -> project closeable
- API: `can_close_project` returns correct status after early termination

### Manual Tests
- Dashboard shows 5 columns (not 9)
- Steps cell shows `5(1)/6` notation when items skipped
- Skipped count appears in orange
- "Close Out Project" button works after early termination

---

## Cascading Impact Analysis

**Downstream:** Adding "skipped" to AgentTodoItem does not affect child entities (none exist below TODO items). The constraint change is additive - existing "pending", "in_progress", "completed" statuses remain valid.

**Upstream:** No impact on Product, Project, or Job layers. The TODO status is a leaf property.

**Sibling:** Other agents in the same project are unaffected. Force close only touches the targeted agent's TODOs and messages.

**Installation:** Alembic migration handles both fresh installs (`install.py` runs `alembic upgrade head`) and upgrades. The `_constraint_exists()` + `drop_constraint()` + `create_check_constraint()` pattern is idempotent.

**MCP Layer:** The `report_progress` MCP tool schema enum in `mcp_http.py` must be updated alongside the backend validation. No new MCP tools are needed -- all changes work through existing tools.

---

## Dependencies and Blockers

**Dependencies:** None. This is self-contained within the existing agent lifecycle system.

**Blockers:** None identified.

**Related handovers:**
- 0497a-e (Multi-Terminal Production Parity) - The protocol injection in Phase 4 extends the work in 0497c
- 0411a (Phase Labels) - The column reduction may interact with proposed phase column

---

## Success Criteria

1. Force-closing a project with active agents drains their lifecycle (TODOs skipped, messages read with prefix) before decommissioning
2. Orchestrator protocol includes early termination instructions for both CLI and multi-terminal modes
3. Jobs dashboard shows 5 columns instead of 9
4. Steps column shows `completed(skipped)/total` notation with orange skipped count
5. All existing tests continue to pass
6. New regression tests cover the early termination flow

---

## Rollback Plan

1. **Schema:** Alembic downgrade reverses constraint. Any "skipped" items would need manual cleanup (UPDATE to "completed").
2. **Frontend:** Revert JobsTab.vue column changes (git revert).
3. **Protocol:** Remove early termination section from orchestrator protocol (revert orchestration_service.py).
4. **MCP Schema:** Revert enum in mcp_http.py.
