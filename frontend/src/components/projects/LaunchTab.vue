<template>
  <div class="launch-tab-wrapper">
    <!-- Main Container (unified border) - buttons moved to ProjectTabs -->
    <div class="main-container">
      <div class="three-panels">
        <!-- Panel 1: Project Description -->
        <div class="panel project-description-panel">
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
        <div class="panel mission-panel">
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
        <div class="panel default-agent-panel">
          <div class="panel-header">Default agent</div>
          <div class="panel-content">
            <!-- Orchestrator Card -->
            <div class="orchestrator-card">
              <v-avatar :color="orchestratorAvatarColor" size="40" class="agent-avatar">
                <span class="orchestrator-text">Or</span>
              </v-avatar>
              <span class="agent-name">Orchestrator</span>
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
                >
                  <div class="agent-avatar" :style="{ background: getAgentColor(agent.agent_type) }">
                    {{ getAgentInitials(agent.agent_type) }}
                  </div>
                  <span class="agent-name">{{ agent.agent_type }}</span>
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
import AgentDetailsModal from '@/components/projects/AgentDetailsModal.vue'

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
const orchestratorAvatarColor = computed(() => '#d4a574') // $color-agent-orchestrator

/**
 * Filter out orchestrator from agents list (since it's shown in Default Agent)
 */
const nonOrchestratorAgents = computed(() => {
  return agents.value.filter(agent => agent.agent_type !== 'orchestrator')
})

/**
 * Get agent color based on type
 */
const getAgentColor = (agentType) => {
  const colors = {
    orchestrator: '#d4a574', // tan
    analyzer: '#e1564b',     // red
    implementor: '#3493bf',  // blue
    tester: '#d4a574',       // gold/tan variant
    researcher: '#27ae60',   // green
    reviewer: '#9b59b6'      // purple
  }
  return colors[agentType?.toLowerCase()] || '#666'
}

/**
 * Get agent initials
 */
const getAgentInitials = (agentType) => {
  if (!agentType) return '??'
  const type = agentType.toLowerCase()
  if (type === 'orchestrator') return 'Or'
  if (type === 'analyzer') return 'An'
  if (type === 'implementor') return 'Im'
  if (type === 'tester') return 'Te'
  if (type === 'researcher') return 'Re'
  if (type === 'reviewer') return 'Rv'
  return agentType.substring(0, 2).toUpperCase()
}

/**
 * WebSocket and Auth Setup
 */
const { on, off } = useWebSocket()
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
  // TODO: Implement agent editing functionality
  console.log('Edit agent:', agent)
  // For now, show a message that editing will be implemented
  alert('Agent editing functionality coming soon!')
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

  console.log('[LaunchTab] WebSocket listeners registered for project:', projectId.value)
  console.log('[LaunchTab] Current tenant key:', currentTenantKey.value)
})

onUnmounted(() => {
  // Clean up WebSocket listeners
  off('project:mission_updated', handleMissionUpdate)
  off('orchestrator:instructions_fetched', handleMissionUpdate)
  off('agent:created', handleAgentCreated)

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

    .agent-name {
      flex: 1;
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
