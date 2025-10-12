<template>
  <v-card-text class="pa-8">
    <h2 class="text-h5 mb-2">Attach Coding Tools</h2>
    <p class="text-body-1 mb-6">
      Connect AI coding assistants to GiljoAI MCP using the Model Context Protocol
    </p>

    <!-- Unified Mode: Auto-configuration for all IPs -->
    <div>
      <v-row>
        <!-- Claude Code - Active -->
        <v-col cols="12" md="4">
          <v-card
            variant="outlined"
            class="tool-card h-100"
            :class="{ 'tool-configured': claudeCodeConfigured }"
          >
            <v-card-text class="d-flex flex-column h-100">
              <!-- Tool Header -->
              <div class="text-center mb-4">
                <v-img
                  src="/Claude_AI_symbol.svg"
                  alt="Claude Code"
                  max-width="48"
                  class="mx-auto"
                />
                <h3 class="text-h6 mt-2">Claude Code</h3>
                <v-chip v-if="claudeCodeConfigured" size="small" color="success" class="mt-2">
                  Configured
                </v-chip>
              </div>

              <!-- Tool Description -->
              <p class="text-body-2 text-medium-emphasis flex-grow-1">
                Anthropic's official CLI for Claude with built-in MCP support
              </p>

              <!-- Action Button -->
              <v-btn
                v-if="!claudeCodeConfigured"
                color="primary"
                variant="flat"
                block
                :loading="attaching"
                @click="attachClaudeCode"
                aria-label="Attach Claude Code"
              >
                Attach
              </v-btn>

              <!-- Verification Instructions -->
              <v-alert
                v-if="claudeCodeConfigured"
                type="success"
                variant="tonal"
                density="compact"
                class="mt-2"
              >
                <div class="text-caption">
                  <strong>Next:</strong> Relaunch Claude Code CLI and type <code>/mcp</code> to
                  verify
                </div>
              </v-alert>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- ChatGPT - Future -->
        <v-col cols="12" md="4">
          <v-card variant="outlined" class="tool-card h-100 disabled-tool">
            <v-card-text class="d-flex flex-column h-100">
              <!-- Tool Header -->
              <div class="text-center mb-4">
                <v-img
                  src="/openai-logo.svg"
                  alt="ChatGPT"
                  max-width="48"
                  class="mx-auto"
                  style="opacity: 0.5"
                />
                <h3 class="text-h6 mt-2 text-disabled">ChatGPT</h3>
                <v-chip size="small" color="info" class="mt-2">Future</v-chip>
              </div>

              <!-- Tool Description -->
              <p class="text-body-2 text-disabled flex-grow-1">
                OpenAI's ChatGPT with MCP integration (coming soon)
              </p>

              <!-- Disabled Button -->
              <v-btn
                color="grey"
                variant="outlined"
                block
                disabled
                aria-label="ChatGPT not yet available"
              >
                Coming Soon
              </v-btn>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Gemini - Future -->
        <v-col cols="12" md="4">
          <v-card variant="outlined" class="tool-card h-100 disabled-tool">
            <v-card-text class="d-flex flex-column h-100">
              <!-- Tool Header -->
              <div class="text-center mb-4">
                <v-img
                  src="/gemini-icon.svg"
                  alt="Gemini"
                  max-width="48"
                  class="mx-auto"
                  style="opacity: 0.5"
                />
                <h3 class="text-h6 mt-2 text-disabled">Gemini</h3>
                <v-chip size="small" color="info" class="mt-2">Future</v-chip>
              </div>

              <!-- Tool Description -->
              <p class="text-body-2 text-disabled flex-grow-1">
                Google's Gemini with MCP integration (coming soon)
              </p>

              <!-- Disabled Button -->
              <v-btn
                color="grey"
                variant="outlined"
                block
                disabled
                aria-label="Gemini not yet available"
              >
                Coming Soon
              </v-btn>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Success Message -->
      <v-alert v-if="claudeCodeConfigured" type="success" variant="tonal" class="mt-4">
        <v-icon start>mdi-check-circle</v-icon>
        <strong>Claude Code configured successfully</strong>
        <div class="text-caption mt-2">
          Server URL: <code>{{ serverUrl || `${window.location.protocol}//${window.location.hostname}:7272` }}</code>
        </div>
      </v-alert>

      <!-- Manual Configuration Section (when needed) -->
      <div v-if="false" style="display: none">
      <v-alert type="info" variant="tonal" class="mb-4">
        <v-icon start>mdi-information</v-icon>
        <strong>LAN Mode: Manual Configuration Required</strong>
        <div class="text-body-2 mt-2">
          In LAN mode, you need to manually add the MCP configuration to Claude Code CLI. Copy the
          configuration below and follow the step-by-step instructions.
        </div>
      </v-alert>

      <!-- Admin API Key Display -->
      <v-card variant="outlined" class="mb-4">
        <v-card-title class="bg-surface-variant">
          <v-icon start>mdi-key</v-icon>
          Admin API Key
        </v-card-title>
        <v-card-text>
          <div class="d-flex align-center">
            <v-text-field
              :model-value="apiKey || 'Not available'"
              label="API Key"
              variant="outlined"
              readonly
              density="compact"
              class="flex-grow-1 mr-2"
              aria-label="Admin API key for MCP configuration"
            />
            <v-btn
              icon="mdi-content-copy"
              variant="tonal"
              color="primary"
              @click="copyToClipboard(apiKey, 'API Key')"
              aria-label="Copy API key to clipboard"
              :disabled="!apiKey"
            />
          </div>
          <div class="text-caption text-medium-emphasis mt-2">
            Save this API key securely. You will need it to configure Claude Code CLI.
          </div>
        </v-card-text>
      </v-card>

      <!-- MCP Configuration Snippet -->
      <v-card variant="outlined" class="mb-4">
        <v-card-title class="bg-surface-variant d-flex justify-space-between align-center">
          <div>
            <v-icon start>mdi-code-json</v-icon>
            MCP Configuration for Claude Code
          </div>
          <v-btn
            size="small"
            variant="tonal"
            color="primary"
            @click="copyToClipboard(mcpConfigJson, 'MCP Configuration')"
            aria-label="Copy MCP configuration to clipboard"
          >
            <v-icon start>mdi-content-copy</v-icon>
            Copy All
          </v-btn>
        </v-card-title>
        <v-card-text>
          <pre class="mcp-config-code" v-html="highlightedMcpConfig"></pre>
        </v-card-text>
      </v-card>

      <!-- Step-by-step Instructions -->
      <v-card variant="outlined" class="mb-4">
        <v-card-title class="bg-surface-variant">
          <v-icon start>mdi-clipboard-list-outline</v-icon>
          Configuration Steps
        </v-card-title>
        <v-card-text>
          <v-stepper :model-value="instructionStep" alt-labels class="elevation-0" hide-actions>
            <v-stepper-header>
              <v-stepper-item :complete="instructionStep > 1" :value="1" title="Open config file" />
              <v-divider />
              <v-stepper-item
                :complete="instructionStep > 2"
                :value="2"
                title="Add configuration"
              />
              <v-divider />
              <v-stepper-item
                :complete="instructionStep > 3"
                :value="3"
                title="Restart Claude Code"
              />
              <v-divider />
              <v-stepper-item :value="4" title="Verify" />
            </v-stepper-header>

            <v-stepper-window>
              <v-stepper-window-item :value="1">
                <div class="pa-4">
                  <h4 class="text-h6 mb-3">Step 1: Open Config File</h4>
                  <p class="text-body-2 mb-3">
                    Open (or create) the Claude Code configuration file at:
                  </p>
                  <v-code class="mb-3">~/.claude.json</v-code>
                  <p class="text-caption text-medium-emphasis">
                    On Windows: <code>C:\Users\&lt;username&gt;\.claude.json</code>
                  </p>
                </div>
              </v-stepper-window-item>

              <v-stepper-window-item :value="2">
                <div class="pa-4">
                  <h4 class="text-h6 mb-3">Step 2: Add Configuration</h4>
                  <p class="text-body-2 mb-3">
                    Add the configuration above to the <code>mcpServers</code> section. If the file
                    is empty, paste the entire JSON block.
                  </p>
                  <v-alert type="warning" variant="tonal" density="compact">
                    Make sure the JSON is valid (use a JSON validator if needed)
                  </v-alert>
                </div>
              </v-stepper-window-item>

              <v-stepper-window-item :value="3">
                <div class="pa-4">
                  <h4 class="text-h6 mb-3">Step 3: Restart Claude Code CLI</h4>
                  <p class="text-body-2 mb-3">
                    Close and restart Claude Code CLI to load the new configuration.
                  </p>
                  <v-code>claude code</v-code>
                </div>
              </v-stepper-window-item>

              <v-stepper-window-item :value="4">
                <div class="pa-4">
                  <h4 class="text-h6 mb-3">Step 4: Verify Configuration</h4>
                  <p class="text-body-2 mb-3">
                    In Claude Code CLI, type the following command to verify MCP tools are loaded:
                  </p>
                  <v-code class="mb-3">/mcp</v-code>
                  <v-alert type="success" variant="tonal" density="compact">
                    You should see "giljo-mcp" listed with available tools
                  </v-alert>
                </div>
              </v-stepper-window-item>
            </v-stepper-window>
          </v-stepper>

          <div class="d-flex justify-center mt-4">
            <v-btn
              v-if="instructionStep > 1"
              variant="text"
              @click="instructionStep--"
              aria-label="Previous step"
            >
              <v-icon start>mdi-arrow-left</v-icon>
              Previous
            </v-btn>
            <v-btn
              v-if="instructionStep < 4"
              variant="text"
              color="primary"
              @click="instructionStep++"
              aria-label="Next step"
            >
              Next
              <v-icon end>mdi-arrow-right</v-icon>
            </v-btn>
          </div>
        </v-card-text>
      </v-card>

      <!-- Future MCP Clients Note -->
      <v-alert type="info" variant="tonal" class="mt-4">
        <v-icon start>mdi-information</v-icon>
        <strong>Future MCP Clients:</strong>
        <div class="text-body-2 mt-2">
          Support for additional MCP clients is coming soon:
          <ul class="ml-4 mt-2">
            <li>Codex CLI (Coming Soon)</li>
            <li>Gemini CLI (Coming Soon)</li>
          </ul>
        </div>
      </v-alert>
    </div>

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

    <!-- Copy Success Snackbar -->
    <v-snackbar v-model="showCopyConfirmation" timeout="2000" location="top right" color="success">
      {{ copyConfirmationMessage }}
    </v-snackbar>

    <!-- Info Alert -->
    <v-alert type="info" variant="tonal" class="mt-6">
      You can configure additional tools later in Settings. At least one tool is recommended but not
      required.
    </v-alert>

    <!-- Progress -->
    <v-card variant="outlined" class="mt-6 mb-6">
      <v-card-text>
        <div class="d-flex justify-space-between mb-2">
          <span class="text-caption">Progress: Step 2 of 5</span>
          <span class="text-caption">40%</span>
        </div>
        <v-progress-linear :model-value="40" color="warning" />
      </v-card-text>
    </v-card>

    <!-- Navigation -->
    <v-card variant="outlined" class="mt-6 mb-0">
      <v-card-text class="d-flex justify-space-between">
        <v-btn variant="outlined" @click="$emit('back')" aria-label="Go back to database check">
          <v-icon start>mdi-arrow-left</v-icon>
          Back
        </v-btn>
        <v-btn color="primary" @click="handleNext" aria-label="Continue to Serena MCP">
          Continue
          <v-icon end>mdi-arrow-right</v-icon>
        </v-btn>
      </v-card-text>
    </v-card>
  </v-card-text>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import setupService from '@/services/setupService'

/**
 * AttachToolsStep - Tool attachment step (Step 1 of 3)
 *
 * Mode-aware tool attachment: auto-configuration for localhost, manual for LAN
 */

const props = defineProps({
  modelValue: {
    type: Array,
    default: () => [],
  },
  // deploymentMode removed - v3.0 unified approach for all IPs
  apiKey: {
    type: String,
    default: null,
  },
  serverUrl: {
    type: String,
    default: null,
  },
})

const emit = defineEmits(['update:modelValue', 'next', 'back'])

// State
const attaching = ref(false)
const claudeCodeConfigured = ref(false)
const errorMessage = ref('')
const showCopyConfirmation = ref(false)
const copyConfirmationMessage = ref('')
const instructionStep = ref(1)

// Computed
const mcpConfigJson = computed(() => {
  // v3.0 Unified: Default to current host if no URL provided
  const serverUrlValue = props.serverUrl || `${window.location.protocol}//${window.location.hostname}:7272`
  const apiKeyValue = props.apiKey || 'YOUR_API_KEY_HERE'

  // Generate the MCP configuration JSON for LAN mode
  const config = {
    mcpServers: {
      'giljo-mcp': {
        command: 'uvx',
        args: ['giljo-mcp'],
        env: {
          GILJO_SERVER_URL: serverUrlValue,
          GILJO_API_KEY: apiKeyValue,
        },
      },
    },
  }

  return JSON.stringify(config, null, 2)
})

const highlightedMcpConfig = computed(() => {
  const apiKeyValue = props.apiKey || 'YOUR_API_KEY_HERE'
  const jsonString = mcpConfigJson.value

  // Find the line with GILJO_API_KEY BEFORE escaping
  const lines = jsonString.split('\n')
  const highlightedLines = lines.map((line) => {
    // Check if this line contains the GILJO_API_KEY
    if (line.includes('GILJO_API_KEY') && line.includes(apiKeyValue)) {
      // Escape the line
      const escapedLine = line
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;')

      // Apply CSS class for yellow highlighting
      return `<span class="api-key-highlight">${escapedLine}</span>`
    } else {
      // Escape normally
      return line
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;')
    }
  })

  return highlightedLines.join('\n')
})

// Methods
const copyToClipboard = async (text, label) => {
  if (!text) {
    errorMessage.value = 'Nothing to copy'
    return
  }

  try {
    await navigator.clipboard.writeText(text)
    copyConfirmationMessage.value = `${label} copied to clipboard!`
    showCopyConfirmation.value = true
    console.log(`[ATTACH_TOOLS] Copied ${label} to clipboard`)
  } catch (err) {
    console.error(`[ATTACH_TOOLS] Failed to copy ${label}:`, err)
    errorMessage.value = `Failed to copy ${label} to clipboard`
  }
}

const attachClaudeCode = async () => {
  attaching.value = true
  errorMessage.value = ''

  try {
    // Generate MCP configuration for Claude Code (v3.0 unified approach)
    const mcpConfig = await setupService.generateMcpConfig('Claude Code')
    console.log('[ATTACH_TOOLS] Generated MCP config:', mcpConfig)

    // Register MCP configuration (writes to .claude.json)
    await setupService.registerMcp('Claude Code', mcpConfig)
    console.log('[ATTACH_TOOLS] Claude Code MCP registered')

    // Mark as configured
    claudeCodeConfigured.value = true

    // Update parent
    const tools = [
      {
        id: 'claude-code',
        name: 'Claude Code',
        configured: true,
      },
    ]
    emit('update:modelValue', tools)

    console.log('[ATTACH_TOOLS] Claude Code attached successfully')
  } catch (error) {
    console.error('[ATTACH_TOOLS] Failed to attach Claude Code:', error)
    errorMessage.value = `Failed to attach Claude Code: ${error.message}`
  } finally {
    attaching.value = false
  }
}

const handleNext = () => {
  console.log('[ATTACH_TOOLS] Moving to next step')
  emit('next')
}

// Lifecycle
onMounted(async () => {
  console.log('[ATTACH_TOOLS] Checking if Claude Code MCP is already configured')

  try {
    const status = await setupService.checkMcpConfigured()

    if (status.configured) {
      console.log('[ATTACH_TOOLS] Claude Code MCP already configured')
      claudeCodeConfigured.value = true

      // Update parent with existing configuration
      const tools = [
        {
          id: 'claude-code',
          name: 'Claude Code',
          configured: true,
        },
      ]
      emit('update:modelValue', tools)
    } else {
      console.log('[ATTACH_TOOLS] Claude Code MCP not configured')
    }
  } catch (error) {
    console.error('[ATTACH_TOOLS] Failed to check MCP status:', error)
    // Non-fatal error, continue with wizard
  }
})
</script>

<style scoped>
h2 {
  color: rgb(var(--v-theme-primary));
}

.tool-card {
  transition: all 0.2s ease;
  border-width: 2px;
}

.tool-card:not(.disabled-tool):hover {
  border-color: rgb(var(--v-theme-primary));
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.tool-configured {
  border-color: rgb(var(--v-theme-success));
  background-color: rgba(var(--v-theme-success), 0.05);
}

.disabled-tool {
  opacity: 0.6;
}

code {
  background-color: rgba(var(--v-theme-surface-variant), 0.5);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
}

.mcp-config-code {
  background-color: rgba(var(--v-theme-surface-variant), 0.5);
  padding: 16px;
  border-radius: 8px;
  font-family: 'Courier New', Consolas, Monaco, monospace;
  font-size: 0.875rem;
  overflow-x: auto;
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 400px;
  overflow-y: auto;
  color: rgb(var(--v-theme-on-surface));
}

/* Target dynamically injected content via v-html using :deep() */
.mcp-config-code :deep(.api-key-highlight) {
  color: #ffc107;
  display: block;
}

v-code {
  display: block;
  background-color: rgba(var(--v-theme-surface-variant), 0.5);
  padding: 12px;
  border-radius: 8px;
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
  white-space: pre-wrap;
  overflow-x: auto;
}
</style>
