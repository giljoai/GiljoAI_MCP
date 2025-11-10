<template>
  <v-card
    class="agent-card responsive"
    :class="[`status-${agent.status}`]"
    role="article"
    :aria-label="`${agent.name} - ${statusConfig.label}`"
    :style="cardStyles"
  >
    <!-- Status border indicator -->
    <div class="status-border" :style="{ backgroundColor: statusConfig.borderColor }"></div>

    <!-- Card header -->
    <v-card-title class="d-flex align-center justify-space-between pa-3">
      <div class="d-flex align-center flex-grow-1">
        <span class="agent-name text-subtitle-1 font-weight-bold">{{ agent.name }}</span>
      </div>

      <!-- Tool badge -->
      <v-chip
        v-if="agent.tool_type"
        class="tool-badge ml-2"
        :color="toolBadgeColor"
        size="small"
        label
      >
        {{ agent.tool_type }}
      </v-chip>
    </v-card-title>

    <v-divider />

    <!-- Card content -->
    <v-card-text class="pa-3">
      <!-- Status badge with icon -->
      <div class="mb-3">
        <v-chip
          class="status-badge"
          :color="statusConfig.color"
          size="small"
        >
          <v-icon :icon="statusConfig.icon" size="small" start />
          {{ statusConfig.label }}
        </v-chip>
      </div>

      <!-- Job description (truncated to 120 chars) -->
      <div class="job-description text-body-2 text-grey-darken-1 mb-3">
        {{ truncatedDescription }}
      </div>

      <!-- Progress bar (only for working status) -->
      <div v-if="agent.status === 'working'" class="mb-3">
        <div class="progress-bar">
          <v-progress-linear
            :model-value="agent.progress || 0"
            :color="statusConfig.color"
            height="8"
            rounded
          />
          <div class="text-caption text-center mt-1">{{ agent.progress || 0 }}%</div>
        </div>

        <!-- Current task -->
        <div v-if="agent.current_task" class="current-task text-caption text-grey mt-2">
          <v-icon icon="mdi-arrow-right" size="x-small" />
          {{ agent.current_task }}
        </div>
      </div>

      <!-- Block reason alert (only for blocked status) -->
      <v-alert
        v-if="agent.status === 'blocked' && agent.block_reason"
        class="block-reason mb-3"
        type="warning"
        density="compact"
        variant="tonal"
      >
        {{ agent.block_reason }}
      </v-alert>

      <!-- Message toggle button -->
      <v-btn
        v-if="agent.messages && agent.messages.length > 0"
        class="message-toggle"
        variant="text"
        size="small"
        block
        @click="toggleMessages"
      >
        <v-badge
          v-if="unreadCount > 0"
          :content="unreadCount"
          color="error"
          inline
        >
          <v-icon icon="mdi-message" size="small" />
        </v-badge>
        <v-icon v-else icon="mdi-message" size="small" />
        <span class="ml-2">Messages ({{ agent.messages.length }})</span>
        <v-icon
          :icon="isExpanded ? 'mdi-chevron-up' : 'mdi-chevron-down'"
          size="small"
          class="ml-auto"
        />
      </v-btn>

      <!-- Expanded messages section -->
      <div v-if="isExpanded" class="expanded-messages mt-2">
        <v-card variant="outlined">
          <v-card-text class="pa-2">
            <div
              v-for="msg in agent.messages"
              :key="msg.id"
              class="text-caption mb-1"
              :class="{ 'font-weight-bold': !msg.read }"
            >
              {{ msg.content }}
            </div>
          </v-card-text>
        </v-card>
      </div>
    </v-card-text>

    <!-- Card actions -->
    <v-card-actions class="pa-3 pt-0">
      <v-btn
        class="copy-prompt-btn"
        color="primary"
        variant="outlined"
        size="small"
        block
        :aria-label="`Copy prompt for ${agent.name}`"
        @click="handleCopyPrompt"
      >
        <v-icon icon="mdi-content-copy" size="small" start />
        Copy Prompt
      </v-btn>
    </v-card-actions>

    <!-- Copy success snackbar -->
    <v-snackbar
      v-model="showCopySuccess"
      :timeout="2000"
      location="top"
      color="success"
    >
      <div role="status">Copied to clipboard!</div>
    </v-snackbar>

    <!-- Status change announcement for screen readers -->
    <div v-if="statusChanged" role="status" class="sr-only" aria-live="polite">
      Status changed to {{ statusConfig.label }}
    </div>
  </v-card>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useClipboard } from '@/composables/useClipboard'
import api from '@/services/api'

const props = defineProps({
  agent: {
    type: Object,
    required: true
  },
  unreadCount: {
    type: Number,
    default: 0
  },
  isExpanded: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['copy-prompt', 'toggle-messages'])

// Status configuration matching test specifications
const STATUS_CONFIG = {
  waiting: {
    color: 'grey',
    icon: 'mdi-clock-outline',
    label: 'Waiting',
    borderColor: '#9e9e9e'
  },
  preparing: {
    color: 'light-blue',
    icon: 'mdi-loading',
    label: 'Preparing',
    borderColor: '#03a9f4'
  },
  working: {
    color: 'primary',
    icon: 'mdi-cog',
    label: 'Working',
    borderColor: '#2196f3'
  },
  review: {
    color: 'purple',
    icon: 'mdi-eye',
    label: 'Under Review',
    borderColor: '#9c27b0'
  },
  complete: {
    color: 'success',
    icon: 'mdi-check-circle',
    label: 'Complete',
    borderColor: '#4caf50'
  },
  failed: {
    color: 'error',
    icon: 'mdi-alert-circle',
    label: 'Failed',
    borderColor: '#f44336'
  },
  blocked: {
    color: 'deep-orange-darken-4',
    icon: 'mdi-block-helper',
    label: 'Blocked',
    borderColor: '#bf360c'
  }
}

// Tool badge colors
const TOOL_BADGE_COLORS = {
  'claude-code': 'primary',
  'codex': 'secondary',
  'gemini': 'accent',
  'universal': 'grey'
}

// Composables
const { copy, copied } = useClipboard()

// Reactive state
const showCopySuccess = ref(false)
const statusChanged = ref(false)

// Computed properties
const statusConfig = computed(() => {
  return STATUS_CONFIG[props.agent.status] || STATUS_CONFIG.waiting
})

const toolBadgeColor = computed(() => {
  return TOOL_BADGE_COLORS[props.agent.tool_type] || 'grey'
})

const truncatedDescription = computed(() => {
  const desc = props.agent.job_description || ''
  if (desc.length <= 120) return desc
  return desc.substring(0, 120) + '...'
})

const cardStyles = computed(() => {
  return {
    width: '280px',
    minHeight: '360px',
    position: 'relative'
  }
})

// Watch for status changes
watch(() => props.agent.status, (newStatus, oldStatus) => {
  if (oldStatus && newStatus !== oldStatus) {
    statusChanged.value = true
    setTimeout(() => {
      statusChanged.value = false
    }, 3000)
  }
})

// Methods
// MIGRATION NOTE (Handover 0119): Updated to use /api/v1/prompts instead of /api/prompts
const handleCopyPrompt = async () => {
  emit('copy-prompt', props.agent.id)

  try {
    // Fetch prompt from API
    const response = await api.get(`/api/v1/prompts/agent/${props.agent.id}`)
    const promptText = response.data.prompt || 'Prompt not available'

    // Copy to clipboard
    await copy(promptText)
    showCopySuccess.value = true
  } catch (err) {
    console.error('[AgentCard] Failed to copy prompt:', err)
  }
}

const toggleMessages = () => {
  emit('toggle-messages', props.agent.id)
}
</script>

<style scoped>
.agent-card {
  display: flex;
  flex-direction: column;
  position: relative;
  transition: all 0.3s ease;
}

.agent-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.status-border {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 8px;
  border-top-left-radius: inherit;
  border-bottom-left-radius: inherit;
}

.agent-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.job-description {
  min-height: 3em;
  line-height: 1.5;
}

.current-task {
  display: flex;
  align-items: center;
  gap: 4px;
}

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

/* Responsive adjustments */
@media (max-width: 600px) {
  .agent-card {
    width: 100% !important;
  }
}

@media (min-width: 601px) and (max-width: 959px) {
  .agent-card {
    width: 100% !important;
    min-width: 240px;
  }
}
</style>
