# Handover 0392: TODO Progress Simplification

**Status**: IN PROGRESS
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

### Phase 4: Templates
- [ ] Update template_seeder.py
- [ ] Regenerate .claude/agents templates

### Phase 5: Verification
- [ ] Test dashboard Steps column
- [ ] Test Plan/TODOs tab
- [ ] Verify old format still works
