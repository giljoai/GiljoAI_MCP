<template>
  <v-card
    class="agent-card"
    :class="[
      `agent-card--${agent.agent_display_name}`,
      `status--${agent.status}`,
      { 'priority-card': isPriorityState },
    ]"
    :style="cardStyles"
    role="article"
    :aria-label="cardAriaLabel"
  >
    <!-- Colored Header with Agent Type -->
    <div class="agent-card__header" :style="headerStyles">
      <span class="agent-header-text">{{ agentDisplayNameLabel }}</span>
    </div>

    <!-- Card Body -->
    <v-card-text class="agent-card__body pa-4">
      <!-- Agent ID -->
      <div class="agent-id mb-2">
        <div class="text-caption text-grey mb-1">Agent ID</div>
        <div class="text-caption font-weight-medium agent-id-value">{{ fullAgentId }}</div>
      </div>

      <!-- Status Display (Jobs Tab only) -->
      <div v-if="mode === 'jobs'" class="agent-status mb-3">
        <span class="text-caption text-grey">Status:</span>
        <span class="text-body-2 font-weight-bold ml-1">{{ statusConfig.label }}</span>
      </div>

      <!-- Message Badges (Jobs Tab only) -->
      <div v-if="mode === 'jobs' && hasMessages" class="message-badges mb-3 d-flex flex-wrap gap-2">
        <!-- Unread Messages (Red) -->
        <v-chip
          v-if="unreadCount > 0"
          color="error"
          size="x-small"
          prepend-icon="mdi-message-badge"
        >
          {{ unreadCount }} Unread
        </v-chip>

        <!-- Acknowledged Messages (Green) -->
        <v-chip
          v-if="acknowledgedCount > 0"
          color="success"
          size="x-small"
          prepend-icon="mdi-check-all"
        >
          {{ acknowledgedCount }} Read
        </v-chip>

        <!-- Sent Messages (Grey) -->
        <v-chip v-if="sentCount > 0" color="grey-darken-2" size="x-small" prepend-icon="mdi-send">
          {{ sentCount }} Sent
        </v-chip>
      </div>

      <!-- Scrollable Content Area -->
      <div class="scrollable-content">
        <!-- Launch Tab Mode: Mission Display -->
        <div v-if="mode === 'launch'" class="mission-content">
          <div class="text-caption text-grey mb-1">Role/Mission:</div>
          <div class="text-body-2 mission-text">
            {{ agent.mission || 'No mission assigned' }}
          </div>
        </div>

        <!-- Jobs Tab - Waiting State -->
        <div v-else-if="agent.status === 'waiting'" class="waiting-content">
          <div class="text-caption text-grey mb-1">Mission:</div>
          <div class="text-body-2">
            {{ truncatedMission }}
          </div>
        </div>

        <!-- Jobs Tab - Working State -->
        <div v-else-if="agent.status === 'working'" class="working-content">
          <!-- Progress Bar -->
          <div class="progress-section mb-3">
            <div class="d-flex align-center justify-space-between mb-1">
              <span class="text-caption text-grey">Progress</span>
              <span class="text-caption font-weight-bold">{{ agent.progress || 0 }}%</span>
            </div>
            <v-progress-linear
              :model-value="agent.progress || 0"
              color="primary"
              height="6"
              rounded
            />
          </div>

          <!-- Health Indicator (Handover 0107: Last Update Time) -->
          <div
            v-if="showHealthIndicator"
            class="health-indicator mb-3"
            role="status"
            :aria-label="`Agent health: ${healthConfig.label}. ${healthConfig.tooltip}`"
          >
            <v-chip
              :color="healthConfig.color"
              size="x-small"
              :prepend-icon="healthConfig.icon"
              :class="['health-chip', { 'pulse-warning': agent.health_state === 'critical' }]"
              tabindex="0"
            >
              <span class="text-caption">{{ healthConfig.label }}</span>
            </v-chip>

            <!-- Tooltip for details -->
            <v-tooltip activator="parent" location="bottom">
              <div class="text-caption">
                <div class="font-weight-bold mb-1">{{ healthConfig.tooltip }}</div>
                <div v-if="agent.health_issue_description" class="mt-1">
                  {{ agent.health_issue_description }}
                </div>
                <div v-if="agent.recommended_action" class="mt-1 text-grey-lighten-1">
                  → {{ agent.recommended_action }}
                </div>
              </div>
            </v-tooltip>
          </div>

          <!-- Stale Warning Alert (Handover 0107) -->
          <v-alert v-if="isStale" type="warning" variant="tonal" density="compact" class="mb-3">
            <div class="d-flex align-center">
              <v-icon size="small" class="mr-2">mdi-clock-alert</v-icon>
              <span class="text-caption">
                No update for {{ minutesSinceLastUpdate }}m - Agent may be stuck
              </span>
            </div>
          </v-alert>

          <!-- Current Task -->
          <div v-if="agent.current_task" class="current-task">
            <div class="text-caption text-grey mb-1">Current Task:</div>
            <div class="text-body-2">
              {{ agent.current_task }}
            </div>
          </div>
        </div>

        <!-- Jobs Tab - Complete State -->
        <div v-else-if="agent.status === 'complete'" class="complete-content text-center py-4">
          <div class="complete-text">Complete</div>
        </div>

        <!-- Jobs Tab - Silent State (Handover 0491: Agent stopped communicating) -->
        <div v-else-if="agent.status === 'silent'" class="silent-content">
          <v-alert type="warning" density="compact" variant="tonal" class="mb-2">
            <div class="text-caption font-weight-bold mb-1">Silent</div>
            <div class="text-body-2">
              {{ agent.block_reason || 'Agent stopped communicating' }}
            </div>
          </v-alert>
        </div>

        <!-- Jobs Tab - Blocked State -->
        <div v-else-if="agent.status === 'blocked'" class="error-content">
          <v-alert type="warning" density="compact" variant="tonal" class="mb-2">
            <div class="text-caption font-weight-bold mb-1">Blocked</div>
            <div class="text-body-2">
              {{ agent.block_reason || 'No details available' }}
            </div>
          </v-alert>
        </div>

        <!-- Decommissioned/Cancelled states removed (Handovers 0461d, 0491) -->
      </div>

      <!-- Orchestrator special launch icons removed per UX request -->
    </v-card-text>

    <!-- REMOVED: Succession Timeline (0461d) - Uses simple handover API now -->

    <!-- Action Button -->
    <v-card-actions class="pa-4 pt-0 agent-card-actions">
      <!-- Custom Actions Slot (for orchestrator special buttons) -->
      <slot name="actions">
        <!-- Default Action Buttons -->
        <!-- Launch Tab: Edit Mission -->
        <v-btn
          v-if="mode === 'launch'"
          variant="outlined"
          color="primary"
          block
          @click="$emit('edit-mission', agent)"
        >
          <v-icon start>mdi-pencil</v-icon>
          Edit Mission
        </v-btn>

        <!-- Jobs Tab: Waiting State - Launch Agent -->
        <v-tooltip
          v-if="mode === 'jobs' && agent.status === 'waiting'"
          :disabled="!promptButtonDisabled"
          location="bottom"
        >
          <template v-slot:activator="{ props: tooltipProps }">
            <v-btn
              v-bind="tooltipProps"
              variant="elevated"
              :color="promptButtonDisabled ? 'grey' : 'yellow-darken-2'"
              :disabled="promptButtonDisabled"
              block
              @click="$emit('launch-agent', agent)"
            >
              <v-icon start>
                {{ promptButtonDisabled ? 'mdi-pause-circle' : 'mdi-rocket-launch' }}
              </v-icon>
              {{ promptButtonDisabled ? 'Claude Code Mode' : 'Launch Agent' }}
            </v-btn>
          </template>
          <span class="text-caption">
            This agent will run as a Claude Code subagent - orchestrator will spawn it automatically
          </span>
        </v-tooltip>

        <!-- Orchestrator: Copy Execution Prompt removed - Launch button handles prompt copy -->

        <!-- REMOVED: Hand Over button (0461d) - Uses simple handover API now -->

        <!-- Jobs Tab: Working State - Details -->
        <v-btn
          v-else-if="mode === 'jobs' && agent.status === 'working'"
          variant="outlined"
          color="primary"
          block
          @click="$emit('view-details', agent)"
        >
          <v-icon start>mdi-information</v-icon>
          Details
        </v-btn>

        <!-- Jobs Tab: Blocked State - View Error -->
        <v-btn
          v-else-if="mode === 'jobs' && agent.status === 'blocked'"
          variant="outlined"
          color="warning"
          block
          @click="$emit('view-error', agent)"
        >
          <v-icon start>mdi-alert-circle</v-icon>
          View Error
        </v-btn>

        <!-- Jobs Tab: Silent State - Clear Silent (Handover 0491) -->
        <v-btn
          v-else-if="mode === 'jobs' && agent.status === 'silent'"
          variant="elevated"
          color="amber-darken-2"
          block
          :loading="clearingSilent"
          @click="clearSilentStatus"
        >
          <v-icon start>mdi-refresh</v-icon>
          Clear Silent
        </v-btn>

        <!-- Complete State: Continue Working OR Close Out (Handover 0113) -->
        <div v-else-if="mode === 'jobs' && agent.status === 'complete'" class="complete-actions">
          <v-btn
            variant="outlined"
            color="primary"
            block
            class="mb-2"
            @click="$emit('continue-working', agent)"
          >
            <v-icon start>mdi-play-circle</v-icon>
            Continue Working
          </v-btn>

          <v-btn
            v-if="isOrchestrator"
            variant="elevated"
            color="success"
            block
            @click="$emit('closeout-project')"
          >
            <v-icon start>mdi-check-circle</v-icon>
            Close Out Project
          </v-btn>
        </div>

        <!-- Cancelled state action removed (Handover 0491) -->
      </slot>
    </v-card-actions>
  </v-card>
</template>

<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'
import { getAgentColor } from '@/config/agentColors'
import { useWebSocket } from '@/composables/useWebSocket'
import { getStatusConfig } from '@/utils/statusConfig'
import api from '@/services/api'

// Handover 0461d: Removed instance_number, decommissioned, and succession chain UI

/**
 * AgentCard Component (Consolidated - Handover 0515a)
 *
 * Unified agent card component replacing:
 * - AgentCardEnhanced (projects)
 * - AgentCard (orchestration)
 * - AgentStatusCard (dashboard)
 *
 * Production-grade reusable agent card matching visual specs in handovers/Launch-Jobs_panels2/
 * Works across Launch Tab, Jobs Tab, and Dashboard with different states.
 *
 * Props:
 * - agent: Agent job object (required)
 * - mode: 'launch' | 'jobs' (default: 'jobs')
 * - isOrchestrator: Special orchestrator features
 * - showCloseoutButton: Show closeout button when all agents complete
 *
 * Emits:
 * - edit-mission: (agent) => void
 * - launch-agent: (agent) => void
 * - view-details: (agent) => void
 * - view-error: (agent) => void
 * - closeout-project: () => void
 * - continue-working: (agent) => void
 * - refresh-jobs: () => void
 */

const props = defineProps({
  agent: {
    type: Object,
    required: true,
    validator: (value) => {
      return value && typeof value === 'object' && 'agent_display_name' in value && 'status' in value
    },
  },
  mode: {
    type: String,
    default: 'jobs',
    validator: (value) => ['launch', 'jobs'].includes(value),
  },
  isOrchestrator: {
    type: Boolean,
    default: false,
  },
  showCloseoutButton: {
    type: Boolean,
    default: false,
  },
  promptButtonDisabled: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits([
  'edit-mission',
  'launch-agent',
  'view-details',
  'view-error',
  'closeout-project',
  'hand-over',
  'continue-working',
  'refresh-jobs',
])

/**
 * Agent color configuration
 */
const agentColor = computed(() => getAgentColor(props.agent.agent_name || props.agent.agent_display_name))

const agentDisplayNameLabel = computed(() => agentColor.value.name)

/**
 * Card styling with agent colors
 */
const cardStyles = computed(() => ({
  width: '280px',
  minHeight: '200px',
  maxHeight: '400px',
  borderRadius: '20px',
  overflow: 'hidden',
  transition: 'all 0.3s ease',
}))

const headerStyles = computed(() => ({
  background: agentColor.value.hex,
  color: 'white',
  padding: '16px 20px',
  textAlign: 'center',
  borderRadius: '18px 18px 0 0',
}))

/**
 * Status configuration for Jobs Tab (using shared utility)
 */
const statusConfig = computed(() => {
  return getStatusConfig(props.agent.status)
})

/**
 * Priority states (moved to top)
 */
const isPriorityState = computed(() => {
  return props.agent.status === 'silent' || props.agent.status === 'blocked'
})

/**
 * Message count calculations
 */
const hasMessages = computed(() => {
  return (
    (props.agent?.messages_waiting_count ?? 0) > 0 ||
    (props.agent?.messages_read_count ?? 0) > 0 ||
    (props.agent?.messages_sent_count ?? 0) > 0
  )
})

const unreadCount = computed(() => props.agent?.messages_waiting_count ?? 0)

const acknowledgedCount = computed(() => props.agent?.messages_read_count ?? 0)

const sentCount = computed(() => props.agent?.messages_sent_count ?? 0)

/**
 * Text truncation helpers
 */
const fullAgentId = computed(() => {
  const id = props.agent.job_id || props.agent.agent_id || 'Unknown'
  return id
})

const truncatedMission = computed(() => {
  const mission = props.agent.mission || 'No mission assigned'
  if (mission.length <= 120) return mission
  return `${mission.substring(0, 120)}...`
})

/**
 * Accessibility label
 */
const cardAriaLabel = computed(() => {
  const type = agentDisplayNameLabel.value
  const status = statusConfig.value.label
  return `${type} agent - ${status}`
})

/**
 * Health Indicator Logic (Handover 0107)
 * Only show health indicator when:
 * 1. Mode is 'jobs' (not 'launch')
 * 2. Agent is active/waiting/working (not in terminal state)
 * 3. Health state is not 'healthy'
 */
const showHealthIndicator = computed(() => {
  // Skip if mode is launch (cards not yet spawned)
  if (props.mode === 'launch') {
    return false
  }

  // Skip if job is in terminal state
  if (['complete', 'silent', 'decommissioned'].includes(props.agent.status)) {
    return false
  }

  // Skip if healthy or no health data
  if (!props.agent.health_state || props.agent.health_state === 'healthy') {
    return false
  }

  return true
})

/**
 * Health Configuration
 * Maps health state to UI config (color, icon, label, tooltip)
 */
const healthConfig = computed(() => {
  const state = props.agent.health_state
  const minutes = props.agent.minutes_since_update || 0

  const configs = {
    warning: {
      color: 'warning',
      icon: 'mdi-clock-alert',
      label: 'Slow response',
      tooltip: `No activity for ${minutes.toFixed(1)} minutes`,
    },
    critical: {
      color: 'error',
      icon: 'mdi-alert-circle',
      label: 'Not responding',
      tooltip: `Agent silent for ${minutes.toFixed(1)} minutes`,
    },
    timeout: {
      color: 'grey-darken-1',
      icon: 'mdi-clock-remove',
      label: 'Timed out',
      tooltip: `No response for ${minutes.toFixed(1)} minutes - may need restart`,
    },
  }

  return configs[state] || configs.warning
})

/**
 * Handover 0107: Agent Monitoring Computed Properties
 */

// Calculate minutes since last progress update
const minutesSinceLastUpdate = computed(() => {
  if (!props.agent.last_progress_at) return null
  const lastUpdate = new Date(props.agent.last_progress_at)
  const now = new Date()
  return Math.floor((now - lastUpdate) / 60000)
})

// Check if agent is stale (no update > 10 minutes while active)
const isStale = computed(() => {
  return (
    minutesSinceLastUpdate.value !== null &&
    minutesSinceLastUpdate.value > 10 &&
    ['working'].includes(props.agent.status)
  )
})

/**
 * Handover 0491: Clear Silent status
 * Calls POST /api/agent-executions/{agent_id}/clear-silent to resume the agent
 */
const clearingSilent = ref(false)

async function clearSilentStatus() {
  const agentId = props.agent.agent_id || props.agent.job_id
  if (!agentId) return

  clearingSilent.value = true
  try {
    await api.post(`/api/agent-executions/${agentId}/clear-silent`)
    emit('refresh-jobs')
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('[AgentCard] Failed to clear silent status:', error)
  } finally {
    clearingSilent.value = false
  }
}

/**
 * Initialize composables
 */
const { on, off } = useWebSocket()

/**
 * Lifecycle hooks for WebSocket event listeners
 */
onMounted(() => {
  // Listen for stale warnings from background monitor
  on('job:stale_warning', (data) => {
    if (data.job_id === props.agent.id) {
      // Force component update to refresh health display
      // Note: This is handled automatically by Vue reactivity
      // when agent data is updated by parent component
    }
  })

  // Listen for progress updates
  on('job:progress_update', (data) => {
    if (data.job_id === props.agent.id) {
      // Update last_progress_at timestamp
      // Note: Parent component should update the agent prop
      // This listener is for real-time UI refresh triggers
    }
  })
})

onBeforeUnmount(() => {
  // Cleanup WebSocket listeners
  off('job:stale_warning')
  off('job:progress_update')
})
</script>

<style scoped lang="scss">
@use '@/styles/agent-colors.scss' as *;

.agent-card {
  display: flex;
  flex-direction: column;
  transition: all 0.3s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
  }

  &.priority-card {
    box-shadow: 0 0 0 3px rgba(255, 152, 0, 0.5);
  }
}

.agent-card__header {
  font-weight: 600;
  font-size: 16px;
  text-transform: none;
  letter-spacing: 0;
  padding: 16px 20px;
  text-align: center;
  border-radius: 18px 18px 0 0;
}

.agent-header-text {
  flex: 1;
}

.agent-card__body {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
}

.agent-id {
  padding: 8px;
  background: rgba(0, 0, 0, 0.03);
  border-radius: 4px;
}

.agent-id-value {
  font-size: 10px;
  font-family: 'Courier New', monospace;
  white-space: nowrap;
  line-height: 1.4;
  letter-spacing: -0.2px;
}

.agent-status {
  padding: 8px;
  background: rgba(0, 0, 0, 0.03);
  border-radius: 4px;
}

.message-badges {
  min-height: 32px;
}

.scrollable-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 100px;
  max-height: 200px;
  padding: 4px;
  margin: -4px;

  /* Custom scrollbar */
  &::-webkit-scrollbar {
    width: 6px;
  }

  &::-webkit-scrollbar-track {
    background: rgba(0, 0, 0, 0.05);
    border-radius: 3px;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(0, 0, 0, 0.2);
    border-radius: 3px;

    &:hover {
      background: rgba(0, 0, 0, 0.3);
    }
  }
}

.mission-content,
.waiting-content,
.working-content,
.error-content,
.silent-content {
  padding: 8px;
}

.mission-text {
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

.progress-section {
  padding: 8px 0;
}

.current-task {
  padding: 8px;
  background: rgba(33, 150, 243, 0.05);
  border-left: 3px solid #2196f3;
  border-radius: 4px;
}

.complete-content {
  .complete-text {
    font-size: 24px;
    font-weight: 700;
    color: #ffc107;
    text-transform: uppercase;
    letter-spacing: 1px;
  }
}

.orchestrator-tools {
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  padding-top: 12px;
}

/* Health Indicator Styles (Handover 0106) */
.health-indicator {
  display: flex;
  align-items: center;
}

.health-chip {
  font-size: 11px;
  height: 20px;
  cursor: help; /* Show it's interactive (tooltip) */
}

/* Subtle pulse animation for critical state */
.health-chip.pulse-warning {
  animation: pulse-warning 2s ease-in-out infinite;
}

@keyframes pulse-warning {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

/* Status-specific styling */
.status--complete {
  .agent-card__body {
    background: linear-gradient(to bottom, rgba(255, 193, 7, 0.05) 0%, transparent 100%);
  }
}

.status--silent {
  .agent-card__body {
    background: linear-gradient(to bottom, rgba(255, 152, 0, 0.05) 0%, transparent 100%);
  }
}

.status--blocked {
  .agent-card__body {
    background: linear-gradient(to bottom, rgba(255, 152, 0, 0.05) 0%, transparent 100%);
  }
}

/* Responsive */
@media (max-width: 1200px) {
  .agent-card {
    width: 240px;
  }
}

@media (max-width: 768px) {
  .agent-card {
    width: 100%;
    max-width: 280px;
  }
}

/* Accessibility */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}

/* Stack action buttons vertically */
.agent-card-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
</style>
