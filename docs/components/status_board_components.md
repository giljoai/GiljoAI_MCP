# StatusBoard Component API Documentation

Developer reference for StatusBoard components created in Handovers 0234-0235.

---

## Overview

StatusBoard components provide reusable UI elements for displaying and interacting with agent jobs in the status board table. All components follow Vue 3 Composition API patterns with props-based configuration and event emission.

**Component Location**: `frontend/src/components/StatusBoard/`

**Components**:
1. `StatusChip.vue` - Status badge with health indicators
2. `ActionIcons.vue` - Agent action buttons
3. `JobReadAckIndicators.vue` - Read/acknowledged checkmarks

**Utilities**:
- `statusConfig.js` - Status/health configuration and helper functions
- `actionConfig.js` - Action availability logic and configuration

**Composables**:
- `useStalenessMonitor.js` - Staleness detection for agents

**Integration**:
- `AgentTableView.vue` - Reusable status board table (`frontend/src/components/orchestration/`)

---

## StatusChip.vue

Visual status indicator with health overlay and staleness warnings.

### Location
`frontend/src/components/StatusBoard/StatusChip.vue`

### Props

| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `status` | String | Yes | - | Agent status key (waiting, working, blocked, complete, failed, cancelled, decommissioned) |
| `healthStatus` | String | No | `'healthy'` | Health status key (healthy, warning, critical, timeout, unknown) |
| `lastProgressAt` | String | No | `null` | ISO 8601 timestamp of last progress update |
| `minutesSinceProgress` | Number | No | `null` | Number of minutes since last progress (calculated if not provided) |

### Example Usage

```vue
<template>
  <StatusChip
    status="working"
    health-status="warning"
    :last-progress-at="job.last_progress_at"
    :minutes-since-progress="job.minutes_since_progress"
  />
</template>

<script setup>
import StatusChip from '@/components/StatusBoard/StatusChip.vue'
</script>
```

### Visual Elements

- **Status chip**: Colored chip with icon and label (color/icon from statusConfig)
- **Health indicator**: Small dot overlay (top-right) with pulse animation for warning/critical
- **Staleness indicator**: Clock-alert icon if no activity >10 minutes
- **Tooltip**: Shows status description, health status, failure count, and last activity time

### Styling

The component includes:
- `.status-chip` - Base chip styling with relative positioning
- `.status-chip--stale` - Border styling for stale agents
- `.health-indicator` - Dot overlay positioning and styling
- `.pulse-animation` - CSS keyframe animation for critical health
- `.status-tooltip` - Tooltip container with max-width

---

## ActionIcons.vue

Action buttons for launching, copying prompts, viewing messages, and managing agents.

### Location
`frontend/src/components/StatusBoard/ActionIcons.vue`

### Props

| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `job` | Object | Yes | - | Agent job object (must contain job_id, status, agent_type, unread_count) |
| `claudeCodeCliMode` | Boolean | No | `false` | If true, only orchestrator can be launched |

### Events

| Event | Payload | Description |
|-------|---------|-------------|
| `launch` | job object | Emitted when launch button clicked |
| `copy-prompt` | job object | Emitted when copy button clicked (prompt already copied to clipboard) |
| `view-messages` | job object | Emitted when message button clicked |
| `cancel` | job object | Emitted when cancel confirmed in dialog |
| `hand-over` | job object | Emitted when hand over confirmed in dialog |

### Example Usage

```vue
<template>
  <ActionIcons
    :job="agentJob"
    :claude-code-cli-mode="usingClaudeCodeSubagents"
    @launch="handleLaunchAgent"
    @copy-prompt="handleCopyPrompt"
    @view-messages="handleViewMessages"
    @cancel="handleCancelAgent"
    @hand-over="handleHandOver"
  />
</template>

<script setup>
import ActionIcons from '@/components/StatusBoard/ActionIcons.vue'

const handleLaunchAgent = (job) => {
  console.log('Launching agent:', job.job_id)
}

const handleCopyPrompt = (job) => {
  console.log('Prompt copied for agent:', job.job_id)
}

const handleViewMessages = (job) => {
  console.log('Viewing messages for agent:', job.job_id)
}

const handleCancelAgent = (job) => {
  console.log('Cancelling agent:', job.job_id)
}

const handleHandOver = (job) => {
  console.log('Triggering handover for orchestrator:', job.job_id)
}
</script>
```

### Action Buttons

1. **Launch button** (▶️ `mdi-rocket-launch`)
   - Visible when: Agent status is "waiting" AND (claudeCodeCliMode=false OR agent_type="orchestrator")
   - Color: Primary (blue)
   - Loading state: Disabled during launch
   - Tooltip: "Copy prompt to clipboard and launch agent"

2. **Copy prompt button** (📋 `mdi-content-copy`)
   - Visible when: Agent status is not "decommissioned"
   - Color: Grey darken-1
   - Loading state: Disabled during copy
   - Tooltip: "Copy agent prompt to clipboard"
   - Success feedback: Green snackbar

3. **View messages button** (💬 `mdi-message-text`)
   - Always visible
   - Color: Blue
   - Badge: Red badge shows `job.unread_count` if > 0
   - Tooltip: "Open message history"

4. **Cancel button** (✖️ `mdi-cancel`)
   - Visible when: Agent status is working/waiting/blocked
   - Color: Error (red)
   - Confirmation: Shows dialog before emitting event
   - Tooltip: "Cancel this agent job"

5. **Hand over button** (🖐️ `mdi-hand-left`)
   - Visible when: agent_type="orchestrator" AND status="working" AND context usage >= 90%
   - Color: Warning (yellow)
   - Confirmation: Shows dialog before emitting event
   - Tooltip: "Trigger orchestrator succession and hand over context"

### Confirmation Dialogs

Destructive actions (cancel, hand over) show confirmation dialogs:

```vue
<!-- Automatically handled within ActionIcons component -->
<v-dialog v-model="showConfirmDialog" max-width="500">
  <v-card>
    <v-card-title>{{ confirmationConfig.title }}</v-card-title>
    <v-card-text>{{ confirmationConfig.message }}</v-card-text>
    <v-card-actions>
      <v-btn @click="cancelConfirmation">Cancel</v-btn>
      <v-btn :color="confirmationConfig.color" @click="executeConfirmedAction">
        {{ confirmationConfig.confirmText }}
      </v-btn>
    </v-card-actions>
  </v-card>
</v-dialog>
```

### Styling

The component includes comprehensive hover states and animations:
- Opacity transitions on hover (0.75 → 1.0)
- Scale transforms on hover (1.0 → 1.1)
- Brightness filter on hover
- Disabled state styling (opacity 0.4)
- Focus-visible accessibility outline
- Responsive spacing (4px mobile, 8px desktop, 12px large screens)

---

## JobReadAckIndicators.vue

Simple component for read/acknowledged status indicators.

### Location
`frontend/src/components/StatusBoard/JobReadAckIndicators.vue`

### Props

| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `missionReadAt` | String | No | `null` | ISO 8601 timestamp when mission was read (or null) |
| `missionAcknowledgedAt` | String | No | `null` | ISO 8601 timestamp when mission was acknowledged (or null) |

### Example Usage

```vue
<template>
  <div>
    <!-- Mission read indicator -->
    <JobReadAckIndicators
      :mission-read-at="job.mission_read_at"
      :mission-acknowledged-at="job.mission_acknowledged_at"
    />
  </div>
</template>

<script setup>
import JobReadAckIndicators from '@/components/StatusBoard/JobReadAckIndicators.vue'
</script>
```

### Visual Elements

- **Mission read icon**: Green check-circle (if set) or grey minus-circle-outline (if null)
- **Mission acknowledged icon**: Green check-circle (if set) or grey minus-circle-outline (if null)
- **Tooltips**:
  - If set: "Read at {formatted timestamp}" or "Acknowledged at {formatted timestamp}"
  - If null: "Not yet read" or "Not yet acknowledged"

---

## AgentTableView.vue

Reusable status board table component wrapping v-data-table with custom columns.

### Location
`frontend/src/components/orchestration/AgentTableView.vue`

### Props

| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `agents` | Array | Yes | `[]` | Array of agent job objects |
| `mode` | String | No | `'jobs'` | Display mode (affects action column rendering) |
| `usingClaudeCodeSubagents` | Boolean | No | `false` | Passed to ActionIcons for launch button visibility |

### Events

| Event | Payload | Description |
|-------|---------|-------------|
| `launch-agent` | job object | Emitted when agent launched |
| `copy-prompt` | job object | Emitted when prompt copied |
| `view-messages` | job object | Emitted when messages viewed |
| `cancel-agent` | job object | Emitted when agent cancelled |
| `hand-over` | job object | Emitted when hand over triggered |
| `row-click` | job object | Emitted when table row clicked |

### Example Usage

```vue
<template>
  <AgentTableView
    :agents="agents"
    mode="jobs"
    :using-claude-code-subagents="usingClaudeCodeSubagents"
    @launch-agent="handleLaunchAgent"
    @copy-prompt="handleCopyPrompt"
    @view-messages="handleViewMessages"
    @cancel-agent="handleCancelAgent"
    @hand-over="handleHandOver"
  />
</template>

<script setup>
import { ref } from 'vue'
import AgentTableView from '@/components/orchestration/AgentTableView.vue'

const agents = ref([
  {
    job_id: 'abc123',
    agent_type: 'orchestrator',
    status: 'working',
    health_status: 'healthy',
    last_progress_at: '2025-11-22T10:30:00Z',
    mission_read_at: '2025-11-22T10:00:00Z',
    mission_acknowledged_at: '2025-11-22T10:01:00Z',
    messages_sent: 5,
    messages_waiting: 2,
    messages_read: 3,
    unread_count: 2
  }
])

const usingClaudeCodeSubagents = ref(false)
</script>
```

### Table Columns

1. **Agent Type** - Avatar with initials + agent type text
2. **Agent ID** - 8-character UUID (truncated, monospace)
3. **Status** - StatusChip component
4. **Job Read** - Icon (green check or grey dash)
5. **Job Acknowledged** - Icon (green check or grey dash)
6. **Messages Sent** - Numeric count
7. **Messages Waiting** - Numeric count (yellow if > 0)
8. **Messages Read** - Numeric count
9. **Actions** - ActionIcons component (if mode='jobs')

### Sorting

Agents automatically sorted by:
1. Status (custom sort order: working → blocked → waiting → complete → failed → cancelled → decommissioned)
2. Agent type alphabetically (within same status)

Default sort: `[{ key: 'status', order: 'asc' }]`

### No Data State

Shows empty state when no agents:
- Icon: `mdi-table-off` (grey, size 64)
- Text: "No agents to display"

---

## statusConfig.js Utilities

Helper functions for status/health configuration.

### Location
`frontend/src/utils/statusConfig.js`

### Exports

#### STATUS_CONFIG

Object mapping status keys to configuration:

```javascript
{
  waiting: {
    icon: 'mdi-clock-outline',
    color: 'grey',
    label: 'Waiting',
    description: 'Agent is waiting to start'
  },
  working: {
    icon: 'mdi-cog',
    color: 'primary',
    label: 'Working',
    description: 'Agent is actively working'
  },
  blocked: {
    icon: 'mdi-alert-octagon',
    color: 'orange',
    label: 'Blocked',
    description: 'Agent is blocked waiting for input'
  },
  complete: {
    icon: 'mdi-check-circle',
    color: 'yellow-darken-2',
    label: 'Complete',
    description: 'Agent has completed successfully'
  },
  failed: {
    icon: 'mdi-alert-circle',
    color: 'purple',
    label: 'Failure',
    description: 'Agent has failed'
  },
  cancelled: {
    icon: 'mdi-cancel',
    color: 'warning',
    label: 'Cancelled',
    description: 'Agent was cancelled by user'
  },
  decommissioned: {
    icon: 'mdi-archive',
    color: 'grey-darken-1',
    label: 'Decommissioned',
    description: 'Agent has been decommissioned'
  }
}
```

#### HEALTH_CONFIG

Object mapping health status keys to configuration:

```javascript
{
  healthy: {
    icon: null,
    color: 'success',
    label: 'Healthy',
    showIndicator: false
  },
  warning: {
    icon: 'mdi-alert',
    color: 'warning',
    label: 'Warning',
    showIndicator: true,
    dotColor: 'yellow darken-2',
    pulse: false
  },
  critical: {
    icon: 'mdi-alert-octagon',
    color: 'error',
    label: 'Critical',
    showIndicator: true,
    dotColor: 'red',
    pulse: true
  },
  timeout: {
    icon: 'mdi-timer-alert',
    color: 'grey',
    label: 'Timeout',
    showIndicator: true,
    dotColor: 'grey'
  },
  unknown: {
    icon: 'mdi-help-circle',
    color: 'grey lighten-1',
    label: 'Unknown',
    showIndicator: false
  }
}
```

#### getStatusConfig(status)

Returns status configuration object for given status key. Falls back to 'waiting' if unknown.

```javascript
import { getStatusConfig } from '@/utils/statusConfig'

const config = getStatusConfig('working')
// Returns: { icon: 'mdi-cog', color: 'primary', label: 'Working', description: '...' }
```

#### getHealthConfig(healthStatus)

Returns health configuration object for given health status key. Falls back to 'unknown' if unknown.

```javascript
import { getHealthConfig } from '@/utils/statusConfig'

const config = getHealthConfig('warning')
// Returns: { icon: 'mdi-alert', color: 'warning', label: 'Warning', showIndicator: true, dotColor: 'yellow darken-2', pulse: false }
```

#### isJobStale(lastProgressAt, status)

Returns true if job has no activity in >10 minutes (configurable via STALENESS_THRESHOLD).

```javascript
import { isJobStale } from '@/utils/statusConfig'

const stale = isJobStale('2025-11-22T10:00:00Z', 'working')
// Returns: true if current time > 10:10 (more than 10 minutes ago)
```

Terminal states (complete, failed, cancelled, decommissioned) are never considered stale.

#### formatLastActivity(lastProgressAt)

Formats timestamp as relative time string.

```javascript
import { formatLastActivity } from '@/utils/statusConfig'

formatLastActivity('2025-11-22T10:00:00Z')
// Returns: "5 minutes ago" or "2 hours ago" or "3 days ago" or "Never"
```

---

## actionConfig.js Utilities

Helper functions for action availability logic and configuration.

### Location
`frontend/src/utils/actionConfig.js`

### Exports

#### ACTION_CONFIG

Object mapping action keys to configuration:

```javascript
{
  launch: {
    icon: 'mdi-rocket-launch',
    color: 'primary',
    label: 'Launch Agent',
    tooltip: 'Copy prompt to clipboard and launch agent',
    confirmation: false,
    requiresStatus: ['waiting'],
    excludeTerminalStates: true
  },
  copyPrompt: {
    icon: 'mdi-content-copy',
    color: 'grey darken-1',
    label: 'Copy Prompt',
    tooltip: 'Copy agent prompt to clipboard',
    confirmation: false,
    requiresStatus: [],  // Available for all
    excludeTerminalStates: false
  },
  // ... (cancel, viewMessages, handOver)
}
```

#### getAvailableActions(job, claudeCodeCliMode)

Returns array of available action names for given job.

```javascript
import { getAvailableActions } from '@/utils/actionConfig'

const actions = getAvailableActions(
  { status: 'working', agent_type: 'orchestrator' },
  false
)
// Returns: ['copyPrompt', 'viewMessages', 'cancel']
```

#### getActionConfig(actionName)

Returns action configuration object for given action name.

```javascript
import { getActionConfig } from '@/utils/actionConfig'

const config = getActionConfig('launch')
// Returns: { icon: 'mdi-rocket-launch', color: 'primary', label: 'Launch Agent', ... }
```

#### actionRequiresConfirmation(actionName)

Returns true if action requires confirmation dialog.

```javascript
import { actionRequiresConfirmation } from '@/utils/actionConfig'

const needsConfirm = actionRequiresConfirmation('cancel')
// Returns: true (cancel requires confirmation)
```

#### getDisabledReason(actionName, job, claudeCodeCliMode)

Returns reason why action is disabled (for tooltips), or empty string if available.

```javascript
import { getDisabledReason } from '@/utils/actionConfig'

const reason = getDisabledReason('launch', { status: 'working', agent_type: 'implementer' }, true)
// Returns: "Agent must be in waiting status to launch"
```

---

## useStalenessMonitor.js Composable

Composable for detecting stale agents and emitting warnings.

### Location
`frontend/src/composables/useStalenessMonitor.js`

### Usage

```javascript
import { useStalenessMonitor } from '@/composables/useStalenessMonitor'

const { monitorStaleness, stopMonitoring } = useStalenessMonitor(agents, {
  thresholdMinutes: 10,
  onStaleDetected: (job) => {
    console.warn(`Agent ${job.agent_type} is stale (${job.minutes_since_progress} minutes)`)
  }
})

// Start monitoring
monitorStaleness()

// Stop monitoring when component unmounts
onUnmounted(() => {
  stopMonitoring()
})
```

---

## Testing

All StatusBoard components have comprehensive unit tests.

**Test Location**: `frontend/tests/unit/components/StatusBoard/`

**Run tests**:
```bash
cd frontend
npm run test:unit
```

**Coverage target**: >80% for all components

**Test Files**:
- `StatusChip.spec.js` - StatusChip component tests
- `ActionIcons.spec.js` - ActionIcons component tests
- `JobReadAckIndicators.spec.js` - JobReadAckIndicators component tests
- `AgentTableView.spec.js` - AgentTableView integration tests

---

## Future Enhancements

Potential improvements for future handovers:

1. **Table row expansion** - Click row to expand agent details
2. **Column reordering** - Drag-and-drop column reordering
3. **Export to CSV** - Export table data to CSV file
4. **Filter/Search** - Filter agents by status, type, or search by ID
5. **Bulk actions** - Select multiple agents and perform bulk operations
6. **Custom column visibility** - User can show/hide columns
7. **Agent timeline** - Visual timeline showing agent state transitions

---

## Related Documentation

- [Dashboard User Guide](../user_guides/dashboard_guide.md)
- [Architecture Overview](../SERVER_ARCHITECTURE_TECH_STACK.md)
- [Vue 3 Composition API](https://vuejs.org/guide/extras/composition-api-faq.html)
- [Vuetify 3 Components](https://vuetifyjs.com/en/components/all/)
- [Agent Jobs API Reference](../AGENT_JOBS_API_REFERENCE.md)
