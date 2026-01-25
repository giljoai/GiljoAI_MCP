# Handover 0460: Agent ID Swap Succession Implementation

**Date**: 2025-01-24
**Session Duration**: ~3 hours
**Status**: IMPLEMENTED & TESTED
**Commits**: `824fe2ae`, `d3dbb4d0`, `7f3e0251`

---

## Executive Summary

This session implemented **PROPOSAL 2: Agent ID Swap on Handover** to fix orchestrator succession issues where multiple execution instances with the same `agent_id` caused multi-row query errors and UI display problems.

**Key Change**: On succession, the OLD orchestrator gets a decommissioned ID (`decomm-xxx`), and the NEW orchestrator TAKES OVER the original `agent_id`. This ensures only ONE execution owns an active `agent_id` at any time.

---

## Problem Statement

After triggering orchestrator succession multiple times, three issues were identified:

| Issue | Root Cause | Resolution |
|-------|------------|------------|
| Messages endpoint 500 error | Multiple rows returned when querying by `agent_id` | Agent ID Swap eliminates multi-row issue |
| Duplicate agents in UI | Frontend store using inconsistent keys | Fixed `upsertJob` to search existing jobs first |
| All agents show same mission | By design (Handover 0429) | No fix needed - mission is on AgentJob |

---

## Implementation Details

### Commit 1: `824fe2ae` - Agent ID Swap Core Logic

**Files Modified:**

#### 1. `src/giljo_mcp/orchestrator_succession.py`
- **Method**: `OrchestratorSuccessionManager.create_successor()`
- **Change**: Implemented Agent ID Swap logic

**Before:**
```python
# Old orchestrator kept same agent_id, marked complete
successor_execution = AgentExecution(
    agent_id=current_execution.agent_id,  # SAME agent_id
    ...
)
current_execution.status = "complete"
```

**After:**
```python
# Step 1: Preserve original agent_id
original_agent_id = current_execution.agent_id

# Step 2: Generate decommissioned ID for OLD orchestrator
decomm_id = f"decomm-{original_agent_id[:8]}-{uuid4().hex[:8]}"

# Step 3: Update OLD orchestrator with decommissioned ID
current_execution.agent_id = decomm_id  # Swap to decommissioned ID
current_execution.status = "decommissioned"

# Step 4: Create NEW orchestrator that TAKES OVER original agent_id
successor_execution = AgentExecution(
    agent_id=original_agent_id,  # TAKE OVER original
    spawned_by=decomm_id,  # Points to decommissioned predecessor
    ...
)
```

#### 2. `src/giljo_mcp/services/orchestration_service.py`
- **Method**: `trigger_succession()` (lines ~2095-2115)
- **Change**: Added `decommissioned_agent_id` to return dict and logging

```python
# After refresh
decommissioned_agent_id = execution.agent_id  # Now decomm-xxx

return {
    "success": True,
    "job_id": execution.job_id,
    "successor_agent_id": successor_execution.agent_id,  # Original ID
    "decommissioned_agent_id": decommissioned_agent_id,  # New field
    ...
}
```

#### 3. `src/giljo_mcp/models/schemas.py`
- **Class**: `SuccessionResponse`
- **Change**: Added `decommissioned_agent_id` field

```python
class SuccessionResponse(BaseModel):
    current_agent_id: str  # Now the decommissioned ID after swap
    decommissioned_agent_id: Optional[str]  # Explicit field for clarity
    successor_agent_id: str  # Takes over original ID
    ...
```

#### 4. `api/endpoints/agent_jobs/succession.py`
- **Endpoint**: `POST /{job_id}/trigger-succession`
- **Changes**:
  - Extract `decommissioned_agent_id` from service result
  - Include in API response
  - Include in WebSocket event `orchestrator:succession_triggered`

#### 5. `frontend/src/utils/statusConfig.js`
- Added `decommissioned` status to both config objects:

```javascript
// JobsTab-specific config
decommissioned: {
  label: 'Decommissioned',
  color: '#757575',  // Dark grey
  italic: false,
  chipColor: 'default',
}

// Legacy STATUS_CONFIG
decommissioned: {
  icon: 'mdi-archive',
  color: 'grey-darken-1',
  label: 'Decommissioned',
  description: 'Agent has been decommissioned',
}
```

#### 6. `frontend/src/components/StatusBoard/StatusChip.vue`
- Added `handed_over` to status validator (was missing)

#### 7. `tests/services/test_orchestration_service_dual_model.py`
- Updated 3 succession tests for Agent ID Swap behavior:
  - `test_succession_creates_new_execution_same_job`
  - `test_succession_sets_succeeded_by_on_predecessor`
  - `test_succession_sets_spawned_by_on_successor`

**Test assertions changed from:**
```python
# Old: agent_id preserved across instances
assert new_agent_id == initial_agent_id
exec_count_stmt = select(AgentExecution).where(AgentExecution.agent_id == initial_agent_id)
assert len(executions) == 2  # Two instances with same agent_id
```

**To:**
```python
# New: Agent ID Swap - check for decommissioned ID
assert decommissioned_agent_id.startswith("decomm-")
exec_count_stmt = select(AgentExecution).where(AgentExecution.job_id == initial_job_id)
assert len(executions) == 2  # Two instances, different agent_ids
assert initial_agent_id in agent_ids  # Successor has original
assert decommissioned_agent_id in agent_ids  # Predecessor has decomm
```

---

### Commit 2: `d3dbb4d0` - Frontend Succession Instance Support

**Files Modified:**

#### 1. `api/endpoints/agent_jobs/models.py`
- Added to `JobResponse`:
  - `execution_id: Optional[str]` - Unique per row (AgentExecution PK)
  - `instance_number: int = 1` - Succession instance number

#### 2. `api/endpoints/agent_jobs/status.py`
- Updated `job_to_response()` to include new fields

#### 3. `frontend/src/services/api.js`
- Added `getExecutions(jobId)` endpoint for fetching succession history

#### 4. `frontend/src/stores/agentJobsStore.js`
- Changed Map key from `job_id` to `unique_key`
- `unique_key = execution_id || job_id-instance_number`
- Updated `normalizeJob()`, `setJobs()`, `upsertJob()`, `getJob()`

#### 5. `frontend/src/components/projects/LaunchSuccessorDialog.vue`
- Added warning for existing waiting successors
- Fixed `nextInstanceNumber` calculation using max across all executions

---

### Commit 3: `7f3e0251` - Fix Duplicate Agent Entries Bug

**Problem Discovered During Testing:**
After staging a project, the UI showed 6 agents instead of 3:
- ORCHESTRATOR, API-TESTER, CRUD-IMPLEMENTER (correct)
- Three "??" entries with partial IDs (duplicates)

**Root Cause:**
The `upsertJob` function computed a new `unique_key` for each update without checking if the job already existed under a different key. WebSocket events use `agent_id` while API responses use `job_id`, causing duplicates.

**Fix in `frontend/src/stores/agentJobsStore.js`:**

```javascript
function upsertJob(patch) {
  // CRITICAL FIX: Find existing job FIRST before computing unique_key
  let existingJob = null
  let existingKey = null

  // 1. Try execution_id (most specific)
  if (patch?.execution_id && jobsById.value.has(patch.execution_id)) {
    existingKey = patch.execution_id
    existingJob = jobsById.value.get(existingKey)
  }

  // 2. Try unique_key from patch
  if (!existingJob && patch?.unique_key && jobsById.value.has(patch.unique_key)) {
    existingKey = patch.unique_key
    existingJob = jobsById.value.get(existingKey)
  }

  // 3. Search by agent_id (executor UUID - used in WebSocket events)
  if (!existingJob && agentId) {
    for (const [key, job] of jobsById.value.entries()) {
      if (job.agent_id === agentId) {
        existingKey = key
        existingJob = job
        break
      }
    }
  }

  // 4. Search by job_id + instance_number (work order)
  if (!existingJob && jobId) {
    for (const [key, job] of jobsById.value.entries()) {
      if (job.job_id === jobId && job.instance_number === instanceNumber) {
        existingKey = key
        existingJob = job
        break
      }
    }
  }

  // Use existing key if found, otherwise compute new one
  const uniqueKey = existingKey || patch?.execution_id || ...

  // Rest of upsert logic using finalKey = existingKey || nextJob.unique_key
}
```

---

## Database Operations Performed

### Cleanup for Testing
Deleted extra orchestrator succession instances:
```sql
DELETE FROM agent_executions
WHERE job_id = 'f3085fb1-258d-4998-97bc-e603e0f026c6'
AND instance_number > 1;

UPDATE agent_executions
SET status = 'waiting',
    succeeded_by = NULL,
    succession_reason = NULL,
    completed_at = NULL,
    context_used = 0
WHERE job_id = 'f3085fb1-258d-4998-97bc-e603e0f026c6'
AND instance_number = 1;
```

---

## Test Results

### Unit Tests
```bash
pytest tests/services/test_orchestration_service_dual_model.py -v -k "succession" --no-cov
# 4 passed

pytest tests/services/test_orchestration_service_full.py -v -k "succession" --no-cov
# 2 passed

pytest tests/integration/test_orchestration_e2e.py -v --no-cov
# 6 passed, 1 skipped
```

### Manual Testing
User tested with project "0002b TC CRUD API":
1. Launched orchestrator (agent_id: ecf0a229...)
2. Orchestrator spawned 2 agents (api-tester, crud-implementer)
3. **Bug Found**: UI showed 6 agents instead of 3 (duplicates)
4. **Fix Applied**: Commit `7f3e0251`
5. **Pending**: Re-test after frontend restart

---

## Data Model: Before vs After

### Before Agent ID Swap (Handover 0429)
```
Succession creates:
  Row 1: agent_id=AAA, instance=1, status='complete'
  Row 2: agent_id=AAA, instance=2, status='waiting'

Problem: Queries by agent_id return MULTIPLE rows
```

### After Agent ID Swap (This Handover)
```
Succession swaps IDs:
  Row 1: agent_id=decomm-AAA-xxx, instance=1, status='decommissioned'
  Row 2: agent_id=AAA, instance=2, status='waiting'

Benefit: Queries by agent_id return ONE row
```

---

## Key Design Decisions

1. **Decommissioned ID Format**: `decomm-{first 8 chars}-{random 8 chars}`
   - Example: `decomm-d8c2f99f-26ea87c0`
   - Clearly identifies retired orchestrators
   - Preserves partial original ID for debugging

2. **Status Name**: `decommissioned` (not `retired` or `handed_over`)
   - Distinct from `handed_over` (used for different flow)
   - Implies permanent state change

3. **Frontend Store Keying Strategy**:
   - Primary: `execution_id` (database row ID)
   - Fallback: `job_id-instance_number` composite
   - Search existing jobs before creating new entries

---

## Files Changed Summary

| File | Lines | Change Type |
|------|-------|-------------|
| `src/giljo_mcp/orchestrator_succession.py` | +57/-35 | Core swap logic |
| `src/giljo_mcp/services/orchestration_service.py` | +32 | Return decommissioned_id |
| `src/giljo_mcp/models/schemas.py` | +11 | Schema field |
| `api/endpoints/agent_jobs/succession.py` | +89 | API response |
| `api/endpoints/agent_jobs/models.py` | +2 | execution_id, instance_number |
| `api/endpoints/agent_jobs/status.py` | +2 | job_to_response |
| `frontend/src/utils/statusConfig.js` | +7 | decommissioned status |
| `frontend/src/components/StatusBoard/StatusChip.vue` | +1 | validator |
| `frontend/src/stores/agentJobsStore.js` | +49/-6 | Duplicate fix |
| `frontend/src/components/projects/LaunchSuccessorDialog.vue` | +69 | Warning, instance calc |
| `frontend/src/services/api.js` | +2 | getExecutions endpoint |
| `tests/services/test_orchestration_service_dual_model.py` | +59/-35 | Test updates |

---

## Git History

```
7f3e0251 fix(store): Prevent duplicate agent entries in agentJobsStore
d3dbb4d0 fix(succession): Frontend support for multiple succession instances
824fe2ae feat(succession): Implement Agent ID Swap on handover
```

**Branch**: `master` (ahead of origin/master by 1 commit at session end)

---

## Remaining Work

1. **Re-test** after frontend restart to verify duplicate fix works
2. **Push** commits to origin when ready
3. **Monitor** for any edge cases with the Agent ID Swap in production

---

## Related Handovers

- **Handover 0429**: Original "preserve agent_id across instances" design (superseded by this)
- **Handover 0080**: Orchestrator succession lifecycle
- **Handover 0366b**: Dual-model architecture (AgentJob + AgentExecution)
- **Handover 0387**: Message counter architecture
- **Handover 0401**: WebSocket event matching with agent_id

---

## Session Notes

- User observed context compaction 3 times during session
- This handover document created to preserve full context
- All work done directly on `master` branch (user confirmed no divergence)
- Security tests have pre-existing failures (unrelated to this work)
