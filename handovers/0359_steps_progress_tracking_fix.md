---
**Handover**: 0359 - Steps Column Progress Tracking Fix
**Type**: Full-Stack (Backend + Protocol + Frontend)
**Effort**: 3-4 hours
**Priority**: P1 (Critical - Blocking Alpha Trial)
**Status**: Ready
**Complexity**: Low
**Category**: Bug Fix / Agent Protocol
**Tool**: CLI (for backend, protocol changes, and testing)
**Issue**: #5 (Steps column always shows 0/0)
---

# Handover 0359: Steps Column Progress Tracking Fix

## Executive Summary

Alpha trial revealed **Steps column in Jobs table always shows 0/0**, preventing users from monitoring agent progress. Root cause: Protocol mismatch between agent instructions and backend implementation.

**What's Broken**:
- Protocol instructs: `report_progress(progress={"steps_completed": Y, "steps_total": Z})`
- Backend expects: `report_progress(progress={"mode": "todo", "completed_steps": Y, "total_steps": Z})`
- Result: Agents call tool correctly per protocol, but backend doesn't recognize the format

**Impact**:
- Users cannot see agent task progress (0/0 displayed for all jobs)
- TodoWrite tracking disconnected from UI visibility
- Agent progress invisible to orchestrator and users

**Fix Strategy**:
Update protocol to match backend implementation (simpler than changing backend + tests).

---

## Context

### What We're Fixing

**Issue #5**: Steps column always shows 0/0 in Jobs table
- Reported in alpha trial feedback
- Prevents visibility into agent task completion
- Breaks TodoWrite → UI pipeline

### System Architecture (Current)

**Backend Flow** (Handover 0297 - Working):
```python
# src/giljo_mcp/services/orchestration_service.py:994-1022
async def report_progress(job_id, progress, tenant_key):
    mode = progress.get("mode")
    if mode == "todo":
        total_steps = progress.get("total_steps")
        completed_steps = progress.get("completed_steps")
        current_step = progress.get("current_step")

        if isinstance(total_steps, int) and isinstance(completed_steps, int):
            # Persist to job_metadata.todo_steps
            metadata["todo_steps"] = {
                "total_steps": total_steps,
                "completed_steps": completed_steps,
            }
```

**Frontend Transformation** (Handover 0297 - Working):
```python
# src/giljo_mcp/services/orchestration_service.py:1323-1339
async def list_jobs():
    # Extract from job_metadata.todo_steps
    todo_steps = metadata.get("todo_steps") or {}
    total_steps = todo_steps.get("total_steps")
    completed_steps = todo_steps.get("completed_steps")

    # Transform to frontend format
    steps_summary = {
        "total": total_steps,
        "completed": completed_steps,
    }
```

**Frontend Display** (Handover 0243c - Working):
```vue
<!-- frontend/src/components/projects/JobsTab.vue:77-88 -->
<td class="steps-cell text-center">
  <button v-if="agent.steps && typeof agent.steps.completed === 'number' && typeof agent.steps.total === 'number'">
    {{ agent.steps.completed }} / {{ agent.steps.total }}
  </button>
  <span v-else>—</span>
</td>
```

**Agent Protocol** (Handover 0359 - BROKEN):
```python
# src/giljo_mcp/services/orchestration_service.py:191
### Phase 3: PROGRESS REPORTING (After each milestone)
1. Call `mcp__giljo-mcp__report_progress(
     job_id="{job_id}",
     progress={
       "percent": X,
       "message": "current task",
       "steps_completed": Y,   # ❌ Wrong field name
       "steps_total": Z         # ❌ Wrong field name
     }
   )`
```

---

## Problem Statement

### Root Cause Analysis

**Protocol vs Implementation Mismatch**:

| Component | Field Name | Value |
|-----------|------------|-------|
| Protocol (line 191) | `steps_completed` | Integer (completed count) |
| Protocol (line 191) | `steps_total` | Integer (total count) |
| Backend expects | `completed_steps` | Integer (completed count) |
| Backend expects | `total_steps` | Integer (total count) |
| Backend expects | `mode` | String (`"todo"`) |

**Why It Fails**:
1. Agent follows protocol: `progress={"steps_completed": 3, "steps_total": 5}`
2. Backend checks: `mode = progress.get("mode")` → Returns `None`
3. Backend skips: `if mode == "todo"` block never executes
4. Result: `job_metadata.todo_steps` never populated
5. Frontend gets: `steps: None` (displays as `—`)

**Evidence from Code**:

```python
# src/giljo_mcp/services/orchestration_service.py:994-1006
mode = progress.get("mode")  # ❌ Protocol doesn't include "mode"
if mode == "todo":           # ❌ Condition never true
    total_steps = progress.get("total_steps")     # ✅ Correct field name
    completed_steps = progress.get("completed_steps")  # ✅ Correct field name
    # ... persist to job_metadata.todo_steps
```

### Why Protocol Needs Fixing (Not Backend)

**Option 1: Fix Protocol** ✅ (This handover)
- Changes: 1 line (protocol string)
- Risk: Low (protocol already broken, no agents using it correctly)
- Tests: Update 1 test (protocol assertion)
- Documentation: Clear agent contract

**Option 2: Fix Backend** ❌ (Rejected)
- Changes: 5+ files (orchestration_service.py, tests, docs)
- Risk: Medium (breaks existing tests, need migration for field names)
- Tests: Update 8+ tests (report_progress, list_jobs, integration)
- Complexity: Higher (backward compatibility concerns)

**Decision**: Fix protocol to match backend (Handover 0297 already validated backend).

---

## Investigation Findings

### Code Inspection Results

**1. Backend Implementation** (`src/giljo_mcp/services/orchestration_service.py:994-1022`):
- ✅ Correctly stores to `job_metadata.todo_steps`
- ✅ Validates `total_steps` and `completed_steps` as integers
- ✅ Handles `current_step` as optional string
- ❌ Requires `mode: "todo"` to trigger (protocol omits this)

**2. Frontend Transformation** (`src/giljo_mcp/services/orchestration_service.py:1323-1339`):
- ✅ Correctly extracts from `job_metadata.todo_steps`
- ✅ Transforms to `{"total": int, "completed": int}` format
- ✅ Returns `None` when `todo_steps` missing (displays as `—`)

**3. Frontend Display** (`frontend/src/components/projects/JobsTab.vue:77-88`):
- ✅ Correctly checks for nested `agent.steps.completed` and `agent.steps.total`
- ✅ Displays `{{ agent.steps.completed }} / {{ agent.steps.total }}`
- ✅ Shows `—` when steps data unavailable

**4. Existing Tests** (All passing ✅):
- `tests/api/test_agent_jobs_api.py:522-576` - Tests `todo_steps` backend persistence
- `tests/services/test_orchestration_service_context.py:89-131` - Tests mode="todo" format
- Backend → Frontend pipeline validated in Handover 0297

**Gap**: Protocol doesn't instruct agents to use correct format.

---

## Implementation Plan

### Step 1: Update Agent Protocol String

**File**: `src/giljo_mcp/services/orchestration_service.py`

**Location**: Line 191 (function `_generate_agent_protocol()`)

**Change**:
```python
# BEFORE (Handover 0359 - BROKEN):
### Phase 3: PROGRESS REPORTING (After each milestone)
1. Call `mcp__giljo-mcp__report_progress(
     job_id="{job_id}",
     progress={{
       "percent": X,
       "message": "current task",
       "steps_completed": Y,
       "steps_total": Z
     }}
   )`

# AFTER (This handover - FIXED):
### Phase 3: PROGRESS REPORTING (After each milestone)
1. Call `mcp__giljo-mcp__report_progress(
     job_id="{job_id}",
     progress={{
       "mode": "todo",
       "completed_steps": Y,
       "total_steps": Z,
       "current_step": "task description",
       "percent": X
     }}
   )`
2. Optional: Include "message" for legacy compatibility
```

**Why This Works**:
- Matches backend expectation: `mode = progress.get("mode")` → `"todo"`
- Uses correct field names: `completed_steps`, `total_steps`
- Triggers persistence: `if mode == "todo"` block executes
- Result: `job_metadata.todo_steps` populated → Frontend displays correctly

**Additional Context in Protocol**:
Add note explaining fields:
```markdown
**Progress Fields**:
- `mode: "todo"` - REQUIRED to trigger steps tracking
- `completed_steps: int` - Number of tasks completed (e.g., 3)
- `total_steps: int` - Total number of tasks (e.g., 5)
- `current_step: str` - OPTIONAL description of current task
- `percent: int` - OPTIONAL overall completion percentage (0-100)
- `message: str` - OPTIONAL status message (legacy field)
```

### Step 2: Update Protocol Documentation

**File**: Add comment in `_generate_agent_protocol()` docstring

**Addition**:
```python
"""
Generate the 5-phase agent lifecycle protocol (Handover 0334, 0359).

Handover 0359: Fixed progress reporting format to match backend:
- Added mode="todo" to trigger steps tracking
- Changed steps_completed/steps_total → completed_steps/total_steps
- This enables Steps column in Jobs table to display progress
"""
```

### Step 3: Update Tests (If Any Assert Protocol String)

**File**: `tests/unit/test_thin_prompt_generator_execution_mode.py` (if relevant)

**Potential Update**:
```python
# Update any test that asserts protocol string contains "steps_completed"
# Change to expect "completed_steps" and "mode": "todo"
```

**Note**: Based on grep results, protocol tests are mostly skipped (Handover 0333 simplified staging).
Verify with:
```bash
grep -r "steps_completed" tests/
```

### Step 4: Verification Testing

**Manual Test**:
1. Launch project with orchestrator
2. Spawn agent (via orchestrator)
3. Agent calls `report_progress(progress={"mode": "todo", "completed_steps": 2, "total_steps": 5})`
4. Check database: `SELECT job_metadata FROM mcp_agent_jobs WHERE job_id = '...'`
5. Verify: `job_metadata.todo_steps = {"total_steps": 5, "completed_steps": 2}`
6. Refresh Jobs table in UI
7. Verify: Steps column shows `2 / 5`

**Integration Test**:
```python
# tests/integration/test_agent_steps_tracking.py
async def test_agent_progress_updates_steps_column():
    """
    End-to-end test: Agent reports progress → Steps column updates.

    Flow:
    1. Spawn agent job
    2. Call report_progress with mode="todo"
    3. Verify job_metadata.todo_steps populated
    4. Call list_jobs endpoint
    5. Verify response includes steps: {total: 5, completed: 2}
    """
    # Implementation details in Testing Strategy below
```

---

## Files to Modify

### Backend Changes

**1. `src/giljo_mcp/services/orchestration_service.py`**
- **Function**: `_generate_agent_protocol()` (line 153-211)
- **Change**: Update Phase 3 protocol string (line 191)
- **Impact**: All agents spawned after this change will receive correct instructions
- **Testing**: Verify protocol string contains `"mode": "todo"`, `completed_steps`, `total_steps`

**Estimated Changes**:
- Lines modified: ~10 (protocol string + docstring)
- Lines added: ~5 (additional documentation)
- Risk: Low (existing backend implementation unchanged)

### Test Updates (Minimal)

**2. `tests/unit/test_thin_prompt_generator_execution_mode.py`** (if relevant)
- **Function**: Any test asserting protocol string format
- **Change**: Update assertions to expect new field names
- **Note**: Most protocol tests skipped per Handover 0333

**Estimated Changes**:
- Lines modified: 0-5 (only if tests assert protocol string)
- Risk: Low (protocol tests mostly skipped)

### Documentation Updates (Optional)

**3. `docs/agent-templates/*.md`** (if agent templates exist)
- **Change**: Update progress reporting examples in templates
- **Impact**: Ensures template documentation matches protocol
- **Priority**: P2 (can defer to separate handover)

---

## Testing Strategy

### Unit Tests

**Test 1: Protocol String Contains Correct Format** ✅
```python
# tests/services/test_orchestration_service_protocol.py
@pytest.mark.asyncio
async def test_agent_protocol_includes_mode_todo():
    """Verify protocol instructs agents to include mode='todo' in progress."""
    from src.giljo_mcp.services.orchestration_service import _generate_agent_protocol

    protocol = _generate_agent_protocol(
        job_id="job-123",
        tenant_key="tenant-abc",
        agent_name="tdd-implementor"
    )

    # Verify protocol contains correct progress format
    assert '"mode": "todo"' in protocol
    assert '"completed_steps"' in protocol
    assert '"total_steps"' in protocol
    assert '"current_step"' in protocol

    # Verify old incorrect format removed
    assert '"steps_completed"' not in protocol
    assert '"steps_total"' not in protocol
```

**Test 2: Backend Accepts New Format** ✅ (Already passing)
```python
# tests/services/test_orchestration_service_context.py:89-131
# This test already validates backend accepts mode="todo" format
# No changes needed - confirms fix works
```

### Integration Tests

**Test 3: End-to-End Steps Tracking** 🆕
```python
# tests/integration/test_agent_steps_tracking.py
@pytest.mark.asyncio
async def test_agent_progress_updates_steps_column_e2e(
    api_client, tenant_a_admin_token, tenant_a_project, db_manager
):
    """
    End-to-end test: Agent reports progress → Steps column updates.

    Validates:
    1. report_progress with mode="todo" persists to job_metadata.todo_steps
    2. list_jobs endpoint transforms todo_steps to frontend format
    3. Frontend receives steps: {total: int, completed: int}
    """
    # Step 1: Create agent job
    response = await api_client.post(
        f"/api/projects/{tenant_a_project['project_id']}/orchestrate",
        headers={"Cookie": f"access_token={tenant_a_admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    job_id = data["orchestrator_job_id"]

    # Step 2: Agent reports progress with mode="todo"
    progress_response = await api_client.post(
        f"/api/agent-jobs/{job_id}/progress",
        headers={"Cookie": f"access_token={tenant_a_admin_token}"},
        json={
            "progress": {
                "mode": "todo",
                "completed_steps": 3,
                "total_steps": 7,
                "current_step": "Implementing feature X",
                "percent": 43
            }
        }
    )
    assert progress_response.status_code == 200

    # Step 3: Verify database persistence
    async with db_manager.get_session_async() as session:
        result = await session.execute(
            select(MCPAgentJob).where(MCPAgentJob.job_id == job_id)
        )
        job = result.scalar_one()

        assert job.job_metadata is not None
        assert "todo_steps" in job.job_metadata
        steps = job.job_metadata["todo_steps"]
        assert steps["total_steps"] == 7
        assert steps["completed_steps"] == 3
        assert steps["current_step"] == "Implementing feature X"

    # Step 4: Verify list_jobs transformation
    jobs_response = await api_client.get(
        "/api/agent-jobs/",
        headers={"Cookie": f"access_token={tenant_a_admin_token}"},
    )
    assert jobs_response.status_code == 200
    jobs_data = jobs_response.json()

    job = next((j for j in jobs_data["jobs"] if j["job_id"] == job_id), None)
    assert job is not None
    assert "steps" in job
    assert job["steps"] == {"total": 7, "completed": 3}
```

### Manual Verification

**Scenario 1: Alpha Trial Reproduction** 🧪
```bash
# 1. Start server
python startup.py

# 2. Login and create project
# 3. Launch project (spawns orchestrator)
# 4. Orchestrator spawns implementer agent
# 5. Implementer calls get_agent_mission() → receives full_protocol
# 6. Implementer follows protocol: report_progress(progress={"mode": "todo", ...})
# 7. Check Jobs table: Steps column should show "3 / 7" (not "0 / 0")
```

**Database Verification** 🔍
```sql
-- Check job_metadata.todo_steps directly
SELECT
  job_id,
  agent_type,
  status,
  job_metadata->'todo_steps' as steps
FROM mcp_agent_jobs
WHERE tenant_key = 'tenant-abc'
ORDER BY created_at DESC;

-- Expected result:
-- | job_id | agent_type | status  | steps                                                    |
-- |--------|-----------|---------|----------------------------------------------------------|
-- | abc123 | implementer| working | {"total_steps": 7, "completed_steps": 3, "current_step": "..."} |
```

**WebSocket Event Verification** 📡
```javascript
// Browser console (on Jobs tab)
// 1. Open Network tab → Filter: WS
// 2. Trigger agent progress update
// 3. Verify WebSocket message contains:
{
  "type": "job:progress_update",
  "data": {
    "job_id": "abc123",
    "steps": {"total": 7, "completed": 3}
  }
}
```

---

## Success Criteria

### Functional Requirements

**✅ Protocol Correctness**:
- [ ] `_generate_agent_protocol()` includes `"mode": "todo"` in Phase 3
- [ ] Protocol uses `completed_steps` (not `steps_completed`)
- [ ] Protocol uses `total_steps` (not `steps_total`)
- [ ] Protocol includes `current_step` as optional field
- [ ] Protocol docstring updated with Handover 0359 reference

**✅ Backend Integration**:
- [ ] `report_progress()` with new format persists to `job_metadata.todo_steps`
- [ ] `list_jobs()` transforms `todo_steps` to `steps: {total, completed}`
- [ ] No regressions in existing `report_progress` tests

**✅ Frontend Display**:
- [ ] Jobs table Steps column displays `3 / 7` (not `0 / 0` or `—`)
- [ ] Steps column updates in real-time via WebSocket
- [ ] Tooltip shows `current_step` when hovering over steps count

### Non-Functional Requirements

**✅ Performance**:
- [ ] No additional database queries (uses existing `list_jobs` query)
- [ ] WebSocket events <100ms latency (same as existing events)

**✅ Backward Compatibility**:
- [ ] Agents without `mode: "todo"` still work (no steps displayed, graceful fallback)
- [ ] Legacy `progress: {percent: X, message: Y}` format still accepted (no steps tracking)
- [ ] Existing orchestrator jobs unaffected (protocol change applies to new jobs only)

**✅ Testing**:
- [ ] All existing tests pass (no regressions)
- [ ] New protocol unit test passes
- [ ] E2E integration test passes
- [ ] Manual alpha trial scenario verified

---

## Rollback Plan

**If Fix Causes Issues**:

1. **Immediate Rollback** (1 minute):
   ```bash
   git revert <commit-hash>
   python startup.py --restart
   ```

2. **Revert Protocol String** (manual):
   ```python
   # src/giljo_mcp/services/orchestration_service.py:191
   # Change back to:
   progress={{"percent": X, "steps_completed": Y, "steps_total": Z}}
   # Remove: "mode": "todo", completed_steps, total_steps
   ```

3. **Verify Rollback**:
   ```bash
   pytest tests/services/test_orchestration_service_context.py -v
   # If tests fail: Backend expects mode="todo", protocol omits it
   # Result: Same broken state as before (Steps = 0/0)
   ```

**Rollback Impact**:
- Steps column returns to `0 / 0` (broken state)
- No data corruption (job_metadata unchanged)
- No API breakage (backward compatible)

**Alternative Fix (If Protocol Fix Fails)**:
- Revert protocol change
- Update backend to accept both formats:
  ```python
  # Accept mode="todo" OR steps_completed/steps_total
  if mode == "todo" or "steps_completed" in progress:
      total = progress.get("total_steps") or progress.get("steps_total")
      completed = progress.get("completed_steps") or progress.get("steps_completed")
  ```
- Requires more extensive testing (deferred to 0360 if needed)

---

## Dependencies

**Blockers**: None (this handover is self-contained)

**Related Handovers**:
- **0297** - UI Message Status and Job Signaling (introduced `todo_steps` backend)
- **0334** - HTTP-Only MCP Consolidation (introduced `full_protocol` field)
- **0353** - Agent Team Awareness (updated `get_agent_mission()` response format)

**Follow-Up Handovers** (Optional):
- **0360** - Agent Template Progress Examples (update template docs to match protocol)
- **0361** - Steps UI Enhancements (add current_step tooltip, progress bar)

---

## Notes

### Why This Wasn't Caught Earlier

**Timeline**:
1. **Handover 0297** (Nov 2025): Backend implemented `mode="todo"` format
2. **Handover 0334** (Nov 2025): Protocol added to `get_agent_mission()` response
3. **Handover 0359** (This handover): Protocol format mismatch discovered in alpha trial

**Gap**: Protocol string (line 191) was copy-pasted from earlier vision doc that predated 0297 backend changes. No integration test validated protocol → backend → frontend pipeline.

### Lessons Learned

**Prevention Strategies**:
1. **Integration Tests**: Always test full protocol → backend → frontend flow
2. **Protocol Validation**: Add unit test that parses protocol and validates field names
3. **Documentation**: Keep protocol docstring in sync with backend implementation
4. **Alpha Testing**: Caught in alpha trial (good safety net)

### Future Improvements

**Auto-Validation** (Deferred to 0370):
- Add `validate_protocol_format()` helper that parses protocol string
- Extract expected MCP tool signatures from protocol
- Compare against actual MCP tool parameter names
- Fail CI if mismatch detected

**Example**:
```python
def validate_protocol_format():
    protocol = _generate_agent_protocol("job-id", "tenant", "agent")

    # Extract report_progress signature from protocol
    match = re.search(r'report_progress\(.*?progress=\{(.*?)\}\)', protocol)
    fields = extract_fields(match.group(1))

    # Validate against backend
    assert "mode" in fields, "Protocol missing mode='todo'"
    assert "completed_steps" in fields, "Protocol uses wrong field name"
    assert "total_steps" in fields, "Protocol uses wrong field name"
```

---

## Implementation Checklist

- [ ] Update `_generate_agent_protocol()` Phase 3 string (line 191)
- [ ] Update function docstring with Handover 0359 note
- [ ] Add protocol validation unit test
- [ ] Add E2E integration test (agent → backend → frontend)
- [ ] Run existing test suite (verify no regressions)
- [ ] Manual test: Spawn agent, report progress, verify Steps column
- [ ] Database verification: Check `job_metadata.todo_steps` persisted
- [ ] WebSocket verification: Check `job:progress_update` event format
- [ ] Update CLAUDE.md with Handover 0359 reference
- [ ] Alpha trial re-test: Verify Steps column now shows correct counts

---

## Execution Notes

**Estimated Timeline**:
- Protocol update: 30 minutes
- Unit test: 30 minutes
- Integration test: 1 hour
- Manual verification: 1 hour
- Documentation: 30 minutes
- **Total**: 3-4 hours

**Tool**: CLI (backend changes, testing, database verification)

**Deployment**:
- No database migration needed
- No API version bump needed
- Hot reload: Restart server for protocol change to take effect

**Risk**: Low
- Protocol already broken (no agents using it correctly)
- Backend implementation unchanged (Handover 0297 validated)
- Frontend implementation unchanged (Handover 0243c validated)
- Fix is single-line string change (easy to review/revert)

---

## ⚠️ DEVELOPER DISCUSSION REQUIRED

**Before implementing this handover, discuss the following with the developer:**

### Options to Review

1. **Fix Location**
   - Option A: Fix protocol string only (proposed - single line change)
   - Option B: Also fix backend to accept both formats
   - Option C: Add transformation layer to normalize either format
   - **Trade-offs**: Simplicity vs robustness vs backward compatibility

2. **Step Reporting Granularity**
   - Option A: Report after each TodoWrite update (current protocol)
   - Option B: Report only at phase boundaries
   - Option C: Automatic tracking from TodoWrite (no manual reporting)
   - **Trade-offs**: Visibility vs token usage vs agent burden

3. **Frontend Display Format**
   - Current: "3/5" format
   - Alternative: Progress bar visualization
   - Alternative: "60% complete" percentage display

### Questions for Developer

- [ ] Is the single-line protocol fix acceptable, or do you want a more robust solution?
- [ ] Should agents report steps for every task or only significant milestones?
- [ ] Would you like the Steps column to be more prominent in the UI?

### Alpha Trial Reference

Review agent feedback for real-world context:
- Dashboard Steps column showed 0/0 throughout both agent executions
- Agents DID call report_progress but with wrong format
- `F:\TinyContacts\analyzer_feedback.md` - Lines 117-119 (Progress Reporting)

### Session Context

This handover originated from the **Alpha Trial Remediation Session** (2025-12-19).
See: `handovers/alpha_trial_remediation_roadmap.md` for full context and prioritization rationale.

---

**End of Handover 0359**
