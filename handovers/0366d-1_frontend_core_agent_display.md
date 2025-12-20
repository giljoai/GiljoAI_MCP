# Handover 0366d-1: Frontend Core Agent Display

**Date**: 2025-12-20
**Agent**: Documentation Manager
**Status**: Specification
**Duration**: 3-4 hours
**Scope**: EXPLICIT (4 files only)

## Mission

Update frontend UI to display both `agent_id` and `job_id` fields for agent executions, replacing the single ID display with proper dual-identifier support. This handover is EXPLICITLY SCOPED to prevent scope creep (lesson learned from 0366c).

## Context

**Dual-Model Architecture** (Handovers 0366a-c):
- Backend now uses `AgentJob` (mission/template) + `AgentExecution` (instance) dual-model architecture
- Each execution has both `agent_id` (execution instance UUID) and `job_id` (foreign key to AgentJob)
- Frontend currently displays only one ID field and lacks execution-specific columns
- `instance_number` provides human-readable instance tracking (1, 2, 3...)

**Critical Constraint**: This handover covers ONLY the core display changes. Additional features (succession timeline, message components, launch workflow, installation) are handled in separate handovers (0366d-2, 0366d-3, 0366d-4).

## In Scope (EXPLICIT - 4 Files Only)

### 1. JobsTab.vue
**File**: `frontend/src/components/projects/JobsTab.vue`
**Lines**: ~390-400, ~21, ~39

**Changes Required**:
1. **Line ~390**: Change `agents` prop to accept `executions` data structure
   ```javascript
   // BEFORE
   agents: {
     type: Array,
     required: true,
     default: () => [],
   },

   // AFTER
   executions: {
     type: Array,
     required: true,
     default: () => [],
   },
   ```

2. **Line ~21**: Update table row binding to use `agent_id` as key
   ```vue
   <!-- BEFORE -->
   <tr v-for="agent in sortedAgents" :key="agent.job_id || agent.agent_id">

   <!-- AFTER -->
   <tr v-for="execution in sortedExecutions" :key="execution.agent_id">
   ```

3. **Line ~39**: Display both IDs in Agent ID column
   ```vue
   <!-- BEFORE -->
   <td class="agent-id-cell">{{ agent.job_id || agent.agent_id }}</td>

   <!-- AFTER -->
   <td class="agent-id-cell">
     <div class="id-container">
       <div class="id-label">Agent:</div>
       <code class="id-value">{{ execution.agent_id.slice(0, 8) }}</code>
       <div class="id-label">Job:</div>
       <code class="id-value">{{ execution.job_id.slice(0, 8) }}</code>
     </div>
   </td>
   ```

4. **Add**: Instance number display (new column after Agent Type)
   ```vue
   <th>Instance</th> <!-- Add to thead -->

   <!-- Add to tbody -->
   <td class="instance-cell">
     <v-chip size="small" color="blue-grey" label>
       #{{ execution.instance_number }}
     </v-chip>
   </td>
   ```

5. **Add**: Data-testid attributes for E2E testing
   ```vue
   <td class="agent-id-cell" data-testid="agent-id">
   <td class="instance-cell" data-testid="instance-number">
   ```

6. **Line ~511**: Update sortedAgents computed to sortedExecutions
   ```javascript
   // BEFORE
   const sortedAgents = computed(() => {
     if (!props.agents || props.agents.length === 0) return []
     return [...props.agents].sort((a, b) => { ... })
   })

   // AFTER
   const sortedExecutions = computed(() => {
     if (!props.executions || props.executions.length === 0) return []
     return [...props.executions].sort((a, b) => { ... })
   })
   ```

**Acceptance Criteria**:
- [ ] JobsTab displays both agent_id and job_id (truncated to 8 chars)
- [ ] Instance number displays as chip badge
- [ ] Data-testid attributes present on both ID columns
- [ ] Table sorts by execution status correctly
- [ ] No console errors when viewing Jobs tab

---

### 2. AgentTableView.vue
**File**: `frontend/src/components/orchestration/AgentTableView.vue`
**Lines**: ~205-215, ~42-44

**Changes Required**:
1. **Line ~205**: Update headers array to include new columns
   ```javascript
   // BEFORE
   const headers = [
     { title: 'Agent Type', key: 'agent_type', sortable: true },
     { title: 'Agent ID', key: 'agent_id', sortable: false },
     { title: 'Job Acknowledged', key: 'job_acknowledged', sortable: false, align: 'center' },
     ...
   ]

   // AFTER
   const headers = [
     { title: 'Agent Type', key: 'agent_type', sortable: true },
     { title: 'Instance', key: 'instance_number', sortable: true, align: 'center' },
     { title: 'Agent ID', key: 'agent_id', sortable: false },
     { title: 'Job ID', key: 'job_id', sortable: false },
     { title: 'Job Acknowledged', key: 'job_acknowledged', sortable: false, align: 'center' },
     ...
   ]
   ```

2. **Line ~42-44**: Replace single Agent ID template with dual ID templates
   ```vue
   <!-- BEFORE -->
   <template #item.agent_id="{ item }">
     <code class="agent-id">{{ item.job_id ? item.job_id.slice(0, 8) : '—' }}</code>
   </template>

   <!-- AFTER -->
   <template #item.instance_number="{ item }">
     <v-chip size="small" color="blue-grey" label data-testid="instance-chip">
       #{{ item.instance_number }}
     </v-chip>
   </template>

   <template #item.agent_id="{ item }">
     <code class="agent-id" data-testid="agent-id">{{ item.agent_id ? item.agent_id.slice(0, 8) : '—' }}</code>
   </template>

   <template #item.job_id="{ item }">
     <code class="agent-id" data-testid="job-id">{{ item.job_id ? item.job_id.slice(0, 8) : '—' }}</code>
   </template>
   ```

3. **Add**: CSS styles for instance chip
   ```scss
   /* Add to <style scoped> section */
   .agent-table-view :deep(.instance-chip) {
     min-width: 40px;
     justify-content: center;
   }
   ```

**Acceptance Criteria**:
- [ ] AgentTableView shows instance_number column with chip badge
- [ ] Agent ID column displays truncated agent_id only
- [ ] Job ID column displays truncated job_id only
- [ ] All ID columns have data-testid attributes
- [ ] Table renders without layout issues

---

### 3. AgentDetailsModal.vue (NEW FILE)
**File**: `frontend/src/components/projects/AgentDetailsModal.vue` (CREATE)

**Purpose**: Modal dialog for viewing agent execution details (opened from Jobs tab row click or action buttons)

**Full Implementation**:
```vue
<template>
  <v-dialog v-model="isOpen" max-width="700" persistent>
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon start>mdi-robot-outline</v-icon>
        <span>Agent Execution Details</span>
        <v-spacer></v-spacer>
        <v-btn icon variant="text" @click="close" aria-label="Close">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>
      <v-divider></v-divider>
      <v-card-text v-if="execution">
        <!-- Agent Info Section -->
        <div class="agent-info-section mb-4">
          <h4 class="text-subtitle-1 font-weight-bold mb-2">Execution Info</h4>
          <v-row dense>
            <v-col cols="6">
              <div class="info-item">
                <span class="info-label">Agent ID:</span>
                <code class="info-value" data-testid="modal-agent-id">{{ execution.agent_id }}</code>
              </div>
            </v-col>
            <v-col cols="6">
              <div class="info-item">
                <span class="info-label">Job ID:</span>
                <code class="info-value" data-testid="modal-job-id">{{ execution.job_id }}</code>
              </div>
            </v-col>
            <v-col cols="6">
              <div class="info-item">
                <span class="info-label">Instance Number:</span>
                <v-chip size="small" color="blue-grey" label data-testid="modal-instance">
                  #{{ execution.instance_number }}
                </v-chip>
              </div>
            </v-col>
            <v-col cols="6">
              <div class="info-item">
                <span class="info-label">Status:</span>
                <span data-testid="modal-status">{{ execution.status }}</span>
              </div>
            </v-col>
          </v-row>
        </div>

        <!-- Mission Section (from job, not execution) -->
        <div class="mission-section" v-if="job">
          <h4 class="text-subtitle-1 font-weight-bold mb-2">Mission</h4>
          <v-card variant="outlined" class="pa-3">
            <pre class="mission-text" data-testid="modal-mission">{{ job.mission || 'No mission assigned.' }}</pre>
          </v-card>
        </div>

        <!-- Progress Section -->
        <div class="progress-section mt-4" v-if="execution.progress">
          <h4 class="text-subtitle-1 font-weight-bold mb-2">Progress</h4>
          <v-card variant="outlined" class="pa-3">
            <pre class="progress-text">{{ execution.progress }}</pre>
          </v-card>
        </div>
      </v-card-text>
      <v-card-text v-else class="text-center py-4 text-medium-emphasis">
        No execution selected
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn color="primary" @click="close">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { api } from '@/services/api'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  execution: { type: Object, default: null }
})

const emit = defineEmits(['update:modelValue'])

const isOpen = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const job = ref(null)

// Fetch job details when execution changes
watch(() => props.execution, async (newExecution) => {
  if (newExecution?.job_id) {
    try {
      const response = await api.get(`/jobs/${newExecution.job_id}`)
      job.value = response.data
    } catch (error) {
      console.error('[AgentDetailsModal] Failed to fetch job:', error)
      job.value = null
    }
  } else {
    job.value = null
  }
}, { immediate: true })

function close() {
  isOpen.value = false
}
</script>

<style scoped>
.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-label {
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.6);
  font-weight: 500;
}

.info-value {
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
  background: rgba(255, 255, 255, 0.1);
  padding: 4px 8px;
  border-radius: 4px;
  word-break: break-all;
}

.mission-text,
.progress-text {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: 'Roboto Mono', monospace;
  font-size: 13px;
  line-height: 1.5;
  color: rgba(255, 255, 255, 0.9);
  margin: 0;
  max-height: 300px;
  overflow-y: auto;
}
</style>
```

**Acceptance Criteria**:
- [ ] Modal displays when execution is selected
- [ ] Shows both agent_id and job_id (full UUIDs, not truncated)
- [ ] Displays instance_number as chip badge
- [ ] Fetches and displays mission from job (not execution)
- [ ] All fields have data-testid attributes
- [ ] Close button works correctly

---

### 4. API Endpoint: GET /jobs/{job_id}/executions
**File**: `api/endpoints/jobs.py`
**Location**: Add new endpoint after existing job endpoints (~line 150)

**Implementation**:
```python
@router.get("/{job_id}/executions", response_model=List[AgentExecutionResponse])
async def get_job_executions(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[AgentExecutionResponse]:
    """
    Get all agent execution instances for a specific job.

    Returns list of AgentExecution records sorted by instance_number ascending.
    Used by frontend to display execution history and succession timeline.

    Handover 0366d-1: Frontend Core Agent Display
    """
    # Verify job exists and user has access (tenant isolation)
    result = await db.execute(
        select(AgentJob).where(
            AgentJob.job_id == job_id,
            AgentJob.tenant_key == current_user.tenant_key
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Fetch all executions for this job
    result = await db.execute(
        select(AgentExecution)
        .where(AgentExecution.job_id == job_id)
        .order_by(AgentExecution.instance_number.asc())
    )
    executions = result.scalars().all()

    return [
        AgentExecutionResponse(
            agent_id=exec.agent_id,
            job_id=exec.job_id,
            instance_number=exec.instance_number,
            status=exec.status,
            progress=exec.progress,
            spawned_by=exec.spawned_by,
            succeeded_by=exec.succeeded_by,
            created_at=exec.created_at,
            updated_at=exec.updated_at
        )
        for exec in executions
    ]
```

**Required Imports** (add to top of file):
```python
from src.giljo_mcp.models import AgentExecution
from src.giljo_mcp.schemas.agent_execution import AgentExecutionResponse
```

**Acceptance Criteria**:
- [ ] Endpoint returns list of executions for job
- [ ] Results sorted by instance_number ascending
- [ ] Multi-tenant isolation enforced (tenant_key check)
- [ ] Returns 404 if job not found
- [ ] Response includes all required fields (agent_id, job_id, instance_number, status, etc.)

---

## NOT In Scope (EXPLICIT)

The following are EXPLICITLY OUT OF SCOPE for this handover. They will be handled in separate handovers:

### ❌ Out of Scope - 0366d-2: Message Components
- MessageAuditModal.vue updates
- Message count calculations for executions
- WebSocket message routing for agent_id vs job_id

### ❌ Out of Scope - 0366d-3: Launch & Succession
- LaunchTab.vue updates
- LaunchSuccessorDialog.vue updates
- SuccessionTimeline.vue component creation
- Succession visualization features

### ❌ Out of Scope - 0366d-4: Installation & Migration
- Database migration scripts
- Installation flow updates
- Fresh install vs upgrade detection

### ❌ Out of Scope - General
- Comprehensive E2E test suites (only add simple tests for columns)
- Refactoring existing code not directly related to ID display
- New features not explicitly listed in "In Scope" section
- Performance optimizations beyond basic display
- Backend service layer changes (already done in 0366c)

---

## Testing Requirements

**Minimal E2E Test** (add to `tests/e2e/test_jobs_tab.spec.js`):
```javascript
test('JobsTab displays both agent_id and job_id columns', async ({ page }) => {
  await page.goto('/projects/test-project')
  await page.click('[data-testid="jobs-tab"]')

  // Verify both ID columns exist
  await expect(page.locator('[data-testid="agent-id"]').first()).toBeVisible()
  await expect(page.locator('[data-testid="job-id"]').first()).toBeVisible()
  await expect(page.locator('[data-testid="instance-number"]').first()).toBeVisible()
})
```

**Manual Testing Checklist**:
1. Navigate to Jobs tab in project view
2. Verify both agent_id and job_id columns display
3. Verify instance number displays as chip badge
4. Click on agent row to open AgentDetailsModal
5. Verify modal shows full UUIDs and mission
6. Close modal and verify no console errors

---

## Estimated Effort

**Total Duration**: 3-4 hours

**Breakdown**:
- JobsTab.vue updates: 1 hour
- AgentTableView.vue updates: 45 minutes
- AgentDetailsModal.vue creation: 1 hour
- API endpoint implementation: 45 minutes
- Testing & validation: 30 minutes

---

## Success Metrics

**Measurable Outcomes**:
1. ✅ Jobs tab displays 3 ID-related columns (agent_id, job_id, instance_number)
2. ✅ AgentDetailsModal shows both IDs and fetches mission from job
3. ✅ API endpoint returns execution list with all required fields
4. ✅ Simple E2E test passes
5. ✅ No console errors when viewing Jobs tab
6. ✅ All data-testid attributes present for future testing

**Acceptance**: All 4 files updated, all acceptance criteria met, simple E2E test passes.

---

## References

**Related Handovers**:
- 0366a: AgentJob + AgentExecution dual-model architecture
- 0366b: Service layer implementation (message_service_0366b.py)
- 0366c: Backend refactoring (RED phase tests)

**Key Files**:
- Backend Models: `src/giljo_mcp/models/agent_identity.py` (AgentJob, AgentExecution)
- Schemas: `src/giljo_mcp/schemas/agent_execution.py` (AgentExecutionResponse)
- Service: `src/giljo_mcp/services/message_service_0366b.py` (execution queries)

**Documentation**:
- Migration Guide: `handovers/0366c_context_tools_agent_id_red_phase.md` (sections 5-6)
- Test Strategy: `tests/tools/TEST_AGENT_STATUS_0366c_README.md`

---

## Notes

**Lessons from 0366c**:
- ❌ 0366c was too vague ("update context tools") → scope creep, 8+ files touched
- ✅ 0366d-1 is EXPLICIT (4 files, specific line numbers, measurable criteria)
- ✅ Clear boundaries prevent feature drift
- ✅ Separate handovers for related work (messages, launch, succession, installation)

**Key Constraint**: This handover focuses ONLY on displaying the dual-identifier system in the core UI. All other features (messages, launch, succession, installation) are handled in separate, equally scoped handovers.

---

## Handover Complete

This specification is ready for execution by the Frontend Tester agent. All changes are scoped, measurable, and have clear acceptance criteria.
