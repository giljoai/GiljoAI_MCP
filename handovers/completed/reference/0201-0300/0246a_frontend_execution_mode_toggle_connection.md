# Handover 0246a: Frontend Execution Mode Toggle Connection

**Date**: 2025-11-24
**Status**: READY FOR IMPLEMENTATION
**Priority**: HIGH
**Type**: Frontend Connection (TRIVIAL FIX)
**Builds Upon**: Handover 0246 (Dynamic Agent Discovery Research)
**Estimated Time**: 4-6 hours

---

## Executive Summary

**CRITICAL DISCOVERY**: Backend execution mode infrastructure is **90% COMPLETE**. The API endpoint exists, prompt generation paths are implemented, and mode-specific orchestrator instructions are fully functional. The frontend toggle just needs a click handler—this is a **TRIVIAL 4-6 hour fix**, not a major project.

**What Already Exists** (Backend Complete):
- ✅ API endpoint `/api/v1/prompts/execution/{orchestrator_job_id}` accepts `claude_code_mode` parameter
- ✅ Complete prompt generation: `_build_claude_code_execution_prompt()` and `_build_multi_terminal_execution_prompt()`
- ✅ Mode-specific orchestrator instructions differentiated
- ✅ Database JSONB schema supports mode storage in `projects.meta_data`

**What's Missing** (The 10%):
- ❌ Frontend toggle click handler
- ❌ Mode persistence in project metadata
- ❌ Mode validation (prevent changing with active jobs)

**Result**: Wire frontend to existing backend in 4-6 hours.

---

## Problem Statement

### Current State (Broken)

**File**: `F:\GiljoAI_MCP\frontend\src\components\projects\JobsTab.vue`

**Lines 3-7, 321**:
```vue
<!-- No click handler, no API call -->
<v-switch
  v-model="usingClaudeCodeSubagents"
  label="Claude Subagents"
  density="compact"
  hide-details
/>

<!-- Script section - hardcoded -->
const usingClaudeCodeSubagents = ref(false)  // Static value!
```

**Problem**: Toggle is purely visual—clicking it does nothing. No API call, no persistence.

### Target State (After 0246a)

```vue
<v-switch
  v-model="usingClaudeCodeSubagents"
  label="Claude Subagents"
  :disabled="hasActiveJobs"
  @update:model-value="handleModeToggle"
/>

<script setup>
const hasActiveJobs = computed(() => {
  return projectStore.activeJobs.some(job =>
    ['waiting', 'working'].includes(job.status)
  )
})

const handleModeToggle = async (newValue) => {
  if (hasActiveJobs.value) {
    showError("Cannot change execution mode with active jobs");
    return;
  }

  const mode = newValue ? 'claude-code' : 'multi-terminal';
  await projectStore.updateExecutionMode(currentProject.value.id, mode);
}
</script>
```

**Result**: Toggle calls existing backend, mode persists, toggle disabled when jobs active.

---

## Solution Overview

### What We're Building (Frontend Only)

**Component 1: Click Handler in JobsTab.vue**
- Add `@update:model-value` event handler
- Call project store method to update mode
- Validate no active jobs before allowing change

**Component 2: Project Store Method**
- Add `updateExecutionMode(projectId, mode)` method
- Call existing API endpoint
- Emit WebSocket event for real-time UI updates

**Component 3: Backend API Endpoint** (if needed)
- Check if `/api/v1/projects/{project_id}/execution-mode` exists
- If not: Create simple endpoint that updates `project.meta_data['execution_mode']`

**Component 4: Mode Fetching on Load**
- Fetch mode from `project.meta_data['execution_mode']` on component mount
- Set toggle state based on persisted value

### What We're NOT Building

**❌ New Service Layer**: Use existing `ProjectService` to update metadata
**❌ New Database Table**: Use existing `projects.meta_data` JSONB column
**❌ Backend Prompt Logic**: Already complete (Lines 885-1080 in `thin_prompt_generator.py`)
**❌ Complex State Machine**: Just disable toggle when jobs active

---

## Implementation Details

### Phase 1: Add Click Handler (1-2 hours)

**File**: `F:\GiljoAI_MCP\frontend\src\components\projects\JobsTab.vue`

**Changes Required**:

```vue
<template>
  <!-- Existing toggle, add disabled + event handler -->
  <v-switch
    v-model="usingClaudeCodeSubagents"
    label="Claude Subagents"
    density="compact"
    hide-details
    :disabled="hasActiveJobs"
    @update:model-value="handleModeToggle"
  />
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useProjectStore } from '@/stores/projectStore'
import { useNotification } from '@/composables/useNotification'

const projectStore = useProjectStore()
const { showError, showSuccess } = useNotification()

const usingClaudeCodeSubagents = ref(false)

// Computed: Check if any jobs are active
const hasActiveJobs = computed(() => {
  if (!projectStore.currentProject) return false

  return projectStore.activeJobs.some(job =>
    ['waiting', 'working'].includes(job.status)
  )
})

// Handler: Mode toggle clicked
async function handleModeToggle(newValue) {
  // Validate: No active jobs
  if (hasActiveJobs.value) {
    showError("Cannot change execution mode with active jobs")
    // Revert toggle state
    usingClaudeCodeSubagents.value = !newValue
    return
  }

  // Update mode via store
  const mode = newValue ? 'claude-code' : 'multi-terminal'
  const success = await projectStore.updateExecutionMode(
    projectStore.currentProject.id,
    mode
  )

  if (success) {
    showSuccess(`Execution mode changed to ${mode}`)
  } else {
    showError("Failed to update execution mode")
    // Revert toggle state
    usingClaudeCodeSubagents.value = !newValue
  }
}

// On mount: Fetch current mode
onMounted(async () => {
  if (projectStore.currentProject?.meta_data?.execution_mode) {
    const mode = projectStore.currentProject.meta_data.execution_mode
    usingClaudeCodeSubagents.value = mode === 'claude-code'
  }
})
</script>
```

**Estimated Time**: 1-2 hours

---

### Phase 2: Project Store Method (1-2 hours)

**File**: `F:\GiljoAI_MCP\frontend\src\stores\projectStore.js`

**Add Method**:

```javascript
// Add to projectStore actions
async updateExecutionMode(projectId, mode) {
  try {
    const response = await api.patch(
      `/api/v1/projects/${projectId}/execution-mode`,
      { execution_mode: mode }
    )

    if (response.data.success) {
      // Update local project state
      if (this.currentProject?.id === projectId) {
        if (!this.currentProject.meta_data) {
          this.currentProject.meta_data = {}
        }
        this.currentProject.meta_data.execution_mode = mode
      }

      return true
    }

    return false
  } catch (error) {
    console.error('Failed to update execution mode:', error)
    return false
  }
}
```

**Estimated Time**: 1-2 hours

---

### Phase 3: Backend API Endpoint (1-2 hours if needed)

**File**: `F:\GiljoAI_MCP\api\endpoints\projects.py`

**Check if endpoint exists**. If not, add:

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from src.giljo_mcp.services.project_service import ProjectService
from api.dependencies import get_project_service

router = APIRouter()

class ExecutionModeUpdate(BaseModel):
    execution_mode: str  # 'claude-code' or 'multi-terminal'

@router.patch("/{project_id}/execution-mode")
async def update_execution_mode(
    project_id: str,
    data: ExecutionModeUpdate,
    project_service: ProjectService = Depends(get_project_service)
):
    """Update project execution mode (claude-code or multi-terminal)"""

    # Validate mode value
    if data.execution_mode not in ['claude-code', 'multi-terminal']:
        raise HTTPException(
            status_code=400,
            detail="execution_mode must be 'claude-code' or 'multi-terminal'"
        )

    # Update project metadata
    result = await project_service.update_project_metadata(
        project_id=project_id,
        metadata_updates={'execution_mode': data.execution_mode}
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return {"success": True, "data": result["data"]}
```

**Note**: Check if `ProjectService.update_project_metadata()` exists. If not, add simple method:

```python
# In src/giljo_mcp/services/project_service.py

async def update_project_metadata(
    self,
    project_id: str,
    metadata_updates: dict
) -> dict[str, Any]:
    """Update project metadata (JSONB field)"""
    try:
        stmt = select(Project).where(
            Project.id == project_id,
            Project.tenant_key == self.tenant_key
        )
        result = await self.session.execute(stmt)
        project = result.scalar_one_or_none()

        if not project:
            return {"success": False, "error": "Project not found"}

        # Update meta_data JSONB field
        if project.meta_data is None:
            project.meta_data = {}

        project.meta_data.update(metadata_updates)

        # Mark as modified (for JSONB detection)
        flag_modified(project, 'meta_data')

        await self.session.commit()

        # Emit WebSocket event
        await websocket_manager.broadcast_to_tenant(
            tenant_key=self.tenant_key,
            event="project:metadata_updated",
            data={
                "project_id": project_id,
                "metadata": metadata_updates
            }
        )

        return {"success": True, "data": project}

    except Exception as e:
        logger.error(f"Failed to update project metadata: {e}")
        return {"success": False, "error": str(e)}
```

**Import Required**:
```python
from sqlalchemy.orm.attributes import flag_modified
```

**Estimated Time**: 1-2 hours

---

## Testing Requirements (TDD)

### RED Phase (Write Failing Tests First)

**Test File**: `F:\GiljoAI_MCP\tests\integration\test_execution_mode_toggle.py`

```python
import pytest
from httpx import AsyncClient
from src.giljo_mcp.models import Project

@pytest.mark.asyncio
async def test_update_execution_mode_success(
    client: AsyncClient,
    test_project,
    auth_headers
):
    """Test execution mode update succeeds"""
    response = await client.patch(
        f"/api/v1/projects/{test_project.id}/execution-mode",
        json={"execution_mode": "claude-code"},
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["meta_data"]["execution_mode"] == "claude-code"


@pytest.mark.asyncio
async def test_update_execution_mode_with_active_jobs_blocked(
    client: AsyncClient,
    test_project,
    auth_headers,
    db_session
):
    """Test cannot change mode with active jobs"""
    # Create active agent job
    from src.giljo_mcp.models import MCPAgentJob
    job = MCPAgentJob(
        project_id=test_project.id,
        tenant_key=test_project.tenant_key,
        agent_type="implementer",
        status="working",  # Active job
        mission="Test mission"
    )
    db_session.add(job)
    await db_session.commit()

    # Attempt to change mode
    response = await client.patch(
        f"/api/v1/projects/{test_project.id}/execution-mode",
        json={"execution_mode": "claude-code"},
        headers=auth_headers
    )

    # Should fail (or warn)
    assert response.status_code == 400
    data = response.json()
    assert "active jobs" in data["detail"].lower()


@pytest.mark.asyncio
async def test_invalid_execution_mode_rejected(
    client: AsyncClient,
    test_project,
    auth_headers
):
    """Test invalid mode value rejected"""
    response = await client.patch(
        f"/api/v1/projects/{test_project.id}/execution-mode",
        json={"execution_mode": "invalid-mode"},
        headers=auth_headers
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_execution_mode_persists_through_reload(
    client: AsyncClient,
    test_project,
    auth_headers,
    db_session
):
    """Test mode persists in database"""
    # Set mode
    await client.patch(
        f"/api/v1/projects/{test_project.id}/execution-mode",
        json={"execution_mode": "multi-terminal"},
        headers=auth_headers
    )

    # Reload project from database
    from sqlalchemy import select
    stmt = select(Project).where(Project.id == test_project.id)
    result = await db_session.execute(stmt)
    project = result.scalar_one()

    # Verify persisted
    assert project.meta_data["execution_mode"] == "multi-terminal"
```

**Run Tests (Must See RED)**:
```bash
pytest tests/integration/test_execution_mode_toggle.py -v
# EXPECTED: FAILED (tests written before implementation)
```

---

### GREEN Phase (Minimal Implementation)

Implement changes from Phases 1-3 above.

**Run Tests (Must See GREEN)**:
```bash
pytest tests/integration/test_execution_mode_toggle.py -v
# EXPECTED: PASSED (all tests green)
```

---

### REFACTOR Phase (Polish)

**Optimizations**:
- Extract validation logic into helper function
- Add structured logging
- Add WebSocket event emission

**Run Tests (Must Stay GREEN)**:
```bash
pytest tests/integration/test_execution_mode_toggle.py -v
# EXPECTED: PASSED (tests still green after refactor)
```

---

## Success Criteria

### Functional Requirements

**Must Have**:
- ✅ Toggle sends API request when clicked
- ✅ Mode persists in `project.meta_data['execution_mode']`
- ✅ Toggle state reflects persisted mode on page load
- ✅ Toggle disabled when active jobs exist
- ✅ Error message shown when mode change blocked
- ✅ Success notification shown on mode change

**Nice to Have**:
- ✅ WebSocket event emitted on mode change
- ✅ Mode validation (only 'claude-code' or 'multi-terminal')
- ✅ Tooltip explaining when toggle is disabled

### Testing Requirements

**Test Coverage**:
- ✅ >80% coverage on new code
- ✅ Integration tests for API endpoint
- ✅ E2E test for toggle interaction
- ✅ Multi-tenant isolation verified

**Test Cases**:
1. ✅ Mode change succeeds when no active jobs
2. ✅ Mode change blocked with active jobs
3. ✅ Invalid mode value rejected
4. ✅ Mode persists through page reload
5. ✅ Toggle state syncs with backend

### Code Quality

**Standards**:
- ✅ Service layer pattern (ProjectService used)
- ✅ Multi-tenant isolation (tenant_key filter)
- ✅ Pydantic schemas for validation
- ✅ Structured logging with metadata
- ✅ No zombie code (clean implementation)

---

## Edge Cases & Mitigations

### Edge Case 1: Mode Change During Job Spawn

**Scenario**: User changes mode while orchestrator is spawning agent jobs.

**Mitigation**: Check job status before allowing mode change:
```python
# In ProjectService.update_project_metadata()
active_jobs = await self.session.execute(
    select(MCPAgentJob).where(
        MCPAgentJob.project_id == project_id,
        MCPAgentJob.status.in_(['waiting', 'working'])
    )
)
if active_jobs.scalars().first():
    return {"success": False, "error": "Cannot change mode with active jobs"}
```

---

### Edge Case 2: Toggle State Desync

**Scenario**: WebSocket connection drops, toggle state desyncs from backend.

**Mitigation**: Fetch mode from backend on component mount:
```javascript
onMounted(async () => {
  const project = await projectStore.fetchProject(currentProjectId)
  usingClaudeCodeSubagents.value =
    project.meta_data?.execution_mode === 'claude-code'
})
```

---

### Edge Case 3: Mode Not Set (Legacy Projects)

**Scenario**: Existing projects don't have `execution_mode` in metadata.

**Mitigation**: Default to 'multi-terminal':
```javascript
const mode = project.meta_data?.execution_mode || 'multi-terminal'
usingClaudeCodeSubagents.value = mode === 'claude-code'
```

---

## Related Work

**Depends On**:
- None (backend already complete)

**Enables**:
- Handover 0246b (Dynamic Agent Discovery) - uses execution mode for agent filtering
- Handover 0246c (Succession Mode Preservation) - preserves mode through handover

**Related Handovers**:
- Handover 0109 (built the backend infrastructure)
- Handover 0246 (research that discovered backend completeness)

---

## Rollback Plan

### Rollback Triggers

Rollback if:
- Tests fail after implementation
- Mode change breaks existing orchestrator workflows
- WebSocket events cause performance issues
- Toggle causes UI freezing

### Rollback Steps

1. **Immediate**: Revert frontend toggle to hardcoded `ref(false)`
2. **Database**: No schema changes (JSONB field optional)
3. **API**: Endpoint is additive (no breaking changes)

**Rollback Command**:
```bash
git revert HEAD
npm run build && cd frontend && npm run build
```

---

## Deliverables

**Before marking complete, verify**:

1. ✅ Tests written FIRST (TDD Red → Green → Refactor)
2. ✅ All tests passing (pytest + npm test)
3. ✅ Coverage >80% for new code
4. ✅ Service layer compliance (ProjectService used)
5. ✅ Multi-tenant isolation verified
6. ✅ No zombie code (clean implementation)
7. ✅ Structured logging added
8. ✅ WebSocket events emitted
9. ✅ Manual testing complete (toggle works in UI)
10. ✅ Git commit with descriptive message

**Git Commit Template**:
```bash
git add .
git commit -m "feat: Connect execution mode toggle to backend (Handover 0246a)

- Add click handler to JobsTab.vue toggle
- Add ProjectService.update_project_metadata() method
- Add /api/v1/projects/{id}/execution-mode endpoint
- Add mode validation (prevent change with active jobs)
- Add comprehensive integration tests

Tests: 5 passed, 0 failed
Coverage: 87%


```

---

## Conclusion

This is a **TRIVIAL 4-6 hour fix** that connects frontend UI to existing backend infrastructure. The backend is 90% complete (API endpoint, prompt generation, mode differentiation all exist). We're just wiring the toggle to call the API.

**Key Insight**: Always grep for existing implementations before assuming new architecture is needed!

**Implementation Order**: This is the **HIGHEST PRIORITY** handover because it completes work that was 90% done. Implement this before 0246b, 0246c, or 0246d.

---

**Document Version**: 1.0
**Author**: Documentation Manager Agent
**Date**: 2025-11-24
**Builds Upon**: Handover 0246
**Estimated Timeline**: 4-6 hours
**Status**: READY FOR IMPLEMENTATION
