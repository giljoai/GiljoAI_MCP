# Handover 0279: Context Priority & Depth Configuration Integration Fix

**Date**: December 1, 2025
**Status**: Investigation Complete, Ready for Implementation
**Priority**: CRITICAL
**Complexity**: Medium (Frontend + Backend)
**Estimated Effort**: 4-6 hours

---

## Executive Summary

**CRITICAL FINDING**: Context Priority and Depth Configuration settings are **70% wired** but have **two critical gaps**:

1. **Frontend Bug**: GET/PUT endpoints for depth config have data structure mismatch (wrapper issue)
2. **Backend Gap**: Orchestrator tool call templates missing `user_id` parameter, causing priority filtering to be bypassed

**Impact**: Users can configure context priorities and depth settings in the UI, but:
- ✅ Depth settings (chunking levels, commit counts) ARE applied
- ❌ Field priorities (1=CRITICAL, 2=IMPORTANT, 3=NICE_TO_HAVE, 4=EXCLUDED) are NOT applied when orchestrator fetches context
- ⚠️ UI shows default values instead of user's saved settings (frontend bug)

**Root Cause**: Two-phase implementation where Phase 1 (MCP tool priority logic) and Phase 2 (thin client prompt generator) were never fully connected.

---

## Investigation Findings

### 1. Frontend Issue (DATA STRUCTURE MISMATCH)

**Error Log**:
```
08:13:00 - ERROR - Error in database session dependency:
[{'type': 'missing', 'loc': ('body', 'depth_config'), 'msg': 'Field required',
'input': {'vision_chunking': 'moderate', 'memory_last_n_projects': 3, ...}}]
```

**Root Cause**: API expects wrapped structure, frontend sends flat structure

**Backend Expects** (`api/endpoints/users.py:256-259`):
```json
{
  "depth_config": {
    "vision_chunking": "moderate",
    "memory_last_n_projects": 3,
    "git_commits": 25,
    ...
  }
}
```

**Frontend Sends** (`frontend/src/components/settings/ContextPriorityConfig.vue:329-336`):
```json
{
  "vision_chunking": "moderate",
  "memory_last_n_projects": 3,
  "git_commits": 25,
  ...
}
```

**Also Affected**: GET endpoint returns `{depth_config: {config: {...}}}` but frontend expects `{depth_config: {...}}`

---

### 2. Backend Issue (MISSING user_id IN ORCHESTRATOR TOOL CALLS)

**Location**: `src/giljo_mcp/thin_prompt_generator.py:560-577`

**Current Tool Templates**:
```python
category_to_tool = {
    "vision_documents": [
        f"fetch_vision_document("
        f"product_id='{product.id}', "
        f"tenant_key='{self.tenant_key}', "
        f"chunking='{depth_config.get('vision_chunking', 'moderate')}')"
        # ❌ NO user_id parameter
    ],
    "tech_stack": [
        f"fetch_tech_stack("
        f"product_id='{product.id}', "
        f"tenant_key='{self.tenant_key}', "
        f"sections='{depth_config.get('tech_stack_sections', 'all')}')"
        # ❌ NO user_id parameter
    ],
    # ... all 9 tools missing user_id
}
```

**Impact**: When orchestrator calls MCP tools without `user_id`:
```python
# Inside fetch_vision_document():
priority = await get_user_priority("vision_documents", tenant_key, user_id=None, db_manager)
# ↓ user_id is None
# ↓ Returns DEFAULT priority (not user's custom priority)
# ↓ USER'S FIELD PRIORITY CONFIGURATION IGNORED
```

---

## Architecture Analysis

### Data Flow (What Works ✅)

```
User Settings UI
    ↓ (Save settings)
Database (users.field_priority_config, users.depth_config) ✅
    ↓ (Launch project)
ProjectService.launch_project() ✅
    ↓ (Extract settings from user)
Orchestrator Job Metadata ✅
    {
        "field_priorities": {...},  # User's custom priorities
        "depth_config": {...},      # User's depth settings
        "user_id": "..."            # User ID
    }
    ↓ (Orchestrator calls MCP tool)
get_orchestrator_instructions(orchestrator_id, tenant_key) ✅
    ↓ (Reads job_metadata)
MissionPlanner._build_context_with_priorities(..., user_id) ✅
    ↓ (Applies priorities)
Condensed Mission (Internal context building) ✅ PRIORITIES APPLIED
```

### Data Flow (What's Broken ❌)

```
Orchestrator Staging Prompt
    ↓ (Reads tool templates from thin_prompt_generator)
Tool Call Template: fetch_vision_document(product_id, tenant_key, chunking) ❌
                    # Missing: user_id parameter
    ↓ (Orchestrator executes tool)
fetch_vision_document(product_id='...', tenant_key='...', chunking='moderate')
    ↓ (Tool checks priority)
get_user_priority("vision_documents", tenant_key, user_id=None, ...) ❌
    ↓ (user_id is None)
return default_priority  # ❌ USER'S CUSTOM PRIORITY IGNORED
    ↓
Full Vision Document Returned (even if user set EXCLUDED) ❌
```

---

## Integration Verification Matrix

| Context Source | Storage | Retrieval | Depth Applied | Priority Applied | Tool Template Issue |
|----------------|---------|-----------|---------------|------------------|---------------------|
| Product Core | ✅ | ✅ | N/A | ❌ | Missing user_id |
| Vision Docs | ✅ | ✅ | ✅ (chunking) | ❌ | Missing user_id |
| Tech Stack | ✅ | ✅ | ✅ (sections) | ❌ | Missing user_id |
| Architecture | ✅ | ✅ | ✅ (depth) | ❌ | Missing user_id |
| Testing Config | ✅ | ✅ | ✅ (depth) | ❌ | Missing user_id |
| 360 Memory | ✅ | ✅ | ✅ (last_n) | ❌ | Missing user_id |
| Git History | ✅ | ✅ | ✅ (commits) | ❌ | Missing user_id |
| Agent Templates | ✅ | ✅ | ✅ (detail) | ❌ | Missing user_id |
| Project Context | ✅ | ✅ | N/A | ❌ | Missing user_id |

**Legend**:
- ✅ = Fully implemented and working
- ❌ = Implemented but not working due to gap
- ⚠️ = Partial implementation

---

## Workflow Impact Analysis

### According to Workflow PDF (Page 19, 23, 32)

**Expected Behavior**:
1. User configures context priorities: "Vision Documents = EXCLUDED (4)"
2. User clicks [Stage Project]
3. Orchestrator fetches context based on priorities
4. Vision documents are NOT included in mission (excluded)

**Actual Behavior**:
1. User configures context priorities: "Vision Documents = EXCLUDED (4)"
2. User clicks [Stage Project]
3. Orchestrator calls `fetch_vision_document()` WITHOUT user_id
4. Tool returns DEFAULT priority → Full vision documents included ❌

### Real-World Example

**User Configuration**:
```json
{
  "field_priority_config": {
    "priorities": {
      "vision_documents": 4,  // EXCLUDED
      "tech_stack": 1,        // CRITICAL
      "architecture": 2,      // IMPORTANT
      "testing_config": 3     // NICE_TO_HAVE
    }
  },
  "depth_config": {
    "vision_chunking": "none",  // Don't want vision docs
    "git_commits": 10           // Want minimal git history
  }
}
```

**Current Orchestrator Behavior**:
- ✅ Fetches only 10 git commits (depth setting works)
- ❌ Still fetches full vision documents (priority setting ignored)
- Result: Token waste, slower mission generation, user intent not respected

---

## Fix Plan

### Fix #1: Frontend - Data Structure Wrapper (2 lines)

**File**: `frontend/src/components/settings/ContextPriorityConfig.vue`

**Change #1 - GET Response Parsing (Line 282)**:
```javascript
// BEFORE:
const depthData = depthResponse.data || {}

// AFTER:
const depthData = depthResponse.data?.depth_config || {}
```

**Change #2 - PUT Request Wrapping (Lines 329-336)**:
```javascript
// BEFORE:
await axios.put('/api/v1/users/me/context/depth', {
  vision_chunking: config.value.vision_documents?.depth || 'moderate',
  memory_last_n_projects: config.value.memory_360?.count || 3,
  git_commits: config.value.git_history?.count || 25,
  agent_template_detail: config.value.agent_templates?.depth || 'standard',
  tech_stack_sections: config.value.tech_stack?.sections || 'all',
  architecture_depth: config.value.architecture?.depth || 'overview',
})

// AFTER:
await axios.put('/api/v1/users/me/context/depth', {
  depth_config: {  // ← Wrap in depth_config
    vision_chunking: config.value.vision_documents?.depth || 'moderate',
    memory_last_n_projects: config.value.memory_360?.count || 3,
    git_commits: config.value.git_history?.count || 25,
    agent_template_detail: config.value.agent_templates?.depth || 'standard',
    tech_stack_sections: config.value.tech_stack?.sections || 'all',
    architecture_depth: config.value.architecture?.depth || 'overview',
  }
})
```

---

### Fix #2: Backend - Add user_id to Tool Templates (~50 lines)

**File**: `src/giljo_mcp/thin_prompt_generator.py`

**Method**: `_generate_thin_prompt()` (Lines 517-704)

**Strategy**: Add `user_id` parameter to all tool call templates in `category_to_tool` dict

**Example Changes**:

```python
# Line 560 - Vision Documents
# BEFORE:
f"fetch_vision_document(product_id='{product.id}', tenant_key='{self.tenant_key}', chunking='{depth_config.get('vision_chunking', 'moderate')}')"

# AFTER:
f"fetch_vision_document(product_id='{product.id}', tenant_key='{self.tenant_key}', chunking='{depth_config.get('vision_chunking', 'moderate')}', user_id='{user_id}')"

# Line 568 - Tech Stack
# BEFORE:
f"fetch_tech_stack(product_id='{product.id}', tenant_key='{self.tenant_key}', sections='{depth_config.get('tech_stack_sections', 'all')}')"

# AFTER:
f"fetch_tech_stack(product_id='{product.id}', tenant_key='{self.tenant_key}', sections='{depth_config.get('tech_stack_sections', 'all')}', user_id='{user_id}')"

# Line 570 - Architecture
# BEFORE:
f"fetch_architecture(product_id='{product.id}', tenant_key='{self.tenant_key}', depth='{depth_config.get('architecture_depth', 'overview')}')"

# AFTER:
f"fetch_architecture(product_id='{product.id}', tenant_key='{self.tenant_key}', depth='{depth_config.get('architecture_depth', 'overview')}', user_id='{user_id}')"

# Line 572 - Testing Config
# BEFORE:
f"fetch_testing_config(product_id='{product.id}', tenant_key='{self.tenant_key}')"

# AFTER:
f"fetch_testing_config(product_id='{product.id}', tenant_key='{self.tenant_key}', user_id='{user_id}')"

# Line 574 - 360 Memory
# BEFORE:
f"fetch_360_memory(product_id='{product.id}', tenant_key='{self.tenant_key}', last_n_projects={depth_config.get('memory_last_n_projects', 3)})"

# AFTER:
f"fetch_360_memory(product_id='{product.id}', tenant_key='{self.tenant_key}', last_n_projects={depth_config.get('memory_last_n_projects', 3)}, user_id='{user_id}')"

# Line 577 - Git History
# BEFORE:
f"fetch_git_history(product_id='{product.id}', tenant_key='{self.tenant_key}', commits={depth_config.get('git_commits', 25)})"

# AFTER:
f"fetch_git_history(product_id='{product.id}', tenant_key='{self.tenant_key}', commits={depth_config.get('git_commits', 25)}, user_id='{user_id}')"

# Additional tools at lines 581-592:
# - fetch_agent_templates
# - fetch_product_context
# - fetch_project_context
# (Apply same pattern)
```

**Verification Step**: Ensure `user_id` variable is available in `_generate_thin_prompt()` scope (should already be passed at line 304 in `generate()` method)

---

### Fix #3: Add Integration Test (NEW FILE)

**File**: `tests/integration/test_orchestrator_priority_filtering.py` (NEW)

```python
"""
Integration test for Context Priority & Depth Configuration in Orchestrator Workflow.

Tests that user's field priority settings are respected when orchestrator fetches context.
"""
import pytest
from sqlalchemy import select
from src.giljo_mcp.models.auth import User
from src.giljo_mcp.services.project_service import ProjectService
from src.giljo_mcp.tools.orchestration import get_orchestrator_instructions
from src.giljo_mcp.tools.context import fetch_vision_document


@pytest.mark.asyncio
async def test_orchestrator_respects_user_priority_excluded(
    db_session,
    test_user,
    test_product,
    test_project,
):
    """
    Test that when user sets vision_documents priority to EXCLUDED (4),
    orchestrator does NOT include vision documents in context.
    """
    # ARRANGE: Set user's vision_documents priority to EXCLUDED
    test_user.field_priority_config = {
        "version": "2.0",
        "priorities": {
            "vision_documents": 4,  # EXCLUDED
            "tech_stack": 1,        # CRITICAL
        }
    }
    await db_session.commit()

    # ACT: Launch project (creates orchestrator job with metadata)
    project_service = ProjectService(db_session, test_user.tenant_key)
    await project_service.launch_project(
        project_id=test_project.id,
        user_id=test_user.id
    )

    # Get orchestrator instructions
    orchestrator_job = await db_session.execute(
        select(AgentJob).where(
            AgentJob.project_id == test_project.id,
            AgentJob.agent_type == "orchestrator"
        )
    )
    orchestrator = orchestrator_job.scalar_one()

    instructions = await get_orchestrator_instructions(
        orchestrator_id=str(orchestrator.id),
        tenant_key=test_user.tenant_key
    )

    # ASSERT: Vision documents should NOT be in the tool list
    assert "fetch_vision_document" not in instructions["prompt"]
    # OR: If tool is listed, verify it's marked as excluded
    if "fetch_vision_document" in instructions["prompt"]:
        # Check that tool call includes user_id
        assert f"user_id='{test_user.id}'" in instructions["prompt"]


@pytest.mark.asyncio
async def test_fetch_vision_document_respects_user_priority(
    db_session,
    test_user,
    test_product,
):
    """
    Test that fetch_vision_document MCP tool respects user's priority when user_id is passed.
    """
    # ARRANGE: Set user's vision_documents priority to EXCLUDED
    test_user.field_priority_config = {
        "version": "2.0",
        "priorities": {
            "vision_documents": 4,  # EXCLUDED
        }
    }
    await db_session.commit()

    # ACT: Call fetch_vision_document WITH user_id
    result = await fetch_vision_document(
        product_id=str(test_product.id),
        tenant_key=test_user.tenant_key,
        chunking="moderate",
        user_id=str(test_user.id)  # ← CRITICAL: Pass user_id
    )

    # ASSERT: Should return excluded response
    assert result["excluded"] is True
    assert result["reason"] == "User priority set to EXCLUDED (4)"
    assert "vision_document_content" not in result  # No actual content


@pytest.mark.asyncio
async def test_depth_config_applied(
    db_session,
    test_user,
    test_product,
):
    """
    Test that depth configuration (chunking, commits, etc.) is applied correctly.
    """
    # ARRANGE: Set user's depth config
    test_user.depth_config = {
        "vision_chunking": "light",  # Only 1 chunk
        "git_commits": 10,           # Only 10 commits
    }
    await db_session.commit()

    # ACT: Launch project and verify tool calls include depth params
    project_service = ProjectService(db_session, test_user.tenant_key)
    result = await project_service.launch_project(
        project_id=test_project.id,
        user_id=test_user.id
    )

    # ASSERT: Orchestrator prompt should include depth parameters
    orchestrator_prompt = result["orchestrator_prompt"]
    assert "chunking='light'" in orchestrator_prompt
    assert "commits=10" in orchestrator_prompt
```

**Test Coverage**:
- ✅ User priority EXCLUDED (4) is respected
- ✅ Depth configuration is applied
- ✅ user_id is passed to MCP tools
- ✅ MCP tools return filtered/excluded responses correctly

---

## Testing Strategy

### 1. Unit Tests (Existing - Should Pass)

**Files**:
- `tests/api/test_depth_controls.py` (Lines 160-201)
- `tests/services/test_user_service.py`

**Verification**: These already test backend storage/retrieval correctly. No changes needed.

---

### 2. Integration Tests (NEW - To Be Added)

**File**: `tests/integration/test_orchestrator_priority_filtering.py` (see Fix #3 above)

**Test Scenarios**:
1. User sets priority EXCLUDED → Tool returns excluded response
2. User sets priority CRITICAL → Tool returns full content with priority framing
3. Depth config applied correctly (chunking, commits, etc.)
4. Orchestrator prompt includes user_id in all tool calls

---

### 3. End-to-End Manual Test

**Test Procedure**:

```bash
# 1. Start server
python startup.py

# 2. Login to UI (http://localhost:7274)
# 3. Navigate to My Settings → Context
# 4. Configure priorities:
#    - Vision Documents: EXCLUDED (4)
#    - Tech Stack: CRITICAL (1)
#    - Architecture: IMPORTANT (2)
# 5. Configure depth:
#    - Vision Chunking: none
#    - Git Commits: 10
# 6. Save settings
# 7. Create/activate a project
# 8. Click [Stage Project]
# 9. Verify in logs:
#    - Orchestrator tool calls include user_id
#    - Vision documents NOT fetched (or marked excluded)
#    - Only 10 git commits fetched
```

**Expected Logs**:
```
[ORCHESTRATOR] Calling: fetch_tech_stack(product_id='...', tenant_key='...', sections='all', user_id='...')
[ORCHESTRATOR] Calling: fetch_git_history(product_id='...', tenant_key='...', commits=10, user_id='...')
[MCP TOOL] fetch_vision_document: Priority EXCLUDED (4) - skipping
[ORCHESTRATOR] Mission generated with 2 context sources (vision_documents excluded per user priority)
```

---

## Rollout Plan

### Phase 1: Frontend Fix (Low Risk)
1. Update `ContextPriorityConfig.vue` (2 lines)
2. Test in browser dev tools
3. Verify GET/PUT requests work correctly
4. Deploy to frontend

**Risk**: Low - Only affects UI display, doesn't break orchestrator

---

### Phase 2: Backend Fix (Medium Risk)
1. Update `thin_prompt_generator.py` (~50 lines)
2. Run unit tests (existing tests should still pass)
3. Add integration tests (new file)
4. Test with real orchestrator in dev environment
5. Deploy to backend

**Risk**: Medium - Affects orchestrator behavior, but changes are additive (adds user_id parameter)

---

### Phase 3: Validation
1. Run full end-to-end test (UI → Database → Orchestrator → MCP → Context)
2. Verify priority filtering works
3. Verify depth settings work
4. Monitor orchestrator logs for correct tool calls

---

## Success Criteria

### Frontend Fix Success ✅
- [ ] GET `/api/v1/users/me/context/depth` returns parsable data
- [ ] PUT `/api/v1/users/me/context/depth` accepts wrapped structure
- [ ] UI displays user's saved depth settings correctly
- [ ] No more 422 Unprocessable Entity errors in logs

### Backend Fix Success ✅
- [ ] Orchestrator tool call templates include `user_id` parameter
- [ ] MCP tools receive `user_id` when called by orchestrator
- [ ] Priority filtering IS applied (user priority = 4 → excluded response)
- [ ] Integration tests pass (all green)

### End-to-End Success ✅
- [ ] User sets "Vision Documents = EXCLUDED" → Vision docs NOT fetched
- [ ] User sets "Git Commits = 10" → Only 10 commits fetched
- [ ] Orchestrator logs show correct tool calls with user_id
- [ ] Token usage reduced when user excludes heavy contexts

---

## Impact Assessment

### Before Fix
**Problem**: Users configure priorities but orchestrator ignores them
- ❌ Wasted tokens fetching excluded contexts
- ❌ Slower mission generation
- ❌ User intent not respected
- ⚠️ UI shows defaults instead of user settings

**Example**: User excludes vision documents (20K tokens), but orchestrator still fetches them → 20K token waste per staging

### After Fix
**Solution**: Orchestrator respects user's priorities and depth settings
- ✅ Excluded contexts are NOT fetched (token savings)
- ✅ Faster mission generation
- ✅ User intent fully respected
- ✅ UI shows correct user settings

**Example**: User excludes vision documents → Orchestrator skips fetch → 20K token savings per staging

---

## Risk Analysis

### Frontend Fix Risks
- **Low Risk**: Only affects UI parsing, no orchestrator impact
- **Rollback**: Easy - revert 2-line change

### Backend Fix Risks
- **Medium Risk**: Changes orchestrator behavior
- **Mitigation**:
  - `user_id` parameter is optional in MCP tools (backward compatible)
  - Existing tests validate current behavior
  - New tests validate priority filtering
- **Rollback**: Medium difficulty - revert tool template changes

### Deployment Risks
- **Low Risk**: Changes are additive, not breaking
- **Backward Compatibility**: ✅ Old prompts without user_id still work (fall back to defaults)

---

## Related Handovers

- **Handover 0314**: Context Management v2.0 - Depth Configuration implementation
- **Handover 0315**: Context Priority Configuration - Field priority implementation
- **Handover 0316**: Context Framing & Filtering - MCP tool priority logic
- **Handover 0246a-c**: Orchestrator Workflow & Token Optimization - Thin client architecture
- **Handover 0088**: Thin Client Architecture - Context prioritization

---

## Files to Modify

### Frontend (1 file, 2 lines)
- `frontend/src/components/settings/ContextPriorityConfig.vue`
  - Line 282: Change `depthResponse.data` → `depthResponse.data?.depth_config`
  - Lines 329-336: Wrap PUT payload in `depth_config` object

### Backend (1 file, ~50 lines)
- `src/giljo_mcp/thin_prompt_generator.py`
  - Lines 560-592: Add `user_id` parameter to all tool call templates

### Tests (1 new file, ~150 lines)
- `tests/integration/test_orchestrator_priority_filtering.py` (NEW)
  - Add 3 integration tests verifying priority filtering

---

## Documentation Updates Needed

### After Fix Complete:
1. Update `docs/ORCHESTRATOR.md` - Add note about user_id parameter in tool calls
2. Update `docs/components/STAGING_WORKFLOW.md` - Document priority filtering in staging
3. Update workflow PDF if needed (pages 19, 23, 32) - Verify context filtering diagrams

---

## Open Questions

1. **Q**: Should we add a UI indicator showing which contexts are excluded?
   **A**: Future enhancement - out of scope for this fix

2. **Q**: Should we log when contexts are excluded due to priority?
   **A**: Yes - add INFO log in `get_user_priority()` when returning EXCLUDED

3. **Q**: What happens if user_id is invalid/not found?
   **A**: Current behavior: Fall back to defaults (safe)

---

## Conclusion

This handover addresses a **critical integration gap** where user context settings are stored and retrieved correctly but not fully applied in the orchestrator workflow. The fix is straightforward:

1. **Frontend**: 2-line change to fix data structure wrapper
2. **Backend**: Add `user_id` to ~9 tool call templates
3. **Testing**: Add integration tests to prevent regression

**Estimated Complexity**: Medium
**Estimated Time**: 4-6 hours (including testing)
**Risk Level**: Low-Medium
**Priority**: CRITICAL (core feature not working as designed)

---

## Next Steps

1. ✅ Investigation complete (this handover)
2. ⏳ Implement frontend fix (2 lines)
3. ⏳ Implement backend fix (~50 lines)
4. ⏳ Add integration tests (~150 lines)
5. ⏳ Test end-to-end workflow
6. ⏳ Deploy and validate

---

**Handover Author**: Claude Code (Deep Researcher Agent)
**Review Status**: Ready for Implementation
**Approval Required**: Yes (affects orchestrator core functionality)
