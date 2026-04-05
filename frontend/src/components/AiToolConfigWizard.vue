<template>
  <v-dialog v-model="showWizard" max-width="720" persistent scrollable>
    <template #activator="{ props }">
      <button v-bind="props" class="configurator-pill smooth-border">
        <v-icon size="16" class="mr-1">mdi-wrench-outline</v-icon>
        Configurator
      </button>
    </template>

    <v-card v-draggable class="smooth-border">
      <div class="dlg-header">
        <v-img src="/giljo_YW_Face.svg" width="32" height="32" class="dlg-icon" style="flex-shrink: 0" />
        <span class="dlg-title">MCP Configuration Tool</span>
        <v-btn icon variant="text" class="dlg-close" aria-label="Close" @click="showWizard = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </div>

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

        <v-divider class="mb-4 opacity-30" />

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
              icon="mdi-pencil"
              size="x-small"
              variant="text"
              class="ml-1"
              @click="editingServer = true"
            />
          </div>
        </div>

        <v-divider class="mb-4 mt-2 opacity-30" />

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
          <template v-if="(selectedTool === 'gemini' || selectedTool === 'claude' || selectedTool === 'codex') && isHttps">
            <v-radio-group v-model="certPlatform" inline hide-details class="platform-radios mb-2">
              <v-radio label="PowerShell" value="windows" density="compact" />
              <v-radio label="Linux / macOS / Git Bash" value="unix" density="compact" />
            </v-radio-group>
            <v-alert type="info" variant="tonal" density="compact" class="mb-3">
              <strong>HTTPS with self-signed certificates:</strong> Node.js-based AI coding agents need to trust the system CA store (one-time setup, requires Node.js 20.12+).
            </v-alert>
            <v-textarea
              v-if="certPlatform === 'windows'"
              :model-value="certTrustCommandWindows"
              label="Certificate Trust (one-time setup)"
              readonly
              rows="2"
              auto-grow
              variant="outlined"
              class="font-monospace no-resize mb-3"
              append-inner-icon="mdi-content-copy"
              :messages="copiedCert ? 'Copied!' : ''"
              @click:append-inner="copyCertCommand"
            />
            <v-textarea
              v-else
              :model-value="certTrustCommandUnix"
              label="Certificate Trust (one-time setup)"
              readonly
              rows="1"
              auto-grow
              variant="outlined"
              class="font-monospace no-resize mb-3"
              append-inner-icon="mdi-content-copy"
              :messages="copiedCert ? 'Copied! Add to ~/.bashrc or ~/.zshrc to persist across sessions.' : 'Add to ~/.bashrc or ~/.zshrc to persist across sessions.'"
              @click:append-inner="copyCertCommand"
            />
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
import {
  buildServerUrl as buildUrl,
  generateConfigForTool,
  generateCodexEnvVar,
  makeKeyName,
  CERT_TRUST_WINDOWS,
  CERT_TRUST_UNIX,
} from '@/composables/useMcpConfig'

const { copy: clipboardCopy } = useClipboard()
const { showToast } = useToast()

const showWizard = ref(false)
const editingServer = ref(false)
const busy = ref(false)
const copied = ref(false)
const copiedEnv = ref(false)
const copiedCert = ref(false)
const errorMsg = ref('')
const selectedPlatform = ref('windows')
const certPlatform = ref('windows')

// Server detection
function detectServerInfo() {
  const hostname = window.location.hostname
  const port = window.location.port || '7272'
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

const certTrustCommandWindows = CERT_TRUST_WINDOWS
const certTrustCommandUnix = CERT_TRUST_UNIX

const envVarCommand = computed(() => generateCodexEnvVar(generatedKey.value, selectedPlatform.value))

function onToolChange() {
  generatedPrompt.value = ''
  errorMsg.value = ''
}

async function generateApiKey() {
  const keyName = makeKeyName(selectedTool.value)
  const resp = await api.apiKeys.create(keyName)
  generatedKey.value = resp.data.api_key
  try {
    window.dispatchEvent(new CustomEvent('api-key-created', { detail: { name: keyName } }))
  } catch {
    /* no-op */
  }
}

function buildServerUrl() {
  return buildUrl(serverIp.value, serverPort.value)
}

async function generatePrompt() {
  try {
    busy.value = true
    errorMsg.value = ''
    generatedPrompt.value = ''
    await generateApiKey()
    const serverUrl = buildServerUrl()
    generatedPrompt.value = generateConfigForTool(selectedTool.value, serverUrl, generatedKey.value)
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
    showToast({ message: 'Configuration copied to clipboard', type: 'success' })
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
    showToast({ message: 'Environment variable copied to clipboard', type: 'success' })
  } else {
    showToast({ message: 'Copy failed — select the text and press Ctrl+C', type: 'warning' })
  }
}

async function copyCertCommand() {
  const text = certPlatform.value === 'windows' ? certTrustCommandWindows : certTrustCommandUnix
  const success = await clipboardCopy(text)
  if (success) {
    copiedCert.value = true
    setTimeout(() => (copiedCert.value = false), 3000)
    showToast({ message: 'Certificate trust command copied to clipboard', type: 'success' })
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

<style lang="scss" scoped>
@use '../styles/design-tokens' as *;
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

.configurator-pill {
  --smooth-border-color: #ffc300;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: $border-radius-rounded;
  padding: 8px 20px;
  height: 40px;
  font-size: 0.82rem;
  font-weight: 500;
  background: transparent;
  color: #ffc300;
  border: none;
  cursor: pointer;
  transition: background $transition-fast;
  white-space: nowrap;
}

.configurator-pill:hover {
  background: rgba(255, 195, 0, 0.12);
}
</style>
