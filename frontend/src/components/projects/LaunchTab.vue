<template>
  <div class="launch-tab">
    <!-- 3-Column Layout -->
    <v-row class="launch-columns mb-6">
      <!-- Left Column: Orchestrator Card -->
      <v-col cols="12" md="3" class="mb-4 mb-md-0">
        <AgentCardEnhanced
          :agent="orchestratorAgent"
          mode="launch"
          :is-orchestrator="true"
        >
          <template #actions>
            <!-- Stage Project Button (Initial State) -->
            <v-btn
              v-if="!isStaging && !readyToLaunch"
              block
              color="primary"
              variant="elevated"
              size="large"
              :loading="stagingInProgress"
              @click="handleStageProject"
              class="mb-2"
            >
              <v-icon start>mdi-rocket-launch-outline</v-icon>
              Stage Project
            </v-btn>

            <!-- Launch jobs Button (Ready State) -->
            <v-btn
              v-if="readyToLaunch"
              block
              color="yellow-darken-2"
              variant="elevated"
              size="large"
              @click="handleLaunchJobs"
              class="mb-2 launch-button"
            >
              <v-icon start>mdi-rocket-launch</v-icon>
              Launch jobs
            </v-btn>

            <!-- Cancel Button (Always visible during staging) -->
            <v-btn
              v-if="isStaging || readyToLaunch"
              block
              color="error"
              variant="outlined"
              size="large"
              @click="showCancelDialog = true"
            >
              <v-icon start>mdi-close-circle</v-icon>
              Cancel
            </v-btn>
          </template>
        </AgentCardEnhanced>
      </v-col>

      <!-- Middle Column: Project Description Panel -->
      <v-col cols="12" md="4" class="mb-4 mb-md-0 d-flex">
        <v-card class="description-panel d-flex flex-column" elevation="2" style="height: 100%;">
          <!-- Header -->
          <v-card-title class="panel-header bg-primary text-white">
            <span>Project Description</span>
          </v-card-title>

          <v-divider />

          <!-- Content -->
          <v-card-text class="pa-4 d-flex flex-column flex-grow-1">
            <div class="scrollable-content flex-grow-1 mb-3">
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
      <v-col cols="12" md="4" class="mb-4 mb-md-0 d-flex">
        <v-card class="mission-panel d-flex flex-column" elevation="2" style="height: 100%;">
          <!-- Header -->
          <v-card-title class="panel-header bg-primary text-white">
            <span>Orchestrator Created Mission</span>
          </v-card-title>

          <v-divider />

          <!-- Content -->
          <v-card-text class="pa-4 d-flex flex-column flex-grow-1">
            <!-- Loading State -->
            <div
              v-if="stagingInProgress"
              class="flex-grow-1 d-flex flex-column align-center justify-center"
            >
              <v-progress-circular indeterminate color="primary" size="48" />
              <p class="text-subtitle-2 mt-4">Orchestrator generating mission...</p>
            </div>

            <!-- Content State -->
            <div v-else-if="missionText" class="d-flex flex-column flex-grow-1">
              <div class="scrollable-content flex-grow-1 mb-3">
                <div class="text-body-2 mission-text">
                  {{ missionText }}
                </div>
              </div>

              <!-- Edit Button -->
              <v-btn
                variant="outlined"
                color="info"
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
              class="flex-grow-1 d-flex flex-column align-center justify-center py-8"
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
          <v-card-title class="panel-header bg-success text-white">
            <v-icon class="mr-2">mdi-account-group</v-icon>
            <span>Agent Team</span>
            <v-spacer />
            <v-chip
              v-if="agents.length > 0"
              color="white"
              text-color="success"
              size="small"
              class="font-weight-bold"
            >
              {{ agents.length }} Agent{{ agents.length !== 1 ? 's' : '' }}
            </v-chip>
          </v-card-title>

          <v-divider />

          <v-card-text class="pa-4">
            <!-- Agent Cards Container -->
            <div v-if="agents.length > 0" class="agent-cards-container">
              <AgentCardEnhanced
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

    <!-- Cancel Confirmation Dialog -->
    <v-dialog v-model="showCancelDialog" max-width="500" persistent>
      <v-card>
        <v-card-title class="text-h5 bg-error text-white">
          <v-icon class="mr-2">mdi-alert</v-icon>
          Cancel Project Staging?
        </v-card-title>

        <v-divider />

        <v-card-text class="pa-6">
          <p class="text-body-1 mb-3">
            This will completely reset the project staging area:
          </p>

          <v-list density="compact" class="mb-0">
            <v-list-item prepend-icon="mdi-file-document-remove">
              <v-list-item-title>Clear generated mission text</v-list-item-title>
            </v-list-item>
            <v-list-item prepend-icon="mdi-account-group-outline">
              <v-list-item-title>Delete all created agents ({{ agents.length }})</v-list-item-title>
            </v-list-item>
            <v-list-item prepend-icon="mdi-refresh">
              <v-list-item-title>Return to initial state</v-list-item-title>
            </v-list-item>
          </v-list>

          <v-alert type="warning" variant="tonal" density="compact" class="mt-4 mb-0">
            <v-icon start size="small">mdi-information</v-icon>
            You will need to re-run the orchestrator to generate a new mission.
          </v-alert>
        </v-card-text>

        <v-card-actions class="pa-4">
          <v-btn
            @click="showCancelDialog = false"
            variant="text"
          >
            Keep Staging
          </v-btn>
          <v-spacer />
          <v-btn
            @click="handleCancelStaging"
            color="error"
            variant="elevated"
          >
            <v-icon start>mdi-delete</v-icon>
            Yes, Cancel Everything
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
import { ref, computed, watch } from 'vue'
import AgentCardEnhanced from './AgentCardEnhanced.vue'
import api from '@/services/api'

/**
 * LaunchTab Component
 *
 * Production-grade staging area for Handover 0077.
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
 * Component State
 */
const missionText = ref('')

// Orchestrator agent from props (real data from API)
const orchestratorAgent = computed(() => {
  if (!props.orchestrator) {
    // Fallback if no orchestrator provided
    return {
      agent_id: 'loading',
      agent_type: 'orchestrator',
      job_id: 'loading',
      mission: 'Loading orchestrator...',
      status: 'waiting'
    }
  }
  
  // Use real orchestrator data from API
  return {
    agent_id: props.orchestrator.job_id,  // Full 36-digit UUID
    agent_type: props.orchestrator.agent_type,
    job_id: props.orchestrator.job_id,  // Full 36-digit UUID
    mission: props.orchestrator.mission,
    status: props.orchestrator.status,
    progress: props.orchestrator.progress,
    agent_name: props.orchestrator.agent_name
  }
})

const agents = ref([])
const stagingInProgress = ref(false)
const readyToLaunch = ref(false) // Set to false to show "Stage Project" button
const showCancelDialog = ref(false)
const showToast = ref(false)
const toastMessage = ref('')

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
 * Handle Stage Project button click - Handover 0079
 */
async function handleStageProject() {
  stagingInProgress.value = true

  try {
    // Show loading toast
    toastMessage.value = 'Generating comprehensive orchestrator prompt...'
    showToast.value = true

    // Call API to generate comprehensive staging prompt
    const response = await api.prompts.staging(props.project.id, {
      tool: 'claude-code'  // TODO: Make tool selectable in UI
    })

    const { prompt, token_estimate, budget_utilization, warnings, context_included } = response.data

    // Log generation details
    console.log('[STAGING] Prompt generated:', {
      tokens: token_estimate,
      utilization: budget_utilization,
      context: context_included,
      warnings
    })

    // Show warnings if any
    if (warnings && warnings.length > 0) {
      console.warn('[STAGING] Token budget warnings:', warnings)
      toastMessage.value = `Prompt generated (${token_estimate} tokens, ${budget_utilization})`
      showToast.value = true
      await new Promise(resolve => setTimeout(resolve, 2000))
    }

    // Copy comprehensive prompt to clipboard
    await navigator.clipboard.writeText(prompt)

    // Success feedback
    toastMessage.value = `Orchestrator prompt copied! (${token_estimate} tokens, ${budget_utilization} budget used)`
    showToast.value = true

    emit('stage-project')

  } catch (err) {
    console.error('[STAGING] Failed to generate prompt:', err)
    stagingInProgress.value = false

    // Show error with details
    const errorMsg = err.response?.data?.detail || err.message || 'Failed to generate orchestrator prompt'
    toastMessage.value = `Error: ${errorMsg}`
    showToast.value = true
  }
}

/**
 * Handle Launch jobs button click
 */
function handleLaunchJobs() {
  emit('launch-jobs')
}

/**
 * Handle Cancel button (with confirmation)
 */
function handleCancelStaging() {
  showCancelDialog.value = false

  // Reset state
  missionText.value = ''
  agents.value = []
  stagingInProgress.value = false
  readyToLaunch.value = false

  emit('cancel-staging')
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
 */
defineExpose({
  setMission: (mission) => {
    missionText.value = mission
    stagingInProgress.value = false
    readyToLaunch.value = true
  },
  addAgent: (agent) => {
    agents.value.push(agent)
  },
  clearAgents: () => {
    agents.value = []
  },
  resetStaging: () => {
    missionText.value = ''
    agents.value = []
    stagingInProgress.value = false
    readyToLaunch.value = false
  }
})
</script>

<style scoped lang="scss">
@import '@/styles/agent-colors.scss';

.launch-tab {
  padding: 0;
}

/* Column Layout */
.launch-columns {
  gap: 1rem;
}

/* Panel Headers */
.panel-header {
  font-weight: 600;
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 12px 16px;
}
n/* Description and Mission Panels */
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
  max-height: 300px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.02);
  border-radius: 4px;
  border: 1px solid rgba(0, 0, 0, 0.06);

  /* Custom scrollbar */
  &::-webkit-scrollbar {
    width: 6px;
  }

  &::-webkit-scrollbar-track {
    background: rgba(0, 0, 0, 0.05);
    border-radius: 3px;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(0, 0, 0, 0.2);
    border-radius: 3px;

    &:hover {
      background: rgba(0, 0, 0, 0.3);
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

/* Launch Button Styling */
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
