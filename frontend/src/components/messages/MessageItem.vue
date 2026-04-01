<template>
  <v-card variant="flat" class="message-item smooth-border mb-3" :class="messageClass" data-testid="message-item">
    <v-card-text class="pa-3">
      <div class="d-flex align-start">
        <!-- Sender Badge -->
        <div class="sender-badge mr-3" :style="senderBadgeStyle">
          <v-icon :icon="senderIcon" size="20" />
        </div>

        <!-- Message Content -->
        <div class="flex-grow-1">
          <!-- Header: Sender and Timestamp -->
          <div class="d-flex align-center justify-space-between mb-2">
            <div class="d-flex align-center">
              <span class="font-weight-medium text-body-1 mr-2" data-testid="message-from">
                {{ displaySender }}
              </span>
              <v-icon
                v-if="isBroadcast"
                icon="mdi-bullhorn"
                size="16"
                color="orange"
                class="mr-2"
              />
              <span
                v-if="message.priority !== 'normal'"
                class="tinted-chip mr-2"
                :style="priorityChipStyle"
              >
                {{ message.priority }}
              </span>
              <span class="tinted-chip" :style="statusChipStyle">
                {{ message.status }}
              </span>
            </div>
            <span class="text-caption text-muted-a11y">
              {{ relativeTime }}
            </span>
          </div>

          <!-- Recipients -->
          <div v-if="recipients.length > 0" class="text-caption text-muted-a11y mb-2" data-testid="message-to">
            <v-icon icon="mdi-arrow-right" size="12" class="mr-1" />
            {{ recipientsText }}
          </div>

          <!-- Message Content with Markdown -->
          <div class="message-content text-body-2" data-testid="message-content" v-html="renderedContent" />

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
import DOMPurify from 'dompurify'
import { hexToRgba } from '@/utils/colorUtils'
import { getAgentColor } from '@/config/agentColors'
import { getStatusColor } from '@/utils/statusConfig'
import { useFormatDate } from '@/composables/useFormatDate'
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

const { formatDate } = useFormatDate()

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

// Sender appearance — agent color tokens
const senderHex = computed(() => {
  if (isBroadcast.value) return getAgentColor('tester').hex
  if (isSystem.value) return '#8895a8'
  if (isUser.value) return getAgentColor('reviewer').hex
  if (isOrchestrator.value) return getAgentColor('orchestrator').hex
  return getAgentColor('implementer').hex
})

const senderBadgeStyle = computed(() => ({
  width: '36px',
  height: '36px',
  minWidth: '36px',
  borderRadius: '8px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  backgroundColor: hexToRgba(senderHex.value, 0.15),
  color: senderHex.value,
}))

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

// Priority styling — agent color tokens
const PRIORITY_COLORS: Record<string, string> = {
  urgent: getAgentColor('analyzer').hex,
  high: getAgentColor('tester').hex,
}

const priorityChipStyle = computed(() => {
  const hex = PRIORITY_COLORS[props.message.priority] || '#8895a8'
  return {
    backgroundColor: hexToRgba(hex, 0.15),
    color: hex,
  }
})

// Status styling — status/agent color tokens
const STATUS_COLORS: Record<string, string> = {
  completed: getStatusColor('complete'),
  failed: getAgentColor('analyzer').hex,
  acknowledged: getAgentColor('implementer').hex,
  delivered: getAgentColor('implementer').hex,
  pending: getAgentColor('tester').hex,
}

const statusChipStyle = computed(() => {
  const hex = STATUS_COLORS[props.message.status] || '#8895a8'
  return {
    backgroundColor: hexToRgba(hex, 0.15),
    color: hex,
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
  return formatDate(timestamp)
})

// Markdown rendering
const renderedContent = computed(() => {
  try {
    return DOMPurify.sanitize(marked(props.message.content))
  } catch {
    return DOMPurify.sanitize(props.message.content)
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

<style lang="scss" scoped>
@use '../../styles/design-tokens' as *;
.message-item {
  background: $elevation-raised;
  border-radius: $border-radius-md;
  transition: all $transition-normal ease;
}

.message-item:hover {
  background: rgba(255, 255, 255, 0.02);
}

.broadcast-message {
  --smooth-border-color: rgba(237, 186, 74, 0.3);
}

.system-message {
  background-color: rgba(255, 255, 255, 0.02);
}

.tinted-chip {
  display: inline-flex;
  align-items: center;
  padding: 1px 8px;
  border-radius: $border-radius-default;
  font-size: 0.68rem;
  font-weight: 600;
  text-transform: capitalize;
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
  border-radius: $border-radius-sharp;
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
}

.message-content :deep(pre) {
  background-color: rgba(var(--v-theme-surface-variant), 0.5);
  padding: 1rem;
  border-radius: $border-radius-sharp;
  overflow-x: auto;
  margin: 0.5rem 0;
}

.message-content :deep(pre code) {
  background-color: transparent;
  padding: 0;
}
</style>
