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
            <v-stepper-item :complete="currentStep > 2" :value="2" title="Tool"></v-stepper-item>
            <v-divider></v-divider>
            <v-stepper-item :complete="currentStep > 3" :value="3" title="Generate"></v-stepper-item>
          </v-stepper-header>
        </v-stepper>
      </v-card-text>

      <!-- Step Content -->
      <v-card-text class="px-6 py-4">
        <!-- Step 1: Name Your Key -->
        <div v-if="currentStep === 1" data-test="step-1">
          <h3 class="text-h6 mb-2">Name Your API Key</h3>
          <p class="text-subtitle-2 text-medium-emphasis mb-4">Choose a descriptive name for this API key</p>
          <v-text-field
            v-model="keyName"
            label="Key Name"
            variant="outlined"
            hint="e.g., 'Production Server', 'Dev Environment', 'Claude Code Integration'"
            persistent-hint
            data-test="key-name"
            :error-messages="nameError"
            autofocus
            @input="nameError = ''"
          />
        </div>

        <!-- Step 2: Select Tool -->
        <div v-if="currentStep === 2" data-test="step-2">
          <h3 class="text-h6 mb-2">Select Your Tool</h3>
          <p class="text-subtitle-2 text-medium-emphasis mb-4">Choose the tool you'll use with this API key</p>
          <v-row>
            <v-col
              v-for="tool in tools"
              :key="tool.id"
              cols="12"
              sm="6"
            >
              <v-card
                :variant="selectedTool === tool.id ? 'elevated' : 'outlined'"
                :color="selectedTool === tool.id ? 'primary' : ''"
                :class="{ 'tool-card-selected': selectedTool === tool.id }"
                class="tool-card"
                :data-test="`tool-${tool.id}`"
                @click="selectTool(tool.id)"
                :disabled="!tool.available"
              >
                <v-card-text class="text-center">
                  <v-icon size="48" :class="{ 'mb-2': true, 'text-disabled': !tool.available }">
                    {{ tool.icon }}
                  </v-icon>
                  <h3 class="text-h6">{{ tool.name }}</h3>
                  <p class="text-caption mt-2">{{ tool.description }}</p>
                  <v-chip
                    v-if="!tool.available"
                    size="small"
                    color="warning"
                    class="mt-2"
                  >
                    Coming Soon
                  </v-chip>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
        </div>

        <!-- Step 3: Generate & Copy -->
        <div v-if="currentStep === 3" data-test="step-3">
          <h3 class="text-h6 mb-2">Your API Key</h3>
          <p class="text-subtitle-2 text-medium-emphasis mb-4">
            Copy and save this key securely - it will only be shown once!
          </p>

          <v-alert
            v-if="!generatedKey && !errorMessage"
            type="info"
            variant="tonal"
            class="mb-4"
          >
            Click "Generate Key" to create your new API key
          </v-alert>

          <v-alert
            v-if="errorMessage"
            type="error"
            variant="tonal"
            class="mb-4"
          >
            {{ errorMessage }}
          </v-alert>

          <div v-if="generatedKey">
            <v-alert type="warning" variant="tonal" prominent class="mb-4">
              <v-alert-title class="text-h6 mb-2">
                <v-icon start>mdi-shield-alert</v-icon>
                Save this key now!
              </v-alert-title>
              This API key will only be shown ONCE. After closing this wizard, you will not
              be able to retrieve it again.
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

            <v-alert
              v-if="copiedKey"
              type="success"
              variant="tonal"
              density="compact"
              class="mb-4"
            >
              <v-icon start size="small">mdi-check-circle</v-icon>
              API key copied to clipboard!
            </v-alert>

            <v-divider class="my-4" />

            <h3 class="text-subtitle-1 mb-2">Configuration Snippet</h3>
            <p class="text-caption mb-3">
              Use this configuration for {{ getSelectedToolName() }}:
            </p>

            <ToolConfigSnippet
              :config="configSnippet"
              :language="configLanguage"
            />

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
        <v-btn
          v-if="currentStep > 1 && !generatedKey"
          variant="text"
          @click="previousStep"
        >
          Back
        </v-btn>
        <v-spacer />
        <v-btn variant="text" @click="close" :disabled="generating">Cancel</v-btn>

        <v-btn
          v-if="currentStep < 3"
          color="primary"
          @click="nextStep"
          data-test="next-button"
        >
          Next
        </v-btn>

        <v-btn
          v-if="currentStep === 3 && !generatedKey"
          color="primary"
          @click="generateApiKey"
          :loading="generating"
          data-test="generate-button"
        >
          Generate Key
        </v-btn>

        <v-btn
          v-if="currentStep === 3 && generatedKey"
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
import axios from 'axios'
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
const selectedTool = ref('')
const generatedKey = ref(null)
const configSnippet = ref('')
const configLanguage = ref('json')
const confirmSaved = ref(false)
const copiedKey = ref(false)
const errorMessage = ref('')
const generating = ref(false)

// Tools configuration
const tools = [
  {
    id: 'claude-code',
    name: 'Claude Code',
    icon: 'mdi-code-json',
    configFile: '.claude.json',
    description: 'Configure your Claude Code MCP server',
    available: true,
  },
  {
    id: 'codex',
    name: 'Codex CLI',
    icon: 'mdi-console',
    configFile: 'config.toml',
    description: 'Command-line tool for AI development',
    available: false,
  },
  {
    id: 'gemini',
    name: 'Gemini',
    icon: 'mdi-google',
    configFile: 'config.json',
    description: "Google's AI assistant",
    available: false,
  },
  {
    id: 'other',
    name: 'Other',
    icon: 'mdi-wrench',
    configFile: 'Generic',
    description: 'Custom API integration',
    available: true,
  },
]

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
  if (currentStep.value === 2) {
    if (!selectedTool.value) return
  }
  currentStep.value++
}

function previousStep() {
  if (currentStep.value > 1) {
    currentStep.value--
  }
}

function selectTool(toolId) {
  const tool = tools.find((t) => t.id === toolId)
  if (tool && tool.available) {
    selectedTool.value = toolId
  }
}

function getSelectedToolName() {
  const tool = tools.find((t) => t.id === selectedTool.value)
  return tool ? tool.name : 'this tool'
}

async function generateApiKey() {
  generating.value = true
  errorMessage.value = ''

  try {
    // Create axios instance (mocked in tests)
    const apiClient = axios.create()

    const response = await apiClient.post('/api/auth/api-keys', {
      name: keyName.value,
      tool: selectedTool.value,
    })

    generatedKey.value = response.data.key

    // Generate config snippet based on selected tool
    const serverUrl = 'http://localhost:7272'
    const projectPath = 'F:/GiljoAI_MCP'
    const pythonPath = getPythonPath(projectPath, detectOS())

    if (selectedTool.value === 'claude-code') {
      configSnippet.value = generateClaudeCodeConfig(
        generatedKey.value,
        serverUrl,
        pythonPath
      )
      configLanguage.value = 'json'
    } else if (selectedTool.value === 'codex') {
      configSnippet.value = generateCodexConfig(generatedKey.value)
      configLanguage.value = 'toml'
    } else {
      configSnippet.value = generateGenericConfig(generatedKey.value, serverUrl)
      configLanguage.value = 'bash'
    }
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
  selectedTool.value = ''
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
