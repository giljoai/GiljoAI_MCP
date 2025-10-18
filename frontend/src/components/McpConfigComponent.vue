<template>
  <v-card>
    <v-card-title class="d-flex align-center bg-primary">
      <v-icon start>mdi-robot-outline</v-icon>
      Manual AI Tool Configuration
      <v-spacer />
      <v-btn icon="mdi-close" variant="text" @click="$emit('close')" aria-label="Close dialog" />
    </v-card-title>

    <v-card-text class="pt-6">
      <!-- Universal Agent Configuration Section -->
      <v-card class="mb-6" variant="outlined" style="border: 2px solid var(--v-theme-primary);">
        <v-card-title class="d-flex align-center bg-primary text-white">
          <v-icon start size="large">mdi-robot-excited</v-icon>
          <div>
            <div class="text-h6">AI Tool MCP Configurator</div>
            <div class="text-subtitle-2 opacity-90">
              Works with Claude Code, Codex, Gemini, Cursor, and more
            </div>
          </div>
        </v-card-title>
        
        <v-card-text>
          <v-alert type="success" variant="tonal" class="mb-4">
            <v-alert-title>Automatic Configuration</v-alert-title>
            <div class="mt-2">
              Your AI tool can visit a special URL and configure itself automatically.
              This works with any AI coding tool that supports MCP.
            </div>
          </v-alert>

          <p class="text-body-1 mb-3">
            <strong>Copy this instruction</strong> and send it to your AI coding tool:
          </p>

          <v-card variant="outlined" class="pa-3 mb-3">
            <div class="d-flex justify-space-between align-center mb-2">
              <span class="text-caption text-medium-emphasis">Universal AI Instruction</span>
              <v-btn 
                @click="copyAgentInstruction" 
                :color="agentInstructionCopied ? 'success' : 'primary'"
                size="small"
                variant="elevated"
              >
                <v-icon start>{{ agentInstructionCopied ? 'mdi-check' : 'mdi-content-copy' }}</v-icon>
                {{ agentInstructionCopied ? 'Copied!' : 'Copy Instruction' }}
              </v-btn>
            </div>
            
            <div class="agent-instruction-text">
              {{ agentInstruction }}
            </div>
          </v-card>

          <v-expansion-panels class="mb-4">
            <v-expansion-panel>
              <v-expansion-panel-title>
                <v-icon start>mdi-help-circle</v-icon>
                How This Works
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <ol class="ml-4">
                  <li class="mb-2">
                    <strong>Send the instruction</strong> to your AI tool (Claude Code, Codex, Gemini, etc.)
                  </li>
                  <li class="mb-2">
                    <strong>AI visits the URL</strong> and receives tailored configuration instructions
                  </li>
                  <li class="mb-2">
                    <strong>AI asks for your API key</strong> (generate one in Settings if needed)
                  </li>
                  <li class="mb-2">
                    <strong>AI configures itself</strong> with the correct settings
                  </li>
                  <li class="mb-2">
                    <strong>Restart your AI tool</strong> to activate the connection
                  </li>
                </ol>
                
                <v-alert type="info" variant="tonal" class="mt-3">
                  <strong>Works with:</strong> Claude Code, GitHub Codex, Google Gemini Code Assist, 
                  Cursor, Continue.dev, and any future AI coding tool
                </v-alert>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>

          <div class="d-flex gap-3">
            <v-btn 
              @click="testAgentEndpoint" 
              variant="outlined" 
              :loading="testingEndpoint"
              prepend-icon="mdi-test-tube"
            >
              Test Endpoint
            </v-btn>
            
            <v-btn 
              @click="navigateToApiKeys" 
              variant="outlined"
              prepend-icon="mdi-key"
            >
              Manage API Keys
            </v-btn>
          </div>
        </v-card-text>
      </v-card>

      <!-- Manual Configuration Section (fallback) -->
      <v-card class="mb-6">
        <v-card-title>
          <v-icon start>mdi-cog</v-icon>
          Manual Configuration
        </v-card-title>
        <v-card-text>
          <p class="text-body-2 mb-3">
            If your AI tool doesn't support automatic configuration, use manual configuration below:
          </p>
          
          <!-- Tool Selection -->
          <v-alert type="info" variant="tonal" class="mb-6">
            <div class="d-flex align-center">
              <v-icon start>mdi-information</v-icon>
              <div>
                Generate configuration for your AI tool to connect to this GiljoAI MCP server.
                Copy and paste the configuration, or download a complete setup guide.
              </div>
            </div>
          </v-alert>

      <v-select
        v-model="selectedTool"
        :items="supportedTools"
        item-title="name"
        item-value="id"
        label="Select AI Tool"
        variant="outlined"
        prepend-icon="mdi-robot"
        hint="Choose the AI tool you want to connect"
        persistent-hint
        @update:model-value="generateConfig"
      >
        <template v-slot:item="{ props, item }">
          <v-list-item v-bind="props">
            <template v-slot:prepend>
              <v-icon :icon="getToolIcon(item.raw.id)" />
            </template>
          </v-list-item>
        </template>
      </v-select>

      <!-- Loading State -->
      <div v-if="loading" class="text-center my-8">
        <v-progress-circular indeterminate color="primary" size="64" />
        <p class="mt-4 text-body-1">Generating configuration...</p>
      </div>

      <!-- Error State -->
      <v-alert v-if="error" type="error" variant="tonal" class="mt-6">
        <div class="d-flex align-center">
          <v-icon start>mdi-alert-circle</v-icon>
          <div>
            <strong>Error:</strong> {{ error }}
          </div>
        </div>
      </v-alert>

      <!-- Configuration Display -->
      <div v-if="configData && !loading" class="mt-6">
        <!-- API Key Warning -->
        <v-alert
          v-if="showApiKeyWarning && generatedApiKey"
          type="warning"
          variant="tonal"
          prominent
          class="mb-4"
          data-test="api-key-warning"
        >
          <v-alert-title class="text-h6 mb-2">
            <v-icon start>mdi-shield-alert</v-icon>
            Save this API key now!
          </v-alert-title>
          This API key will only be shown ONCE. After closing this dialog, you will not
          be able to retrieve it again. Make sure to copy the configuration below.
        </v-alert>

        <!-- API Key Success Message -->
        <v-alert
          v-if="generatedApiKey"
          type="success"
          variant="tonal"
          class="mb-4"
          data-test="api-key-success"
        >
          <div class="d-flex align-center">
            <v-icon start>mdi-key-check</v-icon>
            <div>
              <strong>API Key Generated:</strong>
              <code class="ml-2 text-primary">{{ generatedApiKey.substring(0, 10) }}...</code>
              <div class="text-caption mt-1">
                Your key is embedded in the configuration below.
                <router-link
                  to="/api-keys"
                  class="text-primary"
                  data-test="manage-api-keys-link"
                >
                  Manage all API keys
                </router-link>
              </div>
            </div>
          </div>
        </v-alert>

        <!-- File Location -->
        <v-alert type="info" variant="tonal" class="mb-4">
          <div class="d-flex align-center">
            <v-icon start>mdi-file-document</v-icon>
            <div>
              <strong>Configuration File:</strong>
              <code class="ml-2 text-primary">{{ configData.file_location }}</code>
            </div>
          </div>
        </v-alert>

        <!-- Configuration Content -->
        <v-card variant="outlined" class="mb-4">
          <v-card-title class="bg-grey-darken-3 d-flex align-center">
            <v-icon start>mdi-code-json</v-icon>
            Configuration Content
            <v-spacer />
            <v-btn
              size="small"
              variant="text"
              :prepend-icon="copied ? 'mdi-check' : 'mdi-content-copy'"
              @click="copyToClipboard"
            >
              {{ copied ? 'Copied!' : 'Copy' }}
            </v-btn>
          </v-card-title>
          <v-card-text class="pa-0">
            <pre class="config-code"><code>{{ configData.config_content }}</code></pre>
          </v-card-text>
        </v-card>

        <!-- Instructions -->
        <v-card variant="outlined" class="mb-4">
          <v-card-title class="bg-grey-darken-3 d-flex align-center">
            <v-icon start>mdi-list-box-outline</v-icon>
            Setup Instructions
          </v-card-title>
          <v-card-text>
            <v-list density="compact">
              <v-list-item
                v-for="(instruction, index) in configData.instructions"
                :key="index"
                class="px-0"
              >
                <template v-slot:prepend>
                  <v-icon
                    :icon="index === configData.instructions.length - 1 ? 'mdi-check-circle' : 'mdi-numeric-' + (index + 1) + '-circle'"
                    :color="index === configData.instructions.length - 1 ? 'success' : 'primary'"
                  />
                </template>
                <v-list-item-title>{{ instruction }}</v-list-item-title>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>

        <!-- Download Button -->
        <v-btn
          block
          color="success"
          variant="flat"
          size="large"
          :prepend-icon="'mdi-download'"
          @click="downloadMarkdownGuide"
        >
          Download Complete Setup Guide (Markdown)
        </v-btn>
      </div>
        </v-card-text>
      </v-card>
    </v-card-text>

    <!-- Snackbar for user feedback -->
    <v-snackbar
      v-model="snackbar.show"
      :color="snackbar.color"
      :timeout="3000"
      location="bottom right"
    >
      {{ snackbar.message }}
      <template v-slot:actions>
        <v-btn variant="text" @click="snackbar.show = false" icon="mdi-close" />
      </template>
    </v-snackbar>
  </v-card>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/services/api'
import {
  generateClaudeCodeConfig,
  generateCodexConfig,
  generateGenericConfig,
} from '@/utils/configTemplates'

// State
const selectedTool = ref(null)
const supportedTools = ref([])
const configData = ref(null)
const loading = ref(false)
const error = ref(null)
const copied = ref(false)
const generatedApiKey = ref(null)
const showApiKeyWarning = ref(false)

// Agent-driven configuration state
const agentInstructionCopied = ref(false)
const testingEndpoint = ref(false)

// Snackbar state
const snackbar = ref({
  show: false,
  message: '',
  color: 'success'
})

function showSnackbar(message, color = 'success') {
  snackbar.value = {
    show: true,
    message,
    color
  }
}

// Agent instruction computed property
import { API_CONFIG } from '@/config/api'
const agentInstruction = computed(() =>
  `Visit ${API_CONFIG.REST_API.baseURL}/api/v1/user/ai-tools-configurator and configure yourself for MCP integration with this GiljoAI server. You will receive tailored configuration instructions for your platform.`
)

// Methods
async function loadSupportedTools() {
  try {
    const response = await api.aiTools.getSupportedTools()
    supportedTools.value = response.data.tools.filter(tool => tool.supported)
  } catch (err) {
    console.error('[McpConfig] Failed to load supported tools:', err)
    error.value = 'Failed to load supported tools. Please try again.'
  }
}

function generateApiKeyName(toolId) {
  const toolNames = {
    claude: 'Claude Code',
    codex: 'Codex CLI',
    gemini: 'Gemini',
  }
  const toolName = toolNames[toolId] || 'AI Tool'
  const date = new Date().toLocaleDateString()
  return `${toolName} - ${date}`
}

async function generateConfig() {
  if (!selectedTool.value) {
    return
  }

  loading.value = true
  error.value = null
  configData.value = null
  generatedApiKey.value = null
  showApiKeyWarning.value = false

  try {
    // Step 1: Generate API key for this tool
    const keyName = generateApiKeyName(selectedTool.value)
    const apiKeyResponse = await api.apiKeys.create(keyName)

    generatedApiKey.value = apiKeyResponse.data.key
    showApiKeyWarning.value = true

    // Step 2: Generate configuration using frontend templates with the API key
    const serverUrl = `${window.location.protocol}//${window.location.hostname}:7272`
    const pythonPath = 'python'

    let configContent = ''
    let fileLocation = ''
    let downloadFilename = ''
    const instructions = []

    if (selectedTool.value === 'claude') {
      configContent = generateClaudeCodeConfig(generatedApiKey.value, serverUrl, pythonPath)
      fileLocation = '~/.claude.json'
      downloadFilename = 'claude-code-setup.md'
      instructions.push(
        'Open or create the file ~/.claude.json',
        'Copy and paste the configuration above',
        'Restart Claude Code to apply the changes',
        'Your API key is now configured and ready to use'
      )
    } else if (selectedTool.value === 'codex') {
      configContent = generateCodexConfig(generatedApiKey.value, serverUrl)
      fileLocation = '~/config.toml'
      downloadFilename = 'codex-setup.md'
      instructions.push(
        'Open or create the file ~/config.toml',
        'Copy and paste the configuration above',
        'Restart Codex CLI to apply the changes'
      )
    } else {
      configContent = generateGenericConfig(generatedApiKey.value, serverUrl)
      fileLocation = 'Custom integration'
      downloadFilename = 'generic-api-setup.md'
      instructions.push(
        'Use the API key in your HTTP requests',
        'Include it in the X-API-Key header',
        'See the example code above for usage'
      )
    }

    configData.value = {
      file_location: fileLocation,
      config_content: configContent,
      instructions: instructions,
      download_filename: downloadFilename,
    }

    console.log('[McpConfig] Configuration generated successfully with API key for', selectedTool.value)
  } catch (err) {
    console.error('[McpConfig] Failed to generate config:', err)
    error.value = err.message || 'Failed to generate configuration. Please try again.'
  } finally {
    loading.value = false
  }
}

async function copyToClipboard() {
  if (!configData.value) return

  try {
    await navigator.clipboard.writeText(configData.value.config_content)
    copied.value = true
    console.log('[McpConfig] Configuration copied to clipboard')
    showSnackbar('Configuration copied to clipboard!', 'success')

    // Reset copied state after 2 seconds
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (err) {
    console.error('[McpConfig] Failed to copy to clipboard:', err)
    showSnackbar('Failed to copy to clipboard. Please copy manually.', 'error')
  }
}

async function downloadMarkdownGuide() {
  if (!configData.value || !selectedTool.value) return

  try {
    const response = await api.get(
      `/api/ai-tools/config-generator/${selectedTool.value}/markdown`,
      { responseType: 'text' }
    )

    const markdown = response.data

    // Create blob and download
    const blob = new Blob([markdown], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = configData.value.download_filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)

    console.log('[McpConfig] Setup guide downloaded successfully')
    showSnackbar('Setup guide downloaded successfully!', 'success')
  } catch (err) {
    console.error('[McpConfig] Failed to download guide:', err)
    showSnackbar('Failed to download setup guide. Please try again.', 'error')
  }
}

function getToolIcon(toolId) {
  const icons = {
    claude: 'mdi-chat-processing',
    codex: 'mdi-code-braces',
    gemini: 'mdi-diamond-stone'
  }
  return icons[toolId] || 'mdi-robot'
}

// Agent-driven configuration methods
async function copyAgentInstruction() {
  try {
    await navigator.clipboard.writeText(agentInstruction.value)
    agentInstructionCopied.value = true
    setTimeout(() => { agentInstructionCopied.value = false }, 3000)
    
    console.log('[McpConfig] Agent instruction copied to clipboard')
    showSnackbar('Agent instruction copied to clipboard!', 'success')
  } catch (error) {
    console.error('[McpConfig] Failed to copy agent instruction:', error)
    showSnackbar('Failed to copy instruction. Please copy manually.', 'error')
  }
}

async function testAgentEndpoint() {
  testingEndpoint.value = true
  try {
    const response = await fetch(`${API_CONFIG.REST_API.baseURL}/api/v1/user/ai-tools-configurator`)
    if (response.ok) {
      const instructions = await response.text()
      console.log('[McpConfig] Agent endpoint working:', instructions.slice(0, 100) + '...')

      // Show success feedback
      showSnackbar('Agent endpoint is working correctly!', 'success')
    } else {
      throw new Error(`HTTP ${response.status}`)
    }
  } catch (error) {
    console.error('[McpConfig] Agent endpoint test failed:', error)
    showSnackbar('Agent endpoint test failed. Check server status.', 'error')
  } finally {
    testingEndpoint.value = false
  }
}

function navigateToApiKeys() {
  // Navigate to API keys management page
  window.location.href = '/settings/api-keys'
}

// Lifecycle
onMounted(() => {
  loadSupportedTools()
})
</script>

<style scoped>
.config-code {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 16px;
  margin: 0;
  overflow-x: auto;
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.875rem;
  line-height: 1.5;
  border-radius: 0;
  max-height: 400px;
}

.config-code code {
  background: transparent;
  color: inherit;
  padding: 0;
}

/* Syntax highlighting for JSON */
.config-code :deep(.token.property) {
  color: #9cdcfe;
}

.config-code :deep(.token.string) {
  color: #ce9178;
}

.config-code :deep(.token.number) {
  color: #b5cea8;
}

.config-code :deep(.token.boolean) {
  color: #569cd6;
}

.config-code :deep(.token.null) {
  color: #569cd6;
}

.agent-instruction-text {
  font-family: 'Roboto Mono', monospace;
  background-color: rgba(var(--v-theme-surface-variant), 0.3);
  padding: 12px;
  border-radius: 6px;
  font-size: 0.875rem;
  line-height: 1.4;
  word-break: break-all;
}
</style>
