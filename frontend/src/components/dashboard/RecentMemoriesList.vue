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
        class="px-2 py-1 memory-row clickable-row"
        @click="openMemory(memory)"
      >
        <div class="memory-header">
          <span class="text-body-2 font-weight-bold memory-title">
            {{ memory.project_name }}
            <span v-if="memory.product_name" class="text-caption text-medium-emphasis">({{ memory.product_name }})</span>
          </span>
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
        </div>
        <div class="text-caption text-medium-emphasis summary-text">
          {{ truncate(memory.summary, 120) }}
        </div>
      </v-list-item>
    </v-list>

    <!-- Memory Detail Dialog -->
    <v-dialog v-model="showDetail" max-width="640" scrollable>
      <v-card v-if="selectedMemory" class="smooth-border">
        <v-card-title class="d-flex align-center ga-2 py-3">
          <span>{{ selectedMemory.project_name }}</span>
          <v-chip
            v-if="selectedMemory.entry_type"
            size="x-small"
            variant="outlined"
            color="yellow-darken-2"
          >
            {{ humanizeType(selectedMemory.entry_type) }}
          </v-chip>
          <v-spacer />
          <v-btn icon="mdi-close" variant="text" size="small" @click="showDetail = false" />
        </v-card-title>
        <v-divider />
        <v-card-text class="pa-4">
          <div v-if="selectedMemory.product_name" class="text-caption text-medium-emphasis mb-3">
            Product: {{ selectedMemory.product_name }}
          </div>
          <div v-if="selectedMemory.timestamp" class="text-caption text-medium-emphasis mb-4">
            {{ new Date(selectedMemory.timestamp).toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' }) }}
          </div>
          <div class="text-body-2" style="white-space: pre-wrap; line-height: 1.6;">{{ selectedMemory.summary }}</div>
        </v-card-text>
        <v-divider v-if="selectedMemory.project_id" />
        <v-card-actions v-if="selectedMemory.project_id">
          <v-spacer />
          <v-btn
            variant="text"
            color="yellow-darken-2"
            prepend-icon="mdi-eye"
            @click="showDetail = false; emit('review-project', selectedMemory)"
          >
            View Project Review
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  memories: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['review-project'])

const showDetail = ref(false)
const selectedMemory = ref(null)

function openMemory(memory) {
  selectedMemory.value = memory
  showDetail.value = true
}

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

.memory-header {
  display: grid;
  grid-template-columns: 1fr 72px 56px;
  align-items: center;
  gap: 8px;
}

.memory-header .entry-type-chip {
  justify-self: center;
  font-size: 0.6rem;
  font-weight: 600;
}

.memory-header .relative-time {
  justify-self: end;
  text-align: right;
  white-space: nowrap;
}

.memory-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.summary-text {
  line-height: 1.3;
  word-break: break-word;
}

.clickable-row {
  cursor: pointer;
}

.clickable-row:hover {
  background: rgba(255, 255, 255, 0.04);
}
</style>
