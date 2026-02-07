# Handover: Continuation Workflow Enhancements

**Date:** 2026-02-05
**From Agent:** Orchestrator (Claude Opus 4.5)
**To Agent:** Next Session / TDD Implementor
**Priority:** High
**Estimated Complexity:** 16-24 hours (5 implementation phases)
**Status:** Ready

---

## Task Summary

Enable seamless multi-phase project continuation by implementing job reactivation, mission versioning, todo list extension, and duration timer resumption. Currently, when an orchestrator session ends, a new session cannot properly continue work under the same job context.

**Why it matters:** Continuation sessions currently fragment project history across multiple jobs, lose mission context, and cannot extend progress tracking.

**Expected outcome:** True multi-phase workflows where users can continue, extend, and iterate on completed work without losing context.

---

## Context and Background

**Origin:** Testing the GiljoAI MCP server's continuation/handover workflow (2026-02-05/06 sessions in TinyContacts project trial)

**Key Discovery:** 360 Memory correctly APPENDS (sequence numbers increment), but job lifecycle and mission management have gaps that prevent smooth continuation.

**Test Results Summary:**
| Capability | Current Behavior | Expected |
|------------|-----------------|----------|
| 360 Memory | Appends correctly | Working |
| Mission update | Overwrites completely | Version/Append |
| Job reactivation | Not possible | Reopen completed jobs |
| Todo list | Overwrites completely | Append mode |
| Duration timer | Stops at completion | Resume on reopen |
| `set_agent_status()` | EXISTS (proposal was incorrect) | N/A |

---

## Technical Details

### Issue 1: Job Reactivation (P0 - Critical)

**Current State:**
- Once `AgentJob.status = "completed"`, no MCP tool can transition it back
- `acknowledge_job()`, `report_error()` return "No active execution found"
- All tools filter with: `AgentExecution.status.not_in(["complete", "failed", "cancelled", "decommissioned"])`

**Files to Modify:**

1. **`src/giljo_mcp/services/agent_job_manager.py`** (after line 428)
   - Add `reopen_job()` method to reset AgentJob status

2. **`src/giljo_mcp/services/orchestration_service.py`** (after line 1896)
   - Add `reopen_job()` wrapper with validation and WebSocket emission

3. **`src/giljo_mcp/tools/job_reopen.py`** (NEW FILE)
   - MCP tool: `mcp__giljo-mcp__reopen_job(job_id, tenant_key, reason)`

4. **`api/endpoints/agent_jobs/lifecycle.py`** (after line 241)
   - Add `POST /agent-jobs/{job_id}/reopen` endpoint

5. **`api/endpoints/mcp_http.py`**
   - Add tool schema and handler routing

**Implementation Strategy:**
- Create NEW AgentExecution record (preserves succession chain)
- Reset `AgentJob.status` from `completed` → `active`
- Clear `AgentJob.completed_at` to NULL
- Preserve all existing progress/message history
- Emit WebSocket event for UI update

---

### Issue 2: Mission Versioning (P1 - High)

**Current State:**
- `update_project_mission()` performs complete OVERWRITE (`project_service.py:461-548`)
- No `ProjectMissionHistory` table or versioning exists
- Multi-phase projects lose previous mission context

**Files to Modify:**

**Option B (Recommended): Mission History Table**

1. **`src/giljo_mcp/models/project_mission_history.py`** (NEW FILE)
   ```python
   class ProjectMissionHistory(Base):
       __tablename__ = "project_mission_history"
       id, tenant_key, project_id, version, phase_name
       mission, author_job_id, change_type, created_at
   ```

2. **`src/giljo_mcp/services/project_service.py`** (line 461)
   - Modify `update_project_mission()` to write history before update
   - Add `mode` parameter: "replace" (default) | "append"

3. **`src/giljo_mcp/tools/mission_history.py`** (NEW FILE)
   - MCP tool: `get_mission_history(project_id, tenant_key, version=None)`

4. **Database migration** for `project_mission_history` table

**Alternative (Option A - Minimal):**
- Add `mode` parameter only, append to existing mission text
- Pros: No migration needed
- Cons: No structured history, difficult to query phases

---

### Issue 3: Todo List Extension (P2 - Medium)

**Current State:**
- `report_progress()` DELETE-ALL-THEN-INSERT (`orchestration_service.py:1584-1604`)
- Storage: `AgentTodoItem` table with FK to agent_jobs
- Cannot extend todo list during continuation

**Files to Modify:**

1. **`api/endpoints/mcp_http.py`** (lines 406-429)
   - Add `todo_mode` parameter: "replace" (default) | "append" | "merge"

2. **`src/giljo_mcp/tools/tool_accessor.py`** (lines 656-673)
   - Add `todo_mode` parameter passthrough

3. **`src/giljo_mcp/services/orchestration_service.py`** (lines 1578-1604)
   - Branch logic based on mode:
     - `replace`: Current behavior
     - `append`: Skip delete, insert with `sequence = max(existing) + 1`
     - `merge`: Match by content, update status if found, append if not

---

### Issue 4: Duration Timer Reactivation (P2 - Medium)

**Current State:**
- Frontend calculates: `completed_at - started_at` (`JobsTab.vue:559-604`)
- No `paused_duration` tracking
- Timer stops permanently at completion

**Files to Modify:**

1. **`src/giljo_mcp/models/agent_identity.py`** (AgentJob model)
   - Add: `paused_duration_seconds = Column(Integer, default=0)`

2. **`src/giljo_mcp/services/agent_job_manager.py`**
   - On `complete_job()`: Calculate and store elapsed duration
   - On `reopen_job()`: Preserve paused_duration for cumulative tracking

3. **`frontend/src/components/projects/JobsTab.vue`** (lines 690-721)
   - `formatDuration()`: Add `paused_duration_seconds` to calculation

4. **Database migration** for new column

---

### Issue 5: set_agent_status() Clarification (NO ACTION NEEDED)

**Finding:** The tool EXISTS at `src/giljo_mcp/tools/agent_status.py:54-222`

The proposal was incorrect - the tool exists but enforces terminal state restrictions:
```python
TERMINAL_STATES = {"failed", "cancelled", "decommissioned"}
# Note: "complete" is NOT in TERMINAL_STATES
```

The real issue is the active execution filter pattern, not missing tool.

---

## Implementation Plan

### Phase 1: Job Reactivation (P0) - 6-8 hours
**Recommended Agent:** TDD Implementor

1. Write tests for `reopen_job()` behavior
2. Add `AgentJobManager.reopen_job()` method
3. Add `OrchestrationService.reopen_job()` wrapper
4. Create MCP tool in `src/giljo_mcp/tools/job_reopen.py`
5. Add API endpoint `POST /agent-jobs/{job_id}/reopen`
6. Add MCP schema and handler routing
7. Test: Reopen completed job, verify new execution created

### Phase 2: Mission Versioning (P1) - 4-6 hours
**Recommended Agent:** Database Expert + TDD Implementor

1. Create `ProjectMissionHistory` model
2. Write database migration
3. Modify `update_project_mission()` to save history
4. Add `mode` parameter support
5. Create `get_mission_history()` MCP tool
6. Test: Update mission in append mode, query history

### Phase 3: Todo List Extension (P2) - 2-3 hours
**Recommended Agent:** TDD Implementor

1. Add `todo_mode` parameter to MCP schema
2. Modify `report_progress()` logic with mode branching
3. Test: Append items without overwriting

### Phase 4: Duration Timer (P2) - 2-3 hours
**Recommended Agent:** TDD Implementor

1. Add `paused_duration_seconds` column
2. Write migration
3. Update `complete_job()` to store duration
4. Update `reopen_job()` to preserve duration
5. Update frontend `formatDuration()`
6. Test: Complete, reopen, verify cumulative duration

### Phase 5: Integration Testing - 2-4 hours
**Recommended Agent:** Backend Integration Tester

1. Full multi-phase scenario test:
   - Stage and complete Phase 1
   - Trigger session handover
   - Start fresh with continuation prompt
   - Verify 360 Memory readable
   - Reopen job
   - Verify duration resumes
   - Update mission with append
   - Add new todo items
   - Complete Phase 2
   - Verify dashboard shows both phases

---

## Testing Requirements

### Unit Tests
- `test_reopen_job_creates_new_execution()`
- `test_reopen_job_resets_status_to_active()`
- `test_reopen_job_preserves_messages()`
- `test_mission_history_created_on_update()`
- `test_mission_append_mode()`
- `test_todo_append_mode()`
- `test_duration_cumulative_after_reopen()`

### Integration Tests
- E2E multi-phase continuation scenario
- WebSocket event verification for reopened jobs
- Dashboard UI updates correctly

### Manual Testing
1. Complete a project
2. Call `reopen_job()` via MCP
3. Verify job shows "active" in dashboard
4. Verify duration timer resumes
5. Add new todo items via append mode
6. Complete again
7. Verify cumulative duration accurate

---

## Dependencies and Blockers

**Dependencies:**
- Database migration capability (already exists via install.py)
- Frontend build pipeline
- MCP tool registration pattern

**Known Blockers:** None identified

**Questions for User:**
1. Should `reopen_job()` require admin privileges or allow any orchestrator?
2. Should mission history have a retention limit (e.g., keep last 10 versions)?
3. Should reopening a job notify original orchestrator via message?

---

## Success Criteria

- [ ] `reopen_job()` MCP tool creates new execution for completed jobs
- [ ] Mission updates preserve history with version tracking
- [ ] Todo list supports append mode without overwriting
- [ ] Duration timer shows cumulative time across reopens
- [ ] Dashboard correctly reflects multi-phase job history
- [ ] All existing tests pass
- [ ] New tests achieve >80% coverage for changed code

---

## Rollback Plan

**If deployment fails:**
1. Database: Migration includes `IF NOT EXISTS` guards
2. Backend: Feature-flagged via `mode` parameters (default = current behavior)
3. Frontend: Graceful degradation (shows 0 if `paused_duration_seconds` missing)

**Revert command:** Standard git revert of feature commits

---

## Additional Resources

**Original Proposal:** `F:\TinyContacts\PROPOSAL_Continuation_Workflow_Enhancements.md`

**Related Handovers:**
- 0460-0463: Agent ID Swap & Ghost Agent Fixes (succession patterns)
- 0390: 360 Memory Normalization (append-only patterns)
- 0461: Simplify Handover (360 Memory approach)

**Key File References:**
| File | Lines | Purpose |
|------|-------|---------|
| `orchestration_service.py` | 1411-1681 | `report_progress()` |
| `orchestration_service.py` | 1683-1896 | `complete_job()` |
| `project_service.py` | 461-548 | `update_project_mission()` |
| `agent_identity.py` | 37-127 | AgentJob model |
| `agent_identity.py` | 321-399 | AgentTodoItem model |
| `agent_status.py` | 54-222 | `set_agent_status()` (EXISTS) |
| `JobsTab.vue` | 559-604, 690-721 | Duration timer |

---

## Continuation Prompt Template (Updated)

Once implemented, update the continuation prompt in proposal with:

```markdown
## IF JOB IS COMPLETED

1. **Reopen the job:**
   mcp__giljo-mcp__reopen_job(
       job_id="{job_id}",
       reason="Continuing with Phase 2 requirements"
   )
   → Creates new execution, resets status to active, preserves history

2. **Update mission (append mode):**
   mcp__giljo-mcp__update_project_mission(
       project_id="{project_id}",
       mission="## Phase 2: [New Title]\n[New requirements]",
       mode="append"
   )
   → Previous mission preserved in history

3. **Add new tasks:**
   mcp__giljo-mcp__report_progress(
       job_id="{job_id}",
       todo_items=[{"content": "New task", "status": "pending"}],
       todo_mode="append"
   )
   → Existing tasks preserved, new tasks added
```

---

**Note:** This handover supersedes the original proposal document. Implementation should follow TDD approach per handover instructions.
