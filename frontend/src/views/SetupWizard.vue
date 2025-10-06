<template>
  <v-container class="setup-wizard" fluid>
    <!-- Restart Overlay -->
    <v-overlay
      v-model="isRestarting"
      :persistent="true"
      class="align-center justify-center"
    >
      <v-card class="pa-8 text-center" min-width="400">
        <v-progress-circular
          indeterminate
          size="64"
          color="primary"
          class="mb-4"
        />
        <h3 class="text-h5 mb-2">Restarting Services...</h3>
        <p class="text-body-1 text-medium-emphasis mb-4">
          {{ restartMessage }}
        </p>
        <v-progress-linear
          indeterminate
          color="primary"
        />
      </v-card>
    </v-overlay>

    <v-row justify="center">
      <v-col cols="12" md="10" lg="8" xl="6">
        <v-card class="wizard-card" elevation="4">
          <!-- Logo Header -->
          <v-card-title class="text-center pa-6">
            <v-img
              :src="logoSrc"
              alt="GiljoAI Logo"
              height="60"
              contain
            />
          </v-card-title>

          <!-- Vuetify Stepper -->
          <v-stepper
            v-model="currentStep"
            :items="stepperItems"
            alt-labels
            flat
          >
            <!-- Step 1: Welcome -->
            <v-stepper-window-item :value="1">
              <WelcomeStep @next="handleWelcomeNext" />
            </v-stepper-window-item>

            <!-- Step 2: Database -->
            <v-stepper-window-item :value="2">
              <DatabaseStep
                @next="handleDatabaseNext"
                @back="handleBack"
              />
            </v-stepper-window-item>

            <!-- Step 3: Deployment Mode -->
            <v-stepper-window-item :value="3">
              <DeploymentModeStep
                v-model="config.deploymentMode"
                @next="handleDeploymentModeNext"
                @back="handleBack"
              />
            </v-stepper-window-item>

            <!-- Step 4: Admin Account (conditional - LAN only) -->
            <v-stepper-window-item
              v-if="isLanMode"
              :value="4"
            >
              <AdminAccountStep
                v-model="config.adminAccount"
                @next="handleAdminAccountNext"
                @back="handleBack"
              />
            </v-stepper-window-item>

            <!-- Step 5/4: AI Tools -->
            <v-stepper-window-item :value="toolsStepNumber">
              <ToolIntegrationStep
                v-model="config.aiTools"
                :deployment-mode="config.deploymentMode"
                @next="handleToolsNext"
                @back="handleBack"
              />
            </v-stepper-window-item>

            <!-- Step 6: LAN Config (conditional - LAN only) -->
            <v-stepper-window-item
              v-if="isLanMode"
              :value="6"
            >
              <LanConfigStep
                v-model="config.lanSettings"
                @next="handleLanConfigNext"
                @back="handleBack"
              />
            </v-stepper-window-item>

            <!-- Step 7/5: Complete -->
            <v-stepper-window-item :value="completeStepNumber">
              <CompleteStep
                :config="config"
                @finish="handleFinish"
              />
            </v-stepper-window-item>
          </v-stepper>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useTheme } from 'vuetify'
import setupService from '@/services/setupService'
import WelcomeStep from '@/components/setup/WelcomeStep.vue'
import DatabaseStep from '@/components/setup/DatabaseStep.vue'
import DeploymentModeStep from '@/components/setup/DeploymentModeStep.vue'
import AdminAccountStep from '@/components/setup/AdminAccountStep.vue'
import ToolIntegrationStep from '@/components/setup/ToolIntegrationStep.vue'
import LanConfigStep from '@/components/setup/LanConfigStep.vue'
import CompleteStep from '@/components/setup/CompleteStep.vue'

const theme = useTheme()

// State
const currentStep = ref(1)
const isRestarting = ref(false)
const restartMessage = ref("Please wait while services restart...")
const config = ref({
  deploymentMode: 'localhost', // 'localhost' | 'lan' | 'wan'
  adminAccount: null,
  aiTools: [],
  lanSettings: null,
  databaseVerified: false
})

// Computed
const isLanMode = computed(() => config.value.deploymentMode === 'lan')

const logoSrc = computed(() =>
  theme.global.current.value.dark ? '/Giljo_YW.svg' : '/Giljo_BY.svg'
)

// Dynamic step numbers based on mode
const toolsStepNumber = computed(() => isLanMode.value ? 5 : 4)
const completeStepNumber = computed(() => isLanMode.value ? 7 : 5)

const stepperItems = computed(() => {
  const items = [
    { title: 'Welcome', value: 1 },
    { title: 'Database', value: 2 },
    { title: 'Mode', value: 3 }
  ]

  if (isLanMode.value) {
    items.push({ title: 'Admin', value: 4 })
  }

  items.push({ title: 'AI Tools', value: toolsStepNumber.value })

  if (isLanMode.value) {
    items.push({ title: 'Network', value: 6 })
  }

  items.push({ title: 'Complete', value: completeStepNumber.value })

  return items
})

// Methods
const handleWelcomeNext = () => {
  currentStep.value = 2
}

const handleDatabaseNext = () => {
  config.value.databaseVerified = true
  currentStep.value = 3
}

const handleDeploymentModeNext = () => {
  if (isLanMode.value) {
    currentStep.value = 4 // Admin account
  } else {
    currentStep.value = toolsStepNumber.value // AI tools
  }
}

const handleAdminAccountNext = () => {
  currentStep.value = toolsStepNumber.value
}

const handleToolsNext = () => {
  if (isLanMode.value) {
    currentStep.value = 6 // LAN config
  } else {
    currentStep.value = completeStepNumber.value
  }
}

const handleLanConfigNext = () => {
  currentStep.value = completeStepNumber.value
}

const handleBack = () => {
  currentStep.value--
}

const handleFinish = async () => {
  try {
    console.log('[WIZARD] Completing setup...')

    // Show restart overlay
    isRestarting.value = true
    restartMessage.value = 'Saving configuration...'

    // Step 1: Save setup completion flag
    await setupService.completeSetup(config.value)
    console.log('[WIZARD] Setup marked as complete')

    // Step 2: Trigger service restart
    restartMessage.value = 'Restarting services...'
    await setupService.restartServices()
    console.log('[WIZARD] Restart triggered')

    // Step 3: Wait for backend to come back online
    restartMessage.value = 'Waiting for services to restart... (this may take 15 seconds)'
    const backendOnline = await setupService.waitForBackend(30, 1000)

    if (backendOnline) {
      console.log('[WIZARD] Backend is back online!')
      restartMessage.value = 'Services restarted successfully! Redirecting...'

      // Wait 1 second to show success message
      await new Promise(resolve => setTimeout(resolve, 1000))

      // Redirect to main dashboard
      window.location.href = 'http://localhost:7274'
    } else {
      console.error('[WIZARD] Backend did not come back online within timeout')
      restartMessage.value = 'Services are taking longer than expected. Please refresh manually.'

      // Wait 3 seconds then try redirecting anyway
      await new Promise(resolve => setTimeout(resolve, 3000))
      window.location.href = 'http://localhost:7274'
    }
  } catch (error) {
    console.error('[WIZARD] Setup completion/restart failed:', error)
    restartMessage.value = 'Error during restart. Redirecting...'

    // Wait 2 seconds then redirect anyway
    await new Promise(resolve => setTimeout(resolve, 2000))
    window.location.href = 'http://localhost:7274'
  }
}

// Lifecycle
onMounted(async () => {
  console.log('[WIZARD] Component mounted, checking setup status...')

  // Check if setup already completed
  try {
    const status = await setupService.checkStatus()

    if (status.completed) {
      console.log('[WIZARD] Setup already complete, redirecting to dashboard...')
      // Setup already done, redirect to dashboard
      window.location.href = 'http://localhost:7274'
    } else {
      console.log('[WIZARD] Setup not complete, showing wizard')
    }
  } catch (error) {
    // If endpoint doesn't exist yet, continue with wizard
    console.log('[WIZARD] Setup status check unavailable, continuing with wizard')
  }
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
