<template>
  <div class="message-detail" data-test="audit-message-detail" data-testid="message-detail">
    <h3 class="text-subtitle-1 mb-2">Message Details</h3>

    <div v-if="!message" class="text-body-2 text-muted-a11y">
      Select a message to inspect its details.
    </div>

    <div v-else>
      <div class="meta-row">
        <strong>From:</strong>
        <span>{{ message.from || 'unknown' }}</span>
      </div>
      <div class="meta-row">
        <strong>From Agent ID:</strong>
        <code class="text-mono">{{ message.from_agent_id || 'User' }}</code>
      </div>
      <div class="meta-row">
        <strong>To:</strong>
        <span>{{ message.to || 'Unknown' }}</span>
      </div>
      <div class="meta-row">
        <strong>To Agent ID:</strong>
        <code class="text-mono">{{ message.to_agent_id || 'N/A' }}</code>
      </div>
      <div class="meta-row">
        <strong>Direction:</strong>
        <span>{{ message.direction || 'unknown' }}</span>
      </div>
      <div class="meta-row">
        <strong>Status:</strong>
        <span>{{ message.status || 'unknown' }}</span>
      </div>
      <div class="meta-row">
        <strong>Timestamp:</strong>
        <span>{{ formattedTimestamp }}</span>
      </div>
      <div v-if="message.priority" class="meta-row">
        <strong>Priority:</strong>
        <span>{{ message.priority }}</span>
      </div>

      <v-divider class="my-3" />

      <div class="text-caption text-muted-a11y mb-1">
        Content
      </div>
      <pre class="message-body">
{{ message.text || message.content || message.message || '' }}
      </pre>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  message: {
    type: Object,
    default: null,
  },
})

const formattedTimestamp = computed(() => {
  if (!props.message) return 'Unknown time'
  const raw = props.message.timestamp || props.message.created_at
  if (!raw) return 'Unknown time'
  const date = new Date(raw)
  if (Number.isNaN(date.getTime())) return 'Unknown time'
  return date.toLocaleString()
})
</script>

<style lang="scss" scoped>
@use '../../styles/design-tokens' as *;
.message-detail {
  padding: 16px;
}

.meta-row {
  display: flex;
  gap: 8px;
  margin-bottom: 4px;
}

.message-body {
  white-space: pre-wrap;
  font-family: 'Courier New', monospace;
  font-size: 0.85rem;
  background-color: rgba(0, 0, 0, 0.03);
  padding: 8px;
  border-radius: $border-radius-sharp;
}

.text-mono {
  font-family: 'Courier New', monospace;
  font-size: 0.85rem;
  background-color: rgba(0, 0, 0, 0.05);
  padding: 2px 6px;
  border-radius: $border-radius-sharp;
}
</style>
