<template>
  <v-card>
    <v-card-title class="d-flex align-center bg-primary">
      <v-icon start>mdi-robot-outline</v-icon>
      Manual AI Tool Configuration
      <v-spacer />
      <v-btn icon="mdi-close" variant="text" @click="$emit('close')" aria-label="Close dialog" />
    </v-card-title>

    <v-card-text class="pt-6">
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
          <v-alert type="info" variant="tonal" class="mb-6" :icon="false">
            <div class="d-flex align-center">
              <v-icon start>mdi-information</v-icon>
              <div>
                <strong>Zero-Dependency HTTP Transport Setup</strong>
                <p class="text-body-2 mt-2 mb-0">
                  Connect your AI tool to GiljoAI using HTTP transport - no Python installation or local packages required.
                  Just copy and run a single command to enable all GiljoAI orchestration tools.
                </p>
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
      <v-alert v-if="error" type="error" variant="tonal" class="mt-6" :icon="false">
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
          :icon="false"
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
          :icon="false"
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

        <!-- Setup Method -->
        <v-alert type="info" variant="tonal" class="mb-4" :icon="false">
          <div class="d-flex align-center">
            <v-icon start>mdi-hammer-wrench</v-icon>
            <div>
              <strong>Setup Method:</strong>
              <code class="ml-2 text-primary">{{ configData.file_location }}</code>
            </div>
          </div>
        </v-alert>

        <!-- Configuration Content -->
        <v-card variant="outlined" class="mb-4">
          <v-card-title class="bg-grey-darken-3 d-flex align-center">
            <v-icon start>mdi-console-line</v-icon>
            Setup Command
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
  generateGeminiConfig,
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

// Agent-driven configuration removed in Project 0031 (wizard handles prompts)

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
  // Do not reset any existing session key; reuse across tool selections

  try {
    // Step 1: Ensure we have an API key for this session
    if (!generatedApiKey.value) {
      const keyName = generateApiKeyName(selectedTool.value)
      const apiKeyResponse = await api.apiKeys.create(keyName)
      generatedApiKey.value = apiKeyResponse.data.api_key
      showApiKeyWarning.value = true
    }

    // Step 2: Generate configuration using frontend templates with the API key
    const serverUrl = `${window.location.protocol}//${window.location.hostname}:7272`

    let configContent = ''
    let fileLocation = ''
    let downloadFilename = ''
    const instructions = []

    if (selectedTool.value === 'claude') {
      configContent = generateClaudeCodeConfig(generatedApiKey.value, serverUrl)
      fileLocation = 'Command Line (Terminal/PowerShell)'
      downloadFilename = 'claude-code-setup.md'
      instructions.push(
        'Open your terminal or command prompt',
        'Copy the command shown above',
        'Paste and run the command to configure Claude Code',
        'Verify connection with: claude mcp list',
        'Start using GiljoAI tools in Claude Code conversations'
      )
    } else if (selectedTool.value === 'codex') {
      configContent = generateCodexConfig(generatedApiKey.value, serverUrl)
      fileLocation = 'Command Line (Terminal/PowerShell)'
      downloadFilename = 'codex-setup.md'
      instructions.push(
        'Open your terminal or command prompt',
        'Copy the command shown above',
        'Paste and run the command to configure Codex CLI',
        'Verify connection with: codex mcp list',
        'Start using GiljoAI tools in Codex sessions'
      )
    } else if (selectedTool.value === 'gemini') {
      configContent = generateGeminiConfig(generatedApiKey.value, serverUrl)
      fileLocation = 'Command Line (Terminal/PowerShell)'
      downloadFilename = 'gemini-setup.md'
      instructions.push(
        'Open your terminal or command prompt',
        'Copy the command shown above',
        'Paste and run the command to configure Gemini CLI',
        'Verify connection with: gemini mcp list',
        'Start using GiljoAI tools in Gemini sessions'
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

  const text = String(configData.value.config_content || '')
  if (!text) return

  // Production-grade cross-platform clipboard handler
  // Tries modern Clipboard API first, falls back gracefully to execCommand
  const fallbackCopy = () => {
    try {
      const ta = document.createElement('textarea')
      ta.value = text
      ta.setAttribute('readonly', '')
      ta.style.position = 'absolute'
      ta.style.left = '-9999px'
      ta.style.top = '0'
      document.body.appendChild(ta)

      // Select and copy
      ta.focus()
      ta.select()

      // For iOS compatibility
      if (navigator.userAgent.match(/ipad|iphone/i)) {
        const range = document.createRange()
        range.selectNodeContents(ta)
        const selection = window.getSelection()
        selection.removeAllRanges()
        selection.addRange(range)
        ta.setSelectionRange(0, text.length)
      }

      const success = document.execCommand('copy')
      document.body.removeChild(ta)
      return success
    } catch (err) {
      console.error('[McpConfig] Fallback copy failed:', err)
      return false
    }
  }

  // Try Clipboard API first (works in secure contexts and localhost)
  if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
    try {
      await navigator.clipboard.writeText(text)
      copied.value = true
      console.log('[McpConfig] Configuration copied via Clipboard API')
      showSnackbar('Configuration copied to clipboard!', 'success')
    } catch (err) {
      // Clipboard API failed (permissions/browser restrictions), try fallback
      console.warn('[McpConfig] Clipboard API failed, using fallback:', err)
      const success = fallbackCopy()
      copied.value = success

      if (success) {
        console.log('[McpConfig] Configuration copied via fallback method')
        showSnackbar('Configuration copied to clipboard!', 'success')
      } else {
        console.error('[McpConfig] All copy methods failed')
        showSnackbar('Failed to copy. Please select and copy the text manually.', 'error')
      }
    }
  } else {
    // Clipboard API not available, use fallback directly
    const success = fallbackCopy()
    copied.value = success

    if (success) {
      console.log('[McpConfig] Configuration copied via fallback method')
      showSnackbar('Configuration copied to clipboard!', 'success')
    } else {
      console.error('[McpConfig] Fallback copy method failed')
      showSnackbar('Failed to copy. Please select and copy the text manually.', 'error')
    }
  }

  // Reset copied state after 2 seconds
  setTimeout(() => {
    copied.value = false
  }, 2000)
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

// Agent-driven configuration methods removed

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
