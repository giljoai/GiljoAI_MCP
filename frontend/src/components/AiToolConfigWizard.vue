<template>
  <v-dialog v-model="showWizard" max-width="720">
    <template #activator="{ props }">
      <v-btn v-bind="props" color="primary" size="large" block prepend-icon="mdi-robot-excited">
        🤖 Setup AI Tool Connection
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
  const date = new Date().toISOString().slice(0, 10)
  return `${map[tool] || 'AI Tool'} - ${date}`
}

async function generateApiKey() {
  try {
    busy.value = true
    const keyName = makeKeyName(selectedTool.value)
    const resp = await api.apiKeys.create(keyName)
    generatedKey.value = resp.data.key
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
  return `Please modify your claude_desktop_config.json file to add this MCP server:\n\n{
  "mcpServers": {
    "giljo-mcp": {
      "command": "uvx",
      "args": ["giljo-mcp"],
      "env": {
        "GILJO_API_KEY": "${apiKey}",
        "GILJO_SERVER_URL": "${serverUrl}"
      }
    }
  }
}
\nAfter updating the file, restart Claude Code to connect to the GiljoAI MCP server.`
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
    // Ensure we have a key
    if (!generatedKey.value) {
      await generateApiKey()
    }
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
  try {
    await navigator.clipboard.writeText(generatedPrompt.value)
    copied.value = true
    setTimeout(() => (copied.value = false), 2000)
  } catch (e) {
    console.error('[Wizard] Failed to copy prompt', e)
  }
}
</script>

<style scoped>
</style>

