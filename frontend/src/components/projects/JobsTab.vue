<template>
  <div class="jobs-tab" role="main" :aria-label="`Jobs view for project ${project.name}`">
    <!-- All Agents Complete Banner -->
    <v-alert
      v-if="allAgentsComplete"
      type="success"
      variant="tonal"
      class="jobs-tab__complete-banner mb-4"
      prominent
    >
      <v-icon start size="large">mdi-check-circle</v-icon>
      <div class="text-h6 font-weight-bold">
        All agents report complete
      </div>
      <p class="text-body-2 mb-0 mt-1">
        All agent tasks have been completed successfully. Review the results and proceed with closeout.
      </p>
    </v-alert>

    <!-- Main 2-Column Layout -->
    <v-row class="jobs-tab__row" no-gutters>
      <!-- Left Column: Project Header + Agent Cards (60%) -->
      <v-col cols="12" lg="7" xl="8" class="jobs-tab__left-column">

        <!-- Agent Cards Container -->
        <div class="jobs-tab__agents-container">
          <div class="jobs-tab__agents-header mb-3">
            <div class="panel-header bg-success text-white">
              <v-icon size="small" class="flex-shrink-0">mdi-account-group</v-icon>
              <span class="flex-shrink-0">Active Agents</span>
              <v-chip size="x-small" color="white" text-color="success" class="font-weight-bold flex-shrink-0" density="compact">
                {{ sortedAgents.length }}
              </v-chip>
            </div>
          </div>

          <!-- Claude Code Subagent Mode Toggle (Handover 0105) -->
          <v-card class="claude-code-toggle mb-3" elevation="2">
            <div class="panel-header bg-primary text-white d-flex align-center">
              <v-icon class="mr-2">mdi-robot</v-icon>
              <span>Launch Mode</span>
            </div>
            <v-card-text class="pa-3">
              <v-switch
                v-model="usingClaudeCodeSubagents"
                color="orange"
                density="comfortable"
                hide-details
              >
                <template v-slot:label>
                  <div class="d-flex align-center">
                    <v-icon color="orange" class="mr-2">mdi-robot</v-icon>
                    <span class="font-weight-medium">Using Claude Code subagents</span>
                  </div>
                </template>
              </v-switch>
              <div class="text-caption text-grey mt-2 ml-8">
                {{ toggleHintText }}
              </div>
            </v-card-text>
          </v-card>

          <!-- Status Board Table (Handover 0240b) -->
          <AgentTableView
            :agents="sortedAgents"
            :using-claude-code-subagents="usingClaudeCodeSubagents"
            mode="jobs"
            @launch-agent="handleLaunchAgent"
            @row-click="handleViewDetails"
          />
        </div>
      </v-col>

      <!-- Right Column: Messages (40%) -->
      <v-col cols="12" lg="5" xl="4" class="jobs-tab__right-column">
        <div class="jobs-tab__messages-panel">
          <!-- Message Stream -->
          <MessageStream
            :messages="messages"
            :project-id="projectId"
            :auto-scroll="true"
            :loading="false"
            class="jobs-tab__message-stream"
          />

          <!-- Message Input (Sticky at bottom) -->
          <MessageInput
            :disabled="false"
            @send="handleSendMessage"
            class="jobs-tab__message-input"
          />
        </div>
      </v-col>
    </v-row>

    <!-- Execution Prompt Dialog removed: Launch Agent now copies prompt directly -->
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import AgentTableView from '@/components/orchestration/AgentTableView.vue'
import MessageStream from './MessageStream.vue'
import MessageInput from './MessageInput.vue'
import { api } from '@/services/api'
import { useToast } from '@/composables/useToast'

/**
 * JobsTab Component
 *
 * Production-grade implementation view for Handover 0077 showing active agent
 * work with real-time messaging and coordination.
 *
 * Features:
 * - 2-column layout: Agents (60%) | Messages (40%)
 * - Project header with ID display
 * - Green completion banner when all agents complete
 * - Horizontal scrollable agent cards with priority sorting
 * - Real-time message stream
 * - Sticky message input at bottom
 * - Keyboard navigation support
 * - Responsive design (stacks on mobile)
 * - ARIA labels for accessibility
 *
 * Agent Sorting Priority:
 * 1. Failed/Blocked (highest priority - float to top)
 * 2. Waiting (ready to launch)
 * 3. Working (actively running)
 * 4. Complete (lowest priority)
 *
 * @see handovers/0077_launch_jobs_dual_tab_interface.md
 */

const props = defineProps({
  /**
   * Project object
   * Fields: project_id, name, description
   */
  project: {
    type: Object,
    required: true,
    validator: (value) => {
      // Accept either project_id or id to support both shapes
      return (
        value &&
        typeof value === 'object' &&
        (('project_id' in value) || ('id' in value)) &&
        'name' in value
      )
    }
  },

  /**
   * Array of agent job objects
   * Each agent should have:
   * - job_id or agent_id: unique identifier
   * - agent_type: type (orchestrator, analyzer, implementor, etc.)
   * - status: waiting | working | complete | failed | blocked
   * - mission: mission text
   * - progress: 0-100 (for working agents)
   * - current_task: current task description (for working agents)
   * - block_reason: error message (for failed/blocked agents)
   * - messages: array of messages (optional)
   */
  agents: {
    type: Array,
    required: true,
    default: () => []
  },

  /**
   * Array of message objects
   * Each message should have:
   * - id: unique identifier
   * - from: 'agent' | 'developer'
   * - from_agent: sender agent type
   * - to_agent: recipient agent type (or null for broadcast)
   * - type: 'agent' | 'broadcast' | 'user'
   * - content: message text
   * - timestamp: ISO timestamp
   * - agent_type: agent type for chat head
   * - instance_number: instance number (optional)
   */
  messages: {
    type: Array,
    default: () => []
  },

  /**
   * Whether all agents have completed
   */
  allAgentsComplete: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits([
  'launch-agent',
  'view-details',
  'view-error',
  'closeout-project',
  'send-message'
])

/**
 * Composables
 */
const { showToast } = useToast()

/**
 * Claude Code Subagent Mode Toggle (Handover 0105)
 */
const usingClaudeCodeSubagents = ref(false)

/**
 * Project ID (supports either project_id or id)
 */
const projectId = computed(() => {
  return (
    (props.project && (props.project.project_id || props.project.id)) || 'Unknown'
  )
})

/**
 * Agent sorting priority map
 * Lower number = higher priority (appears first)
 */
const AGENT_PRIORITY = {
  failed: 1,
  blocked: 2,
  waiting: 3,
  working: 4,
  complete: 5
}

/**
 * Sort agents by priority (failed/blocked first, complete last)
 */
const sortedAgents = computed(() => {
  if (!props.agents || props.agents.length === 0) return []

  return [...props.agents].sort((a, b) => {
    const priorityA = AGENT_PRIORITY[a.status] || 999
    const priorityB = AGENT_PRIORITY[b.status] || 999

    // Primary sort: by priority
    if (priorityA !== priorityB) {
      return priorityA - priorityB
    }

    // Secondary sort: by agent type (orchestrator first)
    const isOrchestratorA = a.agent_type === 'orchestrator' ? 0 : 1
    const isOrchestratorB = b.agent_type === 'orchestrator' ? 0 : 1

    if (isOrchestratorA !== isOrchestratorB) {
      return isOrchestratorA - isOrchestratorB
    }

    // Tertiary sort: by agent_type alphabetically
    return (a.agent_type || '').localeCompare(b.agent_type || '')
  })
})

/**
 * Get instance number for agent
 * Counts how many agents of same type appear before this one
 */
function getInstanceNumber(agent) {
  if (!agent.agent_type) return 1

  const agentsOfSameType = props.agents.filter(a => a.agent_type === agent.agent_type)
  if (agentsOfSameType.length === 1) return 1

  const index = agentsOfSameType.findIndex(a => {
    return (a.job_id || a.agent_id) === (agent.job_id || agent.agent_id)
  })

  return index + 1
}

/**
 * Check if agent is orchestrator
 */
function isOrchestratorAgent(agent) {
  return agent.agent_type === 'orchestrator'
}

/**
 * Toggle hint text - explains mode behavior
 */
const toggleHintText = computed(() => {
  if (usingClaudeCodeSubagents.value) {
    return 'Claude Code subagent mode active - Launch only orchestrators. All other agents will run as Claude Code subagents.'
  } else {
    return 'Normal mode - All agents launch as independent MCP server instances.'
  }
})

/**
 * Determine if prompt button should be disabled for this agent
 * Only non-orchestrators are disabled when toggle is ON
 */
function shouldDisablePromptButton(agent) {
  if (!usingClaudeCodeSubagents.value) {
    return false // Normal mode - all enabled
  }

  // Claude Code mode - disable non-orchestrators
  return !isOrchestratorAgent(agent)
}

/**
 * Event handlers for agent actions
 */
async function handleLaunchAgent(agent) {
  try {
    let promptText = ''

    if (agent.agent_type === 'orchestrator') {
      // Orchestrator prompt depends on Claude Code subagent toggle
      const response = await api.prompts.execution(
        agent.job_id,
        usingClaudeCodeSubagents.value
      )
      promptText = response.data?.prompt || ''
    } else {
      // Specialist agent universal prompt
      const response = await api.prompts.agentPrompt(agent.job_id)
      promptText = response.data?.prompt || ''
    }

    if (!promptText) {
      throw new Error('No prompt text returned')
    }

    await copyToClipboard(promptText)
    showToast({ message: 'Launch prompt copied to clipboard', type: 'success', duration: 3000 })
  } catch (error) {
    console.error('[JobsTab] Failed to prepare launch prompt:', error)
    const msg = error.response?.data?.detail || error.message || 'Failed to prepare launch prompt'
    showToast({ message: msg, type: 'error', duration: 5000 })
  }
}

/**
 * Copy helper with fallback (works in non-secure contexts)
 */
async function copyToClipboard(text) {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      return await navigator.clipboard.writeText(text)
    }
  } catch (e) {
    // fall through to fallback
  }
  // Fallback: temporary textarea + execCommand
  const textArea = document.createElement('textarea')
  textArea.value = text
  textArea.style.position = 'fixed'
  textArea.style.left = '-9999px'
  textArea.style.top = '-9999px'
  document.body.appendChild(textArea)
  textArea.focus()
  textArea.select()
  try {
    document.execCommand('copy')
  } finally {
    document.body.removeChild(textArea)
  }
}

function handleViewDetails(agent) {
  console.log('[JobsTab] View details:', agent.agent_type)
  emit('view-details', agent)
}

function handleViewError(agent) {
  console.log('[JobsTab] View error:', agent.agent_type)
  emit('view-error', agent)
}

function handleCloseoutProject() {
  console.log('[JobsTab] Closeout project')
  emit('closeout-project')
}

/**
 * Handle orchestrator handover (Handover 0080a)
 */
function handleHandOver(agent) {
  console.log('[JobsTab] Hand over orchestrator:', agent.job_id)
  emit('hand-over', agent)
}

/**
 * Handle message sending
 */
function handleSendMessage(message, recipient) {
  console.log('[JobsTab] Send message:', { message, recipient })
  emit('send-message', message, recipient)
}
</script>

<style scoped lang="scss">
@use '@/styles/agent-colors.scss' as *;

.jobs-tab {
  width: 100%;
  height: 100%;
  padding: 16px;
  background: var(--color-bg-secondary, #fafafa);

  &__complete-banner {
    background: linear-gradient(135deg, rgba(76, 175, 80, 0.15) 0%, rgba(56, 142, 60, 0.1) 100%) !important;
    border: 2px solid #4caf50 !important;
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(76, 175, 80, 0.2);

    :deep(.v-alert__prepend) {
      color: #4caf50;
    }

    :deep(.v-alert__content) {
      color: rgba(0, 0, 0, 0.87);
    }
  }

  &__row {
    gap: 24px;
  }

  &__left-column {
    display: flex;
    flex-direction: column;
    padding-right: 12px;
  }

  &__right-column {
    display: flex;
    flex-direction: column;
    padding-left: 12px;
    border-left: 2px solid rgba(0, 0, 0, 0.06);
  }

  &__project-header {
    background: var(--color-bg-primary, #ffffff);
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);

    .project-id-code {
      font-family: 'Courier New', monospace;
      font-size: 12px;
      background: rgba(0, 0, 0, 0.05);
      padding: 2px 6px;
      border-radius: 4px;
    }
  }

  &__agents-container {
    position: relative;
    flex: 1;
    min-height: 300px;
  }

  &__agents-header {
    display: inline-block;

    .panel-header {
      display: inline-flex !important;
      flex-direction: row !important;
      align-items: center !important;
      flex-wrap: nowrap !important;
      gap: 6px !important;
      padding: 8px 10px !important;
      width: fit-content !important;
      border-radius: 4px;
      white-space: nowrap;
    }
  }

  /* Claude Code Toggle Card (Handover 0105) */
  .claude-code-toggle {
    border-radius: 8px;
    background: var(--color-bg-primary, #ffffff);
    border: 1px solid rgba(0, 0, 0, 0.08);
    border-left: 3px solid var(--agent-orchestrator-primary);
  }

  &__messages-panel {
    display: flex;
    flex-direction: column;
    height: 100%;
    background: var(--color-bg-primary, #ffffff);
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    overflow: hidden;
  }

  &__message-stream {
    flex: 1;
    min-height: 0;
  }

  &__message-input {
    flex-shrink: 0;
  }
}

/* Panel header styling (match LaunchTab) */
.panel-header {
  font-weight: 600;
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 12px 16px;
}

/* Execution Prompt Dialog (Handover 0109) */
.execution-prompt-textarea {
  font-family: 'Courier New', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.5;

  :deep(textarea) {
    font-family: inherit;
  }
}

/* Responsive Design */
@media (max-width: 1280px) {
  .jobs-tab {
    &__left-column {
      padding-right: 8px;
    }

    &__right-column {
      padding-left: 8px;
    }
  }
}

/* Tablet: Stack columns vertically */
@media (max-width: 1024px) {
  .jobs-tab {
    &__row {
      flex-direction: column;
    }

    &__left-column {
      padding-right: 0;
      margin-bottom: 24px;
    }

    &__right-column {
      padding-left: 0;
      border-left: none;
      border-top: 2px solid rgba(0, 0, 0, 0.06);
      padding-top: 24px;
    }

    &__messages-panel {
      min-height: 500px;
    }
  }
}

/* Mobile: Compact spacing */
@media (max-width: 768px) {
  .jobs-tab {
    padding: 12px;

    &__row {
      gap: 16px;
    }

    &__complete-banner {
      padding: 12px !important;

      :deep(.text-h6) {
        font-size: 1rem;
      }

      :deep(.text-body-2) {
        font-size: 0.875rem;
      }
    }

    &__project-header {
      padding: 12px;

      .text-h5 {
        font-size: 1.25rem;
      }
    }

    &__messages-panel {
      min-height: 400px;
    }
  }
}

/* Small mobile: Further compact */
@media (max-width: 600px) {
  .jobs-tab {
    padding: 8px;
  }
}

/* Accessibility: High Contrast Mode */
@media (prefers-contrast: high) {
  .jobs-tab {
    &__project-header,
    &__messages-panel {
      border: 2px solid currentColor;
    }

    &__complete-banner {
      border-width: 3px !important;
    }

    &__right-column {
      border-left-width: 3px;
    }
  }
}

/* Dark Theme Optimization */
.v-theme--dark {
  .jobs-tab {
    background: var(--color-bg-elevated, #1e1e1e);

    &__project-header,
    &__messages-panel {
      background: var(--color-bg-primary, #121212);
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
    }

    &__complete-banner {
      background: linear-gradient(135deg, rgba(76, 175, 80, 0.25) 0%, rgba(56, 142, 60, 0.2) 100%) !important;
      border-color: #66bb6a !important;
    }

    &__right-column {
      border-left-color: rgba(255, 255, 255, 0.12);
    }

    .project-id-code {
      background: rgba(255, 255, 255, 0.1);
    }
  }
}

/* Light Theme Optimization */
.v-theme--light {
  .jobs-tab {
    background: #fafafa;

    &__project-header,
    &__messages-panel {
      background: #ffffff;
    }

    &__right-column {
      border-left-color: rgba(0, 0, 0, 0.06);
    }
  }
}

/* Print Styles */
@media print {
  .jobs-tab {
    &__complete-banner {
      border: 2px solid #4caf50 !important;
      background: #e8f5e9 !important;
      color: #000 !important;
    }

    &__messages-panel {
      border: 1px solid #ccc;
      page-break-inside: avoid;
    }
  }
}
</style>
