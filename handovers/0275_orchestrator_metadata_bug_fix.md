# Handover 0275: Orchestrator job_metadata Bug Fix

**Date**: 2025-11-30
**Agent**: Backend Integration Tester Agent
**Status**: ✅ COMPLETED
**Criticality**: HIGH - Blocks context prioritization and orchestration (v2.0)

## Problem Statement

Orchestrator `job_metadata` was empty `{}` in database despite user having field priorities configured in My Settings → Context. This breaks the entire context prioritization system because orchestrators cannot access user settings when calling MCP tools.

### Root Cause

**File**: `src/giljo_mcp/thin_prompt_generator.py`
**Method**: `ThinClientPromptGenerator.generate()` (lines 209-217)

When reusing an existing orchestrator (instead of creating a new one), the code did NOT update `job_metadata`. It simply reused the orchestrator ID and returned, leaving the old (empty) metadata intact.

```python
# BEFORE FIX (line 209-217):
if existing_orchestrator:
    # Reuse existing active orchestrator (no database write)
    orchestrator_id = existing_orchestrator.job_id
    instance_number = existing_orchestrator.instance_number

    logger.info(
        f"[ThinPromptGenerator] Reusing existing orchestrator {orchestrator_id} "
        f"(instance #{instance_number}) for project {project_id}"
    )
    # ❌ BUG: No metadata update - job_metadata stays as {}
```

### Why This Happened

1. **Historical Context**: The orchestrator was created BEFORE Handover 0088/0315 implemented metadata storage
2. **Reuse Logic**: Handover 0111 added orchestrator reuse to prevent duplicate creation on every "Stage Project" click
3. **Metadata Addition**: Handovers 0088/0315 added `job_metadata` storage for field priorities and depth config
4. **Missing Update**: The reuse logic was never updated to populate metadata for existing orchestrators

## Solution

**File**: `src/giljo_mcp/thin_prompt_generator.py`
**Lines**: 209-233

Added metadata update logic when reusing existing orchestrator:

```python
# AFTER FIX (lines 209-233):
if existing_orchestrator:
    # Reuse existing active orchestrator
    orchestrator_id = existing_orchestrator.job_id
    instance_number = existing_orchestrator.instance_number

    # BUG FIX (Handover 0275): Update job_metadata when reusing orchestrator
    # Before fix: job_metadata was left as {} from old orchestrator creation
    # After fix: job_metadata is updated with current user settings
    existing_orchestrator.job_metadata = {
        "field_priorities": field_priorities or {},
        "depth_config": depth_config,
        "user_id": user_id,
        "tool": tool,
        "created_via": "thin_client_generator",
        "reused_at": str(datetime.now())  # Track when metadata was updated
    }

    # Commit metadata update to database
    await self.db.commit()
    await self.db.refresh(existing_orchestrator)

    logger.info(
        f"[ThinPromptGenerator] Reusing existing orchestrator {orchestrator_id} "
        f"(instance #{instance_number}) for project {project_id} - metadata updated"
    )
```

### Key Changes

1. ✅ Update `job_metadata` with current user settings (field_priorities, depth_config, user_id, tool)
2. ✅ Commit changes to database (`await self.db.commit()`)
3. ✅ Refresh orchestrator object (`await self.db.refresh()`)
4. ✅ Add `reused_at` timestamp for audit trail
5. ✅ Add `datetime` import at top of file

## Testing

**File**: `tests/integration/test_orchestrator_metadata_flow.py`
**Tests**: 3 comprehensive integration tests

### Test 1: New Orchestrator Creation
- ✅ User configures field priorities in My Settings
- ✅ User clicks "Stage Project" for first time
- ✅ Orchestrator created with populated job_metadata
- ✅ Verifies field_priorities, depth_config, user_id, tool all present

### Test 2: Orchestrator Reuse with Metadata Update (BUG FIX TEST)
- ✅ Create old orchestrator with empty metadata `{}`
- ✅ User updates field priorities in My Settings
- ✅ User clicks "Stage Project" again
- ✅ ThinClientPromptGenerator reuses orchestrator
- ✅ **BUG FIX VERIFIED**: job_metadata is UPDATED (not left as `{}`)
- ✅ Verifies updated field priorities match user's current settings
- ✅ Verifies `reused_at` timestamp is present

### Test 3: Default Values
- ✅ User has NO custom field_priority_config or depth_config
- ✅ User clicks "Stage Project"
- ✅ Orchestrator created with default values (field_priorities={}, depth_config=defaults)

### Test Results

```bash
tests/integration/test_orchestrator_metadata_flow.py::test_orchestrator_metadata_new_creation PASSED [ 33%]
tests/integration/test_orchestrator_metadata_flow.py::test_orchestrator_metadata_reuse_updates PASSED [ 66%]
tests/integration/test_orchestrator_metadata_flow.py::test_orchestrator_metadata_default_values PASSED [100%]

============================== 3 passed in 0.89s ==============================
```

## Impact

### Before Fix
- ❌ Orchestrator `job_metadata` was empty `{}`
- ❌ MCP tools could not access user field priorities
- ❌ Context prioritization system broken
- ❌ Depth configuration not accessible
- ❌ No audit trail of who created orchestrator

### After Fix
- ✅ Orchestrator `job_metadata` populated with user settings
- ✅ MCP tools can access field priorities via `job_metadata`
- ✅ Context prioritization system functional
- ✅ Depth configuration accessible to MCP tools
- ✅ Full audit trail (user_id, tool, created_via, reused_at)

## Database Schema

**Table**: `mcp_agent_jobs`
**Column**: `job_metadata` (JSONB)

**Structure**:
```json
{
  "field_priorities": {
    "product_core": 1,      // CRITICAL
    "vision_documents": 2,  // IMPORTANT
    "tech_stack": 1,        // CRITICAL
    "architecture": 2,      // IMPORTANT
    "testing": 3,           // NICE_TO_HAVE
    "memory_360": 3,        // NICE_TO_HAVE
    "git_history": 4,       // EXCLUDED
    "agent_templates": 1,   // CRITICAL
    "project_context": 2    // IMPORTANT
  },
  "depth_config": {
    "vision_chunking": "moderate",
    "memory_last_n_projects": 3,
    "git_commits": 25,
    "agent_template_detail": "standard",
    "tech_stack_sections": "all",
    "architecture_depth": "overview"
  },
  "user_id": "uuid-of-user",
  "tool": "claude-code",
  "created_via": "thin_client_generator",
  "reused_at": "2025-11-30T10:00:00"  // Only present when reused
}
```

## Verification Steps

1. **Before Fix**:
   ```sql
   SELECT job_metadata FROM mcp_agent_jobs
   WHERE job_id = 'f73f6798-5922-4813-bc80-802c68ce1645';
   -- Result: {}
   ```

2. **After Fix** (user clicks "Stage Project" again):
   ```sql
   SELECT jsonb_pretty(job_metadata) FROM mcp_agent_jobs
   WHERE job_id = 'f73f6798-5922-4813-bc80-802c68ce1645';
   -- Result: {
   --   "field_priorities": { "product_core": 1, ... },
   --   "depth_config": { "vision_chunking": "moderate", ... },
   --   "user_id": "uuid",
   --   "tool": "claude-code",
   --   "created_via": "thin_client_generator",
   --   "reused_at": "2025-11-30T..."
   -- }
   ```

## Related Handovers

- **Handover 0088**: Introduced `job_metadata` storage for thin client architecture
- **Handover 0111**: Added orchestrator reuse logic (introduced the bug)
- **Handover 0315**: Added depth_config to job_metadata
- **Handover 0313**: User-configurable field priorities (v2.0)
- **Handover 0314**: User-configurable depth settings (v2.0)

## Files Changed

1. ✅ `src/giljo_mcp/thin_prompt_generator.py` (lines 49, 209-233)
   - Added `datetime` import
   - Added metadata update logic in orchestrator reuse block

2. ✅ `tests/integration/test_orchestrator_metadata_flow.py` (NEW FILE)
   - 3 comprehensive integration tests
   - Tests new creation, reuse update, and default values
   - Verifies complete metadata pipeline from user settings to database

## Follow-up Actions

1. ✅ Tests written and passing (3/3 pass)
2. ✅ Code fix implemented and tested
3. ⏸️ Database migration NOT needed (JSONB column already exists)
4. ⏸️ User communication NOT needed (silent bug fix)
5. ⏸️ Documentation update NOT needed (internal fix)

## Quality Assurance

✅ **TDD Methodology Followed**:
- Tests written FIRST to define expected behavior
- Code implemented to pass tests
- All tests passing (3/3)

✅ **Multi-Tenant Isolation**:
- All tests verify tenant_key filtering
- No cross-tenant data leakage

✅ **Edge Cases Covered**:
- New orchestrator creation
- Existing orchestrator reuse
- Default values when user has no settings
- Empty field_priorities and depth_config handling

✅ **Performance Impact**:
- Minimal (one additional UPDATE query on reuse)
- No impact on new orchestrator creation path

## Conclusion

The orchestrator `job_metadata` bug has been **COMPLETELY FIXED**. The fix ensures that:

1. **New orchestrators** are created with populated metadata (existing behavior - still works)
2. **Reused orchestrators** now have their metadata UPDATED with current user settings (BUG FIX)
3. **MCP tools** can now access user field priorities and depth config from `job_metadata`
4. **Context prioritization** system is fully functional
5. **Audit trail** is complete (user_id, tool, created_via, reused_at)

The fix is minimal, targeted, and thoroughly tested with 3 comprehensive integration tests covering all scenarios.

**Status**: ✅ READY FOR DEPLOYMENT
