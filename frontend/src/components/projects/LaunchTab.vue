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
            <!-- Orchestrator Card (Handover 0506: Status-aware display) -->
            <div class="orchestrator-card" :class="{ 'orchestrator-complete': needsOrchestratorRelaunch }">
              <v-avatar :color="orchestratorAvatarColor" size="40" class="agent-avatar">
                <span class="orchestrator-text">OR</span>
              </v-avatar>
              <div class="orchestrator-info">
                <span class="agent-name">ORCHESTRATOR</span>
                <div v-if="currentOrchestrator" class="text-caption text-medium-emphasis">
                  Instance #{{ currentOrchestrator.instance_number || 1 }} •
                  <span class="status-text" :class="'status-' + currentOrchestrator.status">
                    {{ currentOrchestrator.status }}
                  </span>
                  •
                  Agent ID:
                  <code data-testid="orchestrator-agent-id">
                    {{ (currentOrchestrator?.agent_id || currentOrchestrator?.job_id || '').slice(0, 8) }}...
                  </code>
                </div>
                <div v-else class="text-caption text-medium-emphasis">
                  No orchestrator - click Launch to create one
                </div>
              </div>
              <!-- Re-launch button when orchestrator is complete/null (Handover 0506) -->
              <v-btn
                v-if="needsOrchestratorRelaunch"
                icon="mdi-rocket-launch"
                size="small"
                variant="text"
                color="primary"
                title="Launch new orchestrator"
                class="relaunch-btn"
                data-testid="relaunch-orchestrator"
                @click="emit('launch-orchestrator')"
              />
              <v-icon v-else size="small" class="eye-icon" title="View orchestrator details (read-only)">mdi-eye</v-icon>
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
                  :key="agent.job_id || agent.agent_id || agent.id"
                  class="agent-slim-card"
                  data-testid="agent-card"
                  :data-agent-display-name="agent.agent_display_name"
                >
                  <div class="agent-avatar" :style="{ background: getAgentColor(agent.agent_name || agent.agent_display_name) }">
                    {{ getAgentInitials(agent.agent_display_name) }}
                  </div>
                  <span class="agent-name" data-testid="agent-name">{{ agent.agent_display_name?.toUpperCase() || '' }}</span>
                  <span class="agent-type" data-testid="agent-display-name" style="display: none;">{{ agent.agent_display_name || '' }}</span>
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
import { ref, computed, watch } from 'vue'
import api from '@/services/api'
import { useAgentJobs } from '@/composables/useAgentJobs'
import { useAgentJobsStore } from '@/stores/agentJobsStore'
import { useProjectStateStore } from '@/stores/projectStateStore'
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
  'launch-orchestrator', // Handover 0506: Re-launch orchestrator when complete/null
])

/**
 * Project ID from props
 */
const projectId = computed(() => {
  const id = props.project?.project_id || props.project?.id
  if (!id) {
    console.error('[LaunchTab] Project missing ID field')
    throw new Error('Invalid project: missing ID')
  }
  return id
})

/**
 * Filter out orchestrator from agents list (since it's shown in Default Agent)
 */
const nonOrchestratorAgents = computed(() => {
  return sortedJobs.value.filter((agent) => agent.agent_display_name !== 'orchestrator')
})

/**
 * Get current orchestrator execution (most recent instance)
 */
const currentOrchestrator = computed(() => {
  if (!sortedJobs.value || sortedJobs.value.length === 0) return null

  // Find orchestrator jobs
  const orchestrators = sortedJobs.value
    .filter((agent) => agent.agent_display_name === 'orchestrator')
    .sort((a, b) => (b.instance_number || 0) - (a.instance_number || 0))

  return orchestrators[0] || null
})

/**
 * Handover 0506: Check if orchestrator needs re-launch
 * True when orchestrator is null or in terminal state (complete/handed_over)
 */
const needsOrchestratorRelaunch = computed(() => {
  if (!currentOrchestrator.value) return true
  const terminalStates = ['complete', 'handed_over', 'failed', 'cancelled', 'decommissioned']
  return terminalStates.includes(currentOrchestrator.value.status)
})

/**
 * Orchestrator avatar color - always tan (agent's brand color)
 * Status is shown via text label, not avatar color
 */
const orchestratorAvatarColor = computed(() => '#D4A574') // Tan/Beige from branding guide

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
const getAgentColor = (displayName) => {
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
  return colors[displayName?.toLowerCase()] || '#90A4AE' // Gray for custom agents
}

/**
 * Get agent initials
 */
const getAgentInitials = (displayName) => {
  if (!displayName) return '??'
  const type = displayName.toLowerCase()
  if (type === 'orchestrator') return 'OR'
  if (type === 'analyzer') return 'AN'
  if (type === 'implementer') return 'IM'
  if (type === 'implementor') return 'IM' // alias
  if (type === 'tester') return 'TE'
  if (type === 'reviewer') return 'RV'
  if (type === 'documenter') return 'DO'
  if (type === 'researcher') return 'RE'
  return displayName.substring(0, 2).toUpperCase()
}

const { showToast: showToastNotification } = useToast()

const projectStateStore = useProjectStateStore()
const missionText = computed(
  () => projectStateStore.getProjectState(projectId.value)?.mission || '',
)

const { sortedJobs } = useAgentJobs()
const agentJobsStore = useAgentJobsStore()

/**
 * Component State
 */
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
  const displayName = agent.agent_display_name?.toLowerCase()
  if (!displayName) return 1

  const sameTypeAgents = sortedJobs.value.filter((a) => a.agent_display_name?.toLowerCase() === displayName)
  const index = sameTypeAgents.findIndex(
    (a) => (a.agent_id || a.job_id) === (agent.agent_id || agent.job_id),
  )

  return index + 1
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
    await api.projects.update(projectId.value, { execution_mode: newMode })

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
    agent_display_name: 'orchestrator',
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
  if (agent.agent_display_name === 'orchestrator') {
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
  agentJobsStore.upsertJob?.({ job_id: jobId, mission })

  // Show success message
  showToastNotification({
    message: 'Agent mission updated successfully',
    type: 'success',
    timeout: 3000,
  })
}

/**
 * Watchers
 */
watch(missionText, (next, previous) => {
  if (next && !previous) {
    toastMessage.value = 'Mission generated'
    showToast.value = true
  }
})

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
</script>

<style scoped lang="scss">
@use '@/styles/design-tokens.scss' as *;

.launch-tab-wrapper {
  padding: 20px;
  background: rgb(var(--v-theme-background));
  min-height: 100vh;

  .execution-mode-toggle-bar {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 20px;
    margin-bottom: 20px;
    border: 1px solid rgba(var(--v-theme-on-surface), 0.3);
    border-radius: 8px;
    background: rgba(var(--v-theme-on-surface), 0.05);
    cursor: pointer;
    transition: all 0.2s ease;

    &:hover {
      border-color: $color-text-highlight;
      background: rgba(var(--v-theme-on-surface), 0.1);
    }

    // Handover 0343: Locked state styles
    &.toggle-locked {
      cursor: not-allowed;
      opacity: 0.6;

      &:hover {
        border-color: rgba(var(--v-theme-on-surface), 0.3);
        background: rgba(var(--v-theme-on-surface), 0.05);
      }
    }

    .toggle-label {
      font-weight: 600;
      color: rgb(var(--v-theme-on-surface));
      font-size: 14px;
      min-width: 120px;
    }

    .toggle-options {
      display: flex;
      align-items: center;
      gap: 8px;
      color: rgba(var(--v-theme-on-surface), 0.6);
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
        color: rgba(var(--v-theme-on-surface), 0.6);
      }
    }

    .help-icon {
      color: rgba(var(--v-theme-on-surface), 0.6);
      margin-left: auto;
      flex-shrink: 0;
    }

    // Handover 0343: Lock icon styling
    .lock-icon {
      color: rgba(var(--v-theme-on-surface), 0.6);
      flex-shrink: 0;
    }

    .toggle-indicator {
      width: 14px;
      height: 14px;
      border-radius: 50%;
      background: rgba(var(--v-theme-on-surface), 0.6);
      flex-shrink: 0;
      transition: background-color 0.2s ease;

      &.active {
        background: $color-text-highlight;
      }
    }
  }

  .main-container {
    border: $border-width-standard solid rgba(var(--v-theme-on-surface), 0.12);
    border-radius: $border-radius-large;
    padding: $spacing-container-padding;
    background: rgb(var(--v-theme-surface));

    .three-panels {
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: $spacing-panel-gap;

      .panel {
        .panel-header {
          font-size: $typography-panel-header-size;
          color: rgba(var(--v-theme-on-surface), 0.6);
          margin-bottom: 16px;
          font-weight: $typography-font-weight-bold;
          text-transform: capitalize;
        }

        .panel-content {
          background: rgba(var(--v-theme-on-surface), 0.05);
          border-radius: $radius-medium;
          padding: $spacing-panel-content-padding;
          height: $spacing-panel-min-height; // Fixed height to lock all panels same size
          position: relative;
          color: rgb(var(--v-theme-on-surface));
          font-size: $typography-panel-content-size;
          line-height: 1.6;
          overflow-y: auto; // Enable scrolling when content exceeds height


          .empty-state {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);

            .empty-icon {
              color: rgba(var(--v-theme-on-surface), 0.15);
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
    border: $border-width-standard solid #67bd6d; // Green for orchestrator
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
        background: rgba(var(--v-theme-on-surface), 0.1);
        padding: 1px 4px;
        border-radius: 2px;
      }
    }

    .agent-name {
      color: rgb(var(--v-theme-on-surface));
      font-size: $typography-font-size-body;
    }

    .eye-icon {
      color: rgba(var(--v-theme-on-surface), 0.6);
      flex-shrink: 0;
      margin-right: 4px;  // Reduced to 4px for tighter spacing
    }

    .info-icon {
      color: rgba(var(--v-theme-on-surface), 0.6);
      flex-shrink: 0;
      cursor: pointer;
      transition: color 0.2s ease;

      &:hover {
        color: $color-text-highlight;
      }
    }

    // Handover 0506: Re-launch button styling
    .relaunch-btn {
      flex-shrink: 0;
      margin-right: 4px;
    }

    // Handover 0506: Status text styling
    .status-text {
      text-transform: capitalize;
      font-weight: 500;

      &.status-waiting { color: #ffd700; }
      &.status-working { color: #D4A574; }
      &.status-complete { color: #67bd6d; }
      &.status-handed_over { color: #9e9e9e; }
      &.status-blocked { color: #ff9800; }
      &.status-failed { color: #e53935; }
      &.status-cancelled { color: #ff9800; }
    }

    // Handover 0506: Completed orchestrator styling
    &.orchestrator-complete {
      opacity: 0.8;
      border-color: #67bd6d;
    }
  }

  .agent-team-section {
    .agent-team-header {
      font-size: $typography-panel-header-size;
      color: rgba(var(--v-theme-on-surface), 0.6);
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
      border: 2px solid rgb(var(--v-theme-primary)); // Blue border (theme-aware)
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
        color: rgb(var(--v-theme-on-surface));
        font-size: $typography-font-size-body;
        text-transform: capitalize;
      }

      .edit-icon {
        color: rgba(var(--v-theme-on-surface), 0.6);
        flex-shrink: 0;
        cursor: pointer;
        transition: color 0.2s ease;
        margin-right: 4px;  // Reduced from 8px to match orchestrator

        &:hover {
          color: $color-text-highlight;
        }
      }

      .info-icon {
        color: rgba(var(--v-theme-on-surface), 0.6);
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
