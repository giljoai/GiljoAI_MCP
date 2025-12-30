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
        <div class="d-flex flex-column">
          <span class="font-weight-medium text-capitalize">{{ item.agent_name || item.agent_type }}</span>
          <span
            v-if="item.agent_name && item.agent_name !== item.agent_type"
            class="text-caption text-grey text-capitalize"
          >
            {{ item.agent_type }}
          </span>
        </div>
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

    <!-- Instance Number Column (Handover 0366d-1) -->
    <template #item.instance_number="{ item }">
      <v-chip size="small" color="blue-grey" label data-testid="instance-chip">
        #{{ item.instance_number || 1 }}
      </v-chip>
    </template>

    <!-- Agent ID Column (Handover 0240b; Handover 0366d-1: display agent_id not job_id) -->
    <template #item.agent_id="{ item }">
      <code class="agent-id" data-testid="agent-id">{{ item.agent_id ? item.agent_id.slice(0, 8) : '—' }}</code>
    </template>

    <!-- Job ID Column (Handover 0366d-1: NEW) -->
    <template #item.job_id="{ item }">
      <code class="agent-id" data-testid="job-id">{{ item.job_id ? item.job_id.slice(0, 8) : '—' }}</code>
    </template>


    <!-- Job Acknowledged Column (Handover 0240b) -->
    <template #item.job_acknowledged="{ item }">
      <v-icon :color="item.mission_acknowledged_at ? 'success' : 'grey'" size="small">
        {{ item.mission_acknowledged_at ? 'mdi-check-circle' : 'mdi-minus-circle-outline' }}
      </v-icon>
    </template>

    <!-- Steps Column (Handover 0297: TODO progress summary) -->
    <template #item.steps="{ item }">
      <span class="text-body-2">
        <span v-if="typeof item.steps_completed === 'number' && typeof item.steps_total === 'number'">
          {{ item.steps_completed }} / {{ item.steps_total }}
        </span>
        <span v-else>—</span>
      </span>
    </template>

    <!-- Messages Sent Column (Handover 0240b) -->
    <template #item.messages_sent="{ item }">
      <span class="text-body-2">{{ item.messages_sent || 0 }}</span>
    </template>

    <!-- Messages Waiting Column (Handover 0240b) -->
    <template #item.messages_waiting="{ item }">
      <span class="text-body-2" :class="{ 'text-warning': item.messages_waiting > 0 }">
        {{ item.messages_waiting || 0 }}
      </span>
    </template>

    <!-- Messages Read Column (Handover 0240b) -->
    <template #item.messages_read="{ item }">
      <span class="text-body-2">{{ item.messages_read || 0 }}</span>
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
import { shouldShowLaunchAction } from '@/utils/actionConfig'

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

// Handover 0234: Staleness monitoring (notifications now go to notification bell)
useStalenessMonitor(computed(() => props.agents))

// Table headers configuration (Handover 0240b, updated for Steps column; Handover 0366d-1: Added Instance and Job ID)
const headers = [
  { title: 'Agent Type', key: 'agent_type', sortable: true },
  { title: 'Instance', key: 'instance_number', sortable: true, align: 'center' },
  { title: 'Agent ID', key: 'agent_id', sortable: false },
  { title: 'Job ID', key: 'job_id', sortable: false },
  { title: 'Job Acknowledged', key: 'job_acknowledged', sortable: false, align: 'center' },
  { title: 'Agent Status', key: 'status', sortable: true },
  { title: 'Steps', key: 'steps', sortable: false, align: 'center' },
  { title: 'Messages Sent', key: 'messages_sent', sortable: true, align: 'center' },
  { title: 'Messages Waiting', key: 'messages_waiting', sortable: true, align: 'center' },
  { title: 'Messages Read', key: 'messages_read', sortable: true, align: 'center' },
  { title: '', key: 'actions', sortable: false },
]

// Handle row click event
function handleRowClick(event, { item }) {
  emit('row-click', item)
}

/**
 * Handover 0229: Determine if agent can be launched
 * Handover 0260: Consolidated to use actionConfig.shouldShowLaunchAction()
 *
 * Terminal states: cannot be launched
 * Blocked state: cannot be launched
 * Claude Code mode: only orchestrator can be launched
 */
function canLaunchAgent(agent) {
  // Handover 0260: Use consolidated function from actionConfig.js
  return shouldShowLaunchAction(agent, props.usingClaudeCodeSubagents)
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

/* Handover 0240b: Agent ID styling */
.agent-id {
  font-family: 'Courier New', monospace;
  font-size: 0.75rem;
  background: rgba(0, 0, 0, 0.2);
  padding: 2px 6px;
  border-radius: 4px;
}

/* Handover 0366d-1: Instance chip styling */
.agent-table-view :deep(.instance-chip) {
  min-width: 40px;
  justify-content: center;
}
</style>
