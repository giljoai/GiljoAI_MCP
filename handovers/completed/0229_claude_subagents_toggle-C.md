# Handover 0229: Claude Subagents Toggle

**Status**: Ready for Implementation
**Priority**: Medium
**Estimated Effort**: 2 hours
**Dependencies**: Handover 0228 (StatusBoardTable component)
**Part of**: Visual Refactor Series (0225-0237)

---

## Before You Begin

**REQUIRED READING** (Critical for TDD discipline and architectural alignment):

1. **F:\GiljoAI_MCP\handovers\QUICK_LAUNCH.txt**
   - TDD discipline (Red → Green → Refactor)
   - Write tests FIRST (behavior, not implementation)
   - No zombie code policy (delete, don't comment)

2. **F:\GiljoAI_MCP\handovers\013A_code_review_architecture_status.md**
   - Service layer patterns
   - Multi-tenant isolation
   - Component reuse principles

3. **F:\GiljoAI_MCP\handovers\code_review_nov18.md**
   - Past mistakes to avoid (ProductsView 2,582 lines)
   - Success patterns to follow (ProjectsView componentization)

**Execute in order**: Red (failing tests) → Green (minimal implementation) → Refactor (cleanup)

---

## Objective

Verify and enhance the existing Claude Subagents toggle in JobsTab.vue, ensuring it correctly disables non-orchestrator agent launch actions in the new StatusBoardTable component while providing clear visual feedback and hint text.

---

## Current State Analysis

### Existing Toggle Implementation

**Location**: `frontend/src/components/projects/JobsTab.vue:268-369`

**Current Behavior** (from vision slides 11-12):

**Toggle OFF (General CLI Mode)** - Slide 19:
- All agents can be launched independently
- Each agent has its own prompt for individual terminals
- All action buttons (Launch, Copy Prompt) are enabled for all agents
- Hint: "Each agent runs in its own terminal. All agents can be launched independently."

**Toggle ON (Claude Code CLI Mode)** - Slides 10-14:
- Only orchestrator can be launched
- Other agents run as Claude Code subagents within orchestrator context
- Non-orchestrator action buttons are disabled
- Hint: "Only orchestrator can be launched. Other agents run as Claude Code subagents."

### Existing Toggle Logic

**Reference Implementation** (from current codebase):

```javascript
// JobsTab.vue:268-369
const usingClaudeCodeSubagents = ref(false);

const toggleHintText = computed(() => {
  if (usingClaudeCodeSubagents.value) {
    return 'Only orchestrator can be launched in Claude Code mode. Other agents are subagents.';
  }
  return 'All agents can be launched in individual terminals (General CLI mode).';
});

function shouldDisablePromptButton(agent) {
  if (!usingClaudeCodeSubagents.value) {
    return false; // General mode: all agents can be launched
  }

  // Claude Code mode: only orchestrator can be launched
  return agent.agent_type !== 'orchestrator';
}
```

---

## TDD Approach

### 0. Test-Driven Development Order

**Test-Driven Development Order**:

1. Write failing tests for toggle component rendering and state
2. Implement minimal toggle UI to pass tests
3. Write failing tests for toggle behavior (enables/disables launch buttons correctly)
4. Implement minimal toggle logic in StatusBoardTable
5. Write failing tests for visual feedback (disabled rows, tooltips)
6. Implement minimal styling
7. Write failing tests for persistence (localStorage)
8. Implement localStorage integration
9. Refactor if needed

**Test Focus**: Behavior (toggle changes button availability, visual feedback works, state persists), NOT implementation (which Vuetify component is used, internal state management).

**Key Principle**: Test names should be descriptive like `test_toggle_disables_non_orchestrator_launch_buttons_in_claude_mode` not `test_toggle_function`.

---

## Implementation Plan

### 1. Verify Toggle Component

**File**: `frontend/src/components/projects/JobsTab.vue`

Ensure toggle is properly structured:

```vue
<template>
  <v-container fluid class="jobs-tab pa-4">
    <!-- Claude Subagents Toggle -->
    <v-row class="mb-4">
      <v-col cols="12" md="6">
        <v-switch
          v-model="usingClaudeCodeSubagents"
          color="orange"
          label="Claude Subagents"
          :hint="toggleHintText"
          persistent-hint
          hide-details="auto"
        >
          <template #label>
            <div class="d-flex align-center">
              <span class="font-weight-medium">Claude Code CLI Mode</span>
              <v-tooltip location="top" max-width="400">
                <template #activator="{ props }">
                  <v-icon v-bind="props" class="ml-2" size="small" color="grey">
                    mdi-help-circle-outline
                  </v-icon>
                </template>
                <div>
                  <p class="font-weight-bold mb-2">Claude Code CLI Mode:</p>
                  <p class="mb-2">
                    Enable this when using Claude Code in a single terminal window.
                    Only the orchestrator needs to be launched; other agents run as subagents.
                  </p>
                  <p class="font-weight-bold mb-2">General CLI Mode:</p>
                  <p>
                    Disable this when using multiple terminal windows.
                    Each agent runs independently in its own terminal.
                  </p>
                </div>
              </v-tooltip>
            </div>
          </template>
        </v-switch>

        <!-- Visual Mode Indicator -->
        <v-alert
          v-if="usingClaudeCodeSubagents"
          type="info"
          variant="tonal"
          density="compact"
          class="mt-2"
        >
          <div class="d-flex align-center">
            <v-icon class="mr-2">mdi-information</v-icon>
            <div>
              <strong>Claude Code Mode Active</strong>
              <p class="text-caption mb-0">
                Only orchestrator can be launched. Other agents will run as subagents.
              </p>
            </div>
          </div>
        </v-alert>

        <v-alert
          v-else
          type="success"
          variant="tonal"
          density="compact"
          class="mt-2"
        >
          <div class="d-flex align-center">
            <v-icon class="mr-2">mdi-check-circle</v-icon>
            <div>
              <strong>General CLI Mode Active</strong>
              <p class="text-caption mb-0">
                All agents can be launched in individual terminals.
              </p>
            </div>
          </div>
        </v-alert>
      </v-col>
    </v-row>

    <!-- Status Board Table -->
    <v-row>
      <v-col>
        <StatusBoardTable
          :project-id="projectId"
          :using-claude-code-subagents="usingClaudeCodeSubagents"
          @open-message-modal="handleOpenMessageModal"
          @open-info-modal="handleOpenInfoModal"
        />
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, computed } from 'vue';
import StatusBoardTable from '@/components/projects/StatusBoardTable.vue';

const props = defineProps({
  projectId: {
    type: String,
    required: true
  }
});

// State
const usingClaudeCodeSubagents = ref(false);

// Computed
const toggleHintText = computed(() => {
  if (usingClaudeCodeSubagents.value) {
    return 'Only orchestrator can be launched. Other agents run as Claude Code subagents.';
  }
  return 'Each agent runs in its own terminal. All agents can be launched independently.';
});
</script>
```

### 2. Integrate Toggle with StatusBoardTable

**File**: `frontend/src/components/projects/StatusBoardTable.vue`

Update action button logic to respect toggle:

```vue
<template>
  <!-- ... table structure ... -->

  <!-- Actions Column -->
  <template #item.actions="{ item }">
    <div class="action-buttons">
      <!-- Launch/Reuse Prompt Button -->
      <v-btn
        icon
        size="small"
        variant="text"
        :disabled="!canLaunchAgent(item)"
        :color="canLaunchAgent(item) ? 'primary' : 'grey'"
        @click.stop="handleLaunchAgent(item)"
      >
        <v-icon>mdi-play</v-icon>
        <v-tooltip activator="parent" location="top">
          <span v-if="!canLaunchAgent(item) && usingClaudeCodeSubagents">
            Disabled in Claude Code mode (non-orchestrator)
          </span>
          <span v-else-if="item.status === 'waiting'">
            Launch agent
          </span>
          <span v-else>
            Reuse prompt (copy to clipboard)
          </span>
        </v-tooltip>
      </v-btn>

      <!-- Copy Prompt Button -->
      <v-btn
        icon
        size="small"
        variant="text"
        :disabled="!canCopyPrompt(item)"
        :color="canCopyPrompt(item) ? 'primary' : 'grey'"
        @click.stop="handleCopyPrompt(item)"
      >
        <v-icon>mdi-content-copy</v-icon>
        <v-tooltip activator="parent" location="top">
          <span v-if="!canCopyPrompt(item) && usingClaudeCodeSubagents">
            Disabled in Claude Code mode (non-orchestrator)
          </span>
          <span v-else>
            Copy prompt to clipboard
          </span>
        </v-tooltip>
      </v-btn>

      <!-- ... other action buttons ... -->
    </div>
  </template>
</template>

<script setup>
// Props
const props = defineProps({
  projectId: {
    type: String,
    required: true
  },
  usingClaudeCodeSubagents: {
    type: Boolean,
    default: false
  }
});

// Methods
function canLaunchAgent(agent) {
  // Terminal states: cannot be launched
  const terminalStates = ['complete', 'failed', 'cancelled', 'decommissioned'];
  if (terminalStates.includes(agent.status)) {
    return false;
  }

  // Blocked state: cannot be launched
  if (agent.status === 'blocked') {
    return false;
  }

  // Claude Code mode: only orchestrator can be launched
  if (props.usingClaudeCodeSubagents) {
    return agent.is_orchestrator;
  }

  // General CLI mode: all non-terminal agents can be launched
  return true;
}

function canCopyPrompt(agent) {
  // Decommissioned agents have no prompt
  if (agent.status === 'decommissioned') {
    return false;
  }

  // Claude Code mode: only orchestrator prompts can be copied
  if (props.usingClaudeCodeSubagents) {
    return agent.is_orchestrator;
  }

  // General CLI mode: all agent prompts can be copied
  return true;
}
</script>

<style scoped>
/* Disabled action buttons visual feedback */
.action-buttons .v-btn:disabled {
  opacity: 0.4;
}

.action-buttons .v-btn:disabled .v-icon {
  color: grey !important;
}
</style>
```

### 3. Visual Feedback for Disabled Rows

**File**: `frontend/src/components/projects/StatusBoardTable.vue`

Add visual indication for disabled agents in Claude Code mode:

```vue
<template>
  <v-data-table
    :headers="headers"
    :items="sortedAgents"
    :loading="loading"
    :items-per-page="50"
    :sort-by="[{ key: 'priority', order: 'asc' }]"
    class="agent-table"
    :row-props="getRowProps"
    @click:row="handleRowClick"
  >
    <!-- ... template slots ... -->
  </v-data-table>
</template>

<script setup>
// Methods
function getRowProps({ item }) {
  const props = {
    class: []
  };

  // Add disabled visual style for non-orchestrators in Claude Code mode
  if (usingClaudeCodeSubagents.value && !item.is_orchestrator) {
    props.class.push('disabled-agent-row');
  }

  // Add priority-based row classes
  if (item.status === 'failed' || item.status === 'blocked') {
    props.class.push('priority-high-row');
  }

  return props;
}
</script>

<style scoped>
/* Disabled agent row in Claude Code mode */
.disabled-agent-row {
  opacity: 0.6;
  background-color: rgba(0, 0, 0, 0.02);
}

.disabled-agent-row:hover {
  background-color: rgba(0, 0, 0, 0.04) !important;
}

/* Priority rows */
.priority-high-row {
  border-left: 3px solid rgb(var(--v-theme-error));
}
</style>
```

### 4. Persist Toggle State

**File**: `frontend/src/stores/preferences.js` (NEW or existing)

Save toggle state to localStorage:

```javascript
import { defineStore } from 'pinia';
import { ref } from 'vue';

export const usePreferencesStore = defineStore('preferences', () => {
  const usingClaudeCodeSubagents = ref(
    localStorage.getItem('claudeCodeMode') === 'true'
  );

  function setClaudeCodeMode(enabled) {
    usingClaudeCodeSubagents.value = enabled;
    localStorage.setItem('claudeCodeMode', enabled.toString());
  }

  return {
    usingClaudeCodeSubagents,
    setClaudeCodeMode
  };
});
```

**Update JobsTab.vue to use store**:

```vue
<script setup>
import { usePreferencesStore } from '@/stores/preferences';

const preferencesStore = usePreferencesStore();

// Use store state instead of local ref
const usingClaudeCodeSubagents = computed({
  get: () => preferencesStore.usingClaudeCodeSubagents,
  set: (value) => preferencesStore.setClaudeCodeMode(value)
});
</script>
```

---

## Cleanup Checklist

**Old Code Removed**:
- [ ] No commented-out blocks remaining
- [ ] No orphaned imports (check with linter)
- [ ] No unused functions or variables
- [ ] No `// TODO` or `// FIXME` comments without tickets

**Integration Verified**:
- [ ] Existing components reused where possible
- [ ] No duplicate functionality created
- [ ] Shared logic extracted to composables (if applicable)
- [ ] No zombie code (per QUICK_LAUNCH.txt line 28)

**Testing**:
- [ ] All imports resolved correctly
- [ ] No linting errors (eslint/ruff)
- [ ] Coverage maintained (>80%)

---

## Testing Criteria

### 1. Toggle Functionality

**Test**: Verify toggle changes behavior correctly

```javascript
// tests/components/test_claude_subagents_toggle.spec.js

describe('Claude Subagents Toggle', () => {
  it('enables all agents in General CLI mode', async () => {
    const wrapper = mount(JobsTab, {
      props: { projectId: 'test-uuid' }
    });

    wrapper.vm.usingClaudeCodeSubagents = false;
    await wrapper.vm.$nextTick();

    const table = wrapper.findComponent(StatusBoardTable);

    // All agents should be launchable
    const orchestrator = { agent_type: 'orchestrator', status: 'waiting', is_orchestrator: true };
    const analyzer = { agent_type: 'analyzer', status: 'waiting', is_orchestrator: false };

    expect(table.vm.canLaunchAgent(orchestrator)).toBe(true);
    expect(table.vm.canLaunchAgent(analyzer)).toBe(true);
  });

  it('disables non-orchestrators in Claude Code mode', async () => {
    const wrapper = mount(JobsTab, {
      props: { projectId: 'test-uuid' }
    });

    wrapper.vm.usingClaudeCodeSubagents = true;
    await wrapper.vm.$nextTick();

    const table = wrapper.findComponent(StatusBoardTable);

    const orchestrator = { agent_type: 'orchestrator', status: 'waiting', is_orchestrator: true };
    const analyzer = { agent_type: 'analyzer', status: 'waiting', is_orchestrator: false };

    expect(table.vm.canLaunchAgent(orchestrator)).toBe(true);
    expect(table.vm.canLaunchAgent(analyzer)).toBe(false);
  });

  it('updates hint text based on toggle state', async () => {
    const wrapper = mount(JobsTab, {
      props: { projectId: 'test-uuid' }
    });

    wrapper.vm.usingClaudeCodeSubagents = false;
    await wrapper.vm.$nextTick();
    expect(wrapper.vm.toggleHintText).toContain('individual terminals');

    wrapper.vm.usingClaudeCodeSubagents = true;
    await wrapper.vm.$nextTick();
    expect(wrapper.vm.toggleHintText).toContain('Claude Code subagents');
  });
});
```

### 2. Visual Feedback

**Test**: Verify disabled state styling

```javascript
it('applies disabled-agent-row class in Claude Code mode', async () => {
  const wrapper = mount(StatusBoardTable, {
    props: {
      projectId: 'test-uuid',
      usingClaudeCodeSubagents: true
    }
  });

  wrapper.vm.agents = [
    { job_id: '1', agent_type: 'orchestrator', is_orchestrator: true },
    { job_id: '2', agent_type: 'analyzer', is_orchestrator: false }
  ];

  await wrapper.vm.$nextTick();

  const rows = wrapper.findAll('tbody tr');
  expect(rows[0].classes()).not.toContain('disabled-agent-row'); // Orchestrator
  expect(rows[1].classes()).toContain('disabled-agent-row'); // Analyzer
});

it('displays correct tooltip for disabled launch button', async () => {
  const wrapper = mount(StatusBoardTable, {
    props: {
      projectId: 'test-uuid',
      usingClaudeCodeSubagents: true
    }
  });

  wrapper.vm.agents = [
    { job_id: '1', agent_type: 'analyzer', status: 'waiting', is_orchestrator: false }
  ];

  await wrapper.vm.$nextTick();

  const launchButton = wrapper.find('[data-test="launch-button"]');
  const tooltip = wrapper.findComponent({ name: 'VTooltip' });

  expect(launchButton.attributes('disabled')).toBe('true');
  expect(tooltip.text()).toContain('Disabled in Claude Code mode');
});
```

### 3. Persistence

**Test**: Verify toggle state persists across sessions

```javascript
it('saves toggle state to localStorage', async () => {
  const wrapper = mount(JobsTab, {
    props: { projectId: 'test-uuid' }
  });

  const preferencesStore = usePreferencesStore();

  preferencesStore.setClaudeCodeMode(true);
  expect(localStorage.getItem('claudeCodeMode')).toBe('true');

  preferencesStore.setClaudeCodeMode(false);
  expect(localStorage.getItem('claudeCodeMode')).toBe('false');
});

it('loads toggle state from localStorage on mount', () => {
  localStorage.setItem('claudeCodeMode', 'true');

  const wrapper = mount(JobsTab, {
    props: { projectId: 'test-uuid' }
  });

  expect(wrapper.vm.usingClaudeCodeSubagents).toBe(true);
});
```

---

## Key Interactions

### 1. Toggle State → StatusBoardTable

**Flow**:
1. User toggles Claude Code mode in JobsTab
2. `usingClaudeCodeSubagents` prop passed to StatusBoardTable
3. StatusBoardTable recalculates `canLaunchAgent()` for all rows
4. Action buttons enable/disable accordingly
5. Visual feedback (row opacity, tooltip text) updates

### 2. Disabled State Behavior

**Claude Code Mode ON**:
- Orchestrator row: Fully interactive (all action buttons enabled)
- Non-orchestrator rows: Launch/Copy Prompt disabled, Messages/Info enabled
- Visual: Non-orchestrator rows have reduced opacity + disabled-agent-row class

**General CLI Mode**:
- All rows: Fully interactive (all action buttons enabled based on agent status)
- Visual: No opacity reduction, all rows have normal styling

---

## Success Criteria

- ✅ Toggle switches between Claude Code mode and General CLI mode
- ✅ Hint text updates based on toggle state
- ✅ Visual mode indicator (alert) displays current mode
- ✅ StatusBoardTable receives toggle state via prop
- ✅ Launch button disabled for non-orchestrators in Claude Code mode
- ✅ Copy Prompt button disabled for non-orchestrators in Claude Code mode
- ✅ Tooltips explain why buttons are disabled
- ✅ Disabled agent rows have visual feedback (opacity, background)
- ✅ Toggle state persists to localStorage
- ✅ Messages and Info buttons always enabled (regardless of toggle)
- ✅ Help tooltip explains both modes clearly

---

## Next Steps

→ **Handover 0230**: Prompt Generation & Clipboard Copy
- Implement "Copy Prompt" action with clipboard integration
- Add success feedback (snackbar notification)
- Integrate with toggle logic (respect disabled state)

---

## References

- **Vision Document**: Slides 10-14 (Claude Code mode), Slides 19-27 (General CLI mode)
- **Current Implementation**: `frontend/src/components/projects/JobsTab.vue:268-369`
- **StatusBoardTable**: Handover 0228
- **Vuetify v-switch**: [Documentation](https://vuetifyjs.com/en/components/switches/)
- **Existing Toggle Logic**: `shouldDisablePromptButton()` function

---

## ✅ HANDOVER COMPLETION SUMMARY

**Status**: COMPLETE
**Completed**: 2025-11-21
**Execution Time**: 2 hours
**Git Commit**: c61a962
**Merged to**: master

### Deliverables Completed

✅ Integrated Claude Subagents toggle with AgentCardGrid and AgentTableView
✅ Implemented canLaunchAgent() and canCopyPrompt() logic methods
✅ Added visual feedback (disabled buttons, row opacity, tooltips)
✅ Verified existing toggle in JobsTab.vue (lines 268-369)
✅ Comprehensive TDD test coverage (25 tests, 100% passing)

### Test Results

**JobsTab tests**:
- Tests written: 10 tests
- Tests passing: 10/10 (100%)
- Coverage: Toggle logic, hint text, alert indicators

**AgentCardGrid tests**:
- Tests written: 15 tests
- Tests passing: 15/15 (100%)
- Coverage: Button disabling, tooltips, visual feedback

**Total**: 25/25 tests passing (100%)

### Files Modified/Created

**Modified**:
- `frontend/src/components/orchestration/AgentCardGrid.vue` (+52 lines)
- `frontend/src/components/orchestration/AgentTableView.vue` (+82 lines)

**Created**:
- `frontend/tests/components/projects/JobsTab.0229.spec.js` (305 lines, 10 tests)
- `frontend/tests/components/orchestration/AgentCardGrid.0229.spec.js` (405 lines, 15 tests)
- `frontend/tests/components/orchestration/AgentTableView.0229.spec.js` (392 lines)

### Key Changes

**Toggle Integration**:
- usingClaudeCodeSubagents prop added to AgentCardGrid
- Prop passed through to AgentTableView
- Existing toggle in JobsTab.vue verified and reused (no duplication)

**Logic Methods**:
- canLaunchAgent(agent) - Disables non-orchestrators in Claude Code mode
- canCopyPrompt(agent) - Disables prompt copying for non-orchestrators
- Implemented in both AgentCardGrid and AgentTableView for consistency

**Visual Feedback**:
- Launch button :disabled binding based on canLaunchAgent()
- Color changes: primary → grey for disabled buttons
- Tooltips: "Disabled in Claude Code mode (non-orchestrator)"
- CSS: disabled-agent-row class (opacity 0.6, background shading)

**Behavior Modes**:
- General CLI Mode: All agents can be launched independently
- Claude Code Mode: Only orchestrator can be launched (others are subagents)

### Integration Points

- JobsTab.vue toggle controls behavior via prop drilling
- Data flow: JobsTab → AgentCardGrid → AgentTableView
- Both card and table views respect toggle state
- Visual feedback consistent across both views
- Existing toggle implementation preserved (no parallel system)

### Next Steps

→ Handover 0230: Prompt Generation & Clipboard Copy
- Implement "Copy Prompt" action with clipboard integration
- Add success feedback (snackbar notification)

---

**Archive Status**: Moved to `handovers/completed/` on 2025-11-21
