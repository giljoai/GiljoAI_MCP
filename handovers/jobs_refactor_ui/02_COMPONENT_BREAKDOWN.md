# Component Breakdown - Jobs Page Refactor

**Document ID**: jobs_refactor_ui/02
**Created**: 2025-11-21

---

## Table of Contents

1. [Component Hierarchy](#component-hierarchy)
2. [Launch Tab Components](#launch-tab-components)
3. [Implementation Tab Components](#implementation-tab-components)
4. [Shared Components](#shared-components)
5. [Component Specifications](#component-specifications)

---

## Component Hierarchy

```
ProjectJobsView.vue (Container)
│
├─ TabNavigation.vue
│  ├─ LaunchTab (button)
│  └─ ImplementationTab (button)
│
├─ LaunchTabPanel.vue (v-show based on activeTab)
│  │
│  ├─ StageProjectButton.vue
│  │  ├─ Props: status, disabled
│  │  └─ Emits: @click
│  │
│  ├─ StatusIndicator.vue
│  │  ├─ Props: status ('Waiting', 'Working', 'Completed!')
│  │  └─ Displays: badge with icon + text
│  │
│  ├─ ThreePanelLayout.vue
│  │  │
│  │  ├─ ProjectDescriptionPanel.vue
│  │  │  ├─ Props: description, editable
│  │  │  ├─ Emits: @update:description
│  │  │  └─ Features: inline editing, auto-save, scrollable
│  │  │
│  │  ├─ MissionPanel.vue
│  │  │  ├─ Props: mission, loading
│  │  │  ├─ Emits: @update:mission
│  │  │  └─ Features: streaming text, scrollable, edit icon
│  │  │
│  │  └─ DefaultAgentPanel.vue
│  │     │
│  │     ├─ AgentCard.vue (Orchestrator - locked)
│  │     │  ├─ Props: agent, locked
│  │     │  └─ Actions: info [ℹ], locked [🔒]
│  │     │
│  │     └─ AgentTeamSection.vue
│  │        └─ AgentCard.vue (x3: Analyzer, Implementor, Tester)
│  │           ├─ Props: agent, editable
│  │           ├─ Emits: @view-template, @edit-mission
│  │           └─ Actions: info [ℹ], edit [✎]
│  │
│  └─ LaunchJobsButton.vue
│     ├─ Props: enabled, loading
│     └─ Emits: @launch
│
└─ ImplementationTabPanel.vue (v-show based on activeTab)
   │
   ├─ CLIModeToggle.vue
   │  ├─ Props: modelValue (boolean)
   │  ├─ Emits: @update:modelValue
   │  └─ Features: toggle switch, label, tooltip
   │
   ├─ CLIModeBanner.vue
   │  ├─ Props: mode ('claude-code' | 'general')
   │  └─ Displays: colored banner with mode text
   │
   ├─ StatusBoard.vue
   │  │
   │  ├─ StatusBoardHeader.vue
   │  │  └─ Columns: Agent Type, Agent ID, Agent Status, Job Read, Job Ack, etc.
   │  │
   │  └─ AgentRow.vue (v-for each agent)
   │     │
   │     ├─ AgentAvatar.vue
   │     │  ├─ Props: agentType, color
   │     │  └─ Displays: colored circle with initials
   │     │
   │     ├─ AgentIDCell.vue
   │     │  ├─ Props: agentId
   │     │  └─ Displays: truncated UUID with tooltip
   │     │
   │     ├─ AgentStatusBadge.vue
   │     │  ├─ Props: status
   │     │  └─ Displays: "Waiting", "Working", "Completed!"
   │     │
   │     ├─ JobStatusIndicators.vue
   │     │  ├─ Props: jobRead, jobAcknowledged
   │     │  └─ Displays: ✓ checkmarks
   │     │
   │     ├─ MessageCounters.vue
   │     │  ├─ Props: sent, waiting, read
   │     │  └─ Displays: numerical counts
   │     │
   │     └─ AgentActions.vue
   │        ├─ Props: agent, cliMode, disabled
   │        ├─ Emits: @copy-prompt, @view-messages, @view-info
   │        └─ Buttons: ▶/🔄 (copy), 📁 (messages), ℹ (info)
   │
   └─ MessageQueuePanel.vue
      │
      ├─ RecipientSelector.vue
      │  ├─ Props: agents, mode ('direct' | 'broadcast')
      │  ├─ Emits: @update:recipient
      │  └─ Features: dropdown, "Message Orchestrator" / "Broadcast"
      │
      ├─ MessageInput.vue
      │  ├─ Props: modelValue
      │  ├─ Emits: @update:modelValue
      │  └─ Features: text field, placeholder
      │
      └─ SendButton.vue
         ├─ Props: disabled
         ├─ Emits: @send
         └─ Features: yellow arrow icon, enabled state

```

---

## Launch Tab Components

### 1. LaunchTabPanel.vue

**Purpose**: Container for the Launch tab content

**Template Structure:**
```vue
<template>
  <v-card class="launch-tab-panel" flat>
    <!-- Header -->
    <div class="d-flex justify-space-between align-center mb-4">
      <StageProjectButton
        :status="stagingStatus"
        :disabled="isStagingDisabled"
        @click="handleStageProject"
      />
      <StatusIndicator :status="stagingStatus" />
      <LaunchJobsButton
        :enabled="isLaunchEnabled"
        :loading="isLaunching"
        @launch="handleLaunchJobs"
      />
    </div>

    <!-- Three-column layout -->
    <ThreePanelLayout>
      <template #left>
        <ProjectDescriptionPanel
          v-model:description="projectDescription"
          :editable="true"
        />
      </template>

      <template #center>
        <MissionPanel
          v-model:mission="orchestratorMission"
          :loading="stagingStatus === 'Working'"
        />
      </template>

      <template #right>
        <DefaultAgentPanel
          :orchestrator="orchestratorAgent"
          :agents="agentTeam"
          @view-template="handleViewTemplate"
          @edit-mission="handleEditMission"
        />
      </template>
    </ThreePanelLayout>
  </v-card>
</template>
```

**Props:**
```typescript
interface Props {
  projectId: string
}
```

**Data/State:**
```typescript
interface State {
  stagingStatus: 'Waiting' | 'Working' | 'Completed!'
  projectDescription: string
  orchestratorMission: string
  orchestratorAgent: Agent
  agentTeam: Agent[]
  isLaunching: boolean
}
```

**Computed:**
```typescript
isStagingDisabled = computed(() => stagingStatus !== 'Waiting')
isLaunchEnabled = computed(() => stagingStatus === 'Completed!')
```

**Methods:**
```typescript
async handleStageProject() {
  // 1. Copy staging prompt to clipboard
  // 2. Show toast: "Prompt copied! Paste in CLI."
  // 3. Set stagingStatus = 'Working'
  // 4. Call API: POST /api/projects/{id}/stage
  // 5. WebSocket listens for stage completion
  // 6. On complete, stagingStatus = 'Completed!'
}

async handleLaunchJobs() {
  // 1. Set isLaunching = true
  // 2. Call API: POST /api/projects/{id}/launch-jobs
  // 3. Switch to Implementation tab
  // 4. Set isLaunching = false
}
```

---

### 2. StageProjectButton.vue

**Purpose**: Button to initiate project staging

**Template:**
```vue
<template>
  <v-btn
    color="primary"
    size="large"
    :disabled="disabled"
    :loading="status === 'Working'"
    @click="$emit('click')"
  >
    <v-icon left>mdi-rocket-launch</v-icon>
    Stage project
  </v-btn>
</template>
```

**Props:**
```typescript
interface Props {
  status: 'Waiting' | 'Working' | 'Completed!'
  disabled: boolean
}
```

**Emits:**
```typescript
const emit = defineEmits<{
  click: []
}>()
```

---

### 3. StatusIndicator.vue

**Purpose**: Display current staging status with visual indicator

**Template:**
```vue
<template>
  <v-chip
    :color="statusColor"
    :variant="statusVariant"
    size="large"
    class="status-indicator"
  >
    <v-icon left :icon="statusIcon" />
    {{ statusText }}
  </v-chip>
</template>
```

**Props:**
```typescript
interface Props {
  status: 'Waiting' | 'Working' | 'Completed!'
}
```

**Computed:**
```typescript
statusColor = computed(() => {
  switch (props.status) {
    case 'Waiting': return 'grey'
    case 'Working': return 'info'
    case 'Completed!': return 'success'
  }
})

statusIcon = computed(() => {
  switch (props.status) {
    case 'Waiting': return 'mdi-clock-outline'
    case 'Working': return 'mdi-loading mdi-spin'
    case 'Completed!': return 'mdi-check-circle'
  }
})

statusText = computed(() => props.status)
```

---

### 4. ThreePanelLayout.vue

**Purpose**: Three-column responsive layout

**Template:**
```vue
<template>
  <v-row class="three-panel-layout">
    <v-col cols="12" md="4">
      <slot name="left" />
    </v-col>
    <v-col cols="12" md="4">
      <slot name="center" />
    </v-col>
    <v-col cols="12" md="4">
      <slot name="right" />
    </v-col>
  </v-row>
</template>
```

**Styling:**
```scss
.three-panel-layout {
  .v-col {
    height: 500px; // Fixed height for consistency
    overflow: hidden;
  }
}
```

---

### 5. ProjectDescriptionPanel.vue

**Purpose**: Display and edit project description

**Template:**
```vue
<template>
  <v-card class="description-panel h-100" outlined>
    <v-card-title class="d-flex justify-space-between">
      <span>Project Description</span>
      <v-btn
        icon="mdi-pencil"
        size="small"
        variant="text"
        @click="isEditing = true"
      />
    </v-card-title>

    <v-card-text class="description-content">
      <v-textarea
        v-if="isEditing"
        v-model="localDescription"
        auto-grow
        rows="15"
        @blur="handleSave"
      />
      <div v-else class="description-text">
        {{ description }}
      </div>
    </v-card-text>
  </v-card>
</template>
```

**Props:**
```typescript
interface Props {
  description: string
  editable: boolean
}
```

**Emits:**
```typescript
const emit = defineEmits<{
  'update:description': [value: string]
}>()
```

**Methods:**
```typescript
async handleSave() {
  isEditing.value = false
  emit('update:description', localDescription.value)
  // Auto-save to API
  await api.updateProjectDescription(projectId, localDescription.value)
}
```

---

### 6. MissionPanel.vue

**Purpose**: Display orchestrator-generated mission

**Template:**
```vue
<template>
  <v-card class="mission-panel h-100" outlined>
    <v-card-title class="d-flex justify-space-between">
      <span>Orchestrator Generated Mission</span>
      <v-btn
        v-if="mission && editable"
        icon="mdi-pencil"
        size="small"
        variant="text"
        @click="isEditing = true"
      />
    </v-card-title>

    <v-card-text class="mission-content">
      <!-- Empty state -->
      <div v-if="!mission && !loading" class="empty-state">
        <v-icon size="64" color="grey">mdi-file-document-outline</v-icon>
        <p class="mt-4">Mission will appear after staging</p>
        <p class="text-caption">
          Click 'Stage Project' to begin orchestrator mission generation
        </p>
      </div>

      <!-- Loading state -->
      <div v-else-if="loading" class="loading-state">
        <v-progress-circular indeterminate color="primary" />
        <p class="mt-4">Generating mission...</p>
      </div>

      <!-- Mission text (streaming or complete) -->
      <v-textarea
        v-else-if="isEditing"
        v-model="localMission"
        auto-grow
        rows="15"
        @blur="handleSave"
      />
      <div v-else class="mission-text">
        {{ mission }}
      </div>
    </v-card-text>
  </v-card>
</template>
```

**Props:**
```typescript
interface Props {
  mission: string
  loading: boolean
  editable?: boolean
}
```

**Features:**
- Streaming text support (append text as it arrives via WebSocket)
- Auto-scroll to bottom during streaming
- Scrollable when content overflows

---

### 7. DefaultAgentPanel.vue

**Purpose**: Display orchestrator and agent team

**Template:**
```vue
<template>
  <v-card class="default-agent-panel h-100" outlined>
    <v-card-title>Default agent</v-card-title>

    <v-card-text class="agent-content">
      <!-- Orchestrator (locked) -->
      <AgentCard
        :agent="orchestrator"
        :locked="true"
        class="mb-4"
        @view-template="$emit('view-template', orchestrator)"
      />

      <!-- Agent Team Section -->
      <v-divider class="my-4" />
      <div class="agent-team-header mb-2">
        <strong>Agent Team</strong>
      </div>

      <!-- Agent Team Cards (scrollable) -->
      <div class="agent-team-list">
        <AgentCard
          v-for="agent in agents"
          :key="agent.id"
          :agent="agent"
          :editable="true"
          class="mb-3"
          @view-template="$emit('view-template', agent)"
          @edit-mission="$emit('edit-mission', agent)"
        />
      </div>
    </v-card-text>
  </v-card>
</template>
```

**Props:**
```typescript
interface Props {
  orchestrator: Agent
  agents: Agent[]
}
```

**Emits:**
```typescript
const emit = defineEmits<{
  'view-template': [agent: Agent]
  'edit-mission': [agent: Agent]
}>()
```

---

### 8. AgentCard.vue (Launch Tab Variant)

**Purpose**: Display individual agent with avatar and actions

**Template:**
```vue
<template>
  <v-card class="agent-card" outlined>
    <div class="d-flex align-center">
      <!-- Avatar -->
      <AgentAvatar
        :agent-type="agent.agent_type"
        :color="agentColor"
        size="48"
      />

      <!-- Agent Name -->
      <div class="ml-3 flex-grow-1">
        <strong>{{ agentName }}</strong>
      </div>

      <!-- Actions -->
      <div class="agent-actions">
        <v-btn
          icon="mdi-information-outline"
          size="small"
          variant="text"
          @click="$emit('view-template')"
        />
        <v-btn
          v-if="editable"
          icon="mdi-pencil"
          size="small"
          variant="text"
          @click="$emit('edit-mission')"
        />
        <v-icon v-if="locked" size="small" color="grey">
          mdi-lock
        </v-icon>
      </div>
    </div>
  </v-card>
</template>
```

**Props:**
```typescript
interface Props {
  agent: Agent
  locked?: boolean
  editable?: boolean
}
```

**Emits:**
```typescript
const emit = defineEmits<{
  'view-template': []
  'edit-mission': []
}>()
```

**Computed:**
```typescript
agentName = computed(() => {
  const names = {
    'orchestrator': 'Orchestrator',
    'analyzer': 'Analyzer',
    'implementor': 'Implementor',
    'tester': 'Tester'
  }
  return names[agent.agent_type] || agent.agent_type
})

agentColor = computed(() => {
  const colors = {
    'orchestrator': '#C9A961', // tan
    'analyzer': '#C75146',     // red
    'implementor': '#5B9BD5',  // blue
    'tester': '#F4B042'        // yellow
  }
  return colors[agent.agent_type] || '#666'
})
```

---

### 9. LaunchJobsButton.vue

**Purpose**: Button to launch all agent jobs

**Template:**
```vue
<template>
  <v-btn
    color="success"
    size="large"
    :disabled="!enabled"
    :loading="loading"
    @click="$emit('launch')"
  >
    <v-icon left>mdi-play</v-icon>
    Launch Jobs
  </v-btn>
</template>
```

**Props:**
```typescript
interface Props {
  enabled: boolean
  loading: boolean
}
```

**Emits:**
```typescript
const emit = defineEmits<{
  launch: []
}>()
```

---

## Implementation Tab Components

### 10. ImplementationTabPanel.vue

**Purpose**: Container for Implementation tab (Status Board)

**Template:**
```vue
<template>
  <v-card class="implementation-tab-panel" flat>
    <!-- CLI Mode Controls -->
    <div class="cli-controls mb-4">
      <CLIModeToggle
        v-model="cliMode"
        @update:modelValue="handleCLIModeChange"
      />
      <CLIModeBanner :mode="cliModeBannerText" />
    </div>

    <!-- Status Board -->
    <StatusBoard
      :agents="agents"
      :cli-mode="cliMode"
      @copy-prompt="handleCopyPrompt"
      @view-messages="handleViewMessages"
      @view-info="handleViewInfo"
    />

    <!-- Message Queue -->
    <MessageQueuePanel
      :agents="agents"
      @send-message="handleSendMessage"
      @send-broadcast="handleSendBroadcast"
    />
  </v-card>
</template>
```

**Props:**
```typescript
interface Props {
  projectId: string
}
```

**Data/State:**
```typescript
interface State {
  cliMode: boolean // true = Claude Code CLI, false = General CLI
  agents: Agent[]
}
```

**Computed:**
```typescript
cliModeBannerText = computed(() => {
  return cliMode.value ? 'claude-code' : 'general'
})
```

---

### 11. CLIModeToggle.vue

**Purpose**: Toggle between Claude Code CLI and General CLI modes

**Template:**
```vue
<template>
  <div class="cli-mode-toggle">
    <v-switch
      :model-value="modelValue"
      color="success"
      label="Claude Subagents"
      hide-details
      @update:model-value="$emit('update:modelValue', $event)"
    >
      <template #label>
        <div class="d-flex align-center">
          <span class="mr-2">Claude Subagents</span>
          <v-tooltip location="bottom">
            <template #activator="{ props }">
              <v-icon v-bind="props" size="small">
                mdi-information-outline
              </v-icon>
            </template>
            <div style="max-width: 300px">
              <strong>ON:</strong> Claude Code CLI Mode - Only orchestrator needs prompt, subagents managed internally.<br>
              <strong>OFF:</strong> General CLI Mode - Each agent needs separate terminal.
            </div>
          </v-tooltip>
        </div>
      </template>
    </v-switch>
  </div>
</template>
```

**Props:**
```typescript
interface Props {
  modelValue: boolean
}
```

**Emits:**
```typescript
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()
```

---

### 12. CLIModeBanner.vue

**Purpose**: Display prominent banner indicating current CLI mode

**Template:**
```vue
<template>
  <v-alert
    :type="bannerType"
    :color="bannerColor"
    variant="tonal"
    prominent
    class="cli-mode-banner mt-2"
  >
    <template #prepend>
      <v-icon :icon="bannerIcon" size="large" />
    </template>
    <div class="banner-content">
      <strong>{{ bannerTitle }}</strong>
      <div class="text-caption mt-1">{{ bannerSubtext }}</div>
    </div>
  </v-alert>
</template>
```

**Props:**
```typescript
interface Props {
  mode: 'claude-code' | 'general'
}
```

**Computed:**
```typescript
bannerType = computed(() => props.mode === 'claude-code' ? 'error' : 'success')
bannerColor = computed(() => props.mode === 'claude-code' ? 'red' : 'green')

bannerIcon = computed(() => {
  return props.mode === 'claude-code'
    ? 'mdi-code-braces'
    : 'mdi-console-line'
})

bannerTitle = computed(() => {
  return props.mode === 'claude-code'
    ? 'CLAUDE CODE CLI MODE'
    : 'General CLI MODE (individual terminals for agents)'
})

bannerSubtext = computed(() => {
  return props.mode === 'claude-code'
    ? 'Copy orchestrator prompt only. Subagents managed by Claude Code.'
    : 'Copy each agent prompt to separate terminal windows.'
})
```

---

### 13. StatusBoard.vue

**Purpose**: Table displaying all agents and their statuses

**Template:**
```vue
<template>
  <v-card class="status-board" outlined>
    <v-table fixed-header height="400px">
      <thead>
        <tr>
          <th>Agent Type</th>
          <th>Agent ID</th>
          <th>Agent Status</th>
          <th>Job Read</th>
          <th>Job Ack</th>
          <th>Msgs Sent</th>
          <th>Msgs Wait</th>
          <th>Msgs Read</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        <AgentRow
          v-for="agent in agents"
          :key="agent.id"
          :agent="agent"
          :cli-mode="cliMode"
          :disabled="isSubagentDisabled(agent)"
          @copy-prompt="$emit('copy-prompt', agent)"
          @view-messages="$emit('view-messages', agent)"
          @view-info="$emit('view-info', agent)"
        />
      </tbody>
    </v-table>
  </v-card>
</template>
```

**Props:**
```typescript
interface Props {
  agents: Agent[]
  cliMode: boolean // true = Claude Code CLI
}
```

**Emits:**
```typescript
const emit = defineEmits<{
  'copy-prompt': [agent: Agent]
  'view-messages': [agent: Agent]
  'view-info': [agent: Agent]
}>()
```

**Methods:**
```typescript
isSubagentDisabled(agent: Agent): boolean {
  // In Claude Code CLI mode, only orchestrator is active
  return cliMode && agent.agent_type !== 'orchestrator'
}
```

---

### 14. AgentRow.vue

**Purpose**: Single row in status board table

**Template:**
```vue
<template>
  <tr :class="{ 'agent-row--disabled': disabled }">
    <!-- Agent Type -->
    <td>
      <div class="d-flex align-center">
        <AgentAvatar
          :agent-type="agent.agent_type"
          :color="agentColor"
          size="32"
        />
        <span class="ml-2">{{ agentName }}</span>
      </div>
    </td>

    <!-- Agent ID -->
    <td>
      <v-tooltip location="bottom">
        <template #activator="{ props }">
          <span v-bind="props" class="agent-id-truncated">
            {{ truncatedId }}
          </span>
        </template>
        {{ agent.id }}
      </v-tooltip>
    </td>

    <!-- Agent Status -->
    <td>
      <AgentStatusBadge :status="agent.status" />
    </td>

    <!-- Job Read -->
    <td class="text-center">
      <v-icon v-if="agent.job_read" color="success" size="small">
        mdi-check-circle
      </v-icon>
    </td>

    <!-- Job Acknowledged -->
    <td class="text-center">
      <v-icon v-if="agent.job_acknowledged" color="success" size="small">
        mdi-check-circle
      </v-icon>
    </td>

    <!-- Messages Sent -->
    <td class="text-center">{{ agent.messages_sent || 0 }}</td>

    <!-- Messages Waiting -->
    <td class="text-center">
      <v-badge
        v-if="agent.messages_waiting > 0"
        :content="agent.messages_waiting"
        color="warning"
      >
        {{ agent.messages_waiting }}
      </v-badge>
      <span v-else>0</span>
    </td>

    <!-- Messages Read -->
    <td class="text-center">{{ agent.messages_read || 0 }}</td>

    <!-- Actions -->
    <td>
      <AgentActions
        :agent="agent"
        :disabled="disabled"
        @copy-prompt="$emit('copy-prompt')"
        @view-messages="$emit('view-messages')"
        @view-info="$emit('view-info')"
      />
    </td>
  </tr>
</template>
```

**Props:**
```typescript
interface Props {
  agent: Agent
  cliMode: boolean
  disabled: boolean
}
```

**Computed:**
```typescript
truncatedId = computed(() => {
  return agent.id.substring(0, 8) + '...'
})
```

---

### 15. AgentStatusBadge.vue

**Purpose**: Display agent status with appropriate styling

**Template:**
```vue
<template>
  <v-chip
    :color="statusColor"
    :variant="statusVariant"
    size="small"
    class="agent-status-badge"
  >
    {{ displayStatus }}
  </v-chip>
</template>
```

**Props:**
```typescript
interface Props {
  status: 'Waiting' | 'Working' | 'Working...' | 'Completed!'
}
```

**Computed:**
```typescript
statusColor = computed(() => {
  switch (props.status) {
    case 'Waiting': return 'grey'
    case 'Working': return 'info'
    case 'Working...': return 'info'
    case 'Completed!': return 'success'
    default: return 'grey'
  }
})

statusVariant = computed(() => {
  return props.status.startsWith('Working') ? 'flat' : 'tonal'
})

displayStatus = computed(() => {
  return props.status.replace('!', '')
})
```

---

### 16. AgentActions.vue

**Purpose**: Action buttons for each agent row

**Template:**
```vue
<template>
  <div class="agent-actions d-flex align-center">
    <!-- Copy Prompt Button -->
    <v-btn
      :icon="promptIcon"
      size="small"
      variant="text"
      :disabled="disabled"
      :color="promptCopied ? 'info' : 'default'"
      @click="handleCopyPrompt"
    />

    <!-- View Messages Button -->
    <v-btn
      icon="mdi-folder-outline"
      size="small"
      variant="text"
      @click="$emit('view-messages')"
    />

    <!-- View Info Button -->
    <v-btn
      icon="mdi-information-outline"
      size="small"
      variant="text"
      @click="$emit('view-info')"
    />
  </div>
</template>
```

**Props:**
```typescript
interface Props {
  agent: Agent
  disabled: boolean
}
```

**Data:**
```typescript
const promptCopied = ref(false)
```

**Computed:**
```typescript
promptIcon = computed(() => {
  return promptCopied.value ? 'mdi-refresh' : 'mdi-play'
})
```

**Methods:**
```typescript
async handleCopyPrompt() {
  // 1. Fetch agent-specific prompt from API
  const prompt = await api.getAgentPrompt(agent.id)

  // 2. Copy to clipboard
  await navigator.clipboard.writeText(prompt)

  // 3. Show feedback
  promptCopied.value = true
  showToast('Prompt copied! Paste in CLI.')

  // 4. Emit event
  emit('copy-prompt')

  // 5. Reset icon after 2 seconds
  setTimeout(() => {
    promptCopied.value = false
  }, 2000)
}
```

---

### 17. MessageQueuePanel.vue

**Purpose**: Interface for sending messages to agents

**Template:**
```vue
<template>
  <v-card class="message-queue-panel mt-4" outlined>
    <v-card-text>
      <v-row align="center">
        <!-- Recipient Selector -->
        <v-col cols="12" sm="3">
          <RecipientSelector
            v-model:recipient="selectedRecipient"
            v-model:mode="messageMode"
            :agents="agents"
          />
        </v-col>

        <!-- Message Input -->
        <v-col cols="12" sm="7">
          <MessageInput
            v-model="messageText"
            :placeholder="messagePlaceholder"
            @keydown.enter.ctrl="handleSend"
          />
        </v-col>

        <!-- Send Button -->
        <v-col cols="12" sm="2">
          <SendButton
            :disabled="!canSend"
            @send="handleSend"
          />
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>
```

**Props:**
```typescript
interface Props {
  agents: Agent[]
}
```

**Data:**
```typescript
const selectedRecipient = ref<string | null>(null)
const messageMode = ref<'direct' | 'broadcast'>('direct')
const messageText = ref('')
```

**Computed:**
```typescript
messagePlaceholder = computed(() => {
  return messageMode.value === 'broadcast'
    ? 'Broadcast message to all agents...'
    : 'Direct message...'
})

canSend = computed(() => {
  return messageText.value.trim().length > 0 &&
         (messageMode.value === 'broadcast' || selectedRecipient.value)
})
```

**Methods:**
```typescript
async handleSend() {
  if (!canSend.value) return

  if (messageMode.value === 'broadcast') {
    await emit('send-broadcast', messageText.value)
  } else {
    await emit('send-message', {
      recipientId: selectedRecipient.value,
      message: messageText.value
    })
  }

  // Clear input
  messageText.value = ''
}
```

---

### 18. RecipientSelector.vue

**Purpose**: Dropdown to select message recipient or broadcast

**Template:**
```vue
<template>
  <div class="recipient-selector">
    <v-btn-toggle
      v-model="localMode"
      mandatory
      variant="outlined"
      class="mb-2"
      @update:model-value="handleModeChange"
    >
      <v-btn value="direct" size="small">
        Message Agent
      </v-btn>
      <v-btn value="broadcast" size="small">
        Broadcast
      </v-btn>
    </v-btn-toggle>

    <v-select
      v-if="localMode === 'direct'"
      v-model="localRecipient"
      :items="agentOptions"
      item-title="name"
      item-value="id"
      label="Select agent"
      density="compact"
      @update:model-value="$emit('update:recipient', $event)"
    />
  </div>
</template>
```

**Props:**
```typescript
interface Props {
  recipient: string | null
  mode: 'direct' | 'broadcast'
  agents: Agent[]
}
```

**Computed:**
```typescript
agentOptions = computed(() => {
  return agents.map(agent => ({
    id: agent.id,
    name: agentDisplayName(agent)
  }))
})
```

---

### 19. MessageInput.vue

**Purpose**: Text input for message content

**Template:**
```vue
<template>
  <v-text-field
    :model-value="modelValue"
    :placeholder="placeholder"
    density="compact"
    variant="outlined"
    hide-details
    clearable
    @update:model-value="$emit('update:modelValue', $event)"
    @keydown.enter.ctrl="$emit('send')"
  />
</template>
```

---

### 20. SendButton.vue

**Purpose**: Button to send message

**Template:**
```vue
<template>
  <v-btn
    color="warning"
    size="large"
    block
    :disabled="disabled"
    @click="$emit('send')"
  >
    <v-icon>mdi-send</v-icon>
  </v-btn>
</template>
```

---

## Shared Components

### 21. AgentAvatar.vue

**Purpose**: Circular avatar with agent initials

**Template:**
```vue
<template>
  <v-avatar
    :size="size"
    :color="color"
  >
    <span class="agent-initials">{{ initials }}</span>
  </v-avatar>
</template>
```

**Props:**
```typescript
interface Props {
  agentType: string
  color: string
  size?: number | string
}
```

**Computed:**
```typescript
initials = computed(() => {
  const initialsMap = {
    'orchestrator': 'Or',
    'analyzer': 'An',
    'implementor': 'Im',
    'tester': 'Te'
  }
  return initialsMap[props.agentType] || props.agentType.substring(0, 2).toUpperCase()
})
```

---

## Component Data Flow

```
User Action → Component Event → Parent Handler → API Call → WebSocket → State Update → Re-render
```

**Example: Copy Prompt Flow**

```
1. User clicks ▶ on AgentRow
   ↓
2. AgentActions.vue emits @copy-prompt
   ↓
3. AgentRow.vue emits @copy-prompt (bubbles up)
   ↓
4. StatusBoard.vue emits @copy-prompt
   ↓
5. ImplementationTabPanel.vue handles event:
   - Fetches prompt from API
   - Copies to clipboard
   - Shows toast notification
   ↓
6. (Optional) API updates agent status
   ↓
7. WebSocket pushes status change
   ↓
8. Pinia store updates agent
   ↓
9. Component re-renders with new status
```

---

## Styling Guidelines

### Colors

```scss
$orchestrator-color: #C9A961; // tan
$analyzer-color: #C75146;     // red
$implementor-color: #5B9BD5;  // blue
$tester-color: #F4B042;        // yellow

$status-waiting: #757575;      // grey
$status-working: #2196F3;      // blue
$status-completed: #4CAF50;    // green

$cli-mode-claude: #EF5350;     // red banner
$cli-mode-general: #66BB6A;    // green banner
```

### Typography

```scss
.agent-initials {
  font-weight: 600;
  font-size: 14px;
}

.status-indicator {
  font-weight: 500;
  text-transform: capitalize;
}

.agent-id-truncated {
  font-family: monospace;
  font-size: 12px;
}
```

---

## Next Document

[03_DATA_FLOW.md](./03_DATA_FLOW.md) - State management and data flow architecture

---

**Document Version**: 1.0
**Last Updated**: 2025-11-21
