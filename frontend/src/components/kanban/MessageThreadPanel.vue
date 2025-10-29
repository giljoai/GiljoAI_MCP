<template>
  <v-navigation-drawer
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    location="right"
    temporary
    width="400"
    class="message-thread-panel"
  >
    <!-- Header -->
    <v-card class="panel-header" elevation="0">
      <v-card-title class="d-flex align-center justify-space-between">
        <div>
          <p class="text-h6 mb-1">Messages</p>
          <p v-if="job" class="text-caption text-grey">
            {{ job.agent_name || job.agent_id }}
          </p>
        </div>
        <v-btn
          icon
          size="small"
          variant="text"
          @click="$emit('update:modelValue', false)"
          aria-label="Close message panel"
        >
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>
    </v-card>

    <v-divider />

    <!-- Mission Display (Context) -->
    <v-card v-if="job" variant="tonal" class="ma-3 mission-card">
      <v-card-title class="text-subtitle-2">Mission</v-card-title>
      <v-card-text class="text-body-2 pa-3">
        {{ job.mission || 'No mission assigned' }}
      </v-card-text>
    </v-card>

    <!-- Messages Container -->
    <div class="messages-container flex-grow-1">
      <!-- Loading State -->
      <div v-if="loadingMessages" class="d-flex align-center justify-center" style="height: 100px">
        <v-progress-circular indeterminate color="primary" size="32" />
      </div>

      <!-- Messages List -->
      <div v-else-if="messages.length > 0" class="messages-list">
        <div
          v-for="(message, index) in messages"
          :key="`${message.id}-${index}`"
          class="message-item"
          :class="{ 'message-developer': isDeveloperMessage(message), 'message-agent': !isDeveloperMessage(message) }"
        >
          <div class="message-bubble">
            <!-- Sender info -->
            <p class="message-sender text-caption font-weight-bold mb-1">
              {{ message.from || 'Unknown' }}
            </p>

            <!-- Message content -->
            <p class="message-content text-body-2 mb-1">
              {{ message.content || message.text }}
            </p>

            <!-- Message status -->
            <div class="d-flex align-center gap-1">
              <p class="text-caption text-grey mb-0">
                {{ formatTime(message.created_at || message.timestamp) }}
              </p>

              <!-- Status icon -->
              <v-icon
                v-if="isDeveloperMessage(message)"
                :color="getStatusColor(message.status)"
                size="x-small"
                :title="`Status: ${message.status}`"
              >
                {{ getStatusIcon(message.status) }}
              </v-icon>
            </div>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-else class="d-flex align-center justify-center" style="height: 100px">
        <div class="text-center">
          <v-icon color="grey-lighten-1" size="40" class="mb-2 d-block">
            mdi-message-outline
          </v-icon>
          <p class="text-body-2 text-grey">No messages yet</p>
        </div>
      </div>
    </div>

    <v-divider />

    <!-- Message Compose Section -->
    <div class="compose-section pa-3">
      <!-- Warning for blocked/pending jobs -->
      <v-alert
        v-if="job && ['blocked', 'pending'].includes(columnStatus)"
        type="warning"
        variant="tonal"
        size="small"
        class="mb-3"
        density="compact"
      >
        <v-icon start size="x-small">mdi-alert-circle</v-icon>
        Job is {{ columnStatus }}. Agent may not respond until activated.
      </v-alert>

      <!-- Message input -->
      <v-textarea
        v-model="newMessage"
        placeholder="Send a message..."
        variant="outlined"
        density="compact"
        rows="3"
        hide-details
        @keydown.ctrl.enter="sendMessage"
        @keydown.meta.enter="sendMessage"
      />

      <!-- Send button -->
      <v-btn
        block
        color="primary"
        class="mt-2"
        @click="sendMessage"
        :disabled="!newMessage.trim() || sending"
        :loading="sending"
        size="small"
      >
        <v-icon start size="small">mdi-send</v-icon>
        Send Message
      </v-btn>

      <!-- Keyboard hint -->
      <p class="text-caption text-grey text-center mt-2 mb-0">
        Ctrl+Enter to send
      </p>
    </div>
  </v-navigation-drawer>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { api } from '@/services/api'
import { formatDistanceToNow, format } from 'date-fns'

/**
 * MessageThreadPanel Component
 *
 * Slack-style message thread panel for developer-agent communication.
 * Shows job mission at top, messages in chronological order, and compose area at bottom.
 *
 * Features:
 * - Display mission context at top
 * - Messages in chronological order
 * - Three message statuses: pending, acknowledged, sent
 * - Developer message indicators
 * - Agent response indicators
 * - Message composition with Ctrl+Enter support
 * - Loading states and error handling
 *
 * Props:
 * - modelValue: Whether panel is open
 * - job: Agent job object
 * - columnStatus: Job status (pending|active|completed|blocked)
 *
 * Emits:
 * - update:modelValue: Toggle panel open/closed
 * - message-sent: New message was sent
 */

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  job: {
    type: Object,
    default: null,
  },
  columnStatus: {
    type: String,
    default: 'pending',
  },
})

const emit = defineEmits(['update:modelValue', 'message-sent'])

// State
const messages = ref([])
const newMessage = ref('')
const loadingMessages = ref(false)
const sending = ref(false)

/**
 * Fetch messages for the current job
 */
async function fetchMessages() {
  if (!props.job?.job_id) {
    messages.value = []
    return
  }

  loadingMessages.value = true

  try {
    const response = await api.agentJobs.getMessageThread(props.job.job_id)
    messages.value = response.data.messages || []

    // Auto-scroll to bottom after loading
    setTimeout(() => {
      const container = document.querySelector('.messages-list')
      if (container) {
        container.scrollTop = container.scrollHeight
      }
    }, 50)

    console.log('[MessageThreadPanel] Messages loaded:', messages.value.length)
  } catch (error) {
    console.error('[MessageThreadPanel] Error fetching messages:', error)
    messages.value = []
  } finally {
    loadingMessages.value = false
  }
}

/**
 * Send message to agent
 */
async function sendMessage() {
  if (!newMessage.value.trim() || !props.job?.job_id) {
    return
  }

  const content = newMessage.value.trim()
  newMessage.value = ''
  sending.value = true

  try {
    const response = await api.agentJobs.sendMessage(props.job.job_id, {
      content,
      to: props.job.agent_id,
    })

    // Add message to local list immediately
    const sentMessage = {
      id: response.data.message_id,
      from: 'developer',
      content,
      status: 'sent',
      created_at: new Date().toISOString(),
    }

    messages.value.push(sentMessage)

    // Emit event
    emit('message-sent', sentMessage)

    // Auto-scroll to bottom
    setTimeout(() => {
      const container = document.querySelector('.messages-list')
      if (container) {
        container.scrollTop = container.scrollHeight
      }
    }, 50)

    console.log('[MessageThreadPanel] Message sent:', content.substring(0, 50))
  } catch (error) {
    console.error('[MessageThreadPanel] Error sending message:', error)
    // Restore message in input if failed
    newMessage.value = content
  } finally {
    sending.value = false
  }
}

/**
 * Check if message is from developer
 */
function isDeveloperMessage(message) {
  return message.from === 'developer' || message.from_type === 'developer'
}

/**
 * Get status icon for message
 */
function getStatusIcon(status) {
  const icons = {
    pending: 'mdi-clock-outline',
    acknowledged: 'mdi-check',
    sent: 'mdi-check-all',
  }
  return icons[status] || 'mdi-help-circle'
}

/**
 * Get status color
 */
function getStatusColor(status) {
  const colors = {
    pending: 'grey',
    acknowledged: 'orange',
    sent: 'success',
  }
  return colors[status] || 'grey'
}

/**
 * Format message timestamp
 */
function formatTime(timestamp) {
  if (!timestamp) return 'Unknown'

  try {
    const date = new Date(timestamp)
    const now = new Date()
    const diffHours = (now - date) / (1000 * 60 * 60)

    // Show relative time if less than 24 hours
    if (diffHours < 24) {
      return formatDistanceToNow(date, { addSuffix: true })
    }

    // Otherwise show date and time
    return format(date, 'MMM d, HH:mm')
  } catch {
    return 'Unknown'
  }
}

/**
 * Watch job changes and fetch messages
 */
watch(
  () => props.job?.job_id,
  () => {
    if (props.modelValue) {
      fetchMessages()
    }
  },
)

/**
 * Watch panel open state
 */
watch(
  () => props.modelValue,
  (isOpen) => {
    if (isOpen && props.job?.job_id) {
      fetchMessages()
    }
  },
)

/**
 * Lifecycle
 */
onMounted(() => {
  if (props.modelValue && props.job?.job_id) {
    fetchMessages()
  }
})
</script>

<style scoped>
.message-thread-panel {
  display: flex;
  flex-direction: column;
}

.panel-header {
  position: sticky;
  top: 0;
  z-index: 10;
  background-color: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(4px);
}

.mission-card {
  margin-left: 0.75rem;
  margin-right: 0.75rem;
  margin-top: 0.75rem;
}

.messages-container {
  overflow-y: auto;
  flex: 1;
  padding: 0.75rem 0;
}

.messages-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0 0.75rem;
}

/* Message items */
.message-item {
  display: flex;
  margin-bottom: 0.75rem;
  animation: messageSlide 0.2s ease-out;
}

@keyframes messageSlide {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-developer {
  justify-content: flex-end;
}

.message-agent {
  justify-content: flex-start;
}

.message-bubble {
  max-width: 85%;
  padding: 0.75rem;
  border-radius: 8px;
  word-break: break-word;
  line-height: 1.5;
}

.message-developer .message-bubble {
  background-color: #2196f3;
  color: white;
  border-bottom-right-radius: 0;
}

.message-agent .message-bubble {
  background-color: rgba(0, 0, 0, 0.05);
  color: rgba(0, 0, 0, 0.87);
  border-bottom-left-radius: 0;
}

.message-sender {
  opacity: 0.7;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.message-content {
  white-space: pre-wrap;
  word-wrap: break-word;
}

.message-developer .message-content {
  color: white;
}

/* Compose section */
.compose-section {
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  background-color: rgba(0, 0, 0, 0.01);
}

:deep(.v-textarea) {
  font-family: 'Roboto', sans-serif;
}

:deep(.v-textarea textarea) {
  resize: none;
  max-height: 100px;
}

/* Responsive */
@media (max-width: 600px) {
  .message-thread-panel {
    position: fixed;
    right: 0;
    bottom: 0;
    top: 0;
    width: 100% !important;
    max-width: 100%;
    border-radius: 0;
  }

  .message-bubble {
    max-width: 90%;
  }
}

/* Scrollbar styling */
.messages-container::-webkit-scrollbar {
  width: 6px;
}

.messages-container::-webkit-scrollbar-track {
  background: transparent;
}

.messages-container::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.1);
  border-radius: 3px;
}

.messages-container::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.2);
}

/* Firefox */
.messages-container {
  scrollbar-color: rgba(0, 0, 0, 0.1) transparent;
  scrollbar-width: thin;
}
</style>
