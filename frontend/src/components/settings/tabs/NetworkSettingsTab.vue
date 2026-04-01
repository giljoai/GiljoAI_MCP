<template>
  <v-card variant="flat" class="smooth-border network-card">
    <v-card-title>Network Configuration</v-card-title>
    <v-card-subtitle class="network-subtitle">Server network settings (configured during installation)</v-card-subtitle>

    <v-card-text>
      <!-- Loading State -->
      <div v-if="loading" class="d-flex justify-center py-8">
        <v-progress-circular indeterminate color="primary" />
      </div>

      <template v-else>
        <!-- Unified Architecture Info -->
        <v-alert
          type="info"
          variant="tonal"
          class="mb-4"
          data-test="v3-unified-alert"
          :icon="false"
        >
          <div class="d-flex align-center">
            <v-icon start>mdi-information</v-icon>
            <div>
              <strong>Unified Architecture:</strong> Server binds to all interfaces with
              authentication always enabled. OS firewall controls network access (defense in depth).
            </div>
          </div>
        </v-alert>

        <!-- Server Configuration -->
        <h3 class="text-h6 mb-3">Server Configuration from Installation</h3>

        <!-- Plugin Integration Reminder (Handover 0334) -->
        <v-alert
          type="warning"
          variant="tonal"
          class="mb-4"
          data-test="plugin-integration-reminder"
        >
          <div class="d-flex align-center">
            <v-icon start>mdi-puzzle-outline</v-icon>
            <div>
              <strong>Claude Code Plugin Integration:</strong> The External Host below is used by
              the Claude Code plugin to connect to this server. Ensure this IP/hostname is
              accessible from machines running Claude Code. See Handover 0334 for plugin setup.
            </div>
          </div>
        </v-alert>

        <v-text-field
          :model-value="config.externalHost"
          label="External Host"
          variant="outlined"
          readonly
          hint="Host/IP configured during installation for external access"
          persistent-hint
          class="mb-4"
          data-test="external-host-field"
        />

        <v-text-field
          :model-value="config.apiPort"
          label="API Port"
          variant="outlined"
          readonly
          hint="Default: 7272"
          persistent-hint
          class="mb-4"
          data-test="api-port-field"
        />

        <v-text-field
          :model-value="config.frontendPort"
          label="Frontend Port"
          variant="outlined"
          readonly
          hint="Default: 7274"
          persistent-hint
          class="mb-4"
          data-test="frontend-port-field"
        />

        <!-- CORS Origins Management -->
        <v-divider class="my-6" />

        <h3 class="text-h6 mb-3" style="color: var(--text-secondary);">CORS Allowed Origins</h3>

        <v-alert type="info" variant="tonal" class="mb-4">
          <strong>Foundation implementation exists.</strong> Reserved for future use when frontend
          and backend are hosted on separate domains (e.g., SaaS deployments). Not needed for
          current single-server installations where frontend and backend run together.
        </v-alert>

        <div data-test="cors-origins-section" class="disabled-section">
          <v-list v-if="corsOrigins.length > 0" density="compact" class="mb-4" disabled>
            <v-list-item v-for="(origin, index) in corsOrigins" :key="index" disabled>
              <v-list-item-title class="text-muted-a11y">{{ origin }}</v-list-item-title>

              <template v-slot:append>
                <v-btn
                  icon="mdi-content-copy"
                  size="small"
                  variant="text"
                  title="Copy Origin"
                  disabled
                  @click="copyOrigin(origin)"
                />
                <v-btn
                  v-if="!isDefaultOrigin(origin)"
                  icon="mdi-delete"
                  size="small"
                  variant="text"
                  color="error"
                  title="Remove Origin"
                  disabled
                  @click="removeOrigin(index)"
                />
              </template>
            </v-list-item>
          </v-list>

          <v-alert v-else type="info" variant="outlined" class="mb-4">
            <span class="text-muted-a11y"
              >No CORS origins configured. Foundation ready for future SaaS deployments.</span
            >
          </v-alert>

          <v-text-field
            v-model="newOrigin"
            label="Add New Origin"
            variant="outlined"
            placeholder="https://192.168.1.100:7274"
            hint="Disabled for single-server installations"
            persistent-hint
            :append-icon="'mdi-plus'"
            disabled
            @click:append="addOrigin"
            @keyup.enter="addOrigin"
          />
        </div>

        <!-- HTTPS Configuration -->
        <v-divider class="my-6" />

        <div data-test="https-status-section">
          <div class="d-flex align-center justify-space-between mb-3">
            <h3 class="text-h6">HTTPS Encryption</h3>
            <v-switch
              :model-value="sslStatus.ssl_enabled"
              :loading="sslToggling"
              :disabled="sslToggling"
              :label="sslStatus.ssl_enabled ? 'Enabled' : 'Disabled'"
              color="success"
              hide-details
              density="compact"
              data-test="ssl-toggle"
              @update:model-value="toggleSsl"
            />
          </div>

          <v-alert
            :type="sslStatus.ssl_enabled ? 'success' : 'info'"
            variant="tonal"
            class="mb-4"
            data-test="https-status-alert"
          >
            <div class="d-flex align-center">
              <v-icon start>{{ sslStatus.ssl_enabled ? 'mdi-lock' : 'mdi-lock-open-outline' }}</v-icon>
              <div>
                <strong>HTTPS:</strong>
                {{ sslStatus.ssl_enabled ? 'Enabled' : 'Disabled' }}
                <span v-if="sslStatus.has_certificate && !sslStatus.ssl_enabled" class="text-caption ml-1">
                  (certificate available)
                </span>
              </div>
            </div>
          </v-alert>

          <v-alert
            v-if="sslStatus.ssl_enabled"
            type="info"
            variant="tonal"
            density="compact"
            class="mb-4"
          >
            <strong>AI coding agent note:</strong> Some AI coding agents (e.g., Gemini CLI) may require additional
            certificate trust configuration when using self-signed HTTPS certificates. Regenerate your
            MCP configuration commands from the Configurator after enabling HTTPS.
          </v-alert>

          <!-- Restart required banner -->
          <v-alert
            v-if="sslRestartRequired"
            type="warning"
            variant="tonal"
            class="mb-4"
            data-test="ssl-restart-alert"
          >
            <div class="d-flex align-center">
              <v-icon start>mdi-restart</v-icon>
              <div>
                <strong>Server restart required</strong> for HTTPS changes to take effect.
              </div>
            </div>
          </v-alert>

          <!-- MCP re-attachment warning after protocol change -->
          <v-alert
            v-if="showMcpReattachWarning"
            type="warning"
            variant="tonal"
            class="mb-4"
            closable
            @click:close="showMcpReattachWarning = false"
          >
            <strong>Action required:</strong> Changing the protocol (HTTP/HTTPS) invalidates existing
            MCP tool connections. You must remove and re-add your AI coding agents:
            <ol class="mt-2 ml-4 text-body-2">
              <li>Remove existing connections: <code>claude mcp remove giljo_mcp</code>, <code>codex mcp remove giljo_mcp</code>, <code>gemini mcp remove giljo_mcp</code></li>
              <li>Delete old API keys from User Settings</li>
              <li>Use the Configurator to generate new connection commands</li>
            </ol>
          </v-alert>

          <!-- Error banner -->
          <v-alert
            v-if="sslError"
            type="error"
            variant="tonal"
            class="mb-4"
            closable
            data-test="ssl-error-alert"
            @click:close="sslError = ''"
          >
            {{ sslError }}
          </v-alert>

          <!-- Certificate info when certs exist -->
          <div v-if="sslStatus.has_certificate" class="mb-3">
            <div class="text-caption text-muted-a11y">
              <v-icon size="x-small" class="mr-1">mdi-certificate</v-icon>
              Certificate: <code>{{ sslStatus.cert_path }}</code>
            </div>
          </div>

          <!-- HTTPS setup guide (always available for post-install certificate setup) -->
          <div>
            <div
              class="d-flex align-center cursor-pointer mb-3"
              data-test="https-setup-toggle"
              @click="showHttpsGuide = !showHttpsGuide"
            >
              <v-icon start size="small">
                {{ showHttpsGuide ? 'mdi-chevron-down' : 'mdi-chevron-right' }}
              </v-icon>
              <span class="text-subtitle-2 text-muted-a11y">
                {{ sslStatus.ssl_enabled ? 'How to use trusted certificates (no browser warnings)' : 'How to set up trusted HTTPS certificates' }}
              </span>
            </div>

            <v-card v-if="showHttpsGuide" variant="flat" class="smooth-border mb-4 pa-4">
              <div class="text-body-2">
                <p class="mb-3">
                  To avoid browser "connection not private" warnings, you need
                  <strong>trusted certificates</strong>. Choose one option:
                </p>

                <v-expansion-panels variant="accordion">
                  <v-expansion-panel>
                    <v-expansion-panel-title>
                      <v-icon start color="success" size="small">mdi-star</v-icon>
                      <strong>Option 1: mkcert (Recommended for local/LAN)</strong>
                    </v-expansion-panel-title>
                    <v-expansion-panel-text>
                      <p class="mb-2">
                        mkcert creates a local Certificate Authority trusted by your browser.
                        No internet required, works offline.
                      </p>
                      <p class="mb-1"><strong>Install mkcert:</strong></p>
                      <div class="mb-2 pa-2 bg-grey-darken-4 rounded">
                        <code class="d-block">Windows: winget install FiloSottile.mkcert</code>
                        <code class="d-block">macOS: &nbsp; brew install mkcert</code>
                        <code class="d-block">Linux: &nbsp; sudo apt install mkcert</code>
                      </div>
                      <p class="mb-1"><strong>Generate trusted certificates:</strong></p>
                      <div class="mb-2 pa-2 bg-grey-darken-4 rounded">
                        <code class="d-block">mkcert -install</code>
                        <code class="d-block">mkcert -cert-file certs/ssl_cert.pem -key-file certs/ssl_key.pem localhost 127.0.0.1 ::1</code>
                      </div>
                      <p class="mb-0">Then flip the HTTPS toggle above and restart the server.</p>
                    </v-expansion-panel-text>
                  </v-expansion-panel>

                  <v-expansion-panel>
                    <v-expansion-panel-title>
                      <v-icon start color="info" size="small">mdi-web</v-icon>
                      <strong>Option 2: Let's Encrypt (Public-facing servers)</strong>
                    </v-expansion-panel-title>
                    <v-expansion-panel-text>
                      <p class="mb-2">
                        Free, globally trusted certificates. Requires a public domain name
                        and port 80/443 accessible from the internet.
                      </p>
                      <div class="mb-2 pa-2 bg-grey-darken-4 rounded">
                        <code class="d-block">sudo apt install certbot</code>
                        <code class="d-block">sudo certbot certonly --standalone -d yourdomain.com</code>
                      </div>
                      <p class="mb-0">
                        Copy the generated cert and key to <code>certs/</code>,
                        update <code>config.yaml</code> paths, then flip the toggle above.
                      </p>
                    </v-expansion-panel-text>
                  </v-expansion-panel>

                  <v-expansion-panel>
                    <v-expansion-panel-title>
                      <v-icon start color="warning" size="small">mdi-alert-outline</v-icon>
                      <strong>Option 3: Self-signed (Quick, but shows browser warning)</strong>
                    </v-expansion-panel-title>
                    <v-expansion-panel-text>
                      <p class="mb-2">
                        Generates a certificate immediately but browsers will show a
                        "connection not private" warning. You'll need to click
                        "Advanced" → "Proceed" each time.
                      </p>
                      <p class="mb-0">
                        Just flip the HTTPS toggle above — a self-signed certificate
                        will be generated automatically if none exists.
                      </p>
                    </v-expansion-panel-text>
                  </v-expansion-panel>
                </v-expansion-panels>
              </div>
            </v-card>
          </div>

        </div>

        <!-- Network Configuration Info -->
        <v-divider class="my-6" />

        <h3 class="text-h6 mb-3">Configuration Notes</h3>

        <v-alert type="info" variant="tonal" class="mb-0">
          <div class="mb-2">
            <strong>Network settings are configured during installation.</strong>
          </div>
          <div class="text-body-2">
            To modify the external host or ports, update <code>config.yaml</code> and restart the
            server. Authentication is always enabled for all connections (local and remote). Use OS
            firewall to control network access.
          </div>
        </v-alert>
      </template>
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn variant="text" data-test="reload-button" @click="handleRefresh">
        <v-icon start>mdi-refresh</v-icon>
        Reload
      </v-btn>
      <v-btn color="primary" disabled data-test="save-button"> Save Changes </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getApiBaseURL } from '@/config/api'
import { useClipboard } from '@/composables/useClipboard'

const { copy: clipboardCopy } = useClipboard()

const props = defineProps({
  config: {
    type: Object,
    required: true,
    default: () => ({
      externalHost: 'localhost',
      apiPort: 7272,
      frontendPort: 7274,
    }),
  },
  corsOrigins: {
    type: Array,
    default: () => [],
  },
  sslEnabled: {
    type: Boolean,
    default: false,
  },
  loading: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['refresh', 'save'])

// Local state for CORS management (disabled for now)
const newOrigin = ref('')

// SSL state
const sslStatus = ref({
  ssl_enabled: false,
  has_certificate: false,
  cert_path: null,
  key_path: null,
})
const sslToggling = ref(false)
const sslRestartRequired = ref(false)
const sslError = ref('')
const showMcpReattachWarning = ref(false)
const showHttpsGuide = ref(false)

// Methods
function handleRefresh() {
  emit('refresh')
  loadSslStatus()
}

function isDefaultOrigin(origin) {
  return origin.includes('localhost') || origin.includes('127.0.0.1')
}

function copyOrigin(origin) {
  clipboardCopy(origin)
}

function addOrigin() {
  if (!newOrigin.value) return

  // Validate origin format
  try {
    new URL(newOrigin.value)
    // Would emit save event with updated origins
    // For now this is disabled
    newOrigin.value = ''
  } catch (error) {
    console.error('Invalid origin format:', error)
  }
}

function removeOrigin() {
  // Would emit save event with updated origins
  // For now this is disabled
}

async function loadSslStatus() {
  try {
    const csrfToken = document.cookie.match(/csrf_token=([^;]+)/)?.[1]
    const response = await fetch(`${getApiBaseURL()}/api/v1/config/ssl`, {
      credentials: 'include',
      headers: {
        ...(csrfToken && { 'X-CSRF-Token': csrfToken }),
      },
    })
    if (response.ok) {
      sslStatus.value = await response.json()
    }
  } catch (error) {
    console.error('[NETWORK] Failed to load SSL status:', error)
    // Fall back to prop value
    sslStatus.value.ssl_enabled = props.sslEnabled
  }
}

async function toggleSsl(enabled) {
  sslToggling.value = true
  sslError.value = ''
  sslRestartRequired.value = false

  try {
    const csrfToken = document.cookie.match(/csrf_token=([^;]+)/)?.[1]
    const response = await fetch(`${getApiBaseURL()}/api/v1/config/ssl`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...(csrfToken && { 'X-CSRF-Token': csrfToken }),
      },
      body: JSON.stringify({ enabled }),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to toggle SSL')
    }

    const result = await response.json()
    sslStatus.value = result
    sslRestartRequired.value = result.restart_required
    showMcpReattachWarning.value = true
  } catch (error) {
    sslError.value = error.message || 'Failed to toggle SSL'
    console.error('[NETWORK] SSL toggle failed:', error)
  } finally {
    sslToggling.value = false
  }
}

onMounted(() => {
  loadSslStatus()
})
</script>

<style lang="scss" scoped>
@use '../../../styles/design-tokens' as *;
.network-card {
  background: var(--bg-raised, #1e3147);
  border-radius: $border-radius-rounded;
}

.network-subtitle {
  color: var(--text-muted);
}
</style>
