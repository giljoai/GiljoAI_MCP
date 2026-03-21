<template>
  <v-card>
    <v-card-title>Network Configuration</v-card-title>
    <v-card-subtitle>Server network settings (configured during installation)</v-card-subtitle>

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

        <h3 class="text-h6 mb-3 text-medium-emphasis">CORS Allowed Origins</h3>

        <v-alert type="info" variant="tonal" class="mb-4">
          <strong>Foundation implementation exists.</strong> Reserved for future use when frontend
          and backend are hosted on separate domains (e.g., SaaS deployments). Not needed for
          current single-server installations where frontend and backend run together.
        </v-alert>

        <div data-test="cors-origins-section" class="disabled-section">
          <v-list v-if="corsOrigins.length > 0" density="compact" class="mb-4" disabled>
            <v-list-item v-for="(origin, index) in corsOrigins" :key="index" disabled>
              <v-list-item-title class="text-medium-emphasis">{{ origin }}</v-list-item-title>

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
            <span class="text-medium-emphasis"
              >No CORS origins configured. Foundation ready for future SaaS deployments.</span
            >
          </v-alert>

          <v-text-field
            v-model="newOrigin"
            label="Add New Origin"
            variant="outlined"
            placeholder="http://192.168.1.100:7274"
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
          <h3 class="text-h6 mb-3">HTTPS Encryption</h3>

          <v-alert
            :type="sslStatus.ssl_enabled ? 'success' : 'info'"
            variant="tonal"
            class="mb-4"
            data-test="https-status-alert"
          >
            <div class="d-flex align-center justify-space-between">
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
              <v-switch
                :model-value="sslStatus.ssl_enabled"
                :loading="sslToggling"
                :disabled="sslToggling"
                color="success"
                hide-details
                density="compact"
                data-test="ssl-toggle"
                @update:model-value="toggleSsl"
              />
            </div>
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

          <!-- Certificate info when SSL is enabled -->
          <div v-if="sslStatus.has_certificate" class="mb-3">
            <div class="text-caption text-medium-emphasis">
              <v-icon size="x-small" class="mr-1">mdi-certificate</v-icon>
              Certificate: <code>{{ sslStatus.cert_path }}</code>
            </div>
          </div>

          <!-- Self-signed certificate note -->
          <v-alert
            v-if="sslStatus.ssl_enabled"
            type="info"
            variant="outlined"
            density="compact"
            class="mb-4"
          >
            <div class="text-body-2">
              Self-signed certificates will show browser warnings. For production, use
              Let's Encrypt for trusted certificates.
              See <code>docs/security/HTTPS_SETUP.md</code> for details.
            </div>
          </v-alert>
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
