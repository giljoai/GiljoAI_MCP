<template>
  <v-container>
    <!-- Page Header -->
    <h1 class="text-h4 mb-2">System Settings</h1>
    <p class="text-subtitle-1 mb-4">Configure server and system-wide settings (Admin only)</p>

    <!-- Settings Tabs -->
    <v-tabs v-model="activeTab" class="mb-6">
      <v-tab value="network">
        <v-icon start>mdi-network-outline</v-icon>
        Network
      </v-tab>
      <v-tab value="database">
        <v-icon start>mdi-database</v-icon>
        Database
      </v-tab>
      <v-tab value="integrations">
        <v-icon start>mdi-api</v-icon>
        Integrations
      </v-tab>
      <v-tab value="users">
        <v-icon start>mdi-account-multiple</v-icon>
        Users
      </v-tab>
    </v-tabs>

    <!-- Tab Content -->
    <v-window v-model="activeTab">
      <!-- Network Settings -->
      <v-window-item value="network">
        <v-card>
          <v-card-title>Network Configuration</v-card-title>
          <v-card-subtitle>Manage deployment mode and network access</v-card-subtitle>

          <v-card-text>
            <!-- Current Mode Display -->
            <v-alert type="info" variant="tonal" class="mb-4">
              <div class="d-flex align-center">
                <v-icon start>mdi-information</v-icon>
                <div>
                  <strong>Current Mode:</strong>
                  <v-chip :color="modeColor" size="small" class="ml-2" data-test="mode-chip">
                    {{ currentMode.toUpperCase() }}
                  </v-chip>
                </div>
              </div>
            </v-alert>

            <!-- API Binding Info -->
            <h3 class="text-h6 mb-3">API Server Configuration</h3>

            <v-text-field
              :model-value="networkSettings.apiHost"
              label="API Host Binding"
              variant="outlined"
              readonly
              hint="127.0.0.1 = localhost only, specific IP = network accessible"
              persistent-hint
              class="mb-4"
              data-test="api-host-field"
            />

            <v-text-field
              :model-value="networkSettings.apiPort"
              label="API Port"
              variant="outlined"
              readonly
              hint="Default: 7272"
              persistent-hint
              class="mb-4"
              data-test="api-port-field"
            />

            <!-- CORS Origins Management -->
            <v-divider class="my-6" />

            <h3 class="text-h6 mb-3">CORS Allowed Origins</h3>

            <div data-test="cors-origins-section">
              <v-list density="compact" class="mb-4">
                <v-list-item v-for="(origin, index) in corsOrigins" :key="index">
                  <v-list-item-title>{{ origin }}</v-list-item-title>

                  <template v-slot:append>
                    <v-btn
                      icon="mdi-content-copy"
                      size="small"
                      variant="text"
                      @click="copyOrigin(origin)"
                    />
                    <v-btn
                      v-if="!isDefaultOrigin(origin)"
                      icon="mdi-delete"
                      size="small"
                      variant="text"
                      color="error"
                      @click="removeOrigin(index)"
                    />
                  </template>
                </v-list-item>
              </v-list>

              <v-text-field
                v-model="newOrigin"
                label="Add New Origin"
                variant="outlined"
                placeholder="http://192.168.1.100:7274"
                hint="Format: http://hostname:port or http://ip:port"
                persistent-hint
                :append-icon="'mdi-plus'"
                @click:append="addOrigin"
                @keyup.enter="addOrigin"
              />
            </div>

            <!-- API Key Info (Readonly for now) -->
            <v-divider class="my-6" />

            <h3 class="text-h6 mb-3">API Key Information</h3>

            <v-alert v-if="currentMode === 'localhost'" type="info" variant="tonal">
              <div class="d-flex align-center">
                <v-icon start>mdi-lock-open</v-icon>
                <div>API key authentication is disabled in localhost mode</div>
              </div>
            </v-alert>

            <template v-else-if="currentMode === 'lan'">
              <v-alert type="success" variant="tonal" class="mb-4">
                <div class="d-flex align-center">
                  <v-icon start>mdi-shield-check</v-icon>
                  <div>LAN mode requires API key authentication for secure network access</div>
                </div>
              </v-alert>

              <v-text-field
                v-if="apiKeyInfo"
                :model-value="maskedApiKey"
                label="Active API Key"
                variant="outlined"
                readonly
                hint="Key is masked for security. Clients must use this key to authenticate."
                persistent-hint
                class="mb-2"
                data-test="api-key-field"
              >
                <template v-slot:append>
                  <v-btn
                    icon="mdi-content-copy"
                    size="small"
                    variant="text"
                    @click="copyApiKey"
                    title="Copy API Key"
                  />
                </template>
              </v-text-field>

              <v-text-field
                v-if="apiKeyInfo"
                :model-value="apiKeyInfo.created_at"
                label="Created At"
                variant="outlined"
                readonly
                class="mb-4"
              />

              <v-btn variant="outlined" color="warning" @click="showRegenerateDialog = true">
                <v-icon start>mdi-refresh</v-icon>
                Regenerate API Key
              </v-btn>
            </template>

            <!-- Deployment Mode Change via Setup Wizard -->
            <v-divider class="my-6" />

            <h3 class="text-h6 mb-3">Change Deployment Mode</h3>

            <v-alert type="info" variant="tonal" class="mb-4">
              To change deployment mode (localhost ↔ LAN), use the Setup Wizard below. This ensures
              all network settings, API keys, and configurations are properly updated.
            </v-alert>
          </v-card-text>

          <v-card-actions>
            <v-btn variant="outlined" @click="navigateToSetupWizard">
              <v-icon start>mdi-wizard-hat</v-icon>
              Re-run Setup Wizard
            </v-btn>
            <v-spacer />
            <v-btn variant="text" @click="loadNetworkSettings">
              <v-icon start>mdi-refresh</v-icon>
              Reload
            </v-btn>
            <v-btn color="primary" :disabled="!networkSettingsChanged" @click="saveNetworkSettings">
              Save Changes
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-window-item>

      <!-- Database Settings -->
      <v-window-item value="database">
        <DatabaseConnection
          :readonly="true"
          :show-title="true"
          title="PostgreSQL Database Configuration"
          :show-info-banner="true"
          info-banner-text="Database settings are configured during installation"
          :show-test-button="true"
          test-button-text="Test Connection"
          @connection-success="handleDatabaseSuccess"
          @connection-error="handleDatabaseError"
        >
          <template #actions>
            <v-btn variant="text" @click="loadDatabaseSettings">
              <v-icon start>mdi-refresh</v-icon>
              Reload from Config
            </v-btn>
          </template>
        </DatabaseConnection>
      </v-window-item>

      <!-- Integrations -->
      <v-window-item value="integrations">
        <v-card>
          <v-card-title>MCP Integrations</v-card-title>
          <v-card-subtitle>Configure external tool integrations</v-card-subtitle>

          <v-card-text>
            <h3 class="text-h6 mb-4">Available Integrations</h3>

            <v-card variant="outlined" class="mb-4" data-test="serena-integration">
              <v-list>
                <v-list-item>
                  <template v-slot:prepend>
                    <v-avatar size="40" rounded="0">
                      <v-img src="/Serena.png" alt="Serena MCP" />
                    </v-avatar>
                  </template>

                  <v-list-item-title class="text-h6 mb-1">Serena MCP</v-list-item-title>
                  <v-list-item-subtitle>
                    Enabling adds Serena tool instructions to agent prompts. Disabling removes them
                    from agent tool startup. (Currently only Claude Code)
                  </v-list-item-subtitle>

                  <template v-slot:append>
                    <v-switch
                      v-model="serenaEnabled"
                      @update:model-value="toggleSerena"
                      color="primary"
                      :loading="toggling"
                      hide-details
                      inset
                      class="serena-toggle"
                      data-test="serena-toggle"
                    />
                  </template>
                </v-list-item>
              </v-list>
            </v-card>

            <v-alert type="info" variant="tonal" class="mb-4">
              <v-icon start>mdi-information</v-icon>
              Serena MCP must be installed separately and configured in your coding tool (e.g.,
              Claude Code). This toggle only controls whether Serena instructions are included in
              agent prompts.
            </v-alert>
          </v-card-text>
        </v-card>
      </v-window-item>

      <!-- Users Placeholder (Phase 5) -->
      <v-window-item value="users">
        <v-card>
          <v-card-title>User Management</v-card-title>
          <v-card-text>
            <v-alert type="info" variant="tonal" data-test="users-placeholder">
              <v-icon start>mdi-information</v-icon>
              User management coming in Phase 5
            </v-alert>
          </v-card-text>
        </v-card>
      </v-window-item>
    </v-window>

    <!-- Regenerate API Key Dialog -->
    <v-dialog v-model="showRegenerateDialog" max-width="500">
      <v-card>
        <v-card-title>Regenerate API Key</v-card-title>
        <v-card-text>
          <v-alert type="warning" variant="tonal" class="mb-4">
            <v-icon start>mdi-alert</v-icon>
            This will invalidate the current API key. All clients will need to update their configuration with the new key.
          </v-alert>
          Are you sure you want to regenerate the API key?
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showRegenerateDialog = false">Cancel</v-btn>
          <v-btn color="warning" variant="flat" @click="regenerateApiKey">Regenerate</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import DatabaseConnection from '@/components/DatabaseConnection.vue'
import { API_CONFIG } from '@/config/api'
import setupService from '@/services/setupService'

// Router
const router = useRouter()

// State
const activeTab = ref('network')
const serenaEnabled = ref(false)
const toggling = ref(false)

// Network settings state
const networkSettings = ref({
  apiHost: '127.0.0.1',
  apiPort: 7272,
})
const currentMode = ref('localhost')
const corsOrigins = ref([])
const newOrigin = ref('')
const apiKeyInfo = ref(null)
const networkSettingsChanged = ref(false)
const showRegenerateDialog = ref(false)

// Computed Properties
const modeColor = computed(() => {
  const colors = {
    localhost: 'success',
    lan: 'info',
    wan: 'warning',
  }
  return colors[currentMode.value] || 'grey'
})

const maskedApiKey = computed(() => {
  if (!apiKeyInfo.value || !apiKeyInfo.value.key_preview) {
    return 'No API key configured'
  }
  const preview = apiKeyInfo.value.key_preview
  return `${preview.substring(0, 8)}...${preview.substring(preview.length - 4)}`
})

// Serena MCP Methods
async function checkSerenaStatus() {
  try {
    const status = await setupService.getSerenaStatus()
    serenaEnabled.value = status.enabled || false
    console.log('[SYSTEM SETTINGS] Serena prompt injection status:', serenaEnabled.value)
  } catch (error) {
    console.error('[SYSTEM SETTINGS] Failed to check Serena status:', error)
    serenaEnabled.value = false
  }
}

async function toggleSerena(enabled) {
  toggling.value = true
  try {
    const result = await setupService.toggleSerena(enabled)
    if (result.success) {
      serenaEnabled.value = result.enabled
      console.log('[SYSTEM SETTINGS] Serena prompt injection toggled:', result.enabled)
    } else {
      // Revert on failure
      serenaEnabled.value = !enabled
      console.error('[SYSTEM SETTINGS] Failed to toggle Serena:', result.message)
    }
  } catch (error) {
    console.error('[SYSTEM SETTINGS] Error toggling Serena:', error)
    // Revert on error
    serenaEnabled.value = !enabled
  } finally {
    toggling.value = false
  }
}

// Network Settings Methods
async function loadNetworkSettings() {
  try {
    let config
    try {
      // First, try loading from /api/v1/config
      const response = await fetch(`${API_CONFIG.REST_API.baseURL}/api/v1/config`, {
        timeout: 5000,
      })

      if (!response.ok) {
        throw new Error('Config endpoint failed')
      }

      config = await response.json()
    } catch (configError) {
      console.warn(
        '[SYSTEM SETTINGS] Failed to load config from /api/v1/config, falling back to /api/setup/status',
      )

      // Fallback to /api/setup/status
      const fallbackResponse = await fetch(`${API_CONFIG.REST_API.baseURL}/api/setup/status`)

      if (!fallbackResponse.ok) {
        throw fallbackResponse.statusText
      }

      const fallbackConfig = await fallbackResponse.json()

      // Map the fallback response to the expected config structure
      config = {
        installation: { mode: fallbackConfig.network_mode || 'localhost' },
        services: {
          api: {
            host: fallbackConfig.host || '127.0.0.1',
            port: fallbackConfig.port || 7272,
          },
        },
        security: {
          cors: {
            allowed_origins: fallbackConfig.allowed_origins || [],
          },
        },
      }
    }

    // Set mode with robust fallback
    currentMode.value = config.installation?.mode?.toLowerCase() || 'localhost'

    // Set API settings
    networkSettings.value.apiHost = config.services?.api?.host || '127.0.0.1'
    networkSettings.value.apiPort = config.services?.api?.port || 7272

    // Set CORS origins
    corsOrigins.value = config.security?.cors?.allowed_origins || []

    // Load API key info for LAN mode
    if (currentMode.value === 'lan') {
      try {
        const apiKeyResponse = await fetch(`${API_CONFIG.REST_API.baseURL}/api/setup/api-key-info`)
        const apiKeyData = await apiKeyResponse.json()

        apiKeyInfo.value = {
          created_at: apiKeyData.created_at || new Date().toISOString(),
          key_preview: apiKeyData.key_preview || 'gk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
        }
      } catch (apiKeyError) {
        console.warn('[SYSTEM SETTINGS] Failed to load API key info', apiKeyError)
        apiKeyInfo.value = null
      }
    }

    console.log('[SYSTEM SETTINGS] Network settings loaded successfully')
  } catch (error) {
    console.error('Completely failed to load network settings:', error)

    // Absolute last resort fallback
    currentMode.value = 'localhost'
    networkSettings.value.apiHost = '127.0.0.1'
    networkSettings.value.apiPort = 7272
    corsOrigins.value = []
  }
}

function isDefaultOrigin(origin) {
  return origin.includes('localhost') || origin.includes('127.0.0.1')
}

function copyOrigin(origin) {
  navigator.clipboard.writeText(origin)
  console.log('[SYSTEM SETTINGS] Origin copied to clipboard:', origin)
}

function copyApiKey() {
  if (apiKeyInfo.value && apiKeyInfo.value.key_preview) {
    navigator.clipboard.writeText(apiKeyInfo.value.key_preview)
    console.log('[SYSTEM SETTINGS] API key copied to clipboard')
  }
}

function addOrigin() {
  if (!newOrigin.value) return

  // Validate origin format
  try {
    new URL(newOrigin.value)
    if (!corsOrigins.value.includes(newOrigin.value)) {
      corsOrigins.value.push(newOrigin.value)
      newOrigin.value = ''
      networkSettingsChanged.value = true
      console.log('[SYSTEM SETTINGS] Origin added successfully')
    }
  } catch (error) {
    console.error('Invalid origin format:', error)
  }
}

function removeOrigin(index) {
  corsOrigins.value.splice(index, 1)
  networkSettingsChanged.value = true
  console.log('[SYSTEM SETTINGS] Origin removed')
}

async function saveNetworkSettings() {
  try {
    // Save CORS origins back to config
    const response = await fetch(`${API_CONFIG.REST_API.baseURL}/api/v1/config`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        security: {
          cors: {
            allowed_origins: corsOrigins.value,
          },
        },
      }),
    })

    if (response.ok) {
      networkSettingsChanged.value = false
      console.log('[SYSTEM SETTINGS] Network settings saved successfully')
    }
  } catch (error) {
    console.error('Failed to save network settings:', error)
  }
}

async function regenerateApiKey() {
  try {
    const response = await fetch(`${API_CONFIG.REST_API.baseURL}/api/setup/regenerate-api-key`, {
      method: 'POST',
    })

    if (response.ok) {
      showRegenerateDialog.value = false
      await loadNetworkSettings() // Reload to get new key
      console.log('[SYSTEM SETTINGS] API key regenerated successfully')
    }
  } catch (error) {
    console.error('Failed to regenerate API key:', error)
  }
}

// Database Methods
async function loadDatabaseSettings() {
  try {
    // Fetch database config from API
    const response = await fetch(`${API_CONFIG.REST_API.baseURL}/api/v1/config/database`)
    const config = await response.json()

    console.log('Database settings reloaded from config')
  } catch (error) {
    console.error('Failed to load database settings:', error)
  }
}

function handleDatabaseSuccess(result) {
  console.log('Database connection successful:', result)
}

function handleDatabaseError(error) {
  console.error('Database connection failed:', error)
}

// Setup Wizard Navigation
const navigateToSetupWizard = () => {
  router.push('/setup')
}

// Lifecycle
onMounted(async () => {
  // Check Serena MCP status
  await checkSerenaStatus()

  // Load database settings from config on mount
  await loadDatabaseSettings()

  // Load network settings from config on mount
  await loadNetworkSettings()
})
</script>

<style scoped>
/* Make Serena toggle more visible */
.serena-toggle :deep(.v-switch__track) {
  border: 2px solid rgba(var(--v-theme-primary), 0.5);
}

.serena-toggle :deep(.v-switch__thumb) {
  border: 2px solid rgba(var(--v-theme-primary), 0.8);
}
</style>
