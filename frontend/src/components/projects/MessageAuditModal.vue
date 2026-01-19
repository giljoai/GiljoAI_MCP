<template>
  <v-dialog
    :model-value="show"
    max-width="960"
    persistent
    class="message-audit-modal"
    @keydown.esc="handleClose"
  >
    <v-card>
      <!-- Header -->
      <v-card-title class="d-flex align-center justify-space-between">
        <div class="d-flex align-center">
          <v-icon icon="mdi-folder-account-outline" class="mr-2" />
          <div class="d-flex flex-column">
            <span class="text-subtitle-1">Message Audit: {{ agentLabel }}</span>
            <span class="text-caption text-medium-emphasis">
              {{ agent?.job_id || 'Unknown job' }}
            </span>
            <span
              v-if="steps && typeof steps.completed === 'number' && typeof steps.total === 'number'"
              class="text-caption text-medium-emphasis"
            >
              Steps: {{ steps.completed }} / {{ steps.total }}
            </span>
          </div>
        </div>
        <v-btn
          icon
          variant="text"
          aria-label="Close message audit"
          @click="handleClose"
        >
          <v-icon icon="mdi-close" />
        </v-btn>
      </v-card-title>

      <v-divider />

      <!-- Tabs + Content -->
      <v-card-text class="pa-0">
        <!-- Loading State (Handover 0387g Phase 4) -->
        <div v-if="loading" class="pa-8 text-center">
          <v-progress-circular indeterminate color="primary" size="48" class="mb-4" />
          <div class="text-body-2 text-medium-emphasis">Loading messages...</div>
        </div>

        <!-- Error State (Handover 0387g Phase 4) -->
        <div v-else-if="error" class="pa-4">
          <v-alert type="error" variant="tonal" closable>
            {{ error }}
          </v-alert>
        </div>

        <!-- Loaded State: Tabs + Content (Handover 0387g Phase 4) -->
        <div v-else>
          <!-- Category Tabs (simple buttons to avoid extra dependencies in tests) -->
          <div class="message-audit-tabs">
            <button
              type="button"
              class="tab-button"
              :class="{ active: activeTab === 'sent' }"
              data-test="messages-tab-sent"
              @click="activeTab = 'sent'"
            >
              Sent ({{ sentCount }})
            </button>
            <button
              type="button"
              class="tab-button"
              :class="{ active: activeTab === 'waiting' }"
              data-test="messages-tab-waiting"
              @click="activeTab = 'waiting'"
            >
              Waiting ({{ waitingCount }})
            </button>
            <button
              type="button"
              class="tab-button"
              :class="{ active: activeTab === 'read' }"
              data-test="messages-tab-read"
              @click="activeTab = 'read'"
            >
              Read ({{ readCount }})
            </button>
          </div>

          <v-divider />

          <!-- Two-column layout: list + detail -->
          <div class="message-audit-body">
            <!-- Message list -->
            <div class="message-list-column">
              <div
                v-if="currentMessages.length === 0"
                class="empty-state pa-4 text-center"
              >
                <v-icon icon="mdi-message-outline" size="32" class="mb-2" />
                <div class="text-body-2 text-medium-emphasis">
                  No messages in this category
                </div>
              </div>

              <div
                v-else
                class="audit-message-list"
              >
                <div
                  v-for="message in currentMessages"
                  :key="message.id"
                  class="message-item-wrapper"
                  data-test="audit-message-row"
                >
                  <!-- Message Header: Timestamp | Recipient -->
                  <div class="message-header">
                    <span class="message-timestamp">{{ formatTimestamp(message) }}</span>
                    <span class="message-separator">|</span>
                    <span class="message-recipient">To: {{ formatRecipient(message) }}</span>
                  </div>

                  <!-- Message Content Line with Eye Icon -->
                  <div
                    class="message-content-line"
                    @click="toggleMessageExpansion(message.id)"
                  >
                    <span class="message-preview">{{ getMessagePreview(message) }}</span>
                    <v-icon
                      icon="mdi-eye"
                      size="small"
                      class="message-eye-icon"
                    />
                  </div>

                  <!-- Expanded Full Content -->
                  <div
                    v-if="isMessageExpanded(message.id)"
                    class="message-full-content"
                  >
                    <div class="message-full-text">
                      {{ getMessageContent(message) }}
                    </div>
                  </div>

                  <!-- Divider -->
                  <v-divider class="message-divider" />
                </div>
              </div>
            </div>

            <!-- Detail pane -->
            <div
              v-if="selectedMessage"
              class="message-detail-column"
            >
              <MessageDetailView :message="selectedMessage" />
            </div>
          </div>
        </div>
        <!-- End v-else wrapper for loaded state -->
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import MessageDetailView from '@/components/projects/MessageDetailView.vue'
import api from '@/services/api'

const props = defineProps({
  show: {
    type: Boolean,
    required: true,
  },
  agent: {
    type: Object,
    default: null,
  },
  // Initial tab when opening the modal: 'waiting' | 'sent' | 'read' | 'plan'
  initialTab: {
    type: String,
    default: 'waiting',
  },
  // Optional steps summary for header context (completed/total)
  steps: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['close'])

// Tabs: 'sent' | 'waiting' | 'read' | 'plan'
const activeTab = ref(props.initialTab || 'waiting')
const selectedMessage = ref(null)

// Track expanded messages by message ID (for inline expansion)
const expandedMessages = ref(new Set())

// API fetch logic (Handover 0387g Phase 4: fetch from MessageRepository, not JSONB)
const messages = ref([])
const loading = ref(false)
const error = ref(null)

async function fetchMessages() {
  if (!props.agent?.job_id) {
    messages.value = []
    return
  }

  loading.value = true
  error.value = null

  try {
    const response = await api.agentJobs.messages(props.agent.job_id)
    messages.value = response.data?.messages || []
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || 'Failed to load messages'
    messages.value = []
  } finally {
    loading.value = false
  }
}

// Match JobsTab helper semantics so counts stay aligned with the table
const sentMessages = computed(() =>
  messages.value.filter(
    (m) => m.from === 'developer' || m.direction === 'outbound',
  ),
)

const waitingMessages = computed(() =>
  messages.value.filter(
    (m) => m.status === 'pending' || m.status === 'waiting',
  ),
)

const readMessages = computed(() =>
  messages.value.filter(
    (m) =>
      m.direction === 'inbound' &&
      (m.status === 'acknowledged' || m.status === 'read'),
  ),
)

const sentCount = computed(() => sentMessages.value.length)
const waitingCount = computed(() => waitingMessages.value.length)
const readCount = computed(() => readMessages.value.length)

const currentMessages = computed(() => {
  if (activeTab.value === 'sent') return sentMessages.value
  if (activeTab.value === 'read') return readMessages.value
  return waitingMessages.value
})

const agentLabel = computed(() => {
  if (!props.agent) return 'Unknown agent'
  return props.agent.agent_name || props.agent.agent_display_name || 'Agent'
})

// Fetch messages when modal opens (Handover 0387g Phase 4)
watch(
  () => props.show,
  (value) => {
    if (!value) {
      selectedMessage.value = null
      expandedMessages.value = new Set() // Clear expanded state when closing
      return
    }
    // When opening, pick the requested initial tab if provided
    activeTab.value = props.initialTab || 'waiting'
    selectedMessage.value = null
    expandedMessages.value = new Set() // Clear expanded state when opening
    // Fetch messages from API instead of using props.agent.messages
    fetchMessages()
  },
)

watch(
  () => props.agent,
  () => {
    selectedMessage.value = null
    // Refetch if agent changes while modal is open
    if (props.show) {
      fetchMessages()
    }
  },
)

function handleClose() {
  emit('close')
}

function selectMessage(message) {
  selectedMessage.value = message
}

function toggleMessageExpansion(messageId) {
  if (expandedMessages.value.has(messageId)) {
    expandedMessages.value.delete(messageId)
  } else {
    expandedMessages.value.add(messageId)
  }
  // Trigger reactivity
  expandedMessages.value = new Set(expandedMessages.value)
}

function isMessageExpanded(messageId) {
  return expandedMessages.value.has(messageId)
}

function formatTimestamp(message) {
  const timestamp = message.timestamp || message.created_at
  if (!timestamp) return 'Unknown time'
  const date = new Date(timestamp)
  if (Number.isNaN(date.getTime())) return 'Unknown time'

  // Format as "HH:MM:SS"
  return date.toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

function formatRecipient(message) {
  // Check if broadcast message
  const toBroadcast = message.to_agents?.includes('all') ||
                      message.message_type === 'broadcast' ||
                      !message.to_agent_id

  if (toBroadcast) return 'Broadcast'

  // Try to get agent name if available
  // Note: The message object may not have agent names, only IDs
  // In a future enhancement, we could look up the agent name from the jobs list
  const toAgentId = message.to_agent_id
  if (toAgentId) {
    return toAgentId.slice(0, 8) + '...'
  }

  return 'Unknown'
}

function getMessageContent(message) {
  return message.text || message.content || message.message || ''
}

function getMessagePreview(message) {
  const text = getMessageContent(message)
  if (!text) return '(empty message)'
  if (text.length <= 80) return text
  return `${text.slice(0, 77)}...`
}

function formatMessageMeta(message) {
  const fromId = message.from_agent_id
    ? message.from_agent_id.slice(0, 8) + '...'
    : 'user'
  const toId = message.to_agent_id
    ? message.to_agent_id.slice(0, 8) + '...'
    : 'broadcast'
  const status = message.status || 'unknown'
  const timestamp = message.timestamp || message.created_at
  const date = timestamp ? new Date(timestamp) : null
  const timePart =
    date && !Number.isNaN(date.getTime()) ? date.toLocaleTimeString() : 'Unknown time'

  return `${timePart} | ${fromId} → ${toId} (${status})`
}
</script>

<style scoped>
.message-audit-modal {
  z-index: 2100;
}

.message-audit-tabs {
  display: flex;
  border-bottom: 1px solid rgba(0, 0, 0, 0.12);
}

.tab-button {
  flex: 1 1 0;
  padding: 8px 12px;
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 0.875rem;
  text-align: center;
}

.tab-button.active {
  border-bottom: 2px solid rgb(var(--v-theme-primary));
  font-weight: 600;
}

.message-audit-body {
  display: flex;
  flex-direction: row;
  min-height: 280px;
}

.message-list-column {
  flex: 1 1 55%;
  max-height: 400px;
  overflow-y: auto;
  border-right: 1px solid rgba(0, 0, 0, 0.06);
}

.message-detail-column {
  flex: 1 1 45%;
  max-height: 400px;
  overflow-y: auto;
}

.audit-message-list {
  padding: 8px 0;
}

.message-item-wrapper {
  padding: 12px 16px;
  transition: background-color 0.2s ease;
}

.message-item-wrapper:hover {
  background-color: rgba(0, 0, 0, 0.02);
}

/* Message Header: Timestamp | Recipient */
.message-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
  font-size: 0.875rem;
}

.message-timestamp {
  color: rgba(0, 0, 0, 0.6);
  font-family: 'Courier New', monospace;
}

.message-separator {
  color: rgba(0, 0, 0, 0.4);
}

.message-recipient {
  color: rgba(0, 0, 0, 0.6);
  font-weight: 500;
}

/* Message Content Line with Eye Icon */
.message-content-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  cursor: pointer;
  padding: 4px 0;
  transition: all 0.2s ease;
}

.message-content-line:hover {
  color: rgb(var(--v-theme-primary));
}

.message-content-line:hover .message-eye-icon {
  color: rgb(var(--v-theme-primary));
  transform: scale(1.1);
}

.message-preview {
  flex: 1;
  font-size: 0.875rem;
  line-height: 1.4;
}

.message-eye-icon {
  color: rgba(0, 0, 0, 0.5);
  transition: all 0.2s ease;
  flex-shrink: 0;
}

/* Expanded Full Content */
.message-full-content {
  margin-top: 8px;
  padding: 12px;
  background-color: rgba(0, 0, 0, 0.03);
  border-radius: 4px;
  border-left: 3px solid rgb(var(--v-theme-primary));
}

.message-full-text {
  white-space: pre-wrap;
  font-family: 'Courier New', monospace;
  font-size: 0.85rem;
  line-height: 1.5;
  color: rgba(0, 0, 0, 0.87);
}

/* Divider between messages */
.message-divider {
  margin-top: 12px;
  opacity: 0.6;
}

.empty-state {
  color: rgba(0, 0, 0, 0.6);
}

/* Legacy styles (kept for compatibility with any remaining references) */
.audit-message-row {
  cursor: pointer;
}

.audit-message-row:hover {
  background-color: rgba(0, 0, 0, 0.04);
}
</style>
