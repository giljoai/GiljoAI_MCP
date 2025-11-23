<template>
  <div>
    <!-- Launch Button -->
    <v-tooltip location="bottom">
      <template v-slot:activator="{ props: tooltipProps }">
        <v-btn
          v-bind="tooltipProps"
          color="primary"
          variant="elevated"
          :disabled="!canLaunch"
          :loading="isLaunching"
          @click="handleLaunch"
          aria-label="Launch Orchestrator"
        >
          <v-icon start>mdi-rocket-launch</v-icon>
          Launch Orchestrator
        </v-btn>
      </template>
      <span v-if="!product.is_active">Product must be active</span>
      <span v-else-if="!product.has_vision_documents">Product must have vision documents</span>
      <span v-else>Launch multi-agent orchestration workflow</span>
    </v-tooltip>

    <!-- Progress Dialog -->
    <v-dialog
      v-model="showProgressDialog"
      max-width="700"
      persistent
      :aria-label="`Orchestrator progress: ${currentProgress}%`"
    >
      <v-card>
        <v-card-title class="d-flex align-center text-h5" :class="progressHeaderClass">
          <v-icon class="mr-2" :color="progressIconColor">{{ progressIcon }}</v-icon>
          {{ progressTitle }}
        </v-card-title>

        <v-divider></v-divider>

        <v-card-text class="pt-4">
          <!-- Progress Bar -->
          <div class="mb-4">
            <v-progress-linear
              :model-value="currentProgress"
              :color="progressBarColor"
              height="8"
              rounded
              :indeterminate="currentProgress === 0"
              aria-label="Progress bar"
            ></v-progress-linear>
            <div class="text-caption text-center mt-1 text-medium-emphasis">
              {{ currentProgress }}%
            </div>
          </div>

          <!-- Current Stage Message -->
          <v-alert
            :type="currentStageAlertType"
            variant="tonal"
            density="comfortable"
            class="mb-4"
            :icon="currentStageIcon"
          >
            <div class="text-body-1">{{ currentMessage }}</div>
          </v-alert>

          <!-- Stage Timeline -->
          <div class="mb-4">
            <div class="text-subtitle-2 text-medium-emphasis mb-2">Workflow Progress:</div>
            <v-timeline side="end" density="compact" class="stage-timeline">
              <v-timeline-item
                v-for="stage in completedStages"
                :key="stage.key"
                :dot-color="stage.color"
                size="small"
              >
                <template v-slot:icon>
                  <v-icon size="small">{{ stage.icon }}</v-icon>
                </template>
                <div class="d-flex align-center">
                  <span class="text-body-2">{{ stage.label }}</span>
                  <v-icon v-if="stage.isComplete" class="ml-2" color="success" size="small">
                    mdi-check-circle
                  </v-icon>
                  <v-progress-circular
                    v-else-if="stage.isActive"
                    class="ml-2"
                    indeterminate
                    size="16"
                    width="2"
                    :color="stage.color"
                  ></v-progress-circular>
                </div>
              </v-timeline-item>
            </v-timeline>
          </div>

          <!-- Expandable Details Panel -->
          <v-expansion-panels v-if="currentDetails && Object.keys(currentDetails).length > 0">
            <v-expansion-panel>
              <v-expansion-panel-title>
                <v-icon class="mr-2">mdi-information-outline</v-icon>
                Additional Details
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <div class="text-body-2">
                  <div v-for="(value, key) in currentDetails" :key="key" class="mb-2">
                    <strong>{{ formatDetailKey(key) }}:</strong> {{ value }}
                  </div>
                </div>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>

          <!-- Error Alert -->
          <v-alert
            v-if="errorMessage"
            type="error"
            variant="tonal"
            class="mt-4"
            :text="errorMessage"
          >
            <template v-slot:prepend>
              <v-icon>mdi-alert-circle</v-icon>
            </template>
          </v-alert>
        </v-card-text>

        <v-divider></v-divider>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn v-if="canClose" variant="text" @click="handleClose" aria-label="Close dialog">
            Close
          </v-btn>
          <v-btn
            v-if="errorMessage"
            color="primary"
            variant="flat"
            @click="handleRetry"
            aria-label="Retry orchestrator launch"
          >
            Retry
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { api } from '@/services/api'
import { useWebSocketStore } from '@/stores/websocket'

/**
 * OrchestratorLaunchButton Component
 *
 * Production-grade button component for launching multi-agent orchestration workflows.
 * Features real-time WebSocket progress tracking and comprehensive error handling.
 *
 * @component
 * @props {Object} product - Product object with id, is_active, has_vision_documents
 * @emits {void} launched - Emitted when orchestrator successfully completes
 * @emits {Error} error - Emitted when orchestrator launch fails
 */

const props = defineProps({
  product: {
    type: Object,
    required: true,
    validator: (val) => {
      return (
        val &&
        typeof val.id === 'string' &&
        typeof val.is_active === 'boolean' &&
        typeof val.has_vision_documents === 'boolean'
      )
    },
  },
})

const emit = defineEmits(['launched', 'error'])

// State
const isLaunching = ref(false)
const showProgressDialog = ref(false)
const currentStage = ref('idle')
const currentProgress = ref(0)
const currentMessage = ref('')
const currentDetails = ref(null)
const errorMessage = ref('')
const sessionId = ref('')
const completedStagesKeys = ref([])

// Stage configuration mapping
const STAGE_CONFIG = {
  starting: {
    key: 'starting',
    label: 'Initializing Orchestrator',
    progress: 0,
    icon: 'mdi-rocket-launch-outline',
    color: 'primary',
  },
  processing_vision: {
    key: 'processing_vision',
    label: 'Processing Vision Documents',
    progress: 20,
    icon: 'mdi-file-document-multiple',
    color: 'primary',
  },
  generating_missions: {
    key: 'generating_missions',
    label: 'Generating Mission Plan',
    progress: 40,
    icon: 'mdi-file-chart',
    color: 'primary',
  },
  selecting_agents: {
    key: 'selecting_agents',
    label: 'Selecting Optimal Agents',
    progress: 60,
    icon: 'mdi-account-group',
    color: 'primary',
  },
  creating_workflow: {
    key: 'creating_workflow',
    label: 'Coordinating Workflow',
    progress: 80,
    icon: 'mdi-source-branch',
    color: 'primary',
  },
  complete: {
    key: 'complete',
    label: 'Orchestrator Launched',
    progress: 100,
    icon: 'mdi-check-circle',
    color: 'success',
  },
  error: {
    key: 'error',
    label: 'Error Occurred',
    progress: 0,
    icon: 'mdi-alert-circle',
    color: 'error',
  },
}

// Computed properties
const canLaunch = computed(() => {
  return props.product.is_active && props.product.has_vision_documents && !isLaunching.value
})

const canClose = computed(() => {
  return currentStage.value === 'complete' || currentStage.value === 'error'
})

const progressHeaderClass = computed(() => {
  if (currentStage.value === 'error') return 'bg-error'
  if (currentStage.value === 'complete') return 'bg-success'
  return 'bg-primary'
})

const progressIcon = computed(() => {
  return STAGE_CONFIG[currentStage.value]?.icon || 'mdi-rocket-launch'
})

const progressIconColor = computed(() => {
  if (currentStage.value === 'error') return 'error'
  if (currentStage.value === 'complete') return 'success'
  return 'primary'
})

const progressTitle = computed(() => {
  if (currentStage.value === 'error') return 'Orchestrator Launch Failed'
  if (currentStage.value === 'complete') return 'Orchestrator Launched Successfully'
  return 'Launching Orchestrator'
})

const progressBarColor = computed(() => {
  if (currentStage.value === 'error') return 'error'
  if (currentStage.value === 'complete') return 'success'
  return 'primary'
})

const currentStageAlertType = computed(() => {
  if (currentStage.value === 'error') return 'error'
  if (currentStage.value === 'complete') return 'success'
  return 'info'
})

const currentStageIcon = computed(() => {
  if (currentStage.value === 'error') return 'mdi-alert-circle'
  if (currentStage.value === 'complete') return 'mdi-check-circle'
  return 'mdi-information'
})

const completedStages = computed(() => {
  const stages = []
  const stageOrder = [
    'starting',
    'processing_vision',
    'generating_missions',
    'selecting_agents',
    'creating_workflow',
  ]

  for (const stageKey of stageOrder) {
    const config = STAGE_CONFIG[stageKey]
    const isComplete = completedStagesKeys.value.includes(stageKey)
    const isActive = currentStage.value === stageKey && !isComplete

    // Only show completed stages and current active stage
    if (isComplete || isActive) {
      stages.push({
        ...config,
        isComplete,
        isActive,
      })
    }
  }

  return stages
})

// WebSocket event handlers
let unsubscribeProgress = null
let unsubscribeError = null

/**
 * Handle orchestrator progress updates from WebSocket
 * @param {Object} data - Progress data from WebSocket
 */
function handleProgressUpdate(data) {
  // Only process updates for current session
  if (data.session_id !== sessionId.value) return

  console.log('[OrchestratorLaunchButton] Progress update:', data)

  currentStage.value = data.stage
  currentProgress.value = data.progress
  currentMessage.value = data.message
  currentDetails.value = data.details || null

  // Track completed stages
  if (!completedStagesKeys.value.includes(data.stage)) {
    completedStagesKeys.value.push(data.stage)
  }

  // Handle completion
  if (data.stage === 'complete') {
    isLaunching.value = false
    emit('launched', data)

    // Announce completion to screen readers
    announceToScreenReader('Orchestrator launched successfully')
  }
}

/**
 * Handle orchestrator error events from WebSocket
 * @param {Object} data - Error data from WebSocket
 */
function handleErrorUpdate(data) {
  // Only process updates for current session
  if (data.session_id !== sessionId.value) return

  console.error('[OrchestratorLaunchButton] Error:', data)

  currentStage.value = 'error'
  currentProgress.value = 0
  errorMessage.value = data.error || 'An unknown error occurred'
  isLaunching.value = false

  emit('error', {
    stage: data.stage,
    error: data.error,
    details: data.details,
  })

  // Announce error to screen readers
  announceToScreenReader(`Error: ${errorMessage.value}`)
}

/**
 * Launch orchestrator workflow
 */
async function handleLaunch() {
  if (!canLaunch.value) return

  // Reset state
  isLaunching.value = true
  showProgressDialog.value = true
  currentStage.value = 'starting'
  currentProgress.value = 0
  currentMessage.value = 'Initializing orchestrator workflow...'
  errorMessage.value = ''
  completedStagesKeys.value = []
  currentDetails.value = null

  try {
    // Call orchestrator launch API
    const response = await api.orchestrator.launch({
      product_id: props.product.id,
      project_description: 'Generated from product vision documents',
      workflow_type: 'waterfall',
      auto_start: true,
    })

    // Store session ID for WebSocket filtering
    sessionId.value = response.data.session_id

    console.log('[OrchestratorLaunchButton] Launch initiated:', response.data)

    // WebSocket will handle progress updates
    // Final completion will be handled by handleProgressUpdate
  } catch (error) {
    console.error('[OrchestratorLaunchButton] Launch failed:', error)

    // Handle specific error cases
    if (error.response?.status === 409) {
      const detail = error.response.data?.detail || {}
      errorMessage.value = detail.message || 'Product validation failed'
    } else if (error.response?.status === 404) {
      errorMessage.value = 'Product not found'
    } else if (error.response?.status === 400) {
      errorMessage.value = error.response.data?.detail || 'Invalid request'
    } else {
      errorMessage.value = error.message || 'Failed to launch orchestrator'
    }

    currentStage.value = 'error'
    isLaunching.value = false

    emit('error', {
      error: errorMessage.value,
      response: error.response,
    })
  }
}

/**
 * Retry orchestrator launch after error
 */
function handleRetry() {
  errorMessage.value = ''
  showProgressDialog.value = false

  // Small delay before retry
  setTimeout(() => {
    handleLaunch()
  }, 300)
}

/**
 * Close progress dialog
 */
function handleClose() {
  if (!canClose.value) return

  showProgressDialog.value = false
  isLaunching.value = false

  // Reset after animation completes
  setTimeout(() => {
    currentStage.value = 'idle'
    currentProgress.value = 0
    currentMessage.value = ''
    errorMessage.value = ''
    completedStagesKeys.value = []
    currentDetails.value = null
    sessionId.value = ''
  }, 300)
}

/**
 * Format detail key for display
 * @param {string} key - Detail key
 * @returns {string} Formatted key
 */
function formatDetailKey(key) {
  return key
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

/**
 * Announce message to screen readers
 * @param {string} message - Message to announce
 */
function announceToScreenReader(message) {
  const liveRegion = document.createElement('div')
  liveRegion.setAttribute('role', 'status')
  liveRegion.setAttribute('aria-live', 'polite')
  liveRegion.setAttribute('aria-atomic', 'true')
  liveRegion.className = 'sr-only'
  liveRegion.textContent = message

  document.body.appendChild(liveRegion)

  setTimeout(() => {
    document.body.removeChild(liveRegion)
  }, 1000)
}

// Lifecycle hooks
onMounted(() => {
  const wsStore = useWebSocketStore()

  // Register WebSocket event handlers
  unsubscribeProgress = wsStore.on('orchestrator:progress', handleProgressUpdate)
  unsubscribeError = wsStore.on('orchestrator:error', handleErrorUpdate)

  console.log('[OrchestratorLaunchButton] WebSocket listeners registered')
})

onUnmounted(() => {
  // Clean up WebSocket event handlers
  if (unsubscribeProgress) {
    unsubscribeProgress()
  }
  if (unsubscribeError) {
    unsubscribeError()
  }

  console.log('[OrchestratorLaunchButton] WebSocket listeners cleaned up')
})
</script>

<style scoped>
.bg-primary {
  background-color: rgba(var(--v-theme-primary), 0.1) !important;
}

.bg-success {
  background-color: rgba(var(--v-theme-success), 0.1) !important;
}

.bg-error {
  background-color: rgba(var(--v-theme-error), 0.1) !important;
}

.stage-timeline {
  max-height: 250px;
  overflow-y: auto;
}

/* Screen reader only class */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}
</style>
