<template>
  <div class="implement-tab-wrapper">
    <!-- Claude Subagents Toggle -->
    <div class="claude-toggle-bar">
      <span class="toggle-label">Claude Subagents</span>
      <div class="toggle-indicator" :class="{ active: usingClaudeCodeSubagents }"></div>
    </div>

    <!-- Agent Table Container -->
    <div class="table-container">
      <table class="agents-table">
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
          <tr v-for="agent in sortedAgents" :key="agent.job_id || agent.agent_id">
            <!-- Agent Type: Avatar + Name -->
            <td class="agent-type-cell">
              <v-avatar :color="getAgentColor(agent.agent_type)" size="32" class="agent-avatar">
                <span class="avatar-text">{{ getAgentAbbr(agent.agent_type) }}</span>
              </v-avatar>
              <span class="agent-name">{{ agent.agent_type }}</span>
            </td>

            <!-- Agent ID: FULL UUID -->
            <td class="agent-id-cell">{{ agent.job_id || agent.agent_id }}</td>

            <!-- Agent Status: Dynamic binding from agent.status -->
            <td
              class="status-cell"
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
            <td class="count-cell">{{ formatCount(agent.messages_sent) }}</td>

            <!-- Messages Waiting -->
            <td class="count-cell">{{ formatCount(agent.messages_waiting) }}</td>

            <!-- Messages Read -->
            <td class="count-cell">{{ formatCount(agent.messages_read) }}</td>

            <!-- Actions -->
            <td class="actions-cell">
              <!-- Play button: only when waiting (Handover 0243d) -->
              <v-tooltip v-if="agent.status === 'waiting'" text="Copy prompt">
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
      <v-btn class="recipient-btn" variant="outlined" rounded> Orchestrator </v-btn>
      <v-btn class="broadcast-btn" variant="outlined" rounded> Broadcast </v-btn>
      <input
        type="text"
        class="message-input"
        placeholder=""
        v-model="messageText"
        @keyup.enter="sendMessage"
      />
      <v-btn icon="mdi-play" class="send-btn" color="yellow-darken-2" @click="sendMessage" />
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

/**
 * Cancel dialog state (Handover 0243d)
 */
const showCancelDialog = ref(false)
const showHandoverDialog = ref(false)
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
 * Get agent avatar color
 */
function getAgentColor(agentType) {
  const colors = {
    orchestrator: '#d4a574', // Tan
    analyzer: '#e53935', // Red
    implementor: '#1976d2', // Blue
    tester: '#fbc02d', // Yellow
  }
  return colors[agentType?.toLowerCase()] || '#666'
}

/**
 * Get agent avatar abbreviation
 */
function getAgentAbbr(agentType) {
  const abbrs = {
    orchestrator: 'Or',
    analyzer: 'An',
    implementor: 'Im',
    tester: 'Te',
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
 * Handle Play button click
 */
async function handlePlay(agent) {
  try {
    let promptText = ''

    if (agent.agent_type === 'orchestrator') {
      // Orchestrator prompt depends on Claude Code subagent toggle
      const response = await api.prompts.execution(
        agent.job_id || agent.agent_id,
        usingClaudeCodeSubagents.value,
      )
      promptText = response.data?.prompt || ''
    } else {
      // Specialist agent universal prompt
      const response = await api.prompts.agentPrompt(agent.job_id || agent.agent_id)
      promptText = response.data?.prompt || ''
    }

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
 */
function handleInfo(agent) {
  console.log('[JobsTab] Info action:', agent.agent_type)
  emit('view-details', agent)
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
 * Send message
 */
function sendMessage() {
  if (!messageText.value.trim()) return

  console.log('[JobsTab] Send message:', messageText.value)
  emit('send-message', messageText.value, null)

  messageText.value = ''
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
})

onUnmounted(() => {
  off('agent:status_changed', handleStatusUpdate)
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

    .toggle-label {
      color: #ccc;
      font-size: 14px;
    }

    .toggle-indicator {
      width: 16px;
      height: 16px;
      border-radius: 50%;
      background: #666;
      transition: background 0.3s;

      &.active {
        background: #00ff00;
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

    .recipient-btn,
    .broadcast-btn {
      border: 2px solid rgba(255, 255, 255, 0.3);
      color: #ccc;
      text-transform: none;
      font-weight: 400;
    }

    .message-input {
      flex: 1;
      background: rgba(20, 35, 50, 0.8);
      border: 2px solid rgba(255, 255, 255, 0.2);
      border-radius: 8px;
      padding: 12px 16px;
      color: #fff;
      font-size: 14px;
      outline: none;

      &::placeholder {
        color: #666;
      }

      &:focus {
        border-color: rgba(255, 255, 255, 0.4);
      }
    }

    .send-btn {
      min-width: auto;
    }
  }
}
</style>
