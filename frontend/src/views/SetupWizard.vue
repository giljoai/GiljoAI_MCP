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
          <!-- Vuetify Stepper -->
          <v-stepper v-model="currentStep" :items="stepperItems" alt-labels flat hide-actions>
            <template v-slot:item.1>
              <v-card flat>
                <DatabaseCheckStep @next="handleDatabaseNext" />
              </v-card>
            </template>

            <template v-slot:item.2>
              <v-card flat>
                <AttachToolsStep v-model="config.aiTools" @next="handleToolsNext" @back="handleBack" />
              </v-card>
            </template>

            <template v-slot:item.3>
              <v-card flat>
                <SerenaAttachStep
                  @next="handleSerenaNext"
                  @back="handleBack"
                />
              </v-card>
            </template>

            <template v-slot:item.4>
              <v-card flat>
                <NetworkConfigStep
                  v-model:mode="config.deploymentMode"
                  v-model:lan-settings="config.lanSettings"
                  @next="handleNetworkNext"
                  @back="handleBack"
                />
              </v-card>
            </template>

            <template v-slot:item.5>
              <v-card flat>
                <SetupCompleteStep :config="config" @finish="handleFinish" @back="handleBack" />
              </v-card>
            </template>
          </v-stepper>
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
              When you restart the backend services, this application will be accessible over your local network.
            </div>
          </v-alert>

          <div class="text-body-2">
            <p class="mb-2"><strong>This will:</strong></p>
            <ul class="ml-4 mb-3">
              <li>Bind the API server to 0.0.0.0 (all network interfaces)</li>
              <li>Enable API key authentication</li>
              <li>Allow network devices to access this server</li>
              <li>Require a service restart to take effect</li>
            </ul>
            <p class="text-medium-emphasis">
              Make sure your firewall is configured and your network is trusted.
            </p>
          </div>
        </v-card-text>

        <v-card-actions>
          <v-btn variant="outlined" @click="cancelLanConfig">
            Cancel
          </v-btn>
          <v-spacer />
          <v-btn color="warning" @click="confirmLanConfig">
            <span class="text-white">Yes, Configure for LAN</span>
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- API Key Modal -->
    <v-dialog v-model="showApiKeyModal" max-width="600" persistent>
      <v-card>
        <v-card-title class="text-h5">
          <v-icon start color="warning">mdi-key</v-icon>
          Your API Key
        </v-card-title>

        <v-card-text>
          <v-alert type="warning" variant="tonal" class="mb-4">
            <strong>Important:</strong> Save this API key securely. You will need it to access the
            API from network clients. It cannot be recovered if lost.
          </v-alert>

          <v-text-field
            :model-value="generatedApiKey"
            label="API Key"
            readonly
            variant="outlined"
            density="compact"
            :append-icon="apiKeyCopied ? 'mdi-check' : 'mdi-content-copy'"
            @click:append="copyApiKey"
          />

          <v-checkbox
            v-model="apiKeyConfirmed"
            label="I have saved this API key securely"
            color="primary"
          />
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn color="primary" :disabled="!apiKeyConfirmed" @click="proceedToRestart">
            <span class="text-white">Continue</span>
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
            <strong>Setup Complete!</strong> Configuration has been saved. Please restart services to activate LAN mode.
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
              <strong>Note:</strong> After restarting, this browser window will reconnect and show a welcome message confirming LAN mode is active.
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
import { ref, computed, onMounted } from 'vue'
import { useTheme } from 'vuetify'
import setupService from '@/services/setupService'
import DatabaseCheckStep from '@/components/setup/DatabaseCheckStep.vue'
import AttachToolsStep from '@/components/setup/AttachToolsStep.vue'
import SerenaAttachStep from '@/components/setup/SerenaAttachStep.vue'
import NetworkConfigStep from '@/components/setup/NetworkConfigStep.vue'
import SetupCompleteStep from '@/components/setup/SetupCompleteStep.vue'

const theme = useTheme()

// State
const currentStep = ref(1)
const isRestarting = ref(false)
const restartMessage = ref('Saving configuration...')
const showLanConfirmModal = ref(false)
const showApiKeyModal = ref(false)
const showRestartModal = ref(false)
const generatedApiKey = ref(null)
const apiKeyCopied = ref(false)
const apiKeyConfirmed = ref(false)
const installationPath = ref('(project directory)')  // Fallback if API fails
const detectedPlatform = ref('windows')
const config = ref({
  deploymentMode: 'localhost', // 'localhost' | 'lan'
  aiTools: [],
  serenaEnabled: false,
  lanSettings: null,
})

// Computed
const logoSrc = computed(() =>
  theme.global.current.value.dark ? '/Giljo_YW.svg' : '/Giljo_BY.svg',
)

const stepperItems = computed(() => [
  { title: 'Database', value: 1 },
  { title: 'Attach Tools', value: 2 },
  { title: 'Serena MCP', value: 3 },
  { title: 'Network', value: 4 },
  { title: 'Complete', value: 5 },
])

const platform = computed(() => {
  return detectedPlatform.value
})

const restartInstructions = computed(() => {
  const instructions = {
    windows: [
      'Open Command Prompt or PowerShell',
      `Navigate to ${installationPath.value}`,
      'Run: stop_giljo.bat',
      'Run: start_giljo.bat',
      'Wait 10-15 seconds for services to start',
    ],
    macos: [
      'Open Terminal',
      `Navigate to ${installationPath.value}`,
      'Run: ./stop_giljo.sh',
      'Run: ./start_giljo.sh',
      'Wait 10-15 seconds',
    ],
    linux: [
      'Open Terminal',
      `Navigate to ${installationPath.value}`,
      'Run: ./stop_giljo.sh',
      'Run: ./start_giljo.sh',
      'Wait 10-15 seconds',
    ],
  }
  return instructions[platform.value]
})

// Methods
const handleDatabaseNext = () => {
  currentStep.value = 2
}

const handleToolsNext = () => {
  currentStep.value = 3
}

const handleSerenaNext = (data) => {
  config.value.serenaEnabled = data.serenaEnabled
  currentStep.value = 4
}

const handleNetworkNext = () => {
  currentStep.value = 5
}

const handleBack = () => {
  currentStep.value--
}

const handleFinish = async () => {
  // For LAN mode, show confirmation modal first
  if (config.value.deploymentMode === 'lan') {
    showLanConfirmModal.value = true
    return
  }

  // For localhost mode, proceed directly
  await saveSetupConfig()
}

const cancelLanConfig = () => {
  showLanConfirmModal.value = false
  // User stays on summary screen
}

const confirmLanConfig = async () => {
  showLanConfirmModal.value = false
  await saveSetupConfig()
}

const saveSetupConfig = async () => {
  try {
    console.log('[WIZARD] Completing setup with config:', config.value)
    console.log('[WIZARD] Config details:', {
      deploymentMode: config.value.deploymentMode,
      aiTools: config.value.aiTools,
      serenaEnabled: config.value.serenaEnabled,
      lanSettings: config.value.lanSettings,
    })

    // Show completion overlay
    isRestarting.value = true
    restartMessage.value = 'Saving configuration...'

    // Save setup completion
    const result = await setupService.completeSetup(config.value)
    console.log('[WIZARD] Setup marked as complete:', result)

    // Hide completion overlay
    isRestarting.value = false

    if (result.api_key) {
      // LAN mode - show API key modal
      generatedApiKey.value = result.api_key
      showApiKeyModal.value = true
    } else if (result.requires_restart) {
      // Localhost mode but requires restart
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

const copyApiKey = () => {
  navigator.clipboard.writeText(generatedApiKey.value)
  apiKeyCopied.value = true
  setTimeout(() => {
    apiKeyCopied.value = false
  }, 3000)
}

const proceedToRestart = () => {
  showApiKeyModal.value = false
  showRestartModal.value = true
}

const finishSetup = () => {
  showRestartModal.value = false
  // Set flag in localStorage to show LAN welcome banner
  if (config.value.deploymentMode === 'lan') {
    localStorage.setItem('giljo_lan_setup_complete', 'true')
  }
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

  // Allow wizard to run even if setup was previously completed
  // (user clicked "Re-run Setup Wizard" button)
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
</style>
