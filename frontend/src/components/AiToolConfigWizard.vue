<template>
  <v-dialog v-model="showWizard" max-width="720" persistent>
    <template #activator="{ props }">
      <v-btn v-bind="props" color="primary" variant="flat">
        Configurator
      </v-btn>
    </template>

    <v-card v-draggable>
      <v-card-title class="d-flex align-center justify-space-between">
        <div class="d-flex align-center">
          <v-img src="/giljo_YW_Face.svg" width="32" height="32" class="mr-2" />
          <span>MCP Configuration Tool</span>
        </div>
        <v-btn icon="mdi-close" variant="text" aria-label="Close" @click="showWizard = false" />
      </v-card-title>

      <v-card-text>
        <!-- Tool Selection: Logo + Name + Radio -->
        <v-radio-group v-model="selectedTool" inline class="tool-radios mb-2" hide-details @update:model-value="onToolChange">
          <div v-for="tool in aiTools" :key="tool.value" class="tool-option text-center">
            <v-img
              :src="toolLogos[tool.value]"
              width="36"
              height="36"
              class="mx-auto mb-1"
              contain
            />
            <div class="text-caption mb-1">{{ tool.name }}</div>
            <v-radio :value="tool.value" density="compact" />
          </div>
        </v-radio-group>

        <v-divider class="mb-4" style="opacity: 0.3" />

        <!-- Server Info (centered, inline edit) -->
        <div class="d-flex align-center justify-center mb-1">
          <v-expand-transition>
            <v-row v-if="editingServer" dense class="server-edit-row" style="max-width: 420px">
              <v-col cols="8">
                <v-text-field
                  v-model="serverIp"
                  label="Hostname / IP"
                  variant="outlined"
                  density="compact"
                  hide-details
                />
              </v-col>
              <v-col cols="3">
                <v-text-field
                  v-model="serverPort"
                  label="Port"
                  variant="outlined"
                  density="compact"
                  hide-details
                />
              </v-col>
              <v-col cols="1" class="d-flex align-center">
                <v-btn icon="mdi-check" size="x-small" variant="text" @click="editingServer = false" />
              </v-col>
            </v-row>
          </v-expand-transition>
          <div v-if="!editingServer" class="d-flex align-center text-body-2">
            <v-icon size="small" class="mr-2">mdi-server</v-icon>
            <span>{{ buildServerUrl() }}</span>
            <v-btn
              icon="mdi-pencil-outline"
              size="x-small"
              variant="text"
              class="ml-1"
              @click="editingServer = true"
            />
          </div>
        </div>

        <v-divider class="mb-4 mt-2" style="opacity: 0.3" />

        <!-- Error Alert -->
        <v-alert v-if="errorMsg" type="error" variant="tonal" density="compact" class="mb-3" closable @click:close="errorMsg = ''">
          {{ errorMsg }}
        </v-alert>

        <!-- Generate Button (centered, default yellow) -->
        <div class="d-flex justify-center mb-2">
          <v-btn
            :loading="busy"
            color="primary"
            prepend-icon="mdi-wand"
            @click="generatePrompt"
          >
            Generate Configuration Prompt
          </v-btn>
        </div>

        <!-- Generated Prompt Output -->
        <div v-if="generatedPrompt" class="mt-4">
          <v-alert type="info" variant="tonal" density="compact" class="mb-3">
            <template v-if="selectedTool === 'openclaw'">
              Add this to the <code>mcpServers</code> block in <code>~/.openclaw/openclaw.json</code>, then restart the gateway. Also works with NemoClaw.
            </template>
            <template v-else>
              Copy and paste {{ selectedTool === 'codex' ? 'these commands' : 'this' }} in your terminal to configure {{ selectedToolName }}:
            </template>
          </v-alert>

          <!-- HTTPS: Node.js cert trust warning (Claude Code + Gemini are Node.js-based) -->
          <template v-if="(selectedTool === 'gemini' || selectedTool === 'claude') && isHttps">
            <v-radio-group v-model="certPlatform" inline hide-details class="platform-radios mb-2">
              <v-radio label="PowerShell" value="windows" density="compact" />
              <v-radio label="Linux / macOS / Git Bash" value="unix" density="compact" />
            </v-radio-group>
            <v-alert
              type="warning"
              variant="tonal"
              density="compact"
              class="mb-3"
            >
              <strong>HTTPS with self-signed certificates:</strong> Node.js-based AI coding agents require a one-time setup step.
              <template v-if="certPlatform === 'windows'">
                <code class="d-block mt-1 text-body-2">[System.Environment]::SetEnvironmentVariable('NODE_EXTRA_CA_CERTS', (mkcert -CAROOT) + '\rootCA.pem', 'User')</code>
                <span class="text-caption">Then restart your terminal. This is a one-time setup.</span>
              </template>
              <template v-else>
                <code class="d-block mt-1 text-body-2">export NODE_EXTRA_CA_CERTS="$(mkcert -CAROOT)/rootCA.pem"</code>
                <span class="text-caption">Add to your <code>~/.bashrc</code> or <code>~/.zshrc</code> to make it permanent.</span>
              </template>
            </v-alert>
          </template>

          <!-- C+D) Codex: Platform selector + Environment Variable command -->
          <template v-if="selectedTool === 'codex'">
            <v-radio-group v-model="selectedPlatform" inline hide-details class="platform-radios mb-2">
              <v-radio label="PowerShell" value="windows" density="compact" />
              <v-radio label="Linux / macOS / Git Bash" value="unix" density="compact" />
            </v-radio-group>
            <v-textarea
              :model-value="envVarCommand"
              label="Environment Variable"
              readonly
              rows="2"
              auto-grow
              variant="outlined"
              class="font-monospace no-resize mb-3"
              append-inner-icon="mdi-content-copy"
              :messages="copiedEnv ? 'Copied!' : ''"
              @click:append-inner="copyEnvVar"
            />
          </template>

          <!-- E) Configuration Command / JSON snippet -->
          <v-textarea
            v-model="generatedPrompt"
            :label="selectedTool === 'openclaw' ? 'JSON Configuration' : 'Configuration Command'"
            readonly
            rows="3"
            auto-grow
            variant="outlined"
            class="font-monospace no-resize"
            append-inner-icon="mdi-content-copy"
            :messages="copied ? 'Copied!' : ''"
            @click:append-inner="copyPrompt"
          />
        </div>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import api from '@/services/api'
import { useClipboard } from '@/composables/useClipboard'
import { useToast } from '@/composables/useToast'

const { copy: clipboardCopy } = useClipboard()
const { showToast } = useToast()

const showWizard = ref(false)
const editingServer = ref(false)
const busy = ref(false)
const copied = ref(false)
const copiedEnv = ref(false)
const errorMsg = ref('')
const selectedPlatform = ref('windows')
const certPlatform = ref('windows')

// Server detection
function detectServerInfo() {
  const hostname = window.location.hostname
  const port = '7272'
  return { hostname, port }
}

// State
const selectedTool = ref('claude')
const serverIp = ref(detectServerInfo().hostname)
const serverPort = ref(detectServerInfo().port)
const generatedKey = ref('')
const generatedPrompt = ref('')

const aiTools = [
  { name: 'Claude Code', value: 'claude' },
  { name: 'Codex CLI', value: 'codex' },
  { name: 'Gemini CLI', value: 'gemini' },
  { name: 'OpenClaw', value: 'openclaw' },
]

const toolLogos = {
  claude: '/claude_pix.svg',
  codex: '/icons/codex_mark_white.svg',
  gemini: '/gemini-icon.svg',
  openclaw: '/openclaw-dark.svg',
}

const selectedToolName = computed(
  () => aiTools.find((t) => t.value === selectedTool.value)?.name || 'AI Agent',
)

const isHttps = computed(() => window.location.protocol === 'https:')

const envVarCommand = computed(() => {
  const key = generatedKey.value || 'YOUR_API_KEY'
  if (selectedPlatform.value === 'windows') {
    // setx persists for future sessions, $env: applies to current session
    return `setx GILJO_API_KEY "${key}"\n$env:GILJO_API_KEY="${key}"`
  }
  return `export GILJO_API_KEY="${key}"`
})

function onToolChange() {
  generatedPrompt.value = ''
  errorMsg.value = ''
}

function makeKeyName(tool) {
  const map = {
    claude: 'Claude Code',
    codex: 'Codex CLI',
    gemini: 'Gemini',
    openclaw: 'OpenClaw',
  }
  return `${map[tool] || 'AI Agent'} prompt key`
}

async function generateApiKey() {
  const keyName = makeKeyName(selectedTool.value)
  const resp = await api.apiKeys.create(keyName)
  generatedKey.value = resp.data.api_key
  try {
    window.dispatchEvent(new CustomEvent('api-key-created', { detail: { name: keyName } }))
  } catch (_) {
    /* no-op */
  }
}

function buildServerUrl() {
  const protocol = window.location.protocol === 'https:' ? 'https' : 'http'
  return `${protocol}://${serverIp.value}:${serverPort.value}`
}

function claudePrompt(serverUrl, apiKey) {
  return `claude mcp add --transport http giljo-mcp ${serverUrl}/mcp --header "Authorization: Bearer ${apiKey}"`
}

function codexPrompt(serverUrl) {
  // Codex CLI reads bearer token from env var at runtime.
  // Env var value shown separately in the UI alert above.
  return `codex mcp add giljo-mcp --url ${serverUrl}/mcp --bearer-token-env-var GILJO_API_KEY`
}

function geminiPrompt(serverUrl, apiKey) {
  return `gemini mcp add -t http -H "Authorization: Bearer ${apiKey}" giljo-mcp ${serverUrl}/mcp`
}

function openclawPrompt(serverUrl, apiKey) {
  // JSON snippet for ~/.openclaw/openclaw.json mcpServers block
  return JSON.stringify({
    'giljo-mcp': {
      transport: 'streamable-http',
      url: `${serverUrl}/mcp`,
      headers: { Authorization: `Bearer ${apiKey}` },
    },
  }, null, 2)
}

function buildPromptFor(tool, serverUrl, apiKey) {
  switch (tool) {
    case 'claude':
      return claudePrompt(serverUrl, apiKey)
    case 'codex':
      return codexPrompt(serverUrl)
    case 'gemini':
      return geminiPrompt(serverUrl, apiKey)
    case 'openclaw':
      return openclawPrompt(serverUrl, apiKey)
    default:
      return `Use these values with your tool:\n- Base URL: ${serverUrl}\n- Header: Authorization: Bearer ${apiKey}`
  }
}

async function generatePrompt() {
  try {
    busy.value = true
    errorMsg.value = ''
    generatedPrompt.value = ''
    await generateApiKey()
    const serverUrl = buildServerUrl()
    generatedPrompt.value = buildPromptFor(selectedTool.value, serverUrl, generatedKey.value)
  } catch (e) {
    const msg = e?.response?.data?.message || e?.message || 'Failed to generate API key'
    errorMsg.value = msg
    console.error('[Wizard] Failed to generate API key', e)
  } finally {
    busy.value = false
  }
}

async function copyPrompt() {
  const text = String(generatedPrompt.value || '').trim()
  if (!text) return
  const success = await clipboardCopy(text)
  if (success) {
    copied.value = true
    setTimeout(() => (copied.value = false), 3000)
    showToast({ message: 'Configuration copied to clipboard!', type: 'success' })
  } else {
    showToast({ message: 'Copy failed — select the text and press Ctrl+C', type: 'warning' })
  }
}

async function copyEnvVar() {
  const text = envVarCommand.value
  if (!text) return
  const success = await clipboardCopy(text)
  if (success) {
    copiedEnv.value = true
    setTimeout(() => (copiedEnv.value = false), 3000)
    showToast({ message: 'Environment variable copied to clipboard!', type: 'success' })
  } else {
    showToast({ message: 'Copy failed — select the text and press Ctrl+C', type: 'warning' })
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
.tool-radios :deep(.v-selection-control-group) {
  gap: 0;
  justify-content: center;
}

.tool-option {
  min-width: 120px;
  padding: 8px 16px;
}

.font-monospace :deep(textarea) {
  font-family: 'Courier New', Courier, monospace;
  font-size: 14px;
}

.no-resize :deep(textarea) {
  resize: none;
}

.platform-radios :deep(.v-selection-control-group) {
  gap: 10px;
  justify-content: center;
}
</style>
