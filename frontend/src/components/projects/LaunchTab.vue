<template>
  <div class="launch-tab-wrapper">
    <!-- Execution Mode Toggle (Handover 0333 Phase 1) -->
    <!-- Lock added in Handover 0343 -->
    <div
      class="execution-mode-toggle-bar"
      :class="{ 'toggle-locked': isExecutionModeLocked }"
      data-testid="execution-mode-toggle"
      @click="toggleExecutionMode"
    >
      <span class="toggle-label">Execution Mode</span>
      <span class="toggle-options">
        <span :class="{ active: !usingClaudeCodeSubagents }">Multi-Terminal</span>
        <span class="toggle-separator">/</span>
        <span :class="{ active: usingClaudeCodeSubagents }">Claude Code CLI</span>
      </span>
      <v-tooltip location="bottom">
        <template v-slot:activator="{ props: tooltipProps }">
          <v-icon v-bind="tooltipProps" size="small" class="ml-1 help-icon">mdi-help-circle-outline</v-icon>
        </template>
        <span>Multi-Terminal: Manually launch each agent in separate terminals. Claude Code CLI: Orchestrator spawns specialists via Task tool.</span>
      </v-tooltip>
      <v-icon v-if="isExecutionModeLocked" size="small" class="ml-1 lock-icon">mdi-lock</v-icon>
      <div class="toggle-indicator" data-testid="execution-mode-indicator" :class="{ active: usingClaudeCodeSubagents }"></div>
    </div>

    <!-- Main Container (unified border) - buttons moved to ProjectTabs -->
    <div class="main-container">
      <div class="three-panels">
        <!-- Panel 1: Project Description -->
        <div class="panel project-description-panel" data-testid="description-panel">
          <div class="panel-header">Project Description</div>
          <div class="panel-content">
            <p class="description-text">{{ project.description || 'No description available' }}</p>
            <v-btn
              icon="mdi-pencil"
              size="small"
              variant="text"
              class="edit-icon"
              @click="editDescription"
            />
          </div>
        </div>

        <!-- Panel 2: Orchestrator Mission -->
        <div class="panel mission-panel" data-testid="mission-panel">
          <div class="panel-header">Orchestrator Generated Mission</div>
          <div class="panel-content">
            <div v-if="!missionText" class="empty-state">
              <v-icon size="80" class="empty-icon">mdi-file-document-outline</v-icon>
            </div>
            <div v-else class="mission-content">
              {{ missionText }}
            </div>
          </div>
        </div>

        <!-- Panel 3: Default Agent -->
        <div class="panel default-agent-panel" data-testid="agents-panel">
          <div class="panel-header">Default agent</div>
          <div class="panel-content">
            <!-- Orchestrator Card -->
            <div class="orchestrator-card">
              <v-avatar :color="orchestratorAvatarColor" size="40" class="agent-avatar">
                <span class="orchestrator-text">OR</span>
              </v-avatar>
              <div class="orchestrator-info">
                <span class="agent-name">ORCHESTRATOR</span>
                <div v-if="currentOrchestrator" class="text-caption text-medium-emphasis">
                  Instance #{{ currentOrchestrator.instance_number || 1 }} •
                  ID: <code data-testid="orchestrator-agent-id">{{ currentOrchestrator.agent_id?.slice(0, 8) }}...</code>
                </div>
              </div>
              <v-icon size="small" class="eye-icon" title="View orchestrator details (read-only)">mdi-eye</v-icon>
              <v-icon
                size="small"
                class="info-icon"
                role="button"
                tabindex="0"
                title="View orchestrator template"
                @click="handleOrchestratorInfo"
                @keydown.enter="handleOrchestratorInfo"
              >
                mdi-information
              </v-icon>
            </div>

            <!-- Agent Team Section -->
            <div class="agent-team-section">
              <div class="agent-team-header">Agent Team</div>
              <div class="agent-team-list">
                <!-- Slim agent cards (exclude orchestrator as it's shown above) -->
                <div
                  v-for="agent in nonOrchestratorAgents"
                  :key="agent.agent_id || agent.job_id"
                  class="agent-slim-card"
                  data-testid="agent-card"
                  :data-agent-type="agent.agent_type"
                >
                  <div class="agent-avatar" :style="{ background: getAgentColor(agent.agent_type) }">
                    {{ getAgentInitials(agent.agent_type) }}
                  </div>
                  <span class="agent-name" data-testid="agent-name">{{ agent.agent_type?.toUpperCase() || '' }}</span>
                  <span class="agent-type" data-testid="agent-type" style="display: none;">{{ agent.agent_type || '' }}</span>
                  <span class="status-chip" data-testid="status-chip" style="display: none;">{{ agent.status || 'pending' }}</span>
                  <v-icon
                    size="small"
                    class="edit-icon"
                    role="button"
                    tabindex="0"
                    title="Edit agent configuration"
                    @click="handleAgentEdit(agent)"
                    @keydown.enter="handleAgentEdit(agent)"
                  >mdi-pencil</v-icon>
                  <v-icon
                    size="small"
                    class="info-icon"
                    role="button"
                    tabindex="0"
                    title="View agent template"
                    @click="handleAgentInfo(agent)"
                    @keydown.enter="handleAgentInfo(agent)"
                  >mdi-information</v-icon>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Agent Details Modal -->
    <AgentDetailsModal
      v-model="showDetailsModal"
      :agent="selectedAgent"
    />

    <!-- Agent Mission Edit Modal -->
    <AgentMissionEditModal
      v-model="showMissionEditModal"
      :agent="selectedAgentForEdit"
      @mission-updated="handleMissionUpdated"
    />

    <!-- Toast Notification -->
    <v-snackbar v-model="showToast" :timeout="3000" color="success" location="top">
      <v-icon start>mdi-check-circle</v-icon>
      {{ toastMessage }}
      <template #actions>
        <v-btn variant="text" @click="showToast = false"> Close </v-btn>
      </template>
    </v-snackbar>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useWebSocket } from '@/composables/useWebSocket'
import { useUserStore } from '@/stores/user'
import { useToast } from '@/composables/useToast'
import AgentDetailsModal from '@/components/projects/AgentDetailsModal.vue'
import AgentMissionEditModal from '@/components/projects/AgentMissionEditModal.vue'

/**
 * LaunchTab Component - Complete Rewrite (Handover 0241)
 *
 * Exact match to screenshot design:
 * - Top action bar with stage button (left), status text (center), launch button (right)
 * - Main container with unified border and rounded corners
 * - Three equal panels: Project Description, Orchestrator Mission, Default Agent
 * - Dark navy background, tan orchestrator avatar, yellow buttons
 */

const props = defineProps({
  project: {
    type: Object,
    required: true,
    validator: (value) => {
      return value && typeof value === 'object' && ('id' in value || 'project_id' in value)
    },
  },
  orchestrator: {
    type: Object,
    default: null,
  },
  isStaging: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits([
  'edit-description',
  'edit-mission',
  'execution-mode-changed', // Handover 0335: Notify parent when execution mode changes
  'edit-agent-mission',
])

/**
 * Project ID from props
 */
const projectId = computed(() => {
  const id = props.project?.id
  if (!id) {
    console.error('[LaunchTab] Project missing ID field')
    throw new Error('Invalid project: missing ID')
  }
  return id
})

/**
 * Orchestrator avatar color (from design tokens)
 */
const orchestratorAvatarColor = computed(() => '#D4A574') // Tan/Beige from branding guide

/**
 * Filter out orchestrator from agents list (since it's shown in Default Agent)
 */
const nonOrchestratorAgents = computed(() => {
  return agents.value.filter(agent => agent.agent_type !== 'orchestrator')
})

/**
 * Get current orchestrator execution (most recent instance)
 */
const currentOrchestrator = computed(() => {
  if (!agents.value || agents.value.length === 0) return null

  // Find orchestrator jobs
  const orchestrators = agents.value
    .filter(agent => agent.agent_type === 'orchestrator')
    .sort((a, b) => (b.instance_number || 0) - (a.instance_number || 0))

  return orchestrators[0] || null
})

/**
 * Check if execution mode is locked (Handover 0343)
 * Execution mode is locked when orchestrator has generated a mission
 * (missionText exists = staging has occurred)
 */
const isExecutionModeLocked = computed(() => {
  return Boolean(missionText.value)
})

/**
 * Get agent color based on type
 */
const getAgentColor = (agentType) => {
  const colors = {
    orchestrator: '#D4A574', // Tan/Beige - Project coordination
    analyzer: '#E74C3C',     // Red - Analysis & research
    implementer: '#3498DB',  // Blue - Code implementation
    implementor: '#3498DB',  // Blue - Code implementation (alias)
    tester: '#FFC300',       // Yellow - Testing & QA
    reviewer: '#9B59B6',     // Purple - Code review
    documenter: '#27AE60',   // Green - Documentation
    researcher: '#27AE60',   // Green - Research (alias)
  }
  return colors[agentType?.toLowerCase()] || '#90A4AE' // Gray for custom agents
}

/**
 * Get agent initials
 */
const getAgentInitials = (agentType) => {
  if (!agentType) return '??'
  const type = agentType.toLowerCase()
  if (type === 'orchestrator') return 'OR'
  if (type === 'analyzer') return 'AN'
  if (type === 'implementer') return 'IM'
  if (type === 'implementor') return 'IM' // alias
  if (type === 'tester') return 'TE'
  if (type === 'reviewer') return 'RV'
  if (type === 'documenter') return 'DO'
  if (type === 'researcher') return 'RE'
  return agentType.substring(0, 2).toUpperCase()
}

/**
 * WebSocket and Auth Setup
 */
const { on, off } = useWebSocket()
const { showToast: showToastNotification } = useToast()
const userStore = useUserStore()
const currentTenantKey = computed(() => userStore.currentUser?.tenant_key)

/**
 * Component State
 */
const missionText = ref('')
const agentIds = ref(new Set())
const agents = ref([])
const showToast = ref(false)
const toastMessage = ref('')
const showDetailsModal = ref(false)
const selectedAgent = ref(null)
const showMissionEditModal = ref(false)
const selectedAgentForEdit = ref(null)

/**
 * Execution Mode Toggle (Handover 0333 Phase 1)
 */
const usingClaudeCodeSubagents = ref(false)

/**
 * Get instance number for multi-instance agents
 */
function getInstanceNumber(agent) {
  const agentType = agent.agent_type?.toLowerCase()
  if (!agentType) return 1

  const sameTypeAgents = agents.value.filter((a) => a.agent_type?.toLowerCase() === agentType)
  const index = sameTypeAgents.findIndex(
    (a) => (a.agent_id || a.job_id) === (agent.agent_id || agent.job_id),
  )

  return index + 1
}

/**
 * WebSocket Event Handlers
 */
const handleMissionUpdate = (data) => {
  console.log('[LaunchTab] Received project:mission_updated event:', data)

  // Multi-tenant isolation check
  if (!currentTenantKey.value || data.tenant_key !== currentTenantKey.value) {
    console.warn('[LaunchTab] Mission update rejected: tenant mismatch')
    return
  }

  // Project isolation check
  if (data.project_id !== projectId.value) {
    console.log('[LaunchTab] Mission update ignored: different project')
    return
  }

  // Update mission text reactively
  missionText.value = data.mission

  toastMessage.value = `Mission generated (${data.token_estimate || 0} tokens)`
  showToast.value = true

  console.log('[LaunchTab] Mission panel updated successfully')
}

const handleAgentCreated = (data) => {
  console.log('[LaunchTab] Received agent:created event:', data)

  // Multi-tenant isolation check
  if (!currentTenantKey.value || data.tenant_key !== currentTenantKey.value) {
    console.warn('[LaunchTab] Agent creation rejected: tenant mismatch')
    return
  }

  // Project isolation check
  if (data.project_id !== projectId.value) {
    console.log('[LaunchTab] Agent creation ignored: different project')
    return
  }

  // Support both payload shapes
  const nestedAgent = data.agent || {}
  const fallbackAgentId = data.agent_id || data.agent_job_id
  const agentId = nestedAgent.id || nestedAgent.job_id || fallbackAgentId

  if (!agentId) {
    console.warn('[LaunchTab] Agent creation ignored: no ID in payload')
    return
  }

  // Prevent duplicates
  if (agentIds.value.has(agentId)) {
    console.log('[LaunchTab] Agent already exists, skipping duplicate')
    return
  }

  // Build normalized agent object
  const normalizedAgent = {
    id: agentId,
    job_id: agentId,
    agent_type: nestedAgent.agent_type || data.agent_type || 'unknown',
    agent_name: nestedAgent.agent_name || data.agent_name || `Agent ${agentId.substring(0, 6)}`,
    status: nestedAgent.status || data.status || 'waiting',
  }

  // Add to Set and array
  agentIds.value.add(agentId)
  agents.value.push(normalizedAgent)

  const agentType = normalizedAgent.agent_type || 'Unknown'
  toastMessage.value = `Agent Selected - ${agentType} agent assigned to project`
  showToast.value = true

  console.log('[LaunchTab] Agent card added to UI. Total agents:', agents.value.length)
}

/**
 * Toggle Execution Mode (Handover 0333 Phase 1)
 * Switches between Multi-Terminal and Claude Code CLI modes
 * Handover 0343: Prevent toggle when orchestrator exists
 */
async function toggleExecutionMode() {
  // Handover 0343: Check if execution mode is locked
  if (isExecutionModeLocked.value) {
    showToastNotification({
      message: 'Execution mode locked after staging begins. Complete or cancel the orchestrator job to unlock.',
      type: 'warning',
      timeout: 3000
    })
    return
  }

  const newValue = !usingClaudeCodeSubagents.value
  const newMode = newValue ? 'claude_code_cli' : 'multi_terminal'

  // Optimistically update UI
  usingClaudeCodeSubagents.value = newValue

  try {
    // Persist to backend
    const projectId = props.project.id
    const { api } = await import('@/services/api')
    await api.projects.update(projectId, { execution_mode: newMode })

    // Handover 0335: Emit event so parent can update project prop
    // This ensures ProjectTabs.handleStageProject() uses fresh execution_mode
    emit('execution-mode-changed', newMode)

    showToastNotification({
      message: newValue
        ? 'Claude Code CLI mode enabled'
        : 'Manual mode enabled',
      type: 'info',
      timeout: 3000
    })
  } catch (error) {
    // Revert on failure
    usingClaudeCodeSubagents.value = !newValue
    console.error('Failed to update execution mode:', error)
    showToastNotification({
      message: 'Failed to save execution mode',
      type: 'error',
      timeout: 3000
    })
  }
}

/**
 * Handle Edit Description button
 */
function editDescription() {
  emit('edit-description')
}

/**
 * Handle Edit Agent Mission button
 */
function handleEditAgentMission(agent) {
  const agentId = agent.agent_id || agent.job_id
  const missionContent = agent.mission || ''
  emit('edit-agent-mission', agentId, missionContent)
}

/**
 * Handle Info icon click for Orchestrator
 */
function handleOrchestratorInfo() {
  selectedAgent.value = {
    agent_type: 'orchestrator',
    agent_name: 'Orchestrator',
    id: 'orchestrator',
  }
  showDetailsModal.value = true
}

/**
 * Handle Info icon click for Agent Team members
 */
function handleAgentInfo(agent) {
  selectedAgent.value = {
    ...agent,
    id: agent.id || agent.job_id,
  }
  showDetailsModal.value = true
}

/**
 * Handle Edit icon click for Agent Team members
 */
function handleAgentEdit(agent) {
  if (agent.agent_type === 'orchestrator') {
    // Orchestrators don't have editable missions
    showToastNotification({
      message: 'Orchestrator configuration cannot be edited here',
      type: 'info',
      timeout: 3000,
    })
    return
  }

  selectedAgentForEdit.value = agent
  showMissionEditModal.value = true
}

/**
 * Handle mission updated event from modal
 */
function handleMissionUpdated({ jobId, mission }) {
  // Update local agent data
  const agentIndex = agents.value.findIndex((a) => a.id === jobId)
  if (agentIndex !== -1) {
    agents.value[agentIndex].mission = mission
  }

  // Show success message
  showToastNotification({
    message: 'Agent mission updated successfully',
    type: 'success',
    timeout: 3000,
  })
}

/**
 * Handle agent mission updated via WebSocket (real-time updates)
 */
function handleAgentMissionUpdatedViaWebSocket(data) {
  console.log('[LaunchTab] Received agent:mission_updated event:', data)

  // Update agent in local state if it matches
  const agentIndex = agents.value.findIndex((a) => a.id === data.job_id)
  if (agentIndex !== -1) {
    agents.value[agentIndex].mission = data.mission

    // Show notification if not the current user's action
    // (if modal is closed, it means another user made the change)
    if (!showMissionEditModal.value) {
      showToastNotification({
        message: `Mission updated for ${data.agent_name}`,
        type: 'info',
        timeout: 3000,
      })
    }
  }
}

/**
 * Lifecycle Hooks
 */
onMounted(() => {
  // Initialize from props if data exists
  if (props.project.mission) {
    console.log('[LaunchTab] Loading existing mission from props on mount')
    missionText.value = props.project.mission
  }

  // Load agents from props if they exist
  if (
    props.project.agents &&
    Array.isArray(props.project.agents) &&
    props.project.agents.length > 0
  ) {
    console.log(
      '[LaunchTab] Loading existing agents from props on mount:',
      props.project.agents.length,
    )
    agents.value = props.project.agents

    // Populate agent IDs set to prevent duplicates
    props.project.agents.forEach((agent) => {
      const agentId = agent.id || agent.job_id
      if (agentId) {
        agentIds.value.add(agentId)
      }
    })
  }

  // Register WebSocket event listeners
  on('project:mission_updated', handleMissionUpdate)
  on('orchestrator:instructions_fetched', handleMissionUpdate)
  on('agent:created', handleAgentCreated)
  on('agent:mission_updated', handleAgentMissionUpdatedViaWebSocket)

  console.log('[LaunchTab] WebSocket listeners registered for project:', projectId.value)
  console.log('[LaunchTab] Current tenant key:', currentTenantKey.value)
})

onUnmounted(() => {
  // Clean up WebSocket listeners
  off('project:mission_updated', handleMissionUpdate)
  off('orchestrator:instructions_fetched', handleMissionUpdate)
  off('agent:created', handleAgentCreated)
  off('agent:mission_updated', handleAgentMissionUpdatedViaWebSocket)

  // Clear agent tracking Set
  agentIds.value.clear()

  console.log('[LaunchTab] Cleanup complete - WebSocket listeners removed, agent IDs cleared')
})

/**
 * Watchers
 */
watch(
  () => props.project.mission,
  (newMission) => {
    if (newMission) {
      missionText.value = newMission
    }
  },
)

watch(
  () => props.project.agents,
  (newAgents) => {
    if (newAgents && Array.isArray(newAgents)) {
      agents.value = newAgents
    }
  },
  { immediate: true, deep: true },
)

/**
 * Watch for execution_mode changes (Handover 0333 Phase 1)
 */
watch(
  () => props.project?.execution_mode,
  (newMode) => {
    usingClaudeCodeSubagents.value = newMode === 'claude_code_cli'
  },
  { immediate: true }
)

/**
 * Expose methods for parent component
 */
defineExpose({
  setMission: (mission) => {
    missionText.value = mission
  },
  addAgent: (agent) => {
    const agentId = agent.id || agent.job_id
    if (agentId && !agentIds.value.has(agentId)) {
      agentIds.value.add(agentId)
      agents.value.push({ ...agent, id: agentId })
    }
  },
  clearAgents: () => {
    agents.value = []
    agentIds.value.clear()
  },
  resetStaging: () => {
    missionText.value = ''
    agents.value = []
    agentIds.value.clear()
  },
})
</script>

<style scoped lang="scss">
@import '@/styles/design-tokens.scss';

.launch-tab-wrapper {
  padding: 20px;
  background: $color-background-primary;
  min-height: 100vh;

  .execution-mode-toggle-bar {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 20px;
    margin-bottom: 20px;
    border: 1px solid $color-text-secondary;
    border-radius: 8px;
    background: rgba(212, 165, 116, 0.05);
    cursor: pointer;
    transition: all 0.2s ease;

    &:hover {
      border-color: $color-text-highlight;
      background: rgba(212, 165, 116, 0.1);
    }

    // Handover 0343: Locked state styles
    &.toggle-locked {
      cursor: not-allowed;
      opacity: 0.6;

      &:hover {
        border-color: $color-text-secondary;
        background: rgba(212, 165, 116, 0.05);
      }
    }

    .toggle-label {
      font-weight: 600;
      color: $color-text-primary;
      font-size: 14px;
      min-width: 120px;
    }

    .toggle-options {
      display: flex;
      align-items: center;
      gap: 8px;
      color: $color-text-secondary;
      font-size: 13px;
      flex: 1;

      span {
        transition: color 0.2s ease;

        &.active {
          color: $color-text-highlight;
          font-weight: 600;
        }
      }

      .toggle-separator {
        color: $color-text-secondary;
      }
    }

    .help-icon {
      color: $color-text-secondary;
      margin-left: auto;
      flex-shrink: 0;
    }

    // Handover 0343: Lock icon styling
    .lock-icon {
      color: $color-text-secondary;
      flex-shrink: 0;
    }

    .toggle-indicator {
      width: 14px;
      height: 14px;
      border-radius: 50%;
      background: $color-text-secondary;
      flex-shrink: 0;
      transition: background-color 0.2s ease;

      &.active {
        background: $color-text-highlight;
      }
    }
  }

  .main-container {
    border: $border-width-standard solid $color-container-border;
    border-radius: $border-radius-large;
    padding: $spacing-container-padding;
    background: $color-container-background;

    .three-panels {
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: $spacing-panel-gap;

      .panel {
        .panel-header {
          font-size: $typography-panel-header-size;
          color: $color-text-secondary;
          margin-bottom: 16px;
          font-weight: $typography-font-weight-bold;
          text-transform: capitalize;
        }

        .panel-content {
          background: $color-panel-background;
          border-radius: $radius-medium;
          padding: $spacing-panel-content-padding;
          height: $spacing-panel-min-height; // Fixed height to lock all panels same size
          position: relative;
          color: $color-text-primary;
          font-size: $typography-panel-content-size;
          line-height: 1.6;
          overflow-y: auto; // Enable scrolling when content exceeds height


          .empty-state {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);

            .empty-icon {
              color: rgba(255, 255, 255, 0.15);
            }
          }

          .mission-content {
            white-space: pre-wrap;
            word-break: break-word;
            font-family: 'Courier New', Courier, monospace;
            font-size: 0.875rem;
            padding: 10px; // 10px buffer all around the text
            padding-right: 18px; // 10px + 8px for scrollbar

            /* Custom Scrollbar - match agent team list styling */
            &::-webkit-scrollbar {
              width: 8px;
            }

            &::-webkit-scrollbar-track {
              background: $color-scrollbar-track-background;
              border-radius: $radius-scrollbar;
            }

            &::-webkit-scrollbar-thumb {
              background: $color-scrollbar-thumb-background;
              border-radius: $radius-scrollbar;

              &:hover {
                background: $color-scrollbar-thumb-hover-background;
              }
            }

            /* Firefox scrollbar */
            scrollbar-color: $color-scrollbar-thumb-background $color-scrollbar-track-background;
            scrollbar-width: thin;
          }

          .description-text {
            line-height: 1.6;
            white-space: pre-wrap;
            word-break: break-word;
          }
        }
      }
    }
  }

  .orchestrator-card {
    display: flex;
    align-items: center;
    gap: 12px;
    border: $border-width-standard solid $color-text-highlight;
    border-radius: $border-radius-pill;
    padding: 12px 20px;
    margin-bottom: 20px;

    .agent-avatar {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    .orchestrator-text {
      color: $color-avatar-text-light;
      font-weight: $typography-font-weight-bold;
      font-size: 14px;
    }

    .orchestrator-info {
      display: flex;
      flex-direction: column;
      gap: 2px;
      flex: 1;

      code {
        font-family: 'Roboto Mono', monospace;
        font-size: 0.7rem;
        background: rgba(0, 0, 0, 0.05);
        padding: 1px 4px;
        border-radius: 2px;
      }
    }

    .agent-name {
      color: $color-text-primary;
      font-size: $typography-font-size-body;
    }

    .eye-icon {
      color: $color-text-secondary;  // Changed from tertiary to match edit-icon
      flex-shrink: 0;
      margin-right: 4px;  // Reduced to 4px for tighter spacing
    }

    .info-icon {
      color: $color-text-secondary;  // Changed from tertiary to match other icons
      flex-shrink: 0;
      cursor: pointer;
      transition: color 0.2s ease;

      &:hover {
        color: $color-text-highlight;
      }
    }
  }

  .agent-team-section {
    .agent-team-header {
      font-size: $typography-panel-header-size;
      color: $color-text-secondary;
      margin-bottom: 16px;
      font-weight: $typography-font-weight-bold;
      text-transform: capitalize;
    }

    .agent-team-list {
      min-height: 200px;
      padding-right: 8px;
      overflow-y: auto;
      max-height: 350px;

      /* Custom Scrollbar */
      &::-webkit-scrollbar {
        width: 8px;
      }

      &::-webkit-scrollbar-track {
        background: $color-scrollbar-track-background;
        border-radius: $radius-scrollbar;
      }

      &::-webkit-scrollbar-thumb {
        background: $color-scrollbar-thumb-background;
        border-radius: $radius-scrollbar;

        &:hover {
          background: $color-scrollbar-thumb-hover-background;
        }
      }
    }

    // Slim agent card (matches orchestrator card style)
    .agent-slim-card {
      display: flex;
      align-items: center;
      gap: 12px;
      border: 2px solid $color-text-highlight; // yellow border
      border-radius: $border-radius-pill; // 24px pill shape
      padding: 12px 20px;
      margin-bottom: 12px;
      background: transparent;

      .agent-avatar {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: $typography-font-weight-bold;
        font-size: 14px;
      }

      .agent-name {
        flex: 1;
        color: $color-text-primary;
        font-size: $typography-font-size-body;
        text-transform: capitalize;
      }

      .edit-icon {
        color: $color-text-secondary;
        flex-shrink: 0;
        cursor: pointer;
        transition: color 0.2s ease;
        margin-right: 4px;  // Reduced from 8px to match orchestrator

        &:hover {
          color: $color-text-highlight;
        }
      }

      .info-icon {
        color: $color-text-secondary;
        flex-shrink: 0;
        cursor: pointer;
        transition: color 0.2s ease;

        &:hover {
          color: $color-text-highlight;
        }
      }
    }
  }
}
</style>
