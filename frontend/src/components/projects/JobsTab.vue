<template>
  <div class="implement-tab-wrapper">
    <!-- Agent Table Container -->
    <div class="table-container smooth-border">
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
                  <span
                    class="agent-tinted-badge"
                    :style="{ backgroundColor: agent.tintedBg, color: agent.color }"
                  >{{ agent.displayName }}</span>
                </template>
              </span>
            </div>
          </template>
        </div>
      </div>
      <!-- Handover 0904: Auto check-in controls (multi-terminal only, after staging) -->
      <div
        v-if="showAutoCheckin"
        class="auto-checkin-section"
        data-testid="auto-checkin"
      >
        <div class="auto-checkin-row">
          <span class="auto-checkin-label">Orchestrator Auto Check-in</span>
          <v-switch
            v-model="autoCheckinEnabled"
            density="compact"
            hide-details
            color="rgb(var(--v-theme-primary))"
            class="auto-checkin-toggle"
            data-testid="auto-checkin-toggle"
            @update:model-value="onAutoCheckinToggle"
          />
        </div>
        <div v-if="autoCheckinEnabled" class="auto-checkin-interval" data-testid="auto-checkin-interval">
          <span class="auto-checkin-interval-label">Check-in every:</span>
          <v-btn-toggle
            v-model="autoCheckinInterval"
            mandatory
            density="compact"
            class="auto-checkin-btn-group"
            @update:model-value="onAutoCheckinIntervalChange"
          >
            <v-btn :value="30" size="small" variant="outlined">0:30</v-btn>
            <v-btn :value="60" size="small" variant="outlined">1:00</v-btn>
            <v-btn :value="90" size="small" variant="outlined">1:30</v-btn>
          </v-btn-toggle>
        </div>
      </div>
      <table class="agents-table" data-testid="agent-status-table">
        <thead>
          <tr>
            <th class="col-phase">Phase</th>
            <th class="col-play"></th>
            <th class="col-agent-name">Agent Name</th>
            <th class="col-center">Agent Status</th>
            <th class="col-center hide-mobile">Duration</th>
            <th class="col-center hide-mobile">Steps</th>
            <th class="col-center hide-mobile">Messages Waiting</th>
            <th class="col-actions"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="agent in phaseSortedAgents" :key="agent.job_id || agent.agent_id" data-testid="agent-row" :data-agent-display-name="agent.agent_display_name" :data-agent-status="agent.status">
            <!-- Phase Badge (Handover 0829, 0875: "All" for subagent modes) -->
            <td class="phase-cell" data-testid="phase-badge">
              <span v-if="isSubagentMode" class="phase-badge">All</span>
              <span v-else-if="isOrchestrator(agent)" class="phase-badge">Start</span>
              <span v-else-if="agent.phase == null" class="phase-badge phase-badge--none">&mdash;</span>
              <span v-else class="phase-badge">P{{ agent.phase }}</span>
            </td>
            <!-- Agent Display Name: Play Button + Avatar + Name -->
            <!-- Play button: own column, no header -->
            <td class="play-cell">
              <div class="play-btn-slot">
                <template v-if="shouldShowCopyButton(agent)">
                  <!-- Play button (fades after launch, reactivatable) -->
                  <v-tooltip text="Copy prompt">
                    <template #activator="{ props: tooltipProps }">
                      <button
                        v-bind="tooltipProps"
                        type="button"
                        class="play-circle-btn icon-interactive-play"
                        :class="{ 'play-btn-faded': isPlayButtonFaded(agent) }"
                        :disabled="isPlayButtonFaded(agent)"
                        aria-label="Copy agent prompt"
                        @click="handlePlay(agent)"
                      >
                        <v-icon size="18">mdi-play</v-icon>
                      </button>
                    </template>
                  </v-tooltip>
                </template>
              </div>
            </td>
            <!-- Agent card: tinted badge + name (0870j) -->
            <td class="agent-display-name-cell">
              <div class="agent-card-row">
                <button
                  type="button"
                  class="agent-avatar-button"
                  aria-label="View agent details"
                  @click="handleAgentRole(agent)"
                >
                  <div
                    class="agent-badge"
                    :class="{ 'agent-badge--active': agent.status === 'working' }"
                    :style="getAgentBadgeStyle(agent?.agent_name || agent?.agent_display_name)"
                  >
                    {{ getAgentAbbr(getPrimaryAgentLabel(agent)) }}
                  </div>
                </button>
                <div class="agent-info">
                  <button
                    type="button"
                    class="agent-name-primary agent-name-button"
                    aria-label="View assigned job"
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
            <td class="duration-cell hide-mobile" data-testid="duration">
              {{ formatDuration(agent) }}
            </td>

            <!-- Steps (numeric TODO progress) -->
            <td class="steps-cell text-center hide-mobile">
              <button
                v-if="agent.steps && typeof agent.steps.completed === 'number' && typeof agent.steps.total === 'number'"
                type="button"
                class="steps-trigger"
                aria-label="View execution plan"
                data-testid="steps-trigger"
                @click="handleStepsClick(agent)"
              >
                {{ agent.steps.completed }}<span v-if="agent.steps.skipped" class="steps-skipped">({{ agent.steps.skipped }})</span> / {{ agent.steps.total }}
              </button>
              <span v-else>—</span>
            </td>

            <!-- Messages (waiting count) — tinted badge (0870j) -->
            <td class="messages-waiting-cell text-center hide-mobile">
              <button
                type="button"
                class="message-count-button"
                aria-label="View messages"
                @click="handleMessages(agent)"
              >
                <span class="msg-badge" :class="getMessagesWaiting(agent) > 0 ? 'has-msgs' : 'zero'">{{ getMessagesWaiting(agent) }}</span>
              </button>
            </td>

            <!-- Actions: inline icons on wide screens, three-dot menu on narrow -->
            <td class="actions-cell">
              <!-- Inline icons (hidden on narrow/portrait screens) -->
              <div class="actions-inline">
                <v-tooltip v-if="isPlayButtonFaded(agent)" text="Re-copy prompt">
                  <template #activator="{ props: tooltipProps }">
                    <v-btn
                      v-bind="tooltipProps"
                      icon="mdi-refresh"
                      size="small"
                      variant="text"
                      class="icon-interactive"
                      aria-label="Re-copy prompt"
                      @click="reactivatePlay(agent)"
                    />
                  </template>
                </v-tooltip>

                <v-tooltip text="View messages">
                  <template #activator="{ props: tooltipProps }">
                    <v-btn
                      v-bind="tooltipProps"
                      icon="mdi-message-outline"
                      size="small"
                      variant="text"
                      class="icon-interactive"
                      aria-label="View messages"
                      data-testid="jobs-messages-btn"
                      @click="handleMessages(agent)"
                    />
                  </template>
                </v-tooltip>

                <v-tooltip text="View agent role">
                  <template #activator="{ props: tooltipProps }">
                    <v-btn
                      v-bind="tooltipProps"
                      size="small"
                      variant="text"
                      class="icon-interactive giljo-face-btn"
                      aria-label="View agent role"
                      data-testid="jobs-role-btn"
                      @click="handleAgentRole(agent)"
                    >
                      <img
                        :src="giljoFaceIcon"
                        alt="Agent Role"
                        class="giljo-face-icon giljo-face-default"
                      />
                      <img
                        :src="giljoFaceIconActive"
                        alt="Agent Role"
                        class="giljo-face-icon giljo-face-hover"
                      />
                    </v-btn>
                  </template>
                </v-tooltip>

                <v-tooltip text="View assigned job">
                  <template #activator="{ props: tooltipProps }">
                    <v-btn
                      v-bind="tooltipProps"
                      icon="mdi-briefcase-outline"
                      size="small"
                      variant="text"
                      class="icon-interactive"
                      aria-label="View assigned job"
                      data-testid="jobs-info-btn"
                      @click="handleAgentJob(agent)"
                    />
                  </template>
                </v-tooltip>

                <v-tooltip
                  v-if="agent.agent_display_name === 'orchestrator' && !['decommissioned', 'handed_over', 'waiting'].includes(agent.status)"
                  text="Hand over"
                >
                  <template #activator="{ props: tooltipProps }">
                    <v-btn
                      v-bind="tooltipProps"
                      icon="mdi-logout"
                      size="small"
                      variant="text"
                      class="icon-interactive"
                      aria-label="Hand over session"
                      @click="handleHandOver(agent)"
                    />
                  </template>
                </v-tooltip>

                <v-tooltip
                  v-if="agent.agent_display_name === 'orchestrator' && agent.status === 'working'"
                  text="Stop project"
                >
                  <template #activator="{ props: tooltipProps }">
                    <v-btn
                      v-bind="tooltipProps"
                      icon="mdi-stop-circle-outline"
                      size="small"
                      variant="text"
                      color="error"
                      aria-label="Stop project"
                      data-testid="jobs-stop-btn"
                      @click="handleStopProject(agent)"
                    />
                  </template>
                </v-tooltip>
              </div>

              <!-- Three-dot menu (shown only on narrow/portrait screens) -->
              <div class="actions-menu">
                <v-menu>
                  <template #activator="{ props: menuProps }">
                    <v-btn
                      v-bind="menuProps"
                      icon="mdi-dots-vertical"
                      size="small"
                      variant="text"
                      class="icon-interactive"
                      aria-label="Agent actions"
                    />
                  </template>
                  <v-list density="compact">
                    <v-list-item prepend-icon="mdi-message-outline" title="View messages" @click="handleMessages(agent)" />
                    <v-list-item title="View agent role" @click="handleAgentRole(agent)">
                      <template #prepend>
                        <img :src="giljoFaceIcon" alt="Agent Role" class="giljo-face-icon menu-icon" />
                      </template>
                    </v-list-item>
                    <v-list-item prepend-icon="mdi-briefcase-outline" title="View assigned job" @click="handleAgentJob(agent)" />
                    <v-list-item
                      v-if="agent.agent_display_name === 'orchestrator' && !['decommissioned', 'handed_over', 'waiting'].includes(agent.status)"
                      prepend-icon="mdi-logout"
                      title="Hand over"
                      @click="handleHandOver(agent)"
                    />
                    <v-list-item
                      v-if="agent.agent_display_name === 'orchestrator' && agent.status === 'working'"
                      prepend-icon="mdi-stop-circle-outline"
                      title="Stop project"
                      class="text-error"
                      @click="handleStopProject(agent)"
                    />
                  </v-list>
                </v-menu>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Message Composer (Bottom) -->
    <div class="message-composer smooth-border">
      <div class="composer-channels">
        <v-btn
          class="recipient-btn smooth-border"
          :variant="selectedRecipient === 'orchestrator' ? 'flat' : 'outlined'"
          color="yellow-darken-2"
          @click="selectedRecipient = 'orchestrator'"
        >
          Orchestrator
        </v-btn>

        <v-btn
          class="broadcast-btn smooth-border"
          :variant="selectedRecipient === 'broadcast' ? 'flat' : 'outlined'"
          color="yellow-darken-2"
          @click="selectedRecipient = 'broadcast'"
        >
          Broadcast
        </v-btn>
      </div>

      <div class="composer-input">
        <v-text-field
          v-model="messageText"
          class="message-input"
          placeholder="Type message..."
          variant="outlined"
          density="compact"
          hide-details
          aria-label="Message to agent"
          @keyup.enter="sendMessage"
        />

        <v-btn
          icon="mdi-play"
          class="send-btn"
          color="yellow-darken-2"
          :loading="sending"
          :disabled="!messageText.trim()"
          aria-label="Send message"
          @click="sendMessage"
        />
      </div>
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

    <!-- Handover Modal (Orchestrator session refresh) -->
    <HandoverModal
      :show="showHandoverModal"
      :retirement-prompt="handoverData.retirement_prompt"
      :continuation-prompt="handoverData.continuation_prompt"
      @close="showHandoverModal = false"
    />

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { api } from '@/services/api'
import { useToast } from '@/composables/useToast'
import { useClipboard } from '@/composables/useClipboard'
import { useWebSocketStore } from '@/stores/websocket'
import { useProjectStateStore } from '@/stores/projectStateStore'
import { useAgentJobs } from '@/composables/useAgentJobs'
import { getStatusLabel, getStatusColor, isStatusItalic } from '@/utils/statusConfig'
import { getAgentColor as getAgentColorConfig } from '@/config/agentColors'
import { hexToRgba, getAgentBadgeStyle } from '@/utils/colorUtils'
import { shouldShowLaunchAction } from '@/utils/actionConfig'
import AgentDetailsModal from '@/components/projects/AgentDetailsModal.vue'
import AgentJobModal from '@/components/projects/AgentJobModal.vue'
import MessageAuditModal from '@/components/projects/MessageAuditModal.vue'
import HandoverModal from '@/components/projects/HandoverModal.vue'

const { copy: clipboardCopy } = useClipboard()

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

})

/**
 * Composables
 */
const { showToast } = useToast()
const wsStore = useWebSocketStore()
const projectStateStore = useProjectStateStore()
const { sortedJobs: sortedAgents, loadJobs, store: agentJobsStore } = useAgentJobs()

/**
 * Subagent mode: all agents launched together by orchestrator (Handover 0875)
 */
const isSubagentMode = computed(() => {
  return ['claude_code_cli', 'codex_cli', 'gemini_cli'].includes(props.project?.execution_mode)
})

/**
 * Handover 0904: Auto check-in state and handlers (multi-terminal only)
 */
const autoCheckinEnabled = ref(props.project?.auto_checkin_enabled ?? false)
const autoCheckinInterval = ref(props.project?.auto_checkin_interval ?? 60)

const showAutoCheckin = computed(() => {
  if (isSubagentMode.value) return false
  const projectId = props.project?.project_id || props.project?.id
  const state = projectStateStore.getProjectState(projectId)
  return !!state?.stagingComplete
})

watch(() => props.project?.auto_checkin_enabled, (val) => {
  if (val !== undefined) autoCheckinEnabled.value = val
})
watch(() => props.project?.auto_checkin_interval, (val) => {
  if (val !== undefined) autoCheckinInterval.value = val
})

async function onAutoCheckinToggle(val) {
  const projectId = props.project?.project_id || props.project?.id
  if (!projectId) return
  try {
    await api.projects.update(projectId, { auto_checkin_enabled: val })
  } catch (err) {
    console.error('[JobsTab] Failed to update auto check-in toggle:', err)
    autoCheckinEnabled.value = !val
    showToast({ message: 'Failed to update auto check-in setting', type: 'error', timeout: 4000 })
  }
}

async function onAutoCheckinIntervalChange(val) {
  const projectId = props.project?.project_id || props.project?.id
  if (!projectId) return
  try {
    await api.projects.update(projectId, { auto_checkin_interval: val })
  } catch (err) {
    console.error('[JobsTab] Failed to update auto check-in interval:', err)
    autoCheckinInterval.value = props.project?.auto_checkin_interval ?? 60
    showToast({ message: 'Failed to update check-in interval', type: 'error', timeout: 4000 })
  }
}

/**
 * Handover 0411a: Proposed execution order phases for multi-terminal mode.
 * Returns structured phase data with labels like "(Start)", "(Phase 1 Parallel Execution)", "(Phase 2)".
 * Hardcoded first entry: (Start) Orchestrator.
 * Phases with '+' (multiple agents) get "Parallel Execution" suffix.
 */
const executionOrderPhases = computed(() => {
  // Only show execution order in multi-terminal mode
  const executionMode = props.project?.execution_mode
  if (['claude_code_cli', 'codex_cli', 'gemini_cli'].includes(executionMode)) return null

  const agentList = sortedAgents.value
  if (!agentList.some(a => a.phase != null)) return null

  // Group by phase (skip orchestrator — hardcoded as Start)
  const groups = {}
  for (const agent of agentList) {
    if (isOrchestrator(agent)) continue
    const phase = agent.phase ?? 999
    if (!groups[phase]) groups[phase] = []
    const agentColor = getAgentColor(agent.agent_name || agent.agent_display_name)
    groups[phase].push({
      displayName: agent.agent_display_name || agent.agent_name || 'unknown',
      color: agentColor,
      tintedBg: hexToRgba(agentColor, 0.15),
    })
  }

  // Build structured phases with hardcoded Start > Orchestrator first
  const phases = [{
    label: 'Start',
    agents: [{
      displayName: 'Orchestrator',
      color: getAgentColor('orchestrator'),
      tintedBg: hexToRgba(getAgentColor('orchestrator'), 0.15),
    }],
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
 * Handover 0829: Sort table rows by phase order.
 * Orchestrator always first, then ascending phase, unphased agents last.
 * Within the same phase, preserves the existing store sort order.
 */
const phaseSortedAgents = computed(() => {
  return [...sortedAgents.value].sort((a, b) => {
    const phaseA = isOrchestrator(a) ? -1 : (a.phase ?? 999)
    const phaseB = isOrchestrator(b) ? -1 : (b.phase ?? 999)
    if (phaseA !== phaseB) return phaseA - phaseB
    return 0
  })
})

/**
 * Handover 0829: Phase badge color palette.
 * Reuses tones from the execution order bar for visual consistency.
 */

/**
 * GiljoAI face icons: gray default, yellow on hover/active
 */
const giljoFaceIcon = '/icons/Giljo_Inactive_Dark.svg'
const giljoFaceIconActive = '/icons/Giljo_YW_Face.svg'

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
const showHandoverModal = ref(false)
const handoverData = ref({ retirement_prompt: '', continuation_prompt: '' })
const jobModalInitialTab = ref('mission')
const messageAuditInitialTab = ref('sent')
const selectedJobId = ref(null)
const selectedAgent = computed(() => agentJobsStore.getJob(selectedJobId.value))

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
      message: 'Failed to load agent jobs. Refresh the page or try again.',
      type: 'error',
      timeout: 5000,
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
 * Get agent avatar color - uses centralized agentColors config
 */
function getAgentColor(displayName) {
  return getAgentColorConfig(displayName).hex
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
 * Format duration between started_at and completed_at (or now for working agents)
 * Shows: "---" if not started, live elapsed time if working, final duration if completed
 */
function formatDuration(agent) {
  if (!agent.started_at) {
    return '---'
  }

  // Handover 0827d: Include accumulated time from previous reactivation cycles
  const accumulatedMs = (agent.accumulated_duration_seconds || 0) * 1000

  const start = new Date(agent.started_at).getTime()
  // Use completed_at if available, otherwise use current time (for working agents)
  const end = agent.completed_at ? new Date(agent.completed_at).getTime() : now.value
  const segmentMs = end - start

  if (segmentMs < 0 && accumulatedMs <= 0) {
    return '---'
  }

  const durationMs = accumulatedMs + Math.max(0, segmentMs)

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
 * Get count of messages waiting to be read by agent
 */
function getMessagesWaiting(agent) {
  return agent?.messages_waiting_count ?? 0
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
  // Hide play button until staging is complete (Handover 0875)
  const projectId = props.project?.project_id || props.project?.id
  const state = projectStateStore.getProjectState(projectId)
  if (!state?.stagingComplete) return false

  // Get execution mode from project prop (read-only)
  const executionMode = props.project?.execution_mode
  const claudeCodeCliMode = ['claude_code_cli', 'codex_cli', 'gemini_cli'].includes(executionMode)

  // Use consolidated function from actionConfig.js
  return shouldShowLaunchAction(agent, claudeCodeCliMode)
}

/**
 * Set of agent job IDs where user has manually reactivated the play button (Handover 0875)
 */
const reactivatedAgents = ref(new Set())

/**
 * Fade the play button for any status other than "waiting"
 * Unless the user has manually reactivated it via the recycle button.
 */
function isPlayButtonFaded(agent) {
  const jobId = agent.job_id || agent.agent_id
  if (reactivatedAgents.value.has(jobId)) return false
  return agent.status !== 'waiting'
}

/**
 * Reactivate the play button for an agent (Handover 0875)
 * Allows re-copying the prompt after initial launch.
 */
function reactivatePlay(agent) {
  const jobId = agent.job_id || agent.agent_id
  reactivatedAgents.value.add(jobId)
}

/**
 * Handle Play button click
 */
async function handlePlay(agent) {
  // Re-fade after re-copy (Handover 0875)
  const jobId = agent.job_id || agent.agent_id
  reactivatedAgents.value.delete(jobId)

  try {
    // Handover 0337: CLI mode implementation prompt for orchestrator
    if (agent.agent_display_name === 'orchestrator') {
      // CLI mode: Generate implementation prompt
      if (['claude_code_cli', 'codex_cli', 'gemini_cli'].includes(props.project?.execution_mode)) {
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
          showToast({
            message: `Implementation prompt copied! ${response.data.agent_count + 1} jobs ready (1 orchestrator, ${response.data.agent_count} agents)`,
            type: 'success',
            timeout: 5000
          })
        } catch (error) {
          const errorMsg = error.response?.data?.detail || 'Failed to generate implementation prompt'
          showToast({
            message: errorMsg,
            type: 'error',
            timeout: 6000
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
        showToast({
          message: `Orchestrator prompt copied! ${response.data.agent_count} agents ready for launch.`,
          type: 'success',
          timeout: 5000
        })
      } catch (error) {
        const errorMsg = error.response?.data?.detail || 'Failed to generate orchestrator prompt'
        showToast({
          message: errorMsg,
          type: 'error',
          timeout: 6000
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
    showToast({ message: 'Launch prompt copied to clipboard', type: 'success', timeout: 3000 })
  } catch (error) {
    console.error('[JobsTab] Failed to prepare launch prompt:', error)
    const msg = error.response?.data?.detail || error.message || 'Failed to prepare launch prompt'
    showToast({ message: msg, type: 'error', timeout: 5000 })
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
      // Store both prompts and open the handover modal
      handoverData.value = {
        retirement_prompt: response.data.retirement_prompt,
        continuation_prompt: response.data.continuation_prompt,
      }
      showHandoverModal.value = true
    } else {
      throw new Error(response.data.error || 'Session refresh failed')
    }
  } catch (error) {
    console.error('[JobsTab] Hand over failed:', error)
    const msg = error.response?.data?.detail || error.message || 'Hand over failed'
    showToast({
      message: msg,
      type: 'error',
      timeout: 5000,
    })
  }
}

/**
 * Handle Stop Project button click (Handover 0498)
 * Calls termination prompt endpoint and copies prompt to clipboard
 */
async function handleStopProject(_agent) {
  try {
    const response = await api.prompts.termination(projectId.value)

    if (response.data.prompt) {
      const copyOk = await clipboardCopy(response.data.prompt)
      if (!copyOk) throw new Error('Clipboard copy failed')

      showToast({
        message: `Termination prompt copied! Paste into orchestrator terminal. (${response.data.agent_count} agents)`,
        type: 'warning',
        timeout: 8000,
      })
    } else {
      throw new Error('No prompt returned')
    }
  } catch (error) {
    console.error('[JobsTab] Stop project failed:', error)
    const msg = error.response?.data?.detail || error.message || 'Failed to generate termination prompt'
    showToast({
      message: msg,
      type: 'error',
      timeout: 5000,
    })
  }
}

/**
 * Send message via API (Handover 0243e)
 * Integrates with backend message service with API call, error handling, and toast notifications
 */
async function sendMessage() {
  if (!messageText.value.trim()) {
    showToast({ message: 'Message cannot be empty', type: 'warning', timeout: 3000 })
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
      timeout: 3000
    })

    messageText.value = ''
    // Message counts will update via WebSocket event
  } catch (error) {
    console.error('[JobsTab] Send message failed:', error)
    const msg = error.response?.data?.detail || error.message || 'Failed to send message'
    showToast({
      message: `Failed to send message: ${msg}`,
      type: 'error',
      timeout: 5000
    })
  } finally {
    sending.value = false
  }
}

/**
 * Copy helper using shared composable
 */
async function copyToClipboard(text) {
  const success = await clipboardCopy(text)
  if (!success) {
    throw new Error('Clipboard copy failed')
  }
}

// WebSocket updates for jobs/messages flow through the centralized router (0379a)
// into `agentJobsStore` (0379b). JobsTab only renders store state and performs user actions.
</script>

<style scoped lang="scss">
@use '../../styles/design-tokens' as *;

.implement-tab-wrapper {
  padding: 16px;

  .table-container {
    background: $elevation-raised;
    border-radius: $border-radius-rounded;
    margin-bottom: 16px;
    overflow: hidden;

    // Handover 0411a: Proposed execution order display
    .execution-order-section {
      padding: 10px 14px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      text-align: center;

      .execution-order-title {
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: $color-text-secondary;
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
            font-size: 0.72rem;
            font-weight: 700;
            color: white;
          }

          .phase-agents {
            display: inline-flex;
            align-items: center;
            gap: 4px;

            .agent-tinted-badge {
              white-space: nowrap;
            }

            .phase-separator {
              font-size: 14px;
              font-weight: 700;
              color: white;
            }
          }
        }
      }
    }

    // Handover 0904: Auto check-in controls
    .auto-checkin-section {
      padding: 10px 14px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);

      .auto-checkin-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
      }

      .auto-checkin-label {
        font-size: 0.78rem;
        font-weight: 600;
        color: #8895a8;
      }

      .auto-checkin-toggle {
        flex-shrink: 0;
      }

      .auto-checkin-interval {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-top: 6px;
      }

      .auto-checkin-interval-label {
        font-size: 0.72rem;
        color: #8895a8;
      }

      .auto-checkin-btn-group {
        :deep(.v-btn) {
          font-size: 0.72rem;
          min-width: 48px;
          height: 28px;
          text-transform: none;
        }
      }
    }

    // 0873: transparent table bg so smooth-border inset shadow shows on all sides
    .agents-table,
    :deep(.v-table) {
      background: transparent;
    }

    .agents-table {
      width: 100%;
      border-collapse: separate;
      border-spacing: 0;

      thead th {
        text-align: left;
        padding: 10px 14px;
        @include table-header-label;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        background: $elevation-raised;
        white-space: nowrap;

        &.col-phase {
          width: 56px;
          text-align: center;
        }

        &.col-play {
          width: 40px;
          padding: 0;
        }

        &.col-agent-name {
          width: 1%;
          white-space: nowrap;
        }

        &.col-center {
          text-align: center;
        }

        &.col-actions {
          width: 160px;
        }
      }

      tbody tr {
        transition: background $transition-fast;
        cursor: pointer;

        &:hover {
          background: rgba(255, 255, 255, 0.02);
        }
      }

      tbody td {
        padding: 12px 14px;
        font-size: 0.78rem;
        @include table-row-separator;
        vertical-align: middle;

        &.phase-cell {
          width: 56px;
          text-align: center;
          padding: 12px 8px;

          .phase-badge {
            display: inline-block;
            font-size: 0.68rem;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: $border-radius-default;
            background-color: rgba(251, 192, 45, 0.15); // design-token-exempt: tinted amber phase badge
            color: #FBC02D; // design-token-exempt: amber phase text
            white-space: nowrap;

            &--none {
              background: transparent;
              color: rgba(var(--v-theme-on-surface), 0.35);
            }
          }
        }

        &.play-cell {
          width: 40px;
          padding: 12px 4px 12px 14px;
          text-align: center;

          .play-btn-slot {
            display: flex;
            align-items: center;
            gap: 2px;
          }

          .play-circle-btn {
            width: 30px;
            height: 30px;
            border: none;
            display: grid;
            place-items: center;
            padding: 0;

            .v-icon {
              color: $color-brand-yellow;
            }

            &.play-btn-faded {
              background: transparent;
              color: $color-text-muted;
              opacity: 0.2;
              cursor: default;
              pointer-events: none;

              .v-icon {
                color: $color-text-muted;
              }
            }
          }

        }

        &.agent-display-name-cell {
          width: 1%;
          white-space: nowrap;
          padding-left: 4px;

          .agent-card-row {
            display: flex;
            align-items: center;
            gap: 10px;
            white-space: nowrap;
          }

          .agent-badge {
            width: 32px;
            height: 32px;
            border-radius: $border-radius-default;
            display: grid;
            place-items: center;
            font-size: 0.62rem;
            font-weight: 700;
            flex-shrink: 0;
            position: relative;
            transition: filter 0.3s ease;
          }

          // Active agent: breathing glow + expanding pulse ring
          .agent-badge--active {
            animation: badgeBreathe 2.4s ease-in-out infinite;

            // Outer expanding ring (uses currentColor from the badge text)
            &::before,
            &::after {
              content: '';
              position: absolute;
              inset: 0;
              border-radius: inherit;
              pointer-events: none;
              animation: badgePulseRing 2.4s ease-out infinite;
            }

            &::after {
              animation-delay: 1.2s;
            }
          }

          @keyframes badgeBreathe {
            0%, 100% { filter: brightness(1); }
            50% { filter: brightness(1.3); }
          }

          @keyframes badgePulseRing {
            0% { box-shadow: 0 0 0 0 currentColor; opacity: 0.4; }
            70% { box-shadow: 0 0 0 10px currentColor; opacity: 0; }
            100% { box-shadow: 0 0 0 10px currentColor; opacity: 0; }
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

          .agent-info {
            display: flex;
            flex-direction: column;
            min-width: 0;

            .agent-name-primary {
              font-size: 0.8rem;
              font-weight: 500;
              text-transform: capitalize;
            }

            .agent-display-name-secondary {
              font-size: 0.62rem;
              color: $color-text-muted;
              text-transform: capitalize;
            }
          }
        }

        &.status-cell {
          text-align: center;
          font-size: 0.75rem;

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
          font-family: 'IBM Plex Mono', monospace;
          font-size: 0.72rem;
          color: $color-text-secondary;
        }

        .steps-trigger {
          font-family: 'IBM Plex Mono', monospace;
          font-size: 0.72rem;
          color: $color-text-secondary;
        }

        .steps-skipped {
          color: #ff9800; // design-token-exempt: status-blocked inline
          font-weight: 600;
        }

        .message-count-button {
          background: none;
          border: none;
          padding: 0;
          cursor: pointer;
          color: inherit;
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

          &.zero {
            background: rgba(103, 189, 109, 0.12);
            color: #67bd6d; // design-token-exempt: status-complete
          }

          &.has-msgs {
            background: rgba(255, 152, 0, 0.15);
            color: #ff9800; // design-token-exempt: status-blocked
          }
        }

        &.actions-cell {
          text-align: right;
          white-space: nowrap;

          .actions-inline {
            display: flex;
            gap: 2px;

            .v-btn {
              min-width: auto;
              width: 30px;
              height: 30px;
              padding: 0;
            }
          }

          .actions-menu {
            display: none;

            .giljo-face-icon.menu-icon {
              width: 20px;
              height: 20px;
              margin-right: 8px;
            }
          }
        }
      }

      // Remove border-bottom on last row
      tbody tr:last-child td {
        border-bottom: none;
      }
    }
  }

  /* Message composer — smooth-border panel (0870j) */
  .message-composer {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 18px;
    background: $elevation-raised;
    border-radius: $border-radius-rounded;
    margin-bottom: 20px;

    .composer-channels {
      display: flex;
      gap: 4px;
      flex-shrink: 0;
      order: 0;
    }

    .composer-input {
      display: flex;
      flex: 1;
      gap: 8px;
      align-items: center;
      min-width: 0;
      order: 1;
    }

    @media (max-width: 576px) {
      flex-wrap: wrap;

      .composer-channels {
        order: 2;
        width: 100%;
      }

      .composer-input {
        order: 1;
        width: 100%;
        flex-basis: 100%;
      }
    }

    .recipient-btn,
    .broadcast-btn {
      border: none !important;
      border-radius: $border-radius-pill;
      text-transform: none;
      font-size: 0.72rem;
      font-weight: 500;
      padding: 6px 14px;
      color: $color-text-muted;
      transition: all $transition-normal ease;

      &.v-btn--variant-flat {
        background: rgba(255, 195, 0, 0.12);
        color: $color-brand-yellow;
        box-shadow: none;
      }

      &.v-btn--variant-outlined {
        background: transparent;

        &:hover {
          background: rgba(255, 255, 255, 0.04);
          color: $color-text-secondary;
        }
      }
    }

    .message-input {
      flex: 1;

      ::v-deep(.v-field) {
        background: $elevation-elevated;
        border: none !important;
        box-shadow: inset 0 0 0 1px var(--smooth-border-color, rgba(255, 255, 255, 0.10));
        border-radius: $border-radius-default;

        input {
          color: $color-text-primary;
          font-size: 0.78rem;
          padding: 8px 12px;

          &::placeholder {
            color: $color-text-muted;
          }
        }

        &:hover {
          box-shadow: inset 0 0 0 1px var(--smooth-border-color, rgba(255, 255, 255, 0.14));
        }

        &.v-field--focused {
          box-shadow: inset 0 0 0 1px rgba($color-brand-yellow, 0.3);
        }
      }
    }

    .send-btn {
      min-width: auto;
      width: 36px;
      height: 36px;
      border-radius: $border-radius-default;

      &:disabled {
        opacity: 0.4;
      }
    }
  }

  /* GiljoAI Face Icon — gray default, yellow on hover */
  .giljo-face-icon {
    width: 18px;
    height: 18px;
    object-fit: contain;
  }

  .giljo-face-btn {
    .giljo-face-hover { display: none; }
    .giljo-face-default { display: block; }

    &:hover {
      .giljo-face-hover { display: block; }
      .giljo-face-default { display: none; }
    }
  }

  /* Responsive: below 1200px — collapse action icons to three-dot menu */
  @media (max-width: 1200px) {
    .table-container .agents-table {
      tbody td.actions-cell {
        .actions-inline {
          display: none;
        }

        .actions-menu {
          display: inline-flex;
        }
      }
    }
  }

  /* Responsive: below 840px — hide agent name text, show badge only */
  @media (max-width: 840px) {
    .table-container .agents-table {
      thead th.col-agent-name {
        text-align: center;
      }

      tbody td.agent-display-name-cell {
        text-align: center;
        padding-left: 14px;

        .agent-card-row {
          justify-content: center;
        }

        .agent-info {
          display: none;
        }
      }
    }
  }

  /* Responsive: portrait / narrow screens — hide extra columns */
  @media (max-width: 768px) {
    .table-container .agents-table {
      .hide-mobile {
        display: none;
      }
    }
  }
}
</style>
