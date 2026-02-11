# Staging Rollback Integration Guide

Guide for integrating database rollback when user cancels project staging.

## Overview

When a user cancels staging after the orchestrator has created a mission and spawned agents, we need to clean up the database to avoid orphaned agents and incomplete state.

**Module**: `src/giljo_mcp/staging_rollback.py`

## Quick Start

```python
from src.giljo_mcp.staging_rollback import rollback_project_staging

# Rollback staging (soft delete with audit trail)
result = await rollback_project_staging(
    tenant_key="tenant_abc123",
    project_id="proj_xyz789",
    orchestrator_job_id="orch_456def",
    reason="User canceled staging",
    hard_delete=False,  # Default: soft delete
)

print(f"Deleted {result['agents_deleted']} agents")
print(f"Protected {result['agents_protected']} agents (already launched)")
```

## API Endpoint Integration

### FastAPI Example

```python
# api/endpoints/projects.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.dependencies.auth import get_current_user
from src.giljo_mcp.staging_rollback import rollback_project_staging

router = APIRouter()


class CancelStagingRequest(BaseModel):
    """Request to cancel staging and rollback database"""
    project_id: str
    orchestrator_job_id: str
    reason: str = "User canceled staging"


class CancelStagingResponse(BaseModel):
    """Response from staging cancellation"""
    success: bool
    agents_deleted: int
    agents_protected: int
    orchestrator_updated: bool
    project_mission_cleared: bool
    rollback_timestamp: str
    rollback_reason: str
    message: str


@router.post(
    "/projects/{project_id}/cancel-staging",
    response_model=CancelStagingResponse,
    summary="Cancel staging and rollback database",
)
async def cancel_staging(
    project_id: str,
    request: CancelStagingRequest,
    current_user = Depends(get_current_user),
):
    """
    Cancel staging and clean up spawned agents.
    
    **Multi-tenant isolation**: Only affects current user's tenant.
    
    **Agent deletion rules**:
    - Deletes agents with status='waiting' or 'preparing' (not yet launched)
    - Protects agents with status='active', 'working', 'review' (already launched)
    - Updates orchestrator to 'failed' status
    - Clears project mission field
    
    **Soft delete (default)**:
    - Agents marked as 'failed' with rollback metadata
    - Maintains audit trail for debugging
    - Can potentially be recovered
    
    **Hard delete (optional)**:
    - Agents permanently removed from database
    - Use only when storage is critical
    """
    try:
        # Validate project_id matches request body
        if project_id != request.project_id:
            raise HTTPException(
                status_code=400,
                detail="project_id in path must match request body"
            )
        
        # Execute rollback
        result = await rollback_project_staging(
            tenant_key=current_user.tenant_key,
            project_id=request.project_id,
            orchestrator_job_id=request.orchestrator_job_id,
            reason=request.reason,
            hard_delete=False,  # Always use soft delete for user actions
        )
        
        # Build response message
        message = (
            f"Staging canceled successfully. "
            f"Deleted {result['agents_deleted']} agents, "
            f"protected {result['agents_protected']} agents (already launched)."
        )
        
        return CancelStagingResponse(
            success=result["success"],
            agents_deleted=result["agents_deleted"],
            agents_protected=result["agents_protected"],
            orchestrator_updated=result["orchestrator_updated"],
            project_mission_cleared=result["project_mission_cleared"],
            rollback_timestamp=result["rollback_timestamp"],
            rollback_reason=result["rollback_reason"],
            message=message,
        )
    
    except ValueError as e:
        # Validation errors (invalid parameters, orchestrator not found)
        raise HTTPException(status_code=400, detail=str(e))
    
    except RuntimeError as e:
        # Database transaction errors
        raise HTTPException(status_code=500, detail=str(e))
    
    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error canceling staging: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error during staging cancellation"
        )
```

### WebSocket Broadcast Integration

```python
# api/endpoints/projects.py (continued)

from api.websocket import websocket_manager

@router.post("/projects/{project_id}/cancel-staging")
async def cancel_staging(
    project_id: str,
    request: CancelStagingRequest,
    current_user = Depends(get_current_user),
):
    # ... (rollback logic as above)
    
    result = await rollback_project_staging(
        tenant_key=current_user.tenant_key,
        project_id=request.project_id,
        orchestrator_job_id=request.orchestrator_job_id,
        reason=request.reason,
    )
    
    # Broadcast WebSocket event to all tenant users
    await websocket_manager.broadcast_to_tenant(
        tenant_key=current_user.tenant_key,
        event_type="staging:canceled",
        data={
            "project_id": project_id,
            "agents_deleted": result["agents_deleted"],
            "agents_protected": result["agents_protected"],
            "reason": request.reason,
            "timestamp": result["rollback_timestamp"],
        }
    )
    
    return CancelStagingResponse(...)
```

## Frontend Integration

### Vue 3 Example

```vue
<!-- frontend/src/components/StagingCancelDialog.vue -->

<template>
  <v-dialog v-model="dialog" max-width="600">
    <v-card>
      <v-card-title>Cancel Staging?</v-card-title>
      
      <v-card-text>
        <p>Are you sure you want to cancel staging?</p>
        
        <v-alert type="warning" class="mt-4">
          <strong>This will:</strong>
          <ul>
            <li>Delete agents that haven't launched yet</li>
            <li>Clear the mission statement</li>
            <li>Mark orchestrator as failed</li>
          </ul>
        </v-alert>
        
        <v-text-field
          v-model="reason"
          label="Reason for cancellation (optional)"
          placeholder="e.g., Need to revise product vision"
          class="mt-4"
        />
      </v-card-text>
      
      <v-card-actions>
        <v-spacer />
        <v-btn @click="dialog = false">Keep Staging</v-btn>
        <v-btn 
          color="error" 
          @click="cancelStaging"
          :loading="loading"
        >
          Cancel Staging
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref } from 'vue'
import { useProjectStore } from '@/stores/project'

const props = defineProps({
  projectId: String,
  orchestratorJobId: String,
})

const emit = defineEmits(['canceled'])

const dialog = ref(false)
const reason = ref('')
const loading = ref(false)
const projectStore = useProjectStore()

async function cancelStaging() {
  loading.value = true
  
  try {
    const result = await projectStore.cancelStaging({
      project_id: props.projectId,
      orchestrator_job_id: props.orchestratorJobId,
      reason: reason.value || 'User canceled staging',
    })
    
    // Show success message
    showNotification({
      type: 'success',
      message: `Staging canceled. ${result.agents_deleted} agents deleted.`,
    })
    
    dialog.value = false
    emit('canceled', result)
    
  } catch (error) {
    // Show error message
    showNotification({
      type: 'error',
      message: error.response?.data?.detail || 'Failed to cancel staging',
    })
  } finally {
    loading.value = false
  }
}

function open() {
  dialog.value = true
}

defineExpose({ open })
</script>
```

### Vuex/Pinia Store Action

```javascript
// frontend/src/stores/project.js

import { defineStore } from 'pinia'
import api from '@/api/client'

export const useProjectStore = defineStore('project', {
  actions: {
    async cancelStaging({ project_id, orchestrator_job_id, reason }) {
      try {
        const response = await api.post(
          `/projects/${project_id}/cancel-staging`,
          {
            project_id,
            orchestrator_job_id,
            reason,
          }
        )
        
        // Update local state
        const project = this.projects.find(p => p.id === project_id)
        if (project) {
          project.mission = ''  // Mission cleared
          project.staging_status = 'canceled'
        }
        
        return response.data
        
      } catch (error) {
        console.error('Failed to cancel staging:', error)
        throw error
      }
    }
  }
})
```

## Soft Delete vs Hard Delete

### When to Use Soft Delete (RECOMMENDED)

**Default behavior** - Use for all user-initiated cancellations.

**Advantages**:
- Maintains audit trail (who canceled, when, why)
- Enables debugging (can inspect failed agents)
- Potential recovery feature (restore canceled staging)
- Compliance-friendly (some industries require retention)

**How it works**:
- Agents marked as `status='failed'`
- Rollback metadata stored in `job_metadata` JSONB field
- Agents remain in database but excluded from active queries

**Example metadata**:
```json
{
  "rollback_info": {
    "reason": "User canceled staging",
    "original_status": "waiting",
    "rollback_timestamp": "2025-11-06T10:30:00Z",
    "rollback_type": "staging_cancellation"
  }
}
```

### When to Use Hard Delete

**Use sparingly** - Only when storage is critical or compliance requires it.

**Advantages**:
- Reduces database size
- Permanent removal (meets some privacy regulations)
- Simplifies queries (no need to filter soft-deleted records)

**Disadvantages**:
- No audit trail (cannot investigate later)
- Cannot be undone
- Harder to debug issues

**How to enable**:
```python
result = await rollback_project_staging(
    tenant_key=tenant_key,
    project_id=project_id,
    orchestrator_job_id=orchestrator_job_id,
    reason=reason,
    hard_delete=True,  # Enable hard delete
)
```

## Edge Cases

### 1. Agents Already Launched

**Scenario**: User cancels staging but some agents already launched.

**Behavior**:
- Agents with `status='waiting'` or `'preparing'` → Deleted
- Agents with `status='active'`, `'working'`, `'review'` → Protected (NOT deleted)

**Result**:
```python
{
    "agents_deleted": 3,       # Deleted waiting agents
    "agents_protected": 2,     # Protected active agents
}
```

### 2. Orchestrator Succession

**Scenario**: Multiple orchestrator instances due to succession.

**Behavior**: Only deletes agents spawned by the SPECIFIC orchestrator instance.

**Example**:
```
Orchestrator Instance 1 (complete) → spawns Agent A
Orchestrator Instance 2 (active) → spawns Agent B, Agent C

Cancel Instance 2 → Only Agents B and C deleted
Agent A remains unchanged (spawned by Instance 1)
```

### 3. No Child Agents

**Scenario**: User cancels before any agents spawned.

**Behavior**: Rollback succeeds with 0 agents deleted.

**Result**:
```python
{
    "success": True,
    "agents_deleted": 0,       # No agents to delete
    "orchestrator_updated": True,  # Orchestrator still marked failed
}
```

### 4. Invalid Orchestrator

**Scenario**: Orchestrator job_id doesn't exist or wrong tenant.

**Behavior**: Raises `ValueError` with message.

**Error**:
```python
ValueError: Orchestrator orch_xyz not found for tenant tenant_abc
```

## Transaction Safety

All operations are wrapped in a database transaction:

```python
async with db_manager.get_session_async() as session:
    try:
        # 1. Validate orchestrator
        # 2. Find child agents
        # 3. Delete/soft-delete agents
        # 4. Clear project mission
        # 5. Update orchestrator status
        
        await session.commit()  # Commit all changes atomically
        
    except Exception as e:
        await session.rollback()  # Rollback on ANY error
        raise
```

**Atomicity Guarantee**: Either ALL changes succeed or NONE succeed (no partial state).

## Multi-Tenant Isolation

**CRITICAL SECURITY REQUIREMENT**: All queries filter by `tenant_key`.

```python
# ✅ CORRECT - Filtered by tenant_key
stmt = select(AgentJob).where(
    and_(
        AgentJob.tenant_key == tenant_key,      # Isolation filter
        AgentJob.spawned_by == orchestrator_job_id,
    )
)

# ❌ WRONG - Missing tenant_key filter (SECURITY VULNERABILITY!)
stmt = select(AgentJob).where(
    AgentJob.spawned_by == orchestrator_job_id,
)
```

**Zero Cross-Tenant Leakage**: Tenant A cannot affect Tenant B's agents.

## Testing

Run comprehensive test suite:

```bash
# Unit tests (12 test scenarios)
pytest tests/unit/test_staging_rollback.py -v

# Specific test
pytest tests/unit/test_staging_rollback.py::TestStagingRollbackSecurity::test_multi_tenant_isolation -v

# Coverage report
pytest tests/unit/test_staging_rollback.py --cov=src.giljo_mcp.staging_rollback --cov-report=html
```

**Test Coverage**:
- ✅ Soft delete with metadata
- ✅ Hard delete (permanent)
- ✅ Protected agents (already launched)
- ✅ Multi-tenant isolation (security)
- ✅ Orchestrator succession (multiple instances)
- ✅ Edge cases (no agents, invalid orchestrator)
- ✅ Transaction rollback on errors
- ✅ Convenience function

## Monitoring & Logging

All operations are logged for audit trail:

```
[StagingRollback] Starting rollback for project=proj_123, orchestrator=orch_456, tenant=tenant_abc
[StagingRollback] Found orchestrator: job_id=orch_456, status=active, agent_type=orchestrator
[StagingRollback] Found 5 child agents
[StagingRollback] Deletable: 3, Protected: 2
[StagingRollback] SOFT DELETE: agent=impl_1, old_status=waiting, type=implementer
[StagingRollback] SOFT DELETE: agent=impl_2, old_status=waiting, type=implementer
[StagingRollback] SOFT DELETE: agent=test_1, old_status=preparing, type=tester
[StagingRollback] Cleared mission for project=proj_123
[StagingRollback] Updated orchestrator: job_id=orch_456, status=failed, agents_deleted=3
[StagingRollback] SUCCESS: Deleted 3 agents, Protected 2 agents
```

## Performance Considerations

**Typical performance** (PostgreSQL):
- 10 agents: <50ms
- 100 agents: <200ms
- 1000 agents: <1s

**Optimizations**:
- Bulk operations (single UPDATE for soft delete)
- Indexed queries (tenant_key + spawned_by)
- Transaction batching (all changes in one commit)

## Troubleshooting

### Error: "tenant_key cannot be empty"

**Cause**: Missing tenant_key parameter.

**Fix**: Ensure tenant_key extracted from authenticated user.

```python
result = await rollback_project_staging(
    tenant_key=current_user.tenant_key,  # Must not be empty
    ...
)
```

### Error: "Orchestrator not found"

**Cause**: Invalid orchestrator job_id or wrong tenant.

**Fix**: Verify orchestrator exists and belongs to tenant.

```python
# Check if orchestrator exists
orchestrator = db.query(AgentJob).filter(
    AgentJob.tenant_key == tenant_key,
    AgentJob.job_id == orchestrator_job_id,
).first()

if not orchestrator:
    raise ValueError("Orchestrator not found")
```

### Protected Agents Not Deleted

**Cause**: Agents have status != 'waiting' or 'preparing'.

**Behavior**: This is EXPECTED and CORRECT. Agents already launched should NOT be deleted.

**Fix**: No fix needed. This is the intended behavior to prevent data loss.

## Future Enhancements

Potential improvements for v4.0:

1. **Restore Canceled Staging**: Undo cancellation within 10 minutes
2. **Partial Cancellation**: Cancel specific agents (not all)
3. **Cascade Cancellation**: Cancel child agents of canceled agents
4. **Auto-Cleanup**: Scheduled cleanup of soft-deleted agents (30+ days old)
5. **Rollback History**: Track all staging cancellations for analytics

## Related Documentation

- [Agent Job Manager](../developer_guides/agent_job_manager.md)
- [Multi-Tenant Architecture](../SERVER_ARCHITECTURE_TECH_STACK.md)
- [Database Schema](../developer_guides/database_schema.md)
- [Orchestrator Succession](../user_guides/orchestrator_succession_guide.md)

## Support

For issues or questions:
- GitHub Issues: https://github.com/patrik-giljoai/GiljoAI-MCP/issues
- Documentation: https://docs.giljoai.com
- Community: https://discord.gg/giljoai
