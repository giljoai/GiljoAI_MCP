# Handover 0366d-3: Frontend Launch & Succession Components

**Date**: 2025-12-20
**Phase**: D-3 of Agent Identity Refactor
**Status**: Ready for Execution
**Estimated Duration**: 3-4 hours
**Dependencies**: 0366a (models), 0366b (services), 0366c (MCP tools + RED phase)

---

## Objective

Update 4 specific frontend components to correctly display agent identity in the launch and succession workflows. This handover focuses ONLY on:

1. **SuccessionTimeline.vue** - Visualize execution chains
2. **LaunchTab.vue** - Minor updates for agent_id display
3. **LaunchSuccessorDialog.vue** - Handover dialog updates
4. **AgentMissionEditModal.vue** - Mission editing (job-level)

**SCOPE BOUNDARY**: This handover does NOT include:
- ❌ JobsTab.vue (covered in 0366d-1)
- ❌ Message components (covered in 0366d-2)
- ❌ Backend succession logic (completed in 0366c)
- ❌ New succession features (out of scope)
- ❌ Auto-succession triggers (out of scope)
- ❌ Comprehensive test suites (only 1 E2E test required)

---

## Prerequisites

**MUST READ**:
1. `handovers/0366_agent_identity_refactor_roadmap.md` - Master roadmap
2. `handovers/0366a_schema_and_models.md` - Database schema (AgentJob vs AgentExecution)
3. `handovers/0366c_context_tools_agent_id_red_phase.md` - Semantic principles

**Key Semantic Principles**:
- **`job_id`** = Work order UUID (the WHAT - persistent across succession)
- **`agent_id`** = Executor UUID (the WHO - specific instance, resets on succession)
- **`instance_number`** = Execution sequence (1, 2, 3...) on same job
- **Mission** = Stored on `AgentJob` (not duplicated per execution)
- **Context window** = Per-execution (`AgentExecution.context_used`, `context_budget`)

---

## Component 1: SuccessionTimeline.vue

**File**: `frontend/src/components/projects/SuccessionTimeline.vue`

### Current State Analysis

**Existing Implementation** (from Handover 0509):
- ✅ Displays orchestrator instances in timeline format
- ✅ Shows context usage, handover summaries, succession reasons
- ✅ Fetches data via `api.agentJobs.list(projectId)`
- ❌ **BUG**: Filters for `agent_type=orchestrator` (wrong filter)
- ❌ **BUG**: Uses `instance.id` as key (should use `agent_id`)
- ❌ **Missing**: job_id display (only shows agent_id implicitly)
- ❌ **Missing**: Instance number display clarity (shows "Instance X" but not agent_id)

### Required Changes

#### 1. Fix Data Fetching (Line 114-119)

**Current (WRONG)**:
```javascript
const response = await api.agentJobs.list(props.projectId)

// Filter orchestrators and sort by instance_number
instances.value = response.data
  .filter((job) => job.agent_type === 'orchestrator')
  .sort((a, b) => (a.instance_number || 1) - (b.instance_number || 1))
```

**Fixed (CORRECT)**:
```javascript
// NEW: Fetch agent executions (not jobs)
const response = await api.agentExecutions.list(props.jobId)

// Sort by instance_number ascending
instances.value = response.data
  .sort((a, b) => (a.instance_number || 1) - (b.instance_number || 1))
```

**Rationale**: SuccessionTimeline should show executions on a SINGLE job, not all jobs in a project.

#### 2. Update Props (Line 97-101)

**Current (WRONG)**:
```javascript
props: {
  projectId: {
    type: String,
    required: true,
  },
}
```

**Fixed (CORRECT)**:
```javascript
props: {
  jobId: {
    type: String,
    required: true,
    validator: (val) => /^[a-f0-9-]{36}$/.test(val), // UUID format
  },
}
```

#### 3. Add agent_id Display (Line 23)

**Current (MISSING)**:
```vue
<v-card-title class="text-subtitle-2">
  <v-chip :color="getStatusColor(instance)" size="small" class="mr-2">
    {{ instance.status }}
  </v-chip>
  {{ instance.agent_name }}
</v-card-title>
```

**Fixed (ADD agent_id)**:
```vue
<v-card-title class="text-subtitle-2">
  <v-chip :color="getStatusColor(instance)" size="small" class="mr-2">
    {{ instance.status }}
  </v-chip>
  {{ instance.agent_type || 'Agent' }}
  <div class="text-caption text-medium-emphasis mt-1">
    Agent ID: <code data-testid="agent-id">{{ instance.agent_id }}</code>
  </div>
</v-card-title>
```

#### 4. Add job_id Display (NEW Section)

**Location**: After succession reason chip (Line 52)

```vue
<!-- Job ID Display (shared across all executions) -->
<div v-if="instances.length > 0" class="mt-2">
  <v-chip size="small" variant="outlined" prepend-icon="mdi-briefcase">
    Job: <code class="ml-1" data-testid="job-id">{{ instances[0].job_id }}</code>
  </v-chip>
</div>
```

**Rationale**: All executions share the same job_id - display it once at the top.

#### 5. Add data-testid Attributes

**Add to timeline container** (Line 2):
```vue
<v-card class="succession-timeline" data-testid="succession-timeline">
```

**Add to timeline item** (Line 7):
```vue
<v-timeline-item
  v-for="(instance, index) in instances"
  :key="instance.agent_id"
  data-testid="execution-node"
  :data-agent-id="instance.agent_id"
  :data-job-id="instance.job_id"
  :dot-color="getStatusColor(instance)"
  :icon="index === instances.length - 1 ? 'mdi-account-circle' : 'mdi-check'"
  size="small"
>
```

#### 6. Update Component Documentation (Line 86-92)

```javascript
/**
 * SuccessionTimeline.vue - Handover 0366d-3 (updated from 0509)
 * Displays agent execution chain for a single job.
 *
 * Props:
 * - jobId: str (REQUIRED) - Job UUID to fetch execution history
 *
 * Fetches all executions for job via api.agentExecutions.list(jobId)
 * Each execution shows: agent_id, instance_number, status, context usage, handover reason
 */
```

### Testing Requirements

**Manual Test**:
1. Open project with succession history
2. View succession timeline
3. Verify:
   - All executions show same job_id
   - Each execution has unique agent_id
   - Instance numbers increment (1, 2, 3...)
   - Context usage displays correctly
   - Timeline scrolls smoothly

---

## Component 2: LaunchTab.vue

**File**: `frontend/src/components/projects/LaunchTab.vue`

### Current State Analysis

**Existing Implementation**:
- ✅ 3-panel layout (description, mission, agents)
- ✅ Orchestrator card displayed
- ✅ Agent team list
- ❌ **Missing**: agent_id display in orchestrator card
- ❌ **Missing**: instance_number display

### Required Changes

#### 1. Update Orchestrator Card (Line 63-80)

**Current (PARTIAL)**:
```vue
<div class="orchestrator-card">
  <v-avatar :color="orchestratorAvatarColor" size="40" class="agent-avatar">
    <span class="orchestrator-text">OR</span>
  </v-avatar>
  <span class="agent-name">ORCHESTRATOR</span>
  <v-icon size="small" class="eye-icon" title="View orchestrator details (read-only)">mdi-eye</v-icon>
  <v-icon
    size="small"
    class="info-icon"
    role="button"
    tabindex="0"
    title="View orchestrator template"
    @click="handleOrchestratorInfo"
    @keydown.enter="handleOrchestratorInfo"
  >
    mdi-information
  </v-icon>
</div>
```

**Fixed (ADD agent_id and instance_number)**:
```vue
<div class="orchestrator-card">
  <v-avatar :color="orchestratorAvatarColor" size="40" class="agent-avatar">
    <span class="orchestrator-text">OR</span>
  </v-avatar>
  <div class="orchestrator-info">
    <span class="agent-name">ORCHESTRATOR</span>
    <div v-if="currentOrchestrator" class="text-caption text-medium-emphasis">
      Instance #{{ currentOrchestrator.instance_number || 1 }} •
      ID: <code data-testid="orchestrator-agent-id">{{ currentOrchestrator.agent_id?.slice(0, 8) }}...</code>
    </div>
  </div>
  <v-icon size="small" class="eye-icon" title="View orchestrator details (read-only)">mdi-eye</v-icon>
  <v-icon
    size="small"
    class="info-icon"
    role="button"
    tabindex="0"
    title="View orchestrator template"
    @click="handleOrchestratorInfo"
    @keydown.enter="handleOrchestratorInfo"
  >
    mdi-information
  </v-icon>
</div>
```

#### 2. Add Computed Property for currentOrchestrator

**Location**: In `<script setup>` section after existing computed properties

```javascript
// Get current orchestrator execution (most recent instance)
const currentOrchestrator = computed(() => {
  if (!agents.value || agents.value.length === 0) return null

  // Find orchestrator jobs
  const orchestrators = agents.value
    .filter(agent => agent.agent_type === 'orchestrator')
    .sort((a, b) => (b.instance_number || 0) - (a.instance_number || 0))

  return orchestrators[0] || null
})
```

#### 3. Add CSS for Orchestrator Info

**Location**: `<style scoped>` section

```css
.orchestrator-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.orchestrator-info code {
  font-family: 'Roboto Mono', monospace;
  font-size: 0.7rem;
  background: rgba(0, 0, 0, 0.05);
  padding: 1px 4px;
  border-radius: 2px;
}
```

### Testing Requirements

**Manual Test**:
1. Open project in LaunchTab
2. Verify orchestrator card shows:
   - Instance number (e.g., "Instance #1")
   - Truncated agent_id (e.g., "ID: 3f2a1b4c...")
   - Tooltip on hover for full agent_id
3. Launch successor → verify instance number increments

---

## Component 3: LaunchSuccessorDialog.vue

**File**: `frontend/src/components/projects/LaunchSuccessorDialog.vue`

### Current State Analysis

**Existing Implementation** (from Handover 0509):
- ✅ Succession reason selection
- ✅ Context usage display
- ✅ Thin-client launch prompt generation
- ✅ Instance number calculation
- ❌ **UNCLEAR**: job_id vs agent_id relationship not explained
- ❌ **Missing**: Clarification that new agent_id is created

### Required Changes

#### 1. Clarify Dialog Title (Line 10-13)

**Current (UNCLEAR)**:
```vue
<v-card-title>
  Launch Successor Orchestrator
  <v-chip class="ml-2" size="small"> Instance {{ nextInstanceNumber }} </v-chip>
</v-card-title>
```

**Fixed (CLARIFIED)**:
```vue
<v-card-title>
  Launch Successor Orchestrator
  <v-chip class="ml-2" size="small" color="primary">
    Instance {{ nextInstanceNumber }}
  </v-chip>
</v-card-title>
```

#### 2. Update Alert Message (Line 16-19)

**Current (VAGUE)**:
```vue
<v-alert type="info" class="mb-4">
  This will create a new orchestrator instance ({{ nextInstanceNumber }}) to continue the
  mission with a fresh context window.
</v-alert>
```

**Fixed (EXPLICIT)**:
```vue
<v-alert type="info" class="mb-4" variant="tonal">
  <div class="text-subtitle-2 mb-2">Creating New Agent Execution</div>
  <ul class="text-body-2 pl-4">
    <li>✓ Same job_id ({{ currentJob.job_id?.slice(0, 8) }}...)</li>
    <li>✓ New agent_id (fresh execution)</li>
    <li>✓ Instance #{{ nextInstanceNumber }} in succession chain</li>
    <li>✓ Fresh context window (resets to 0 tokens)</li>
  </ul>
</v-alert>
```

#### 3. Add job_id to Current Instance Summary (Line 43)

**Current (MISSING job_id)**:
```vue
<div class="text-body-2">
  <div><strong>Instance:</strong> {{ currentJob.instance_number || 1 }}</div>
  <div><strong>Status:</strong> {{ currentJob.status }}</div>
  <div v-if="currentJob.context_used">
    <strong>Context Usage:</strong>
    {{ formatNumber(currentJob.context_used) }} /
    {{ formatNumber(currentJob.context_budget) }} tokens ({{
      Math.round(contextPercentage)
    }}%)
  </div>
</div>
```

**Fixed (ADD job_id and agent_id)**:
```vue
<div class="text-body-2">
  <div><strong>Job ID:</strong> <code data-testid="current-job-id">{{ currentJob.job_id }}</code></div>
  <div><strong>Agent ID:</strong> <code data-testid="current-agent-id">{{ currentJob.agent_id }}</code></div>
  <div><strong>Instance:</strong> {{ currentJob.instance_number || 1 }}</div>
  <div><strong>Status:</strong> {{ currentJob.status }}</div>
  <div v-if="currentJob.context_used">
    <strong>Context Usage:</strong>
    {{ formatNumber(currentJob.context_used) }} /
    {{ formatNumber(currentJob.context_budget) }} tokens ({{
      Math.round(contextPercentage)
    }}%)
  </div>
</div>
```

#### 4. Update CSS for Code Tags

**Location**: `<style scoped>` section (add if missing)

```css
code {
  font-family: 'Courier New', monospace;
  font-size: 0.85rem;
  background: rgba(0, 0, 0, 0.05);
  padding: 2px 6px;
  border-radius: 4px;
  word-break: break-all;
}

.text-body-2 ul {
  list-style: none;
  margin: 0;
}

.text-body-2 ul li {
  margin-bottom: 4px;
}
```

### Testing Requirements

**Manual Test**:
1. Open succession dialog
2. Verify alert clearly explains:
   - Same job_id maintained
   - New agent_id created
   - Instance number increments
   - Context resets
3. Verify current instance shows both job_id and agent_id
4. Trigger succession → verify prompt contains correct IDs

---

## Component 4: AgentMissionEditModal.vue

**File**: `frontend/src/components/projects/AgentMissionEditModal.vue`

### Current State Analysis

**Existing Implementation**:
- ✅ Mission editor with character counter
- ✅ Save/Reset functionality
- ✅ Validation rules
- ❌ **UNCLEAR**: Mission is job-level (not execution-level)
- ❌ **Missing**: job_id display in header
- ❌ **Missing**: Warning that changes affect all executions

### Required Changes

#### 1. Clarify Modal Header (Line 4-15)

**Current (UNCLEAR)**:
```vue
<v-card-title class="d-flex align-center">
  <v-icon class="mr-2" :color="agentColor">mdi-pencil</v-icon>
  Edit {{ agent?.agent_name || 'Agent' }} Mission
  <v-spacer />
  <v-chip size="small" class="mr-2">
    {{ characterCount.toLocaleString() }} chars
  </v-chip>
  <v-btn icon size="small" @click="handleClose" aria-label="Close">
    <v-icon>mdi-close</v-icon>
  </v-btn>
</v-card-title>
```

**Fixed (ADD job_id)**:
```vue
<v-card-title class="d-flex align-center">
  <v-icon class="mr-2" :color="agentColor">mdi-pencil</v-icon>
  Edit {{ agent?.agent_type || 'Agent' }} Mission
  <v-spacer />
  <div class="d-flex flex-column align-end mr-2">
    <v-chip size="small" variant="outlined">
      Job: <code data-testid="mission-job-id">{{ agent?.job_id?.slice(0, 8) }}...</code>
    </v-chip>
    <v-chip size="x-small" class="mt-1">
      {{ characterCount.toLocaleString() }} chars
    </v-chip>
  </div>
  <v-btn icon size="small" @click="handleClose" aria-label="Close">
    <v-icon>mdi-close</v-icon>
  </v-btn>
</v-card-title>
```

#### 2. Update Helper Alert (Line 51-62)

**Current (INCOMPLETE)**:
```vue
<v-alert type="info" variant="tonal" density="compact" class="mt-2">
  <div class="text-caption">
    <strong>Tips:</strong>
    <ul class="pl-4 mt-1">
      <li>This mission was generated by the orchestrator</li>
      <li>You can refine or adjust the instructions as needed</li>
      <li>Changes are saved to the database and visible to all users</li>
      <li>The agent will use this mission when launched</li>
    </ul>
  </div>
</v-alert>
```

**Fixed (ADD job-level warning)**:
```vue
<v-alert type="info" variant="tonal" density="compact" class="mt-2">
  <div class="text-caption">
    <strong>Important:</strong>
    <ul class="pl-4 mt-1">
      <li><strong>Mission is stored at JOB level</strong> (not per execution)</li>
      <li>Changes apply to ALL executions on job {{ agent?.job_id?.slice(0, 8) }}...</li>
      <li>If succession has occurred, all instances share this mission</li>
      <li>Original mission was generated by orchestrator</li>
      <li>You can refine or adjust as needed</li>
    </ul>
  </div>
</v-alert>
```

#### 3. Update Save API Call (Line 180)

**Current (CORRECT - no changes needed)**:
```javascript
const response = await apiClient.agentJobs.updateMission(props.agent.id, {
  mission: missionText.value,
})
```

**Verification**: API call uses `props.agent.id` which is the `job_id` (correct).

#### 4. Add Execution Count Display (NEW)

**Location**: Below helper alert

```vue
<!-- Execution Count (if succession has occurred) -->
<v-alert
  v-if="executionCount > 1"
  type="warning"
  variant="tonal"
  density="compact"
  class="mt-2"
>
  <div class="text-caption">
    <v-icon size="small" start>mdi-alert</v-icon>
    This job has <strong>{{ executionCount }} executions</strong> (succession has occurred).
    Mission changes will affect all instances.
  </div>
</v-alert>
```

**Add computed property**:
```javascript
const executionCount = computed(() => {
  return props.agent?.execution_count || 1
})
```

**Note**: Assumes backend provides `execution_count` field. If not available, can be omitted (low priority).

### Testing Requirements

**Manual Test**:
1. Open mission edit modal
2. Verify header shows job_id
3. Verify alert explains job-level storage
4. Edit mission → save
5. If succession occurred, verify warning appears
6. Close and reopen → verify changes persisted

---

## E2E Test Requirements

**File**: Create `tests/e2e/test_launch_succession_0366d3.spec.js` (Playwright)

```javascript
import { test, expect } from '@playwright/test'

test.describe('Launch & Succession Components - 0366d-3', () => {
  test('SuccessionTimeline shows execution chain correctly', async ({ page }) => {
    // Setup: Navigate to project with succession history
    await page.goto('http://localhost:5173/projects/test-project-123')
    await page.click('button:has-text("Succession Timeline")')

    // Wait for timeline to render
    await page.waitForSelector('[data-testid="succession-timeline"]')

    // Verify multiple executions shown
    const executions = page.locator('[data-testid="execution-node"]')
    const count = await executions.count()
    expect(count).toBeGreaterThan(1) // At least 2 executions (succession occurred)

    // Verify all share SAME job_id
    const jobId1 = await executions.nth(0).getAttribute('data-job-id')
    const jobId2 = await executions.nth(1).getAttribute('data-job-id')
    expect(jobId1).toBe(jobId2)

    // Verify different agent_ids
    const agentId1 = await executions.nth(0).getAttribute('data-agent-id')
    const agentId2 = await executions.nth(1).getAttribute('data-agent-id')
    expect(agentId1).not.toBe(agentId2)
  })

  test('LaunchTab displays orchestrator agent_id and instance', async ({ page }) => {
    await page.goto('http://localhost:5173/projects/test-project-123')

    // Verify orchestrator card shows agent_id
    const agentId = page.locator('[data-testid="orchestrator-agent-id"]')
    await expect(agentId).toBeVisible()
    await expect(agentId).toContainText(/^[a-f0-9]{8}\.\.\./)
  })

  test('LaunchSuccessorDialog clarifies job_id vs agent_id', async ({ page }) => {
    await page.goto('http://localhost:5173/projects/test-project-123')

    // Open succession dialog
    await page.click('button:has-text("Launch Successor")')

    // Verify current job_id shown
    const currentJobId = page.locator('[data-testid="current-job-id"]')
    await expect(currentJobId).toBeVisible()

    // Verify current agent_id shown
    const currentAgentId = page.locator('[data-testid="current-agent-id"]')
    await expect(currentAgentId).toBeVisible()

    // Verify alert explains new agent_id will be created
    await expect(page.locator('text=New agent_id (fresh execution)')).toBeVisible()
  })

  test('AgentMissionEditModal shows job_id in header', async ({ page }) => {
    await page.goto('http://localhost:5173/projects/test-project-123')

    // Open mission edit modal
    await page.click('[data-testid="edit-mission-btn"]')

    // Verify job_id displayed
    const jobId = page.locator('[data-testid="mission-job-id"]')
    await expect(jobId).toBeVisible()
    await expect(jobId).toContainText(/^[a-f0-9]{8}\.\.\./)

    // Verify alert explains job-level storage
    await expect(page.locator('text=Mission is stored at JOB level')).toBeVisible()
  })
})
```

**Test Execution**:
```bash
cd frontend
npm run test:e2e -- test_launch_succession_0366d3.spec.js
```

---

## API Endpoints (Assumed Available)

This handover assumes the following API endpoints exist (implemented in 0366b):

1. **`GET /api/agent-executions`** - List executions
   - Query param: `job_id` (filter by job)
   - Returns: `[{agent_id, job_id, instance_number, status, context_used, ...}]`

2. **`PUT /api/agent-jobs/:job_id/mission`** - Update mission
   - Body: `{mission: str}`
   - Returns: `{success: bool, job_id: str, mission: str}`

3. **`POST /api/agent-jobs/:job_id/trigger-succession`** - Trigger succession
   - Body: `{reason: str, notes: str}`
   - Returns: `{successor_job_id: str, agent_id: str, instance_number: int, launch_prompt: str}`

**If APIs missing**: Backend work required (out of scope for this handover).

---

## Acceptance Criteria

**MUST ALL PASS**:
- [ ] SuccessionTimeline correctly fetches executions by job_id
- [ ] SuccessionTimeline displays agent_id for each execution
- [ ] SuccessionTimeline shows job_id (shared across all executions)
- [ ] LaunchTab orchestrator card shows instance_number and agent_id
- [ ] LaunchSuccessorDialog alert clarifies job_id vs agent_id
- [ ] LaunchSuccessorDialog shows both IDs in current instance summary
- [ ] AgentMissionEditModal header shows job_id
- [ ] AgentMissionEditModal alert explains job-level storage
- [ ] E2E test passes (all 4 test cases green)
- [ ] No console errors on any component
- [ ] Manual test checklist completed

---

## Out of Scope (EXPLICIT)

This handover does NOT cover:
- ❌ JobsTab.vue updates (separate handover 0366d-1)
- ❌ Message component updates (separate handover 0366d-2)
- ❌ Backend API implementation (covered in 0366b)
- ❌ Database migrations (completed in 0366a)
- ❌ MCP tool changes (completed in 0366c)
- ❌ Auto-succession triggers (future enhancement)
- ❌ Comprehensive unit tests (1 E2E test sufficient for this scope)
- ❌ Performance optimization (functional correctness priority)

---

## Implementation Checklist

**TDD Approach**:
1. [ ] Write E2E test (RED phase)
2. [ ] Run test → verify failures
3. [ ] Update SuccessionTimeline.vue (GREEN phase)
4. [ ] Update LaunchTab.vue (GREEN phase)
5. [ ] Update LaunchSuccessorDialog.vue (GREEN phase)
6. [ ] Update AgentMissionEditModal.vue (GREEN phase)
7. [ ] Run E2E test → verify passes
8. [ ] Manual testing checklist
9. [ ] Code review (self-review)
10. [ ] Commit changes with message: "feat(0366d-3): update launch & succession components for agent identity"

**Estimated Time Breakdown**:
- E2E test writing: 30 min
- SuccessionTimeline.vue: 1 hour
- LaunchTab.vue: 30 min
- LaunchSuccessorDialog.vue: 45 min
- AgentMissionEditModal.vue: 45 min
- Testing & debugging: 30 min
- **Total**: 3-4 hours

---

## Success Metrics

**Completion Criteria**:
- ✅ All 4 components updated
- ✅ E2E test passes (all 4 test cases)
- ✅ Manual testing checklist completed
- ✅ No regression in existing functionality
- ✅ Code committed with descriptive message

**Quality Metrics**:
- Zero console errors
- No TypeScript errors (if using TypeScript)
- Consistent code style (ESLint/Prettier)
- Clear UI messaging (job_id vs agent_id distinction)

---

## Related Handovers

**Dependencies**:
- 0366a - Schema & Models (AgentJob + AgentExecution tables)
- 0366b - Service Layer (API endpoints for executions)
- 0366c - MCP Tools (context tracking with agent_id)

**Follow-up**:
- 0366d-1 - JobsTab Component (agent status board)
- 0366d-2 - Message Components (messaging UI)
- 0366e - Installation Seeding (sample data generation)

---

## Notes for Implementer

**Key Decisions**:
1. **Minimal Changes Philosophy**: Only update what's necessary to fix identity display
2. **No Over-Engineering**: Don't add features outside scope
3. **Test-First**: Write E2E test before making changes
4. **Semantic Clarity**: job_id = work order, agent_id = executor

**Pitfalls to Avoid**:
- ❌ Don't refactor unrelated code
- ❌ Don't add new features (stick to identity display)
- ❌ Don't skip manual testing
- ❌ Don't merge without E2E test passing

**Questions?**:
- Refer to master roadmap: `handovers/0366_agent_identity_refactor_roadmap.md`
- Check database schema: `handovers/Reference_docs/DATABASE_SCHEMA_MAP_0366.md`
- Review semantic principles: `handovers/0366c_context_tools_agent_id_red_phase.md`

---

**END OF HANDOVER 0366d-3**
