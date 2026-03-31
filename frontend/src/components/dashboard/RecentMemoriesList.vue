<template>
  <div class="recent-memories-list">
    <div v-if="memories.length === 0" class="text-caption text-disabled pa-3 text-center">
      No recent memories
    </div>
    <v-list
      v-else
      density="compact"
      bg-color="transparent"
      class="pa-0 memories-scroll"
    >
      <v-list-item
        v-for="(memory, idx) in memories"
        :key="idx"
        class="px-2 py-1 memory-row"
      >
        <div class="d-flex align-center ga-2 mb-1">
          <span class="text-body-2 font-weight-bold">
            {{ memory.project_name }}
          </span>
          <span v-if="memory.product_name" class="text-caption text-medium-emphasis">({{ memory.product_name }})</span>
          <span class="ml-auto d-flex align-center ga-2">
            <v-chip
              v-if="memory.entry_type"
              size="x-small"
              variant="outlined"
              color="yellow-darken-2"
              class="entry-type-chip"
              :aria-label="`Archived: ${humanizeType(memory.entry_type)}`"
            >
              Archived
            </v-chip>
            <span class="text-caption text-medium-emphasis relative-time">
              {{ relativeTime(memory.timestamp) }}
            </span>
          </span>
        </div>
        <div class="text-caption text-medium-emphasis summary-text">
          {{ truncate(memory.summary, 120) }}
        </div>
      </v-list-item>
    </v-list>
  </div>
</template>

<script setup>
defineProps({
  memories: {
    type: Array,
    default: () => [],
  },
})

function humanizeType(type) {
  const labels = {
    project_closeout: 'Project closeout',
    project_completion: 'Project completion',
    session_handover: 'Session handover',
    handover_closeout: 'Handover closeout',
  }
  return labels[type] || type.replace(/_/g, ' ')
}

function truncate(text, maxLen) {
  if (!text) return ''
  if (text.length <= maxLen) return text
  return `${text.substring(0, maxLen)}...`
}

function relativeTime(timestamp) {
  if (!timestamp) return ''
  const now = new Date()
  const then = new Date(timestamp)
  const diffMs = now - then
  if (diffMs < 0) return 'just now'

  const minutes = Math.floor(diffMs / 60000)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)
  const weeks = Math.floor(days / 7)

  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes}m ago`
  if (hours < 24) return `${hours}h ago`
  if (days < 7) return `${days}d ago`
  return `${weeks}w ago`
}
</script>

<style scoped>
.memories-scroll {
  max-height: 340px;
  overflow-y: auto;
}

.memory-row {
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  min-height: 48px;
}

.memory-row:last-child {
  border-bottom: none;
}

.entry-type-chip {
  font-size: 0.6rem;
  font-weight: 600;
}

.summary-text {
  line-height: 1.3;
  word-break: break-word;
}

.relative-time {
  white-space: nowrap;
  flex-shrink: 0;
}
</style>
