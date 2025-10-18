<template>
  <v-dialog v-model="showWizard" max-width="720">
    <template #activator="{ props }">
      <v-btn v-bind="props" color="primary" size="large" block>
        <template #prepend>
          <v-img src="/Giljo_gray_Face.svg?v=2" width="24" height="24" class="mr-2" cover />
        </template>
        Setup AI Tool Connection
      </v-btn>
    </template>

    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon start>mdi-robot</v-icon>
        AI Tool Self-Configuration
        <v-spacer />
        <v-btn icon="mdi-close" variant="text" @click="showWizard = false" aria-label="Close" />
      </v-card-title>

      <!-- Quick Path -->
      <v-card-text v-if="!showAdvanced">
        <v-alert type="info" variant="tonal" class="mb-4">
          Auto-detected settings from your browser
        </v-alert>

        <v-list density="compact" class="mb-2">
          <v-list-item>
            <template #prepend><v-icon>mdi-robot-happy</v-icon></template>
            <v-list-item-title>AI Tool: {{ detectedToolName }}</v-list-item-title>
          </v-list-item>
          <v-list-item>
            <template #prepend><v-icon>mdi-server</v-icon></template>
            <v-list-item-title>Server: {{ detectedServer }}</v-list-item-title>
          </v-list-item>
        </v-list>

        <v-btn :loading="busy" @click="generateQuickPrompt" block color="success" prepend-icon="mdi-wand">
          Generate Configuration Prompt
        </v-btn>

        <v-btn @click="showAdvanced = true" variant="text" block class="mt-2">
          Customize Settings
        </v-btn>

        <div v-if="generatedPrompt" class="mt-6">
          <v-textarea v-model="generatedPrompt" label="Configuration Prompt" readonly rows="12" />
          <v-btn class="mt-2" color="primary" block prepend-icon="mdi-content-copy" @click="copyPrompt">
            {{ copied ? 'Copied!' : 'Copy Prompt' }}
          </v-btn>
        </div>
      </v-card-text>

      <!-- Advanced Path -->
      <v-card-text v-else>
        <h3 class="text-h6 mb-3">Customize Configuration</h3>
        <v-select
          v-model="selectedTool"
          :items="aiTools"
          item-title="name"
          item-value="value"
          label="AI coding tool"
          variant="outlined"
          class="mb-3"
        />

        <v-row>
          <v-col cols="12" md="8">
            <v-text-field v-model="serverIp" label="Server Hostname or IP" variant="outlined" />
          </v-col>
          <v-col cols="12" md="4">
            <v-text-field v-model="serverPort" label="Port" variant="outlined" />
          </v-col>
        </v-row>

        <v-btn :loading="busy" color="primary" block class="mb-3" @click="generateApiKey">
          Generate API Key for {{ selectedToolName }}
        </v-btn>

        <v-text-field
          v-if="generatedKey"
          v-model="generatedKey"
          label="Generated API Key"
          readonly
          prepend-inner-icon="mdi-key"
          variant="outlined"
          class="mb-3"
        />

        <v-btn :disabled="!generatedKey" color="success" block @click="generateAdvancedPrompt">
          Build Configuration Prompt
        </v-btn>

        <div v-if="generatedPrompt" class="mt-6">
          <v-textarea v-model="generatedPrompt" label="Configuration Prompt" readonly rows="12" />
          <v-btn class="mt-2" color="primary" block prepend-icon="mdi-content-copy" @click="copyPrompt">
            {{ copied ? 'Copied!' : 'Copy Prompt' }}
          </v-btn>
        </div>

        <v-divider class="my-4" />
        <v-btn variant="text" block prepend-icon="mdi-arrow-left" @click="showAdvanced = false">Back</v-btn>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import api from '@/services/api'

const showWizard = ref(false)
const showAdvanced = ref(false)
const busy = ref(false)
const copied = ref(false)

// Detection
function detectServerInfo() {
  const hostname = window.location.hostname
  // Prefer API port 7272 by default
  const port = '7272'
  return { hostname, port }
}

function detectAITool() {
  const ua = navigator.userAgent || ''
  if (/Claude/i.test(ua)) return 'claude'
  if (/Cursor/i.test(ua)) return 'cursor'
  if (/Codex|GitHub/i.test(ua)) return 'codex'
  if (/Gemini|Google/i.test(ua)) return 'gemini'
  return 'claude'
}

// State
const selectedTool = ref(detectAITool())
const serverIp = ref(detectServerInfo().hostname)
const serverPort = ref(detectServerInfo().port)
const generatedKey = ref('')
const generatedPrompt = ref('')

const aiTools = [
  { name: 'Claude Code', value: 'claude' },
  { name: 'Codex CLI', value: 'codex' },
  { name: 'Gemini Code Assist', value: 'gemini' },
  { name: 'Cursor', value: 'cursor' },
]

const detectedToolName = computed(() => aiTools.find(t => t.value === selectedTool.value)?.name || 'Claude Code')
const selectedToolName = computed(() => aiTools.find(t => t.value === selectedTool.value)?.name || 'AI Tool')
const detectedServer = computed(() => `${serverIp.value}:${serverPort.value}`)

function makeKeyName(tool) {
  const map = { claude: 'Claude Code', codex: 'Codex CLI', gemini: 'Gemini', cursor: 'Cursor' }
  return `${map[tool] || 'AI Tool'} prompt key`
}

async function generateApiKey() {
  try {
    busy.value = true
    const keyName = makeKeyName(selectedTool.value)
    const resp = await api.apiKeys.create(keyName)
    // Backend returns APIKeyCreateResponse with 'api_key'
    generatedKey.value = resp.data.api_key
    try {
      window.dispatchEvent(new CustomEvent('api-key-created', { detail: { name: keyName } }))
    } catch (_) { /* no-op */ }
  } catch (e) {
    console.error('[Wizard] Failed to generate API key', e)
  } finally {
    busy.value = false
  }
}

function buildServerUrl() {
  return `http://${serverIp.value}:${serverPort.value}`
}

function claudePrompt(serverUrl, apiKey) {
  return ` Please add the GiljoAI MCP server to your Claude Code configuration:

  1. Locate your Claude Code MCP config file:
     - Windows: C:\Users\[username]\.claude\mcp.json
     - Linux/macOS: ~/.claude/mcp.json

  2. Add this server configuration to the "mcpServers" section:

  "giljo-mcp": {
    "command": "uvx",
    "args": ["giljo-mcp"],
    "env": {
      "GILJO_API_KEY": "${apiKey}",
      "GILJO_SERVER_URL": "${serverUrl}"
    }
  }

  3. Restart Claude Code to activate the new MCP server connection.`
}

function codexPrompt(serverUrl, apiKey) {
  return `Please update your .codex.toml configuration file to add this MCP server:\n\n[mcp.servers.giljo-mcp]
command = "uvx"
args = ["giljo-mcp"]

[mcp.servers.giljo-mcp.env]
GILJO_API_KEY = "${apiKey}"
GILJO_SERVER_URL = "${serverUrl}"
`
}

function geminiPrompt(serverUrl, apiKey) {
  return `Configure your Gemini Code Assist integration with:\n- Base URL: ${serverUrl}\n- Header: X-API-Key: ${apiKey}\n\nApply settings in your IDE's Gemini extension and restart.`
}

function cursorPrompt(serverUrl, apiKey) {
  return `Configure Cursor to connect to GiljoAI MCP:\n- Base URL: ${serverUrl}\n- Header: X-API-Key: ${apiKey}\n\nRestart Cursor after saving settings.`
}

function buildPromptFor(tool, serverUrl, apiKey) {
  switch (tool) {
    case 'claude':
      return claudePrompt(serverUrl, apiKey)
    case 'codex':
      return codexPrompt(serverUrl, apiKey)
    case 'gemini':
      return geminiPrompt(serverUrl, apiKey)
    case 'cursor':
      return cursorPrompt(serverUrl, apiKey)
    default:
      return `Use these values with your tool:\n- Base URL: ${serverUrl}\n- Header: X-API-Key: ${apiKey}`
  }
}

async function generateQuickPrompt() {
  try {
    busy.value = true
    // Always generate a fresh key for quick prompt
    await generateApiKey()
    const serverUrl = buildServerUrl()
    generatedPrompt.value = buildPromptFor(selectedTool.value, serverUrl, generatedKey.value)
  } finally {
    busy.value = false
  }
}

function generateAdvancedPrompt() {
  const serverUrl = buildServerUrl()
  generatedPrompt.value = buildPromptFor(selectedTool.value, serverUrl, generatedKey.value)
}

async function copyPrompt() {
  const text = String(generatedPrompt.value || '')
  if (!text) return

  // Fallback for non-secure origins (e.g., http://LAN-IP)
  const fallbackCopy = () => {
    try {
      const ta = document.createElement('textarea')
      ta.value = text
      ta.setAttribute('readonly', '')
      ta.style.position = 'fixed'
      ta.style.top = '-1000px'
      ta.style.left = '-1000px'
      document.body.appendChild(ta)
      ta.select()
      const ok = document.execCommand('copy')
      document.body.removeChild(ta)
      return ok
    } catch (err) {
      console.error('[Wizard] Fallback copy failed:', err)
      return false
    }
  }

  try {
    if (window.isSecureContext || location.hostname === 'localhost' || location.hostname === '127.0.0.1') {
      await navigator.clipboard.writeText(text)
      copied.value = true
    } else {
      // Non-secure context (e.g., LAN IP over http)
      copied.value = fallbackCopy()
    }
  } catch (e) {
    console.warn('[Wizard] Clipboard API failed, using fallback:', e)
    copied.value = fallbackCopy()
  } finally {
    if (copied.value) setTimeout(() => (copied.value = false), 2000)
  }
}
</script>

<style scoped>
</style>
