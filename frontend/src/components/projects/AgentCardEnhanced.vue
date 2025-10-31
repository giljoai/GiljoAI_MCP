<template>
  <v-card
    class="agent-card-enhanced"
    :class="[
      `agent-card--${agent.agent_type}`,
      `status--${agent.status}`,
      { 'priority-card': isPriorityState }
    ]"
    :style="cardStyles"
    role="article"
    :aria-label="cardAriaLabel"
  >
    <!-- Colored Header with Agent Type -->
    <div class="agent-card__header" :style="headerStyles">
      <div class="d-flex align-center justify-space-between">
        <span class="agent-header-text">{{ agentTypeLabel }}</span>
        <ChatHeadBadge
          :agent-type="agent.agent_type"
          :instance-number="instanceNumber"
          size="small"
        />
      </div>
    </div>

    <!-- Card Body -->
    <v-card-text class="agent-card__body pa-4">
      <!-- Agent ID -->
      <div class="agent-id mb-2">
        <span class="text-caption text-grey">Agent ID:</span>
        <span class="text-body-2 font-weight-medium ml-1">{{ truncatedAgentId }}</span>
      </div>

      <!-- Status Badge (Jobs Tab only) -->
      <div v-if="mode === 'jobs'" class="mb-3">
        <v-chip
          :color="statusConfig.color"
          :prepend-icon="statusConfig.icon"
          size="small"
          class="status-badge"
        >
          {{ statusConfig.label }}
        </v-chip>
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
        <v-chip
          v-if="sentCount > 0"
          color="grey-darken-2"
          size="x-small"
          prepend-icon="mdi-send"
        >
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
          <div v-if="instanceNumber > 1" class="instance-badge mt-2">
            Instance {{ instanceNumber }}
          </div>
        </div>

        <!-- Jobs Tab - Failure/Blocked State -->
        <div v-else-if="agent.status === 'failed' || agent.status === 'blocked'" class="error-content">
          <v-alert
            :type="agent.status === 'failed' ? 'error' : 'warning'"
            density="compact"
            variant="tonal"
            class="mb-2"
          >
            <div class="text-caption font-weight-bold mb-1">
              {{ agent.status === 'failed' ? 'Failure' : 'Blocked' }}
            </div>
            <div class="text-body-2">
              {{ agent.block_reason || 'No details available' }}
            </div>
          </v-alert>
        </div>
      </div>

      <!-- Orchestrator Special: Launch Prompt Icons -->
      <div v-if="isOrchestrator && mode === 'jobs'" class="orchestrator-tools mt-3">
        <LaunchPromptIcons />
      </div>
    </v-card-text>

    <!-- Action Button -->
    <v-card-actions class="pa-4 pt-0">
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
      <v-btn
        v-else-if="agent.status === 'waiting'"
        variant="elevated"
        color="yellow-darken-2"
        block
        @click="$emit('launch-agent', agent)"
      >
        <v-icon start>mdi-rocket-launch</v-icon>
        Launch Agent
      </v-btn>

      <!-- Jobs Tab: Working State - Details -->
      <v-btn
        v-else-if="agent.status === 'working'"
        variant="outlined"
        color="primary"
        block
        @click="$emit('view-details', agent)"
      >
        <v-icon start>mdi-information</v-icon>
        Details
      </v-btn>

      <!-- Jobs Tab: Failure/Blocked State - View Error -->
      <v-btn
        v-else-if="agent.status === 'failed' || agent.status === 'blocked'"
        variant="outlined"
        :color="agent.status === 'failed' ? 'error' : 'warning'"
        block
        @click="$emit('view-error', agent)"
      >
        <v-icon start>mdi-alert-circle</v-icon>
        View Error
      </v-btn>

      <!-- Orchestrator: Closeout Project (all agents complete) -->
      <v-btn
        v-else-if="isOrchestrator && showCloseoutButton"
        variant="elevated"
        color="success"
        block
        @click="$emit('closeout-project')"
      >
        <v-icon start>mdi-check-circle</v-icon>
        Closeout Project
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup>
import { computed } from 'vue'
import { getAgentColor, darkenColor, lightenColor } from '@/config/agentColors'
import ChatHeadBadge from './ChatHeadBadge.vue'
import LaunchPromptIcons from './LaunchPromptIcons.vue'

/**
 * AgentCardEnhanced Component
 *
 * Production-grade reusable agent card for Handover 0077.
 * Works across both Launch Tab and Jobs Tab with different states.
 *
 * Props:
 * - agent: Agent job object (required)
 * - mode: 'launch' | 'jobs' (default: 'jobs')
 * - instanceNumber: Instance number for multi-instance agents
 * - isOrchestrator: Special orchestrator features
 * - showCloseoutButton: Show closeout button when all agents complete
 *
 * Emits:
 * - edit-mission: (agent) => void
 * - launch-agent: (agent) => void
 * - view-details: (agent) => void
 * - view-error: (agent) => void
 * - closeout-project: () => void
 */

const props = defineProps({
  agent: {
    type: Object,
    required: true,
    validator: (value) => {
      return (
        value &&
        typeof value === 'object' &&
        'agent_type' in value &&
        'status' in value
      )
    }
  },
  mode: {
    type: String,
    default: 'jobs',
    validator: (value) => ['launch', 'jobs'].includes(value)
  },
  instanceNumber: {
    type: Number,
    default: 1,
    validator: (value) => value >= 1
  },
  isOrchestrator: {
    type: Boolean,
    default: false
  },
  showCloseoutButton: {
    type: Boolean,
    default: false
  }
})

defineEmits(['edit-mission', 'launch-agent', 'view-details', 'view-error', 'closeout-project'])

/**
 * Agent color configuration
 */
const agentColor = computed(() => getAgentColor(props.agent.agent_type))

const agentTypeLabel = computed(() => agentColor.value.name)

/**
 * Card styling with agent colors
 */
const cardStyles = computed(() => ({
  width: '280px',
  minHeight: '200px',
  maxHeight: '400px',
  border: `2px solid ${lightenColor(agentColor.value.hex, 20)}`,
  borderRadius: '8px',
  overflow: 'hidden',
  transition: 'all 0.3s ease'
}))

const headerStyles = computed(() => ({
  background: `linear-gradient(135deg, ${agentColor.value.hex} 0%, ${darkenColor(agentColor.value.hex, 10)} 100%)`,
  color: 'white',
  padding: '12px 16px'
}))

/**
 * Status configuration for Jobs Tab
 */
const STATUS_CONFIG = {
  waiting: {
    color: 'grey',
    icon: 'mdi-clock-outline',
    label: 'Waiting'
  },
  working: {
    color: 'primary',
    icon: 'mdi-cog',
    label: 'Working'
  },
  complete: {
    color: 'yellow-darken-2',
    icon: 'mdi-check-circle',
    label: 'Complete'
  },
  failed: {
    color: 'purple',
    icon: 'mdi-alert-circle',
    label: 'Failure'
  },
  blocked: {
    color: 'orange',
    icon: 'mdi-alert-octagon',
    label: 'Blocked'
  }
}

const statusConfig = computed(() => {
  return STATUS_CONFIG[props.agent.status] || STATUS_CONFIG.waiting
})

/**
 * Priority states (moved to top)
 */
const isPriorityState = computed(() => {
  return props.agent.status === 'failed' || props.agent.status === 'blocked'
})

/**
 * Message count calculations
 */
const hasMessages = computed(() => {
  return props.agent.messages && Array.isArray(props.agent.messages) && props.agent.messages.length > 0
})

const unreadCount = computed(() => {
  if (!hasMessages.value) return 0
  return props.agent.messages.filter(m => m.status === 'pending').length
})

const acknowledgedCount = computed(() => {
  if (!hasMessages.value) return 0
  return props.agent.messages.filter(m => m.status === 'acknowledged').length
})

const sentCount = computed(() => {
  if (!hasMessages.value) return 0
  return props.agent.messages.filter(m => m.from === 'developer').length
})

/**
 * Text truncation helpers
 */
const truncatedAgentId = computed(() => {
  const id = props.agent.job_id || props.agent.agent_id || 'Unknown'
  if (id.length <= 12) return id
  return `${id.substring(0, 12)}...`
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
  const type = agentTypeLabel.value
  const status = statusConfig.value.label
  return `${type} agent - ${status}`
})
</script>

<style scoped lang="scss">
@import '@/styles/agent-colors.scss';

.agent-card-enhanced {
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
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
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

.status-badge {
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
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
.error-content {
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

  .instance-badge {
    font-size: 14px;
    font-weight: 600;
    color: rgba(0, 0, 0, 0.6);
  }
}

.orchestrator-tools {
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  padding-top: 12px;
}

/* Status-specific styling */
.status--complete {
  .agent-card__body {
    background: linear-gradient(to bottom, rgba(255, 193, 7, 0.05) 0%, transparent 100%);
  }
}

.status--failed {
  .agent-card__body {
    background: linear-gradient(to bottom, rgba(156, 39, 176, 0.05) 0%, transparent 100%);
  }
}

.status--blocked {
  .agent-card__body {
    background: linear-gradient(to bottom, rgba(255, 152, 0, 0.05) 0%, transparent 100%);
  }
}

/* Responsive */
@media (max-width: 1200px) {
  .agent-card-enhanced {
    width: 240px !important;
  }
}

@media (max-width: 768px) {
  .agent-card-enhanced {
    width: 100% !important;
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
</style>
