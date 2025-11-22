<template>
  <v-data-table
    :headers="headers"
    :items="agents"
    :sort-by="[{ key: 'status', order: 'asc' }]"
    item-key="job_id"
    class="agent-table-view"
    hover
    @click:row="handleRowClick"
  >
    <!-- Agent Type Column -->
    <template #item.agent_type="{ item }">
      <div class="d-flex align-center">
        <v-avatar :color="getAgentTypeColor(item.agent_type)" size="32" class="mr-2">
          <span class="text-caption font-weight-bold white--text">
            {{ getAgentAbbreviation(item.agent_type) }}
          </span>
        </v-avatar>
        <span class="text-capitalize">{{ item.agent_type }}</span>
      </div>
    </template>

    <!-- Status Column (Handover 0234: StatusChip Integration) -->
    <template #item.status="{ item }">
      <StatusChip
        :status="item.status"
        :health-status="item.health_status"
        :last-progress-at="item.last_progress_at"
        :minutes-since-progress="item.minutes_since_progress"
      />
    </template>

    <!-- Messages Column -->
    <template #item.messages="{ item }">
      <div class="d-flex gap-1">
        <v-chip
          v-if="getMessageCounts(item).unread > 0"
          color="error"
          size="x-small"
          prepend-icon="mdi-message-badge"
        >
          {{ getMessageCounts(item).unread }}
        </v-chip>
        <v-chip
          v-if="getMessageCounts(item).acknowledged > 0"
          color="success"
          size="x-small"
          prepend-icon="mdi-check-all"
        >
          {{ getMessageCounts(item).acknowledged }}
        </v-chip>
        <span v-if="getMessageCounts(item).total === 0" class="text-grey">—</span>
      </div>
    </template>

    <!-- Mission Tracking Column (Handover 0233) -->
    <template #item.mission_tracking="{ item }">
      <JobReadAckIndicators
        :mission-read-at="item.mission_read_at"
        :mission-acknowledged-at="item.mission_acknowledged_at"
      />
    </template>

    <!-- Actions Column (Handover 0235: ActionIcons Integration) -->
    <template #item.actions="{ item }">
      <ActionIcons
        v-if="mode === 'jobs'"
        :job="item"
        :claude-code-cli-mode="usingClaudeCodeSubagents"
        @launch="handleLaunchJob"
        @copy-prompt="handleCopyPrompt"
        @view-messages="handleViewMessages"
        @cancel="handleCancelJob"
        @hand-over="handleHandOver"
      />
    </template>

    <!-- No Data State -->
    <template #no-data>
      <div class="text-center py-8">
        <v-icon size="64" color="grey-lighten-1">mdi-table-off</v-icon>
        <p class="text-grey mt-4">No agents to display</p>
      </div>
    </template>
  </v-data-table>

  <!-- Handover 0230: Snackbar for copy feedback -->
  <v-snackbar
    v-model="snackbar.show"
    :color="snackbar.color"
    :timeout="3000"
    location="bottom right"
  >
    {{ snackbar.message }}
    <template #actions>
      <v-btn variant="text" @click="snackbar.show = false">Close</v-btn>
    </template>
  </v-snackbar>

  <!-- Handover 0234: Staleness warning snackbar -->
  <v-snackbar
    v-model="showStaleWarning"
    color="warning"
    :timeout="5000"
    location="bottom"
  >
    <v-icon class="mr-2">mdi-clock-alert</v-icon>
    <strong>{{ staleAgentName }}</strong> has been inactive for over 10 minutes
    <template #actions>
      <v-btn
        variant="text"
        @click="showStaleWarning = false"
      >
        Dismiss
      </v-btn>
    </template>
  </v-snackbar>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useAgentData } from '@/composables/useAgentData'
import { useClipboard } from '@/composables/useClipboard'
import { useStalenessMonitor } from '@/composables/useStalenessMonitor'
import api from '@/services/api'
import JobReadAckIndicators from '@/components/StatusBoard/JobReadAckIndicators.vue'
import StatusChip from '@/components/StatusBoard/StatusChip.vue'
import ActionIcons from '@/components/StatusBoard/ActionIcons.vue'

/**
 * AgentTableView Component
 *
 * Provides a table view for agents using Vuetify's v-data-table.
 * Reuses useAgentData composable for shared logic with card view.
 *
 * Handover 0228: StatusBoardTable Component
 *
 * Props:
 * - agents: Array of agent job objects
 * - mode: 'launch' | 'jobs' (determines action buttons)
 *
 * Emits:
 * - row-click: When user clicks on a table row
 * - launch-agent: When user clicks launch button
 */

const props = defineProps({
  agents: {
    type: Array,
    required: true,
    default: () => [],
  },
  mode: {
    type: String,
    default: 'jobs',
    validator: (value) => ['launch', 'jobs'].includes(value),
  },
  usingClaudeCodeSubagents: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['row-click', 'launch-agent'])

// Reuse shared logic from composable (NO DUPLICATION)
const {
  getStatusColor,
  getAgentTypeColor,
  getAgentAbbreviation,
  getMessageCounts,
  getHealthColor,
  getHealthIcon,
} = useAgentData(computed(() => props.agents))

// Handover 0230: Clipboard functionality
const { copy } = useClipboard()
const copyingJobId = ref(null)
const snackbar = ref({ show: false, message: '', color: 'success' })

// Handover 0234: Staleness monitoring
const showStaleWarning = ref(false)
const staleAgentName = ref('')

const emitStaleWarning = (job) => {
  staleAgentName.value = job.agent_name || job.agent_type
  showStaleWarning.value = true
}

// Initialize staleness monitor
useStalenessMonitor(computed(() => props.agents), emitStaleWarning)

// Table headers configuration (Handover 0234: Removed health_status - now in StatusChip)
const headers = [
  { title: 'Agent Type', key: 'agent_type', sortable: true },
  { title: 'Agent Name', key: 'agent_name', sortable: true },
  { title: 'Status', key: 'status', sortable: true },
  { title: 'Messages', key: 'messages', sortable: false },
  { title: 'Mission Tracking', key: 'mission_tracking', sortable: false },
  { title: 'Actions', key: 'actions', sortable: false },
]

// Handle row click event
function handleRowClick(event, { item }) {
  emit('row-click', item)
}

/**
 * Handover 0229: Determine if agent can be launched
 * Terminal states: cannot be launched
 * Blocked state: cannot be launched
 * Claude Code mode: only orchestrator can be launched
 */
function canLaunchAgent(agent) {
  // Terminal states: cannot be launched
  const terminalStates = ['complete', 'failed', 'cancelled', 'decommissioned']
  if (terminalStates.includes(agent.status)) {
    return false
  }

  // Blocked state: cannot be launched
  if (agent.status === 'blocked') {
    return false
  }

  // Claude Code mode: only orchestrator can be launched
  if (props.usingClaudeCodeSubagents) {
    return agent.is_orchestrator || agent.agent_type === 'orchestrator'
  }

  // General CLI mode: all non-terminal agents can be launched
  return true
}

/**
 * Handover 0235: Handle launch job action from ActionIcons
 */
function handleLaunchJob(job) {
  emit('launch-agent', job)
}

/**
 * Handover 0235: Handle view messages action from ActionIcons
 */
function handleViewMessages(job) {
  emit('row-click', job)
}

/**
 * Handover 0235: Handle cancel job action from ActionIcons
 */
async function handleCancelJob(job) {
  try {
    await api.jobs.cancel(job.job_id)
    showSnackbar('Job cancelled successfully', 'success')
  } catch (error) {
    console.error('[AgentTableView] Cancel job failed:', error)
    showSnackbar('Failed to cancel job', 'error')
  }
}

/**
 * Handover 0235: Handle orchestrator handover action from ActionIcons
 */
async function handleHandOver(job) {
  try {
    await api.orchestration.handOver(job.job_id, 'context_threshold')
    showSnackbar('Orchestrator handover initiated', 'success')
  } catch (error) {
    console.error('[AgentTableView] Handover failed:', error)
    showSnackbar('Failed to trigger handover', 'error')
  }
}

/**
 * Handover 0230: Copy agent prompt to clipboard
 * Fetches prompt from API and copies to clipboard
 */
async function handleCopyPrompt(agent) {
  if (!canCopyPrompt(agent)) return

  copyingJobId.value = agent.job_id

  try {
    // Call existing API endpoint
    const response = await api.prompts.agentPrompt(agent.job_id)
    const prompt = response.data.prompt

    // Copy using existing composable
    const success = await copy(prompt)

    if (success) {
      showSnackbar('Prompt copied to clipboard!', 'success')
    } else {
      throw new Error('Clipboard copy failed')
    }
  } catch (error) {
    console.error('[AgentTableView] Copy prompt failed:', error)
    showSnackbar('Failed to copy prompt', 'error')
  } finally {
    copyingJobId.value = null
  }
}

/**
 * Handover 0230: Show snackbar notification
 */
function showSnackbar(message, color = 'success') {
  snackbar.value = { show: true, message, color }
}

/**
 * Handover 0229: Determine if agent prompt can be copied
 * Decommissioned agents have no prompt
 * Claude Code mode: only orchestrator prompts can be copied
 */
function canCopyPrompt(agent) {
  // Decommissioned agents have no prompt
  if (agent.status === 'decommissioned') {
    return false
  }

  // Claude Code mode: only orchestrator prompts can be copied
  if (props.usingClaudeCodeSubagents) {
    return agent.is_orchestrator || agent.agent_type === 'orchestrator'
  }

  // General CLI mode: all agent prompts can be copied
  return true
}
</script>

<style scoped>
.agent-table-view :deep(tbody tr) {
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.agent-table-view :deep(tbody tr:hover) {
  background-color: rgba(var(--v-theme-primary), 0.05);
}

.agent-table-view :deep(.v-data-table__th) {
  font-weight: 600 !important;
  background-color: rgba(0, 0, 0, 0.02);
}

/* Ensure proper spacing for action buttons */
.agent-table-view :deep(.v-data-table__td) {
  padding: 12px 16px;
}

/* Align health icons to center */
.agent-table-view :deep([data-v-for-health]) {
  display: flex;
  justify-content: center;
}

/* Handover 0229: Visual feedback for disabled rows in Claude Code mode */
.agent-table-view :deep(.disabled-agent-row) {
  opacity: 0.6;
  background-color: rgba(0, 0, 0, 0.02);
}

.agent-table-view :deep(.disabled-agent-row:hover) {
  background-color: rgba(0, 0, 0, 0.04) !important;
}

/* Handover 0229: Disabled action buttons */
.agent-table-view :deep(.v-btn:disabled) {
  opacity: 0.4;
}

.agent-table-view :deep(.v-btn:disabled .v-icon) {
  color: grey !important;
}
</style>
