<template>
  <v-card
    class="job-card pa-4"
    elevation="1"
    :ripple="true"
    @click="showJobDetails"
  >
    <!-- Header: Agent Type + Name -->
    <div class="d-flex align-center justify-space-between mb-3">
      <div class="d-flex align-center gap-2 flex-grow-1 min-width-0">
        <!-- Agent Type Icon -->
        <v-icon
          :color="agentTypeColor"
          size="24"
          :title="`Agent type: ${job.agent_type}`"
        >
          {{ agentTypeIcon }}
        </v-icon>

        <!-- Agent Name -->
        <div class="flex-grow-1 min-width-0">
          <p class="text-subtitle-2 font-weight-bold text-truncate">
            {{ job.agent_name || job.agent_id }}
          </p>
          <p class="text-caption text-grey text-truncate">
            {{ job.agent_type }}
          </p>
        </div>
      </div>

      <!-- Mode Indicator Badge -->
      <v-chip
        v-if="job.mode"
        size="x-small"
        :color="modeBadgeColor"
        text-color="white"
        label
        class="flex-shrink-0"
      >
        {{ job.mode }}
      </v-chip>
    </div>

    <v-divider class="my-3" />

    <!-- Mission Preview (Truncated) -->
    <div class="mission-preview mb-3">
      <p class="text-body-2 line-clamp-3 mb-0">
        {{ missionPreview }}
      </p>
    </div>

    <!-- Progress Bar (Active Jobs Only) -->
    <div v-if="isActive && job.progress !== undefined" class="progress-section mb-3">
      <div class="d-flex align-center justify-space-between mb-1">
        <p class="text-caption text-grey">Progress</p>
        <p class="text-caption font-weight-bold">{{ job.progress }}%</p>
      </div>
      <v-progress-linear
        :model-value="job.progress"
        color="primary"
        height="4"
        rounded
      />
    </div>

    <!-- Timestamp -->
    <p class="text-caption text-grey mb-3">
      <v-icon size="x-small" class="mr-1">mdi-clock</v-icon>
      {{ relativeTime }}
    </p>

    <v-divider class="my-3" />

    <!-- Message Count Badges (THREE separate badges) -->
    <div class="message-counts d-flex flex-wrap gap-2">
      <!-- Unread Messages (Red badge) -->
      <v-chip
        v-if="unreadCount > 0"
        size="x-small"
        color="error"
        text-color="white"
        @click.stop="openMessages"
        class="clickable-chip"
      >
        <v-icon start size="x-small">mdi-message-badge</v-icon>
        {{ unreadCount }} Unread
      </v-chip>

      <!-- Acknowledged Messages (Green checkmark) -->
      <v-chip
        v-if="acknowledgedCount > 0"
        size="x-small"
        color="success"
        text-color="white"
      >
        <v-icon start size="x-small">mdi-check-all</v-icon>
        {{ acknowledgedCount }} Read
      </v-chip>

      <!-- Sent Messages (Grey) -->
      <v-chip
        v-if="sentCount > 0"
        size="x-small"
        color="grey-darken-2"
        text-color="white"
      >
        <v-icon start size="x-small">mdi-send</v-icon>
        {{ sentCount }} Sent
      </v-chip>

      <!-- Empty message state -->
      <p v-if="totalMessageCount === 0" class="text-caption text-grey mb-0">
        No messages yet
      </p>
    </div>

    <!-- Status Badge (Subtle) -->
    <div class="mt-3 pt-3 border-top">
      <v-chip
        :color="statusBadgeColor"
        :text-color="statusBadgeTextColor"
        size="x-small"
        label
        class="w-100 justify-center"
      >
        <v-icon start size="x-small">{{ statusBadgeIcon }}</v-icon>
        {{ formatStatus(columnStatus) }}
      </v-chip>
    </div>
  </v-card>
</template>

<script setup>
import { computed } from 'vue'
import { formatDistanceToNow } from 'date-fns'

/**
 * JobCard Component
 *
 * Displays a job card showing agent information, mission preview, and message counts.
 * Features three separate message count badges: unread, acknowledged, and sent.
 *
 * Props:
 * - job: Agent job object with agent_id, agent_name, agent_type, mission, etc.
 * - columnStatus: Current column status (pending|active|completed|blocked)
 *
 * Emits:
 * - view-details: Open full job details dialog
 * - open-messages: Open message thread panel for this job
 */

const props = defineProps({
  job: {
    type: Object,
    required: true,
  },
  columnStatus: {
    type: String,
    required: true,
  },
})

const emit = defineEmits(['view-details', 'open-messages'])

/**
 * Agent type icon and color mapping
 */
const agentTypeMap = {
  orchestrator: { icon: 'mdi-brain', color: 'purple' },
  analyzer: { icon: 'mdi-magnify', color: 'blue' },
  implementer: { icon: 'mdi-code-braces', color: 'green' },
  tester: { icon: 'mdi-test-tube', color: 'orange' },
  'ux-designer': { icon: 'mdi-palette', color: 'pink' },
  backend: { icon: 'mdi-server', color: 'teal' },
  frontend: { icon: 'mdi-monitor', color: 'indigo' },
}

const agentTypeIcon = computed(() => {
  const typeKey = props.job.agent_type?.toLowerCase() || 'implementer'
  return agentTypeMap[typeKey]?.icon || 'mdi-robot'
})

const agentTypeColor = computed(() => {
  const typeKey = props.job.agent_type?.toLowerCase() || 'implementer'
  return agentTypeMap[typeKey]?.color || 'grey'
})

/**
 * Mode indicator color mapping
 */
const modeColorMap = {
  claude: 'deep-purple',
  codex: 'blue',
  gemini: 'light-blue',
}

const modeBadgeColor = computed(() => {
  return modeColorMap[props.job.mode?.toLowerCase()] || 'grey'
})

/**
 * Mission preview (truncate to 120 chars)
 */
const missionPreview = computed(() => {
  const mission = props.job.mission || 'No mission description'
  return mission.length > 120 ? `${mission.substring(0, 120)}...` : mission
})

/**
 * Check if job is active
 */
const isActive = computed(() => {
  return props.columnStatus === 'active'
})

/**
 * Relative time display (e.g., "2 hours ago")
 */
const relativeTime = computed(() => {
  if (!props.job.created_at) return 'Unknown'

  try {
    return formatDistanceToNow(new Date(props.job.created_at), { addSuffix: true })
  } catch {
    return 'Unknown'
  }
})

/**
 * Message count calculations
 *
 * From MCPAgentJob.messages JSONB array:
 * - unread: status === 'pending'
 * - acknowledged: status === 'acknowledged'
 * - sent: from === 'developer'
 */
const unreadCount = computed(() => {
  if (!props.job.messages || !Array.isArray(props.job.messages)) return 0
  return props.job.messages.filter((m) => m.status === 'pending').length
})

const acknowledgedCount = computed(() => {
  if (!props.job.messages || !Array.isArray(props.job.messages)) return 0
  return props.job.messages.filter((m) => m.status === 'acknowledged').length
})

const sentCount = computed(() => {
  if (!props.job.messages || !Array.isArray(props.job.messages)) return 0
  return props.job.messages.filter((m) => m.from === 'developer').length
})

const totalMessageCount = computed(() => {
  return unreadCount.value + acknowledgedCount.value + sentCount.value
})

/**
 * Status badge styling based on column status
 */
const statusBadgeConfig = computed(() => {
  const configs = {
    pending: { color: 'grey', textColor: 'white', icon: 'mdi-clock-outline' },
    active: { color: 'primary', textColor: 'white', icon: 'mdi-play-circle' },
    completed: { color: 'success', textColor: 'white', icon: 'mdi-check-circle' },
    blocked: { color: 'error', textColor: 'white', icon: 'mdi-alert-circle' },
  }
  return configs[props.columnStatus] || configs.pending
})

const statusBadgeColor = computed(() => statusBadgeConfig.value.color)
const statusBadgeTextColor = computed(() => statusBadgeConfig.value.textColor)
const statusBadgeIcon = computed(() => statusBadgeConfig.value.icon)

/**
 * Format status text (capitalize first letter)
 */
function formatStatus(status) {
  return status.charAt(0).toUpperCase() + status.slice(1)
}

/**
 * Show full job details dialog
 */
function showJobDetails() {
  emit('view-details')
}

/**
 * Open message thread panel
 */
function openMessages() {
  emit('open-messages')
}
</script>

<style scoped>
.job-card {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
  border: 1px solid rgba(0, 0, 0, 0.06);
}

.job-card:hover {
  elevation: 4;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.job-card:active {
  transform: translateY(0);
}

/* Agent name and type section */
.min-width-0 {
  min-width: 0;
}

/* Mission preview with line clamping */
.mission-preview {
  font-size: 0.875rem;
  line-height: 1.5;
  color: rgba(0, 0, 0, 0.7);
}

.line-clamp-3 {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Progress section */
.progress-section {
  padding: 0.5rem 0;
}

/* Message count chips */
.message-counts {
  align-items: flex-start;
}

.clickable-chip {
  cursor: pointer;
  transition: all 0.2s;
}

.clickable-chip:hover {
  transform: scale(1.05);
}

/* Border styling */
.border-top {
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}

/* Status badge full width */
:deep(.v-chip) {
  justify-content: center;
  width: 100%;
}

/* Responsive */
@media (max-width: 600px) {
  .job-card {
    padding: 0.75rem;
  }

  .mission-preview {
    font-size: 0.8125rem;
  }
}
</style>
