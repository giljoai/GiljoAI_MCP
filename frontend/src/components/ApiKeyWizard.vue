<template>
  <v-dialog v-model="isOpen" max-width="800" persistent>
    <v-card>
      <v-card-title class="d-flex align-center bg-primary">
        <v-icon class="mr-2">mdi-key-plus</v-icon>
        Generate API Key
      </v-card-title>

      <!-- Step Progress Indicator -->
      <v-card-text class="pa-0">
        <v-stepper v-model="currentStep" alt-labels flat>
          <v-stepper-header>
            <v-stepper-item :complete="currentStep > 1" :value="1" title="Name"></v-stepper-item>
            <v-divider></v-divider>
            <v-stepper-item
              :complete="currentStep > 2"
              :value="2"
              title="Generate"
            ></v-stepper-item>
          </v-stepper-header>
        </v-stepper>
      </v-card-text>

      <!-- Step Content -->
      <v-card-text class="px-6 py-4">
        <!-- Step 1: Name Your Key -->
        <div v-if="currentStep === 1" data-test="step-1">
          <h3 class="text-h6 mb-2">Name Your Integration Key</h3>
          <p class="text-subtitle-2 text-medium-emphasis mb-4">
            Choose a descriptive name for this integration API key
          </p>
          <v-text-field
            v-model="keyName"
            label="Key Name"
            variant="outlined"
            hint="e.g., 'Claude Code CLI', 'Production Bot', 'Development Environment'"
            persistent-hint
            data-test="key-name"
            :error-messages="nameError"
            autofocus
            @input="nameError = ''"
          />
          <v-alert type="info" variant="tonal" class="mt-4" density="compact">
            <v-icon start size="small">mdi-information</v-icon>
            This key will enable AI tools and external applications to access GiljoAI MCP server
            endpoints.
          </v-alert>
        </div>

        <!-- Step 2: Generate & Copy -->
        <div v-if="currentStep === 2" data-test="step-2">
          <h3 class="text-h6 mb-2">Your API Key</h3>
          <p class="text-subtitle-2 text-medium-emphasis mb-4">
            Copy and save this key securely - it will only be shown once!
          </p>

          <v-alert v-if="!generatedKey && !errorMessage" type="info" variant="tonal" class="mb-4">
            Click "Generate Key" to create your new API key
          </v-alert>

          <v-alert v-if="errorMessage" type="error" variant="tonal" class="mb-4">
            {{ errorMessage }}
          </v-alert>

          <div v-if="generatedKey">
            <v-alert type="warning" variant="tonal" prominent class="mb-4">
              <v-alert-title class="text-h6 mb-2">
                <v-icon start>mdi-shield-alert</v-icon>
                Save this key now!
              </v-alert-title>
              This API key will only be shown ONCE. After closing this wizard, you will not be able
              to retrieve it again.
            </v-alert>

            <v-text-field
              :model-value="generatedKey"
              label="API Key"
              variant="outlined"
              readonly
              class="mb-4"
              data-test="generated-key"
            >
              <template #append-inner>
                <v-btn
                  icon="mdi-content-copy"
                  size="small"
                  variant="text"
                  color="primary"
                  @click="copyKey"
                >
                  <v-icon>mdi-content-copy</v-icon>
                  <v-tooltip activator="parent">Copy API key</v-tooltip>
                </v-btn>
              </template>
            </v-text-field>

            <v-alert v-if="copiedKey" type="success" variant="tonal" density="compact" class="mb-4">
              <v-icon start size="small">mdi-check-circle</v-icon>
              API key copied to clipboard!
            </v-alert>

            <v-divider class="my-4" />

            <h3 class="text-subtitle-1 mb-2">Configuration Snippet</h3>
            <p class="text-caption mb-3">
              Use this configuration for your AI tools and integrations:
            </p>

            <ToolConfigSnippet :config="configSnippet" :language="configLanguage" />

            <v-divider class="my-4" />

            <v-checkbox
              v-model="confirmSaved"
              label="I have copied and saved this key securely"
              color="primary"
              density="compact"
              data-test="key-saved-confirm"
            />
          </div>
        </div>
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-btn v-if="currentStep > 1 && !generatedKey" variant="text" @click="previousStep">
          Back
        </v-btn>
        <v-spacer />
        <v-btn variant="text" @click="close" :disabled="generating">Cancel</v-btn>

        <v-btn v-if="currentStep < 2" color="primary" @click="nextStep" data-test="next-button">
          Next
        </v-btn>

        <v-btn
          v-if="currentStep === 2 && !generatedKey"
          color="primary"
          @click="generateApiKey"
          :loading="generating"
          data-test="generate-button"
        >
          Generate Key
        </v-btn>

        <v-btn
          v-if="currentStep === 2 && generatedKey"
          color="primary"
          @click="finish"
          :disabled="!confirmSaved"
          data-test="finish-button"
        >
          Finish
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import api from '@/services/api'
import ToolConfigSnippet from './ToolConfigSnippet.vue'
import {
  generateClaudeCodeConfig,
  generateCodexConfig,
  generateGenericConfig,
} from '@/utils/configTemplates'
import { getPythonPath, detectOS } from '@/utils/pathDetection'

// Props
const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
})

// Emits
const emit = defineEmits(['update:modelValue', 'key-created'])

// Computed
const isOpen = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

// State
const currentStep = ref(1)
const keyName = ref('')
const nameError = ref('')
// selectedTool removed - using single integration key type
const generatedKey = ref(null)
const configSnippet = ref('')
const configLanguage = ref('json')
const confirmSaved = ref(false)
const copiedKey = ref(false)
const errorMessage = ref('')
const generating = ref(false)

// Tools configuration removed - using single integration key type

// Methods
function validateName() {
  if (!keyName.value) {
    nameError.value = 'Key name is required'
    return false
  }
  if (keyName.value.length < 3) {
    nameError.value = 'Name must be at least 3 characters'
    return false
  }
  if (keyName.value.length > 255) {
    nameError.value = 'Name must be less than 255 characters'
    return false
  }
  nameError.value = ''
  return true
}

function nextStep() {
  if (currentStep.value === 1) {
    if (!validateName()) return
  }
  currentStep.value++
}

function previousStep() {
  if (currentStep.value > 1) {
    currentStep.value--
  }
}

// selectTool and getSelectedToolName functions removed - using single integration key type

async function generateApiKey() {
  generating.value = true
  errorMessage.value = ''

  try {
    // Use authenticated API client (includes cookies and tenant key)
    const response = await api.apiKeys.create(keyName.value)

    generatedKey.value = response.data.api_key

    // Generate config snippet for integration use (v3.0 dynamic URL)
    const serverUrl = `${window.location.protocol}//${window.location.hostname}:7272`
    const projectPath = 'F:/GiljoAI_MCP'
    const pythonPath = getPythonPath(projectPath, detectOS())

    // Default to Claude Code config for integration keys
    configSnippet.value = generateClaudeCodeConfig(generatedKey.value, serverUrl, pythonPath)
    configLanguage.value = 'json'
  } catch (err) {
    console.error('Failed to generate API key:', err)
    errorMessage.value = 'Failed to generate API key. Please try again.'
    generatedKey.value = null
  } finally {
    generating.value = false
  }
}

async function copyKey() {
  try {
    await navigator.clipboard.writeText(generatedKey.value)
    copiedKey.value = true

    setTimeout(() => {
      copiedKey.value = false
    }, 2000)
  } catch (err) {
    console.error('Failed to copy key:', err)
  }
}

function finish() {
  if (!confirmSaved.value) return

  emit('key-created')
  reset()
  isOpen.value = false
}

function close() {
  if (generatedKey.value && !confirmSaved.value) {
    if (!confirm('Are you sure? You will lose access to this API key if you close now.')) {
      return
    }
  }
  reset()
  isOpen.value = false
}

function reset() {
  currentStep.value = 1
  keyName.value = ''
  nameError.value = ''
  generatedKey.value = null
  configSnippet.value = ''
  confirmSaved.value = false
  copiedKey.value = false
  errorMessage.value = ''
}

// Watch for dialog close
watch(isOpen, (newValue) => {
  if (!newValue) {
    reset()
  }
})
</script>

<style scoped>
.tool-card {
  cursor: pointer;
  transition: all 0.2s ease;
}

.tool-card:hover:not(:disabled) {
  transform: translateY(-4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.tool-card-selected {
  border-width: 2px;
}

.tool-card:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Accessibility: Focus indicators */
.tool-card:focus-visible {
  outline: 2px solid rgba(var(--v-theme-primary), 0.5);
  outline-offset: 2px;
}

.v-btn:focus-visible {
  outline: 2px solid rgba(var(--v-theme-primary), 0.5);
  outline-offset: 2px;
}
</style>
