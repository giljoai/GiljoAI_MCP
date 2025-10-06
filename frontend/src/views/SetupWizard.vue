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
          <!-- Logo Header -->
          <v-card-title class="text-center pa-6">
            <v-img :src="logoSrc" alt="GiljoAI Logo" height="60" contain />
          </v-card-title>

          <!-- Vuetify Stepper -->
          <v-stepper v-model="currentStep" :items="stepperItems" alt-labels flat hide-actions>
            <template v-slot:item.1>
              <v-card flat>
                <AttachToolsStep v-model="config.aiTools" @next="handleToolsNext" />
              </v-card>
            </template>

            <template v-slot:item.2>
              <v-card flat>
                <SerenaAttachStep
                  @next="handleSerenaNext"
                  @back="handleBack"
                />
              </v-card>
            </template>

            <template v-slot:item.3>
              <v-card flat>
                <NetworkConfigStep
                  v-model:mode="config.deploymentMode"
                  v-model:lan-settings="config.lanSettings"
                  @next="handleNetworkNext"
                  @back="handleBack"
                />
              </v-card>
            </template>

            <template v-slot:item.4>
              <v-card flat>
                <SetupCompleteStep :config="config" @finish="handleFinish" />
              </v-card>
            </template>
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
import AttachToolsStep from '@/components/setup/AttachToolsStep.vue'
import SerenaAttachStep from '@/components/setup/SerenaAttachStep.vue'
import NetworkConfigStep from '@/components/setup/NetworkConfigStep.vue'
import SetupCompleteStep from '@/components/setup/SetupCompleteStep.vue'

const theme = useTheme()

// State
const currentStep = ref(1)
const isRestarting = ref(false)
const restartMessage = ref('Saving configuration...')
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
  { title: 'Attach Tools', value: 1 },
  { title: 'Serena MCP', value: 2 },
  { title: 'Network', value: 3 },
  { title: 'Complete', value: 4 },
])

// Methods
const handleToolsNext = () => {
  currentStep.value = 2
}

const handleSerenaNext = (data) => {
  config.value.serenaEnabled = data.serenaEnabled
  currentStep.value = 3
}

const handleNetworkNext = () => {
  currentStep.value = 4
}

const handleBack = () => {
  currentStep.value--
}

const handleFinish = async () => {
  try {
    console.log('[WIZARD] Completing setup with config:', config.value)

    // Show completion overlay
    isRestarting.value = true
    restartMessage.value = 'Saving configuration...'

    // Save setup completion
    await setupService.completeSetup(config.value)
    console.log('[WIZARD] Setup marked as complete')

    restartMessage.value = 'Setup complete! Redirecting to dashboard...'

    // Wait 1 second to show success message
    await new Promise((resolve) => setTimeout(resolve, 1000))

    // Redirect to main dashboard
    window.location.href = 'http://localhost:7274'
  } catch (error) {
    console.error('[WIZARD] Setup completion failed:', error)
    restartMessage.value = 'Error during setup completion. Redirecting...'

    // Wait 2 seconds then redirect anyway
    await new Promise((resolve) => setTimeout(resolve, 2000))
    window.location.href = 'http://localhost:7274'
  }
}

// Lifecycle
onMounted(async () => {
  console.log('[WIZARD] Component mounted')

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
