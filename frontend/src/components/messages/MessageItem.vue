<template>
  <v-card variant="outlined" class="message-item mb-3" :class="messageClass">
    <v-card-text class="pa-3">
      <div class="d-flex align-start">
        <!-- Sender Avatar -->
        <v-avatar :color="senderColor" size="40" class="mr-3">
          <v-icon :icon="senderIcon" size="24" />
        </v-avatar>

        <!-- Message Content -->
        <div class="flex-grow-1">
          <!-- Header: Sender and Timestamp -->
          <div class="d-flex align-center justify-space-between mb-2">
            <div class="d-flex align-center">
              <span class="font-weight-medium text-body-1 mr-2">
                {{ displaySender }}
              </span>
              <v-icon
                v-if="isBroadcast"
                icon="mdi-bullhorn"
                size="16"
                color="orange"
                class="mr-2"
              />
              <v-chip
                v-if="message.priority !== 'normal'"
                :color="priorityColor"
                size="x-small"
                class="mr-2"
              >
                {{ message.priority }}
              </v-chip>
              <v-chip :color="statusColor" size="x-small" variant="flat">
                {{ message.status }}
              </v-chip>
            </div>
            <span class="text-caption text-medium-emphasis">
              {{ relativeTime }}
            </span>
          </div>

          <!-- Recipients -->
          <div v-if="recipients.length > 0" class="text-caption text-medium-emphasis mb-2">
            <v-icon icon="mdi-arrow-right" size="12" class="mr-1" />
            {{ recipientsText }}
          </div>

          <!-- Message Content with Markdown -->
          <div class="message-content text-body-2" v-html="renderedContent" />

          <!-- Actions -->
          <div v-if="showActions" class="mt-2">
            <v-btn variant="text" size="small" color="primary" @click="handleReply">
              <v-icon icon="mdi-reply" start />
              Reply
            </v-btn>
          </div>
        </div>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'
import type { Message } from '@/types/message'

interface Props {
  message: Message
  showActions?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  showActions: false,
})

const emit = defineEmits<{
  reply: [message: Message]
}>()

// Display sender (normalize field names)
const displaySender = computed(() => {
  const sender = props.message.from || props.message.from_agent || 'Unknown'
  if (sender === 'user') return 'User'
  if (sender === 'system') return 'System'
  if (sender === 'orchestrator') return 'Orchestrator'
  return sender
})

// Message type classification
const messageType = computed(() => props.message.type || props.message.message_type || 'direct')
const isBroadcast = computed(() => messageType.value === 'broadcast')
const isSystem = computed(() => messageType.value === 'system' || displaySender.value === 'System')
const isUser = computed(() => displaySender.value === 'User')
const isOrchestrator = computed(() => displaySender.value === 'Orchestrator')

// Sender appearance
const senderColor = computed(() => {
  if (isBroadcast.value) return 'orange'
  if (isSystem.value) return 'grey'
  if (isUser.value) return 'purple'
  if (isOrchestrator.value) return 'indigo'
  return 'blue'
})

const senderIcon = computed(() => {
  if (isBroadcast.value) return 'mdi-bullhorn'
  if (isSystem.value) return 'mdi-information'
  if (isUser.value) return 'mdi-account'
  if (isOrchestrator.value) return 'mdi-account-supervisor'
  return 'mdi-chat'
})

// Priority styling
const priorityColor = computed(() => {
  switch (props.message.priority) {
    case 'urgent':
      return 'error'
    case 'high':
      return 'warning'
    default:
      return 'default'
  }
})

// Status styling
const statusColor = computed(() => {
  switch (props.message.status) {
    case 'completed':
      return 'success'
    case 'failed':
      return 'error'
    case 'acknowledged':
      return 'info'
    case 'delivered':
      return 'primary'
    default:
      return 'grey'
  }
})

// Recipients display
const recipients = computed(() => {
  const toAgents = props.message.to_agents || []
  const toAgent = props.message.to_agent
  if (toAgents.length > 0) return toAgents
  if (toAgent) return [toAgent]
  return []
})

const recipientsText = computed(() => {
  if (recipients.value.length === 0) return 'All Agents'
  if (recipients.value.length === 1) return recipients.value[0]
  if (recipients.value.length <= 3) return recipients.value.join(', ')
  return `${recipients.value.length} agents`
})

// Relative time display
const relativeTime = computed(() => {
  const timestamp = new Date(props.message.created_at)
  const now = new Date()
  const diffMs = now.getTime() - timestamp.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return timestamp.toLocaleDateString()
})

// Markdown rendering
const renderedContent = computed(() => {
  try {
    return marked(props.message.content)
  } catch {
    return props.message.content
  }
})

// Card styling based on type
const messageClass = computed(() => {
  if (isBroadcast.value) return 'broadcast-message'
  if (isSystem.value) return 'system-message'
  return ''
})

// Actions
const handleReply = () => {
  emit('reply', props.message)
}
</script>

<style scoped>
.message-item {
  transition: all 0.2s ease;
}

.message-item:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.broadcast-message {
  border-left: 4px solid rgb(var(--v-theme-orange));
}

.system-message {
  background-color: rgba(var(--v-theme-surface-variant), 0.5);
}

.message-content {
  word-wrap: break-word;
  overflow-wrap: break-word;
}

.message-content :deep(p) {
  margin-bottom: 0.5rem;
}

.message-content :deep(p:last-child) {
  margin-bottom: 0;
}

.message-content :deep(code) {
  background-color: rgba(var(--v-theme-surface-variant), 0.5);
  padding: 0.2rem 0.4rem;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
}

.message-content :deep(pre) {
  background-color: rgba(var(--v-theme-surface-variant), 0.5);
  padding: 1rem;
  border-radius: 4px;
  overflow-x: auto;
  margin: 0.5rem 0;
}

.message-content :deep(pre code) {
  background-color: transparent;
  padding: 0;
}
</style>
