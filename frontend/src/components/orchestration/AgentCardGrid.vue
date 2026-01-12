<template>
  <div class="agent-grid-container" role="region" aria-label="Agent orchestration grid">
    <!-- View Mode Toggle (Handover 0228) -->
    <v-row class="mb-4">
      <v-col cols="auto">
        <v-btn-toggle v-model="viewMode" mandatory color="primary" density="compact">
          <v-btn value="cards">
            <v-icon>mdi-view-grid</v-icon>
            <v-tooltip activator="parent" location="top">Card View</v-tooltip>
          </v-btn>
          <v-btn value="table">
            <v-icon>mdi-table</v-icon>
            <v-tooltip activator="parent" location="top">Table View</v-tooltip>
          </v-btn>
        </v-btn-toggle>
      </v-col>
    </v-row>

    <!-- Card View (EXISTING - enhanced with v-if) -->
    <div v-if="viewMode === 'cards'" class="agent-grid" :style="gridStyles">
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

    <!-- Table View (NEW - Handover 0228) -->
<AgentTableView
      v-else
      :agents="tableAgents"
      :using-claude-code-subagents="usingClaudeCodeSubagents"
      mode="jobs"
      @row-click="handleRowClick"
      @launch-agent="handleLaunchAgent"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useWebSocket } from '@/composables/useWebSocket'
import { useOrchestrationStore } from '@/stores/orchestration'
import { useAgentJobsStore } from '@/stores/agentJobs'
import AgentCard from '@/components/AgentCard.vue'
import OrchestratorCard from './OrchestratorCard.vue'
import AgentTableView from './AgentTableView.vue' // NEW - Handover 0228

const props = defineProps({
  projectId: {
    type: String,
    required: true,
  },
  usingClaudeCodeSubagents: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['copy-prompt', 'close-project', 'launch-agent']) // NEW - Handover 0228

// Status priority order for sorting (lower = higher priority)
const STATUS_ORDER = {
  failed: 0,
  blocked: 1,
  working: 2,
  review: 3,
  preparing: 4,
  waiting: 5,
  complete: 6,
}

// Store
const orchestrationStore = useOrchestrationStore()
const agentJobsStore = useAgentJobsStore()

// Reactive state
const expandedAgentId = ref(null)
const viewMode = ref('cards') // NEW - Handover 0228: Default to card view

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

// NEW - Handover 0228: Combined agents for table view
const allAgentsForTable = computed(() => {
  const agents = [...regularAgents.value]
  if (orchestrator.value) {
    // Include orchestrator in table view
    agents.unshift(orchestrator.value)
  }
  return agents
})

const tableAgents = computed(() => agentJobsStore.sortedAgents)

const gridStyles = computed(() => {
  return {
    display: 'grid',
    gap: '16px',
    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
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

/**
 * Handover 0229: Determine if agent can be launched
 * Terminal states: cannot be launched
 * Blocked state: cannot be launched
 * Claude Code mode: only orchestrator can be launched
 */
const canLaunchAgent = (agent) => {
  // Terminal states: cannot be launched
  const terminalStates = ['complete', 'failed', 'cancelled', 'decommissioned']
  if (terminalStates.includes(agent.status)) {
    return false
  }

  // Blocked state: cannot be launched
  if (agent.status === 'blocked') {
    return false
  }

  // Claude Code mode: only orchestrator can be launched
  if (props.usingClaudeCodeSubagents) {
    return agent.is_orchestrator || agent.agent_display_name === 'orchestrator'
  }

  // General CLI mode: all non-terminal agents can be launched
  return true
}

/**
 * Handover 0229: Determine if agent prompt can be copied
 * Decommissioned agents have no prompt
 * Claude Code mode: only orchestrator prompts can be copied
 */
const canCopyPrompt = (agent) => {
  // Decommissioned agents have no prompt
  if (agent.status === 'decommissioned') {
    return false
  }

  // Claude Code mode: only orchestrator prompts can be copied
  if (props.usingClaudeCodeSubagents) {
    return agent.is_orchestrator || agent.agent_display_name === 'orchestrator'
  }

  // General CLI mode: all agent prompts can be copied
  return true
}

const handleCopyPrompt = (data) => {
  emit('copy-prompt', data)
}

const handleCloseProject = () => {
  emit('close-project')
}

const handleAgentStatusUpdate = (event) => {
  orchestrationStore.handleAgentStatusUpdate(event)
  agentJobsStore.updateAgent(event)
}

// NEW - Handover 0228: Table view event handlers
const handleRowClick = (agent) => {
  // Expand agent messages or show details (reuse existing logic)
  toggleAgentMessages(agent.id)
}

const handleLaunchAgent = (agent) => {
  // Emit launch event (can be handled by parent component)
  emit('launch-agent', agent)
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

watch(
  allAgentsForTable,
  (agents) => {
    agentJobsStore.setAgents(agents)
  },
  { immediate: true, deep: true },
)

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
