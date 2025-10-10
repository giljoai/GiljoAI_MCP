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
                @admin-setup-complete="handleAdminSetupComplete"
                @finish="handleFinish"
              />
            </v-window-item>
          </v-window>
        </v-card>
      </v-col>
    </v-row>

    <!-- LAN Confirmation Modal -->
    <v-dialog v-model="showLanConfirmModal" max-width="600" persistent>
      <v-card>
        <v-card-title class="text-h5">
          <v-icon start color="warning">mdi-alert</v-icon>
          Confirm LAN Mode Configuration
        </v-card-title>

        <v-card-text>
          <v-alert type="warning" variant="tonal" class="mb-4">
            <div class="text-body-1 mb-2">
              <strong>You are about to configure GiljoAI for LAN/Network access.</strong>
            </div>
            <div class="text-body-2">
              When you restart the backend services, this application will be accessible over your
              local network.
            </div>
          </v-alert>

          <div class="text-body-2">
            <p class="mb-2"><strong>This will:</strong></p>
            <ul class="ml-4 mb-3">
              <li>Bind the API server to your selected network adapter</li>
              <li>Enable user authentication (username/password login)</li>
              <li>Allow network devices to access this server</li>
              <li>Require a service restart to take effect</li>
            </ul>
            <p class="text-medium-emphasis">
              Make sure your firewall is configured and your network is trusted.
            </p>
          </div>
        </v-card-text>

        <v-card-actions>
          <v-btn variant="outlined" @click="cancelLanConfig"> Cancel </v-btn>
          <v-spacer />
          <v-btn color="warning" @click="confirmLanConfig">
            <span class="text-white">Yes, Configure for LAN</span>
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Restart Instructions Modal -->
    <v-dialog v-model="showRestartModal" max-width="700" persistent>
      <v-card>
        <v-card-title class="text-h5">
          <v-icon start color="info">mdi-restart</v-icon>
          Restart Services Required
        </v-card-title>

        <v-card-text>
          <v-alert type="success" variant="tonal" class="mb-4">
            <strong>Setup Complete!</strong> Configuration has been saved. Please restart services
            to activate LAN mode.
          </v-alert>

          <h3 class="mb-2">Restart Instructions ({{ platform }})</h3>
          <v-list density="compact">
            <v-list-item v-for="(step, index) in restartInstructions" :key="index">
              <template v-slot:prepend>
                <v-avatar color="primary" size="24">{{ index + 1 }}</v-avatar>
              </template>
              <v-list-item-title>{{ step }}</v-list-item-title>
            </v-list-item>
          </v-list>

          <v-alert type="warning" variant="tonal" class="mt-4">
            <div class="text-body-2">
              <strong>Note:</strong> After restarting, this browser window will reconnect and show a
              welcome message confirming LAN mode is active.
            </div>
          </v-alert>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn color="primary" @click="finishSetup">
            <span class="text-white">I've Restarted - Go to Dashboard</span>
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
import DatabaseCheckStep from '@/components/setup/DatabaseCheckStep.vue'
// Deployment Mode selection removed for v3.0
import AdminAccountStep from '@/components/setup/AdminAccountStep.vue'
import AttachToolsStep from '@/components/setup/AttachToolsStep.vue'
import SerenaAttachStep from '@/components/setup/SerenaAttachStep.vue'
import SetupCompleteStep from '@/components/setup/SetupCompleteStep.vue'

const theme = useTheme()

// Step configuration with conditional rendering
const allSteps = [
  {
    component: AdminAccountStep,
    title: 'Admin Setup',
    name: 'adminSetup',
  },
  {
    component: AttachToolsStep,
    title: 'MCP Configuration',
    name: 'attachTools',
  },
  {
    component: SerenaAttachStep,
    title: 'Serena Enhancement',
    name: 'serena',
  },
  {
    component: DatabaseCheckStep,
    title: 'Database Test',
    name: 'database',
  },
  {
    component: SetupCompleteStep,
    title: 'Complete',
    name: 'complete',
  },
]

// Reactive configuration state
const config = reactive({
  adminUsername: '', // Optional admin username
  adminPassword: '', // Optional admin password
  adminEmail: '', // Optional admin email
  apiKey: '', // Generated API key
  serenaEnabled: false, // Serena enabled flag
  dbTestPassed: false, // Database test status
  aiTools: [], // Configured AI tools
  // Removed deployment mode and LAN-specific configuration
})

// State
const currentStepIndex = ref(0)
const isRestarting = ref(false)
const restartMessage = ref('Saving configuration...')
const showLanConfirmModal = ref(false)
const showRestartModal = ref(false)
const installationPath = ref('(project directory)')
const detectedPlatform = ref('windows')
const setupError = ref(null)

// Computed: Visible steps based on current configuration
const visibleSteps = computed(() => {
  return allSteps.filter((step) => {
    if (!step.showIf) return true
    return step.showIf(config)
  })
})

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

// Computed: Always use localhost URL for v3.0
const serverUrl = computed(() => 'http://127.0.0.1:7272')

// Computed: Platform
const platform = computed(() => {
  return detectedPlatform.value
})

// Computed: Restart instructions
const restartInstructions = computed(() => {
  const instructions = {
    windows: [
      'Open Command Prompt or PowerShell',
      `Navigate to ${installationPath.value}`,
      'Stop BACKEND only: stop_backend.bat',
      'Start BACKEND only: start_backend.bat',
      'Wait 10-15 seconds for backend to start',
      '(Frontend does NOT need restart)',
    ],
    macos: [
      'Open Terminal',
      `Navigate to ${installationPath.value}`,
      'Stop BACKEND only: ./stop_backend.sh',
      'Start BACKEND only: ./start_backend.sh',
      'Wait 10-15 seconds for backend to start',
      '(Frontend does NOT need restart)',
    ],
    linux: [
      'Open Terminal',
      `Navigate to ${installationPath.value}`,
      'Stop BACKEND only: ./stop_backend.sh',
      'Start BACKEND only: ./start_backend.sh',
      'Wait 10-15 seconds for backend to start',
      '(Frontend does NOT need restart)',
    ],
  }
  return instructions[platform.value]
})

// Get props for current step
const getStepProps = (step) => {
  const baseProps = {}

  switch (step.name) {
    case 'database':
      baseProps.dbTestPassed = config.dbTestPassed
      break
    case 'adminSetup':
      baseProps.modelValue = {
        username: config.adminUsername,
        password: config.adminPassword,
        email: config.adminEmail,
      }
      baseProps['onUpdate:modelValue'] = (value) => {
        config.adminUsername = value.username
        config.adminPassword = value.password
        config.adminEmail = value.email || ''
        console.log('[WIZARD] Admin setup updated:', {
          username: config.adminUsername,
          email: config.adminEmail,
        })
      }
      break
    case 'attachTools':
      baseProps.modelValue = config.aiTools
      baseProps['onUpdate:modelValue'] = (value) => {
        config.aiTools = value
      }
      baseProps.apiKey = config.apiKey
      baseProps.serverUrl = serverUrl.value
      break
    case 'serena':
      // Serena step doesn't use modelValue, it emits next with data
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
const handleNext = (data) => {
  // Handle data from steps that emit it (like SerenaAttachStep)
  if (data && 'serenaEnabled' in data) {
    config.serenaEnabled = data.serenaEnabled
    console.log('[WIZARD] Serena enabled:', data.serenaEnabled)
  }

  if (currentStepIndex.value < visibleSteps.value.length - 1) {
    currentStepIndex.value++
  }
}

const handlePrevious = () => {
  if (currentStepIndex.value > 0) {
    currentStepIndex.value--
  }
}

// Special handlers
const handleAdminSetupComplete = async (data) => {
  // Call API to create admin user and get API key
  try {
    const response = await setupService.createAdminUser({
      username: config.adminUsername,
      password: config.adminPassword,
      email: config.adminEmail,
    })

    config.apiKey = response.api_key
    console.log('[WIZARD] Admin user created, API key received')
  } catch (error) {
    console.error('[WIZARD] Failed to create admin user:', error)
    setupError.value = 'Failed to create admin user. Please try again.'
  }
}

const handleFinish = async () => {
  // Always proceed to save setup config
  await saveSetupConfig()
}

// Removed LAN-specific config methods

const saveSetupConfig = async () => {
  try {
    console.log('[WIZARD] Completing setup with config:', config)

    // Show completion overlay
    isRestarting.value = true
    restartMessage.value = 'Saving configuration...'

    // Save setup completion with v3.0 unified configuration
    const result = await setupService.completeSetup({
      aiTools: config.aiTools,
      serenaEnabled: config.serenaEnabled,
      adminAccount: config.adminUsername ? {
        username: config.adminUsername,
        password: config.adminPassword,
        email: config.adminEmail
      } : null
    })

    console.log('[WIZARD] Setup marked as complete:', result)

    // Hide completion overlay
    isRestarting.value = false

    // Always show restart modal to standardize flow
    if (result.requires_restart) {
      showRestartModal.value = true
    } else {
      // Localhost mode - skip to completion
      restartMessage.value = 'Setup complete! Redirecting to dashboard...'
      isRestarting.value = true

      // Wait 1 second to show success message
      await new Promise((resolve) => setTimeout(resolve, 1000))

      // Redirect to main dashboard
      window.location.href = 'http://localhost:7274'
    }
  } catch (error) {
    console.error('[WIZARD] Setup completion failed:', error)
    isRestarting.value = false
    restartMessage.value = 'Error during setup completion. Redirecting...'

    // Wait 2 seconds then redirect anyway
    await new Promise((resolve) => setTimeout(resolve, 2000))
    window.location.href = 'http://localhost:7274'
  }
}

const finishSetup = () => {
  showRestartModal.value = false
  window.location.href = 'http://localhost:7274'
}

// Lifecycle
onMounted(async () => {
  console.log('[WIZARD] Component mounted')

  // Fetch installation info for dynamic restart instructions
  try {
    const response = await fetch(`${setupService.baseURL}/api/setup/installation-info`)
    if (response.ok) {
      const info = await response.json()
      installationPath.value = info.installation_path
      detectedPlatform.value = info.platform
      console.log('[WIZARD] Loaded installation info:', info)
    } else {
      console.warn('[WIZARD] Installation info API returned error:', response.status)
    }
  } catch (error) {
    console.warn('[WIZARD] Could not fetch installation info, using fallback:', error)
    // Fallback to browser detection if API fails
    const ua = window.navigator.userAgent.toLowerCase()
    if (ua.includes('win')) detectedPlatform.value = 'windows'
    else if (ua.includes('mac')) detectedPlatform.value = 'macos'
    else detectedPlatform.value = 'linux'
  }

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
