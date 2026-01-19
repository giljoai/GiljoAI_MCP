<template>
  <v-dialog v-model="isVisible" max-width="700" persistent>
    <v-card>
      <!-- Header -->
      <v-card-title class="d-flex align-center">
        <v-avatar :color="getAgentColor(agent?.agent_name || agent?.agent_display_name)" size="32" class="agent-avatar mr-2">
          <span class="avatar-text">{{ getAgentAbbr(agent?.agent_name || agent?.agent_display_name) }}</span>
        </v-avatar>
        <span style="text-transform: capitalize">{{ agent?.agent_name || agent?.agent_display_name }}</span>&nbsp;- Assigned Job
        <v-spacer></v-spacer>
        <v-btn icon variant="text" @click="handleClose" aria-label="Close">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-divider />

      <!-- Agent Info -->
      <v-card-text v-if="agent" class="pb-0">
        <div class="text-caption text-medium-emphasis">
          <div><strong>Agent ID:</strong> {{ agent.agent_id }}</div>
          <div><strong>Job ID:</strong> {{ agent.job_id }}</div>
        </div>
      </v-card-text>

      <!-- Tabs -->
      <v-tabs v-model="activeTab" bg-color="transparent" class="px-4">
        <v-tab value="mission" data-test="job-tab-mission">Mission</v-tab>
        <v-tab value="plan" data-test="job-tab-plan">Plan ({{ todoItemsCount }})</v-tab>
      </v-tabs>

      <v-divider />

      <!-- Tab Content -->
      <v-card-text>
        <v-window v-model="activeTab">
          <!-- Mission Tab -->
          <v-window-item value="mission">
            <div v-if="agent" class="mission-section">
              <v-card variant="outlined" class="pa-3">
                <pre class="mission-text">{{ agent.mission || 'No mission assigned yet.' }}</pre>
              </v-card>
            </div>
            <div v-else class="text-center py-4 text-medium-emphasis">
              No agent selected
            </div>
          </v-window-item>

          <!-- Plan Tab -->
          <v-window-item value="plan">
            <div v-if="todoItems.length === 0" class="empty-state pa-4 text-center">
              <v-icon icon="mdi-checkbox-blank-outline" size="32" class="mb-2" />
              <div class="text-body-2 text-medium-emphasis">
                No tasks reported yet
              </div>
            </div>

            <div v-else class="todo-items-list">
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
          </v-window-item>
        </v-window>
      </v-card-text>

      <!-- Footer -->
      <v-card-actions>
        <v-spacer />
        <v-btn color="primary" @click="handleClose">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { computed, watch, ref } from 'vue'

// Props
const props = defineProps({
  show: {
    type: Boolean,
    required: true,
  },
  agent: {
    type: Object,
    default: null,
  },
  initialTab: {
    type: String,
    default: 'mission',
    validator: (value) => ['mission', 'plan'].includes(value),
  },
})

// Emits
const emit = defineEmits(['close'])

// State
const activeTab = ref(props.initialTab)

// Computed
const isVisible = computed({
  get: () => props.show,
  set: (value) => {
    if (!value) emit('close')
  },
})

const todoItems = computed(() =>
  props.agent?.todo_items && Array.isArray(props.agent.todo_items)
    ? props.agent.todo_items
    : [],
)

const todoItemsCount = computed(() => todoItems.value.length)

// Watch initialTab to update activeTab when modal opens
watch(
  () => props.initialTab,
  (newTab) => {
    activeTab.value = newTab
  },
  { immediate: true },
)

// Methods
function handleClose() {
  emit('close')
}

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

// Agent avatar helpers
function getAgentColor(agentName) {
  if (!agentName) return '#757575'
  const colors = [
    '#1976D2', '#388E3C', '#D32F2F', '#7B1FA2',
    '#F57C00', '#0097A7', '#C2185B', '#5D4037',
  ]
  const hash = agentName.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)
  return colors[hash % colors.length]
}

function getAgentAbbr(agentName) {
  if (!agentName) return '?'
  return agentName
    .split(/[\s_-]+/)
    .map(word => word[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
}
</script>

<style scoped>
.agent-avatar {
  border: 2px solid rgba(255, 255, 255, 0.2);
}

.avatar-text {
  font-size: 14px;
  font-weight: 600;
  color: white;
}

.mission-section {
  max-height: 400px;
  overflow-y: auto;
}

.mission-text {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: 'Roboto Mono', monospace;
  font-size: 0.875rem;
  line-height: 1.5;
  margin: 0;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 200px;
}

.todo-items-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 400px;
  overflow-y: auto;
  padding: 8px 0;
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
