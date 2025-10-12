<template>
  <v-container class="setup-wizard" fluid>
    <!-- Restart Overlay -->
    <v-overlay v-model="isRestarting" :persistent="true" class="align-center justify-center">
      <v-card class="pa-8 text-center" min-width="400">
        <v-progress-circular indeterminate size="64" color="primary" class="mb-4" />
        <h3 class="text-h5 mb-2">Completing Setup...</h3>
        <p class="text-body-1 text-medium-emphasis mb-4">
          {{ restartMessage }}
        </p>
        <v-progress-linear indeterminate color="primary" />
      </v-card>
    </v-overlay>

    <v-row justify="center">
      <v-col cols="12" md="10" lg="8" xl="6">
        <v-card class="wizard-card" elevation="4">
          <!-- Progress Indicator -->
          <v-card-text class="pa-6 pb-0">
            <div class="d-flex justify-space-between align-center mb-2">
              <h2 class="text-h5">GiljoAI MCP Setup</h2>
              <v-chip size="small" color="primary">{{ stepCounter }}</v-chip>
            </div>
            <v-progress-linear
              :model-value="progressPercent"
              color="primary"
              height="8"
              rounded
              class="mb-4"
            />
          </v-card-text>

          <!-- Current Step Component -->
          <v-window v-model="currentStepIndex" class="wizard-window">
            <v-window-item v-for="(step, index) in visibleSteps" :key="index" :value="index">
              <component
                :is="step.component"
                v-bind="getStepProps(step)"
                @next="handleNext"
                @back="handlePrevious"
                @finish="handleFinish"
              />
            </v-window-item>
          </v-window>
        </v-card>
      </v-col>
    </v-row>

    <!-- Restart Instructions Modal -->
    <v-dialog v-model="showRestartModal" max-width="700" persistent>
      <v-card>
        <v-card-title class="text-h5">
          <v-icon start color="info">mdi-restart</v-icon>
          Setup Complete
        </v-card-title>

        <v-card-text>
          <v-alert type="success" variant="tonal" class="mb-4">
            <strong>Setup Complete!</strong> Configuration has been saved and the application is ready to use.
          </v-alert>

          <v-alert type="info" variant="tonal" class="mt-4">
            <div class="text-body-2">
              <strong>Next Steps:</strong>
              <ul class="mt-2">
                <li>Dashboard will open automatically</li>
                <li>First-time login uses the admin account you just created</li>
              </ul>
            </div>
          </v-alert>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn color="primary" @click="finishSetup">
            <span class="text-white">Go to Dashboard</span>
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { useTheme } from 'vuetify'
import setupService from '@/services/setupService'
import McpConfigStep from '@/components/setup/McpConfigStep.vue'
import SerenaConfigStep from '@/components/setup/SerenaConfigStep.vue'
import CompletionStep from '@/components/setup/CompletionStep.vue'

const theme = useTheme()

// Step configuration - simplified to 3 steps
const allSteps = [
  {
    component: McpConfigStep,
    title: 'MCP Configuration',
    name: 'mcpConfig',
  },
  {
    component: SerenaConfigStep,
    title: 'Serena Activation',
    name: 'serenaConfig',
  },
  {
    component: CompletionStep,
    title: 'Complete',
    name: 'complete',
  },
]

// Reactive configuration state
const config = reactive({
  mcpConfigured: false, // Whether MCP was configured
  serenaEnabled: false, // Serena enabled flag
  aiTools: [], // Configured AI tools (for backward compatibility)
})

// State
const currentStepIndex = ref(0)
const isRestarting = ref(false)
const restartMessage = ref('Saving configuration...')
const showRestartModal = ref(false)
const setupError = ref(null)

// Computed: Visible steps - simplified to 2 steps
const visibleSteps = computed(() => allSteps)

// Computed: Current visible step
const currentVisibleStep = computed(() => {
  return visibleSteps.value[currentStepIndex.value]
})

// Computed: Step counter
const stepCounter = computed(() => {
  const current = currentStepIndex.value + 1
  const total = visibleSteps.value.length
  return `Step ${current} of ${total}`
})

// Computed: Progress percentage
const progressPercent = computed(() => {
  const current = currentStepIndex.value + 1
  const total = visibleSteps.value.length
  return Math.round((current / total) * 100)
})

// v3.0 Unified: Dynamic server URL for all IPs
const serverUrl = computed(() => `${window.location.protocol}//${window.location.hostname}:7272`)

// Get props for current step
const getStepProps = (step) => {
  const baseProps = {}

  switch (step.name) {
    case 'mcpConfig':
      // MCP Config step has no props - manages its own state
      break
    case 'serenaConfig':
      // Serena Config step has no props - manages its own state
      break
    case 'complete':
      baseProps.config = config
      break
  }

  return baseProps
}

// Computed: Props for current step
const currentStepProps = computed(() => {
  return getStepProps(currentVisibleStep.value)
})

// Navigation methods
const handleNext = (stepData = {}) => {
  // Update config with data from current step
  if (currentStepIndex.value === 0) {
    // MCP Config step
    config.mcpConfigured = stepData.mcpConfigured || false
    console.log('[WIZARD] MCP config updated:', config.mcpConfigured)
  } else if (currentStepIndex.value === 1) {
    // Serena Config step
    config.serenaEnabled = stepData.serenaEnabled || false
    console.log('[WIZARD] Serena config updated:', config.serenaEnabled)
  }

  // Move to next step
  if (currentStepIndex.value < visibleSteps.value.length - 1) {
    currentStepIndex.value++
  }
}

const handlePrevious = () => {
  if (currentStepIndex.value > 0) {
    currentStepIndex.value--
  }
}

const handleFinish = async () => {
  // Complete setup
  await saveSetupConfig()
}

// LAN-specific configuration removed for v3.0

const saveSetupConfig = async () => {
  try {
    console.log('[WIZARD] Completing setup with config:', config)

    // Show completion overlay
    isRestarting.value = true
    restartMessage.value = 'Saving configuration...'

    // Build tools list - if MCP configured, add 'claude-code'
    const toolsAttached = config.mcpConfigured ? ['claude-code'] : []

    // Save setup completion with simplified configuration
    const result = await setupService.completeSetup({
      serenaEnabled: config.serenaEnabled || false,
      aiTools: toolsAttached,
    })

    console.log('[WIZARD] Setup marked as complete:', result)

    // Hide completion overlay
    isRestarting.value = false

    // Always redirect to dashboard
    restartMessage.value = 'Setup complete! Redirecting to dashboard...'
    isRestarting.value = true

    // Wait 1 second to show success message
    await new Promise((resolve) => setTimeout(resolve, 1000))

    // Redirect to main dashboard (dynamic URL)
    window.location.href = `${window.location.protocol}//${window.location.hostname}:7274`
  } catch (error) {
    console.error('[WIZARD] Setup completion failed:', error)
    isRestarting.value = false
    restartMessage.value = 'Error during setup completion. Redirecting...'

    // Wait 2 seconds then redirect anyway (dynamic URL)
    await new Promise((resolve) => setTimeout(resolve, 2000))
    window.location.href = `${window.location.protocol}//${window.location.hostname}:7274`
  }
}

const finishSetup = () => {
  showRestartModal.value = false
  window.location.href = `${window.location.protocol}//${window.location.hostname}:7274`
}

// Lifecycle
onMounted(() => {
  console.log('[WIZARD] Wizard ready for configuration')
})
</script>

<style scoped>
.setup-wizard {
  min-height: 100vh;
  padding: 2rem 1rem;
  background: linear-gradient(135deg, rgba(14, 28, 45, 0.95) 0%, rgba(24, 39, 57, 0.95) 100%);
}

.wizard-card {
  border-radius: 16px;
  max-width: 100%;
}

.wizard-window {
  min-height: 500px;
}
</style>
