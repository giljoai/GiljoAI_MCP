# Handover 0366d: Agent Identity Refactor - Phase D (Frontend Integration and Seeding)

**Date**: 2025-12-19
**Phase**: D of 4 (Final Phase)
**Status**: Ready for Execution
**Estimated Duration**: 12-16 hours
**TDD Approach**: RED → GREEN → REFACTOR
**Dependencies**: Phase A (0366a), Phase B (0366b), Phase C (0366c) MUST be complete

---

## Prerequisites & Reference Documents

**MUST READ before starting this phase:**

1. **Master Roadmap**: `handovers/0366_agent_identity_refactor_roadmap.md`
   - Executive summary, phase dependencies, success criteria

2. **All Previous Phases**: Verify A, B, C are complete
   - `handovers/0366a_schema_and_models.md` (models + migration)
   - `handovers/0366b_service_layer_updates.md` (services)
   - `handovers/0366c_mcp_tool_standardization.md` (MCP tools)

3. **UUID Index**: `handovers/Reference_docs/UUID_INDEX_0366.md`
   - Frontend files to modify (JobsTab, LaunchTab, AgentTableView, etc.)
   - Install/seeding files (install.py, template_seeder.py)

4. **Database Schema Map**: `handovers/Reference_docs/DATABASE_SCHEMA_MAP_0366.md`
   - Frontend data structure expectations

5. **Project Context**: `F:\GiljoAI_MCP\CLAUDE.md`
   - Vue 3 patterns, composable structure, WebSocket events

---

## Objective

Update the frontend UI and installation seeding scripts to:
1. Display agent identity correctly (separate job_id from agent_id)
2. Show succession chains visually (lineage of executions on same job)
3. Seed new schema with sample data (jobs + executions)
4. Ensure E2E workflows function correctly with dual-model architecture

This is the **final phase** - after completion, the 0366 refactor is production-ready.

---

## Frontend Components to Update

### Priority 1: Core Agent Display
1. **JobsTab.vue** - Agent status board (shows executions, not jobs)
2. **AgentTableView.vue** - Reusable agent table component
3. **AgentDetailsModal.vue** - Agent detail view (show job_id + agent_id)
4. **SuccessionTimeline.vue** - Succession visualization (execution chain)

### Priority 2: Messaging Components
5. **MessageStream.vue** - Message list (display sender/receiver agent_id)
6. **MessageInput.vue** - Message composer (target agent_id)
7. **MessageDetailView.vue** - Message detail modal
8. **MessageAuditModal.vue** - Message audit log

### Priority 3: Launch and Coordination
9. **LaunchTab.vue** - Project launch interface
10. **LaunchSuccessorDialog.vue** - Handover dialog
11. **AgentMissionEditModal.vue** - Mission editor (job-level, not execution)

---

## Installation Scripts to Update

### 1. **install.py** - Main installer
- Update seeding logic to create jobs + executions
- Preserve existing migration run (don't re-run 0366a)
- Seed sample succession chains for demo

### 2. **template_seeder.py** - Template seeding
- Update agent template references (job_id → agent_id where appropriate)
- Preserve template structure (templates define jobs, not executions)

---

## TDD Approach (MANDATORY)

### Phase 1: RED (30-40% of time) - Write Failing E2E Tests FIRST

#### `tests/e2e/test_agent_display_0366d.spec.js` (Playwright)
```javascript
/**
 * E2E tests for agent display with new identity model.
 * These tests MUST be written FIRST (TDD RED phase).
 */
import { test, expect } from '@playwright/test';

test.describe('Agent Display - Identity Model', () => {
  test('JobsTab displays agent_id and job_id separately', async ({ page }) => {
    // Navigate to project jobs tab
    await page.goto('http://localhost:5173/projects/test-project-123');
    await page.click('button:has-text("Jobs")');

    // Wait for agent table to load
    await page.waitForSelector('[data-testid="agent-table"]');

    // Verify first agent row shows both IDs
    const firstRow = page.locator('[data-testid="agent-row"]').first();

    // Agent ID column (executor UUID)
    const agentIdCell = firstRow.locator('[data-testid="agent-id"]');
    await expect(agentIdCell).toContainText(/^[a-f0-9-]{36}$/); // UUID format

    // Job ID column (work order UUID)
    const jobIdCell = firstRow.locator('[data-testid="job-id"]');
    await expect(jobIdCell).toContainText(/^[a-f0-9-]{36}$/);

    // Verify they are DIFFERENT
    const agentId = await agentIdCell.textContent();
    const jobId = await jobIdCell.textContent();
    expect(agentId).not.toBe(jobId);
  });

  test('Succession timeline shows execution chain on same job', async ({ page }) => {
    // Navigate to project with succession history
    await page.goto('http://localhost:5173/projects/test-project-123');

    // Open succession timeline
    await page.click('button:has-text("Succession Timeline")');

    // Wait for timeline to render
    await page.waitForSelector('[data-testid="succession-timeline"]');

    // Verify multiple executions shown
    const executions = page.locator('[data-testid="execution-node"]');
    await expect(executions).toHaveCount(3); // 3 executions in chain

    // Verify all share SAME job_id
    const jobIds = await executions.locator('[data-testid="job-id"]').allTextContents();
    const uniqueJobIds = [...new Set(jobIds)];
    expect(uniqueJobIds).toHaveLength(1); // Only 1 unique job_id

    // Verify different agent_ids
    const agentIds = await executions.locator('[data-testid="agent-id"]').allTextContents();
    const uniqueAgentIds = [...new Set(agentIds)];
    expect(uniqueAgentIds).toHaveLength(3); // 3 unique agent_ids
  });

  test('Agent details modal shows job mission (not duplicated)', async ({ page }) => {
    await page.goto('http://localhost:5173/projects/test-project-123');

    // Click agent row to open details
    await page.click('[data-testid="agent-row"]');

    // Wait for modal
    await page.waitForSelector('[data-testid="agent-details-modal"]');

    // Verify mission displayed (from job, not execution)
    const missionSection = page.locator('[data-testid="mission-section"]');
    await expect(missionSection).toContainText('Build authentication system');

    // Verify execution-specific fields shown
    await expect(page.locator('[data-testid="instance-number"]')).toContainText('Instance: 2');
    await expect(page.locator('[data-testid="progress"]')).toContainText('Progress: 75%');
  });
});
```

#### `tests/e2e/test_messaging_0366d.spec.js`
```javascript
/**
 * E2E tests for messaging with agent_id routing.
 * These tests MUST be written FIRST (TDD RED phase).
 */
import { test, expect } from '@playwright/test';

test.describe('Messaging - Agent ID Routing', () => {
  test('Message composer targets agent_id (not job_id)', async ({ page }) => {
    await page.goto('http://localhost:5173/projects/test-project-123');

    // Open message composer
    await page.click('button:has-text("Send Message")');

    // Select recipient from dropdown
    await page.click('[data-testid="recipient-select"]');

    // Verify dropdown shows agent_id (executor UUIDs)
    const options = page.locator('[data-testid="recipient-option"]');
    const firstOption = options.first();
    const optionText = await firstOption.textContent();

    // Format: "Analyzer Agent (agent-abc-123)"
    expect(optionText).toMatch(/\(agent-[a-f0-9-]{36}\)/);

    // Select recipient
    await firstOption.click();

    // Type message
    await page.fill('[data-testid="message-input"]', 'Please review the code');

    // Send
    await page.click('button:has-text("Send")');

    // Verify success notification
    await expect(page.locator('.v-snackbar')).toContainText('Message sent successfully');
  });

  test('Message stream displays sender and receiver agent_ids', async ({ page }) => {
    await page.goto('http://localhost:5173/projects/test-project-123');

    // Open message stream
    await page.click('button:has-text("Messages")');

    // Wait for messages to load
    await page.waitForSelector('[data-testid="message-list"]');

    // Verify first message shows agent_ids
    const firstMessage = page.locator('[data-testid="message-item"]').first();

    // From field shows sender agent_id
    const fromField = firstMessage.locator('[data-testid="message-from"]');
    await expect(fromField).toContainText(/agent-[a-f0-9-]{36}/);

    // To field shows receiver agent_id
    const toField = firstMessage.locator('[data-testid="message-to"]');
    await expect(toField).toContainText(/agent-[a-f0-9-]{36}/);
  });
});
```

#### `tests/e2e/test_succession_workflow_0366d.spec.js`
```javascript
/**
 * E2E test for full succession workflow.
 * This test validates the entire 0366 refactor end-to-end.
 */
import { test, expect } from '@playwright/test';

test.describe('Succession Workflow - End-to-End', () => {
  test('Complete succession workflow preserves job context', async ({ page }) => {
    // Setup: Create project and orchestrator
    await page.goto('http://localhost:5173/projects/new');
    await page.fill('[data-testid="project-name"]', 'E2E Succession Test');
    await page.click('button:has-text("Create")');

    // Wait for project creation
    await page.waitForSelector('[data-testid="project-view"]');

    // Navigate to Jobs tab
    await page.click('button:has-text("Jobs")');

    // Verify initial orchestrator created (execution 1)
    const agentTable = page.locator('[data-testid="agent-table"]');
    await expect(agentTable.locator('[data-testid="agent-row"]')).toHaveCount(1);

    // Capture initial job_id and agent_id
    const initialRow = agentTable.locator('[data-testid="agent-row"]').first();
    const initialJobId = await initialRow.locator('[data-testid="job-id"]').textContent();
    const initialAgentId = await initialRow.locator('[data-testid="agent-id"]').textContent();

    // Trigger succession (via UI button)
    await initialRow.click(); // Open details
    await page.click('button:has-text("Hand Over")');

    // Confirm succession dialog
    await page.fill('[data-testid="handover-reason"]', 'Manual handover for testing');
    await page.click('button:has-text("Confirm Handover")');

    // Wait for successor to appear
    await page.waitForSelector('[data-testid="agent-row"]', { state: 'attached', timeout: 5000 });

    // Verify TWO executions now visible
    await expect(agentTable.locator('[data-testid="agent-row"]')).toHaveCount(2);

    // Capture successor details
    const successorRow = agentTable.locator('[data-testid="agent-row"]').nth(1);
    const successorJobId = await successorRow.locator('[data-testid="job-id"]').textContent();
    const successorAgentId = await successorRow.locator('[data-testid="agent-id"]').textContent();

    // CRITICAL ASSERTIONS:
    // 1. SAME job_id (work persists)
    expect(successorJobId).toBe(initialJobId);

    // 2. DIFFERENT agent_id (new executor)
    expect(successorAgentId).not.toBe(initialAgentId);

    // 3. Instance number incremented
    await expect(successorRow.locator('[data-testid="instance-number"]')).toContainText('2');

    // 4. Succession chain visible in timeline
    await page.click('button:has-text("Succession Timeline")');
    const timeline = page.locator('[data-testid="succession-timeline"]');

    // Verify chain: exec1 → exec2
    const nodes = timeline.locator('[data-testid="execution-node"]');
    await expect(nodes).toHaveCount(2);

    // Verify connection line between nodes
    await expect(timeline.locator('[data-testid="succession-line"]')).toBeVisible();
  });
});
```

### Phase 2: GREEN (40-50% of time) - Update Frontend Components

#### Update `JobsTab.vue`
```vue
<template>
  <v-card>
    <v-card-title>Agent Executions</v-card-title>
    <AgentTableView
      :executions="agentExecutions"
      @row-click="showAgentDetails"
    />
  </v-card>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import AgentTableView from '@/components/orchestration/AgentTableView.vue';
import { useAgentStore } from '@/stores/agent';

const agentStore = useAgentStore();
const agentExecutions = ref([]);

onMounted(async () => {
  // Fetch agent executions (not jobs)
  const result = await agentStore.fetchExecutions(projectId);
  agentExecutions.value = result.executions;
});

function showAgentDetails(execution) {
  // Show modal with execution + job details
  // execution.agent_id = executor UUID
  // execution.job_id = work order UUID
  // execution.job.mission = mission text (from job, not execution)
}
</script>
```

#### Update `AgentTableView.vue`
```vue
<template>
  <v-data-table
    :items="executions"
    :headers="headers"
    data-testid="agent-table"
  >
    <template v-slot:item.agent_id="{ item }">
      <span data-testid="agent-id" class="text-monospace">
        {{ item.agent_id.substring(0, 8) }}...
      </span>
    </template>

    <template v-slot:item.job_id="{ item }">
      <span data-testid="job-id" class="text-monospace">
        {{ item.job_id.substring(0, 8) }}...
      </span>
    </template>

    <template v-slot:item.instance_number="{ item }">
      <v-chip size="small" data-testid="instance-number">
        Instance {{ item.instance_number }}
      </v-chip>
    </template>
  </v-data-table>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  executions: {
    type: Array,
    required: true,
  },
});

const headers = [
  { title: 'Agent ID', key: 'agent_id', sortable: true },
  { title: 'Job ID', key: 'job_id', sortable: true },
  { title: 'Type', key: 'agent_type', sortable: true },
  { title: 'Instance', key: 'instance_number', sortable: true },
  { title: 'Status', key: 'status', sortable: true },
  { title: 'Progress', key: 'progress', sortable: true },
];
</script>
```

#### Update `MessageInput.vue`
```vue
<template>
  <v-card>
    <v-card-title>Send Message</v-card-title>
    <v-card-text>
      <v-select
        v-model="selectedRecipient"
        :items="availableAgents"
        item-title="displayName"
        item-value="agent_id"
        label="Recipient"
        data-testid="recipient-select"
      >
        <template v-slot:item="{ item }">
          <div data-testid="recipient-option">
            {{ item.agent_type }} Agent ({{ item.agent_id.substring(0, 12) }}...)
          </div>
        </template>
      </v-select>

      <v-textarea
        v-model="messageContent"
        label="Message"
        data-testid="message-input"
      />

      <v-btn @click="sendMessage">Send</v-btn>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useMessageStore } from '@/stores/message';

const messageStore = useMessageStore();
const availableAgents = ref([]);
const selectedRecipient = ref(null); // Will be agent_id (UUID)
const messageContent = ref('');

onMounted(async () => {
  // Fetch available agent EXECUTIONS (not jobs)
  const result = await fetch(`/api/projects/${projectId}/executions`);
  const data = await result.json();
  availableAgents.value = data.executions.map(exec => ({
    agent_id: exec.agent_id,
    agent_type: exec.agent_type,
    displayName: `${exec.agent_type} (Instance ${exec.instance_number})`,
  }));
});

async function sendMessage() {
  await messageStore.sendMessage({
    to_agent_id: selectedRecipient.value, // Agent executor UUID
    content: messageContent.value,
    from_agent_id: currentAgentId, // Sender executor UUID
  });
}
</script>
```

#### Update `SuccessionTimeline.vue`
```vue
<template>
  <v-card data-testid="succession-timeline">
    <v-card-title>Succession Timeline</v-card-title>
    <v-card-text>
      <div class="timeline-container">
        <div
          v-for="(execution, index) in executions"
          :key="execution.agent_id"
          class="timeline-node"
          data-testid="execution-node"
        >
          <!-- Execution card -->
          <v-card variant="outlined">
            <v-card-title>
              Instance {{ execution.instance_number }}
            </v-card-title>
            <v-card-subtitle>
              <div data-testid="agent-id">Agent: {{ execution.agent_id }}</div>
              <div data-testid="job-id">Job: {{ execution.job_id }}</div>
            </v-card-subtitle>
            <v-card-text>
              <div>Status: {{ execution.status }}</div>
              <div>Progress: {{ execution.progress }}%</div>
            </v-card-text>
          </v-card>

          <!-- Connection line to next execution -->
          <div
            v-if="index < executions.length - 1"
            class="succession-line"
            data-testid="succession-line"
          />
        </div>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, onMounted } from 'vue';

const props = defineProps({
  jobId: {
    type: String,
    required: true,
  },
});

const executions = ref([]);

onMounted(async () => {
  // Fetch ALL executions for this job (succession chain)
  const result = await fetch(`/api/jobs/${props.jobId}/executions`);
  const data = await result.json();
  executions.value = data.executions.sort((a, b) => a.instance_number - b.instance_number);
});
</script>

<style scoped>
.timeline-container {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.timeline-node {
  position: relative;
}

.succession-line {
  position: absolute;
  left: 50%;
  width: 2px;
  height: 2rem;
  background: var(--v-primary-base);
  transform: translateX(-50%);
}
</style>
```

### Phase 3: Update Installation Seeding

#### Update `install.py`
```python
"""
GiljoAI MCP Installation Script with Agent Identity Model.

Handover 0366d: Seeds new schema (agent_jobs + agent_executions).
"""

def seed_sample_data(session):
    """Seed sample jobs and executions for demo."""
    from src.giljo_mcp.models import AgentJob, AgentExecution
    from uuid import uuid4
    from datetime import datetime, timezone

    # Create sample job
    job = AgentJob(
        job_id=str(uuid4()),
        tenant_key="demo-tenant",
        project_id="demo-project-123",
        mission="Build authentication system with JWT tokens and role-based access control",
        job_type="orchestrator",
        status="active",
        job_metadata={
            "field_priorities": {"vision_documents": 1, "tech_stack": 1},
            "depth_config": {"vision_documents": "medium"},
        }
    )
    session.add(job)

    # Create execution 1 (completed)
    exec1 = AgentExecution(
        agent_id=str(uuid4()),
        job_id=job.job_id,
        tenant_key="demo-tenant",
        agent_type="orchestrator",
        instance_number=1,
        status="complete",
        progress=100,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        context_used=135000,
        context_budget=150000,
        succeeded_by=None,  # Will be set when exec2 created
    )
    session.add(exec1)

    # Create execution 2 (current)
    exec2 = AgentExecution(
        agent_id=str(uuid4()),
        job_id=job.job_id,  # SAME job
        tenant_key="demo-tenant",
        agent_type="orchestrator",
        instance_number=2,
        status="working",
        progress=45,
        started_at=datetime.now(timezone.utc),
        spawned_by=exec1.agent_id,
        context_used=50000,
        context_budget=150000,
    )
    session.add(exec2)

    # Link succession chain
    exec1.succeeded_by = exec2.agent_id

    session.commit()
    print(f"✓ Seeded sample job {job.job_id} with 2 executions")
```

### Phase 4: REFACTOR (10-20% of time) - E2E Integration Tests

- Run full E2E test suite (Playwright)
- Verify dashboard loads correctly with new schema
- Test succession workflow end-to-end
- Test messaging workflow (send → receive → acknowledge)
- Performance test (load time, query speed)

---

## API Endpoint Updates (if needed)

### New Endpoint: Get Job Executions
```python
# api/endpoints/jobs.py

@router.get("/jobs/{job_id}/executions")
async def get_job_executions(
    job_id: str,
    tenant_key: str = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Get all executions for a job (succession chain)."""
    from sqlalchemy import select
    from src.giljo_mcp.models import AgentExecution

    result = await session.execute(
        select(AgentExecution).where(
            AgentExecution.job_id == job_id,
            AgentExecution.tenant_key == tenant_key
        ).order_by(AgentExecution.instance_number)
    )
    executions = result.scalars().all()

    return {
        "success": True,
        "job_id": job_id,
        "executions": [
            {
                "agent_id": exec.agent_id,
                "instance_number": exec.instance_number,
                "status": exec.status,
                "progress": exec.progress,
                "spawned_by": exec.spawned_by,
                "succeeded_by": exec.succeeded_by,
            }
            for exec in executions
        ]
    }
```

---

## Validation Checklist

Before marking Phase D complete (FINAL PHASE):

- [ ] All E2E tests pass (Playwright suite)
- [ ] Dashboard displays agent_id and job_id correctly
- [ ] Succession timeline shows execution chain visually
- [ ] Messaging targets agent_id (precise delivery)
- [ ] install.py seeds new schema successfully
- [ ] Fresh installation completes in <60 seconds
- [ ] No breaking changes for existing users (migration path clear)
- [ ] Performance benchmarks meet targets (dashboard load <2s)
- [ ] Documentation updated (user guides, API docs)

---

## Kickoff Prompt

Copy and paste this prompt to start a fresh session for Phase D:

---

**Mission**: Implement Handover 0366d - Frontend integration and installation seeding for agent identity model

**Context**: You are the Frontend Tester Agent working on GiljoAI MCP Server. Phase A (0366a), Phase B (0366b), and Phase C (0366c) are complete - backend is fully refactored. Your mission is to update the Vue 3 frontend and installation scripts to work with the new dual-model architecture.

**TDD Approach** (MANDATORY):
1. **RED** (30-40% time): Write ALL E2E tests FIRST (Playwright)
2. **GREEN** (40-50% time): Update frontend components to pass tests
3. **REFACTOR** (10-20% time): Polish UI, optimize seeding, integration tests

**Components to Update**:
- Priority 1: JobsTab.vue, AgentTableView.vue, SuccessionTimeline.vue
- Priority 2: MessageStream.vue, MessageInput.vue, MessageDetailView.vue
- Priority 3: LaunchTab.vue, LaunchSuccessorDialog.vue, AgentDetailsModal.vue

**Test Files to Create** (RED phase):
- `tests/e2e/test_agent_display_0366d.spec.js`
- `tests/e2e/test_messaging_0366d.spec.js`
- `tests/e2e/test_succession_workflow_0366d.spec.js`

**Success Criteria**:
- All E2E tests pass (Playwright)
- Dashboard displays agent_id + job_id correctly
- Succession workflow preserves job context
- Fresh installation seeds new schema

**Reference**: Read `handovers/0366d_frontend_integration_seeding.md` for complete specifications.

**Environment**:
- Vue 3 + Vuetify
- Playwright for E2E testing
- PostgreSQL 18 with Phase A+B+C complete

**First Step**: Create `tests/e2e/test_agent_display_0366d.spec.js` with failing tests (RED phase).

---

**Estimated Duration**: 12-16 hours
**Priority**: CRITICAL - Final phase of 0366 refactor
**Status**: Ready for execution (after Phase A+B+C complete)
