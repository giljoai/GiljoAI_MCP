# Handover 0227: Launch Tab 3-Panel Refinement

**Status**: Ready for Implementation
**Priority**: High
**Estimated Effort**: 3 hours
**Dependencies**: Handover 0226 (backend API extensions)
**Part of**: Visual Refactor Series (0225-0237)

---

## Objective

Verify and refine the existing LaunchTab.vue 3-panel layout to match slides 1-9 of the vision document, ensuring proper staging workflow, WebSocket integration, and seamless transition to the Implement tab.

---

## Current State Analysis

### Existing LaunchTab.vue Structure

**Location**: `frontend/src/components/projects/LaunchTab.vue`

**Current Layout** (based on vision document slides 2-9):

1. **Top Section**: 2 tabs (Launch | Implement)
2. **Action Row**: "Stage project" / "Launch Jobs" buttons
3. **3-Column Layout**:
   - **Left**: Project Description (scrollable, editable)
   - **Center**: Orchestrator Generated Mission (scrollable, read-only)
   - **Right**: Default Agent panel (Orchestrator card with info/lock icons)
4. **Bottom Row**: Horizontal agent cards (Agent Team section)

### Staging State Progression

**State 1: Pre-staging (Waiting)** - Slides 2, 5:
- "Stage project" button: Active (yellow outline)
- "Launch Jobs" button: Inactive (grayed out)
- Mission panel: Empty document icon with "Mission will appear after staging"
- Agent Team: Single orchestrator card (sleeping Giljo avatar)

**State 2: Staging (Working)** - Slide 7:
- "Stage project" button: Inactive (grayed out, spinner)
- Status text: "Working..."
- Mission panel: Gradually fills with mission text
- Agent Team: Spinner until agents populate

**State 3: Staging Complete (Ready)** - Slides 8-9:
- "Stage project" button: Inactive ("Completed!" text)
- "Launch Jobs" button: Active (yellow outline)
- Mission panel: Fully populated mission text
- Agent Team: All agent cards visible with edit icons
- Status text: "Completed!"

### WebSocket Integration Requirements

**Events to Subscribe** (from vision slides 2-9):

1. **`project:mission_updated`** - Triggered during orchestrator staging
   - Updates center mission panel in real-time
   - Streams mission text as orchestrator generates it

2. **`agent:created`** - Triggered when orchestrator spawns agents
   - Adds new agent cards to bottom row
   - Shows agent type, name, and mission preview

3. **`project:staging_cancelled`** - Triggered if staging fails/cancelled
   - Resets UI to pre-staging state
   - Shows error notification

### Race Condition Prevention

**Issue**: Multiple WebSocket events may fire simultaneously during staging.

**Solution** (from existing codebase pattern):

```javascript
// Use Set-based tracking for agent IDs
const agentIdsTracked = ref(new Set());

// WebSocket handler
function handleAgentCreated(event) {
  if (!agentIdsTracked.value.has(event.agent_id)) {
    agentIdsTracked.value.add(event.agent_id);
    agents.value.push(event.agent_data);
  }
}
```

---

## TDD Approach

### 0. Test-Driven Development Order

**Test-Driven Development Order**:

1. Write failing tests for 3-panel layout rendering
2. Implement minimal layout code to pass tests
3. Write failing tests for staging workflow state transitions
4. Implement minimal state management code
5. Write failing tests for WebSocket subscription and event handling
6. Integrate existing useWebSocketV2() composable
7. Refactor if needed

**Test Focus**: Behavior (layout renders correctly, state transitions work, events update UI), NOT implementation (specific Vue lifecycle methods used).

**Key Principle**: Write tests that describe WHAT the component should do, not HOW it does it.

---

## Implementation Plan

### 1. Verify 3-Panel Layout

**File**: `frontend/src/components/projects/LaunchTab.vue`

Ensure layout matches vision document slides 2-9:

```vue
<template>
  <v-container fluid class="launch-tab pa-4">
    <!-- Tabs -->
    <v-tabs v-model="activeTab" color="primary">
      <v-tab value="launch">Launch</v-tab>
      <v-tab value="implement">Implement</v-tab>
    </v-tabs>

    <!-- Action Buttons Row -->
    <v-row class="my-4">
      <v-col>
        <v-btn
          color="warning"
          variant="outlined"
          size="large"
          :loading="stagingInProgress"
          :disabled="stagingComplete || stagingInProgress"
          @click="handleStageProject"
        >
          {{ stageButtonText }}
        </v-btn>

        <v-btn
          color="warning"
          variant="outlined"
          size="large"
          class="ml-4"
          :disabled="!stagingComplete"
          @click="handleLaunchJobs"
        >
          Launch Jobs
        </v-btn>
      </v-col>
    </v-row>

    <!-- 3-Column Layout -->
    <v-row class="three-panel-layout">
      <!-- Left: Project Description -->
      <v-col cols="4">
        <v-card class="fill-height">
          <v-card-title>
            Project Description
            <v-icon class="ml-2" size="small">mdi-pencil</v-icon>
          </v-card-title>
          <v-card-text class="scrollable-content">
            <v-textarea
              v-model="projectDescription"
              variant="outlined"
              rows="20"
              no-resize
              @blur="updateProjectDescription"
            />
          </v-card-text>
        </v-card>
      </v-col>

      <!-- Center: Orchestrator Generated Mission -->
      <v-col cols="4">
        <v-card class="fill-height">
          <v-card-title>Orchestrator Generated Mission</v-card-title>
          <v-card-text class="scrollable-content">
            <div v-if="!orchestratorMission" class="empty-state text-center">
              <v-icon size="120" color="grey-darken-1">mdi-file-document-outline</v-icon>
              <p class="text-grey mt-4">Mission will appear after staging</p>
              <p class="text-caption text-grey">
                Click 'Stage Project' to begin orchestrator mission generation
              </p>
            </div>
            <div v-else class="mission-content">
              {{ orchestratorMission }}
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- Right: Default Agent -->
      <v-col cols="4">
        <v-card class="fill-height">
          <v-card-title>Default agent</v-card-title>
          <v-card-text class="scrollable-content">
            <div v-if="orchestratorAgent" class="agent-preview">
              <v-avatar color="orange" size="64" class="mb-3">
                <span class="text-h5">Or</span>
              </v-avatar>
              <h3 class="mb-2">Orchestrator</h3>
              <div class="agent-actions">
                <v-btn icon size="small" variant="text">
                  <v-icon>mdi-information-outline</v-icon>
                  <v-tooltip activator="parent" location="bottom">
                    View agent template (read-only)
                  </v-tooltip>
                </v-btn>
                <v-btn icon size="small" variant="text">
                  <v-icon>mdi-lock</v-icon>
                  <v-tooltip activator="parent" location="bottom">
                    Agent template locked
                  </v-tooltip>
                </v-btn>
              </div>
            </div>
            <div v-else class="empty-state text-center">
              <v-icon size="120" color="grey-darken-1">mdi-sleep</v-icon>
              <p class="text-grey mt-4">Waiting.</p>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Bottom: Agent Team (Horizontal Cards) -->
    <v-row class="mt-4">
      <v-col>
        <v-card>
          <v-card-title>
            <v-icon class="mr-2">mdi-account-group</v-icon>
            Agent Team
            <v-chip class="ml-2" size="small" color="primary">
              {{ agents.length }} AGENT{{ agents.length !== 1 ? 'S' : '' }}
            </v-chip>
          </v-card-title>
          <v-card-text>
            <div v-if="agents.length === 0" class="text-center py-8">
              <v-progress-circular
                v-if="stagingInProgress"
                indeterminate
                color="primary"
                size="64"
              />
              <p v-else class="text-grey">No agents assigned yet</p>
            </div>
            <div v-else class="agent-cards-horizontal">
              <AgentCard
                v-for="agent in agents"
                :key="agent.job_id"
                :agent="agent"
                class="agent-card-item"
              />
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useProjectStore } from '@/stores/project';
import { useWebSocketV2 } from '@/composables/useWebSocket';
import AgentCard from '@/components/AgentCard.vue';

const projectStore = useProjectStore();
const { subscribe, on } = useWebSocketV2();

// State
const activeTab = ref('launch');
const stagingInProgress = ref(false);
const stagingComplete = ref(false);
const projectDescription = ref('');
const orchestratorMission = ref('');
const orchestratorAgent = ref(null);
const agents = ref([]);
const agentIdsTracked = ref(new Set());

// Computed
const stageButtonText = computed(() => {
  if (stagingComplete.value) return 'Completed!';
  if (stagingInProgress.value) return 'Working...';
  return 'Stage project';
});

// Methods
async function handleStageProject() {
  try {
    stagingInProgress.value = true;

    // Copy orchestrator prompt to clipboard
    const prompt = await projectStore.generateOrchestratorPrompt();
    await navigator.clipboard.writeText(prompt);

    // Show success notification
    // User will paste prompt in CLI to begin staging

  } catch (error) {
    console.error('Staging failed:', error);
    stagingInProgress.value = false;
  }
}

function handleLaunchJobs() {
  // Switch to Implement tab
  activeTab.value = 'implement';
  // Emit event to parent to change tab
  emit('switch-tab', 'implement');
}

async function updateProjectDescription() {
  await projectStore.updateProjectDescription(projectDescription.value);
}

// WebSocket Handlers
function handleMissionUpdated(event) {
  orchestratorMission.value = event.mission;

  // Check if mission generation complete
  if (event.status === 'complete') {
    stagingInProgress.value = false;
    stagingComplete.value = true;
  }
}

function handleAgentCreated(event) {
  // Prevent duplicates
  if (!agentIdsTracked.value.has(event.job_id)) {
    agentIdsTracked.value.add(event.job_id);

    if (event.agent_type === 'orchestrator') {
      orchestratorAgent.value = event;
    }

    agents.value.push(event);
  }
}

function handleStagingCancelled(event) {
  stagingInProgress.value = false;
  stagingComplete.value = false;
  orchestratorMission.value = '';
  agents.value = [];
  agentIdsTracked.value.clear();

  // Show error notification
  console.error('Staging cancelled:', event.reason);
}

// Lifecycle
onMounted(() => {
  // Load project data
  projectDescription.value = projectStore.activeProject?.description || '';

  // Subscribe to project updates using existing useWebSocketV2 composable
  subscribe('project', projectStore.activeProject?.project_id);

  // Listen for WebSocket events
  on('project:mission_updated', handleMissionUpdated);
  on('agent:created', handleAgentCreated);
  on('project:staging_cancelled', handleStagingCancelled);
});

// Note: No onUnmounted cleanup needed - useWebSocketV2 handles cleanup automatically
</script>

<style scoped>
.three-panel-layout {
  min-height: 500px;
}

.scrollable-content {
  max-height: 500px;
  overflow-y: auto;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}

.agent-preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 2rem;
}

.agent-cards-horizontal {
  display: flex;
  gap: 1rem;
  overflow-x: auto;
  padding: 1rem 0;
}

.agent-card-item {
  flex-shrink: 0;
  width: 280px;
}
</style>
```

### 2. Tab Navigation Integration

**File**: `frontend/src/components/projects/ProjectDetail.vue` (or parent)

Ensure seamless tab switching:

```vue
<template>
  <v-tabs v-model="currentTab" class="project-tabs">
    <v-tab value="launch" :disabled="false">Launch</v-tab>
    <v-tab value="implement" :disabled="!projectStaged">Implement</v-tab>
  </v-tabs>

  <v-window v-model="currentTab">
    <v-window-item value="launch">
      <LaunchTab @switch-tab="handleTabSwitch" />
    </v-window-item>

    <v-window-item value="implement">
      <ImplementTab />
    </v-window-item>
  </v-window>
</template>

<script setup>
import { ref, computed } from 'vue';
import LaunchTab from '@/components/projects/LaunchTab.vue';
import ImplementTab from '@/components/projects/ImplementTab.vue';

const currentTab = ref('launch');
const projectStaged = computed(() => {
  // Check if project has been staged
  return projectStore.activeProject?.status === 'staged';
});

function handleTabSwitch(tab) {
  currentTab.value = tab;
}
</script>
```

### 3. Clipboard Integration

**File**: `frontend/src/stores/project.js`

Add orchestrator prompt generation:

```javascript
async generateOrchestratorPrompt() {
  const project = this.activeProject;

  // Call backend endpoint to generate prompt
  const response = await api.post(`/api/projects/${project.project_id}/generate-prompt`, {
    agent_type: 'orchestrator',
    include_context: true
  });

  return response.data.prompt;
}
```

---

## Testing Criteria

### 1. Visual Layout Verification

**Test**: Compare rendered LaunchTab with vision slides 2-9

**Checklist**:
- ✅ 3-column layout with equal widths
- ✅ Left panel: Project Description with edit icon
- ✅ Center panel: Mission display (empty state → populated)
- ✅ Right panel: Orchestrator card (sleeping → active)
- ✅ Bottom row: Horizontal agent cards
- ✅ Action buttons: Stage project + Launch Jobs
- ✅ Tabs: Launch (active) + Implement (faded)

### 2. Staging Workflow

**Test**: Complete staging flow from pre-staging to ready

**Steps**:
1. Load project (pre-staging state)
   - Verify "Stage project" button is active
   - Verify "Launch Jobs" button is disabled
   - Verify mission panel shows empty state icon
2. Click "Stage project"
   - Verify button changes to "Working..." with spinner
   - Verify prompt copied to clipboard
3. Paste prompt in CLI (simulate orchestrator work)
   - Verify mission panel updates in real-time
   - Verify agent cards appear as agents are created
4. Wait for staging completion
   - Verify button changes to "Completed!"
   - Verify "Launch Jobs" button becomes active
   - Verify all agent cards visible

### 3. WebSocket Event Handling

**Test**: Verify WebSocket subscriptions and race condition prevention

```javascript
// Test file: tests/components/test_launch_tab.spec.js

describe('LaunchTab WebSocket Integration', () => {
  it('updates mission panel on project:mission_updated', async () => {
    const wrapper = mount(LaunchTab);

    // Simulate WebSocket event
    await wrapper.vm.handleMissionUpdated({
      mission: 'Test mission content',
      status: 'in_progress'
    });

    expect(wrapper.vm.orchestratorMission).toBe('Test mission content');
    expect(wrapper.vm.stagingInProgress).toBe(true);
  });

  it('prevents duplicate agents with Set-based tracking', async () => {
    const wrapper = mount(LaunchTab);

    const agentEvent = {
      job_id: 'test-uuid-1',
      agent_type: 'analyzer',
      agent_name: 'Analyzer'
    };

    // Fire same event twice
    await wrapper.vm.handleAgentCreated(agentEvent);
    await wrapper.vm.handleAgentCreated(agentEvent);

    // Should only add once
    expect(wrapper.vm.agents).toHaveLength(1);
    expect(wrapper.vm.agentIdsTracked.has('test-uuid-1')).toBe(true);
  });

  it('resets UI on project:staging_cancelled', async () => {
    const wrapper = mount(LaunchTab);

    // Set some state
    wrapper.vm.stagingInProgress = true;
    wrapper.vm.orchestratorMission = 'Test mission';
    wrapper.vm.agents = [{ job_id: 'test-1' }];

    // Cancel staging
    await wrapper.vm.handleStagingCancelled({ reason: 'User cancelled' });

    expect(wrapper.vm.stagingInProgress).toBe(false);
    expect(wrapper.vm.orchestratorMission).toBe('');
    expect(wrapper.vm.agents).toHaveLength(0);
  });
});
```

### 4. Tab Navigation

**Test**: Verify tab switching behavior

**Steps**:
1. Before staging: Implement tab should be accessible but show empty state
2. Click "Launch Jobs" after staging completion
3. Verify automatic switch to Implement tab
4. Verify Implement tab shows populated agent table

---

## Integration with StatusBoardTable (Handover 0228)

### Minimal Changes Expected

The LaunchTab 3-panel layout is **independent** from the StatusBoardTable implementation:

- **Launch Tab**: Manages project staging and mission generation
- **Implement Tab**: Displays StatusBoardTable for agent monitoring

**Integration Point**:

```vue
<!-- ImplementTab.vue -->
<template>
  <div class="implement-tab">
    <StatusBoardTable
      :project-id="projectId"
      :agents="agents"
    />
    <!-- Message panel, etc. -->
  </div>
</template>
```

The only shared data is the `agents` array populated during staging, which flows from LaunchTab → Store → ImplementTab.

---

## Success Criteria

- ✅ LaunchTab layout matches vision slides 2-9 exactly
- ✅ 3-panel layout with proper spacing and scrollability
- ✅ Staging workflow progresses through 3 states correctly
- ✅ WebSocket events update UI in real-time without race conditions
- ✅ Clipboard integration copies orchestrator prompt successfully
- ✅ "Launch Jobs" button switches to Implement tab
- ✅ Empty states display appropriate icons and messages
- ✅ Agent cards appear dynamically as agents are created
- ✅ All buttons enable/disable at correct workflow stages

---

## Next Steps

→ **Handover 0228**: StatusBoardTable Component
- Create StatusBoardTable.vue component
- Replace horizontal agent cards in Implement tab
- Integrate with table view endpoint from 0226

---

## References

- **Vision Document**: Slides 1-9 (Pre-staging through staging completion)
- **Current Implementation**: `frontend/src/components/projects/LaunchTab.vue`
- **WebSocket Patterns**: `frontend/src/composables/useWebSocket.js`
- **Agent Cards**: `frontend/src/components/AgentCard.vue`
- **Backend API**: Handover 0226 (table view endpoint)

---

## ✅ HANDOVER COMPLETION SUMMARY

**Status**: COMPLETE
**Completed**: 2025-11-21
**Execution Time**: 2-3 hours
**Git Commit**: 10b3197
**Merged to**: master

### Deliverables Completed

✅ Verified and refined LaunchTab.vue 3-panel layout to match vision slides 2-9
✅ Ensured equal column proportions (4-4-4) for desktop layout
✅ Verified WebSocket integration for real-time mission updates
✅ Confirmed empty state icons and messaging
✅ Comprehensive TDD test coverage (19 behavioral tests)

### Test Results

- Tests written: 19 tests
- Tests passing: 19/19 (100%)
- Coverage: 100% for modified code

### Files Modified/Created

**Modified**:
- `frontend/src/components/projects/LaunchTab.vue` (+6 lines modified)

**Created**:
- `frontend/tests/components/projects/LaunchTab.0227.spec.js` (+580 lines)

### Key Changes

**Layout Adjustments**:
- Column proportions changed from 3-4-4 to 4-4-4 for equal spacing
- Vuetify grid adjustments: cols="12" md="3" → cols="4" md="4"

**Testing Focus**:
- TDD methodology: Tests written first, implementation followed
- 19 comprehensive behavioral tests covering layout, empty states, WebSocket subscriptions
- Verified LaunchTab was already 80% aligned with vision document

### Integration Points

- LaunchTab 3-panel layout is independent from StatusBoardTable implementation
- Shared data flows through `agents` array: LaunchTab → Store → ImplementTab
- WebSocket integration already functional (verified, not reimplemented)

### Next Steps

→ Handover 0228: StatusBoardTable Component
- Create dual-view capability (card/table toggle) via composable extraction
- Enhance existing AgentCardGrid with view mode toggle

---

**Archive Status**: Moved to `handovers/completed/` on 2025-11-21
