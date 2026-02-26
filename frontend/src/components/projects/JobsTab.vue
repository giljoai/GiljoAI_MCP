<template>
  <div class="implement-tab-wrapper">
    <!-- Agent Table Container -->
    <div class="table-container">
      <!-- Handover 0411a: Proposed execution order (multi-terminal mode) -->
      <div v-if="executionOrderPhases" class="execution-order-section" data-testid="execution-order">
        <div class="execution-order-title">Proposed Execution Order:</div>
        <div class="execution-order-phases">
          <template v-for="(phase, idx) in executionOrderPhases" :key="idx">
            <span v-if="idx > 0" class="phase-dot">&middot;</span>
            <div class="phase-entry">
              <span class="phase-label">{{ phase.label }}</span>
              <span class="phase-agents">
                <template v-for="(agent, aidx) in phase.agents" :key="aidx">
                  <span v-if="aidx > 0" class="phase-separator">+</span>
                  <span class="agent-pill" :style="{ backgroundColor: agent.color }">{{ agent.displayName }}</span>
                </template>
              </span>
            </div>
          </template>
        </div>
      </div>
      <table class="agents-table" data-testid="agent-status-table">
        <thead>
          <tr>
            <th class="text-center">Agent Name</th>
            <th>Agent ID</th>
            <th>Agent Status</th>
            <th>Duration</th>
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
          <tr v-for="agent in sortedAgents" :key="agent.job_id || agent.agent_id" data-testid="agent-row" :data-agent-display-name="agent.agent_display_name" :data-agent-status="agent.status">
            <!-- Agent Display Name: Play Button + Avatar + Name -->
            <td class="agent-display-name-cell">
              <!-- Fixed-width play button column: always reserves space -->
              <div class="play-btn-slot">
                <v-tooltip v-if="shouldShowCopyButton(agent)" text="Copy prompt">
                  <template #activator="{ props: tooltipProps }">
                    <button
                      v-bind="tooltipProps"
                      type="button"
                      class="play-circle-btn"
                      @click="handlePlay(agent)"
                    >
                      <v-icon size="18">mdi-play</v-icon>
                    </button>
                  </template>
                </v-tooltip>
              </div>
              <button
                type="button"
                class="agent-avatar-button"
                aria-label="View agent details"
                @click="handleAgentRole(agent)"
              >
                <v-avatar :color="getAgentColor(agent?.agent_name || agent?.agent_display_name)" size="32" class="agent-avatar">
                  <span class="avatar-text">{{ getAgentAbbr(getPrimaryAgentLabel(agent)) }}</span>
                </v-avatar>
              </button>
              <div class="agent-info">
                <button
                  type="button"
                  class="agent-name-primary agent-name-button"
                  @click="handleAgentJob(agent)"
                >
                  {{ getPrimaryAgentLabel(agent) }}
                </button>
                <span
                  v-if="agent.agent_name && !isOrchestrator(agent)"
                  class="agent-display-name-secondary"
                >
                  Skills: {{ agent.agent_name }}
                </span>
                <button
                  v-else-if="isOrchestrator(agent)"
                  type="button"
                  class="agent-display-name-secondary agent-name-button"
                  @click="handleAgentJob(agent)"
                >
                  Skills: Fixed system agent
                </button>
              </div>
            </td>

            <!-- Agent ID: Dual display -->
            <td class="agent-id-cell" data-testid="agent-id">
              <div class="id-container">
                <div class="id-row">
                  <span class="id-label">Agent:</span>
                  <v-tooltip
                    :text="agent.agent_id || agent.job_id || '—'"
                    location="top"
                    open-on-hover
                    open-on-click
                  >
                    <template #activator="{ props: tooltipProps }">
                      <button
                        type="button"
                        class="id-value id-value-button"
                        v-bind="tooltipProps"
                        aria-label="Show full agent ID"
                        @click="copyId(agent.agent_id || agent.job_id, 'Agent ID')"
                      >
                        {{ getShortId(agent.agent_id || agent.job_id) }}
                      </button>
                    </template>
                  </v-tooltip>
                </div>
                <div class="id-row">
                  <span class="id-label">Job:</span>
                  <v-tooltip
                    :text="agent.job_id || '—'"
                    location="top"
                    open-on-hover
                    open-on-click
                  >
                    <template #activator="{ props: tooltipProps }">
                      <button
                        type="button"
                        class="id-value id-value-button"
                        v-bind="tooltipProps"
                        aria-label="Show full job ID"
                        @click="copyId(agent.job_id, 'Job ID')"
                      >
                        {{ getShortId(agent.job_id) }}
                      </button>
                    </template>
                  </v-tooltip>
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
              {{ getStatusLabel(agent.status) }}<span v-if="agent.status === 'working'" class="working-dots"><span class="dot">.</span><span class="dot">.</span><span class="dot">.</span></span>
            </td>

            <!-- Duration: Time from working to completed (or elapsed if still working) -->
            <td class="duration-cell" data-testid="duration">
              {{ formatDuration(agent) }}
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
              <button
                type="button"
                class="message-count-button"
                aria-label="View messages sent"
                @click="handleMessages(agent)"
              >
                <span class="message-count">{{ getMessagesSent(agent) }}</span>
              </button>
            </td>

            <!-- Messages Waiting -->
            <td class="messages-waiting-cell text-center">
              <button
                type="button"
                class="message-count-button"
                aria-label="View messages waiting"
                @click="handleMessages(agent)"
              >
                <span class="message-count message-waiting">{{ getMessagesWaiting(agent) }}</span>
              </button>
            </td>

            <!-- Messages Read -->
            <td class="messages-read-cell text-center">
              <button
                type="button"
                class="message-count-button"
                aria-label="View messages read"
                @click="handleMessages(agent)"
              >
                <span class="message-count message-read">{{ getMessagesRead(agent) }}</span>
              </button>
            </td>

            <!-- Actions -->
            <td class="actions-cell">
              <!-- Messages button: opens Message Audit Modal (Handover 0358) -->
              <v-tooltip text="View messages">
                <template #activator="{ props: tooltipProps }">
                  <v-btn
                    v-bind="tooltipProps"
                    icon="mdi-message-outline"
                    size="small"
                    variant="text"
                    :color="actionIconColor"
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
                    :color="actionIconColor"
                    data-testid="jobs-info-btn"
                    @click="handleAgentJob(agent)"
                  />
                </template>
              </v-tooltip>

              <!-- Hand Over button: only for working orchestrators (Handover 0243d) -->
              <v-tooltip
                v-if="agent.agent_display_name === 'orchestrator' && ['working', 'complete', 'completed'].includes(agent.status)"
                text="Hand over"
              >
                <template #activator="{ props: tooltipProps }">
                  <v-btn
                    v-bind="tooltipProps"
                    icon="mdi-refresh"
                    size="small"
                    variant="text"
                    :color="actionIconColor"
                    @click="handleHandOver(agent)"
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
        color="yellow-darken-2"
        @click="selectedRecipient = 'orchestrator'"
      >
        Orchestrator
      </v-btn>

      <v-btn
        class="broadcast-btn"
        :variant="selectedRecipient === 'broadcast' ? 'flat' : 'outlined'"
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

    <!-- REMOVED: Hand Over Dialog (0461d) - Uses simple handover API now -->

    <!-- Agent Details Modal (GiljoAI face - shows role/template) -->
    <AgentDetailsModal
      v-model="showAgentDetailsModal"
      :agent="selectedAgent"
    />

    <!-- Agent Job Modal (Info button - shows assigned job/mission) - Handover 0423 -->
    <AgentJobModal
      :show="showAgentJobModal"
      :agent="selectedAgent"
      :initial-tab="jobModalInitialTab"
      @close="showAgentJobModal = false"
    />

    <!-- Message Audit Modal (Chat bubble - Handover 0358) -->
    <MessageAuditModal
      :show="showMessageAuditModal"
      :agent="selectedAgent"
      :initial-tab="messageAuditInitialTab"
      :steps="selectedAgent && selectedAgent.steps"
      @close="showMessageAuditModal = false"
    />

    <!-- Closeout Modal (Project completion) -->
    <CloseoutModal
      :show="showCloseoutModal"
      :project-id="projectId"
      :project-name="project.name"
      :product-id="project.product_id"
      @continue="handleContinue"
      @closeout="handleCloseout"
      @close="showCloseoutModal = false"
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
import { useWebSocketStore } from '@/stores/websocket'
import { useAgentJobs } from '@/composables/useAgentJobs'
import { getStatusLabel, getStatusColor, isStatusItalic } from '@/utils/statusConfig'
import { shouldShowLaunchAction } from '@/utils/actionConfig'
import AgentDetailsModal from '@/components/projects/AgentDetailsModal.vue'
import AgentJobModal from '@/components/projects/AgentJobModal.vue'
import MessageAuditModal from '@/components/projects/MessageAuditModal.vue'
import CloseoutModal from '@/components/orchestration/CloseoutModal.vue'

/**
 * JobsTab Component - Handover 0241 + 0243c + 0461d
 *
 * Complete rewrite to match screenshot design exactly.
 * Pure table layout with inline actions and message composer.
 * Dynamic status display from agent.status field with WebSocket updates (0243c).
 *
 * Handover 0461d: Simplified - no longer tracking instance_number or succession chains.
 * Removed instance column and succession-related logic.
 *
 * Reference: handovers/Launch-Jobs_panels2/IMplement tab.jpg
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

  readonly: {
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
const wsStore = useWebSocketStore()
const theme = useTheme()
const { sortedJobs: sortedAgents, loadJobs, store: agentJobsStore } = useAgentJobs()

/**
 * Handover 0411a: Proposed execution order phases for multi-terminal mode.
 * Returns structured phase data with labels like "(Start)", "(Phase 1 Parallel Execution)", "(Phase 2)".
 * Hardcoded first entry: (Start) Orchestrator.
 * Phases with '+' (multiple agents) get "Parallel Execution" suffix.
 */
const executionOrderPhases = computed(() => {
  const agentList = sortedAgents.value
  if (!agentList.some(a => a.phase != null)) return null

  // Group by phase (skip orchestrator — hardcoded as Start)
  const groups = {}
  for (const agent of agentList) {
    if (isOrchestrator(agent)) continue
    const phase = agent.phase ?? 999
    if (!groups[phase]) groups[phase] = []
    groups[phase].push({
      displayName: agent.agent_display_name || agent.agent_name || 'unknown',
      color: getAgentColor(agent.agent_name || agent.agent_display_name),
    })
  }

  // Build structured phases with hardcoded Start > Orchestrator first
  const phases = [{
    label: 'Start',
    agents: [{ displayName: 'Orchestrator', color: getAgentColor('orchestrator') }],
  }]

  Object.keys(groups)
    .map(Number)
    .sort((a, b) => a - b)
    .forEach(phase => {
      const isParallel = groups[phase].length > 1
      const phaseNum = phase === 999 ? '?' : phase
      const label = isParallel ? `Phase ${phaseNum} Parallel Execution` : `Phase ${phaseNum}`
      phases.push({ label, agents: groups[phase] })
    })

  return phases
})

/**
 * GiljoAI face icon (dark theme only)
 */
const giljoFaceIcon = computed(() => {
  return '/giljo_YW_Face.svg'
})

/**
 * Action icon color (dark theme only)
 */
const actionIconColor = computed(() => {
  return 'warning'
})

function isOrchestrator(agent) {
  return agent?.agent_name === 'orchestrator' || agent?.agent_display_name === 'orchestrator'
}

function getPrimaryAgentLabel(agent) {
  if (!agent) {
    return ''
  }

  if (isOrchestrator(agent)) {
    return agent.agent_name || agent.agent_display_name || ''
  }

  return agent.agent_display_name || agent.agent_name || ''
}

function getShortId(value) {
  if (!value || value === '—') {
    return '—'
  }

  return value.slice(0, 8)
}

async function copyId(value, label) {
  if (!value || value === '—') {
    showLocalToast({ message: `${label} unavailable`, type: 'warning', duration: 2500 })
    return
  }

  try {
    await navigator.clipboard.writeText(value)
    showLocalToast({ message: `${label} copied`, type: 'success', duration: 2000 })
  } catch (error) {
    console.warn('[JobsTab] Failed to copy ID:', error)
    showLocalToast({ message: `Failed to copy ${label}`, type: 'error', duration: 3000 })
  }
}

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
const showAgentDetailsModal = ref(false)
const showAgentJobModal = ref(false)
const showMessageAuditModal = ref(false)
const showCloseoutModal = ref(false)
const jobModalInitialTab = ref('mission')
const messageAuditInitialTab = ref('sent')
const selectedJobId = ref(null)
const selectedAgent = computed(() => agentJobsStore.getJob(selectedJobId.value))

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

const projectId = computed(() => props.project?.project_id || props.project?.id)
const loadingJobs = ref(false)

/**
 * Duration tracking - live timer for working agents
 * Updates every second to show elapsed time
 */
const now = ref(Date.now())
let durationTimer = null

async function refreshJobs() {
  if (!projectId.value) return
  if (loadingJobs.value) return

  loadingJobs.value = true
  try {
    await loadJobs(projectId.value)
  } catch (error) {
    console.warn('[JobsTab] Failed to load agent jobs:', error)
    showToast({
      message: 'Failed to load agent jobs',
      type: 'error',
      duration: 5000,
    })
  } finally {
    loadingJobs.value = false
  }
}

watch(projectId, () => {
  refreshJobs()
}, { immediate: true })

let unsubscribeConnectionListener = null
onMounted(() => {
  unsubscribeConnectionListener = wsStore.onConnectionChange((connectionEvent) => {
    if (connectionEvent?.state === 'connected' && connectionEvent?.isReconnect) {
      refreshJobs()
    }
  })

  // Start duration timer for live elapsed time display
  durationTimer = setInterval(() => {
    now.value = Date.now()
  }, 1000)
})

onUnmounted(() => {
  unsubscribeConnectionListener?.()

  // Clean up duration timer
  if (durationTimer) {
    clearInterval(durationTimer)
    durationTimer = null
  }
})

/**
 * Get agent avatar color - matches BRANDING_GUIDE.md
 */
function getAgentColor(displayName) {
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
  return colors[displayName?.toLowerCase()] || '#90A4AE' // Gray for custom agents
}

/**
 * Get agent avatar abbreviation - uses word initials
 * Split by dash, space, or underscore and use first letter of each part
 * e.g., "Backend-Implementer" → "BI", "Backend-Tester" → "BT"
 */
function getAgentAbbr(displayName) {
  if (!displayName) return '??'

  // Split by dash, space, or underscore
  const parts = displayName.split(/[-_\s]+/).filter(Boolean)

  if (parts.length >= 2) {
    // Use first letter of first two parts: "Backend-Implementer" → "BI"
    return (parts[0][0] + parts[1][0]).toUpperCase()
  }

  // Single word fallback: use first two letters
  return displayName.substring(0, 2).toUpperCase()
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
 * Format duration between started_at and completed_at (or now for working agents)
 * Shows: "---" if not started, live elapsed time if working, final duration if completed
 */
function formatDuration(agent) {
  if (!agent.started_at) {
    return '---'
  }

  const start = new Date(agent.started_at).getTime()
  // Use completed_at if available, otherwise use current time (for working agents)
  const end = agent.completed_at ? new Date(agent.completed_at).getTime() : now.value
  const durationMs = end - start

  if (durationMs < 0) {
    return '---'
  }

  // Less than a minute: show seconds
  if (durationMs < 60000) {
    return `${Math.round(durationMs / 1000)}s`
  }

  // Less than an hour: show minutes and seconds
  if (durationMs < 3600000) {
    const mins = Math.floor(durationMs / 60000)
    const secs = Math.round((durationMs % 60000) / 1000)
    return `${mins}m ${secs}s`
  }

  // Hours and minutes
  const hours = Math.floor(durationMs / 3600000)
  const mins = Math.floor((durationMs % 3600000) / 60000)
  return `${hours}h ${mins}m`
}

/**
 * Get count of messages sent from developer to this agent
 */
function getMessagesSent(agent) {
  return agent?.messages_sent_count ?? 0
}

/**
 * Get count of messages waiting to be read by agent
 */
function getMessagesWaiting(agent) {
  return agent?.messages_waiting_count ?? 0
}

/**
 * Get count of messages acknowledged/read by agent
 * Only counts INBOUND messages that were read (not outbound messages sent by agent)
 */
function getMessagesRead(agent) {
  return agent?.messages_read_count ?? 0
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
    if (agent.agent_display_name === 'orchestrator') {
      // CLI mode: Generate implementation prompt
      if (props.project?.execution_mode === 'claude_code_cli') {
        try {
          // Handover 0709: Set implementation phase gate before copying prompt
          const projectId = props.project.project_id || props.project.id
          try {
            await api.projects.launchImplementation(projectId)
          } catch (gateError) {
            console.warn('[JobsTab] launch-implementation call failed (non-blocking):', gateError)
          }

          const response = await api.prompts.implementation(projectId)
          const prompt = response.data.prompt
          await copyToClipboard(prompt)
          showLocalToast({
            message: `Implementation prompt copied! ${response.data.agent_count + 1} jobs ready (1 orchestrator, ${response.data.agent_count} agents)`,
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

      // Multi-terminal mode: implementation prompt with phase gate (0497c)
      try {
        const projectId = props.project.project_id || props.project.id
        try {
          await api.projects.launchImplementation(projectId)
        } catch (gateError) {
          console.warn('[JobsTab] launch-implementation call failed (non-blocking):', gateError)
        }

        const response = await api.prompts.implementation(projectId)
        const prompt = response.data.prompt
        await copyToClipboard(prompt)
        showLocalToast({
          message: `Orchestrator prompt copied! ${response.data.agent_count} agents ready for launch.`,
          type: 'success',
          duration: 5000
        })
      } catch (error) {
        const errorMsg = error.response?.data?.detail || 'Failed to generate orchestrator prompt'
        showLocalToast({
          message: errorMsg,
          type: 'error',
          duration: 6000
        })
      }
      return
    }

    // Specialist agent universal prompt
    let promptText = ''
    const response = await api.prompts.agentPrompt(agent.agent_id || agent.job_id)
    promptText = response.data?.prompt || ''

    if (!promptText) {
      throw new Error('No prompt text returned')
    }

    await copyToClipboard(promptText)
    showLocalToast({ message: 'Launch prompt copied to clipboard', type: 'success', duration: 3000 })
  } catch (error) {
    console.error('[JobsTab] Failed to prepare launch prompt:', error)
    const msg = error.response?.data?.detail || error.message || 'Failed to prepare launch prompt'
    showLocalToast({ message: msg, type: 'error', duration: 5000 })
  }
}

/**
 * Handle Messages button click (Handover 0358)
 * Opens Message Audit Modal for selected agent (Sent tab)
 */
function handleMessages(agent) {
  selectedJobId.value = agent.job_id || agent.agent_id
  messageAuditInitialTab.value = 'sent'
  showMessageAuditModal.value = true
}

/**
 * Handle Steps click
 * Handover 0423: Opens Agent Job Modal focused on Plan tab
 */
function handleStepsClick(agent) {
  if (
    !agent.steps ||
    typeof agent.steps.completed !== 'number' ||
    typeof agent.steps.total !== 'number'
  ) {
    return
  }

  selectedJobId.value = agent.job_id || agent.agent_id
  jobModalInitialTab.value = 'plan'
  showAgentJobModal.value = true
}

/**
 * Handle Agent Role button click (GiljoAI face icon) - Handover 0358
 * Opens AgentDetailsModal to show template or orchestrator prompt
 */
function handleAgentRole(agent) {
  selectedJobId.value = agent.job_id || agent.agent_id
  showAgentDetailsModal.value = true
}

/**
 * Handle Agent Job button click (briefcase icon) - Handover 0423
 * Opens modal to show agent's assigned job/mission
 */
function handleAgentJob(agent) {
  selectedJobId.value = agent.job_id || agent.agent_id
  jobModalInitialTab.value = 'mission'
  showAgentJobModal.value = true
}

/**
 * Handle Hand Over button click (Handover 0461d fix)
 * Calls simple-handover API and copies continuation prompt to clipboard
 */
async function handleHandOver(agent) {
  try {
    const jobId = agent.job_id || agent.agent_id

    // Call simple-handover endpoint (Handover 0461d)
    const response = await api.agentJobs.simpleHandover(jobId)

    if (response.data.success) {
      // Copy continuation prompt to clipboard
      await navigator.clipboard.writeText(response.data.continuation_prompt)

      showLocalToast({
        message: 'Session refreshed! Continuation prompt copied to clipboard.',
        type: 'success',
        duration: 5000,
      })
    } else {
      throw new Error(response.data.error || 'Session refresh failed')
    }
  } catch (error) {
    console.error('[JobsTab] Hand over failed:', error)
    const msg = error.response?.data?.detail || error.message || 'Hand over failed'
    showLocalToast({
      message: msg,
      type: 'error',
      duration: 5000,
    })
  }
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
 * Handle Continue Working action from closeout modal
 * Refreshes jobs to show new orchestrator
 */
async function handleContinue() {
  showCloseoutModal.value = false
  await refreshJobs()
  showToast({
    message: 'Project continues with new orchestrator',
    type: 'info',
    duration: 3000
  })
}

/**
 * Handle Close Out action from closeout modal
 * Project is archived, navigate away or show success
 */
async function handleCloseout(data) {
  showCloseoutModal.value = false
  showToast({
    message: 'Project closed out successfully',
    type: 'success',
    duration: 3000
  })
  // Emit event to parent component to handle navigation
  emit('closeout-project', data)
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

// WebSocket updates for jobs/messages flow through the centralized router (0379a)
// into `agentJobsStore` (0379b). JobsTab only renders store state and performs user actions.
</script>

<style scoped lang="scss">
.implement-tab-wrapper {
  padding: 16px;

  .table-container {
    padding: 16px;
    margin-bottom: 16px;

    // Handover 0411a: Proposed execution order display
    .execution-order-section {
      padding: 8px 0 14px;
      border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.1);
      margin-bottom: 4px;
      text-align: center;

      .execution-order-title {
        font-size: 17px;
        font-weight: 700;
        color: #f5c542;
        margin-bottom: 8px;
      }

      .execution-order-phases {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        align-items: center;
        gap: 6px 8px;

        .phase-dot {
          font-size: 20px;
          font-weight: 700;
          color: rgba(255, 255, 255, 0.4);
          line-height: 1;
        }

        .phase-entry {
          display: flex;
          align-items: center;
          gap: 5px;

          .phase-label {
            font-size: 13px;
            font-weight: 700;
            color: #fff;
          }

          .phase-agents {
            display: inline-flex;
            align-items: center;
            gap: 4px;

            .agent-pill {
              display: inline-block;
              padding: 2px 10px;
              border-radius: 12px;
              font-size: 12px;
              font-weight: 600;
              white-space: nowrap;
              color: #182739;
            }

            .phase-separator {
              font-size: 14px;
              font-weight: 700;
              color: #fff;
            }
          }
        }
      }
    }

    .agents-table {
      width: 100%;
      border-collapse: collapse;

      thead th {
        text-align: left;
        padding: 12px 16px;
        color: rgba(var(--v-theme-on-surface), 0.6);
        font-size: 13px;
        font-weight: 400;
        border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.1);
      }

      tbody tr {
        border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.05);

        &:last-child {
          border-bottom: none;
        }
      }

      tbody td {
        padding: 16px;
        color: rgb(var(--v-theme-on-surface));
        font-size: 14px;

        &.agent-display-name-cell {
          display: flex;
          align-items: center;
          gap: 12px;

          .play-btn-slot {
            flex-shrink: 0;
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
          }

          .play-circle-btn {
            flex-shrink: 0;
            width: 32px;
            height: 32px;
            border-radius: 50%;
            border: 2px solid rgba(255, 215, 0, 0.7);
            background: transparent;
            color: rgba(255, 215, 0, 0.9);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 0;
            transition: all 0.2s ease;

            .v-icon {
              color: rgba(255, 215, 0, 0.9);
            }

            &:hover {
              border-color: #ffd700;
              background: rgba(255, 215, 0, 0.1);
              transform: scale(1.1);

              .v-icon {
                color: #ffd700;
              }
            }
          }

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
            flex: 1;
            min-width: 0;

            .agent-name-primary {
              font-weight: 500;
              text-transform: capitalize;
            }

            .agent-avatar-button,
            .agent-name-button {
              background: none;
              border: none;
              padding: 0;
              cursor: pointer;
              text-align: left;
              color: inherit;
            }

            .agent-display-name-secondary {
              font-size: 0.75rem;
              color: rgba(var(--v-theme-on-surface), 0.6);
              text-transform: capitalize;
            }
          }
        }

        &.agent-id-cell {
          color: rgba(var(--v-theme-on-surface), 0.6);
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
            color: rgba(var(--v-theme-on-surface), 0.7);
            font-size: 10px;
            min-width: 35px;
          }

          .id-value {
            background: rgba(var(--v-theme-on-surface), 0.1);
            padding: 1px 4px;
            border-radius: 2px;
            border: none;
            cursor: pointer;
            font-family: inherit;
          }

          .id-value-button {
            line-height: 1.2;
          }
        }

        &.status-cell {
          font-style: italic;

          .working-dots {
            display: inline;

            .dot {
              animation: dot-blink 1.4s infinite steps(1);
              opacity: 0;
            }

            .dot:nth-child(1) { animation-delay: 0s; }
            .dot:nth-child(2) { animation-delay: 0.3s; }
            .dot:nth-child(3) { animation-delay: 0.6s; }
          }
        }

        @keyframes dot-blink {
          0%, 100% { opacity: 0; }
          30%, 70% { opacity: 1; }
        }

        &.duration-cell {
          text-align: center;
          font-family: 'Roboto Mono', 'Courier New', monospace;
          font-size: 13px;
          color: rgba(var(--v-theme-on-surface), 0.7);
        }

        &.checkbox-cell {
          text-align: center;
        }

        &.count-cell {
          text-align: center;
          color: #ccc;
        }

        .message-count-button {
          background: none;
          border: none;
          padding: 0;
          cursor: pointer;
          color: inherit;
        }

        &.actions-cell {
          text-align: right;

          .v-btn {
            min-width: auto;
            padding: 4px;
            margin-left: 4px;
          }

          .v-icon {
            opacity: 1 !important;
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
    background: rgba(var(--v-theme-on-surface), 0.05);
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
        background: rgba(var(--v-theme-on-surface), 0.05);
        border: 2px solid rgba(var(--v-theme-on-surface), 0.2) !important;
        border-radius: 8px;

        input {
          color: rgb(var(--v-theme-on-surface));
          font-size: 14px;
          padding: 8px 12px;

          &::placeholder {
            color: rgba(var(--v-theme-on-surface), 0.4);
          }
        }

        &:hover {
          border-color: rgba(var(--v-theme-on-surface), 0.3) !important;
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
    background: rgba(var(--v-theme-on-surface), 0.1);
    color: rgb(var(--v-theme-on-surface));
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

  /* Close Out Project Button */
  .closeout-btn {
    font-weight: 600;
    letter-spacing: 0.5px;
    text-transform: none;
    font-size: 15px;
    padding: 12px 24px;
    height: auto;

    &:hover {
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3);
    }
  }
}

/* Global avatar styles for modal consistency - Handover 0401b */
.agent-avatar {
  .avatar-text {
    color: #000;
    font-weight: bold;
    font-size: 12px;
  }
}
</style>
