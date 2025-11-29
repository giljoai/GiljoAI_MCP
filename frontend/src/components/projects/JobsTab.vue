<template>
  <div class="implement-tab-wrapper">
    <!-- Claude Code CLI Toggle -->
    <div class="claude-toggle-bar" @click="toggleExecutionMode">
      <span class="toggle-label">Enable Claude Code CLI</span>
      <v-tooltip location="bottom">
        <template v-slot:activator="{ props: tooltipProps }">
          <v-icon v-bind="tooltipProps" size="small" class="ml-1 help-icon">mdi-help-circle-outline</v-icon>
        </template>
        <span>When enabled, the orchestrator uses Claude Code CLI's Task tool to spawn subagents in a single terminal. When disabled, you'll need to manually launch each agent in separate terminals.</span>
      </v-tooltip>
      <div class="toggle-indicator" :class="{ active: usingClaudeCodeSubagents }"></div>
    </div>

    <!-- Agent Table Container -->
    <div class="table-container">
      <table class="agents-table" data-testid="agent-status-table">
        <thead>
          <tr>
            <th>Agent Type</th>
            <th>Agent ID</th>
            <th>Agent Status</th>
            <th>Job Read</th>
            <th>Job Acknowledged</th>
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
              <span class="agent-name">{{ agent.agent_type?.toUpperCase() || '' }}</span>
            </td>

            <!-- Agent ID: FULL UUID -->
            <td class="agent-id-cell">{{ agent.job_id || agent.agent_id }}</td>

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

            <!-- Job Read -->
            <td class="checkbox-cell">
              <v-icon v-if="agent.mission_read_at" size="small" color="white" icon="mdi-check" />
            </td>

            <!-- Job Acknowledged -->
            <td class="checkbox-cell">
              <v-icon
                v-if="agent.mission_acknowledged_at"
                size="small"
                color="white"
                icon="mdi-check"
              />
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

              <!-- Folder button: always show (Handover 0243d) -->
              <v-tooltip text="Open workspace">
                <template #activator="{ props: tooltipProps }">
                  <v-btn
                    v-bind="tooltipProps"
                    icon="mdi-folder"
                    size="small"
                    variant="text"
                    color="yellow-darken-2"
                    @click="handleFolder(agent)"
                  />
                </template>
              </v-tooltip>

              <!-- Info button: always show (Handover 0243d) -->
              <v-tooltip text="View details">
                <template #activator="{ props: tooltipProps }">
                  <v-btn
                    v-bind="tooltipProps"
                    icon="mdi-information"
                    size="small"
                    variant="text"
                    color="white"
                    @click="handleInfo(agent)"
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

    <!-- Close Out Project Button (Handover 0249c) -->
    <div v-if="showCloseoutButton" class="closeout-button-container">
      <v-btn
        class="closeout-btn"
        color="yellow-darken-2"
        variant="flat"
        size="large"
        prepend-icon="mdi-check-circle"
        data-testid="close-project-btn"
        @click="openCloseoutModal"
      >
        Close Out Project
      </v-btn>
      <v-tooltip location="top">
        <template #activator="{ props: tooltipProps }">
          <v-icon
            v-bind="tooltipProps"
            size="small"
            class="ml-2 help-icon"
          >
            mdi-help-circle-outline
          </v-icon>
        </template>
        <span>Complete the project and update 360 Memory with learnings</span>
      </v-tooltip>
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

    <!-- Agent Details Modal (Info button) -->
    <AgentDetailsModal
      v-model="showAgentDetailsModal"
      :agent="selectedAgent"
    />

    <!-- Project Closeout Modal (Handover 0249c) -->
    <CloseoutModal
      :show="showCloseoutModal"
      :project-id="project.project_id || project.id"
      :project-name="project.name"
      @close="showCloseoutModal = false"
      @complete="handleCloseoutProject"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { api } from '@/services/api'
import { useToast } from '@/composables/useToast'
import { useWebSocketV2 } from '@/composables/useWebSocket'
import { useUserStore } from '@/stores/user'
import { getStatusLabel, getStatusColor, isStatusItalic } from '@/utils/statusConfig'
import LaunchSuccessorDialog from '@/components/projects/LaunchSuccessorDialog.vue'
import AgentDetailsModal from '@/components/projects/AgentDetailsModal.vue'
import CloseoutModal from '@/components/orchestration/CloseoutModal.vue'

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

/**
 * State
 */
const usingClaudeCodeSubagents = ref(false)
const messageText = ref('')
const selectedRecipient = ref('orchestrator')
const sending = ref(false)

/**
 * Closeout modal state (Handover 0249c)
 */
const showCloseoutModal = ref(false)

/**
 * Cancel dialog state (Handover 0243d)
 */
const showCancelDialog = ref(false)
const showHandoverDialog = ref(false)
const showAgentDetailsModal = ref(false)
const selectedAgent = ref(null)

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
 * Show closeout button when orchestrator has completed (Handover 0249c)
 */
const showCloseoutButton = computed(() => {
  if (!props.allAgentsComplete) return false

  const orchestrator = props.agents?.find((a) => a.agent_type === 'orchestrator')
  return Boolean(orchestrator && orchestrator.status === 'complete')
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
    (m) => m.status === 'pending' || m.status === 'sent'
  ).length
}

/**
 * Get count of messages acknowledged/read by agent
 */
function getMessagesRead(agent) {
  if (!agent.messages || !Array.isArray(agent.messages)) return 0
  return agent.messages.filter(
    (m) => m.status === 'acknowledged' || m.status === 'read'
  ).length
}

/**
 * Toggle execution mode (Claude Code CLI vs Manual)
 */
function toggleExecutionMode() {
  usingClaudeCodeSubagents.value = !usingClaudeCodeSubagents.value
  showToast({
    message: usingClaudeCodeSubagents.value
      ? 'Claude Code CLI mode enabled'
      : 'Manual mode enabled',
    type: 'info',
    duration: 3000
  })
}

/**
 * Determine if copy button should be shown for an agent
 *
 * Toggle OFF (Manual Mode):
 *   - Show copy button for any waiting agent (all agents can be launched manually)
 *
 * Toggle ON (Claude Code CLI Mode):
 *   - Show copy button ONLY for waiting orchestrator (it spawns specialists via Task tool)
 *   - Hide copy buttons for specialist agents (orchestrator spawns them)
 */
function shouldShowCopyButton(agent) {
  // Copy button only shows when agent is waiting
  if (agent.status !== 'waiting') {
    return false
  }

  // If Claude Code CLI mode is OFF, show copy button for all waiting agents
  if (!usingClaudeCodeSubagents.value) {
    return true
  }

  // If Claude Code CLI mode is ON, only show for orchestrator
  return agent.agent_type === 'orchestrator'
}

/**
 * Handle Play button click
 * Handover 0260: Set execution mode before copying prompt
 */
async function handlePlay(agent) {
  try {
    // Handover 0253: Orchestrator uses UNIVERSAL prompt from LaunchTab
    if (agent.agent_type === 'orchestrator') {
      // Handover 0260: Set execution mode for orchestrator before redirecting
      try {
        const mode = usingClaudeCodeSubagents.value ? 'claude_code' : 'multi_terminal'
        await api.agentJobs.setExecutionMode(agent.job_id || agent.agent_id, mode)
        console.log(`[JobsTab] Set execution mode to ${mode} for orchestrator`)
      } catch (modeError) {
        console.error('[JobsTab] Failed to set execution mode:', modeError)
        // Non-fatal: continue to Launch tab
      }

      showToast({
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
    showToast({ message: 'Launch prompt copied to clipboard', type: 'success', duration: 3000 })

    emit('launch-agent', agent)
  } catch (error) {
    console.error('[JobsTab] Failed to prepare launch prompt:', error)
    const msg = error.response?.data?.detail || error.message || 'Failed to prepare launch prompt'
    showToast({ message: msg, type: 'error', duration: 5000 })
  }
}

/**
 * Handle Folder button click
 */
function handleFolder(agent) {
  console.log('[JobsTab] Folder action:', agent.agent_type)
  // TODO: Implement folder action
}

/**
 * Handle Info button click
 * Opens AgentDetailsModal to show template or orchestrator prompt
 */
function handleInfo(agent) {
  console.log('[JobsTab] Info action:', agent.agent_type)
  selectedAgent.value = agent
  showAgentDetailsModal.value = true
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
    const payload = {
      to_agent: selectedRecipient.value === 'broadcast' ? 'all' : 'orchestrator',
      message: messageText.value.trim(),
      priority: 'medium'
    }

    await api.messages.send(payload)

    showToast({
      message: 'Message sent successfully',
      type: 'success',
      duration: 3000
    })

    messageText.value = ''

    // Message counts will update via WebSocket event
    emit('send-message', messageText.value, selectedRecipient.value)
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
 * Open closeout modal (Handover 0249c)
 */
function openCloseoutModal() {
  showCloseoutModal.value = true
  console.log('[JobsTab] Opening closeout modal for project:', props.project.project_id || props.project.id)
}

/**
 * Handle project closeout completion (Handover 0249c)
 */
function handleCloseoutProject(closeoutData) {
  const normalized =
    typeof closeoutData === 'string'
      ? { project_id: closeoutData, sequence_number: 0 }
      : closeoutData || {}

  showToast({
    message: `Project closed out successfully (Memory entry #${normalized.sequence_number ?? 0})`,
    type: 'success',
    duration: 5000
  })

  showCloseoutModal.value = false
  emit('closeout-project', normalized)
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

  // Add message to agent's messages array
  const agent = props.agents.find(
    (a) => a.id === data.to_agent || a.agent_id === data.to_agent
  )
  if (agent) {
    if (!agent.messages) agent.messages = []
    agent.messages.push({
      id: data.message_id,
      from: 'developer',
      direction: 'outbound',
      status: 'sent',
      text: data.message,
      priority: data.priority || 'medium',
      timestamp: data.timestamp || new Date().toISOString()
    })
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

  // Update message status
  const agent = props.agents.find(
    (a) => a.id === data.agent_id || a.agent_id === data.agent_id
  )
  if (agent && agent.messages) {
    const message = agent.messages.find((m) => m.id === data.message_id)
    if (message) {
      message.status = 'acknowledged'
    }
  }
}

/**
 * Handle new message event (agent -> developer)
 * Adds incoming messages from agents to the message list
 */
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
      timestamp: data.timestamp || new Date().toISOString()
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
 * Lifecycle hooks - WebSocket event management
 */
onMounted(() => {
  on('agent:status_changed', handleStatusUpdate)
  on('message:sent', handleMessageSent)
  on('message:acknowledged', handleMessageAcknowledged)
  on('message:new', handleNewMessage)
})

onUnmounted(() => {
  off('agent:status_changed', handleStatusUpdate)
  off('message:sent', handleMessageSent)
  off('message:acknowledged', handleMessageAcknowledged)
  off('message:new', handleNewMessage)
})
</script>

<style scoped lang="scss">
.implement-tab-wrapper {
  padding: 20px;
  background: #0e1c2d;
  min-height: 100vh;

  .claude-toggle-bar {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 20px;
    padding: 12px 16px;
    background: rgba(20, 35, 50, 0.6);
    border-radius: 8px;
    cursor: pointer;
    transition: background 0.2s ease;

    &:hover {
      background: rgba(20, 35, 50, 0.8);
    }

    .toggle-label {
      color: #ccc;
      font-size: 14px;
      font-weight: 500;
    }

    .help-icon {
      color: rgba(255, 215, 0, 0.6);
      cursor: help;

      &:hover {
        color: rgba(255, 215, 0, 0.9);
      }
    }

    .toggle-indicator {
      width: 16px;
      height: 16px;
      border-radius: 50%;
      background: #666;
      transition: background 0.3s, box-shadow 0.3s;
      margin-left: auto;

      &.active {
        background: #00ff00;
        box-shadow: 0 0 8px rgba(0, 255, 0, 0.5);
      }
    }
  }

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

          .agent-name {
            text-transform: capitalize;
          }
        }

        &.agent-id-cell {
          color: #999;
          font-family: 'Courier New', monospace;
          font-size: 11px;
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

  .closeout-button-container {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px 16px;
    background: rgba(20, 35, 50, 0.6);
    border-radius: 12px;
    margin-top: 20px;
    gap: 8px;

    .closeout-btn {
      text-transform: none;
      font-size: 16px;
      font-weight: 600;
      padding: 12px 32px;
      letter-spacing: 0.5px;

      &:hover {
        background: #ffed4e !important;
      }
    }

    .help-icon {
      color: rgba(255, 215, 0, 0.6);
      cursor: help;

      &:hover {
        color: rgba(255, 215, 0, 0.9);
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
}
</style>
