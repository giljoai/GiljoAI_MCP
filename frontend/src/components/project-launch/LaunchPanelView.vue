<template>
  <v-row class="launch-panel-container">
    <!-- Left Column: Orchestrator Card -->
    <v-col cols="12" md="4" class="mb-4 mb-md-0">
      <v-card class="h-100" elevation="2">
        <!-- Card Header -->
        <v-card-title class="d-flex align-center bg-gradient-purple text-white">
          <v-icon class="mr-2" size="28">mdi-brain</v-icon>
          <span>Orchestrator</span>
          <v-spacer />
          <v-btn
            icon
            size="small"
            variant="text"
            color="white"
            @click="showOrchestratorInfo = true"
            aria-label="Show orchestrator information"
          >
            <v-icon>mdi-information</v-icon>
          </v-btn>
        </v-card-title>

        <v-divider />

        <v-card-text class="pa-4">
          <!-- Project Description (Editable) -->
          <div class="mb-4">
            <p class="text-subtitle-2 font-weight-bold mb-2">Project Description</p>
            <p class="text-caption text-grey mb-2">
              Human-readable input (this is what you want to build)
            </p>
            <v-textarea
              :model-value="project?.description || project?.mission"
              label="Project Description"
              hint="Describe the project goals and requirements"
              persistent-hint
              rows="8"
              variant="outlined"
              density="compact"
              @update:model-value="$emit('save-description', $event)"
              readonly
            />
          </div>

          <v-divider class="my-4" />

          <!-- Orchestrator Prompt (Copy) -->
          <div>
            <p class="text-subtitle-2 font-weight-bold mb-2">Orchestrator Prompt</p>
            <p class="text-caption text-grey mb-3">
              Copy this prompt and paste into Claude Code, Codex, or Gemini to start the orchestrator
            </p>

            <v-card variant="tonal" color="info" class="mb-3">
              <v-card-text class="pa-3">
                <v-code class="text-body-2 d-block overflow-auto" style="max-height: 200px">
                  You are the Orchestrator for Project ID: {{ project?.id }}.

Project Name: {{ project?.name }}
Project Description: {{ project?.description || project?.mission }}

Your tasks:
1. Retrieve complete project context using MCP tools
2. Analyze requirements and constraints
3. Generate detailed mission plan
4. Select optimal agents (max 6)
5. Create coordinated workflow

Respond with:
- Complete mission statement
- Selected agents
- Workflow structure
- Token estimate
                </v-code>
              </v-card-text>
            </v-card>

            <v-btn
              block
              color="primary"
              variant="elevated"
              @click="$emit('copy-prompt')"
              :loading="copying"
            >
              <v-icon start>mdi-content-copy</v-icon>
              Copy Prompt
            </v-btn>
          </div>
        </v-card-text>
      </v-card>

      <!-- Orchestrator Info Dialog -->
      <v-dialog v-model="showOrchestratorInfo" max-width="500">
        <v-card>
          <v-card-title>About the Orchestrator</v-card-title>
          <v-divider />
          <v-card-text class="pa-4">
            <p class="text-body-2 mb-3">
              The Orchestrator is an AI system that analyzes your project and creates a detailed mission plan.
            </p>

            <p class="text-body-2 font-weight-bold mb-2">How it works:</p>
            <ol class="text-body-2 mb-3">
              <li>Copy the orchestrator prompt</li>
              <li>Paste into Claude Code, Codex, or Gemini</li>
              <li>The orchestrator analyzes your project</li>
              <li>Selected agents are shown below</li>
              <li>Review mission before accepting</li>
            </ol>

            <v-alert type="info" variant="tonal" class="mb-0">
              The orchestrator runs independently and returns results to this dashboard.
              You maintain full control over mission acceptance.
            </v-alert>
          </v-card-text>
          <v-divider />
          <v-card-actions>
            <v-spacer />
            <v-btn @click="showOrchestratorInfo = false">Close</v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
    </v-col>

    <!-- Center Column: Mission Display -->
    <v-col cols="12" md="4" class="mb-4 mb-md-0">
      <v-card class="h-100" elevation="2">
        <!-- Card Header -->
        <v-card-title class="d-flex align-center bg-gradient-blue text-white">
          <v-icon class="mr-2" size="28">mdi-file-document</v-icon>
          <span>Generated Mission</span>
        </v-card-title>

        <v-divider />

        <v-card-text class="pa-4 d-flex flex-column" style="min-height: 500px">
          <!-- Loading State -->
          <div v-if="loadingMission" class="flex-grow-1 d-flex flex-column align-center justify-center">
            <v-progress-circular indeterminate color="primary" size="48" />
            <p class="text-subtitle-2 mt-4">Orchestrator generating mission...</p>
          </div>

          <!-- Content State -->
          <div v-else-if="mission" class="flex-grow-1">
            <div class="mission-content bg-surface rounded pa-3 mb-3 text-body-2" style="min-height: 350px; overflow-y: auto">
              {{ mission }}
            </div>

            <v-chip color="success" label size="small" class="mb-3">
              <v-icon start size="small">mdi-check-circle</v-icon>
              Mission Ready
            </v-chip>
          </div>

          <!-- Empty State -->
          <div v-else class="flex-grow-1 d-flex flex-column align-center justify-center py-8">
            <v-icon size="64" color="grey-lighten-1" class="mb-4">mdi-file-document-outline</v-icon>
            <p class="text-body-1 font-weight-bold mb-2">No Mission Yet</p>
            <p class="text-body-2 text-grey text-center">
              Copy the orchestrator prompt and run it in Claude Code to generate a mission plan. Results will appear here automatically.
            </p>
          </div>
        </v-card-text>
      </v-card>
    </v-col>

    <!-- Right Column: Agent Cards (2x3 Grid) -->
    <v-col cols="12" md="4">
      <v-card class="h-100" elevation="2">
        <!-- Card Header -->
        <v-card-title class="d-flex align-center bg-gradient-green text-white">
          <v-icon class="mr-2" size="28">mdi-account-group</v-icon>
          <span>Selected Agents</span>
          <v-spacer />
          <v-chip
            v-if="agents.length > 0"
            color="white"
            text-color="green"
            size="small"
            label
          >
            {{ agents.length }}/6
          </v-chip>
        </v-card-title>

        <v-divider />

        <v-card-text class="pa-4">
          <!-- Agents Grid -->
          <v-row v-if="agents.length > 0" class="mb-4">
            <v-col
              v-for="agent in agents"
              :key="`${agent.id}-${agent.type}`"
              cols="6"
            >
              <agent-mini-card :agent="agent" />
            </v-col>
          </v-row>

          <!-- Empty State -->
          <div v-else class="text-center py-12">
            <v-icon size="48" color="grey-lighten-1" class="mb-3 d-block">
              mdi-account-group-outline
            </v-icon>
            <p class="text-body-2 text-grey">
              Agents will appear here after orchestrator generates mission.
            </p>
          </div>

          <!-- Agent Count Info -->
          <v-alert
            v-if="agents.length > 0"
            type="info"
            variant="tonal"
            density="compact"
            class="mt-4 mb-0"
          >
            <v-icon start size="small">mdi-information</v-icon>
            {{ agents.length }} agent(s) ready for deployment
          </v-alert>

          <!-- No Agents Info -->
          <v-alert
            v-else
            type="info"
            variant="tonal"
            density="compact"
            class="mt-4 mb-0"
          >
            <v-icon start size="small">mdi-lightbulb</v-icon>
            Agents are assigned by the orchestrator based on mission requirements.
          </v-alert>
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>

  <!-- Token Counter Card Row (Handover 0065) -->
  <v-row v-if="tokenEstimate" class="mt-4">
    <v-col cols="12" md="4" offset-md="4">
      <v-card elevation="2">
        <!-- Card Header -->
        <v-card-title class="d-flex align-center bg-gradient-orange text-white">
          <v-icon class="mr-2" size="28">mdi-counter</v-icon>
          <span>Token Budget</span>
        </v-card-title>

        <v-divider />

        <v-card-text class="pa-4">
          <!-- Token Breakdown -->
          <div class="mb-4">
            <v-row dense>
              <v-col cols="6">
                <p class="text-caption text-grey mb-1">Mission Tokens</p>
                <p class="text-h6 font-weight-bold">{{ tokenEstimate.mission_tokens }}</p>
              </v-col>
              <v-col cols="6">
                <p class="text-caption text-grey mb-1">Agent Overhead</p>
                <p class="text-h6 font-weight-bold">{{ tokenEstimate.agent_overhead }}</p>
              </v-col>
            </v-row>

            <v-row dense class="mt-2">
              <v-col cols="6">
                <p class="text-caption text-grey mb-1">Context Tokens</p>
                <p class="text-h6 font-weight-bold">{{ tokenEstimate.context_tokens }}</p>
              </v-col>
              <v-col cols="6">
                <p class="text-caption text-grey mb-1">Total Estimate</p>
                <p class="text-h5 font-weight-bold text-primary">{{ tokenEstimate.total_estimate }}</p>
              </v-col>
            </v-row>
          </div>

          <v-divider class="my-3" />

          <!-- Budget Progress Bar -->
          <div class="mb-4">
            <div class="d-flex justify-space-between align-center mb-2">
              <p class="text-caption text-grey mb-0">Budget Utilization</p>
              <p class="text-caption font-weight-bold mb-0">
                {{ tokenEstimate.total_estimate }} / {{ tokenEstimate.budget_available }}
              </p>
            </div>

            <v-progress-linear
              :model-value="tokenEstimate.utilization_percent"
              :color="getBudgetColor(tokenEstimate.utilization_percent)"
              height="20"
              rounded
              aria-label="Token budget utilization progress"
            >
              <template v-slot:default>
                <strong class="text-white">{{ tokenEstimate.utilization_percent }}%</strong>
              </template>
            </v-progress-linear>
          </div>

          <!-- Budget Status Alert -->
          <v-alert
            v-if="!tokenEstimate.within_budget"
            type="warning"
            variant="tonal"
            density="compact"
            class="mb-0"
          >
            <v-icon start size="small">mdi-alert</v-icon>
            Mission may exceed token budget. Consider simplifying requirements.
          </v-alert>

          <v-alert
            v-else-if="tokenEstimate.utilization_percent > 80"
            type="info"
            variant="tonal"
            density="compact"
            class="mb-0"
          >
            <v-icon start size="small">mdi-information</v-icon>
            High token usage. Mission is within budget but approaching limit.
          </v-alert>

          <v-alert
            v-else
            type="success"
            variant="tonal"
            density="compact"
            class="mb-0"
          >
            <v-icon start size="small">mdi-check-circle</v-icon>
            Mission is well within token budget.
          </v-alert>
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>

  <!-- Accept Mission Button Row -->
  <v-row class="mt-6 mb-4">
    <v-col cols="12" class="text-center">
      <!-- Accept Button -->
      <v-btn
        size="x-large"
        color="success"
        elevation="4"
        :disabled="!canAccept"
        @click="$emit('accept-mission')"
        :loading="launching"
        min-width="250"
        class="text-h6 mr-4"
        aria-label="Accept mission and create agent jobs"
      >
        <v-icon start size="28">mdi-check-circle</v-icon>
        ACCEPT MISSION
      </v-btn>

      <!-- Cancel/Reset Button -->
      <v-btn
        size="x-large"
        color="error"
        variant="outlined"
        elevation="2"
        :disabled="!canReset"
        @click="handleReset"
        min-width="200"
        class="text-h6"
        aria-label="Cancel and reset mission staging"
      >
        <v-icon start size="28">mdi-close-circle</v-icon>
        CANCEL &amp; RESET
      </v-btn>

      <p v-if="!canAccept && !canReset" class="text-caption text-grey mt-2">
        <v-icon size="small">mdi-information</v-icon>
        Waiting for mission and agents to be selected
      </p>
    </v-col>
  </v-row>

  <!-- Reset Confirmation Dialog -->
  <v-dialog v-model="showResetDialog" max-width="500" persistent>
    <v-card>
      <v-card-title class="text-h5 bg-error text-white">
        <v-icon class="mr-2">mdi-alert</v-icon>
        Cancel &amp; Reset Mission?
      </v-card-title>

      <v-divider />

      <v-card-text class="pa-6">
        <p class="text-body-1 mb-3">
          This will completely reset the mission staging area:
        </p>

        <v-list density="compact" class="mb-0">
          <v-list-item prepend-icon="mdi-file-document-remove">
            <v-list-item-title>Clear generated mission text</v-list-item-title>
          </v-list-item>
          <v-list-item prepend-icon="mdi-account-group-outline">
            <v-list-item-title>Remove all selected agents</v-list-item-title>
          </v-list-item>
          <v-list-item prepend-icon="mdi-counter">
            <v-list-item-title>Reset token counter</v-list-item-title>
          </v-list-item>
        </v-list>

        <v-alert type="warning" variant="tonal" density="compact" class="mt-4 mb-0">
          <v-icon start size="small">mdi-information</v-icon>
          You will need to re-run the orchestrator to generate a new mission.
        </v-alert>
      </v-card-text>

      <v-card-actions class="pa-4">
        <v-btn
          @click="showResetDialog = false"
          variant="text"
        >
          Keep Mission
        </v-btn>
        <v-spacer />
        <v-btn
          @click="confirmReset"
          color="error"
          variant="elevated"
        >
          <v-icon start>mdi-delete</v-icon>
          Yes, Reset Everything
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <!-- Info Row -->
  <v-row>
    <v-col cols="12">
      <v-alert type="info" variant="tonal" density="comfortable">
        <v-icon start>mdi-shield-information</v-icon>
        <div>
          <p class="text-subtitle-2 font-weight-bold">Next Steps</p>
          <ol class="text-body-2 mb-0">
            <li class="mb-1">Review the generated mission and selected agents above</li>
            <li class="mb-1">Click "ACCEPT MISSION" to create agent jobs</li>
            <li>Switch to the "Active Jobs" tab to monitor agent progress</li>
          </ol>
        </div>
      </v-alert>
    </v-col>
  </v-row>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import AgentMiniCard from './AgentMiniCard.vue'
import api from '@/services/api'

/**
 * LaunchPanelView Component (Enhanced with Token Counter - Handover 0065)
 *
 * Displays the project launch interface with four sections:
 * - Left: Orchestrator with editable description and copyable prompt
 * - Center: AI-generated mission display
 * - Right: Selected agents (up to 6) in a 2x3 grid
 * - Token Counter: Budget analysis (appears when mission exists)
 * - Bottom: ACCEPT MISSION and CANCEL/RESET buttons
 */

const props = defineProps({
  project: {
    type: Object,
    required: true,
  },
  mission: {
    type: String,
    default: '',
  },
  agents: {
    type: Array,
    default: () => [],
  },
  loadingMission: {
    type: Boolean,
    default: false,
  },
  launching: {
    type: Boolean,
    default: false,
  },
  canAccept: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['save-description', 'copy-prompt', 'accept-mission', 'reset-mission'])

// Component state
const showOrchestratorInfo = ref(false)
const copying = ref(false)
const tokenEstimate = ref(null)
const loadingTokens = ref(false)
const showResetDialog = ref(false)

// Computed property for reset button state
const canReset = computed(() => {
  return props.mission || props.agents.length > 0 || tokenEstimate.value !== null
})

// Watch for mission changes and estimate tokens
watch(() => [props.mission, props.agents], async ([newMission, newAgents]) => {
  if (newMission && newMission.length > 0 && newAgents.length > 0) {
    await estimateTokens()
  } else if (!newMission) {
    tokenEstimate.value = null
  }
}, { deep: true })

/**
 * Estimate token usage for current mission
 */
async function estimateTokens() {
  if (!props.mission) return

  loadingTokens.value = true
  try {
    const response = await api.prompts.estimateTokens({
      mission: props.mission,
      agent_count: props.agents.length,
      project_description: props.project?.description || props.project?.mission
    })

    tokenEstimate.value = response.data
    console.log('[LAUNCH PANEL] Token estimate:', tokenEstimate.value)
  } catch (error) {
    console.error('[LAUNCH PANEL] Error estimating tokens:', error)
    tokenEstimate.value = null
  } finally {
    loadingTokens.value = false
  }
}

/**
 * Get budget progress bar color based on utilization percentage
 */
function getBudgetColor(utilization) {
  if (utilization > 100) return 'error'
  if (utilization > 80) return 'warning'
  if (utilization > 50) return 'info'
  return 'success'
}

/**
 * Handle reset button click - show confirmation dialog
 */
function handleReset() {
  showResetDialog.value = true
}

/**
 * Confirm reset - clear all staging data and emit reset event
 */
function confirmReset() {
  // Clear token estimate locally
  tokenEstimate.value = null
  showResetDialog.value = false

  // Emit reset event to parent (ProjectLaunchView)
  emit('reset-mission')
}
</script>

<style scoped>
/* Gradient backgrounds for card headers */
.bg-gradient-purple {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.bg-gradient-blue {
  background: linear-gradient(135deg, #2196f3 0%, #1976d2 100%);
}

.bg-gradient-green {
  background: linear-gradient(135deg, #66bb6a 0%, #43a047 100%);
}

.bg-gradient-orange {
  background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%);
}

/* Card container */
.launch-panel-container {
  gap: 1.5rem;
}

/* Mission content scrollable area */
.mission-content {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.6;
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
}

/* Code styling */
:deep(.v-code) {
  background-color: rgba(0, 0, 0, 0.05);
  padding: 0.75rem;
  border-radius: 4px;
}

/* Responsive adjustments */
@media (max-width: 960px) {
  .launch-panel-container {
    gap: 1rem;
  }
}

/* Agent grid */
:deep(.v-col) {
  padding: 0.5rem;
}

/* Button styling */
:deep(.v-btn) {
  text-transform: none;
  letter-spacing: 0;
}

/* Accessibility */
:focus-visible {
  outline: 2px solid #2196f3;
  outline-offset: 2px;
}
</style>
