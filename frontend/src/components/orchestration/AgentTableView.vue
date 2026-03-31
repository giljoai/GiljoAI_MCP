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
    <!-- Agent Type Column — tinted square badge (0870j) -->
    <template #item.agent_display_name="{ item }">
      <div class="agent-cell">
        <div class="agent-badge" :style="getAgentBadgeStyle(item.agent_display_name)">
          {{ getAgentAbbreviation(item.agent_display_name) }}
        </div>
        <div class="agent-cell-info">
          <span class="agent-cell-name">{{ item.agent_name || item.agent_display_name }}</span>
          <span
            v-if="item.agent_name && item.agent_name !== item.agent_display_name"
            class="agent-cell-skills"
          >
            {{ item.agent_display_name }}
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

    <!-- Agent ID Column (Handover 0240b; Handover 0366d-1: display agent_id not job_id) -->
    <template #item.agent_id="{ item }">
      <code class="agent-id" data-testid="agent-id">{{ item.agent_id ? item.agent_id.slice(0, 8) : '—' }}</code>
    </template>

    <!-- Job ID Column (Handover 0366d-1: NEW) -->
    <template #item.job_id="{ item }">
      <code class="agent-id" data-testid="job-id">{{ item.job_id ? item.job_id.slice(0, 8) : '—' }}</code>
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
    <template #item.messages_sent_count="{ item }">
      <span class="text-body-2">{{ item.messages_sent_count || 0 }}</span>
    </template>

    <!-- Messages Waiting Column — tinted badge (0870j) -->
    <template #item.messages_waiting_count="{ item }">
      <span class="msg-badge" :class="(item.messages_waiting_count || 0) > 0 ? 'has-msgs' : 'zero'">
        {{ item.messages_waiting_count || 0 }}
      </span>
    </template>

    <!-- Messages Read Column (Handover 0240b) -->
    <template #item.messages_read_count="{ item }">
      <span class="text-body-2">{{ item.messages_read_count || 0 }}</span>
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


</template>

<script setup>
import { computed, ref } from 'vue'
import { useAgentData } from '@/composables/useAgentData'
import { useClipboard } from '@/composables/useClipboard'
import { useToast } from '@/composables/useToast'
import { useStalenessMonitor } from '@/composables/useStalenessMonitor'
import api from '@/services/api'
import { hexToRgba } from '@/utils/colorUtils'
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
  getAgentDisplayNameColor,
  getAgentAbbreviation,
} = useAgentData(computed(() => props.agents))

/**
 * 0870j: Tinted square badge style for agent
 */
function getAgentBadgeStyle(displayName) {
  const colorObj = getAgentDisplayNameColor(displayName)
  const hex = colorObj?.hex || '#8895a8'
  return {
    background: hexToRgba(hex, 0.15),
    color: hex,
  }
}

// Handover 0230: Clipboard functionality
const { copy } = useClipboard()
const { showToast } = useToast()
const copyingJobId = ref(null)

// Handover 0234: Staleness monitoring (notifications now go to notification bell)
useStalenessMonitor(computed(() => props.agents))

// Table headers configuration (Handover 0240b, updated for Steps column; Handover 0366d-1: Added Job ID; Handover 0700i: Removed Instance)
const headers = [
  { title: 'Agent Type', key: 'agent_display_name', sortable: true },
  { title: 'Agent ID', key: 'agent_id', sortable: false },
  { title: 'Job ID', key: 'job_id', sortable: false },
  { title: 'Agent Status', key: 'status', sortable: true },
  { title: 'Steps', key: 'steps', sortable: false, align: 'center' },
  { title: 'Messages Sent', key: 'messages_sent_count', sortable: true, align: 'center' },
  { title: 'Messages Waiting', key: 'messages_waiting_count', sortable: true, align: 'center' },
  { title: 'Messages Read', key: 'messages_read_count', sortable: true, align: 'center' },
  { title: '', key: 'actions', sortable: false },
]

// Handle row click event
function handleRowClick(event, { item }) {
  emit('row-click', item)
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
 * Handle orchestrator session refresh result from ActionIcons.
 * ActionIcons handles the API call internally and emits the result.
 */
function handleHandOver(event) {
  if (event.success) {
    showToast({ message: event.message || 'Session refreshed! Continuation prompt copied to clipboard.', type: 'success' })
  } else {
    console.error('[AgentTableView] Session refresh failed:', event.error)
    showToast({ message: event.error || 'Failed to refresh session', type: 'error' })
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
      showToast({ message: 'Prompt copied to clipboard!', type: 'success' })
    } else {
      throw new Error('Clipboard copy failed')
    }
  } catch (error) {
    console.error('[AgentTableView] Copy prompt failed:', error)
    showToast({ message: 'Failed to copy prompt', type: 'error' })
  } finally {
    copyingJobId.value = null
  }
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
    return agent.is_orchestrator || agent.agent_display_name === 'orchestrator'
  }

  // General CLI mode: all agent prompts can be copied
  return true
}
</script>

<style scoped lang="scss">
@use '../../styles/design-tokens' as *;

/* Table panel styling (0870j) */
.agent-table-view {
  border-radius: 16px;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.10);
  overflow: hidden;
}

.agent-table-view :deep(tbody tr) {
  cursor: pointer;
  transition: background 0.15s;
}

.agent-table-view :deep(tbody tr:hover) {
  background: rgba(255, 255, 255, 0.02);
}

.agent-table-view :deep(.v-data-table__th) {
  font-size: 0.6rem !important;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: $color-text-muted !important;
  font-weight: 500 !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08) !important;
}

.agent-table-view :deep(.v-data-table__td) {
  padding: 12px 14px;
  font-size: 0.78rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04) !important;
}

/* Agent cell — tinted badge + name (0870j) */
.agent-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.agent-badge {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  font-size: 0.62rem;
  font-weight: 700;
  flex-shrink: 0;
}

.agent-cell-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.agent-cell-name {
  font-size: 0.8rem;
  font-weight: 500;
  text-transform: capitalize;
}

.agent-cell-skills {
  font-size: 0.62rem;
  color: $color-text-muted;
  text-transform: capitalize;
}

/* Messages waiting badge — tinted (0870j) */
.msg-badge {
  display: inline-grid;
  place-items: center;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  font-size: 0.62rem;
  font-weight: 600;
}

.msg-badge.zero {
  background: rgba(103, 189, 109, 0.12);
  color: #67bd6d; /* design-token-exempt: status-complete */
}

.msg-badge.has-msgs {
  background: rgba(255, 152, 0, 0.15);
  color: #ff9800; /* design-token-exempt: status-blocked */
}

/* Disabled rows in Claude Code mode */
.agent-table-view :deep(.disabled-agent-row) {
  opacity: 0.6;
}

.agent-table-view :deep(.disabled-agent-row:hover) {
  background: rgba(255, 255, 255, 0.01);
}

.agent-table-view :deep(.v-btn:disabled) {
  opacity: 0.4;
}

/* Agent ID styling */
.agent-id {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.72rem;
  background: rgba(255, 255, 255, 0.05);
  padding: 2px 6px;
  border-radius: 4px;
  color: $color-text-secondary;
}
</style>
