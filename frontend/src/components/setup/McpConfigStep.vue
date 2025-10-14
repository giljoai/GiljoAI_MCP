<template>
  <v-card-text class="pa-8">
    <h2 class="text-h5 mb-2">MCP Configuration (Optional)</h2>
    <p class="text-body-1 mb-6">Connect GiljoAI MCP with your AI coding assistants</p>

    <!-- Info Alert -->
    <AppAlert type="info" variant="tonal" class="mb-4">
      Configure Model Context Protocol (MCP) integration to enhance your AI assistants with GiljoAI capabilities.
      You can skip this step and configure it later in Settings.
    </AppAlert>

    <!-- Check Status -->
    <v-card variant="outlined" class="mb-4">
      <v-card-text>
        <div class="d-flex align-center justify-space-between">
          <div class="flex-grow-1">
            <div class="text-h6">Claude Code MCP Server</div>
            <div class="text-caption text-medium-emphasis">
              {{ mcpStatus.configured ? 'Already configured' : 'Not configured yet' }}
            </div>
          </div>
          <v-chip :color="mcpStatus.configured ? 'success' : 'default'" size="small">
            {{ mcpStatus.configured ? 'Configured' : 'Not Configured' }}
          </v-chip>
        </div>

        <AppAlert
          v-if="mcpStatus.configured"
          type="success"
          variant="tonal"
          density="compact"
          class="mt-3"
        >
          <v-icon start size="small">mdi-check-circle</v-icon>
          GiljoAI MCP is already configured in Claude Code CLI
        </AppAlert>
      </v-card-text>
    </v-card>

    <!-- Configuration Instructions -->
    <v-expansion-panels v-model="expandedPanels" class="mb-4">
      <v-expansion-panel value="instructions">
        <v-expansion-panel-title>
          <v-icon start>mdi-book-open-variant</v-icon>
          <strong>Setup Instructions</strong>
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <h4 class="text-h6 mb-3">How to Configure MCP</h4>

          <v-stepper :model-value="1" alt-labels class="mb-4">
            <v-stepper-header>
              <v-stepper-item :complete="mcpConfig !== null" value="1" title="Generate Config" />
              <v-stepper-item :complete="false" value="2" title="Download Config" />
              <v-stepper-item :complete="mcpStatus.configured" value="3" title="Verify" />
            </v-stepper-header>
          </v-stepper>

          <ol class="mb-3">
            <li class="mb-2">Click "Generate Configuration" to create your MCP config</li>
            <li class="mb-2">Download the configuration file</li>
            <li class="mb-2">
              Add it to your Claude Code CLI configuration at
              <code>~/.claude.json</code>
            </li>
            <li class="mb-2">Restart Claude Code CLI</li>
            <li>Verify with <code>/mcp</code> command</li>
          </ol>

          <AppAlert type="warning" variant="tonal" density="compact">
            This will modify your .claude.json file. A backup will be created automatically.
          </AppAlert>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>

    <!-- Configuration Actions -->
    <v-card variant="outlined" class="mb-4">
      <v-card-text>
        <div class="d-flex flex-column gap-3">
          <!-- Generate Config Button -->
          <v-btn
            color="primary"
            :loading="generating"
            :disabled="mcpConfig !== null"
            @click="generateConfig"
          >
            <v-icon start>mdi-cog</v-icon>
            {{ mcpConfig ? 'Configuration Generated' : 'Generate Configuration' }}
          </v-btn>

          <!-- Config Preview -->
          <v-expand-transition>
            <div v-if="mcpConfig">
              <v-card variant="outlined" class="mb-3">
                <v-card-text>
                  <div class="d-flex justify-space-between align-center mb-2">
                    <span class="text-subtitle-2">Configuration Preview</span>
                    <v-btn
                      size="small"
                      variant="text"
                      @click="copyConfig"
                      :color="copied ? 'success' : 'default'"
                    >
                      <v-icon start size="small">
                        {{ copied ? 'mdi-check' : 'mdi-content-copy' }}
                      </v-icon>
                      {{ copied ? 'Copied!' : 'Copy' }}
                    </v-btn>
                  </div>
                  <pre class="config-preview">{{ JSON.stringify(mcpConfig, null, 2) }}</pre>
                </v-card-text>
              </v-card>

              <!-- Apply Config Button -->
              <v-btn
                color="success"
                :loading="applying"
                @click="applyConfig"
                block
              >
                <v-icon start>mdi-check-circle</v-icon>
                Apply Configuration to Claude Code
              </v-btn>

              <AppAlert v-if="applyResult" :type="applyResult.success ? 'success' : 'error'" class="mt-3">
                {{ applyResult.message }}
              </AppAlert>
            </div>
          </v-expand-transition>
        </div>
      </v-card-text>
    </v-card>

    <!-- Progress -->
    <v-card variant="outlined" class="mb-6">
      <v-card-text>
        <div class="d-flex justify-space-between mb-2">
          <span class="text-caption">Progress: Step 1 of 3</span>
          <span class="text-caption">33%</span>
        </div>
        <v-progress-linear :model-value="33" color="primary" />
      </v-card-text>
    </v-card>

    <!-- Navigation -->
    <div class="d-flex justify-space-between">
      <v-btn variant="text" disabled aria-label="No previous step">
        <v-icon start>mdi-arrow-left</v-icon>
        Back
      </v-btn>
      <div>
        <v-btn variant="text" @click="handleSkip" class="mr-2" aria-label="Skip this step">
          Skip This Step
        </v-btn>
        <v-btn color="primary" @click="handleNext" aria-label="Continue to next step">
          Continue
          <v-icon end>mdi-arrow-right</v-icon>
        </v-btn>
      </div>
    </div>
  </v-card-text>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import setupService from '@/services/setupService'
import AppAlert from '@/components/ui/AppAlert.vue'

const emit = defineEmits(['next'])

// State
const generating = ref(false)
const applying = ref(false)
const mcpConfig = ref(null)
const mcpStatus = ref({ configured: false })
const expandedPanels = ref([])
const copied = ref(false)
const applyResult = ref(null)

// Methods
const checkMcpStatus = async () => {
  try {
    const status = await setupService.checkMcpConfigured()
    mcpStatus.value = status
  } catch (error) {
    console.error('Failed to check MCP status:', error)
  }
}

const generateConfig = async () => {
  generating.value = true
  try {
    const config = await setupService.generateMcpConfig('Claude Code', 'localhost')
    mcpConfig.value = config
    expandedPanels.value = [] // Collapse instructions
  } catch (error) {
    console.error('Failed to generate config:', error)
    alert('Failed to generate configuration. Please try again.')
  } finally {
    generating.value = false
  }
}

const copyConfig = async () => {
  try {
    await navigator.clipboard.writeText(JSON.stringify(mcpConfig.value, null, 2))
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (error) {
    console.error('Failed to copy config:', error)
  }
}

const applyConfig = async () => {
  applying.value = true
  applyResult.value = null
  try {
    const result = await setupService.registerMcp('Claude Code', mcpConfig.value)
    applyResult.value = {
      success: true,
      message: `Configuration applied successfully! Backup saved to ${result.backup_path || 'backup file'}`
    }
    // Refresh status
    await checkMcpStatus()
  } catch (error) {
    console.error('Failed to apply config:', error)
    applyResult.value = {
      success: false,
      message: `Failed to apply configuration: ${error.message}`
    }
  } finally {
    applying.value = false
  }
}

const handleSkip = () => {
  // Emit next with skipped state
  emit('next', { mcpConfigured: false, skipped: true })
}

const handleNext = () => {
  // Emit next with configuration state
  emit('next', { mcpConfigured: mcpStatus.value.configured })
}

// Lifecycle
onMounted(async () => {
  await checkMcpStatus()
  // Auto-expand instructions if not configured
  if (!mcpStatus.value.configured) {
    expandedPanels.value = ['instructions']
  }
})
</script>

<style scoped>
h2 {
  color: rgb(var(--v-theme-primary));
}

.config-preview {
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
  line-height: 1.5;
  max-height: 300px;
  overflow-y: auto;
  color: rgb(var(--v-theme-on-surface));
  background-color: rgba(var(--v-theme-surface-variant), 0.3);
  padding: 12px;
  border-radius: 8px;
}

code {
  background-color: rgba(var(--v-theme-surface-variant), 0.5);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
}

ol {
  padding-left: 20px;
}

ol li {
  margin-bottom: 8px;
}
</style>
