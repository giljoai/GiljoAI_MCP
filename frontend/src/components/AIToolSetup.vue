<template>
  <v-dialog v-model="dialog" max-width="900" persistent scrollable>
    <template v-slot:activator="{ props }">
      <v-btn color="primary" variant="flat" v-bind="props" :prepend-icon="'mdi-connection'">
        Connect AI Tools
      </v-btn>
    </template>

    <v-card>
      <v-card-title class="d-flex align-center bg-primary">
        <v-icon start>mdi-robot-outline</v-icon>
        Connect AI Tools to GiljoAI MCP
        <v-spacer />
        <v-btn icon="mdi-close" variant="text" @click="closeDialog" />
      </v-card-title>

      <v-card-text class="pt-6">
        <!-- Tool Selection -->
        <v-alert type="info" variant="tonal" class="mb-6">
          Generate configuration for your AI tool to connect to this GiljoAI MCP server. Copy and
          paste the configuration, or download a complete setup guide.
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
                <v-avatar size="32" class="mr-2">
                  <v-img :src="getToolLogo(item.raw.id)" :alt="item.raw.name" />
                </v-avatar>
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
            <div><strong>Error:</strong> {{ error }}</div>
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
            This API key will only be shown ONCE. After closing this dialog, you will not be able to
            retrieve it again. Make sure to copy the configuration below.
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
                  <a
                    href="#/settings"
                    class="text-primary"
                    data-test="manage-api-keys-link"
                    @click="dialog = false"
                  >
                    Manage all API keys
                  </a>
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
                      :icon="
                        index === configData.instructions.length - 1
                          ? 'mdi-check-circle'
                          : 'mdi-numeric-' + (index + 1) + '-circle'
                      "
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

      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="closeDialog">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { getApiBaseURL } from '@/config/api'
import api from '@/services/api'
import {
  generateClaudeCodeConfig,
  generateCodexConfig,
  generateGenericConfig,
} from '@/utils/configTemplates'
import { getPythonPath, detectOS } from '@/utils/pathDetection'

// State
const dialog = ref(false)
const selectedTool = ref(null)
const supportedTools = ref([])
const configData = ref(null)
const loading = ref(false)
const error = ref(null)
const copied = ref(false)
const generatedApiKey = ref(null)
const showApiKeyWarning = ref(false)

// Methods
async function loadSupportedTools() {
  try {
    const response = await api.aiTools.getSupportedTools()
    supportedTools.value = response.data.tools.filter((tool) => tool.supported)
  } catch (err) {
    console.error('[AIToolSetup] Failed to load supported tools:', err)
    // Fallback to default tools if API fails
    supportedTools.value = [
      { id: 'claude', name: 'Claude Code CLI', supported: true },
      { id: 'codex', name: 'Codex CLI', supported: true },
      { id: 'gemini', name: 'Gemini CLI', supported: false },
      { id: 'serena', name: 'Serena MCP', supported: true },
    ]
    error.value = 'Using default tool list. Some features may be limited.'
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
    const apiKeyResponse = await fetch(`${getApiBaseURL()}/api/auth/api-keys`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
      },
      credentials: 'include',
      body: JSON.stringify({ name: keyName }),
    })

    if (!apiKeyResponse.ok) {
      const errorData = await apiKeyResponse.json()
      throw new Error(errorData.detail || 'Failed to create API key')
    }

    const apiKeyData = await apiKeyResponse.json()
    generatedApiKey.value = apiKeyData.key
    showApiKeyWarning.value = true

    // Step 2: Generate configuration using frontend templates with the API key
    const serverUrl = `${window.location.protocol}//${window.location.hostname}:7272`
    const projectPath = 'F:/GiljoAI_MCP'
    const pythonPath = getPythonPath(projectPath, detectOS())

    let configContent = ''
    let fileLocation = ''
    let downloadFilename = ''
    const instructions = []

    if (selectedTool.value === 'claude') {
      configContent = generateClaudeCodeConfig(generatedApiKey.value, serverUrl, pythonPath)
      fileLocation = '~/.claude.json (Claude Code MCP configuration)'
      downloadFilename = 'claude-code-setup.md'
      instructions.push(
        'Locate your Claude Code MCP configuration file:',
        '  • macOS/Linux: ~/.claude.json',
        '  • Windows: %USERPROFILE%\.claude.json',
        "Open the file in a text editor (create if it doesn't exist)",
        'Copy and paste the configuration above into the file',
        'Save the file and restart Claude Code',
        'Verify GiljoAI MCP tools appear in Claude Code',
        'Documentation: https://docs.claude.com/en/docs/claude-code/mcp',
      )
    } else if (selectedTool.value === 'codex') {
      configContent = generateCodexConfig(generatedApiKey.value, serverUrl)
      fileLocation = '~/.codex/config.toml (Codex CLI configuration)'
      downloadFilename = 'codex-setup.md'
      instructions.push(
        'Locate your Codex CLI configuration file:',
        '  • macOS/Linux: ~/.codex/config.toml',
        '  • Windows: %USERPROFILE%\.codex\config.toml',
        'Open the file in a text editor (create directory and file if needed)',
        'Copy and paste the configuration above into the file',
        'Save the file and restart Codex CLI',
        'Test the connection with your first agent command',
        'MCP Documentation: https://developers.openai.com/codex/mcp',
        'CLI Configuration: https://developers.openai.com/codex/local-config#cli',
      )
    } else if (selectedTool.value === 'serena') {
      configContent = generateGenericConfig(generatedApiKey.value, serverUrl)
      fileLocation = 'MCP Client Configuration'
      downloadFilename = 'serena-mcp-setup.md'
      instructions.push(
        'Serena MCP provides intelligent codebase navigation',
        'Configure your MCP client to connect to this server:',
        `  • Server URL: ${serverUrl}`,
        `  • API Key: Your generated key above`,
        'Enable Serena in User Settings → API & Integrations',
        'Visit https://github.com/oraios/serena for more details',
      )
    } else {
      configContent = generateGenericConfig(generatedApiKey.value, serverUrl)
      fileLocation = 'Custom integration'
      downloadFilename = 'generic-api-setup.md'
      instructions.push(
        'Use the API key in your HTTP requests',
        'Include it in the X-API-Key header',
        'See the example code above for usage',
      )
    }

    configData.value = {
      file_location: fileLocation,
      config_content: configContent,
      instructions: instructions,
      download_filename: downloadFilename,
    }

    console.log(
      '[AIToolSetup] Configuration generated successfully with API key for',
      selectedTool.value,
    )
  } catch (err) {
    console.error('[AIToolSetup] Failed to generate config:', err)
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
    console.log('[AIToolSetup] Configuration copied to clipboard')

    // Reset copied state after 2 seconds
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (err) {
    console.error('[AIToolSetup] Failed to copy to clipboard:', err)
    error.value = 'Failed to copy to clipboard. Please copy manually.'
  }
}

async function downloadMarkdownGuide() {
  if (!configData.value || !selectedTool.value) return

  try {
    const response = await fetch(
      `${getApiBaseURL()}/api/ai-tools/config-generator/${selectedTool.value}/markdown`,
    )

    if (!response.ok) {
      throw new Error('Failed to download setup guide')
    }

    const markdown = await response.text()

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

    console.log('[AIToolSetup] Setup guide downloaded successfully')
  } catch (err) {
    console.error('[AIToolSetup] Failed to download guide:', err)
    error.value = 'Failed to download setup guide. Please try again.'
  }
}

function getToolIcon(toolId) {
  const icons = {
    claude: 'mdi-chat-processing',
    codex: 'mdi-code-braces',
    gemini: 'mdi-diamond-stone',
    serena: 'mdi-brain',
  }
  return icons[toolId] || 'mdi-robot'
}

function getToolLogo(toolId) {
  const logos = {
    claude: '/claude_pix.svg',
    codex: '/icons/codex_mark.svg',
    gemini: '/gemini-icon.svg',
    serena: '/Serena.png',
  }
  return logos[toolId] || '/icons/robot.svg'
}

function closeDialog() {
  dialog.value = false
  // Reset state after dialog closes
  setTimeout(() => {
    selectedTool.value = null
    configData.value = null
    error.value = null
    copied.value = false
    generatedApiKey.value = null
    showApiKeyWarning.value = false
  }, 300)
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
</style>
