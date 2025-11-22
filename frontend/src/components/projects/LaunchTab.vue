<template>
  <div class="launch-tab">
    <!-- 3-Column Layout -->
    <v-row class="launch-columns mb-6">
      <!-- Left Column: Action Buttons Panel -->
      <v-col cols="4" md="4" class="mb-4 mb-md-0 d-flex">
        <v-card elevation="2" class="action-panel pa-4">
          <!-- Stage Project Button (Initial State) -->
          <v-btn
            v-if="!isStaging && !readyToLaunch"
            block
            color="yellow-darken-2"
            variant="outlined"
            size="x-large"
            :loading="loadingStageProject"
            @click="handleStageProject"
            class="mb-3 stage-project-btn"
          >
            <v-icon start>mdi-clipboard-text</v-icon>
            Stage Project
          </v-btn>

          <!-- Launch Jobs Button (Ready State) -->
          <v-btn
            v-if="readyToLaunch"
            block
            color="yellow-darken-2"
            variant="flat"
            size="x-large"
            @click="handleLaunchJobs"
            class="mb-3 launch-jobs-btn"
          >
            <v-icon start>mdi-rocket-launch</v-icon>
            Launch Jobs
          </v-btn>

          <!-- Re-Stage Project Button (Visible during staging or when ready) -->
          <v-btn
            v-if="isStaging || readyToLaunch"
            block
            color="error"
            variant="outlined"
            size="large"
            @click="showCancelDialog = true"
          >
            <v-icon start>mdi-refresh</v-icon>
            Re-Stage Project
            <v-tooltip activator="parent" location="bottom">
              Use this when product vision, descriptions, or context configurations have changed.
              This will delete all staged missions and agent jobs, requiring complete re-orchestration.
              Note: This will incur new token costs as agents regenerate everything.
            </v-tooltip>
          </v-btn>

          <!-- Info Text -->
          <v-alert
            v-if="!isStaging && !readyToLaunch"
            type="info"
            variant="tonal"
            density="compact"
            class="mt-4"
          >
            Click to generate mission and spawn agents
          </v-alert>

          <v-alert
            v-if="readyToLaunch"
            type="success"
            variant="tonal"
            density="compact"
            class="mt-4"
          >
            Ready to launch! Review mission and agents below.
          </v-alert>
        </v-card>
      </v-col>

      <!-- Middle Column: Project Description Panel -->
      <v-col cols="4" md="4" class="mb-4 mb-md-0 d-flex">
        <v-card class="description-panel launch-panel d-flex flex-column" flat style="height: 100%;">
          <!-- Header -->
          <v-card-title class="panel-header bg-primary text-white text-center">
            <span>PROJECT DESCRIPTION</span>
          </v-card-title>

          <v-divider />

          <!-- Content -->
          <v-card-text class="pa-4 d-flex flex-column flex-grow-1">
            <div class="scrollable-content scrollable-panel flex-grow-1 mb-3">
              <div class="text-body-2 description-text">
                {{ project.description || 'No description available' }}
              </div>
            </div>

            <!-- Edit Button -->
            <v-btn
              variant="outlined"
              color="white"
              size="small"
              @click="handleEditDescription"
              class="align-self-end"
            >
              <v-icon start size="small">mdi-pencil</v-icon>
              Edit
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- Right Column: Orchestrator Mission Panel -->
      <v-col cols="4" md="4" class="mb-4 mb-md-0 d-flex">
        <v-card class="mission-panel launch-panel d-flex flex-column" flat style="height: 100%;">
          <!-- Header with "Optimized for you" badge -->
          <v-card-title class="panel-header bg-primary text-white d-flex justify-center">
            <span>ORCHESTRATOR CREATED MISSION</span>
            <v-chip
              v-if="userConfigApplied && missionText"
              color="success"
              size="small"
              class="ml-2"
              prepend-icon="mdi-check-circle"
            >
              Optimized for you
            </v-chip>
            <v-chip
              v-if="tokenEstimate > 0 && missionText"
              color="info"
              size="small"
              class="ml-2"
              prepend-icon="mdi-counter"
            >
              {{ tokenEstimate }} tokens
            </v-chip>
          </v-card-title>

          <v-divider />

          <!-- Content -->
          <v-card-text class="pa-4 d-flex flex-column flex-grow-1">
            <!-- Loading State -->
            <div
              v-if="isLoadingMission"
              class="flex-grow-1 d-flex flex-column align-center justify-center"
            >
              <v-progress-circular indeterminate color="primary" size="64" />
              <p class="text-subtitle-1 mt-4 font-weight-bold">Generating mission...</p>
              <p class="text-caption text-medium-emphasis mt-2">
                Analyzing project vision and applying your preferences
              </p>
            </div>

            <!-- Error State -->
            <v-alert
              v-else-if="missionError"
              type="error"
              variant="tonal"
              closable
              @click:close="missionError = null"
              class="mb-0"
            >
              <v-alert-title>
                <v-icon start>mdi-alert-circle</v-icon>
                Mission Generation Failed
              </v-alert-title>
              {{ missionError }}
              <template #append>
                <v-btn
                  size="small"
                  color="error"
                  variant="elevated"
                  @click="handleStageProject"
                  class="mt-2"
                >
                  <v-icon start>mdi-refresh</v-icon>
                  Retry
                </v-btn>
              </template>
            </v-alert>

            <!-- Content State -->
            <div v-else-if="missionText" class="d-flex flex-column flex-grow-1">
              <div class="scrollable-content scrollable-panel flex-grow-1 mb-3">
                <div class="text-body-2 mission-text">
                  {{ missionText }}
                </div>
              </div>

              <!-- Edit Button -->
              <v-btn
                variant="outlined"
                color="white"
                size="small"
                @click="handleEditMission"
                class="align-self-end"
              >
                <v-icon start size="small">mdi-pencil</v-icon>
                Edit
              </v-btn>
            </div>

            <!-- Empty State -->
            <div
              v-else
              class="flex-grow-1 d-flex flex-column align-center justify-center py-8 empty-state"
            >
              <v-icon size="64" color="grey-lighten-1" class="mb-4">
                mdi-file-document-outline
              </v-icon>
              <p class="text-body-1 font-weight-bold mb-2">Mission will appear after staging</p>
              <p class="text-body-2 text-grey text-center px-4">
                Click "Stage Project" to begin orchestrator mission generation
              </p>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Agent Cards Section (Bottom Row) -->
    <v-row class="agent-cards-row">
      <v-col cols="12">
        <v-card elevation="2">
          <v-card-title class="panel-header panel-header-tight bg-primary text-white d-flex align-center">
            <v-icon class="mr-2">mdi-account-group</v-icon>
            <span>AGENT TEAM</span>
            <v-chip
              v-if="agents.length > 0"
              color="white"
              text-color="success"
              size="small"
              class="ml-2 font-weight-bold"
            >
              {{ agents.length }} Agent{{ agents.length !== 1 ? 's' : '' }}
            </v-chip>
          </v-card-title>

          <v-divider />

          <v-card-text class="pa-4">
            <!-- Agent Cards Container -->
            <div v-if="agents.length > 0" class="agent-cards-container">
              <AgentCard
                v-for="agent in agents"
                :key="agent.agent_id || agent.job_id"
                :agent="agent"
                mode="launch"
                :instance-number="getInstanceNumber(agent)"
                @edit-mission="handleEditAgentMission"
              />
            </div>

            <!-- Empty State -->
            <div v-else class="empty-state text-center py-8">
              <v-icon size="64" color="grey-lighten-1" class="mb-4">
                mdi-account-group-outline
              </v-icon>
              <p class="text-body-1 font-weight-bold mb-2">Agents will appear here after staging begins</p>
              <p class="text-body-2 text-grey">
                The orchestrator will create specialized agents based on project requirements
              </p>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Re-Stage Confirmation Dialog -->
    <v-dialog v-model="showCancelDialog" max-width="500" persistent>
      <v-card>
        <v-card-title class="text-h5 bg-error text-white">
          <v-icon class="mr-2">mdi-refresh</v-icon>
          Re-Stage Project?
        </v-card-title>

        <v-divider />

        <v-card-text class="pa-6">
          <p class="text-body-1 mb-3">
            This will completely reset the project staging area and clear all AI-generated content:
          </p>

          <v-list density="compact" class="mb-0">
            <v-list-item prepend-icon="mdi-file-document-remove">
              <v-list-item-title>Clear generated mission text</v-list-item-title>
            </v-list-item>
            <v-list-item prepend-icon="mdi-account-group-outline">
              <v-list-item-title>Delete all spawned agents ({{ agents.length }})</v-list-item-title>
            </v-list-item>
            <v-list-item prepend-icon="mdi-message-off">
              <v-list-item-title>Delete all agent communications</v-list-item-title>
            </v-list-item>
            <v-list-item prepend-icon="mdi-refresh">
              <v-list-item-title>Return to initial state</v-list-item-title>
            </v-list-item>
          </v-list>

          <v-alert type="warning" variant="tonal" density="compact" class="mt-4 mb-0">
            <v-icon start size="small">mdi-currency-usd</v-icon>
            <strong>Token Cost Warning:</strong> Re-staging will incur new token costs as the orchestrator regenerates all missions and agent assignments.
          </v-alert>
        </v-card-text>

        <v-card-actions class="pa-4">
          <v-btn
            @click="showCancelDialog = false"
            variant="text"
          >
            Keep Current Staging
          </v-btn>
          <v-spacer />
          <v-btn
            @click="handleCancelStaging"
            color="error"
            variant="elevated"
          >
            <v-icon start>mdi-refresh</v-icon>
            Yes, Re-Stage Project
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>


    <!-- Toast Notification -->
    <v-snackbar
      v-model="showToast"
      :timeout="3000"
      color="success"
      location="top"
    >
      <v-icon start>mdi-check-circle</v-icon>
      {{ toastMessage }}
      <template #actions>
        <v-btn variant="text" @click="showToast = false">
          Close
        </v-btn>
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
 * LaunchTab Component
 *
 * Production-grade staging area for Handover 0077 + Handover 0086.
 * Orchestrator builds mission, creates agents, user reviews before launch.
 *
 * Layout:
 * - 3-column top: Orchestrator card | Project Description | Orchestrator Mission
 * - Bottom row: Agent cards (horizontal scroll)
 * - Action buttons: Stage Project → Launch jobs, Cancel
 *
 * States:
 * 1. Initial: Empty mission, no agents, "Stage Project" button
 * 2. Staging: Orchestrator building mission, agents appearing dynamically
 * 3. Ready to Launch: Mission complete, all agents created, "Launch jobs" button
 *
 * WebSocket Integration (Handover 0086):
 * - Listens for 'project:mission_updated' events (mission panel populates)
 * - Listens for 'agent:created' events (agent cards appear in real-time)
 * - Multi-tenant isolation: checks project_id and tenant_key
 */

const props = defineProps({
  project: {
    type: Object,
    required: true,
    validator: (value) => {
      return value && typeof value === 'object' && ('id' in value || 'project_id' in value)
    }
  },
  orchestrator: {
    type: Object,
    default: null
  },
  isStaging: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits([
  'stage-project',
  'launch-jobs',
  'cancel-staging',
  'edit-description',
  'edit-mission',
  'edit-agent-mission'
])

/**
 * Project ID from props
 * PRODUCTION-GRADE: Direct access (Handover 0086B Task 4.3)
 * Backend now consistently returns 'id' field via @hybrid_property
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
 * WebSocket and Auth Setup (Handover 0086)
 */
const { on, off } = useWebSocket()
const userStore = useUserStore()
const currentTenantKey = computed(() => userStore.currentUser?.tenant_key)

/**
 * Component State
 */
const missionText = ref('')

// Track agent IDs to prevent duplicates (RACE CONDITION FIX - Task 4.2)
const agentIds = ref(new Set())

const agents = ref([])
const stagingInProgress = ref(false)
const readyToLaunch = ref(false) // Set to false to show "Stage Project" button
const showCancelDialog = ref(false)
const showToast = ref(false)
const toastMessage = ref('')

// Loading states and error boundaries (PRODUCTION-GRADE - Task 4.4)
const isLoadingMission = ref(false)
const isLoadingAgents = ref(false)
const missionError = ref(null)
const agentError = ref(null)
const userConfigApplied = ref(false)
const tokenEstimate = ref(0)
const loadingStageProject = ref(false)

/**
 * Computed Properties
 */
// (Orchestrator agent is now a computed property above - no watch needed)


/**
 * Get status color for chip
 */
function getStatusColor(status) {
  const colors = {
    active: 'success',
    inactive: 'warning',
    completed: 'info',
    cancelled: 'error',
    deleted: 'grey'
  }
  return colors[status] || 'grey'
}

/**
 * Get instance number for multi-instance agents
 * (e.g., if there are 2 Implementors, second one gets instance 2)
 */
function getInstanceNumber(agent) {
  const agentType = agent.agent_type?.toLowerCase()
  if (!agentType) return 1

  // Count how many agents of same type appear before this one
  const sameTypeAgents = agents.value.filter(a => a.agent_type?.toLowerCase() === agentType)
  const index = sameTypeAgents.findIndex(a =>
    (a.agent_id || a.job_id) === (agent.agent_id || agent.job_id)
  )

  return index + 1
}

/**
 * WebSocket Event Handlers (Handover 0086)
 */

/**
 * Handle mission update from external orchestrator execution
 * Called when orchestrator calls update_project_mission() via MCP
 *
 * PRODUCTION-GRADE: Enhanced with loading states (Handover 0086B Task 4.4)
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

  // Capture user config info for UI badges
  userConfigApplied.value = data.user_config_applied || false
  tokenEstimate.value = data.token_estimate || 0

  // Clear loading state
  isLoadingMission.value = false
  stagingInProgress.value = false
  readyToLaunch.value = true
  missionError.value = null

  // Show success notification with config info
  let message = `Mission generated (${data.token_estimate || 0} tokens)`
  if (data.user_config_applied) {
    message += ' • Optimized for you'
  }

  toastMessage.value = message
  showToast.value = true

  console.log('[LaunchTab] Mission panel updated successfully')
}

/**
 * Handle agent creation from external orchestrator execution
 * Called when orchestrator calls create_agent_job_external() via MCP
 *
 * PRODUCTION-GRADE: Race condition fixed (Handover 0086B Task 4.2)
 * - Uses Set for atomic duplicate check
 * - Prevents duplicate agents in concurrent scenarios
 */
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

  // Support both payload shapes:
  // 1) Nested: { agent: { id|job_id, agent_type, agent_name, status } }
  // 2) Flat:   { agent_id|agent_job_id, agent_type, agent_name, status }
  const nestedAgent = data.agent || {}
  const fallbackAgentId = data.agent_id || data.agent_job_id
  const agentId = nestedAgent.id || nestedAgent.job_id || fallbackAgentId

  if (!agentId) {
    console.warn('[LaunchTab] Agent creation ignored: no ID in payload')
    return
  }

  // Use Set for atomic duplicate check (RACE CONDITION FIX)
  if (agentIds.value.has(agentId)) {
    console.log('[LaunchTab] Agent already exists, skipping duplicate')
    return
  }

  // Build normalized agent object for UI
  const normalizedAgent = {
    id: agentId,
    job_id: agentId,
    agent_type: nestedAgent.agent_type || data.agent_type || 'unknown',
    agent_name: nestedAgent.agent_name || data.agent_name || `Agent ${agentId.substring(0, 6)}`,
    status: nestedAgent.status || data.status || 'waiting',
  }

  // Add to Set first (atomic operation)
  agentIds.value.add(agentId)

  // Then add to reactive array
  agents.value.push(normalizedAgent)

  // Show notification
  const agentType = normalizedAgent.agent_type || 'Unknown'
  toastMessage.value = `Agent Selected - ${agentType} agent assigned to project`
  showToast.value = true

  console.log('[LaunchTab] Agent card added to UI. Total agents:', agents.value.length)
}

/**
 * Handle staging cancellation from WebSocket event
 * Called when staging is cancelled (via UI or external action)
 *
 * PRODUCTION-GRADE: Multi-tenant isolation (Handover 0108)
 * - Validates tenant key and project ID
 * - Shows success notification with agent count
 * - Resets UI to initial state
 */
const handleStagingCancelled = (data) => {
  console.log('[LaunchTab] Received project:staging_cancelled event:', data)

  // Multi-tenant isolation check
  if (!currentTenantKey.value || data.tenant_key !== currentTenantKey.value) {
    console.warn('[LaunchTab] Staging cancellation rejected: tenant mismatch')
    return
  }

  // Project isolation check
  if (data.project_id !== projectId.value) {
    console.log('[LaunchTab] Staging cancellation ignored: different project')
    return
  }

  // Reset UI to initial state
  resetStagingState()

  // Show success notification with agent count
  const agentCount = data.agents_deleted || 0
  toastMessage.value = `Staging cancelled: ${agentCount} agent${agentCount !== 1 ? 's' : ''} deleted`
  showToast.value = true

  console.log('[LaunchTab] Staging area reset. Agents deleted:', agentCount)
}

/**
 * Production-grade clipboard copy function
 * Works on both HTTPS and HTTP (10.1.0.164:7272)
 *
 * Strategy:
 * 1. Try modern Clipboard API first (works on HTTPS and localhost)
 * 2. Fallback to execCommand for HTTP network addresses
 * 3. Both methods tested and reliable on current environment
 */
async function copyPromptToClipboard(text) {
  if (!text) {
    toastMessage.value = 'No prompt to copy'
    showToast.value = true
    return false
  }

  try {
    // Try modern Clipboard API first (works on HTTPS and localhost)
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text)
      return true
    }
  } catch (clipErr) {
    console.warn('[LaunchTab] Clipboard API failed, trying fallback:', clipErr)
  }

  // Fallback for HTTP (network addresses like 10.1.0.164:7272)
  try {
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.style.position = 'fixed'
    textarea.style.left = '-9999px'
    textarea.style.top = '0'
    document.body.appendChild(textarea)

    // Focus and select
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
 * Handle Stage Project button click - Handover 0079 + 0088 Thin Client
 * SIMPLIFIED: Direct copy without dialog
 * - Generates thin prompt via API
 * - Copies immediately to clipboard
 * - Shows simple toast notification
 * - NO DIALOG, NO METRICS, NO COMPLEXITY
 */
async function handleStageProject() {
  // Reset errors
  missionError.value = null
  agentError.value = null

  // Set loading state
  loadingStageProject.value = true

  try {
    // Generate thin client staging prompt (Handover 0088)
    const response = await api.prompts.staging(projectId.value, {
      tool: 'claude-code'  // TODO: Make tool selectable in UI
    })

    if (!response.data?.prompt) {
      throw new Error('Invalid response from staging endpoint')
    }

    // Extract prompt from response
    const { prompt, estimated_prompt_tokens } = response.data

    // Copy to clipboard immediately (no dialog)
    const copied = await copyPromptToClipboard(prompt)

    if (copied) {
      // Success: Show simple notification
      toastMessage.value = 'Orchestrator prompt copied to clipboard!'
      showToast.value = true
    } else {
      // Fallback: Show prompt in alert for manual copy
      alert(`Please manually copy this prompt:\n\n${prompt}`)
    }

    // Log for debugging
    const lineCount = prompt.split('\n').length
    console.log('[LaunchTab] Thin client prompt copied:', {
      lines: lineCount,
      tokens: estimated_prompt_tokens
    })

    emit('stage-project')

  } catch (err) {
    console.error('[LaunchTab] Failed to generate prompt:', err)

    // Set error state
    missionError.value = err.response?.data?.detail || err.message || 'Failed to generate orchestrator prompt'

    // Show error toast
    toastMessage.value = `Staging failed: ${missionError.value}`
    showToast.value = true
  } finally {
    loadingStageProject.value = false
  }
}

/**
 * Handle Launch jobs button click
 */
function handleLaunchJobs() {
  emit('launch-jobs')
}

/**
 * Handle Re-Stage Project button (with confirmation)
 * PRODUCTION-GRADE: API call with error handling (Handover 0108)
 * - Calls staging cancellation API endpoint to clear all AI-generated content
 * - Shows success/error notifications
 * - Resets all UI state on success
 * - WebSocket handler updates UI in real-time
 */
async function handleCancelStaging() {
  showCancelDialog.value = false

  try {
    // Call staging cancellation API endpoint (Handover 0108)
    const response = await api.projects.cancelStaging(projectId.value)
    const result = response.data

    // Show success notification with agent count
    toastMessage.value = `Project reset to initial state: ${result.agents_deleted} agent${result.agents_deleted !== 1 ? 's' : ''} and ${result.messages_deleted || 0} message${result.messages_deleted !== 1 ? 's' : ''} deleted`
    showToast.value = true

    // Reset UI state
    resetStagingState()

    emit('cancel-staging')

  } catch (error) {
    console.error('[LaunchTab] Failed to re-stage project:', error)

    // Show error notification
    const errorMsg = error.response?.data?.detail || error.message || 'Failed to reset project'
    toastMessage.value = `Failed to re-stage project: ${errorMsg}`
    showToast.value = true
  }
}

/**
 * Reset staging state (shared by cancel and WebSocket handler)
 * PRODUCTION-GRADE: Complete state reset
 */
function resetStagingState() {
  // Reset mission and agents
  missionText.value = ''
  agents.value = []
  stagingInProgress.value = false
  readyToLaunch.value = false

  // Reset loading states and errors
  isLoadingMission.value = false
  isLoadingAgents.value = false
  missionError.value = null
  agentError.value = null
  userConfigApplied.value = false
  tokenEstimate.value = 0

  // Clear agent tracking Set
  agentIds.value.clear()
}


/**
 * Handle Edit Description button
 */
function handleEditDescription() {
  emit('edit-description')
}

/**
 * Handle Edit Mission button
 */
function handleEditMission() {
  emit('edit-mission', missionText.value)
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
 * Lifecycle Hooks - WebSocket Listener Registration (Handover 0086)
 */
onMounted(() => {
  // Initialize from props if data exists (page refresh scenario)
  // This handles the case where user refreshes the page after staging
  if (props.project.mission) {
    console.log('[LaunchTab] Loading existing mission from props on mount')
    missionText.value = props.project.mission
    stagingInProgress.value = false
    readyToLaunch.value = true
  }

  // Load agents from props if they exist
  if (props.project.agents && Array.isArray(props.project.agents) && props.project.agents.length > 0) {
    console.log('[LaunchTab] Loading existing agents from props on mount:', props.project.agents.length)
    agents.value = props.project.agents

    // Populate agent IDs set to prevent duplicates
    props.project.agents.forEach(agent => {
      const agentId = agent.id || agent.job_id
      if (agentId) {
        agentIds.value.add(agentId)
      }
    })
  }

  // Register WebSocket event listeners
  on('project:mission_updated', handleMissionUpdate)
  on('orchestrator:instructions_fetched', handleMissionUpdate) // Amendment A: Thin client support
  on('agent:created', handleAgentCreated)
  on('project:staging_cancelled', handleStagingCancelled) // Handover 0108: Staging cancellation

  console.log('[LaunchTab] WebSocket listeners registered for project:', projectId.value)
  console.log('[LaunchTab] Current tenant key:', currentTenantKey.value)
})

onUnmounted(() => {
  // Clean up WebSocket listeners (prevent memory leaks)
  off('project:mission_updated', handleMissionUpdate)
  off('orchestrator:instructions_fetched', handleMissionUpdate) // Amendment A: Thin client support
  off('agent:created', handleAgentCreated)
  off('project:staging_cancelled', handleStagingCancelled) // Handover 0108: Staging cancellation

  // Clear agent tracking Set (RACE CONDITION FIX - Task 4.2)
  agentIds.value.clear()

  console.log('[LaunchTab] Cleanup complete - WebSocket listeners removed, agent IDs cleared')
})

/**
 * Watchers - Sync with backend data
 */
watch(() => props.project.mission, (newMission) => {
  if (newMission) {
    missionText.value = newMission
    stagingInProgress.value = false
    readyToLaunch.value = true
  }
})

watch(() => props.project.agents, (newAgents) => {
  if (newAgents && Array.isArray(newAgents)) {
    agents.value = newAgents
  }
}, { immediate: true, deep: true })

/**
 * Expose methods for parent component
 * PRODUCTION-GRADE: Complete state reset (Task 4.4)
 */
defineExpose({
  setMission: (mission) => {
    missionText.value = mission
    stagingInProgress.value = false
    readyToLaunch.value = true
    isLoadingMission.value = false
    missionError.value = null
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
    stagingInProgress.value = false
    readyToLaunch.value = false
    isLoadingMission.value = false
    isLoadingAgents.value = false
    missionError.value = null
    agentError.value = null
    userConfigApplied.value = false
    tokenEstimate.value = 0
    agentIds.value.clear()
  }
})
</script>

<style scoped lang="scss">
@use '@/styles/agent-colors.scss' as *;

.launch-tab {
  padding: 0;
}

/* Column Layout */
.launch-columns {
  gap: 1rem;
}

/* Launch Panel Styling (Task 1: Panel Styling Overhaul) */
.launch-panel {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 8px;
}

/* Panel Headers */
.panel-header {
  font-weight: 600;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: rgba(255, 255, 255, 0.7);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  padding: 12px 16px;
}

/* Tight Panel Header (Agent Team) */
.panel-header-tight {
  padding: 2px 16px !important;
}

/* Description and Mission Panels */
.description-panel,
.mission-panel {
  min-height: 200px;
  max-height: 400px;
}


/* Orchestrator Card */
.orchestrator-card {
  border-radius: 20px;
  overflow: hidden;
}

/* Orchestrator Card Header */
.orchestrator-header {
  background: #D4A574 !important;
  background: var(--agent-orchestrator-primary) !important;
  color: white;
  padding: 16px 20px;
  font-weight: 600;
  font-size: 16px;
  text-transform: none;
  letter-spacing: 0;
  border-radius: 16px 16px 0 0;
  text-align: center;
}

.agent-header-text {
  flex: 1;
}

/* Info Rows */
.info-row {
  padding: 8px;
  background: rgba(0, 0, 0, 0.03);
  border-radius: 4px;
}

/* Scrollable Content Areas */
.scrollable-content {
  overflow-y: auto;
  overflow-x: hidden;
  max-height: 200px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.02);
  border-radius: 4px;
  border: 1px solid rgba(0, 0, 0, 0.06);
}

/* Custom Scrollbar for Panels (Task 1: Panel Styling Overhaul) */
.scrollable-panel {
  &::-webkit-scrollbar {
    width: 8px;
  }

  &::-webkit-scrollbar-track {
    background: rgba(0, 0, 0, 0.2);
    border-radius: 4px;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.2);
    border-radius: 4px;

    &:hover {
      background: rgba(255, 255, 255, 0.3);
    }
  }
}

/* Text Content */
.description-text,
.mission-text {
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  color: #BDBDBD !important;
}

.mission-text {
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.875rem;
}

/* Agent Cards Container */
.agent-cards-container {
  display: flex;
  gap: 16px;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 8px 0;
  scrollbar-width: thin;
  scrollbar-color: var(--agent-orchestrator-primary) transparent;

  &::-webkit-scrollbar {
    height: 8px;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
  }

  &::-webkit-scrollbar-thumb {
    background: var(--agent-orchestrator-primary);
    border-radius: 4px;

    &:hover {
      background: var(--agent-orchestrator-dark);
    }
  }
}

/* Empty State */
.empty-state {
  min-height: 200px;
}

/* Button Styling Enhancements (Task 3: Button Styling Enhancement) */
.stage-project-btn {
  border-width: 2px;
  font-weight: 600;
  text-transform: none;
  letter-spacing: 0.5px;
}

.launch-jobs-btn {
  font-weight: 600;
  text-transform: none;
  letter-spacing: 0.5px;
  color: rgba(0, 0, 0, 0.87) !important;

  &:disabled {
    opacity: 0.4;
  }
}

/* Legacy Launch Button Styling (can be removed if unused) */
.launch-button {
  font-weight: 700;
  font-size: 16px;
  letter-spacing: 0.5px;
  text-transform: uppercase;

  :deep(.v-icon) {
    font-size: 24px;
  }
}

/* Card Heights */
.h-100 {
  height: 100%;
}

/* Responsive Adjustments */
@media (max-width: 960px) {
  .launch-columns {
    gap: 1rem;
  }

  .agent-cards-container {
    justify-content: flex-start;
  }
}

@media (max-width: 600px) {
  .panel-header {
    font-size: 12px;
    padding: 10px 12px;
  }

  .scrollable-content {
    max-height: 200px;
  }
}


/* Accessibility */
:focus-visible {
  outline: 2px solid #2196f3;
  outline-offset: 2px;
}

/* Button Transitions */
.v-btn {
  transition: all 0.3s ease;

  &:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  }

  &:active:not(:disabled) {
    transform: translateY(0);
  }
}

/* Card Elevations on Hover */
.v-card {
  transition: all 0.3s ease;

  &:hover {
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15) !important;
  }
}
</style>
