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
            <button
              type="button"
              class="tab-button"
              :class="{ active: activeTab === 'plan' }"
              data-test="messages-tab-plan"
              @click="activeTab = 'plan'"
            >
              Plan / TODOs ({{ planCount }})
            </button>
          </div>

          <v-divider />

          <!-- Two-column layout: list + detail (or TODO list for Plan tab) -->
          <div class="message-audit-body">
          <!-- Plan/TODOs Tab: Display todo items instead of messages (Handover 0402) -->
          <div v-if="activeTab === 'plan'" class="todo-items-column">
            <div
              v-if="todoItems.length === 0"
              class="empty-state pa-4 text-center"
            >
              <v-icon icon="mdi-checkbox-blank-outline" size="32" class="mb-2" />
              <div class="text-body-2 text-medium-emphasis">
                No tasks reported yet
              </div>
            </div>

            <div
              v-else
              class="todo-items-list pa-2"
            >
              <div
                v-for="(item, index) in todoItems"
                :key="`todo-${index}`"
                class="todo-item-row"
                data-test="todo-item-row"
              >
                <v-icon
                  :icon="getStatusIcon(item.status)"
                  :color="getStatusColor(item.status)"
                  :class="{ 'pulse-animation': item.status === 'in_progress' }"
                  class="mr-2"
                  size="20"
                />
                <span class="todo-item-content">{{ item.content }}</span>
              </div>
            </div>
          </div>

          <!-- Message tabs: Show message list + detail pane -->
          <template v-else>
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
                  class="audit-message-row"
                  data-test="audit-message-row"
                  @click="selectMessage(message)"
                >
                  <div class="audit-message-title">
                    {{ getMessagePreview(message) }}
                  </div>
                  <div class="audit-message-meta">
                    {{ formatMessageMeta(message) }}
                  </div>
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
          </template>
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

// Plan / TODO items (Handover 0402: use todo_items from agent job, not messages)
const todoItems = computed(() =>
  props.agent?.todo_items && Array.isArray(props.agent.todo_items)
    ? props.agent.todo_items
    : [],
)

const sentCount = computed(() => sentMessages.value.length)
const waitingCount = computed(() => waitingMessages.value.length)
const readCount = computed(() => readMessages.value.length)
const planCount = computed(() => todoItems.value.length)

const currentMessages = computed(() => {
  if (activeTab.value === 'sent') return sentMessages.value
  if (activeTab.value === 'read') return readMessages.value
  if (activeTab.value === 'plan') return [] // Plan tab uses todoItems, not messages
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
      return
    }
    // When opening, pick the requested initial tab if provided
    activeTab.value = props.initialTab || 'waiting'
    selectedMessage.value = null
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

function getMessagePreview(message) {
  const text = message.text || message.content || message.message || ''
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

// Handover 0402: Helper functions for todo item status display
function getStatusIcon(status) {
  switch (status) {
    case 'completed':
      return 'mdi-checkbox-marked'
    case 'in_progress':
      return 'mdi-progress-clock'
    case 'pending':
    default:
      return 'mdi-checkbox-blank-outline'
  }
}

function getStatusColor(status) {
  switch (status) {
    case 'completed':
      return 'success'
    case 'in_progress':
      return 'warning'
    case 'pending':
    default:
      return 'grey'
  }
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

.audit-message-row {
  cursor: pointer;
}

.audit-message-row:hover {
  background-color: rgba(0, 0, 0, 0.04);
}

.audit-message-list {
  padding: 8px 0;
}

.empty-state {
  color: rgba(0, 0, 0, 0.6);
}

/* Handover 0402: TODO items styling */
.todo-items-column {
  flex: 1 1 100%;
  max-height: 400px;
  overflow-y: auto;
}

.todo-items-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.todo-item-row {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  border-radius: 4px;
  transition: background-color 0.2s ease;
}

.todo-item-row:hover {
  background-color: rgba(0, 0, 0, 0.02);
}

.todo-item-content {
  font-size: 0.875rem;
  line-height: 1.4;
}

/* Pulse animation for in_progress items */
@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.pulse-animation {
  animation: pulse 2s ease-in-out infinite;
}
</style>
