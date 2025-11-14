<template>
  <v-card
    class="agent-status-card"
    :class="[
      `status--${agent.status}`,
      { 'is-working': agent.status === 'working', 'is-cancelling': agent.status === 'cancelling' }
    ]"
    :style="cardStyles"
    elevation="2"
    hover
    @click="$emit('click', agent)"
    role="article"
    :aria-label="`${agent.agent_type} agent: ${statusConfig.label}`"
    tabindex="0"
    @keydown.enter="$emit('click', agent)"
  >
    <!-- Colored Header -->
    <div class="agent-status-card__header" :style="headerStyles">
      <span class="agent-type-label">{{ agentTypeLabel }}</span>
      <v-chip
        :color="statusConfig.color"
        size="small"
        variant="flat"
        class="status-chip"
      >
        <v-icon v-if="statusConfig.icon" left size="small">{{ statusConfig.icon }}</v-icon>
        {{ statusConfig.label }}
      </v-chip>
    </div>

    <!-- Card Content -->
    <v-card-text class="pa-4">
      <!-- Agent ID -->
      <div class="text-caption text-medium-emphasis mb-3">
        Agent ID: <span class="font-weight-medium">{{ formatAgentId(agent.job_id) }}</span>
      </div>

      <!-- Progress Bar (working status only) -->
      <div v-if="agent.status === 'working' || agent.status === 'cancelling'" class="mb-3">
        <div class="d-flex align-center justify-space-between mb-1">
          <span class="text-caption text-medium-emphasis">Progress</span>
          <span class="text-caption font-weight-bold">{{ agent.progress || 0 }}%</span>
        </div>
        <v-progress-linear
          :model-value="agent.progress || 0"
          :color="agent.status === 'cancelling' ? 'warning' : 'primary'"
          height="6"
          rounded
          :class="{ 'pulse-animation': agent.status === 'working' }"
        />
      </div>

      <!-- Current Task (working status only) -->
      <div v-if="agent.status === 'working' && agent.current_task" class="mb-3">
        <div class="text-caption text-medium-emphasis mb-1">Current Task</div>
        <div class="text-body-2">{{ agent.current_task }}</div>
      </div>

      <!-- Last Heartbeat -->
      <div v-if="agent.last_heartbeat" class="mb-3">
        <div class="text-caption text-medium-emphasis mb-1">Last Update</div>
        <div class="text-body-2 d-flex align-center">
          <v-icon size="small" class="mr-1" :color="heartbeatColor">mdi-heart-pulse</v-icon>
          {{ formatLastHeartbeat(agent.last_heartbeat) }}
        </div>
      </div>

      <!-- Message Counts -->
      <div v-if="hasMessages" class="message-counts mb-3">
        <div class="text-caption text-medium-emphasis mb-2">Messages</div>
        <div class="d-flex flex-wrap gap-2">
          <v-chip
            v-if="agent.messages_sent > 0"
            size="x-small"
            color="grey-darken-2"
            prepend-icon="mdi-send"
          >
            {{ agent.messages_sent }} Sent
          </v-chip>
          <v-chip
            v-if="agent.messages_received > 0"
            size="x-small"
            color="info"
            prepend-icon="mdi-email-receive"
          >
            {{ agent.messages_received }} Received
          </v-chip>
        </div>
      </div>

      <!-- Failure Reason (failed status only) -->
      <v-alert
        v-if="agent.status === 'failed' && agent.failure_reason"
        type="error"
        variant="tonal"
        density="compact"
        class="mb-3"
      >
        <div class="text-caption">{{ agent.failure_reason }}</div>
      </v-alert>

      <!-- Completion Message (completed status only) -->
      <div v-if="agent.status === 'completed'" class="text-center py-2">
        <v-icon color="success" size="48">mdi-check-circle</v-icon>
        <div class="text-body-2 mt-2">Task completed successfully</div>
      </div>

      <!-- Decommissioned Message -->
      <div v-if="agent.status === 'decommissioned'" class="text-center py-2">
        <v-icon color="grey" size="48">mdi-pause-circle</v-icon>
        <div class="text-body-2 mt-2">Agent decommissioned</div>
      </div>
    </v-card-text>

    <!-- Quick Actions -->
    <v-card-actions v-if="showActions">
      <v-btn
        v-if="canCancel"
        color="warning"
        variant="outlined"
        size="small"
        @click.stop="$emit('cancel', agent)"
      >
        <v-icon left size="small">mdi-cancel</v-icon>
        Cancel
      </v-btn>
      <v-spacer />
      <v-btn
        color="primary"
        variant="text"
        size="small"
        @click.stop="$emit('view-messages', agent)"
      >
        <v-icon left size="small">mdi-message-text</v-icon>
        Messages
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup>
import { computed } from 'vue'
import { getAgentColor, darkenColor } from '@/config/agentColors'
import { formatDistanceToNow } from 'date-fns'

// Props
const props = defineProps({
  agent: {
    type: Object,
    required: true
  }
})

// Emits
const emit = defineEmits(['click', 'cancel', 'view-messages'])

// Status configuration matching backend 7-state model (Handover 0113)
const STATUS_CONFIG = {
  waiting: {
    label: 'Waiting',
    color: 'indigo',
    icon: 'mdi-clock-outline'
  },
  working: {
    label: 'Working',
    color: 'cyan',
    icon: 'mdi-cog'
  },
  completed: {
    label: 'Completed',
    color: 'success',
    icon: 'mdi-check-circle'
  },
  failed: {
    label: 'Failed',
    color: 'error',
    icon: 'mdi-alert-circle'
  },
  decommissioned: {
    label: 'Decommissioned',
    color: 'grey',
    icon: 'mdi-pause-circle'
  },
  cancelled: {
    label: 'Cancelled',
    color: 'orange',
    icon: 'mdi-cancel'
  },
  cancelling: {
    label: 'Cancelling...',
    color: 'warning',
    icon: 'mdi-timer-sand'
  }
}

// Computed properties
const agentColor = computed(() => getAgentColor(props.agent.agent_type))

const agentTypeLabel = computed(() => agentColor.value.name || 'Agent')

const statusConfig = computed(() => STATUS_CONFIG[props.agent.status] || STATUS_CONFIG.waiting)

const cardStyles = computed(() => ({
  borderLeft: `4px solid ${agentColor.value.hex}`,
  transition: 'all 0.3s ease'
}))

const headerStyles = computed(() => ({
  backgroundColor: agentColor.value.hex,
  color: '#FFFFFF',
  padding: '12px 16px',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  borderTopLeftRadius: '4px',
  borderTopRightRadius: '4px'
}))

const hasMessages = computed(() => {
  return (props.agent.messages_sent > 0) || (props.agent.messages_received > 0)
})

const canCancel = computed(() => {
  return props.agent.status === 'working' || props.agent.status === 'waiting'
})

const showActions = computed(() => {
  return props.agent.status !== 'decommissioned'
})

// Heartbeat color based on recency
const heartbeatColor = computed(() => {
  if (!props.agent.last_heartbeat) return 'grey'

  const lastUpdate = new Date(props.agent.last_heartbeat)
  const now = new Date()
  const minutesAgo = (now - lastUpdate) / 1000 / 60

  if (minutesAgo < 2) return 'success'
  if (minutesAgo < 5) return 'warning'
  return 'error'
})

// Utility functions
function formatAgentId(jobId) {
  if (!jobId) return 'Unknown'
  return jobId.substring(0, 8)
}

function formatLastHeartbeat(timestamp) {
  if (!timestamp) return 'Never'
  try {
    return formatDistanceToNow(new Date(timestamp), { addSuffix: true })
  } catch (error) {
    return 'Invalid date'
  }
}
</script>

<style scoped>
.agent-status-card {
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.agent-status-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
}

.agent-status-card:focus {
  outline: 2px solid var(--v-primary-base);
  outline-offset: 2px;
}

.agent-status-card__header {
  font-weight: 500;
  font-size: 14px;
  letter-spacing: 0.5px;
}

.agent-type-label {
  text-transform: uppercase;
}

.status-chip {
  font-weight: 600;
  text-transform: uppercase;
  font-size: 11px;
}

/* Pulsing animation for working agents */
.is-working .agent-status-card__header,
.is-cancelling .agent-status-card__header {
  animation: pulse-header 2s ease-in-out infinite;
}

@keyframes pulse-header {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.85;
  }
}

.pulse-animation {
  animation: pulse-progress 1.5s ease-in-out infinite;
}

@keyframes pulse-progress {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

.message-counts .v-chip {
  font-size: 11px;
}

/* Dark mode support */
.v-theme--dark .agent-status-card {
  background-color: rgba(255, 255, 255, 0.05);
}
</style>
