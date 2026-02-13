# Handover: Agent Status Simplification & Silent Detection

**Date:** 2026-02-11
**From Agent:** Claude Code Session (workflow status fix session)
**To Agent:** Next Session (orchestrator-coordinator + tdd-implementor + deep-researcher)
**Priority:** HIGH
**Estimated Complexity:** 12-18h across 3-4 phases
**Status:** Not Started

---

## Task Summary

Simplify the agent status model from 7 statuses to 4 agent-reported + 1 server-detected + 1 lifecycle. Remove `failed` and `cancelled` statuses entirely. Add server-side `Silent` detection for agents that stop communicating. Repurpose existing staleness WebSocket infrastructure.

**Why:** Alpha trial revealed agents waste tokens reporting failure states. Most "failures" are either blockages (need help) or crashes (agent goes silent). The `cancelled` status is orphaned since the cancel button was removed from UI. Simpler status model = fewer protocol instructions = fewer tokens per agent.

---

## Context and Background

### Current Status Model (7 statuses)
```
AgentExecution.status CHECK constraint:
  'waiting', 'working', 'blocked', 'complete', 'failed', 'cancelled', 'decommissioned'
```

### Proposed Status Model
```
Agent-reported:  waiting -> working -> blocked -> complete
Server-detected: silent (10-min inactivity on "working" agents)
Lifecycle:       decommissioned (project complete or cancelled by user)
```

### What led to this decision
- Commit `5d010ddd`: Added `severity` param to `report_error()` (blocked vs failed)
- Commit `54d783e1`: Fixed workflow status counting (blocked/cancelled gaps)
- Commit `8fbf8bf2`: Widened `failure_reason` VARCHAR(50) -> TEXT
- Commit `154cc455`: Added `caller_note` to workflow status for self-awareness
- Alpha trial conversation: orchestrator counted itself, blocked agents invisible, agents self-correcting around DB limits
- Design discussion: concluded `failed` has no unique use case vs `blocked` + `Silent`

### Key architectural decisions (already made)
1. `failed` removed completely (DB, model, service, protocol) - not deprecated, DELETED
2. `cancelled` removed completely - decommission covers all use cases
3. `Silent` is server-detected only, never agent-reported
4. Heartbeat interval: 10 minutes (global setting in admin settings page)
5. Any MCP call from an agent auto-clears `Silent` -> `working`
6. `report_error()` loses `severity` param - always sets `blocked`
7. User clicks `Silent` badge on dashboard -> returns to `working`

---

## CRITICAL: Research Phase Required

**Before ANY implementation, the executing agent MUST run a deep-researcher subagent to validate:**

1. **All references to `failed` status** across the entire codebase (Python, Vue, JS, SQL, tests)
   - Service methods that set `status = "failed"`
   - Frontend components that check for / display "failed"
   - Tests that assert on "failed" status
   - SQL queries / CHECK constraints mentioning "failed"
   - MCP tool descriptions referencing "failed"

2. **All references to `cancelled` status** - same scope as above

3. **All references to `failure_reason` column** - determine if it can be removed or should be merged with `block_reason`

4. **Existing staleness/heartbeat infrastructure** - what exists in:
   - `frontend/src/composables/useStalenessMonitor.js`
   - WebSocket events related to agent health
   - `health_status` / `health_failure_count` columns on AgentExecution
   - Settings page notification sections

5. **`last_progress_at` column** - confirm it exists, is indexed, and is updated on MCP calls

**IF the researcher finds `failed` or `cancelled` statuses are used in contexts beyond what this handover anticipates (e.g., tied to billing, external integrations, or security logic not documented here), STOP and ask the user for guidance before proceeding.**

---

## Technical Details

### Files to Modify

**Database Model:**
- `src/giljo_mcp/models/agent_identity.py` - AgentExecution CHECK constraint, remove `failure_reason` column (merge into `block_reason`)
- `migrations/versions/baseline_v32_unified.py` - Update baseline for fresh installs

**Service Layer:**
- `src/giljo_mcp/services/orchestration_service.py`:
  - `report_error()` - remove `severity` param, always set `blocked`, use `block_reason` only
  - `get_workflow_status()` - remove `failed_count`, `cancelled_count` (replace with just `blocked_count`)
  - Any method that sets `status = "failed"` or `status = "cancelled"`
- `src/giljo_mcp/schemas/service_responses.py` - WorkflowStatus: remove `failed_agents`, `cancelled_agents`

**MCP Layer:**
- `api/endpoints/mcp_http.py` - MCP schema: remove `severity` from `report_error`, update `get_workflow_status` description
- `src/giljo_mcp/tools/tool_accessor.py` - Remove severity passthrough
- `api/endpoints/mcp_tools.py` - Update tool metadata docs

**API Layer:**
- `api/endpoints/agent_jobs/models.py` - WorkflowStatusResponse: remove `failed_count`, `cancelled_count`
- `api/endpoints/agent_jobs/orchestration.py` - Update mapping

**Background Task (NEW):**
- `src/giljo_mcp/services/silence_detector.py` (new file) - Periodic scan for silent agents
- `api/app.py` or `api/lifespan.py` - Register background task on startup

**Frontend:**
- `frontend/src/composables/useStalenessMonitor.js` - Repurpose for Silent detection display
- `frontend/src/utils/statusConfig.js` - Add `silent` status config, remove `failed`/`cancelled`
- Settings page component - Add heartbeat interval setting
- Dashboard components - Silent badge, notification bell filtering

**Live Database Migration:**
```sql
-- Update any 'failed' executions to 'blocked'
UPDATE agent_executions SET status = 'blocked', block_reason = COALESCE(failure_reason, block_reason) WHERE status = 'failed';
-- Update any 'cancelled' executions to 'decommissioned'
UPDATE agent_executions SET status = 'decommissioned' WHERE status = 'cancelled';
-- Add 'silent' to CHECK constraint, remove 'failed' and 'cancelled'
ALTER TABLE agent_executions DROP CONSTRAINT ck_agent_execution_status;
ALTER TABLE agent_executions ADD CONSTRAINT ck_agent_execution_status
  CHECK (status IN ('waiting', 'working', 'blocked', 'complete', 'silent', 'decommissioned'));
-- Drop failure_reason column (merged into block_reason)
ALTER TABLE agent_executions DROP COLUMN IF EXISTS failure_reason;
```

### Settings Model
- Add `agent_silence_threshold_minutes` to system settings (default: 10)
- Expose via existing Settings API and frontend settings page

### Silent Detection Background Task
```python
# Pseudocode - runs every 60 seconds
async def detect_silent_agents():
    threshold = await get_setting("agent_silence_threshold_minutes", default=10)
    silent_agents = await session.execute(
        select(AgentExecution)
        .where(
            AgentExecution.status == "working",
            AgentExecution.last_progress_at < now() - interval(threshold minutes),
        )
    )
    for agent in silent_agents:
        agent.status = "silent"
        emit_websocket("agent:status_changed", {agent_id, status: "silent"})
```

### MCP Handler Auto-Clear
```python
# In mcp_http.py handle_tools_call(), after successful tool execution:
# If we can identify the calling agent's job_id from arguments, auto-clear silent
job_id = arguments.get("job_id")
if job_id:
    await auto_clear_silent(job_id)  # Sets status back to "working" if currently "silent"
```

---

## Implementation Plan

### Phase 1: Research & Validation (deep-researcher)
- Run codebase-wide search for `failed`, `cancelled`, `failure_reason` usage
- Map all references and categorize: removable vs needs migration vs unexpected usage
- Validate `last_progress_at` column exists and is updated
- Document existing staleness infrastructure
- **If conflicts found: STOP and ask user**
- **Output:** Research report with green/red/yellow status per removal target

### Phase 2: Backend Status Cleanup (tdd-implementor)
- Remove `failed` and `cancelled` from CHECK constraint
- Remove `failure_reason` column, merge data into `block_reason`
- Simplify `report_error()` - remove severity, always -> blocked
- Update `get_workflow_status()` - remove failed/cancelled counts
- Add `silent` to CHECK constraint
- Update baseline migration
- Write migration SQL for live DB
- TDD: Update all affected tests

### Phase 3: Silent Detection (tdd-implementor)
- Create `silence_detector.py` background service
- Register in app lifespan
- Add `agent_silence_threshold_minutes` setting
- MCP handler auto-clear logic (job_id based)
- User click-to-clear REST endpoint
- TDD: Unit tests for detection, auto-clear, threshold

### Phase 4: Frontend (ux-designer + frontend-tester)
- Update `statusConfig.js` - add silent (amber?), remove failed/cancelled
- Repurpose `useStalenessMonitor.js` for silent display
- Settings page: heartbeat interval input
- Notification bell: only ring for active working->silent transitions
- Dashboard: Silent badge, click-to-clear interaction
- Test: Component tests, WebSocket event handling

---

## Testing Requirements

**Unit Tests:**
- `report_error()` always sets blocked (no severity)
- `get_workflow_status()` returns no failed/cancelled counts
- Silent detection fires at threshold
- MCP call auto-clears silent -> working
- User clear endpoint works

**Integration Tests:**
- Full lifecycle: working -> silent (timeout) -> MCP call -> working -> complete
- Concurrent agents: some silent, some working, counts correct
- Settings change: threshold update takes effect on next scan cycle

---

## Dependencies and Blockers

**Dependencies:**
- Commits from this session must be on master (54d783e1, 8fbf8bf2, 154cc455)
- Research phase must complete before implementation

**Known Blockers:**
- None - all architectural decisions made

---

## Success Criteria

1. `failed` and `cancelled` statuses completely removed from codebase (0 references)
2. `failure_reason` column removed, `block_reason` is the single error description column
3. `report_error()` has no severity parameter
4. Silent detection works with configurable threshold
5. Dashboard shows Silent badge, notification bell rings for silent agents
6. All existing tests updated, all new tests passing
7. No orphaned code, no deprecated markers - clean removal

---

## Completion Summary

**Completed**: 2026-02-13
**Effort**: ~68 minutes wall-clock (estimated: 12-18h) - parallelized across 4 subagents
**Status**: Complete
**Commits**: 0a1d89fe, 25037291, 6d018c63, 5c48a901, 5d5dda99

### What Was Delivered

**Phase 1: Research & Validation** (deep-researcher)
- Scanned 100+ references across 31 production files, ~50 test files
- Safety check: GREEN - no billing, security, or external integration usage
- Identified 4 distinct `cancelled` domains (only AgentExecution removed)

**Phase 2: Backend Status Cleanup** (tdd-implementor, 400 tool calls)
- CHECK constraint: `('waiting','working','blocked','complete','silent','decommissioned')`
- `failure_reason` column removed, merged into `block_reason`
- `report_error()` severity parameter removed - always sets `blocked`
- `get_workflow_status()` failed/cancelled counts removed, silent/decommissioned added
- 27 production files + 28 test files modified
- Alembic migration `b8d2f3a4e567` with idempotent upgrade/downgrade

**Phase 3: Silent Detection** (tdd-implementor, 155 tool calls)
- `src/giljo_mcp/services/silence_detector.py` - Background service (60s scan interval)
- `api/startup/silence_detector.py` - App lifespan registration
- `auto_clear_silent()` - MCP call resets silent -> working
- `clear_silent_status()` - REST endpoint for dashboard click-to-clear
- `agent_silence_threshold_minutes` setting (default 10, range 1-60)
- 21 tests passing (detection, auto-clear, lifecycle, integration)

**Phase 4: Frontend** (ux-designer, 82 tool calls)
- statusConfig.js: `failed`/`cancelled` removed, `silent` added (amber #ff9800)
- AgentCard.vue: Silent badge with click-to-clear, failure_reason display removed
- StatusChip.vue, useAgentData.js, agentJobsStore.js, useStalenessMonitor.js updated
- websocketEventRouter.js: `agent:auto_failed` replaced with `agent:silent`
- UserSettings.vue: Agent Monitoring section with threshold input

### Success Criteria Verification
- 1. `failed`/`cancelled` removed: 0 references in agent execution context (verified via grep)
- 2. `failure_reason` removed: 0 references in production code
- 3. `report_error()` severity removed: only appears in a comment documenting the change
- 4. Silent detection: SilenceDetector service with configurable threshold, 21 tests passing
- 5. Dashboard: Silent badge (amber), click-to-clear, notification on working->silent
- 6. Tests: 28 test files updated, 21 new tests, all passing
- 7. Clean removal: no orphaned code, no deprecated markers, no stubs

### Domain Separation (Critical)
Files deliberately NOT modified (different domains using "failed"/"cancelled"):
- `workflow_engine.py` - WorkflowResult status
- `download_tokens.py` - staging_status
- `configuration.py` - config update failures
- `statistics.py` - message delivery status
- AgentJob CHECK constraint (`active`, `completed`, `cancelled`) - kept
- Project/Task cancelled status - kept
- Message delivery failed status - kept

### Lessons Learned
- Domain separation was the highest-risk aspect - `cancelled` exists in 4 separate domains
- Parallelizing Phase 3 + Phase 4 after Phase 2 saved significant time
- The existing `useStalenessMonitor.js` with 10-min threshold was a perfect foundation
- `last_progress_at` column was already indexed and reliably updated - no schema changes needed

### Follow-Up Items
- None - all scope items delivered
