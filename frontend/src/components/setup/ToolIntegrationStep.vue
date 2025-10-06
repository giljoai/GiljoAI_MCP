<template>
  <v-card-text class="pa-8">
    <h2 class="text-h5 mb-2">Configure AI Tool Integration</h2>
    <p class="text-body-1 mb-6">Connect GiljoAI MCP with your AI coding assistants</p>

    <!-- Loading state -->
    <div v-if="detecting" class="text-center py-8">
      <v-progress-circular indeterminate color="primary" size="64" />
      <p class="text-body-1 mt-4">Detecting installed AI coding tools...</p>
    </div>

    <!-- Tool cards -->
    <div v-else>
      <v-card v-for="tool in tools" :key="tool.id" variant="outlined" class="mb-4 tool-card">
        <v-card-text>
          <div class="d-flex align-center justify-space-between">
            <!-- Tool info -->
            <div class="flex-grow-1">
              <div class="d-flex align-center">
                <v-icon :color="tool.detected ? 'success' : 'error'" size="large" class="mr-3">
                  {{ tool.detected ? 'mdi-check-circle' : 'mdi-close-circle' }}
                </v-icon>
                <div>
                  <div class="text-h6">
                    {{ tool.name }}
                    <v-chip
                      v-if="toolStates[tool.id]?.configured"
                      size="small"
                      color="success"
                      class="ml-2"
                    >
                      Configured
                    </v-chip>
                  </div>
                  <div v-if="tool.detected" class="text-caption text-medium-emphasis">
                    Version: {{ tool.version }} | Path: {{ truncatePath(tool.path) }}
                  </div>
                  <div v-else class="text-caption text-medium-emphasis">
                    Not detected - Install {{ tool.name }} or configure manually
                  </div>
                </div>
              </div>

              <!-- Test result -->
              <v-alert
                v-if="toolStates[tool.id]?.testResult"
                :type="toolStates[tool.id].testResult.success ? 'success' : 'error'"
                variant="tonal"
                density="compact"
                class="mt-3"
              >
                {{ toolStates[tool.id].testResult.message }}
              </v-alert>
            </div>

            <!-- Action buttons -->
            <div class="ml-4">
              <v-btn
                v-if="tool.detected && !toolStates[tool.id]?.configured"
                variant="outlined"
                color="primary"
                :loading="toolStates[tool.id]?.configuring"
                @click="handleConfigure(tool)"
              >
                Configure
              </v-btn>
              <v-btn
                v-if="toolStates[tool.id]?.configured"
                variant="outlined"
                :loading="toolStates[tool.id]?.testing"
                @click="handleTest(tool)"
              >
                Test
              </v-btn>
              <v-btn
                v-if="toolStates[tool.id]?.configured"
                variant="text"
                size="small"
                @click="handleReconfigure(tool)"
              >
                Reconfigure
              </v-btn>
            </div>
          </div>
        </v-card-text>
      </v-card>

      <!-- Info message -->
      <v-alert type="info" variant="tonal" class="mb-6">
        <v-icon start>mdi-information</v-icon>
        You can configure additional tools later in Settings &gt; AI Tools
      </v-alert>
    </div>

    <!-- Config Preview Dialog -->
    <v-dialog v-model="configDialog" max-width="800">
      <v-card>
        <v-card-title class="d-flex justify-space-between align-center">
          <span>Configuration Preview: {{ selectedTool?.name }}</span>
          <v-btn icon variant="text" @click="configDialog = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>

        <v-card-text>
          <v-alert type="info" variant="tonal" class="mb-4">
            <strong>This configuration will be written to:</strong>
            <div class="text-caption mt-1">
              {{ configPath }}
            </div>
          </v-alert>

          <v-card variant="outlined" class="mb-4">
            <v-card-text>
              <pre class="config-preview">{{ JSON.stringify(generatedConfig, null, 2) }}</pre>
            </v-card-text>
          </v-card>

          <v-alert type="warning" variant="tonal">
            <v-icon start>mdi-alert</v-icon>
            This will modify your tool configuration. A backup will be created automatically.
          </v-alert>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn variant="outlined" @click="configDialog = false"> Cancel </v-btn>
          <v-btn color="primary" :loading="applying" @click="applyConfiguration">
            Apply Configuration
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Progress -->
    <v-card variant="outlined" class="mb-6">
      <v-card-text>
        <div class="d-flex justify-space-between mb-2">
          <span class="text-caption">
            Progress: Step {{ isLanMode ? '5' : '4' }} of {{ isLanMode ? '7' : '5' }}
          </span>
          <span class="text-caption">{{ isLanMode ? '71%' : '80%' }}</span>
        </div>
        <v-progress-linear :model-value="isLanMode ? 71 : 80" color="primary" />
      </v-card-text>
    </v-card>

    <!-- Navigation -->
    <div class="d-flex justify-space-between">
      <v-btn variant="outlined" @click="$emit('back')" aria-label="Go back">
        <v-icon start>mdi-arrow-left</v-icon>
        Back
      </v-btn>
      <div>
        <v-btn v-if="!hasConfiguredTools" variant="text" @click="handleSkip" class="mr-2">
          Skip This Step
        </v-btn>
        <v-btn
          color="primary"
          :disabled="!canProceed"
          @click="$emit('next')"
          aria-label="Continue to next step"
        >
          Continue
          <v-icon end>mdi-arrow-right</v-icon>
        </v-btn>
      </div>
    </div>
  </v-card-text>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import setupService from '@/services/setupService'

/**
 * ToolIntegrationStep - AI tool configuration step
 *
 * Detects installed AI tools and generates MCP configurations
 */

const props = defineProps({
  modelValue: {
    type: Array,
    default: () => [],
  },
  deploymentMode: {
    type: String,
    required: true,
  },
})

const emit = defineEmits(['update:modelValue', 'next', 'back'])

// State
const detecting = ref(false)
const tools = ref([])
const toolStates = ref({})
const configDialog = ref(false)
const selectedTool = ref(null)
const generatedConfig = ref(null)
const configPath = ref('')
const applying = ref(false)

const isLanMode = computed(() => props.deploymentMode === 'lan')

const hasConfiguredTools = computed(() => {
  return Object.values(toolStates.value).some((state) => state.configured)
})

const canProceed = computed(() => {
  // Can proceed if at least one tool is configured or user acknowledged skip
  return hasConfiguredTools.value || userSkipped.value
})

const userSkipped = ref(false)

// Methods
const truncatePath = (path) => {
  if (!path) return ''
  if (path.length <= 50) return path
  return '...' + path.substring(path.length - 47)
}

const detectTools = async () => {
  detecting.value = true
  try {
    const result = await setupService.detectTools()
    tools.value = result.tools || []

    // Initialize tool states
    tools.value.forEach((tool) => {
      toolStates.value[tool.id] = {
        configured: false,
        configuring: false,
        testing: false,
        testResult: null,
      }
    })
  } catch (error) {
    console.error('Tool detection failed:', error)
  } finally {
    detecting.value = false
  }
}

const handleConfigure = async (tool) => {
  selectedTool.value = tool
  toolStates.value[tool.id].configuring = true

  try {
    // Generate configuration
    const result = await setupService.generateMcpConfig(tool.name, props.deploymentMode)
    generatedConfig.value = result

    // Set config path based on tool
    if (tool.name === 'Claude Code') {
      configPath.value = `${process.env.USERPROFILE || '~'}/.claude.json`
    } else if (tool.name === 'Gemini CLI') {
      configPath.value = `${process.env.USERPROFILE || '~'}/.gemini-cli/config.json`
    } else {
      configPath.value = 'Tool-specific config path'
    }

    // Show configuration dialog
    configDialog.value = true
  } catch (error) {
    console.error('Config generation failed:', error)
    toolStates.value[tool.id].testResult = {
      success: false,
      message: `Failed to generate configuration: ${error.message}`,
    }
  } finally {
    toolStates.value[tool.id].configuring = false
  }
}

const applyConfiguration = async () => {
  applying.value = true
  try {
    // Write configuration
    await setupService.registerMcp(selectedTool.value.name, generatedConfig.value)

    // Mark as configured
    toolStates.value[selectedTool.value.id].configured = true
    toolStates.value[selectedTool.value.id].testResult = {
      success: true,
      message: 'Configuration applied successfully!',
    }

    // Update parent
    const configuredTools = props.modelValue.filter((t) => t.id !== selectedTool.value.id)
    configuredTools.push({
      id: selectedTool.value.id,
      name: selectedTool.value.name,
      configured: true,
    })
    emit('update:modelValue', configuredTools)

    // Auto-test connection
    await handleTest(selectedTool.value)

    configDialog.value = false
  } catch (error) {
    console.error('Configuration application failed:', error)
    toolStates.value[selectedTool.value.id].testResult = {
      success: false,
      message: `Failed to apply configuration: ${error.message}`,
    }
  } finally {
    applying.value = false
  }
}

const handleTest = async (tool) => {
  toolStates.value[tool.id].testing = true
  toolStates.value[tool.id].testResult = null

  try {
    const result = await setupService.testMcpConnection(tool.name)
    toolStates.value[tool.id].testResult = result
  } catch (error) {
    console.error('Connection test failed:', error)
    toolStates.value[tool.id].testResult = {
      success: false,
      message: `Connection test failed: ${error.message}`,
    }
  } finally {
    toolStates.value[tool.id].testing = false
  }
}

const handleReconfigure = async (tool) => {
  toolStates.value[tool.id].configured = false
  toolStates.value[tool.id].testResult = null
  await handleConfigure(tool)
}

const handleSkip = () => {
  userSkipped.value = true
}

// Lifecycle
onMounted(() => {
  detectTools()
})
</script>

<style scoped>
h2 {
  color: rgb(var(--v-theme-primary));
}

.tool-card {
  transition: all 0.2s ease;
}

.tool-card:hover {
  background-color: rgba(var(--v-theme-surface-variant), 0.3);
}

.config-preview {
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
  line-height: 1.5;
  max-height: 400px;
  overflow-y: auto;
  color: rgb(var(--v-theme-on-surface));
}
</style>
