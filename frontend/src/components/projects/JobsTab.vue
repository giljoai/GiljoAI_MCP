<template>
  <div class="implement-tab-wrapper">
    <!-- Agent Table Container -->
    <div class="table-container smooth-border">
      <!-- Handover 0411a: Proposed execution order (multi-terminal mode) -->
      <ExecutionOrderBar
        v-if="executionOrderPhases"
        :phases="executionOrderPhases"
      />

      <!-- Handover 0904: Auto check-in controls (multi-terminal only, after staging) -->
      <AutoCheckinControls
        v-if="showAutoCheckin"
        :enabled="autoCheckinEnabled"
        :interval="autoCheckinInterval"
        @update:checkin="onAutoCheckinChange"
      />

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
            <!-- Play button: own column, no header -->
            <td class="play-cell">
              <div class="play-btn-slot">
                <template v-if="shouldShowCopyButton(agent)">
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

            <!-- Duration -->
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
                      @click="handleStopProject(projectId, clipboardCopy)"
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
                      @click="handleStopProject(projectId, clipboardCopy)"
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
    <MessageComposer :project-id="projectId" />

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
import { useToast } from '@/composables/useToast'
import { useClipboard } from '@/composables/useClipboard'
import { useWebSocketStore } from '@/stores/websocket'
import { useProjectStateStore } from '@/stores/projectStateStore'
import { useAgentJobs } from '@/composables/useAgentJobs'
import { useJobActions } from '@/composables/useJobActions'
import { usePlayButton } from '@/composables/usePlayButton'
import { getStatusLabel, getStatusColor, isStatusItalic } from '@/utils/statusConfig'
import { getAgentColor as getAgentColorConfig } from '@/config/agentColors'
import { hexToRgba, getAgentBadgeStyle } from '@/utils/colorUtils'
import { api } from '@/services/api'
import AgentDetailsModal from '@/components/projects/AgentDetailsModal.vue'
import AgentJobModal from '@/components/projects/AgentJobModal.vue'
import MessageAuditModal from '@/components/projects/MessageAuditModal.vue'
import HandoverModal from '@/components/projects/HandoverModal.vue'
import MessageComposer from '@/components/projects/MessageComposer.vue'
import ExecutionOrderBar from '@/components/projects/ExecutionOrderBar.vue'
import AutoCheckinControls from '@/components/projects/AutoCheckinControls.vue'

/** JobsTab — Handover 0241 + 0243c + 0461d. Pure table layout with inline actions. */
const props = defineProps({
  /** Project object with project_id/id and name fields. */
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

const { showToast } = useToast()
const { copy: clipboardCopy } = useClipboard()
const wsStore = useWebSocketStore()
const projectStateStore = useProjectStateStore()
const { sortedJobs: sortedAgents, loadJobs, store: agentJobsStore } = useAgentJobs()

const projectId = computed(() => props.project?.project_id || props.project?.id)

const {
  showAgentDetailsModal,
  showAgentJobModal,
  showMessageAuditModal,
  showHandoverModal,
  handoverData,
  jobModalInitialTab,
  messageAuditInitialTab,
  selectedAgent,
  handleMessages,
  handleStepsClick,
  handleAgentRole,
  handleAgentJob,
  handleHandOver,
  handleStopProject,
} = useJobActions((id) => agentJobsStore.getJob(id))

const {
  shouldShowCopyButton,
  isPlayButtonFaded,
  reactivatePlay,
  handlePlay,
} = usePlayButton(
  computed(() => props.project),
  (pid) => projectStateStore.getProjectState(pid),
  clipboardCopy
)

/** Subagent mode: all agents launched together by orchestrator (Handover 0875) */
const isSubagentMode = computed(() => {
  return ['claude_code_cli', 'codex_cli', 'gemini_cli'].includes(props.project?.execution_mode)
})

/** Handover 0904: Auto check-in state (multi-terminal only) */
const autoCheckinEnabled = ref(props.project?.auto_checkin_enabled ?? false)
const autoCheckinInterval = ref(props.project?.auto_checkin_interval ?? 10)

const showAutoCheckin = computed(() => {
  if (isSubagentMode.value) return false
  const state = projectStateStore.getProjectState(projectId.value)
  return !!state?.stagingComplete
})

watch(() => props.project?.auto_checkin_enabled, (val) => {
  if (val !== undefined) autoCheckinEnabled.value = val
})
watch(() => props.project?.auto_checkin_interval, (val) => {
  if (val !== undefined) autoCheckinInterval.value = val
})

async function onAutoCheckinChange({ enabled, interval }) {
  if (!projectId.value) return
  const payload = { auto_checkin_enabled: enabled }
  if (interval !== undefined) payload.auto_checkin_interval = interval
  try {
    await api.projects.update(projectId.value, payload)
    autoCheckinEnabled.value = enabled
    if (interval !== undefined) autoCheckinInterval.value = interval
  } catch (err) {
    console.error('[JobsTab] Failed to update auto check-in:', err)
    autoCheckinEnabled.value = props.project?.auto_checkin_enabled ?? false
    autoCheckinInterval.value = props.project?.auto_checkin_interval ?? 10
    showToast({ message: 'Failed to update auto check-in setting', type: 'error', timeout: 4000 })
  }
}

/** Handover 0411a: Proposed execution order phases for multi-terminal mode. */
const executionOrderPhases = computed(() => {
  const executionMode = props.project?.execution_mode
  if (['claude_code_cli', 'codex_cli', 'gemini_cli'].includes(executionMode)) return null

  const agentList = sortedAgents.value
  if (!agentList.some(a => a.phase != null)) return null

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

/** Handover 0829: Sort table rows by phase order. */
const phaseSortedAgents = computed(() => {
  return [...sortedAgents.value].sort((a, b) => {
    const phaseA = isOrchestrator(a) ? -1 : (a.phase ?? 999)
    const phaseB = isOrchestrator(b) ? -1 : (b.phase ?? 999)
    if (phaseA !== phaseB) return phaseA - phaseB
    return 0
  })
})

const giljoFaceIcon = '/icons/Giljo_Inactive_Dark.svg'
const giljoFaceIconActive = '/icons/Giljo_YW_Face.svg'

function isOrchestrator(agent) {
  return agent?.agent_name === 'orchestrator' || agent?.agent_display_name === 'orchestrator'
}

function getPrimaryAgentLabel(agent) {
  if (!agent) return ''
  if (isOrchestrator(agent)) return agent.agent_name || agent.agent_display_name || ''
  return agent.agent_display_name || agent.agent_name || ''
}

function getAgentColor(displayName) {
  return getAgentColorConfig(displayName).hex
}

function getAgentAbbr(displayName) {
  if (!displayName) return '??'

  const parts = displayName.split(/[-_\s]+/).filter(Boolean)

  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase()
  }

  return displayName.substring(0, 2).toUpperCase()
}

function getMessagesWaiting(agent) {
  return agent?.messages_waiting_count ?? 0
}

const now = ref(Date.now())
let durationTimer = null

function formatDuration(agent) {
  if (!agent.started_at) return '---'

  const accumulatedMs = (agent.accumulated_duration_seconds || 0) * 1000
  const start = new Date(agent.started_at).getTime()
  const end = agent.completed_at ? new Date(agent.completed_at).getTime() : now.value
  const segmentMs = end - start

  if (segmentMs < 0 && accumulatedMs <= 0) return '---'

  const durationMs = accumulatedMs + Math.max(0, segmentMs)

  if (durationMs < 60000) return `${Math.round(durationMs / 1000)}s`

  if (durationMs < 3600000) {
    const mins = Math.floor(durationMs / 60000)
    const secs = Math.round((durationMs % 60000) / 1000)
    return `${mins}m ${secs}s`
  }

  const hours = Math.floor(durationMs / 3600000)
  const mins = Math.floor((durationMs % 3600000) / 60000)
  return `${hours}h ${mins}m`
}

const loadingJobs = ref(false)

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

watch(projectId, () => { refreshJobs() }, { immediate: true })

let unsubscribeConnectionListener = null
onMounted(() => {
  unsubscribeConnectionListener = wsStore.onConnectionChange((connectionEvent) => {
    if (connectionEvent?.state === 'connected' && connectionEvent?.isReconnect) {
      refreshJobs()
    }
  })

  durationTimer = setInterval(() => { now.value = Date.now() }, 1000)
})

onUnmounted(() => {
  unsubscribeConnectionListener?.()

  if (durationTimer) {
    clearInterval(durationTimer)
    durationTimer = null
  }
})
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
            background-color: rgba($color-phase-amber, 0.15);
            color: $color-phase-amber;
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
          color: $color-status-blocked;
          font-weight: 600;
        }

        .message-count-button {
          background: none;
          border: none;
          padding: 0;
          cursor: pointer;
          color: inherit;
        }

        .msg-badge {
          display: inline-grid;
          place-items: center;
          width: 26px;
          height: 26px;
          border-radius: 50%;
          font-size: 0.62rem;
          font-weight: 600;

          &.zero {
            background: rgba($color-status-complete, 0.12);
            color: $color-status-complete;
          }

          &.has-msgs {
            background: rgba($color-status-blocked, 0.15);
            color: $color-status-blocked;
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
