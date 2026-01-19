# Handover 0392: TODO Progress Simplification

**Status**: COMPLETE
**Date**: 2026-01-19
**Branch**: `TODO_simplification`
**Triggered By**: MCP Enhancement List item #12 (Progress object schema undefined)

---

## Context

During discussion of item #12, we discovered that the `report_progress()` MCP tool has redundant data:
- Agent sends BOTH `todo_items` array AND separate `completed_steps`/`total_steps` counts
- Frontend already calculates counts from the array (agentJobsStore.js lines 170-178)
- This creates confusion for agents and duplicates data

## Problem Statement

**Current State**: Agents must send complex progress objects with redundant fields:
```javascript
report_progress({
  job_id: "...",
  tenant_key: "...",
  progress: {
    mode: "todo",
    completed_steps: 2,    // Redundant
    total_steps: 5,        // Redundant
    current_step: "...",   // Redundant (derivable from in_progress item)
    percent: 40,           // Redundant (2/5 = 40%)
    todo_items: [
      { content: "Task A", status: "completed" },
      { content: "Task B", status: "completed" },
      { content: "Task C", status: "in_progress" },
      { content: "Task D", status: "pending" },
      { content: "Task E", status: "pending" }
    ]
  }
})
```

**Proposed State**: Agents send only `todo_items`:
```javascript
report_progress({
  job_id: "...",
  tenant_key: "...",
  todo_items: [
    { content: "Task A", status: "completed" },
    { content: "Task B", status: "completed" },
    { content: "Task C", status: "in_progress" },
    { content: "Task D", status: "pending" },
    { content: "Task E", status: "pending" }
  ]
})
```

Backend derives:
- `completed_steps` = count where status === "completed"
- `total_steps` = array length
- `current_step` = item where status === "in_progress"
- `percent` = (completed / total) * 100

## Implementation Plan

### Phase 1: Backend Changes

**File**: `src/giljo_mcp/services/orchestration_service.py`

1. Modify `report_progress()` method (lines 1240-1436):
   - Accept `todo_items` at top level (not nested in `progress`)
   - Calculate derived fields from `todo_items` if not explicitly provided
   - Maintain backwards compatibility with old format

2. Update validation:
   - If `todo_items` provided, derive other fields
   - If old format provided, still accept it (deprecation path)

### Phase 2: MCP Schema Update

**File**: `api/endpoints/mcp_http.py`

1. Update `report_progress` schema (lines 314-325):
   - Add `todo_items` as top-level property with proper schema
   - Mark `progress` object as deprecated
   - Update description to show simplified usage

### Phase 3: Protocol Update

**File**: `src/giljo_mcp/services/orchestration_service.py`

1. Update `_generate_agent_protocol()` (lines 186-338):
   - Simplify Phase 3 progress reporting instructions
   - Show new simplified format
   - Remove redundant field requirements

### Phase 4: Template Updates

**Files**:
- `src/giljo_mcp/template_seeder.py`
- `.claude/agents/*.md` (seeded templates)

1. Update check-in protocol section
2. Simplify report_progress examples
3. Remove references to redundant fields

### Phase 5: Frontend Verification

**File**: `frontend/src/stores/agentJobsStore.js`

1. Verify existing array handling works (lines 170-178)
2. Ensure WebSocket payload transformation handles new format
3. Test Steps column displays correctly

## Files to Modify

| File | Change |
|------|--------|
| `src/giljo_mcp/services/orchestration_service.py` | Backend report_progress + protocol |
| `api/endpoints/mcp_http.py` | MCP schema |
| `src/giljo_mcp/template_seeder.py` | Template check-in section |
| `frontend/src/stores/agentJobsStore.js` | Verify/update if needed |
| `frontend/src/stores/websocketEventRouter.js` | Verify payload handling |

## Backwards Compatibility

The old format will still work:
- If `progress.todo_items` exists, use it
- If `progress.completed_steps` exists without `todo_items`, use legacy path
- Log deprecation warning for old format

## Success Criteria

1. Agent can call `report_progress(job_id, tenant_key, todo_items=[...])` with just the array
2. Dashboard Steps column shows "2/5" correctly
3. Plan/TODOs tab shows task list correctly
4. Old format still works (backwards compat)
5. Protocol instructions are simplified

## Rollback

Branch `TODO_simplification` created before changes. To rollback:
```bash
git checkout master
git branch -D TODO_simplification
```

---

## Execution Log

### Phase 1: Backend ✅ COMPLETED (2026-01-18)
- [x] Modify report_progress() to accept top-level todo_items
  - Added `todo_items: list[dict] | None = None` parameter to method signature
  - Made `progress` parameter optional (`dict[str, Any] | None = None`)
- [x] Add derived field calculation
  - When `todo_items` provided at top level, automatically calculates:
    - `completed_steps`: count of items with status="completed"
    - `total_steps`: total array length
    - `current_step`: content of first in_progress item
    - `percent`: (completed_steps / total_steps) * 100
  - Builds progress dict internally for backwards compatibility with existing code paths
- [x] Add backwards compatibility
  - If `progress` dict provided (old format), uses it directly
  - If `progress.todo_items` exists, extracts it
  - If `todo_items` at top level, builds progress dict from it
  - All existing code paths continue to work
- [x] Add unit test
  - New test: `test_report_progress_top_level_todo_items`
  - Verifies simplified format works correctly
  - All 5 progress tests pass

### Phase 2: MCP Schema ✅ COMPLETED (2026-01-18)
- [x] Update inputSchema for report_progress
  - Added `todo_items` as top-level array property with full schema
  - Defined item structure: `content` (string) and `status` (enum: pending/in_progress/completed)
  - Moved `progress` from required to optional with deprecation notice
  - Updated description to emphasize simplified usage
- [x] Add deprecation notice
  - Marked `progress` object as "DEPRECATED: Use todo_items instead"
  - Updated tool description to "Simplified: just send todo_items array. Backend calculates percent/steps automatically."
  - Required parameters now only: job_id, tenant_key (todo_items optional but recommended)

### Phase 3: Protocol ✅ COMPLETED (2026-01-18)
- [x] Simplify _generate_agent_protocol()
  - Simplified Phase 3 progress reporting to show only `todo_items` array parameter
  - Removed complex nested format with mode/completed_steps/total_steps/percent
  - Added clear note: "Backend automatically calculates percent and step counts from your list"
  - Updated "CRITICAL: Sync TodoWrite" section to emphasize simplified approach
- [x] Update Phase 3 instructions
  - Reduced from 26 lines to 11 lines (58% reduction)
  - Removed redundant field instructions
  - Made agent's job much simpler
- [x] Update function docstring
  - Added Handover 0392 to changelog
  - Documented simplification rationale

### Phase 4: Templates ✅ COMPLETED (2026-01-19)
- [x] Update template_seeder.py
  - Updated `_get_check_in_protocol_section()` function (lines 886-922)
  - Added "Simplified Progress Reporting" section with code example
  - Shows new format: `report_progress(job_id, tenant_key, todo_items=[...])`
  - Emphasizes automatic calculation by backend: "Backend automatically calculates percent, step counts, and current step from your list"
  - Updated docstring with Handover 0392 reference
- [ ] Regenerate .claude/agents templates (deferred - requires template refresh command)

### Phase 5: Frontend Verification ✅ COMPLETED (2026-01-19)

**Summary**: Frontend already fully supports the simplified `todo_items` array format. No changes needed.

**Files Verified**:

1. **agentJobsStore.js** (lines 150-196) ✅
   - `handleProgressUpdate()` function already processes `todo_items` correctly
   - Lines 191-193: Extracts `todo_items` from payload when present
   - Lines 170-178: Calculates steps from array when `todo_items` provided
   - Logic: `completed = count(item.status == 'completed' or 'done')`, `total = array.length`
   - Stores both `todo_items` array AND calculated `steps` object for display

2. **websocketEventRouter.js** (lines 299-318) ✅
   - `job:progress_update` handler correctly passes `todo_items` to store
   - Line 310: Explicitly forwards `todo_items: payload.todo_items` to handler
   - Payload structure matches simplified format (todo_items at top level)

3. **MessageAuditModal.vue** (lines 100-131, 263-273) ✅
   - Plan/TODOs tab already displays `todo_items` array
   - Lines 264-267: Computed property extracts `todo_items` from agent object
   - Lines 116-130: Renders each item with status icon and content
   - Lines 346-368: Helper functions `getStatusIcon()` and `getStatusColor()` for visual feedback
   - Supports 3 statuses: pending, in_progress, completed

4. **JobsTab.vue** (lines 102-113, 763-775) ✅
   - Steps column displays `agent.steps.completed / agent.steps.total`
   - Line 108: Clickable trigger opens MessageAuditModal with Plan tab active
   - Steps calculated and stored by agentJobsStore.js (no changes needed)

**Verification Results**:

| Component | Feature | Status | Notes |
|-----------|---------|--------|-------|
| agentJobsStore | Handle array format | ✅ Working | Lines 191-193: stores todo_items |
| agentJobsStore | Calculate steps | ✅ Working | Lines 170-178: completed/total calc |
| websocketEventRouter | Pass todo_items | ✅ Working | Line 310: forwards correctly |
| MessageAuditModal | Render Plan tab | ✅ Working | Lines 100-131: full implementation |
| JobsTab | Display Steps | ✅ Working | Lines 102-113: shows calculated values |

**Flow Validation**:

When agent calls `report_progress(job_id, tenant_key, todo_items=[...])`:
1. Backend derives `completed_steps`, `total_steps` from array
2. WebSocket emits `job:progress_update` with `todo_items` in payload
3. Event router (websocketEventRouter.js) passes to agentJobsStore.handleProgressUpdate()
4. Store calculates `steps` object from array (lines 170-178)
5. Store stores both `todo_items` (for Plan tab) and `steps` (for dashboard)
6. JobsTab renders "X / Y" in Steps column (lines 102-113)
7. User clicks Steps → opens MessageAuditModal with Plan tab
8. MessageAuditModal renders full todo_items array (lines 100-131)

**No Frontend Changes Required**: The existing code already perfectly handles the simplified format introduced in Phase 1-4.

**Conclusion**: Phase 5 verification complete. Frontend is ready for production use of simplified `todo_items` reporting.
