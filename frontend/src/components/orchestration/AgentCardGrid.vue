<template>
  <div class="agent-grid-container" role="region" aria-label="Agent orchestration grid">
    <div class="agent-grid" :style="gridStyles">
      <!-- Orchestrator card always first -->
      <OrchestratorCard
        v-if="orchestrator"
        :orchestrator="orchestrator"
        :project="project"
        @copy-prompt="handleCopyPrompt"
        @close-project="handleCloseProject"
      />

      <!-- Regular agent cards (sorted by status priority) -->
      <AgentCard
        v-for="agent in sortedAgents"
        :key="agent.id"
        :agent="agent"
        :unread-count="getUnreadCount(agent.id)"
        :is-expanded="expandedAgentId === agent.id"
        tabindex="0"
        @copy-prompt="handleCopyPrompt"
        @toggle-messages="toggleAgentMessages"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useWebSocket } from '@/composables/useWebSocket'
import { useOrchestrationStore } from '@/stores/orchestration'
import AgentCard from '@/components/AgentCard.vue'
import OrchestratorCard from './OrchestratorCard.vue'

const props = defineProps({
  projectId: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['copy-prompt', 'close-project'])

// Status priority order for sorting (lower = higher priority)
const STATUS_ORDER = {
  'failed': 0,
  'blocked': 1,
  'working': 2,
  'review': 3,
  'preparing': 4,
  'waiting': 5,
  'complete': 6
}

// Store
const orchestrationStore = useOrchestrationStore()

// Reactive state
const expandedAgentId = ref(null)

// WebSocket setup
const { on, off } = useWebSocket()

// Computed properties
const orchestrator = computed(() => {
  return orchestrationStore.orchestrator
})

const regularAgents = computed(() => {
  return orchestrationStore.regularAgents
})

const sortedAgents = computed(() => {
  return [...regularAgents.value].sort((a, b) => {
    const priorityA = STATUS_ORDER[a.status] ?? 999
    const priorityB = STATUS_ORDER[b.status] ?? 999
    return priorityA - priorityB
  })
})

const project = computed(() => {
  return orchestrationStore.project
})

const gridStyles = computed(() => {
  return {
    display: 'grid',
    gap: '16px',
    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))'
  }
})

// Methods
const getUnreadCount = (agentId) => {
  return orchestrationStore.getUnreadCount(agentId)
}

const toggleAgentMessages = (agentId) => {
  if (expandedAgentId.value === agentId) {
    expandedAgentId.value = null
  } else {
    expandedAgentId.value = agentId
  }
}

const handleCopyPrompt = (data) => {
  emit('copy-prompt', data)
}

const handleCloseProject = () => {
  emit('close-project')
}

const handleAgentStatusUpdate = (event) => {
  orchestrationStore.handleAgentStatusUpdate(event)
}

// Lifecycle hooks
onMounted(() => {
  // Register WebSocket listener for agent status updates
  on('agent:status_changed', handleAgentStatusUpdate)

  // Load initial agent data
  loadAgents()
})

onUnmounted(() => {
  // Unregister WebSocket listener
  off('agent:status_changed', handleAgentStatusUpdate)
})

// Load agents from store
const loadAgents = async () => {
  try {
    await orchestrationStore.loadAgents(props.projectId)
  } catch (err) {
    console.error('[AgentCardGrid] Failed to load agents:', err)
  }
}
</script>

<style scoped>
.agent-grid-container {
  width: 100%;
  padding: 16px;
}

.agent-grid {
  /* Grid styles applied via computed gridStyles */
  width: 100%;
}

/* Responsive breakpoints matching test specifications */
@media (max-width: 600px) {
  .agent-grid {
    grid-template-columns: 1fr !important;
  }
}

@media (min-width: 601px) and (max-width: 767px) {
  .agent-grid {
    grid-template-columns: repeat(2, 1fr) !important;
  }
}

@media (min-width: 768px) and (max-width: 1199px) {
  .agent-grid {
    grid-template-columns: repeat(3, 1fr) !important;
  }
}

@media (min-width: 1200px) {
  .agent-grid {
    grid-template-columns: repeat(4, 1fr) !important;
  }
}

/* Accessibility improvements */
.agent-grid > * {
  outline: none;
}

.agent-grid > *:focus {
  outline: 2px solid #2196f3;
  outline-offset: 4px;
}
</style>
