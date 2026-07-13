<template>
  <main class="pane smooth-border" :class="'route-' + route">
    <!-- WEB & APP -->
    <section v-if="route === 'web'" class="pane-section" data-testid="pane-web">
      <div class="pane-eyebrow route-web">
        <v-icon size="14">mdi-earth</v-icon>Web &amp; app integration
      </div>
      <h2 class="pane-heading">Paste one link into your app</h2>
      <p class="pane-lead">Works with claude.ai, ChatGPT, and any IDE that accepts an MCP connector URL.</p>

      <div class="big-url smooth-border" data-testid="web-url-display">
        <span class="big-url-text">
          <v-icon size="16" class="big-url-icon">mdi-link-variant</v-icon>{{ serverUrlEndpoint }}
        </span>
        <v-btn
          class="big-url-copy"
          variant="flat"
          size="small"
          data-testid="web-url-copy-btn"
          @click="copyWebUrl"
        >
          {{ copiedWebUrl ? 'Copied' : 'Copy' }}
        </v-btn>
      </div>

      <ol class="pane-steps">
        <li><span class="step-num route-web">1</span><span>Open your app's connection or connector settings.</span></li>
        <li><span class="step-num route-web">2</span><span>Paste the link and save.</span></li>
        <li><span class="step-num route-web">3</span><span>Launch the agent and authenticate in your browser.</span></li>
      </ol>
    </section>

    <!-- TERMINAL / CLI -->
    <section v-else-if="route === 'cli'" class="pane-section" data-testid="pane-cli">
      <div class="pane-eyebrow route-cli">{{ selectedRow.vendor }} · terminal</div>
      <h2 class="pane-heading">Connect {{ selectedRow.name }}</h2>
      <p class="pane-lead">Run this once. The CLI opens your browser to authorize. No key to store.</p>

      <div class="code-block smooth-border" data-testid="configurator-artifact">
        <div class="code-block-header">
          <span class="code-block-lang">{{ commandLang }}</span>
          <v-btn
            class="code-copy-btn"
            size="x-small"
            variant="text"
            :prepend-icon="copied ? 'mdi-check' : 'mdi-content-copy'"
            data-testid="configurator-copy-btn"
            @click="copyCommand"
          >
            {{ copied ? 'Copied!' : 'Copy' }}
          </v-btn>
        </div>
        <pre class="config-code" data-testid="config-command">{{ command }}</pre>
      </div>

      <ol class="pane-steps">
        <li><span class="step-num route-cli">1</span><span>Paste the command in your terminal and press Enter.</span></li>
        <li><span class="step-num route-cli">2</span><span>A browser window opens. Approve the connection.</span></li>
      </ol>
    </section>

    <!-- API KEY -->
    <section v-else class="pane-section" data-testid="pane-key">
      <div class="pane-eyebrow route-key">{{ selectedRow.vendor }} · api key</div>
      <h2 class="pane-heading">Connect {{ selectedRow.name }}</h2>
      <p class="pane-lead">
        For generic MCP clients, headless jobs, or tools that can't sign in through a browser.
      </p>

      <!-- Server URL -->
      <div class="server-row">
        <span class="server-label">Server URL</span>
        <template v-if="!isCe">
          <!-- SaaS: read-only, copyable -->
          <span class="server-url-chip" data-testid="server-url-chip">
            <v-icon size="14">mdi-server-network</v-icon>{{ serverUrlEndpoint }}
          </span>
          <v-btn
            icon="mdi-content-copy"
            size="x-small"
            variant="text"
            class="ml-1"
            aria-label="Copy server URL"
            @click="copyUrl"
          />
          <span v-if="copiedUrl" class="copied-hint">Copied!</span>
        </template>
        <template v-else>
          <!-- CE: editable -->
          <div v-if="!editingServer" class="d-flex align-center" data-testid="server-url-edit">
            <span class="server-url-chip">
              <v-icon size="14">mdi-server-network</v-icon>{{ serverUrlEndpoint }}
            </span>
            <v-btn
              icon="mdi-pencil"
              size="x-small"
              variant="text"
              class="ml-1"
              aria-label="Edit server URL"
              @click="editingServer = true"
            />
          </div>
          <v-row v-else dense class="server-edit-row" style="max-width: 380px">
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
        </template>
      </div>

      <!-- Error -->
      <v-alert
        v-if="errorMsg"
        type="error"
        variant="tonal"
        density="compact"
        class="mb-3"
        closable
        @click:close="errorMsg = ''"
      >
        {{ errorMsg }}
      </v-alert>

      <!-- HTTPS self-signed cert trust (CE only, Node-based tools). Kept
           reachable here since CE no longer has a separate Terminal/CLI
           route — this is where CE Node-CLI users land. -->
      <template v-if="showCertTrust">
        <v-radio-group v-model="certPlatform" inline hide-details class="platform-radios mb-2">
          <v-radio label="PowerShell" value="windows" density="compact" />
          <v-radio label="Linux / macOS / Git Bash" value="unix" density="compact" />
        </v-radio-group>
        <v-alert type="info" variant="tonal" density="compact" class="mb-3">
          <strong>HTTPS with self-signed certificates:</strong> Node.js-based AI coding agents need to trust the system CA store (one-time setup, requires Node.js 22+).
        </v-alert>
        <v-textarea
          :model-value="certPlatform === 'windows' ? certTrustCommandWindows : certTrustCommandUnix"
          label="Certificate Trust (one-time setup)"
          readonly
          :rows="certPlatform === 'windows' ? 2 : 1"
          auto-grow
          variant="outlined"
          class="font-monospace no-resize mb-3"
          append-inner-icon="mdi-content-copy"
          :messages="copiedCert ? 'Copied!' : ''"
          @click:append-inner="copyCertCommand"
        />
      </template>

      <!-- Bearer key generation -->
      <div class="bearer-row">
        <v-icon size="18" class="bearer-icon">mdi-key-variant</v-icon>
        <p>
          API keys have no expiry and grant access to your GiljoAI workspace.
          <em>Store them like a password.</em>
        </p>
        <v-btn
          class="bearer-gen-btn"
          :loading="busy"
          variant="flat"
          size="small"
          :prepend-icon="generatedKey ? 'mdi-check' : 'mdi-plus'"
          data-testid="generate-key-btn"
          @click="generateKey"
        >
          {{ generatedKey ? 'Key ready' : 'Generate API key' }}
        </v-btn>
      </div>

      <!-- Codex env var (bearer reads the key from GILJO_API_KEY) -->
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

      <!-- JSON paste hints -->
      <v-alert
        v-if="selectedTool === 'generic_mcp'"
        type="info"
        variant="tonal"
        density="compact"
        class="mb-3"
      >
        Add this to the <code>mcpServers</code> block of your MCP client's config file, then restart it.
      </v-alert>
      <v-alert
        v-else-if="selectedTool === 'antigravity'"
        type="info"
        variant="tonal"
        density="compact"
        class="mb-3"
      >
        Add the <code>giljo_mcp</code> entry to the <code>mcpServers</code> block in your
        <code>.antigravity/mcp.json</code> config file, then restart Antigravity CLI.
      </v-alert>

      <!-- Generated command / JSON -->
      <div class="code-block smooth-border" data-testid="configurator-artifact">
        <div class="code-block-header">
          <span class="code-block-lang">{{ commandLang }}</span>
          <v-btn
            class="code-copy-btn"
            size="x-small"
            variant="text"
            :prepend-icon="copied ? 'mdi-check' : 'mdi-content-copy'"
            data-testid="configurator-copy-btn"
            @click="copyCommand"
          >
            {{ copied ? 'Copied!' : 'Copy' }}
          </v-btn>
        </div>
        <pre class="config-code" data-testid="config-command">{{ command }}</pre>
      </div>
    </section>
  </main>
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
  isBackendHttps,
  makeKeyName,
  CERT_TRUST_WINDOWS,
  CERT_TRUST_UNIX,
} from '@/composables/useMcpConfig'

const props = defineProps({
  // 'web' | 'cli' | 'key' — which route's single artifact to render.
  route: { type: String, required: true },
  // Canonical legacy tool id (claude/codex/gemini/antigravity/generic_mcp).
  // Unused for the 'web' route (one URL works for every connector).
  selectedTool: { type: String, default: '' },
  // { id, vendor, name } — display metadata for the selected tool.
  selectedRow: { type: Object, default: () => ({ id: '', vendor: '', name: '' }) },
  isCe: { type: Boolean, default: false },
  backendConfig: { type: Object, default: null },
})

const { copy: clipboardCopy } = useClipboard()
const { showToast } = useToast()

const editingServer = ref(false)
const busy = ref(false)
const copied = ref(false)
const copiedUrl = ref(false)
const copiedWebUrl = ref(false)
const copiedEnv = ref(false)
const copiedCert = ref(false)
const errorMsg = ref('')
const selectedPlatform = ref('windows')
const certPlatform = ref('windows')
const generatedKey = ref('')

function detectServerInfo() {
  const hostname = window.location.hostname
  const port = window.location.port || '7272'
  return { hostname, port }
}
const serverIp = ref(detectServerInfo().hostname)
const serverPort = ref(detectServerInfo().port)

const certTrustCommandWindows = CERT_TRUST_WINDOWS
const certTrustCommandUnix = CERT_TRUST_UNIX

const isBrowserHttps = computed(() => window.location.protocol === 'https:')

function buildServerUrl() {
  // CE: include the explicit backend port (LAN/WAN/localhost connect direct).
  // SaaS/demo: reverse-proxied on 443, omit the port to match the public host.
  if (!props.isCe) {
    const protocol = window.location.protocol === 'https:' ? 'https' : 'http'
    return buildUrl({ host: serverIp.value, port: null, protocol })
  }
  return buildUrl(serverIp.value, serverPort.value)
}
const serverUrl = computed(() => buildServerUrl())
const serverUrlEndpoint = computed(() => `${serverUrl.value}/mcp`)

// Bearer commands embed the key inline; until generated, show a placeholder.
const keyForCmd = computed(() => (props.route === 'key' ? generatedKey.value || '<YOUR_API_KEY>' : ''))

const command = computed(() => {
  if (props.route === 'web') return ''
  const authMethod = props.route === 'cli' ? 'oauth' : 'bearer'
  const selfSigned = isBackendHttps(props.backendConfig)
  return generateConfigForTool(props.selectedTool, serverUrl.value, keyForCmd.value, { authMethod, selfSigned })
})

const commandLang = computed(() =>
  props.selectedTool === 'generic_mcp' || props.selectedTool === 'antigravity' ? 'json' : 'terminal',
)

const envVarCommand = computed(() => generateCodexEnvVar(generatedKey.value, selectedPlatform.value))

// CE self-signed HTTPS needs the Node CA-trust step for the Node-based CLIs.
// Only reachable from the API-key route now (CE hides Terminal/CLI), so this
// is surfaced here rather than stranded on a route CE never sees.
const showCertTrust = computed(
  () =>
    props.route === 'key' &&
    ['claude', 'codex', 'gemini'].includes(props.selectedTool) &&
    isBrowserHttps.value &&
    props.isCe &&
    isBackendHttps(props.backendConfig),
)

async function generateKey() {
  try {
    busy.value = true
    errorMsg.value = ''
    const keyName = makeKeyName(props.selectedTool)
    const resp = await api.apiKeys.create(keyName)
    generatedKey.value = resp.data.api_key
    try {
      window.dispatchEvent(new CustomEvent('api-key-created', { detail: { name: keyName } }))
    } catch {
      /* no-op */
    }
  } catch (e) {
    errorMsg.value = e?.response?.data?.message || e?.message || 'Failed to generate API key'
    console.error('[Wizard] Failed to generate API key', e)
  } finally {
    busy.value = false
  }
}

async function copyCommand() {
  const text = String(command.value || '').trim()
  if (!text) return
  const ok = await clipboardCopy(text)
  if (ok) {
    copied.value = true
    setTimeout(() => (copied.value = false), 3000)
    const message =
      props.route === 'cli'
        ? 'Command copied. Paste it in your terminal.'
        : 'MCP config copied. Paste it to wire your AI tool to GiljoAI.'
    showToast({ message, type: 'success' })
  } else {
    showToast({ message: 'Clipboard blocked. Select the command and press Ctrl+C to copy manually.', type: 'warning' })
  }
}

async function copyWebUrl() {
  const ok = await clipboardCopy(serverUrlEndpoint.value)
  if (ok) {
    copiedWebUrl.value = true
    setTimeout(() => (copiedWebUrl.value = false), 2000)
    showToast({ message: 'Server link copied. Paste it into your app.', type: 'success' })
  } else {
    showToast({ message: 'Clipboard blocked. Select and press Ctrl+C to copy manually.', type: 'warning' })
  }
}

async function copyUrl() {
  const ok = await clipboardCopy(serverUrlEndpoint.value)
  if (ok) {
    copiedUrl.value = true
    setTimeout(() => (copiedUrl.value = false), 2000)
  }
}

async function copyEnvVar() {
  const text = envVarCommand.value
  if (!text) return
  const ok = await clipboardCopy(text)
  if (ok) {
    copiedEnv.value = true
    setTimeout(() => (copiedEnv.value = false), 3000)
    showToast({ message: 'Env variable copied. Paste so Codex reads your API key.', type: 'success' })
  } else {
    showToast({ message: 'Clipboard blocked. Select the prompt and press Ctrl+C to copy manually.', type: 'warning' })
  }
}

async function copyCertCommand() {
  const text = certPlatform.value === 'windows' ? certTrustCommandWindows : certTrustCommandUnix
  const ok = await clipboardCopy(text)
  if (ok) {
    copiedCert.value = true
    setTimeout(() => (copiedCert.value = false), 3000)
    showToast({ message: 'Trust command copied. Paste it to trust this server\'s certificate on your machine.', type: 'success' })
  } else {
    showToast({ message: 'Clipboard blocked. Select the prompt and press Ctrl+C to copy manually.', type: 'warning' })
  }
}
</script>

<style lang="scss" scoped>
@use '../styles/design-tokens' as *;

/* ── Right pane shell ── */
.pane {
  --smooth-border-color: #{rgba(#fff, 0.1)};
  padding: 26px 28px;
  display: flex;
  flex-direction: column;
  background: transparent;
}

.pane-eyebrow {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.64rem;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}
.pane-eyebrow.route-web {
  color: $color-brand-yellow;
}
.pane-eyebrow.route-cli {
  color: $color-agent-implementor;
}
.pane-eyebrow.route-key {
  color: $color-agent-reviewer;
}

.pane-heading {
  font-family: 'Outfit', sans-serif;
  font-weight: 600;
  font-size: 1.24rem;
  margin: 10px 0 4px;
  letter-spacing: -0.01em;
  color: $color-text-primary;
}

.pane-lead {
  color: var(--text-secondary);
  font-size: 0.86rem;
  margin: 0 0 20px;
  max-width: 46ch;
}

/* ── Big copyable URL (Web & app route) ── */
.big-url {
  --smooth-border-color: #{rgba($color-brand-yellow, 0.32)};
  display: flex;
  align-items: stretch;
  border-radius: $border-radius-default;
  overflow: hidden;
  background: $color-background-primary;
  margin-bottom: 14px;
}
.big-url-text {
  flex: 1;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 1.05rem;
  font-weight: 500;
  color: $color-brand-yellow;
  padding: 16px 18px;
  display: flex;
  align-items: center;
  gap: 11px;
}
.big-url-icon {
  color: rgba($color-brand-yellow, 0.55);
}
.big-url-copy {
  border-radius: 0;
}

/* ── Numbered steps ── */
.pane-steps {
  margin: 4px 0 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.pane-steps li {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  font-size: 0.82rem;
  color: var(--text-secondary);
}
.step-num {
  flex: 0 0 22px;
  height: 22px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.68rem;
  font-weight: 600;
}
.step-num.route-web {
  background: rgba($color-brand-yellow, 0.16);
  color: $color-brand-yellow;
}
.step-num.route-cli {
  background: rgba($color-agent-implementor, 0.16);
  color: $color-agent-implementor;
}

/* ── Server URL row (API-key route) ── */
.server-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}
.server-label {
  font-size: 0.72rem;
  color: var(--text-muted);
  white-space: nowrap;
}
.server-url-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  border-radius: $border-radius-pill;
  background: rgba(0, 0, 0, 0.2);
  box-shadow: inset 0 0 0 1px rgba($color-brand-yellow, 0.18);
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.76rem;
  font-weight: 600;
  color: $color-brand-yellow;
}
.copied-hint {
  font-size: 0.72rem;
  color: $color-accent-success;
}

/* ── Bearer key-gen row ── */
.bearer-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
  padding: 10px 14px;
  border-radius: $border-radius-default;
  background: rgba($color-agent-implementor, 0.06);
  box-shadow: inset 0 0 0 1px rgba($color-agent-implementor, 0.14);
}
.bearer-icon {
  color: $color-agent-implementor;
  flex: 0 0 auto;
}
.bearer-row p {
  flex: 1;
  font-size: 0.78rem;
  color: var(--text-secondary);
  margin: 0;
}
.bearer-row p em {
  font-style: normal;
  color: var(--text-muted);
  font-size: 0.7rem;
}
.bearer-gen-btn {
  flex: 0 0 auto;
  color: $color-agent-implementor;
}

/* ── Code block (shared by Terminal/CLI + API key routes) ── */
.code-block {
  --smooth-border-color: #{rgba(#fff, 0.08)};
  position: relative;
  background: $color-background-primary;
  border-radius: $border-radius-default;
  overflow: hidden;
  margin-bottom: 12px;
}
.code-block-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 5px 10px 5px 14px;
  background: rgba(255, 255, 255, 0.04);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.code-block-lang {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.6rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-muted);
}
.code-copy-btn {
  color: var(--text-muted);
}
.config-code {
  padding: 14px 16px;
  margin: 0;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.8125rem;
  line-height: 1.55;
  color: $color-text-on-dark-surface;
  white-space: pre-wrap;
  word-break: break-all;
}

.font-monospace :deep(textarea) {
  font-family: 'IBM Plex Mono', monospace;
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
