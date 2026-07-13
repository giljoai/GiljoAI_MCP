<template>
  <div class="step-connect" data-testid="step2-connect">
    <p class="step-heading-grad">Connect your tools</p>
    <p class="step-sub">Add GiljoAI to each tool with a one-click browser sign-in, or an API key.</p>

    <!-- Tool tabs (only if multiple tools selected) -->
    <div v-if="tools.length > 1" class="tool-tabs" role="tablist">
      <button
        v-for="tool in tools"
        :key="tool.id"
        :data-testid="'tool-tab-' + tool.id"
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
      <!-- 1. Server URL — read-only on SaaS, editable on CE -->
      <div class="panel-section panel-section--centered">
        <label class="section-label">Server URL</label>
        <div class="server-url-row">
          <v-text-field
            v-model="serverUrl"
            variant="outlined"
            density="compact"
            hide-details
            data-testid="server-url-field"
            :class="['server-url-field', { 'server-url-field--editable': isCeMode }]"
            readonly
            @click="isCeMode ? (editingServer = !editingServer) : null"
          />
          <v-icon v-if="!isCeMode" size="14" class="server-lock-icon" data-testid="server-url-lock" aria-label="Managed server URL">mdi-lock-outline</v-icon>
        </div>
        <v-expand-transition>
          <div v-if="isCeMode && editingServer" class="server-edit-fields">
            <v-text-field
              v-model="serverHostname"
              label="Hostname / IP"
              variant="outlined"
              density="compact"
              hide-details
              data-testid="server-edit-hostname"
              class="server-field"
            />
            <v-text-field
              v-model="serverPort"
              label="Port"
              variant="outlined"
              density="compact"
              hide-details
              data-testid="server-edit-port"
              class="server-field server-field--port"
            />
            <v-btn icon="mdi-check" size="x-small" variant="text" @click="editingServer = false" />
          </div>
        </v-expand-transition>
      </div>

      <!-- 2a. Browser sign-in — the primary, recommended path (OAuth-capable
           tools, SaaS only). CE is API-key-only: the entire section is
           hidden (FE-6242). User copy says "Browser sign-in", never "OAuth"
           (connect-vocabulary parity locked by P1, FE-6259a/b). -->
      <div v-if="activeSupportsOauth && !isCeMode" class="panel-section oauth-section smooth-border" data-testid="oauth-section">
        <div class="oauth-section-head">
          <span class="oauth-section-title">
            <v-icon size="18" :color="COLOR_BRAND">mdi-shield-key-outline</v-icon>
            Browser sign-in
            <span class="badge-rec">
              <v-icon size="11">mdi-star</v-icon>
              Recommended
            </span>
          </span>
          <span v-if="activeConnected" class="conn-check conn-check--visible">
            <v-icon size="13" :color="COLOR_SUCCESS">mdi-check</v-icon>
            Connected
          </span>
        </div>

        <!-- The green-connect moment — driven by the WebSocket setup:tool_connected event -->
        <div class="conn-status-row">
          <span :class="['conn-dot', activeConnected ? 'conn-dot--connected' : 'conn-dot--waiting']" data-testid="oauth-conn-dot" />
          <span :class="['conn-status-text', activeConnected ? 'conn-status-text--connected' : 'conn-status-text--waiting']">
            {{ activeConnected ? 'Connected' : 'Waiting for connection…' }}
          </span>
        </div>

        <p class="oauth-instruction">
          Add GiljoAI to {{ activeToolName }}. Your browser opens for a one-click sign-in:
        </p>

        <div class="config-block smooth-border">
          <div class="config-block-header">
            <span class="config-block-label">Paste in terminal</span>
            <v-btn
              icon="mdi-content-copy"
              size="x-small"
              variant="text"
              aria-label="Copy sign-in command"
              data-testid="oauth-copy-btn"
              @click="copyText(oauthConfigCommand)"
            />
          </div>
          <pre class="config-code">{{ oauthConfigCommand }}</pre>
        </div>

        <!-- C4: cert-trust note for the browser-sign-in path when the server serves its own TLS cert -->
        <div v-if="needsCertTrust" class="oauth-cert-note smooth-border" data-testid="oauth-cert-note">
          <v-icon size="13" :color="COLOR_MUTED">mdi-shield-lock-outline</v-icon>
          <span>
            <strong>HTTPS certificate trust (one-time):</strong>
            If your browser warned you about this server's certificate, paste the
            command below in your terminal so the CLI tool trusts it too.
          </span>
          <div class="config-block smooth-border mt-2">
            <div class="config-block-header">
              <span class="config-block-label">Paste in terminal</span>
              <v-btn
                icon="mdi-content-copy"
                size="x-small"
                variant="text"
                aria-label="Copy certificate trust command"
                data-testid="oauth-cert-copy-btn"
                @click="copyText(certCommand)"
              />
            </div>
            <pre class="config-code">{{ certCommand }}</pre>
          </div>
        </div>
      </div>

      <!-- 2b. Bearer fallback toggle (OAuth-capable tools, SaaS only).
           CE shows the key flow directly — no toggle needed (FE-6242). -->
      <div v-if="activeSupportsOauth && !isCeMode" class="bearer-toggle-row">
        <span
          class="bearer-toggle-link"
          role="button"
          tabindex="0"
          data-testid="bearer-toggle"
          :aria-expanded="!!bearerRevealed[activeToolId]"
          @click="toggleBearer"
          @keydown.enter.prevent="toggleBearer"
        >
          Use an API key instead
        </span>
      </div>

      <!-- 2c. Key-only note (tools without OAuth, e.g. Antigravity) -->
      <div v-if="!activeSupportsOauth" class="panel-section">
        <div class="apikey-only-note smooth-border" data-testid="apikey-only-note">
          <v-icon size="14" :color="COLOR_MUTED">mdi-information-outline</v-icon>
          {{ activeToolName }} uses an API key. Browser sign-in is not supported.
        </div>
      </div>

      <!-- 3. API key flow — delegated to child component -->
      <SetupStep2KeyFlow
        v-if="showBearerFlow"
        :checking-key="checkingKey"
        :generating-key="generatingKey"
        :generated-key="generatedKey"
        :existing-key-prefix="existingKeyPrefix"
        :key-error="keyError"
        :has-key="hasKey"
        :needs-cert-trust="needsCertTrust"
        :active-supports-oauth="activeSupportsOauth"
        :active-connected="activeConnected"
        :active-normalized-id="activeNormalizedId"
        :platform="platform"
        :cert-command="certCommand"
        :env-var-text="envVarText"
        :config-command="configCommand"
        :color-muted="COLOR_MUTED"
        :color-success="COLOR_SUCCESS"
        @generate-key="handleGenerateKey"
        @clear-key-error="keyError = ''"
        @set-platform="(p) => (platform = p)"
        @copy-text="({ text }) => copyText(text)"
      />
    </div>

    <!-- Bottom skip link (between Back and Next) -->
    <div v-if="existingKeyPrefix && !generatedKey" class="skip-configured">
      <span
        class="skip-configured-link"
        role="button"
        tabindex="0"
        data-testid="skip-configured"
        @click="skipAlreadyConfigured"
        @keydown.enter.prevent="skipAlreadyConfigured"
      >
        I already configured this
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue'
import { TEXT_MUTED_BLUE as COLOR_MUTED, COLOR_SUCCESS_SETUP as COLOR_SUCCESS, COLOR_BRAND } from '@/config/colorTokens'
import api from '@/services/api'
import configService from '@/services/configService'
import { useClipboard } from '@/composables/useClipboard'
import { useToast } from '@/composables/useToast'
import { useWebSocketStore } from '@/stores/websocket'
import {
  normalizeToolId,
  detectPlatform,
  buildServerUrl,
  isBackendHttps,
  generateConfigForTool,
  generateCodexEnvVar,
  getCertTrustCommand,
  makeKeyName,
  getAuthCapabilities,
} from '@/composables/useMcpConfig'
import SetupStep2KeyFlow from './SetupStep2KeyFlow.vue'

const TOOL_META = {
  claude_code: { name: 'Claude Code CLI', logo: '/claude-color.svg' },
  codex_cli: { name: 'Codex CLI', logo: '/icons/codex_mark_white.svg' },
  gemini_cli: { name: 'Gemini CLI', logo: '/gemini-icon.svg' },
  antigravity_cli: { name: 'Antigravity CLI', logo: '/antigravity-color.svg' },
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

// Edition: server URL is editable only on CE (self-hosted). On SaaS / unknown it
// stays read-only (managed). Positively confirm 'ce' before unlocking — never
// default to editable on uncertainty (FE-6055).
const isCeMode = ref(false)

// Per-tool auth capability (BE-6157) drives browser-sign-in-default vs key-only.
// NOTE: AUTH_CAPABILITIES.oauth_quirk_note is intentionally NEVER surfaced here —
// its Codex literal ("OAuth auto-detected on add.") leaks the banned word "OAuth"
// into user copy. P1 dropped it from the Split Rail configurator (FE-6259a);
// this step drops it too (connect-vocabulary parity, FE-6259b).
const activeCaps = computed(() => getAuthCapabilities(activeToolId.value))
const activeSupportsOauth = computed(() => activeCaps.value?.supports_oauth === true)
const activeToolName = computed(() => TOOL_META[activeToolId.value]?.name || 'your tool')

// Bearer fallback reveal state, per tool (revealing on one tab must not affect others).
const bearerRevealed = reactive({})
function toggleBearer() {
  bearerRevealed[activeToolId.value] = !bearerRevealed[activeToolId.value]
}

// The API-key flow is shown for key-only tools always, when the OAuth-capable
// tool's "Use an API key instead" fallback is revealed, OR on CE (which is
// API-key-only — no OAuth toggle needed) (FE-6242).
const showBearerFlow = computed(
  () => isCeMode.value || !activeSupportsOauth.value || !!bearerRevealed[activeToolId.value],
)

// Backend config (INF-5012) — fetched from GET /api/v1/config/frontend on mount.
// Populated asynchronously; stays null until the fetch resolves, in which case
// the UI falls back to window.location.* so it renders immediately.
const backendConfig = ref(null)

// Server config — editable fields mirror backendConfig once loaded (important
// for proxied deployments where window.location differs from backend identity).
// On reverse-proxy deployments api.port=null — mirrored as empty so the port
// field doesn't show a stale 7272.
const serverHostname = ref(window.location.hostname)
const serverPort = ref(window.location.port || '7272')
const editingServer = ref(false)

// serverUrl: always use the object-signature of buildServerUrl so an empty
// port correctly omits ':port' instead of falling back to 7272.
const serverUrl = computed(() => {
  if (backendConfig.value && !editingServer.value) {
    return buildServerUrl(backendConfig.value)
  }
  const browserProtocol = window.location.protocol === 'https:' ? 'https' : 'http'
  const protocol = backendConfig.value?.protocol || browserProtocol
  const trimmedPort = String(serverPort.value || '').trim()
  return buildServerUrl({
    host: serverHostname.value,
    port: trimmedPort === '' ? null : trimmedPort,
    protocol,
  })
})

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

// Config generation — bearer (fallback path)
const configCommand = computed(() =>
  generateConfigForTool(activeToolId.value, serverUrl.value, currentApiKey.value),
)

// Config generation — OAuth (primary path): emits the `mcp add` command WITHOUT a
// bearer header; the CLI runs its own browser OAuth handshake (FE-6157).
const oauthConfigCommand = computed(() =>
  generateConfigForTool(activeToolId.value, serverUrl.value, '', { authMethod: 'oauth' }),
)

const envVarText = computed(() =>
  generateCodexEnvVar(currentApiKey.value, platform.value),
)

const certCommand = computed(() => getCertTrustCommand(platform.value))

// Cert-trust UI fires only when the backend itself serves TLS (bring-your-own cert).
// NOT when HTTPS is terminated by a reverse proxy (Cloudflare Tunnel, nginx) —
// those deployments have a trusted public CA, so no cert-trust step is needed.
const needsCertTrust = computed(() => isBackendHttps(backendConfig.value))

async function copyText(text) {
  const success = await clipboardCopy(text)
  if (success) {
    showToast({ message: 'Copied to clipboard', type: 'success' })
  } else {
    showToast({ message: 'Copy failed. Select the text and press Ctrl+C', type: 'warning' })
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

// The active tab's connection state — drives the green-connect light.
const activeConnected = computed(() => connectionStatus.value[activeToolId.value] === 'connected')

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

async function loadBackendConfig() {
  try {
    const cfg = await configService.fetchConfig()
    if (!cfg?.api) return
    backendConfig.value = cfg.api
    // Unlock the editable server URL only when positively CE (self-hosted).
    // Reads giljo_mode straight off the config payload: the useSaasMode/
    // useEditionCapabilities funnel lives under saas/ and a CE component must not
    // import it (edition-isolation Deletion Test). Same precedent as authGuard.js.
    // eslint-disable-next-line giljo-internal/no-scattered-mode-checks
    isCeMode.value = cfg.giljo_mode === 'ce'
    // Mirror real backend host/port into the editable fields so the user sees
    // the actual backend identity (not window.location, which may be the proxy).
    if (cfg.api.host) {
      serverHostname.value = cfg.api.host
    }
    // port may be null on reverse-proxy deployments (std 443/80) — mirror as
    // empty so the edit UI doesn't show a stale 7272 (INF-5012b).
    serverPort.value = cfg.api.port != null ? String(cfg.api.port) : ''
  } catch (e) {
    // Keep window.location.* fallback — harmless on CE localhost/LAN.
    console.warn('[SetupStep2] Failed to fetch backend config:', e)
  }
}

onMounted(() => {
  checkExistingKey()
  loadBackendConfig()
  wsUnsub = wsStore.on('setup:tool_connected', handleToolConnected)
})

onUnmounted(() => {
  if (wsUnsub) wsUnsub()
})
</script>

<style scoped lang="scss" src="./SetupStep2Connect.scss"></style>
