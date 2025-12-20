<template>
  <div class="implement-tab-wrapper">
    <!-- Agent Table Container -->
    <div class="table-container">
      <table class="agents-table" data-testid="agent-status-table">
        <thead>
          <tr>
            <th>Agent Type</th>
            <th>Instance</th>
            <th>Agent ID</th>
            <th>Agent Status</th>
            <th>Job Acknowledged</th>
            <th>Steps</th>
            <th>Messages Sent</th>
            <th>Messages waiting</th>
            <th>Messages Read</th>
            <th></th>
            <!-- Actions -->
          </tr>
        </thead>
        <tbody>
          <tr v-for="agent in sortedAgents" :key="agent.job_id || agent.agent_id" data-testid="agent-row" :data-agent-type="agent.agent_type" :data-agent-status="agent.status">
            <!-- Agent Type: Avatar + Name -->
            <td class="agent-type-cell">
              <v-avatar :color="getAgentColor(agent.agent_type)" size="32" class="agent-avatar">
                <span class="avatar-text">{{ getAgentAbbr(agent.agent_type) }}</span>
              </v-avatar>
              <div class="agent-info">
                <span class="agent-name-primary">{{ agent.agent_name || agent.agent_type }}</span>
                <span
                  v-if="agent.agent_name && agent.agent_name !== agent.agent_type"
                  class="agent-type-secondary"
                >
                  {{ agent.agent_type }}
                </span>
              </div>
            </td>

            <!-- Instance Number: NEW COLUMN -->
            <td class="instance-cell" data-testid="instance-number">
              <v-chip size="small" color="blue-grey" label>
                #{{ agent.instance_number || 1 }}
              </v-chip>
            </td>

            <!-- Agent ID: Dual display -->
            <td class="agent-id-cell" data-testid="agent-id">
              <div class="id-container">
                <div class="id-row">
                  <span class="id-label">Agent:</span>
                  <code class="id-value">{{ (agent.agent_id || agent.job_id || '—').slice(0, 8) }}</code>
                </div>
                <div class="id-row">
                  <span class="id-label">Job:</span>
                  <code class="id-value">{{ (agent.job_id || '—').slice(0, 8) }}</code>
                </div>
              </div>
            </td>

            <!-- Agent Status: Dynamic binding from agent.status -->
            <td
              class="status-cell"
              data-testid="status-chip"
              :style="{
                color: getStatusColor(agent.status),
                fontStyle: isStatusItalic(agent.status) ? 'italic' : 'normal'
              }"
            >
              {{ getStatusLabel(agent.status) }}
            </td>


            <!-- Job Acknowledged -->
            <td class="checkbox-cell">
              <!-- Checkmark when acknowledged -->
              <v-icon
                v-if="agent.mission_acknowledged_at"
                icon="mdi-check"
                color="success"
                size="small"
                :title="formatAcknowledgmentTooltip(agent.mission_acknowledged_at)"
                :aria-label="formatAcknowledgmentTooltip(agent.mission_acknowledged_at)"
              />
              <!-- Dash when not acknowledged -->
              <v-icon
                v-else
                icon="mdi-minus-circle-outline"
                color="grey"
                size="small"
                title="Not yet acknowledged"
                aria-label="Mission not yet acknowledged"
              />
            </td>

            <!-- Steps (numeric TODO progress) -->
            <td class="steps-cell text-center">
              <button
                v-if="agent.steps && typeof agent.steps.completed === 'number' && typeof agent.steps.total === 'number'"
                type="button"
                class="steps-trigger"
                data-testid="steps-trigger"
                @click="handleStepsClick(agent)"
              >
                {{ agent.steps.completed }} / {{ agent.steps.total }}
              </button>
              <span v-else>—</span>
            </td>

            <!-- Messages Sent -->
            <td class="messages-sent-cell text-center">
              <span class="message-count">{{ getMessagesSent(agent) }}</span>
            </td>

            <!-- Messages Waiting -->
            <td class="messages-waiting-cell text-center">
              <span class="message-count message-waiting">{{ getMessagesWaiting(agent) }}</span>
            </td>

            <!-- Messages Read -->
            <td class="messages-read-cell text-center">
              <span class="message-count message-read">{{ getMessagesRead(agent) }}</span>
            </td>

            <!-- Actions -->
            <td class="actions-cell">
              <!-- Play button: visibility controlled by Claude Code CLI toggle (Handover 0243d) -->
              <v-tooltip v-if="shouldShowCopyButton(agent)" text="Copy prompt">
                <template #activator="{ props: tooltipProps }">
                  <v-btn
                    v-bind="tooltipProps"
                    icon="mdi-play"
                    size="small"
                    variant="text"
                    color="yellow-darken-2"
                    @click="handlePlay(agent)"
                  />
                </template>
              </v-tooltip>

              <!-- Messages button: opens Message Audit Modal (Handover 0358) -->
              <v-tooltip text="View messages">
                <template #activator="{ props: tooltipProps }">
                  <v-btn
                    v-bind="tooltipProps"
                    icon="mdi-message-outline"
                    size="small"
                    variant="text"
                    color="yellow-darken-2"
                    data-testid="jobs-messages-btn"
                    @click="handleMessages(agent)"
                  />
                </template>
              </v-tooltip>

              <!-- GiljoAI Face button: shows agent role/template (Handover 0358) -->
              <v-tooltip text="View agent role">
                <template #activator="{ props: tooltipProps }">
                  <v-btn
                    v-bind="tooltipProps"
                    size="small"
                    variant="text"
                    data-testid="jobs-role-btn"
                    @click="handleAgentRole(agent)"
                  >
                    <img
                      :src="giljoFaceIcon"
                      alt="Agent Role"
                      class="giljo-face-icon"
                    />
                  </v-btn>
                </template>
              </v-tooltip>

              <!-- Job button: shows agent job/mission (Handover 0358) -->
              <v-tooltip text="View assigned job">
                <template #activator="{ props: tooltipProps }">
                  <v-btn
                    v-bind="tooltipProps"
                    icon="mdi-briefcase-outline"
                    size="small"
                    variant="text"
                    color="white"
                    data-testid="jobs-info-btn"
                    @click="handleAgentJob(agent)"
                  />
                </template>
              </v-tooltip>

              <!-- Cancel button: only when working (Handover 0243d) -->
              <v-tooltip v-if="agent.status === 'working'" text="Cancel job">
                <template #activator="{ props: tooltipProps }">
                  <v-btn
                    v-bind="tooltipProps"
                    icon="mdi-cancel"
                    size="small"
                    variant="text"
                    color="warning"
                    @click="confirmCancelJob(agent)"
                  />
                </template>
              </v-tooltip>

              <!-- Hand Over button: only for working orchestrators (Handover 0243d) -->
              <v-tooltip
                v-if="agent.agent_type === 'orchestrator' && agent.status === 'working'"
                text="Hand over"
              >
                <template #activator="{ props: tooltipProps }">
                  <v-btn
                    v-bind="tooltipProps"
                    icon="mdi-hand-wave"
                    size="small"
                    variant="text"
                    color="warning"
                    @click="openHandoverDialog(agent)"
                  />
                </template>
              </v-tooltip>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Message Composer (Bottom) -->
    <div class="message-composer">
      <v-btn
        class="recipient-btn"
        :variant="selectedRecipient === 'orchestrator' ? 'flat' : 'outlined'"
        rounded
        color="yellow-darken-2"
        @click="selectedRecipient = 'orchestrator'"
      >
        Orchestrator
      </v-btn>

      <v-btn
        class="broadcast-btn"
        :variant="selectedRecipient === 'broadcast' ? 'flat' : 'outlined'"
        rounded
        color="yellow-darken-2"
        @click="selectedRecipient = 'broadcast'"
      >
        Broadcast
      </v-btn>

      <v-text-field
        v-model="messageText"
        class="message-input"
        placeholder="Type message..."
        variant="outlined"
        density="compact"
        hide-details
        @keyup.enter="sendMessage"
      />

      <v-btn
        icon="mdi-play"
        class="send-btn"
        color="yellow-darken-2"
        :loading="sending"
        :disabled="!messageText.trim()"
        @click="sendMessage"
      />
    </div>

    <!-- Cancel Job Confirmation Dialog (Handover 0243d) -->
    <v-dialog v-model="showCancelDialog" max-width="500">
      <v-card>
        <v-card-title>Cancel Agent Job?</v-card-title>
        <v-card-text>
          The agent will stop work on its next check-in. This action cannot be undone.

          <div class="agent-info mt-4">
            <div><strong>Agent Type:</strong> {{ selectedAgent?.agent_type }}</div>
            <div><strong>Job ID:</strong> {{ selectedAgent?.job_id }}</div>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn text @click="showCancelDialog = false">No, keep running</v-btn>
          <v-btn color="error" @click="cancelJob">Yes, cancel</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Hand Over Dialog (Handover 0243d) -->
    <LaunchSuccessorDialog
      v-if="selectedAgent"
      :job-id="selectedAgent.job_id || selectedAgent.agent_id"
      :current-job="selectedAgent"
      @succession-triggered="handleSuccessorCreated"
    />

    <!-- Agent Details Modal (GiljoAI face - shows role/template) -->
    <AgentDetailsModal
      v-model="showAgentDetailsModal"
      :agent="selectedAgent"
    />

    <!-- Agent Job Modal (Info button - shows assigned job/mission) - Handover 0358 -->
    <v-dialog v-model="showAgentJobModal" max-width="700" persistent>
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon start>mdi-briefcase-outline</v-icon>
          <span>Assigned Job: {{ selectedAgent?.agent_name || selectedAgent?.agent_type }}</span>
          <v-spacer></v-spacer>
          <v-btn icon variant="text" @click="showAgentJobModal = false" aria-label="Close">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>
        <v-divider></v-divider>
        <v-card-text>
          <div v-if="selectedAgent" class="agent-job-content">
            <!-- Agent Info -->
            <div class="d-flex align-center gap-2 mb-4">
              <v-chip size="small" :color="getAgentColor(selectedAgent.agent_type)" label>
                {{ selectedAgent.agent_type }}
              </v-chip>
              <span class="text-caption text-medium-emphasis">ID: {{ selectedAgent.job_id }}</span>
            </div>

            <!-- Mission Content -->
            <div class="mission-section">
              <h4 class="text-subtitle-1 font-weight-bold mb-2">Mission</h4>
              <v-card variant="outlined" class="pa-3">
                <pre class="mission-text">{{ selectedAgent.mission || 'No mission assigned yet.' }}</pre>
              </v-card>
            </div>
          </div>
          <div v-else class="text-center py-4 text-medium-emphasis">
            No agent selected
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn color="primary" @click="showAgentJobModal = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Message Audit Modal (Chat bubble - Handover 0358) -->
    <MessageAuditModal
      :show="showMessageAuditModal"
      :agent="selectedAgent"
      :initial-tab="messageAuditInitialTab"
      :steps="selectedAgent && selectedAgent.steps"
      @close="showMessageAuditModal = false"
    />

    <!-- Local Snackbar for immediate feedback -->
    <v-snackbar
      v-model="localSnackbar.show"
      :color="localSnackbar.color"
      :timeout="localSnackbar.timeout"
      location="top center"
    >
      <v-icon v-if="localSnackbar.icon" class="mr-2">{{ localSnackbar.icon }}</v-icon>
      {{ localSnackbar.message }}
    </v-snackbar>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useTheme } from 'vuetify'
import { api } from '@/services/api'
import { useToast } from '@/composables/useToast'
import { useWebSocketV2 } from '@/composables/useWebSocket'
import { useUserStore } from '@/stores/user'
import { getStatusLabel, getStatusColor, isStatusItalic } from '@/utils/statusConfig'
import { shouldShowLaunchAction } from '@/utils/actionConfig'
import LaunchSuccessorDialog from '@/components/projects/LaunchSuccessorDialog.vue'
import AgentDetailsModal from '@/components/projects/AgentDetailsModal.vue'
import MessageAuditModal from '@/components/projects/MessageAuditModal.vue'

/**
 * JobsTab Component - Handover 0241 + 0243c
 *
 * Complete rewrite to match screenshot design exactly.
 * Pure table layout with inline actions and message composer.
 * Dynamic status display from agent.status field with WebSocket updates (0243c).
 *
 * Reference: F:\GiljoAI_MCP\handovers\Launch-Jobs_panels2\IMplement tab.jpg
 * Handover 0243c: JobsTab Dynamic Status Fix (CRITICAL 0242b)
 */

const props = defineProps({
  /**
   * Project object
   * Fields: project_id, name, description
   */
  project: {
    type: Object,
    required: true,
    validator: (value) => {
      return (
        value &&
        typeof value === 'object' &&
        ('project_id' in value || 'id' in value) &&
        'name' in value
      )
    },
  },

  /**
   * Array of agent job objects
   */
  agents: {
    type: Array,
    required: true,
    default: () => [],
  },

  /**
   * Array of message objects
   */
  messages: {
    type: Array,
    default: () => [],
  },

  /**
   * Whether all agents have completed
   */
  allAgentsComplete: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits([
  'launch-agent',
  'view-details',
  'view-error',
  'closeout-project',
  'send-message',
])

/**
 * Composables
 */
const { showToast } = useToast()
const { on, off } = useWebSocketV2()
const userStore = useUserStore()
const theme = useTheme()

/**
 * GiljoAI face icon - theme-aware (Handover 0358)
 */
const giljoFaceIcon = computed(() => {
  const isDark = theme.global.current.value.dark
  return isDark ? '/giljo_YW_Face.svg' : '/Giljo_BY_Face.svg'
})

/**
 * State
 * Handover 0260: Initialize from project.execution_mode for persistence
 */

const messageText = ref('')
const selectedRecipient = ref('orchestrator')
const sending = ref(false)

/**
 * Dialog modal state (Handover 0243d, 0331)
 */
const showCancelDialog = ref(false)
const showHandoverDialog = ref(false)
const showAgentDetailsModal = ref(false)
const showAgentJobModal = ref(false)
const showMessageAuditModal = ref(false)
const messageAuditInitialTab = ref('waiting')
const selectedAgent = ref(null)

/**
 * Local snackbar state for immediate feedback (fixes first-click race condition)
 * Pattern from ClaudeCodeExport.vue - local v-snackbar works on first click
 */
const localSnackbar = ref({
  show: false,
  message: '',
  color: 'success',
  icon: 'mdi-check-circle',
  timeout: 3000
})

/**
 * Show local toast for immediate feedback
 * Bypasses global toast system's race condition on first click
 */
function showLocalToast(options) {
  const typeConfig = {
    success: { color: 'success', icon: 'mdi-check-circle' },
    error: { color: 'error', icon: 'mdi-alert-circle' },
    warning: { color: 'warning', icon: 'mdi-alert' },
    info: { color: 'info', icon: 'mdi-information' }
  }

  const config = typeConfig[options.type] || typeConfig.success

  localSnackbar.value = {
    show: true,
    message: options.message || '',
    color: options.color || config.color,
    icon: options.icon || config.icon,
    timeout: options.duration || options.timeout || 3000
  }
}

/**
 * Get current tenant key for multi-tenant isolation
 */
const currentTenantKey = computed(() => userStore.currentUser?.tenant_key)

/**
 * Agent sorting priority map
 */
const AGENT_PRIORITY = {
  failed: 1,
  blocked: 2,
  waiting: 3,
  working: 4,
  complete: 5,
}

/**
 * Sort agents by priority
 */
const sortedAgents = computed(() => {
  if (!props.agents || props.agents.length === 0) return []

  return [...props.agents].sort((a, b) => {
    const priorityA = AGENT_PRIORITY[a.status] || 999
    const priorityB = AGENT_PRIORITY[b.status] || 999

    // Primary sort: by priority
    if (priorityA !== priorityB) {
      return priorityA - priorityB
    }

    // Secondary sort: by agent type (orchestrator first)
    const isOrchestratorA = a.agent_type === 'orchestrator' ? 0 : 1
    const isOrchestratorB = b.agent_type === 'orchestrator' ? 0 : 1

    if (isOrchestratorA !== isOrchestratorB) {
      return isOrchestratorA - isOrchestratorB
    }

    // Tertiary sort: by agent_type alphabetically
    return (a.agent_type || '').localeCompare(b.agent_type || '')
  })
})

/**
 * Get agent avatar color - matches BRANDING_GUIDE.md
 */
function getAgentColor(agentType) {
  const colors = {
    orchestrator: '#D4A574', // Tan/Beige - Project coordination
    analyzer: '#E74C3C', // Red - Analysis & research
    implementer: '#3498DB', // Blue - Code implementation
    implementor: '#3498DB', // Blue - Code implementation (alias)
    tester: '#FFC300', // Yellow - Testing & QA
    reviewer: '#9B59B6', // Purple - Code review
    documenter: '#27AE60', // Green - Documentation
    researcher: '#27AE60', // Green - Research (alias)
  }
  return colors[agentType?.toLowerCase()] || '#90A4AE' // Gray for custom agents
}

/**
 * Get agent avatar abbreviation - updated to match branding
 */
function getAgentAbbr(agentType) {
  const abbrs = {
    orchestrator: 'OR',
    analyzer: 'AN',
    implementer: 'IM',
    implementor: 'IM', // alias
    tester: 'TE',
    reviewer: 'RV',
    documenter: 'DO',
    researcher: 'RE',
  }
  return abbrs[agentType?.toLowerCase()] || agentType?.slice(0, 2).toUpperCase()
}

/**
 * Format count - show number or empty string for 0/null
 */
function formatCount(count) {
  return count && count > 0 ? count.toString() : ''
}

/**
 * Format acknowledgment timestamp for tooltip
 * Returns null for invalid/empty timestamps
 */
function formatAcknowledgmentTime(timestamp) {
  if (!timestamp || timestamp === '') {
    return null
  }

  try {
    const date = new Date(timestamp)
    if (isNaN(date.getTime())) {
      return null
    }
    // User-friendly format: "Dec 6, 2025, 10:30 AM"
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    })
  } catch (error) {
    console.warn('[JobsTab] Invalid timestamp:', timestamp, error)
    return null
  }
}

/**
 * Format acknowledgment tooltip with "Acknowledged at" prefix
 */
function formatAcknowledgmentTooltip(timestamp) {
  const formatted = formatAcknowledgmentTime(timestamp)
  return formatted ? `Acknowledged at ${formatted}` : 'Not yet acknowledged'
}

/**
 * Get count of messages sent from developer to this agent
 */
function getMessagesSent(agent) {
  if (!agent.messages || !Array.isArray(agent.messages)) return 0
  return agent.messages.filter(
    (m) => m.from === 'developer' || m.direction === 'outbound'
  ).length
}

/**
 * Get count of messages waiting to be read by agent
 */
function getMessagesWaiting(agent) {
  if (!agent.messages || !Array.isArray(agent.messages)) return 0
  return agent.messages.filter(
    (m) => m.status === 'pending' || m.status === 'waiting'
  ).length
}

/**
 * Get count of messages acknowledged/read by agent
 * Only counts INBOUND messages that were read (not outbound messages sent by agent)
 */
function getMessagesRead(agent) {
  if (!agent.messages || !Array.isArray(agent.messages)) return 0
  return agent.messages.filter(
    (m) => m.direction === 'inbound' && (m.status === 'acknowledged' || m.status === 'read')
  ).length
}

/**
 * Toggle execution mode (Claude Code CLI vs Manual)
 * Handover 0260: Persist execution_mode to backend via API
 */

/**
 * Determine if copy button should be shown for an agent (Handover 0333 Phase 3)
 * Reads execution_mode from project prop (read-only, controlled by LaunchTab)
 * 
 * Multi-Terminal Mode: All waiting agents show copy button
 * CLI Mode: Only waiting orchestrator shows copy button
 */
function shouldShowCopyButton(agent) {
  // Get execution mode from project prop (read-only)
  const executionMode = props.project?.execution_mode
  const claudeCodeCliMode = executionMode === 'claude_code_cli'
  
  // Use consolidated function from actionConfig.js
  return shouldShowLaunchAction(agent, claudeCodeCliMode)
}

/**
 * Handle Play button click
 */
async function handlePlay(agent) {
  try {
    // Handover 0337: CLI mode implementation prompt for orchestrator
    if (agent.agent_type === 'orchestrator') {
      // CLI mode: Generate implementation prompt
      if (props.project?.execution_mode === 'claude_code_cli') {
        try {
          const response = await api.prompts.implementation(props.project.project_id || props.project.id)
          const prompt = response.data.prompt
          await copyToClipboard(prompt)
          showLocalToast({
            message: `Implementation prompt copied! (${response.data.agent_count} agents ready)`,
            type: 'success',
            duration: 5000
          })
        } catch (error) {
          const errorMsg = error.response?.data?.detail || 'Failed to generate implementation prompt'
          showLocalToast({
            message: errorMsg,
            type: 'error',
            duration: 6000
          })
        }
        return
      }

      // Multi-terminal mode: Redirect to Launch tab
      showLocalToast({
        message: "Use 'Copy Orchestrator Prompt' button in Launch tab for universal prompt",
        type: 'info',
        duration: 3000
      })
      return
    }

    // Specialist agent universal prompt
    let promptText = ''
    const response = await api.prompts.agentPrompt(agent.job_id || agent.agent_id)
    promptText = response.data?.prompt || ''

    if (!promptText) {
      throw new Error('No prompt text returned')
    }

    await copyToClipboard(promptText)
    showLocalToast({ message: 'Launch prompt copied to clipboard', type: 'success', duration: 3000 })

    emit('launch-agent', agent)
  } catch (error) {
    console.error('[JobsTab] Failed to prepare launch prompt:', error)
    const msg = error.response?.data?.detail || error.message || 'Failed to prepare launch prompt'
    showLocalToast({ message: msg, type: 'error', duration: 5000 })
  }
}

/**
 * Handle Messages button click (Handover 0358)
 * Opens Message Audit Modal for selected agent (Waiting tab)
 */
function handleMessages(agent) {
  console.log('[JobsTab] Messages action:', agent.agent_type)
  selectedAgent.value = agent
  messageAuditInitialTab.value = 'waiting'
  showMessageAuditModal.value = true
}

/**
 * Handle Steps click
 * Handover 0331: Opens Message Audit Modal focused on Plan / TODOs
 */
function handleStepsClick(agent) {
  if (
    !agent.steps ||
    typeof agent.steps.completed !== 'number' ||
    typeof agent.steps.total !== 'number'
  ) {
    return
  }

  selectedAgent.value = agent
  messageAuditInitialTab.value = 'plan'
  showMessageAuditModal.value = true
}

/**
 * Handle Agent Role button click (GiljoAI face icon) - Handover 0358
 * Opens AgentDetailsModal to show template or orchestrator prompt
 */
function handleAgentRole(agent) {
  console.log('[JobsTab] Agent role action:', agent.agent_type)
  selectedAgent.value = agent
  showAgentDetailsModal.value = true
}

/**
 * Handle Agent Job button click (info icon) - Handover 0358
 * Opens modal to show agent's assigned job/mission
 */
function handleAgentJob(agent) {
  console.log('[JobsTab] Agent job action:', agent.agent_type)
  selectedAgent.value = agent
  showAgentJobModal.value = true
}

/**
 * Confirm cancel job (Handover 0243d)
 * Opens confirmation dialog with agent details
 */
function confirmCancelJob(agent) {
  selectedAgent.value = agent
  showCancelDialog.value = true
}

/**
 * Cancel job (Handover 0243d)
 * Calls API to cancel job and shows confirmation toast
 */
async function cancelJob() {
  try {
    const jobId = selectedAgent.value.job_id || selectedAgent.value.agent_id
    const response = await api.post(`/jobs/${jobId}/cancel`, {
      reason: 'User requested cancellation'
    })

    showToast({
      message: 'Agent job cancelled successfully',
      type: 'success',
      duration: 3000
    })

    showCancelDialog.value = false

    // Status will update via WebSocket event (agent:status_changed)
  } catch (error) {
    console.error('[JobsTab] Cancel job failed:', error)
    const msg = error.response?.data?.detail || error.message || 'Failed to cancel agent job'
    showToast({
      message: msg,
      type: 'error',
      duration: 5000
    })
  }
}

/**
 * Open hand over dialog (Handover 0243d)
 * Shows LaunchSuccessorDialog for orchestrator succession
 */
function openHandoverDialog(agent) {
  selectedAgent.value = agent
  showHandoverDialog.value = true
}

/**
 * Handle successor created event (Handover 0243d)
 * Called by LaunchSuccessorDialog when succession is triggered
 */
function handleSuccessorCreated(successorData) {
  console.log('[JobsTab] Successor created:', successorData)
  showToast({
    message: 'Orchestrator handover initiated',
    type: 'success',
    duration: 3000
  })
  showHandoverDialog.value = false
  selectedAgent.value = null
}

/**
 * Send message via API (Handover 0243e)
 * Integrates with backend message service with API call, error handling, and toast notifications
 */
async function sendMessage() {
  if (!messageText.value.trim()) {
    showToast({ message: 'Message cannot be empty', type: 'warning', duration: 3000 })
    return
  }

  sending.value = true

  try {
    // Backend expects MessageSend model:
    // - to_agents: list[str] (plural, array)
    // - content: str
    // - project_id: str (required)
    // - message_type: str (default "direct")
    // - priority: str (default "normal")
    // - from_agent: Optional[str]
    const payload = {
      to_agents: selectedRecipient.value === 'broadcast' ? ['all'] : ['orchestrator'],
      content: messageText.value.trim(),
      project_id: props.project.project_id || props.project.id,
      message_type: selectedRecipient.value === 'broadcast' ? 'broadcast' : 'direct',
      priority: 'normal',
      from_agent: 'user'  // UI user sending message
    }

    console.log('[JobsTab] Sending message payload:', payload)

    // Use unified endpoint (Handover 0299) - single API call, no emit needed
    await api.messages.sendUnified(
      payload.project_id,
      payload.to_agents,
      payload.content,
      payload.message_type,
      payload.priority
    )

    showToast({
      message: 'Message sent successfully',
      type: 'success',
      duration: 3000
    })

    messageText.value = ''
    // Message counts will update via WebSocket event
  } catch (error) {
    console.error('[JobsTab] Send message failed:', error)
    const msg = error.response?.data?.detail || error.message || 'Failed to send message'
    showToast({
      message: `Failed to send message: ${msg}`,
      type: 'error',
      duration: 5000
    })
  } finally {
    sending.value = false
  }
}

/**
 * Copy helper with fallback
 */
async function copyToClipboard(text) {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      return await navigator.clipboard.writeText(text)
    }
  } catch (e) {
    // fall through to fallback
  }
  // Fallback: temporary textarea + execCommand
  const textArea = document.createElement('textarea')
  textArea.value = text
  textArea.style.position = 'fixed'
  textArea.style.left = '-9999px'
  textArea.style.top = '-9999px'
  document.body.appendChild(textArea)
  textArea.focus()
  textArea.select()
  try {
    document.execCommand('copy')
  } finally {
    document.body.removeChild(textArea)
  }
}

/**
 * Handle message sent event (developer -> agent)
 * Updates agent's message list when a message is successfully sent
 */
const handleMessageSent = (data) => {
  // Multi-tenant isolation check
  if (!currentTenantKey.value || data.tenant_key !== currentTenantKey.value) {
    return
  }

  console.log('[JobsTab] Message sent event:', data)

  // "Messages Sent" counter should ALWAYS increment for the SENDER (from_agent)
  // NOT the recipient - this tracks messages the agent has sent OUT
  const senderAgentId = data.from_agent

  const agent = props.agents.find(
    (a) =>
      a.job_id === senderAgentId ||
      a.id === senderAgentId ||
      a.agent_id === senderAgentId ||
      a.agent_type === senderAgentId
  )

  if (agent) {
    if (!agent.messages) agent.messages = []
    agent.messages.push({
      id: data.message_id,
      from: 'agent', // The agent sent this message
      direction: 'outbound', // Outbound from the agent
      status: 'sent',
      text: data.content || data.content_preview || data.message || '',
      priority: data.priority || 'medium',
      timestamp: data.timestamp || new Date().toISOString(),
      to_agent: data.to_agent, // Track recipient for audit trail
      message_type: data.message_type
    })

    console.log(`[JobsTab] Added SENT message to ${agent.agent_type || agent.agent_name} (sender), total messages: ${agent.messages.length}`)
  } else {
    console.warn(`[JobsTab] Could not find agent for message. from_agent: ${data.from_agent}, to_agent: ${data.to_agent}`)
  }
}

/**
 * Handle message acknowledged event (agent read message)
 * Updates message status when agent acknowledges receipt
 */
const handleMessageAcknowledged = (data) => {
  // Multi-tenant isolation check
  if (!currentTenantKey.value || data.tenant_key !== currentTenantKey.value) {
    return
  }

  console.log('[JobsTab] Message acknowledged event:', data)

  // Find the agent who acknowledged the messages
  const agent = props.agents.find(
    (a) => a.id === data.agent_id || a.agent_id === data.agent_id || a.job_id === data.agent_id
  )

  if (agent && agent.messages) {
    // Handle both single message_id and array of message_ids
    const messageIds = data.message_ids || [data.message_id]
    const messageIdSet = new Set(messageIds)

    let updatedCount = 0
    agent.messages.forEach((msg) => {
      if (messageIdSet.has(msg.id) && msg.status !== 'acknowledged') {
        msg.status = 'acknowledged'
        updatedCount++
      }
    })

    if (updatedCount > 0) {
      console.log(`[JobsTab] Updated ${updatedCount} messages to 'acknowledged' for agent ${agent.agent_type || agent.job_id}`)
    }
  }
}

/**
 * Handle new message event (agent -> developer)
 * Adds incoming messages from agents to the message list
 */
/**
 * Handle message received event for RECIPIENT agents
 * Increments "Messages Waiting" counter on recipient agent cards
 * Emitted via broadcast_message_received() in backend
 */
const handleMessageReceived = (data) => {
  // Multi-tenant isolation check
  if (!currentTenantKey.value || data.tenant_key !== currentTenantKey.value) {
    return
  }

  console.log('[JobsTab] Message received event:', data)

  // data.to_agent_ids contains array of recipient job IDs
  const recipientJobIds = data.to_agent_ids || []

  recipientJobIds.forEach((recipientJobId) => {
    // Find the recipient agent by job_id
    const recipientAgent = props.agents.find(
      (a) =>
        a.job_id === recipientJobId ||
        a.id === recipientJobId ||
        a.agent_id === recipientJobId ||
        a.agent_type === recipientJobId
    )

    if (recipientAgent) {
      // Add message to recipient's messages array (for "Messages Waiting" counter)
      if (!recipientAgent.messages) recipientAgent.messages = []
      recipientAgent.messages.push({
        id: data.message_id,
        from: data.from_agent, // Who sent the message
        direction: 'inbound', // Inbound to this recipient
        status: 'waiting', // Waiting to be read
        text: data.content || data.content_preview || data.message || '',
        priority: data.priority || 'medium',
        timestamp: data.timestamp || new Date().toISOString(),
        message_type: data.message_type
      })

      console.log(
        `[JobsTab] Added WAITING message to ${recipientAgent.agent_type || recipientAgent.agent_name} (recipient), total messages: ${recipientAgent.messages.length}`
      )
    } else {
      console.warn(`[JobsTab] Could not find recipient agent. job_id: ${recipientJobId}`)
    }
  })
}

const handleNewMessage = (data) => {
  // Multi-tenant isolation check
  if (!currentTenantKey.value || data.tenant_key !== currentTenantKey.value) {
    return
  }

  console.log('[JobsTab] New message event:', data)

  // Add message to agent's messages array
  const agent = props.agents.find(
    (a) => a.id === data.from_agent || a.agent_id === data.from_agent
  )
  if (agent) {
    if (!agent.messages) agent.messages = []
    agent.messages.push({
      id: data.message_id,
      from: 'agent',
      direction: 'inbound',
      status: 'pending',
      text: data.message,
      priority: data.priority || 'medium',
      timestamp: data.timestamp || new Date().toISOString(),
      message_type: data.message_type
    })
  }
}

/**
 * Handle agent status updates from WebSocket
 * CRITICAL: Multi-tenant isolation - reject events from other tenants
 * Handover 0243c: Real-time status display
 */
const handleStatusUpdate = (data) => {
  // Multi-tenant isolation check
  if (!currentTenantKey.value || data.tenant_key !== currentTenantKey.value) {
    console.warn('[JobsTab] Status update rejected: tenant mismatch', {
      expected: currentTenantKey.value,
      received: data.tenant_key,
    })
    return
  }

  // Find agent and update status
  const agent = props.agents.find((a) => a.job_id === data.job_id || a.agent_id === data.job_id)
  if (agent) {
    agent.status = data.status
  } else {
    console.warn(`[JobsTab] Agent not found for status update: ${data.job_id}`)
  }
}

/**
 * Handle mission acknowledged event from WebSocket (Handover 0297)
 * Updates agent's mission_acknowledged_at field in real-time
 */
const handleMissionAcknowledged = (data) => {
  // Extract payload from nested structure (broadcast_to_tenant nests under data.data)
  const payload = data.data || data

  // Multi-tenant isolation check
  if (!currentTenantKey.value || payload.tenant_key !== currentTenantKey.value) {
    console.warn('[JobsTab] Mission acknowledged rejected: tenant mismatch', {
      expected: currentTenantKey.value,
      received: payload.tenant_key,
    })
    return
  }

  console.log('[JobsTab] Mission acknowledged event:', payload)

  // Find agent and update mission_acknowledged_at
  const agent = props.agents.find((a) => a.job_id === payload.job_id || a.agent_id === payload.job_id)
  if (agent) {
    agent.mission_acknowledged_at = payload.mission_acknowledged_at
    console.log(`[JobsTab] Updated mission_acknowledged_at for ${agent.agent_type}:`, payload.mission_acknowledged_at)

    // Emit custom event for external listeners
    window.dispatchEvent(
      new CustomEvent('agent:mission_acknowledged', {
        detail: {
          jobId: payload.job_id,
          timestamp: payload.mission_acknowledged_at
        }
      })
    )
  } else {
    console.warn(`[JobsTab] Agent not found for mission acknowledged: ${payload.job_id}`)
  }
}

/**
 * Initialize messages array from backend data on mount
 * This ensures counters persist across page refreshes
 */
const initializeMessagesFromBackend = () => {
  if (!props.agents || props.agents.length === 0) {
    console.warn('[JobsTab] No agents to initialize!')
    return
  }

  console.log('[JobsTab] Initializing messages from backend for', props.agents.length, 'agents')

  // Each agent in props.agents should already have messages array from backend
  // The messages come from the JSONB column in PostgreSQL
  props.agents.forEach(agent => {
    const messageCount = agent.messages ? agent.messages.length : 0
    console.log(
      `[JobsTab] Agent ${agent.agent_type} (${agent.job_id})`,
      `- Has ${messageCount} messages from backend`,
      `- Messages array exists: ${!!agent.messages}`,
      messageCount > 0 ? `- Sample message:` : '',
      messageCount > 0 ? agent.messages[0] : ''
    )

    // Ensure messages array is initialized (even if empty)
    if (!agent.messages) {
      agent.messages = []
      console.warn(`[JobsTab] Agent ${agent.agent_type} had NO messages array - initialized empty array`)
    }
  })

  // Log counter values that should be displayed
  console.log('[JobsTab] Counter values after initialization:')
  props.agents.forEach(agent => {
    console.log(
      `  ${agent.agent_type}:`,
      `Sent=${getMessagesSent(agent)},`,
      `Waiting=${getMessagesWaiting(agent)},`,
      `Read=${getMessagesRead(agent)}`
    )
  })
}

/**
 * Lifecycle hooks - WebSocket event management
 */
onMounted(() => {
  // Initialize messages from backend data (for persistence)
  initializeMessagesFromBackend()

  // Register WebSocket event handlers
  // NOTE: message:sent and message:received are handled by websocketIntegrations.js
  // which updates projectTabsStore.agents (same data as props.agents). Registering
  // them here would cause double-counting of messages. (Handover 0297 fix)
  on('agent:status_changed', handleStatusUpdate)
  on('job:mission_acknowledged', handleMissionAcknowledged) // Handover 0297
  on('message:acknowledged', handleMessageAcknowledged)
  on('message:new', handleNewMessage)
})

onUnmounted(() => {
  off('agent:status_changed', handleStatusUpdate)
  off('job:mission_acknowledged', handleMissionAcknowledged) // Handover 0297
  off('message:acknowledged', handleMessageAcknowledged)
  off('message:new', handleNewMessage)
})
</script>

<style scoped lang="scss">
.implement-tab-wrapper {
  padding: 20px;
  background: #0e1c2d;
  min-height: 100vh;

  .table-container {
    border: 2px solid rgba(255, 255, 255, 0.2);
    border-radius: 16px;
    padding: 24px;
    background: rgba(14, 28, 45, 0.5);
    margin-bottom: 20px;

    .agents-table {
      width: 100%;
      border-collapse: collapse;

      thead th {
        text-align: left;
        padding: 12px 16px;
        color: #999;
        font-size: 13px;
        font-weight: 400;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
      }

      tbody tr {
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);

        &:last-child {
          border-bottom: none;
        }
      }

      tbody td {
        padding: 16px;
        color: #e0e0e0;
        font-size: 14px;

        &.agent-type-cell {
          display: flex;
          align-items: center;
          gap: 12px;

          .agent-avatar {
            flex-shrink: 0;

            .avatar-text {
              color: #000;
              font-weight: bold;
              font-size: 12px;
            }
          }

          .agent-info {
            display: flex;
            flex-direction: column;

            .agent-name-primary {
              font-weight: 500;
              text-transform: capitalize;
            }

            .agent-type-secondary {
              font-size: 0.75rem;
              color: #999;
              text-transform: capitalize;
            }
          }
        }

        &.instance-cell {
          text-align: center;
        }

        &.agent-id-cell {
          color: #999;
          font-family: 'Courier New', monospace;
          font-size: 11px;

          .id-container {
            display: flex;
            flex-direction: column;
            gap: 2px;
          }

          .id-row {
            display: flex;
            align-items: center;
            gap: 4px;
          }

          .id-label {
            color: #666;
            font-size: 10px;
            min-width: 35px;
          }

          .id-value {
            background: rgba(255, 255, 255, 0.1);
            padding: 1px 4px;
            border-radius: 2px;
          }
        }

        &.status-cell {
          color: #ffd700;
          font-style: italic;
        }

        &.checkbox-cell {
          text-align: center;
        }

        &.count-cell {
          text-align: center;
          color: #ccc;
        }

        &.actions-cell {
          text-align: right;

          .v-btn {
            min-width: auto;
            padding: 4px;
            margin-left: 4px;
          }
        }
      }
    }
  }

  .message-composer {
    display: flex;
    gap: 12px;
    align-items: center;
    padding: 16px;
    background: rgba(20, 35, 50, 0.6);
    border-radius: 12px;
    margin-bottom: 20px;

    .recipient-btn,
    .broadcast-btn {
      border: 2px solid rgba(255, 215, 0, 0.4);
      border-radius: 6px;
      text-transform: none;
      font-size: 14px;
      font-weight: 400;
      padding: 8px 16px;
      color: rgba(255, 215, 0, 0.7);
      transition: all 0.2s ease;

      &.v-btn--variant-flat {
        background: #ffd700;
        color: #000;
        font-weight: 600;
        border-color: #ffd700;

        &:hover {
          background: #ffed4e;
        }
      }

      &.v-btn--variant-outlined {
        &:hover {
          background: rgba(255, 215, 0, 0.1);
          border-color: rgba(255, 215, 0, 0.6);
          color: rgba(255, 215, 0, 0.9);
        }
      }
    }

    .message-input {
      flex: 1;

      ::v-deep(.v-field) {
        background: rgba(20, 35, 50, 0.8);
        border: 2px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 8px;

        input {
          color: #fff;
          font-size: 14px;
          padding: 8px 12px;

          &::placeholder {
            color: rgba(255, 255, 255, 0.4);
          }
        }

        &:hover {
          border-color: rgba(255, 255, 255, 0.3) !important;
        }

        &.v-field--focused {
          border-color: #ffd700 !important;
        }
      }
    }

    .send-btn {
      min-width: auto;
      width: 40px;
      height: 40px;
      border-radius: 50%;

      &:disabled {
        opacity: 0.4;
      }
    }
  }

  .message-count {
    display: inline-block;
    min-width: 24px;
    padding: 4px 8px;
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.1);
    color: #e0e0e0;
    font-size: 12px;
    font-weight: 600;

    &.message-waiting {
      background: rgba(255, 152, 0, 0.2);
      color: #ff9800;
    }

    &.message-read {
      background: rgba(76, 175, 80, 0.2);
      color: #4caf50;
    }
  }

  /* GiljoAI Face Icon - Handover 0358 */
  .giljo-face-icon {
    width: 20px;
    height: 20px;
    object-fit: contain;
  }

  /* Agent Job Modal - Handover 0358 */
  .mission-text {
    white-space: pre-wrap;
    word-wrap: break-word;
    font-family: 'Roboto Mono', monospace;
    font-size: 13px;
    line-height: 1.5;
    color: rgba(255, 255, 255, 0.9);
    margin: 0;
    max-height: 400px;
    overflow-y: auto;
  }
}
</style>
