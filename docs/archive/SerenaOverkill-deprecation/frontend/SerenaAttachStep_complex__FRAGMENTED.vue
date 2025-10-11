<template>
  <v-card-text class="pa-8">
    <h2 class="text-h5 mb-2">Advanced Code Analysis (Optional)</h2>
    <p class="text-body-1 mb-6">Enhance your coding agents with Serena MCP's semantic code tools</p>

    <!-- Main Card -->
    <v-card variant="outlined" class="serena-card" :class="{ 'serena-configured': isConfigured }">
      <!-- State: Not Detected -->
      <v-card-text v-if="state === 'not_detected'" class="d-flex flex-column align-center pa-6">
        <v-icon size="64" color="warning" class="mb-4">mdi-code-braces-box</v-icon>
        <h3 class="text-h6 mb-2">Serena MCP Not Detected</h3>
        <p class="text-body-2 text-center text-medium-emphasis mb-4">
          Serena MCP provides semantic code analysis, symbol search, and intelligent code
          navigation.
        </p>

        <div class="d-flex gap-2 mt-2">
          <v-btn
            color="primary"
            variant="outlined"
            @click="openInstallDialog"
            aria-label="Open installation instructions"
          >
            <v-icon start>mdi-help-circle</v-icon>
            How to Install
          </v-btn>
          <v-btn variant="text" @click="handleSkip" aria-label="Skip Serena MCP setup">
            Skip
          </v-btn>
        </div>
      </v-card-text>

      <!-- State: Detected -->
      <v-card-text v-if="state === 'detected'" class="d-flex flex-column align-center pa-6">
        <v-icon size="64" color="success" class="mb-4">mdi-check-circle</v-icon>
        <h3 class="text-h6 mb-2">Serena MCP Detected</h3>
        <v-chip size="small" color="success" variant="tonal" class="mb-4"> Detected </v-chip>
        <p class="text-body-2 text-center text-medium-emphasis mb-4">
          Serena MCP is installed and ready to attach to Claude Code.
        </p>

        <v-btn
          color="primary"
          variant="flat"
          :loading="attaching"
          @click="attachSerena"
          aria-label="Attach Serena MCP"
        >
          <v-icon start>mdi-link-variant-plus</v-icon>
          Attach to Claude Code
        </v-btn>
      </v-card-text>

      <!-- State: Configured -->
      <v-card-text v-if="state === 'configured'" class="d-flex flex-column align-center pa-6">
        <v-icon size="64" color="success" class="mb-4">mdi-check-decagram</v-icon>
        <h3 class="text-h6 mb-2">Serena MCP Configured</h3>
        <v-chip size="small" color="success" variant="flat" class="mb-4"> Configured </v-chip>

        <v-alert type="success" variant="tonal" density="compact" class="mt-2">
          <div class="text-caption">
            <strong>Next:</strong> Relaunch Claude Code CLI and use semantic code tools
          </div>
        </v-alert>
      </v-card-text>
    </v-card>

    <!-- Error Alert -->
    <v-alert
      v-if="errorMessage"
      type="error"
      variant="tonal"
      class="mt-4"
      closable
      @click:close="errorMessage = ''"
    >
      {{ errorMessage }}
    </v-alert>

    <!-- Info Alert -->
    <v-alert type="info" variant="tonal" class="mt-6">
      <v-icon start>mdi-information</v-icon>
      Serena MCP is optional but enhances agent capabilities with semantic code analysis, symbol
      search, and intelligent navigation.
    </v-alert>

    <!-- Progress Indicator -->
    <v-card variant="outlined" class="mt-6 mb-6">
      <v-card-text>
        <div class="d-flex justify-space-between mb-2">
          <span class="text-caption">Progress: Step 2 of 4</span>
          <span class="text-caption">50%</span>
        </div>
        <v-progress-linear :model-value="50" color="primary" />
      </v-card-text>
    </v-card>

    <!-- Navigation -->
    <div class="d-flex justify-space-between">
      <v-btn variant="text" @click="handleBack" aria-label="Go back to previous step">
        <v-icon start>mdi-arrow-left</v-icon>
        Back
      </v-btn>
      <v-btn color="primary" @click="handleNext" aria-label="Continue to next step">
        Continue
        <v-icon end>mdi-arrow-right</v-icon>
      </v-btn>
    </div>

    <!-- Installation Dialog -->
    <v-dialog v-model="showInstallDialog" max-width="600">
      <v-card>
        <v-card-title class="d-flex justify-space-between align-center">
          <span>Install Serena MCP</span>
          <v-btn
            icon="mdi-close"
            variant="text"
            size="small"
            @click="showInstallDialog = false"
            aria-label="Close installation dialog"
          />
        </v-card-title>

        <v-card-text>
          <v-tabs v-model="installTab" class="mb-4">
            <v-tab value="uvx">Using uvx (Recommended)</v-tab>
            <v-tab value="local">Local Installation</v-tab>
          </v-tabs>

          <v-tabs-window v-model="installTab">
            <v-tabs-window-item value="uvx">
              <div class="installation-instructions">
                <p class="text-body-2 mb-4">
                  Install Serena MCP using <code>uvx</code> (recommended for simplicity):
                </p>

                <v-card variant="outlined" class="mb-4">
                  <v-card-text>
                    <code class="code-block">uvx mcp-server-serena</code>
                  </v-card-text>
                </v-card>

                <p class="text-body-2 text-medium-emphasis">
                  This will install Serena MCP globally and make it available to Claude Code.
                </p>
              </div>
            </v-tabs-window-item>

            <v-tabs-window-item value="local">
              <div class="installation-instructions">
                <p class="text-body-2 mb-4">Clone and install Serena MCP from source:</p>

                <v-card variant="outlined" class="mb-2">
                  <v-card-text>
                    <code class="code-block"
                      >git clone https://github.com/apify/mcp-server-serena.git</code
                    >
                  </v-card-text>
                </v-card>

                <v-card variant="outlined" class="mb-2">
                  <v-card-text>
                    <code class="code-block">cd mcp-server-serena</code>
                  </v-card-text>
                </v-card>

                <v-card variant="outlined" class="mb-4">
                  <v-card-text>
                    <code class="code-block">uv sync</code>
                  </v-card-text>
                </v-card>

                <p class="text-body-2 text-medium-emphasis">
                  This creates a local installation that can be configured manually.
                </p>
              </div>
            </v-tabs-window-item>
          </v-tabs-window>

          <v-divider class="my-4" />

          <v-btn
            color="primary"
            variant="text"
            :loading="checking"
            @click="checkAgain"
            aria-label="Re-check Serena installation"
          >
            <v-icon start>mdi-refresh</v-icon>
            Check Again
          </v-btn>
        </v-card-text>
      </v-card>
    </v-dialog>
  </v-card-text>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import setupService from '@/services/setupService'

/**
 * SerenaAttachStep - Serena MCP detection and attachment step (Step 2 of 4)
 *
 * Handles detection, installation guidance, and attachment of Serena MCP
 */

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:modelValue', 'next', 'back', 'skip'])

// State
const state = ref('not_detected') // 'not_detected' | 'detected' | 'configured'
const isConfigured = ref(false)
const attaching = ref(false)
const checking = ref(false)
const errorMessage = ref('')
const showInstallDialog = ref(false)
const installTab = ref('uvx')

// Methods
const detectSerena = async () => {
  checking.value = true
  errorMessage.value = ''

  try {
    const result = await setupService.detectSerena()

    if (result.installed) {
      state.value = 'detected'
      console.log('[SERENA_ATTACH] Serena detected')
    } else {
      state.value = 'not_detected'
      console.log('[SERENA_ATTACH] Serena not detected')
    }
  } catch (error) {
    console.error('[SERENA_ATTACH] Detection failed:', error)
    errorMessage.value = `Detection failed: ${error.message}`
  } finally {
    checking.value = false
  }
}

const attachSerena = async () => {
  attaching.value = true
  errorMessage.value = ''

  try {
    console.log('[SERENA_ATTACH] Attaching Serena MCP to Claude Code...')
    const result = await setupService.attachSerena()

    if (result.success) {
      state.value = 'configured'
      isConfigured.value = true
      emit('update:modelValue', true)
      console.log('[SERENA_ATTACH] Serena attached successfully')
    } else {
      errorMessage.value = result.error || 'Failed to attach Serena MCP'
      console.error('[SERENA_ATTACH] Attachment failed:', result.error)
    }
  } catch (error) {
    console.error('[SERENA_ATTACH] Attachment error:', error)
    errorMessage.value = `Attachment failed: ${error.message}`
  } finally {
    attaching.value = false
  }
}

const checkAgain = () => {
  console.log('[SERENA_ATTACH] Re-checking Serena installation...')
  detectSerena()
}

const handleNext = () => {
  console.log('[SERENA_ATTACH] Moving to next step')
  emit('next')
}

const handleBack = () => {
  console.log('[SERENA_ATTACH] Going back to previous step')
  emit('back')
}

const handleSkip = () => {
  console.log('[SERENA_ATTACH] Skipping Serena MCP setup')
  emit('skip')
}

const openInstallDialog = () => {
  showInstallDialog.value = true
}

// Lifecycle
onMounted(() => {
  console.log('[SERENA_ATTACH] Component mounted, detecting Serena...')
  detectSerena()
})
</script>

<style scoped>
h2 {
  color: rgb(var(--v-theme-primary));
}

.serena-card {
  transition: all 0.2s ease;
  border-width: 2px;
}

.serena-card:hover {
  border-color: rgb(var(--v-theme-primary));
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.serena-configured {
  border-color: rgb(var(--v-theme-success));
  background-color: rgba(var(--v-theme-success), 0.05);
}

code {
  background-color: rgba(var(--v-theme-surface-variant), 0.5);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
}

.code-block {
  display: block;
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
  padding: 0;
  background: none;
}

.installation-instructions {
  padding: 0.5rem 0;
}

.gap-2 {
  gap: 0.5rem;
}
</style>
