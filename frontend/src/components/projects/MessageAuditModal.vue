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
        </div>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import MessageDetailView from '@/components/projects/MessageDetailView.vue'

const props = defineProps({
  show: {
    type: Boolean,
    required: true,
  },
  agent: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['close'])

// Tabs: 'sent' | 'waiting' | 'read'
const activeTab = ref('waiting')
const selectedMessage = ref(null)

const messages = computed(() =>
  props.agent && Array.isArray(props.agent.messages) ? props.agent.messages : [],
)

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
  return props.agent.agent_name || props.agent.agent_type || 'Agent'
})

watch(
  () => props.show,
  (value) => {
    if (!value) {
      activeTab.value = 'waiting'
      selectedMessage.value = null
    }
  },
)

watch(
  () => props.agent,
  () => {
    selectedMessage.value = null
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
  const direction = message.direction || 'unknown'
  const status = message.status || 'unknown'
  const timestamp = message.timestamp || message.created_at
  const date = timestamp ? new Date(timestamp) : null
  const timePart =
    date && !Number.isNaN(date.getTime()) ? date.toLocaleString() : 'Unknown time'
  return `${direction} · ${status} · ${timePart}`
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
</style>
