<template>
  <v-dialog
    :model-value="show"
    max-width="960"
    persistent
    class="message-audit-modal"
    @keydown.esc="handleClose"
  >
    <v-card v-draggable class="smooth-border">
      <!-- Header -->
      <div class="dlg-header">
        <div
          class="agent-badge-sq"
          :style="{
            background: agentTintedBg,
            color: agentPrimaryColor,
          }"
        >{{ agentAbbr }}</div>
        <div class="d-flex flex-column" style="flex:1">
          <span class="dlg-title">Message Audit: {{ agentLabel }}</span>
          <span class="text-caption text-muted-a11y">
            {{ displayAgent?.job_id || 'Unknown job' }}
          </span>
          <span
            v-if="steps && typeof steps.completed === 'number' && typeof steps.total === 'number'"
            class="text-caption text-muted-a11y"
          >
            Steps: {{ steps.completed }} / {{ steps.total }}
          </span>
        </div>
        <v-btn icon variant="text" size="small" class="dlg-close" @click="handleClose">
          <v-icon icon="mdi-close" size="18" />
        </v-btn>
      </div>

      <v-divider />

      <!-- Tabs + Content -->
      <v-card-text class="pa-0">
        <!-- Loading State (Handover 0387g Phase 4) -->
        <div v-if="loading" class="pa-8 text-center">
          <v-progress-circular indeterminate color="primary" size="48" class="mb-4" />
          <div class="text-body-2 text-muted-a11y">Loading messages...</div>
        </div>

        <!-- Error State (Handover 0387g Phase 4) -->
        <div v-else-if="error" class="pa-4">
          <v-alert type="error" variant="tonal" density="compact" closable>
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
              <EmptyState
                v-if="currentMessages.length === 0"
                icon="mdi-message-outline"
                title="No messages in this category"
              />

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
                    role="button"
                    aria-label="Toggle message details"
                    @click="toggleMessageExpansion(message.id)"
                  >
                    <span class="message-preview">{{ getMessagePreview(message) }}</span>
                    <span class="eye-icon-container">
                      <v-icon
                        icon="mdi-eye"
                        size="x-small"
                        class="message-eye-icon"
                      />
                    </span>
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
import { computed, ref, toRaw, watch } from 'vue'
import MessageDetailView from '@/components/projects/MessageDetailView.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import api from '@/services/api'
import { getAgentColor as getAgentColorConfig } from '@/config/agentColors'
import { hexToRgba } from '@/utils/colorUtils'

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
    default: 'sent',
  },
  // Optional steps summary for header context (completed/total)
  steps: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['close'])

// Tabs: 'sent' | 'waiting' | 'read' | 'plan'
const activeTab = ref(props.initialTab || 'sent')
const selectedMessage = ref(null)

// Track expanded messages by message ID (for inline expansion)
const expandedMessages = ref(new Set())

// Snapshot: freeze agent data when modal opens to decouple from live WebSocket reactivity
const agentSnapshot = ref(null)

// API fetch logic (Handover 0387g Phase 4: fetch from MessageRepository, not JSONB)
const messages = ref([])
const loading = ref(false)
const error = ref(null)

async function fetchMessages() {
  const jobId = agentSnapshot.value?.job_id
  if (!jobId) {
    messages.value = []
    return
  }

  loading.value = true
  error.value = null

  try {
    const response = await api.agentJobs.messages(jobId)
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
    (m) => m.direction === 'outbound',
  ),
)

const waitingMessages = computed(() =>
  messages.value.filter(
    (m) => m.direction === 'inbound' && (m.status === 'pending' || m.status === 'waiting'),
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

// Prefer snapshot data while modal is open; fall back to live prop
const displayAgent = computed(() => agentSnapshot.value || props.agent)

const agentLabel = computed(() => {
  const source = displayAgent.value
  if (!source) return 'Unknown agent'
  return source.agent_name || source.agent_display_name || 'Agent'
})

const agentPrimaryColor = computed(() => {
  return getAgentColorConfig(agentLabel.value).hex
})

const agentTintedBg = computed(() => {
  return hexToRgba(agentPrimaryColor.value, 0.15)
})

const agentAbbr = computed(() => {
  const name = agentLabel.value
  if (!name) return '?'
  return name
    .split(/[\s_-]+/)
    .map(word => word[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
})

// Fetch messages when modal opens (Handover 0387g Phase 4)
watch(
  () => props.show,
  (value) => {
    if (!value) {
      selectedMessage.value = null
      expandedMessages.value = new Set()
      agentSnapshot.value = null
      return
    }
    // Snapshot agent data on open -- disconnect from live WebSocket reactivity
    agentSnapshot.value = props.agent ? { ...toRaw(props.agent) } : null
    activeTab.value = props.initialTab || 'sent'
    selectedMessage.value = null
    expandedMessages.value = new Set()
    fetchMessages()
  },
)

function handleClose() {
  emit('close')
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
  return message.to || 'Unknown'
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

</script>

<style lang="scss" scoped>
@use '../../styles/design-tokens' as *;
.message-audit-modal {
  z-index: 2100;
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
  margin: 4px 8px;
  border-radius: $border-radius-sharp;
  transition: background-color $transition-normal ease;
}

.message-item-wrapper:hover {
  background-color: rgba(var(--v-theme-primary), 0.08);
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
  color: rgb(var(--v-theme-primary));
  font-family: 'IBM Plex Mono', monospace;
}

.v-theme--dark .message-timestamp {
  color: rgb(var(--v-theme-primary));
  opacity: 1;
}

.message-separator {
  color: rgb(var(--v-theme-primary));
  opacity: 0.7;
}

.v-theme--dark .message-separator {
  color: rgb(var(--v-theme-primary));
  opacity: 1;
}

.message-recipient {
  color: rgb(var(--v-theme-primary));
  font-weight: 500;
}

.v-theme--dark .message-recipient {
  color: rgb(var(--v-theme-primary));
  opacity: 1;
}

/* Message Content Line with Eye Icon */
.message-content-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  cursor: pointer;
  padding: 4px 0;
  transition: all $transition-normal ease;
}

.message-content-line:hover {
  color: rgb(var(--v-theme-primary));
}

.message-content-line:hover .eye-icon-container {
  transform: scale(1.15);
  box-shadow: 0 2px 8px rgba(var(--v-theme-primary), 0.4);
}

.v-theme--dark .message-content-line:hover .eye-icon-container {
  box-shadow: none;
}

.message-preview {
  flex: 1;
  font-size: 0.875rem;
  line-height: 1.4;
}

/* Eye Icon with Blue Circle Background and Yellow Icon */
.eye-icon-container {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background-color: rgb(var(--v-theme-primary));
  flex-shrink: 0;
  transition: all $transition-normal ease;
}

.v-theme--dark .eye-icon-container {
  background-color: transparent;
  box-shadow: none;
}

.message-eye-icon {
  color: rgb(var(--v-theme-primary));
  transition: all $transition-normal ease;
}

.v-theme--dark .message-eye-icon {
  opacity: 1;
}

/* Expanded Full Content */
.message-full-content {
  margin-top: 8px;
  padding: 12px;
  background-color: rgba(var(--v-theme-primary), 0.08);
  border-radius: $border-radius-sharp;
  border-left: 3px solid rgb(var(--v-theme-primary));
}

.message-full-text {
  white-space: pre-wrap;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.85rem;
  line-height: 1.5;
}

/* Divider between messages */
.message-divider {
  margin-top: 12px;
  opacity: 0.6;
}



/* Legacy styles (kept for compatibility with any remaining references) */
.audit-message-row {
  cursor: pointer;
}

.audit-message-row:hover {
  background-color: rgba(0, 0, 0, 0.04);
}
</style>
