<template>
  <div class="launch-tab-wrapper">
    <!-- Top Action Bar (outside main container) -->
    <div class="top-action-bar">
      <v-btn
        class="stage-button"
        variant="outlined"
        color="yellow-darken-2"
        rounded
        :loading="loadingStageProject"
        @click="handleStage"
      >
        Stage project
      </v-btn>

      <span class="status-text">Waiting:</span>

      <v-btn
        class="launch-button"
        :disabled="!readyToLaunch"
        :color="readyToLaunch ? 'yellow-darken-2' : 'grey'"
        rounded
        @click="handleLaunch"
      >
        Launch jobs
      </v-btn>
    </div>

    <!-- Main Container (unified border) -->
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
              <v-avatar :color="orchestratorAvatarColor" size="32" class="agent-avatar">
                <span class="orchestrator-text">Or</span>
              </v-avatar>
              <span class="agent-name">Orchestrator</span>
              <v-icon size="small" class="lock-icon">mdi-lock</v-icon>
              <v-icon size="small" class="info-icon">mdi-information</v-icon>
            </div>

            <!-- Agent Team Section -->
            <div class="agent-team-section">
              <div class="agent-team-header">Agent Team</div>
              <div class="agent-team-list">
                <!-- Agent cards will populate here from WebSocket events -->
                <AgentCard
                  v-for="agent in agents"
                  :key="agent.agent_id || agent.job_id"
                  :agent="agent"
                  mode="launch"
                  :instance-number="getInstanceNumber(agent)"
                  @edit-mission="handleEditAgentMission"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

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
import AgentCard from '@/components/AgentCard.vue'
import { useWebSocket } from '@/composables/useWebSocket'
import { useUserStore } from '@/stores/user'
import api from '@/services/api'

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
  'stage-project',
  'launch-jobs',
  'cancel-staging',
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
const readyToLaunch = ref(false)
const showToast = ref(false)
const toastMessage = ref('')
const loadingStageProject = ref(false)

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
  readyToLaunch.value = true

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
 * Production-grade clipboard copy function
 */
async function copyPromptToClipboard(text) {
  if (!text) {
    toastMessage.value = 'No prompt to copy'
    showToast.value = true
    return false
  }

  try {
    // Try modern Clipboard API first
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text)
      return true
    }
  } catch (clipErr) {
    console.warn('[LaunchTab] Clipboard API failed, trying fallback:', clipErr)
  }

  // Fallback for HTTP
  try {
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.style.position = 'fixed'
    textarea.style.left = '-9999px'
    textarea.style.top = '0'
    document.body.appendChild(textarea)

    textarea.focus()
    textarea.select()
    textarea.setSelectionRange(0, textarea.value.length)

    const success = document.execCommand('copy')
    document.body.removeChild(textarea)

    if (success) return true
  } catch (err) {
    console.error('[LaunchTab] All copy methods failed:', err)
  }

  return false
}

/**
 * Handle Stage Project button click
 */
async function handleStage() {
  loadingStageProject.value = true

  try {
    // Generate thin client staging prompt
    const response = await api.prompts.staging(projectId.value, {
      tool: 'claude-code',
    })

    if (!response.data?.prompt) {
      throw new Error('Invalid response from staging endpoint')
    }

    const { prompt, estimated_prompt_tokens } = response.data

    // Copy to clipboard immediately
    const copied = await copyPromptToClipboard(prompt)

    if (copied) {
      toastMessage.value = 'Orchestrator prompt copied to clipboard!'
      showToast.value = true
    } else {
      alert(`Please manually copy this prompt:\n\n${prompt}`)
    }

    const lineCount = prompt.split('\n').length
    console.log('[LaunchTab] Thin client prompt copied:', {
      lines: lineCount,
      tokens: estimated_prompt_tokens,
    })

    emit('stage-project')
  } catch (err) {
    console.error('[LaunchTab] Failed to generate prompt:', err)
    toastMessage.value = `Staging failed: ${err.response?.data?.detail || err.message}`
    showToast.value = true
  } finally {
    loadingStageProject.value = false
  }
}

/**
 * Handle Launch jobs button click
 */
function handleLaunch() {
  emit('launch-jobs')
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
 * Lifecycle Hooks
 */
onMounted(() => {
  // Initialize from props if data exists
  if (props.project.mission) {
    console.log('[LaunchTab] Loading existing mission from props on mount')
    missionText.value = props.project.mission
    readyToLaunch.value = true
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
      readyToLaunch.value = true
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
    readyToLaunch.value = true
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
    readyToLaunch.value = false
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

  .top-action-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;

    .stage-button {
      text-transform: none;
      font-weight: 500;
    }

    .status-text {
      color: $color-text-highlight;
      font-style: italic;
      font-size: 20px;
      font-weight: 400;
    }

    .launch-button {
      text-transform: none;
      font-weight: 500;
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
          min-height: $spacing-panel-min-height;
          position: relative;
          color: $color-text-primary;
          font-size: $typography-panel-content-size;
          line-height: 1.6;

          .edit-icon {
            position: absolute;
            bottom: 16px;
            right: 16px;
            color: $color-text-tertiary;
          }

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

    .lock-icon,
    .info-icon {
      color: $color-text-tertiary;
      flex-shrink: 0;
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
      border-right: 2px solid rgba(255, 255, 255, 0.1);
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
  }
}
</style>
