<template>
  <div class="step-connect">
    <p class="step-heading">Connect your tools to GiljoAI MCP</p>

    <!-- Tool tabs (only if multiple tools selected) -->
    <div v-if="tools.length > 1" class="tool-tabs" role="tablist">
      <button
        v-for="tool in tools"
        :key="tool.id"
        role="tab"
        :aria-selected="activeToolId === tool.id"
        :class="['tool-tab', 'smooth-border', { 'tool-tab--active': activeToolId === tool.id }]"
        @click="activeToolId = tool.id"
      >
        <img :src="tool.logo" :alt="tool.name" class="tool-tab-logo" />
        <span>{{ tool.name }}</span>
        <span
          :class="['tab-status-dot', connectionStatus[tool.id] === 'connected' ? 'tab-status-dot--connected' : '']"
        />
      </button>
    </div>

    <!-- Active tool panel -->
    <div class="tool-panel" role="tabpanel">
      <!-- 1. Server URL -->
      <div class="panel-section panel-section--centered">
        <label class="section-label">Server URL</label>
        <div class="server-url-row">
          <v-text-field
            v-model="serverUrl"
            variant="outlined"
            density="compact"
            hide-details
            class="server-url-field"
            readonly
            @click="editingServer = !editingServer"
          />
        </div>
        <v-expand-transition>
          <div v-if="editingServer" class="server-edit-fields">
            <v-text-field
              v-model="serverHostname"
              label="Hostname / IP"
              variant="outlined"
              density="compact"
              hide-details
              class="server-field"
            />
            <v-text-field
              v-model="serverPort"
              label="Port"
              variant="outlined"
              density="compact"
              hide-details
              class="server-field server-field--port"
            />
            <v-btn icon="mdi-check" size="x-small" variant="text" @click="editingServer = false" />
          </div>
        </v-expand-transition>
      </div>

      <!-- 2. API Key Status -->
      <div class="panel-section panel-section--centered">
        <label class="section-label">API Key</label>

        <!-- Checking for existing key -->
        <div v-if="checkingKey" class="api-key-status api-key-status--centered">
          <v-progress-circular size="16" width="2" indeterminate :color="COLOR_MUTED" />
          <span class="status-text">Checking for existing key...</span>
        </div>

        <!-- Generating key -->
        <div v-else-if="generatingKey" class="api-key-status api-key-status--centered">
          <v-progress-circular size="16" width="2" indeterminate :color="COLOR_MUTED" />
          <span class="status-text">Generating API key...</span>
        </div>

        <!-- Fresh key generated (full key available) -->
        <div v-else-if="generatedKey" class="api-key-status api-key-status--centered">
          <v-icon size="16" :color="COLOR_SUCCESS">mdi-check-circle</v-icon>
          <span class="status-text">Key generated — copy the config below</span>
        </div>

        <!-- Existing key found (prefix only, no plaintext) -->
        <div v-else-if="existingKeyPrefix" class="api-key-status api-key-status--centered">
          <v-icon size="16" :color="COLOR_SUCCESS">mdi-check-circle</v-icon>
          <span class="status-text">Key exists ({{ existingKeyPrefix }}...)</span>
          <v-btn
            size="small"
            color="primary"
            variant="flat"
            prepend-icon="mdi-key-plus"
            class="ml-3"
            :loading="generatingKey"
            @click="handleGenerateKey"
          >
            Generate New Config
          </v-btn>
          <v-btn
            size="small"
            variant="text"
            class="ml-1"
            @click="skipAlreadyConfigured"
          >
            I already configured this
          </v-btn>
        </div>

        <!-- No key at all -->
        <div v-else class="api-key-status api-key-status--centered">
          <v-btn
            size="small"
            color="primary"
            variant="flat"
            prepend-icon="mdi-key-plus"
            :loading="generatingKey"
            @click="handleGenerateKey"
          >
            Generate API Key
          </v-btn>
        </div>

        <v-alert v-if="keyError" type="error" variant="tonal" density="compact" class="mt-2" closable @click:close="keyError = ''">
          {{ keyError }}
        </v-alert>
      </div>

      <!-- 3. Configuration Display (only when key is available) -->
      <div v-if="hasKey" class="panel-section">
        <label class="section-label">Configuration</label>

        <!-- HTTPS cert trust (Node.js tools) -->
        <template v-if="needsCertTrust">
          <v-btn-toggle v-model="platform" mandatory variant="outlined" divided rounded="t-lg" color="primary" class="mb-3">
            <v-btn value="windows" size="small">PowerShell</v-btn>
            <v-btn value="unix" size="small">Linux / macOS</v-btn>
          </v-btn-toggle>
          <v-alert type="info" variant="tonal" density="compact" class="mb-3">
            <strong>HTTPS with self-signed certificates:</strong> Node.js-based AI coding agents need to trust the system CA store (one-time setup, requires Node.js 20.12+).
          </v-alert>
          <div class="config-block smooth-border">
            <div class="config-block-header">
              <span class="config-block-label">Certificate Trust (one-time)</span>
              <v-btn
                icon="mdi-content-copy"
                size="x-small"
                variant="text"
                aria-label="Copy certificate command"
                @click="copyText(certCommand, 'cert')"
              />
            </div>
            <pre class="config-code">{{ certCommand }}</pre>
            <span v-if="copiedField === 'cert'" class="copied-badge">Copied!</span>
          </div>
        </template>

        <!-- Platform toggle for Codex env var (if not already shown for HTTPS) -->
        <v-btn-toggle v-if="!needsCertTrust && activeNormalizedId === 'codex'" v-model="platform" mandatory variant="outlined" divided rounded="t-lg" color="primary" class="mb-3">
          <v-btn value="windows" size="small">PowerShell</v-btn>
          <v-btn value="unix" size="small">Linux / macOS</v-btn>
        </v-btn-toggle>

        <!-- Codex: Environment Variable -->
        <div v-if="activeNormalizedId === 'codex'" class="config-block smooth-border">
          <div class="config-block-header">
            <span class="config-block-label">Environment Variable</span>
            <v-btn
              icon="mdi-content-copy"
              size="x-small"
              variant="text"
              aria-label="Copy environment variable"
              @click="copyText(envVarText, 'env')"
            />
          </div>
          <pre class="config-code">{{ envVarText }}</pre>
          <span v-if="copiedField === 'env'" class="copied-badge">Copied!</span>
        </div>

        <!-- Main config command -->
        <div class="config-block smooth-border">
          <div class="config-block-header">
            <span class="config-block-label">Configuration Command — copy in terminal, not inside tool session</span>
            <v-btn
              icon="mdi-content-copy"
              size="x-small"
              variant="text"
              aria-label="Copy configuration command"
              @click="copyText(configCommand, 'config')"
            />
          </div>
          <pre class="config-code">{{ configCommand }}</pre>
          <span v-if="copiedField === 'config'" class="copied-badge">Copied!</span>
        </div>
      </div>

      <!-- 4. Connection Status -->
      <div class="panel-section connection-section">
        <p class="instruction-text mb-4">Start your AI Coding tool</p>
        <div class="connection-status-line">
          <span class="connection-label">CONNECTION STATUS:</span>
          <span
            :class="[
              'status-indicator',
              connectionStatus[activeToolId] === 'connected'
                ? 'status-indicator--connected'
                : 'status-indicator--waiting',
            ]"
          >
            {{ connectionStatus[activeToolId] === 'connected' ? 'Connected' : 'Not Connected' }}
          </span>
        </div>
        <p class="instruction-text mt-4">Ask your AI Coding tool to run a health check</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

/* design-token-exempt: Vuetify color prop requires hex values */
const COLOR_MUTED = '#8f97b7' // $lightest-blue
const COLOR_SUCCESS = '#6bcf7f' // $gradient-brand-end
import api from '@/services/api'
import { useClipboard } from '@/composables/useClipboard'
import { useToast } from '@/composables/useToast'
import { useWebSocketStore } from '@/stores/websocket'
import {
  normalizeToolId,
  detectPlatform,
  buildServerUrl,
  isHttps,
  generateConfigForTool,
  generateCodexEnvVar,
  getCertTrustCommand,
  makeKeyName,
} from '@/composables/useMcpConfig'

const TOOL_META = {
  claude_code: { name: 'Claude Code', logo: '/claude_pix.svg' },
  codex_cli: { name: 'Codex CLI', logo: '/icons/codex_mark_white.svg' },
  gemini_cli: { name: 'Gemini CLI', logo: '/gemini-icon.svg' },
}

const props = defineProps({
  selectedTools: {
    type: Array,
    required: true,
  },
})

const emit = defineEmits(['can-proceed', 'step-data'])

const { copy: clipboardCopy } = useClipboard()
const { showToast } = useToast()
const wsStore = useWebSocketStore()

// Tool list derived from props
const tools = computed(() =>
  props.selectedTools.map((id) => ({
    id,
    ...TOOL_META[id],
  })),
)

// Active tab
const activeToolId = ref(props.selectedTools[0] || 'claude_code')
const activeNormalizedId = computed(() => normalizeToolId(activeToolId.value))

// Server config
const serverHostname = ref(window.location.hostname)
const serverPort = ref(window.location.port || '7272')
const editingServer = ref(false)
const serverUrl = computed(() => buildServerUrl(serverHostname.value, serverPort.value))

// Platform
const platform = ref(detectPlatform())

// API key state
const checkingKey = ref(false)
const existingKeyPrefix = ref(null)
const generatedKey = ref(null)
const generatingKey = ref(false)
const keyError = ref('')

const hasKey = computed(() => !!generatedKey.value)
const currentApiKey = computed(() => generatedKey.value || '')

// Config generation
const configCommand = computed(() =>
  generateConfigForTool(activeToolId.value, serverUrl.value, currentApiKey.value),
)

const envVarText = computed(() =>
  generateCodexEnvVar(currentApiKey.value, platform.value),
)

const certCommand = computed(() => getCertTrustCommand(platform.value))

const needsCertTrust = computed(() => isHttps())

// Copy state
const copiedField = ref(null)
let copyTimeout = null

async function copyText(text, field) {
  const success = await clipboardCopy(text)
  if (success) {
    copiedField.value = field
    clearTimeout(copyTimeout)
    copyTimeout = setTimeout(() => { copiedField.value = null }, 3000)
    showToast({ message: 'Copied to clipboard', type: 'success' })
  } else {
    showToast({ message: 'Copy failed — select the text and press Ctrl+C', type: 'warning' })
  }
}

// Check for existing API key on mount
async function checkExistingKey() {
  if (existingKeyPrefix.value || generatedKey.value) return
  checkingKey.value = true
  try {
    const resp = await api.apiKeys.getActive()
    const keys = resp.data
    if (keys && keys.length > 0) {
      existingKeyPrefix.value = keys[0].key_prefix
    }
  } catch (e) {
    console.warn('[SetupStep2] Failed to check active keys:', e)
  } finally {
    checkingKey.value = false
  }
}

async function handleGenerateKey() {
  generatingKey.value = true
  keyError.value = ''
  try {
    const keyName = makeKeyName(activeToolId.value)
    const resp = await api.apiKeys.create(keyName)
    generatedKey.value = resp.data.api_key
    existingKeyPrefix.value = null  // clear prefix state since we have the full key now
    try {
      window.dispatchEvent(new CustomEvent('api-key-created', { detail: { name: keyName } }))
    } catch { /* no-op */ }
  } catch (e) {
    keyError.value = e?.response?.data?.message || e?.message || 'Failed to generate API key'
  } finally {
    generatingKey.value = false
  }
}

function skipAlreadyConfigured() {
  // User says they already configured — mark all tools connected
  for (const id of props.selectedTools) {
    connectionStatus.value[id] = 'connected'
  }
}

// Connection status (reactive per-tool)
const connectionStatus = ref(
  Object.fromEntries(props.selectedTools.map((id) => [id, 'waiting'])),
)

// WebSocket subscription for setup:tool_connected
let wsUnsub = null

function handleToolConnected(payload) {
  const toolName = payload?.tool_name
  if (!toolName) return

  // Generic MCP connection event — mark all selected tools as connected
  // (the MCP server can't distinguish which specific CLI tool connected)
  if (toolName === 'mcp_connected') {
    for (const id of props.selectedTools) {
      connectionStatus.value[id] = 'connected'
    }
    return
  }

  // Specific tool match (legacy/future use)
  for (const id of props.selectedTools) {
    if (normalizeToolId(id) === toolName || id === toolName) {
      connectionStatus.value[id] = 'connected'
    }
  }
}

// Computed: can proceed when >= 1 tool connected
const hasConnectedTool = computed(() =>
  Object.values(connectionStatus.value).some((s) => s === 'connected'),
)

// Emit can-proceed whenever connection state changes
watch(hasConnectedTool, (val) => {
  emit('can-proceed', val)
}, { immediate: true })

// Emit step data for parent to persist
const connectedTools = computed(() =>
  Object.entries(connectionStatus.value)
    .filter(([, status]) => status === 'connected')
    .map(([id]) => id),
)

watch(connectedTools, (val) => {
  emit('step-data', { connectedTools: val })
}, { deep: true })

onMounted(() => {
  checkExistingKey()
  wsUnsub = wsStore.on('setup:tool_connected', handleToolConnected)
})

onUnmounted(() => {
  if (wsUnsub) wsUnsub()
  clearTimeout(copyTimeout)
})
</script>

<style scoped lang="scss">
@use '../../styles/variables' as *;
@use '../../styles/design-tokens' as *;

.step-connect {
  max-width: 680px;
  margin: 0 auto;
}

.step-heading {
  font-size: 1rem;
  font-weight: 500;
  color: $color-text-primary;
  margin-bottom: 20px;
  text-align: center;
}

/* Tool tabs */
.tool-tabs {
  display: flex;
  gap: 8px;
  justify-content: center;
  margin-bottom: 20px;
}

.tool-tab {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: $elevation-elevated;
  border: none;
  border-radius: $border-radius-default;
  color: $lightest-blue;
  cursor: pointer;
  font-size: 0.8125rem;
  font-weight: 500;
  transition: color 250ms ease-out, box-shadow 250ms ease-out;
}

.tool-tab--active {
  color: $color-brand-yellow;
  --smooth-border-color: #{$color-brand-yellow};
}

.tool-tab:hover:not(.tool-tab--active) {
  color: $color-text-primary;
}

.tool-tab-logo {
  width: 20px;
  height: 20px;
  object-fit: contain;
}

.tab-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: $lightest-blue;
  transition: background 250ms ease-out;
}

.tab-status-dot--connected {
  background: $gradient-brand-end;
}

/* Panel sections */
.panel-section {
  margin-bottom: 20px;
}

.section-label {
  display: block;
  font-size: 0.75rem;
  font-weight: 600;
  color: $lightest-blue;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 8px;
}

.panel-section--centered {
  text-align: center;
}

.panel-section--centered .section-label {
  text-align: center;
}

/* Server URL */
.server-url-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

.server-url-field {
  max-width: 320px;
  cursor: pointer;
}

.server-url-field :deep(input) {
  font-family: "Roboto Mono", "Courier New", monospace;
  font-size: 0.875rem;
}


.server-edit-fields {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-top: 8px;
  max-width: 400px;
}

.server-field {
  flex: 1;
}

.server-field--port {
  max-width: 100px;
}

/* API Key */
.api-key-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.api-key-status--centered {
  justify-content: center;
}

.status-text {
  font-size: 0.875rem;
  color: $color-text-primary;
}



/* Platform toggle overrides for dark overlay background */
.step-connect :deep(.v-btn-toggle > .v-btn.v-btn--active) {
  background: $elevation-elevated !important;
  color: $color-surface !important;
}

.step-connect :deep(.v-btn-toggle > .v-btn:not(.v-btn--active)) {
  opacity: 0.5;
}

/* Config blocks */
.config-block {
  position: relative;
  background: $color-background-primary;
  border-radius: $border-radius-default;
  padding: 0;
  margin-bottom: 12px;
  overflow: hidden;
}

.config-block-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  background: rgba($med-blue, 0.3);
}

.config-block-label {
  font-size: 0.6875rem;
  font-weight: 600;
  color: $lightest-blue;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.config-code {
  padding: 12px;
  margin: 0;
  font-family: "Roboto Mono", "Courier New", monospace;
  font-size: 0.8125rem;
  line-height: 1.5;
  color: $color-text-primary;
  white-space: pre-wrap;
  word-break: break-all;
}

.copied-badge {
  position: absolute;
  top: 6px;
  right: 44px;
  font-size: 0.6875rem;
  color: $gradient-brand-end;
  font-weight: 600;
}

/* Connection status */
.connection-section {
  text-align: center;
}

.connection-status-line {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.connection-label {
  font-size: 0.8125rem;
  font-weight: 600;
  color: $lightest-blue;
  letter-spacing: 0.5px;
}

.status-indicator {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 0.875rem;
  font-weight: 500;
}

.status-indicator::before {
  content: '';
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}

.status-indicator--waiting {
  color: $lightest-blue;
}

.status-indicator--waiting::before {
  background: $lightest-blue;
}

.status-indicator--connected {
  color: $gradient-brand-end;
}

.status-indicator--connected::before {
  background: $gradient-brand-end;
}

.instruction-text {
  font-size: 0.8125rem;
  color: $lightest-blue;
  line-height: 1.5;
}

/* Responsive */
@media (max-width: 599px) {
  .tool-tabs {
    flex-direction: column;
    align-items: stretch;
  }

  .tool-tab {
    justify-content: center;
  }

  .server-url-field {
    max-width: 100%;
  }

  .server-edit-fields {
    max-width: 100%;
  }
}
</style>
