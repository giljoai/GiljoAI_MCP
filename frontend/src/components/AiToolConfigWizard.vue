<template>
  <v-dialog v-model="showWizard" max-width="720">
    <template #activator="{ props }">
      <v-btn v-bind="props" color="primary" variant="flat" size="small" width="120">
        Configurator
      </v-btn>
    </template>

    <v-card>
      <v-card-title class="d-flex align-center justify-space-between">
        <div class="d-flex align-center">
          <v-img src="/giljo_YW_Face.svg" width="32" height="32" class="mr-2" />
          <span>AI Tool Configuration</span>
        </div>
        <v-btn icon="mdi-close" variant="text" aria-label="Close" @click="showWizard = false" />
      </v-card-title>

      <!-- Quick Path -->
      <v-card-text v-if="!showAdvanced">
        <v-alert type="info" variant="tonal" class="mb-4">
          Auto-detected settings from your browser
        </v-alert>

        <v-list density="compact" class="mb-2">
          <v-list-item>
            <template #prepend>
              <v-img :src="toolLogo" width="28" height="28" class="mr-2" contain />
            </template>
            <v-list-item-title>AI Tool: {{ detectedToolName }}</v-list-item-title>
          </v-list-item>
          <v-list-item>
            <template #prepend><v-icon>mdi-server</v-icon></template>
            <v-list-item-title>Server: {{ detectedServer }}</v-list-item-title>
          </v-list-item>
        </v-list>

        <v-btn
          :loading="busy"
          block
          color="success"
          prepend-icon="mdi-wand"
          @click="generateQuickPrompt"
        >
          Generate Configuration Prompt
        </v-btn>

        <v-btn variant="text" block class="mt-2" @click="showAdvanced = true">
          Customize Settings
        </v-btn>

        <div v-if="generatedPrompt" class="mt-6">
          <v-alert type="info" class="mb-4">
            Copy and paste this command in your terminal to configure {{ detectedToolName }}:
          </v-alert>
          <v-textarea
            v-model="generatedPrompt"
            label="Configuration Command"
            readonly
            rows="2"
            variant="outlined"
            class="font-monospace no-resize"
            append-inner-icon="mdi-content-copy"
            :messages="
              copied ? 'Command copied to clipboard!' : 'Click the copy icon to copy the command'
            "
            @click:append-inner="copyPrompt"
          />
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
          <v-alert type="info" class="mb-4">
            Copy and paste this command in your terminal to configure {{ detectedToolName }}:
          </v-alert>
          <v-textarea
            v-model="generatedPrompt"
            label="Configuration Command"
            readonly
            rows="2"
            variant="outlined"
            class="font-monospace no-resize"
            append-inner-icon="mdi-content-copy"
            :messages="
              copied ? 'Command copied to clipboard!' : 'Click the copy icon to copy the command'
            "
            @click:append-inner="copyPrompt"
          />
        </div>

        <v-divider class="my-4" />
        <v-btn variant="text" block prepend-icon="mdi-arrow-left" @click="showAdvanced = false"
          >Back</v-btn
        >
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

const detectedToolName = computed(
  () => aiTools.find((t) => t.value === selectedTool.value)?.name || 'Claude Code',
)
const selectedToolName = computed(
  () => aiTools.find((t) => t.value === selectedTool.value)?.name || 'AI Tool',
)
const detectedServer = computed(() => `${serverIp.value}:${serverPort.value}`)

// Get the appropriate logo for the selected tool
const toolLogo = computed(() => {
  const logos = {
    claude: '/claude_pix.svg',
    codex: '/icons/codex_mark.svg',
    gemini: '/gemini-icon.svg',
    cursor: '/claude_pix.svg', // Using Claude pix for Cursor too
  }
  return logos[selectedTool.value] || logos.claude
})

function makeKeyName(tool) {
  const map = {
    claude: 'Claude Code',
    codex: 'Codex CLI',
    gemini: 'Gemini',
    cursor: 'Cursor',
  }
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
    } catch (_) {
      /* no-op */
    }
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
  // Return ONLY the command - adds to user profile by default (available in all projects)
  return `claude mcp add --transport http giljo-mcp ${serverUrl}/mcp --header "X-API-Key: ${apiKey}"`
}

function codexPrompt(serverUrl, apiKey) {
  // StdIO proxy with env managed by Codex (no shell restart required)
  // Proxy module is provided by the giljo-mcp wheel installed via pip.
  return `codex mcp add giljo-mcp --env GILJO_MCP_SERVER_URL="${serverUrl}" --env GILJO_API_KEY="${apiKey}" -- python -m giljo_mcp.mcp_http_stdin_proxy`
}

function geminiPrompt(serverUrl, apiKey) {
  // HTTP transport with explicit header; order is <name> <url>
  return `gemini mcp add -t http -H "X-API-Key: ${apiKey}" giljo-mcp ${serverUrl}/mcp`
}

function cursorPrompt(serverUrl, apiKey) {
  // Cursor needs manual config, so just return the values
  return `Base URL: ${serverUrl}/mcp
API Key: ${apiKey}`
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
  const text = String(generatedPrompt.value || '').trim()
  if (!text) return

  // Simple approach - just select the text in the textarea
  try {
    // Find the textarea and select its content
    const textarea = document.querySelector('.font-monospace textarea')
    if (textarea) {
      textarea.focus()
      textarea.select()

      // Try to copy
      const success = document.execCommand('copy')

      if (success) {
        copied.value = true
        setTimeout(() => (copied.value = false), 3000)
      } else {
        // If copy fails, at least the text is selected for manual copy
        copied.value = true
        setTimeout(() => (copied.value = false), 3000)
      }
    }
  } catch (e) {
    // Fallback - just select the text for manual copy
    const textarea = document.querySelector('.font-monospace textarea')
    if (textarea) {
      textarea.focus()
      textarea.select()
      copied.value = true
      setTimeout(() => (copied.value = false), 3000)
    }
  }
}

// Expose method to programmatically open the wizard
defineExpose({
  open: () => {
    showWizard.value = true
  },
})
</script>

<style scoped>
.font-monospace :deep(textarea) {
  font-family: 'Courier New', Courier, monospace !important;
  font-size: 14px !important;
}

.no-resize :deep(textarea) {
  resize: none !important;
}
</style>
