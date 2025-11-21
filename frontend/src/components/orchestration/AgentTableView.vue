<template>
  <v-data-table
    :headers="headers"
    :items="agents"
    :sort-by="[{ key: 'status', order: 'asc' }]"
    item-key="job_id"
    class="agent-table-view"
    hover
    @click:row="handleRowClick"
  >
    <!-- Agent Type Column -->
    <template #item.agent_type="{ item }">
      <div class="d-flex align-center">
        <v-avatar :color="getAgentTypeColor(item.agent_type)" size="32" class="mr-2">
          <span class="text-caption font-weight-bold white--text">
            {{ getAgentAbbreviation(item.agent_type) }}
          </span>
        </v-avatar>
        <span class="text-capitalize">{{ item.agent_type }}</span>
      </div>
    </template>

    <!-- Status Column -->
    <template #item.status="{ item }">
      <v-chip :color="getStatusColor(item.status)" size="small">
        {{ item.status }}
      </v-chip>
    </template>

    <!-- Messages Column -->
    <template #item.messages="{ item }">
      <div class="d-flex gap-1">
        <v-chip
          v-if="getMessageCounts(item).unread > 0"
          color="error"
          size="x-small"
          prepend-icon="mdi-message-badge"
        >
          {{ getMessageCounts(item).unread }}
        </v-chip>
        <v-chip
          v-if="getMessageCounts(item).acknowledged > 0"
          color="success"
          size="x-small"
          prepend-icon="mdi-check-all"
        >
          {{ getMessageCounts(item).acknowledged }}
        </v-chip>
        <span v-if="getMessageCounts(item).total === 0" class="text-grey">—</span>
      </div>
    </template>

    <!-- Health Column -->
    <template #item.health_status="{ item }">
      <v-icon :color="getHealthColor(item.health_status)" size="small">
        {{ getHealthIcon(item.health_status) }}
      </v-icon>
    </template>

    <!-- Actions Column -->
    <template #item.actions="{ item }">
      <div class="d-flex gap-1">
        <!-- Launch button for waiting agents -->
        <v-btn
          v-if="mode === 'jobs' && item.status === 'waiting'"
          icon="mdi-rocket-launch"
          size="x-small"
          variant="text"
          :color="canLaunchAgent(item) ? 'primary' : 'grey'"
          :disabled="!canLaunchAgent(item)"
          @click.stop="$emit('launch-agent', item)"
        >
          <v-icon>mdi-rocket-launch</v-icon>
          <v-tooltip activator="parent" location="top">
            <span v-if="!canLaunchAgent(item) && usingClaudeCodeSubagents">
              Disabled in Claude Code mode (non-orchestrator)
            </span>
            <span v-else>
              Launch Agent
            </span>
          </v-tooltip>
        </v-btn>

        <!-- View details for working agents -->
        <v-btn
          v-if="mode === 'jobs' && item.status === 'working'"
          icon="mdi-information"
          size="x-small"
          variant="text"
          color="primary"
          @click.stop="$emit('row-click', item)"
        >
          <v-icon>mdi-information</v-icon>
          <v-tooltip activator="parent" location="top">View Details</v-tooltip>
        </v-btn>

        <!-- View error for failed/blocked agents -->
        <v-btn
          v-if="mode === 'jobs' && (item.status === 'failed' || item.status === 'blocked')"
          icon="mdi-alert-circle"
          size="x-small"
          variant="text"
          :color="item.status === 'failed' ? 'error' : 'warning'"
          @click.stop="$emit('row-click', item)"
        >
          <v-icon>mdi-alert-circle</v-icon>
          <v-tooltip activator="parent" location="top">View Error</v-tooltip>
        </v-btn>

        <!-- Complete status -->
        <v-chip v-if="mode === 'jobs' && item.status === 'complete'" color="success" size="x-small">
          <v-icon start size="x-small">mdi-check-circle</v-icon>
          Complete
        </v-chip>
      </div>
    </template>

    <!-- No Data State -->
    <template #no-data>
      <div class="text-center py-8">
        <v-icon size="64" color="grey-lighten-1">mdi-table-off</v-icon>
        <p class="text-grey mt-4">No agents to display</p>
      </div>
    </template>
  </v-data-table>
</template>

<script setup>
import { computed } from 'vue'
import { useAgentData } from '@/composables/useAgentData'

/**
 * AgentTableView Component
 *
 * Provides a table view for agents using Vuetify's v-data-table.
 * Reuses useAgentData composable for shared logic with card view.
 *
 * Handover 0228: StatusBoardTable Component
 *
 * Props:
 * - agents: Array of agent job objects
 * - mode: 'launch' | 'jobs' (determines action buttons)
 *
 * Emits:
 * - row-click: When user clicks on a table row
 * - launch-agent: When user clicks launch button
 */

const props = defineProps({
  agents: {
    type: Array,
    required: true,
    default: () => [],
  },
  mode: {
    type: String,
    default: 'jobs',
    validator: (value) => ['launch', 'jobs'].includes(value),
  },
  usingClaudeCodeSubagents: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['row-click', 'launch-agent'])

// Reuse shared logic from composable (NO DUPLICATION)
const {
  getStatusColor,
  getAgentTypeColor,
  getAgentAbbreviation,
  getMessageCounts,
  getHealthColor,
  getHealthIcon,
} = useAgentData(computed(() => props.agents))

// Table headers configuration
const headers = [
  { title: 'Agent Type', key: 'agent_type', sortable: true },
  { title: 'Agent Name', key: 'agent_name', sortable: true },
  { title: 'Status', key: 'status', sortable: true },
  { title: 'Messages', key: 'messages', sortable: false },
  { title: 'Health', key: 'health_status', sortable: true },
  { title: 'Actions', key: 'actions', sortable: false },
]

// Handle row click event
function handleRowClick(event, { item }) {
  emit('row-click', item)
}

/**
 * Handover 0229: Determine if agent can be launched
 * Terminal states: cannot be launched
 * Blocked state: cannot be launched
 * Claude Code mode: only orchestrator can be launched
 */
function canLaunchAgent(agent) {
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
    return agent.is_orchestrator || agent.agent_type === 'orchestrator'
  }

  // General CLI mode: all non-terminal agents can be launched
  return true
}

/**
 * Handover 0229: Determine if agent prompt can be copied
 * Decommissioned agents have no prompt
 * Claude Code mode: only orchestrator prompts can be copied
 */
function canCopyPrompt(agent) {
  // Decommissioned agents have no prompt
  if (agent.status === 'decommissioned') {
    return false
  }

  // Claude Code mode: only orchestrator prompts can be copied
  if (props.usingClaudeCodeSubagents) {
    return agent.is_orchestrator || agent.agent_type === 'orchestrator'
  }

  // General CLI mode: all agent prompts can be copied
  return true
}
</script>

<style scoped>
.agent-table-view :deep(tbody tr) {
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.agent-table-view :deep(tbody tr:hover) {
  background-color: rgba(var(--v-theme-primary), 0.05);
}

.agent-table-view :deep(.v-data-table__th) {
  font-weight: 600 !important;
  background-color: rgba(0, 0, 0, 0.02);
}

/* Ensure proper spacing for action buttons */
.agent-table-view :deep(.v-data-table__td) {
  padding: 12px 16px;
}

/* Align health icons to center */
.agent-table-view :deep([data-v-for-health]) {
  display: flex;
  justify-content: center;
}

/* Handover 0229: Visual feedback for disabled rows in Claude Code mode */
.agent-table-view :deep(.disabled-agent-row) {
  opacity: 0.6;
  background-color: rgba(0, 0, 0, 0.02);
}

.agent-table-view :deep(.disabled-agent-row:hover) {
  background-color: rgba(0, 0, 0, 0.04) !important;
}

/* Handover 0229: Disabled action buttons */
.agent-table-view :deep(.v-btn:disabled) {
  opacity: 0.4;
}

.agent-table-view :deep(.v-btn:disabled .v-icon) {
  color: grey !important;
}
</style>
