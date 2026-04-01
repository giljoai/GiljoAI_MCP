<template>
  <div class="recent-memories-list">
    <div v-if="memories.length === 0" class="no-data-text">
      No recent memories
    </div>
    <div v-else class="memories-scroll">
      <div
        v-for="(memory, idx) in memories"
        :key="idx"
        class="memory-row"
        @click="openMemory(memory)"
      >
        <div class="memory-icon">
          <span class="mdi mdi-brain" />
        </div>
        <div class="memory-content">
          <div class="memory-text">{{ truncate(memory.summary, 120) }}</div>
          <div class="memory-meta">
            {{ memory.project_name }}
            <span v-if="memory.product_name"> · {{ memory.product_name }}</span>
            <span v-if="memory.timestamp"> · {{ relativeTime(memory.timestamp) }}</span>
          </div>
        </div>
        <span v-if="memory.entry_type" class="memory-type" :style="typeStyle(memory.entry_type)">
          {{ typeLabel(memory.entry_type) }}
        </span>
      </div>
    </div>

    <!-- Memory Detail Dialog -->
    <v-dialog v-model="showDetail" max-width="640" scrollable>
      <v-card v-if="selectedMemory" class="smooth-border">
        <v-card-title class="d-flex align-center ga-2 py-3">
          <span>{{ selectedMemory.project_name }}</span>
          <span
            v-if="selectedMemory.entry_type"
            class="memory-type-dialog"
            :style="typeStyle(selectedMemory.entry_type)"
          >
            {{ humanizeType(selectedMemory.entry_type) }}
          </span>
          <v-spacer />
          <v-btn icon="mdi-close" variant="text" size="small" @click="showDetail = false" />
        </v-card-title>
        <v-divider />
        <v-card-text class="pa-4">
          <div v-if="selectedMemory.product_name" class="text-caption mb-3" style="color: var(--text-muted)">
            Product: {{ selectedMemory.product_name }}
          </div>
          <div v-if="selectedMemory.timestamp" class="text-caption mb-4" style="color: var(--text-muted)">
            {{ new Date(selectedMemory.timestamp).toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' }) }}
          </div>
          <div class="text-body-2 text-pre-wrap" style="line-height: 1.6;">{{ selectedMemory.summary }}</div>
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
import { hexToRgba } from '@/utils/colorUtils'
import { getAgentColor } from '@/config/agentColors'

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

// Tinted type tag colors — mapped to agent color tokens
const typeColorMap = {
  project_closeout: getAgentColor('implementer').hex,
  project_completion: getAgentColor('documenter').hex,
  session_handover: getAgentColor('reviewer').hex,
  handover_closeout: getAgentColor('analyzer').hex,
}

const defaultTypeHex = getAgentColor('tester').hex

function typeStyle(entryType) {
  const hex = typeColorMap[entryType] || defaultTypeHex
  return { background: hexToRgba(hex, 0.12), color: hex }
}

function typeLabel(entryType) {
  const labels = {
    project_closeout: 'closeout',
    project_completion: 'completion',
    session_handover: 'handover',
    handover_closeout: 'archived',
  }
  return labels[entryType] || entryType?.replace(/_/g, ' ') || ''
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

<style scoped lang="scss">
@use '../../styles/design-tokens' as *;

.memories-scroll {
  max-height: 340px;
  overflow-y: auto;
}

.memory-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 9px 0;
  border-bottom: 1px solid $color-border-tertiary;
  cursor: pointer;
  transition: background $transition-fast;

  &:last-child {
    border-bottom: none;
  }

  &:hover {
    background: rgba(255, 255, 255, 0.02);
  }
}

.memory-icon {
  width: 24px;
  height: 24px;
  border-radius: $border-radius-sharp;
  display: grid;
  place-items: center;
  font-size: 12px;
  flex-shrink: 0;
  background: rgba(255, 195, 0, 0.1);
  color: $color-brand-yellow;
}

.memory-content {
  flex: 1;
  min-width: 0;
}

.memory-text {
  font-size: 0.75rem;
  line-height: 1.3;
  color: $color-text-primary;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.memory-meta {
  font-size: 0.58rem;
  color: var(--text-muted);
  font-family: 'IBM Plex Mono', monospace;
  margin-top: 2px;
}

.memory-type {
  padding: 1px 6px;
  border-radius: $border-radius-sharp;
  font-size: 0.52rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  flex-shrink: 0;
  margin-top: 2px;
}

.memory-type-dialog {
  padding: 2px 8px;
  border-radius: $border-radius-sharp;
  font-size: 0.6rem;
  font-weight: 500;
}

.no-data-text {
  font-size: 0.75rem;
  color: var(--text-muted);
  padding: 8px 0;
  text-align: center;
}
</style>
