<template>
  <v-container>
    <!-- Header with Setup Wizard Button -->
    <div class="d-flex justify-space-between align-center mb-6">
      <h1 class="text-h4">Settings</h1>
      <v-btn
        :color="setupCompleted ? 'primary' : 'success'"
        :variant="setupCompleted ? 'outlined' : 'flat'"
        @click="navigateToSetupWizard"
        aria-label="Open setup wizard"
      >
        <v-icon start>{{ setupCompleted ? 'mdi-cog-refresh' : 'mdi-rocket-launch' }}</v-icon>
        {{ setupCompleted ? 'Re-run Setup Wizard' : 'Setup Wizard' }}
      </v-btn>
    </div>

    <!-- Settings Tabs -->
    <v-tabs v-model="activeTab" class="mb-6">
      <v-tab value="general">
        <v-icon start>mdi-cog</v-icon>
        General
      </v-tab>
      <v-tab value="appearance">
        <v-icon start>mdi-palette</v-icon>
        Appearance
      </v-tab>
      <v-tab value="notifications">
        <v-icon start>mdi-bell</v-icon>
        Notifications
      </v-tab>
      <v-tab value="templates">
        <v-icon start>mdi-robot</v-icon>
        Agent Templates
      </v-tab>
      <v-tab value="api">
        <v-icon start>mdi-api</v-icon>
        API and Integrations
      </v-tab>
      <v-tab value="database">
        <v-icon start>mdi-database</v-icon>
        Database
      </v-tab>
      <v-tab value="network">
        <v-icon start>mdi-network-outline</v-icon>
        Network
      </v-tab>
    </v-tabs>

    <!-- Tab Content -->
    <v-window v-model="activeTab">
      <!-- General Settings -->
      <v-window-item value="general">
        <v-card>
          <v-card-title>General Settings</v-card-title>
          <v-card-text>
            <v-form ref="generalForm">
              <v-text-field
                v-model="settings.general.projectName"
                label="Project Name"
                variant="outlined"
                hint="The name of your orchestrator project"
                persistent-hint
              />

              <v-text-field
                v-model="settings.general.contextBudget"
                label="Context Budget (tokens)"
                type="number"
                variant="outlined"
                hint="Maximum context tokens per agent"
                persistent-hint
                class="mt-4"
              />

              <v-select
                v-model="settings.general.defaultPriority"
                :items="['low', 'normal', 'high', 'urgent', 'critical']"
                label="Default Message Priority"
                variant="outlined"
                class="mt-4"
              />

              <v-switch
                v-model="settings.general.autoRefresh"
                label="Auto-refresh data"
                color="primary"
                class="mt-4"
              />

              <v-slider
                v-if="settings.general.autoRefresh"
                v-model="settings.general.refreshInterval"
                :min="5"
                :max="60"
                :step="5"
                label="Refresh Interval (seconds)"
                thumb-label
                class="mt-4"
              />
            </v-form>
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn variant="text" @click="resetGeneralSettings">Reset</v-btn>
            <v-btn color="primary" variant="flat" @click="saveGeneralSettings">Save Changes</v-btn>
          </v-card-actions>
        </v-card>
      </v-window-item>

      <!-- Appearance Settings -->
      <v-window-item value="appearance">
        <v-card>
          <v-card-title>Appearance Settings</v-card-title>
          <v-card-text>
            <v-row>
              <v-col cols="12" md="6">
                <h3 class="text-h6 mb-4">Theme</h3>
                <v-radio-group v-model="settings.appearance.theme">
                  <v-radio label="Dark Theme" value="dark" />
                  <v-radio label="Light Theme" value="light" />
                  <v-radio label="System Default" value="system" />
                </v-radio-group>
              </v-col>

              <v-col cols="12" md="6">
                <h3 class="text-h6 mb-4">Mascot Preferences</h3>
                <v-switch
                  v-model="settings.appearance.showMascot"
                  label="Show mascot animations"
                  color="primary"
                />
                <v-switch
                  v-model="settings.appearance.useBlueVariant"
                  label="Use blue mascot variant"
                  color="primary"
                />
              </v-col>
            </v-row>

            <v-divider class="my-6" />

            <h3 class="text-h6 mb-4">Display Options</h3>
            <v-row>
              <v-col cols="12" md="6">
                <v-switch
                  v-model="settings.appearance.compactMode"
                  label="Compact mode"
                  color="primary"
                />
                <v-switch
                  v-model="settings.appearance.showAnimations"
                  label="Enable animations"
                  color="primary"
                />
              </v-col>
              <v-col cols="12" md="6">
                <v-switch
                  v-model="settings.appearance.showTooltips"
                  label="Show tooltips"
                  color="primary"
                />
                <v-switch
                  v-model="settings.appearance.highContrast"
                  label="High contrast mode"
                  color="primary"
                />
              </v-col>
            </v-row>
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn variant="text" @click="resetAppearanceSettings">Reset</v-btn>
            <v-btn color="primary" variant="flat" @click="saveAppearanceSettings"
              >Save Changes</v-btn
            >
          </v-card-actions>
        </v-card>
      </v-window-item>

      <!-- Notification Settings -->
      <v-window-item value="notifications">
        <v-card>
          <v-card-title>Notification Settings</v-card-title>
          <v-card-text>
            <h3 class="text-h6 mb-4">Message Notifications</h3>
            <v-switch
              v-model="settings.notifications.newMessages"
              label="New message alerts"
              color="primary"
            />
            <v-switch
              v-model="settings.notifications.urgentOnly"
              label="Urgent messages only"
              color="primary"
              :disabled="!settings.notifications.newMessages"
            />

            <v-divider class="my-6" />

            <h3 class="text-h6 mb-4">Agent Notifications</h3>
            <v-switch
              v-model="settings.notifications.agentStatus"
              label="Agent status changes"
              color="primary"
            />
            <v-switch
              v-model="settings.notifications.agentErrors"
              label="Agent errors"
              color="primary"
            />

            <v-divider class="my-6" />

            <h3 class="text-h6 mb-4">Task Notifications</h3>
            <v-switch
              v-model="settings.notifications.taskComplete"
              label="Task completions"
              color="primary"
            />
            <v-switch
              v-model="settings.notifications.taskOverdue"
              label="Overdue task alerts"
              color="primary"
            />

            <v-divider class="my-6" />

            <h3 class="text-h6 mb-4">Notification Display</h3>
            <v-select
              v-model="settings.notifications.position"
              :items="[
                'top-left',
                'top-center',
                'top-right',
                'bottom-left',
                'bottom-center',
                'bottom-right',
              ]"
              label="Notification position"
              variant="outlined"
            />
            <v-slider
              v-model="settings.notifications.duration"
              :min="2"
              :max="10"
              :step="1"
              label="Display duration (seconds)"
              thumb-label
              class="mt-4"
            />
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn variant="text" @click="resetNotificationSettings">Reset</v-btn>
            <v-btn color="primary" variant="flat" @click="saveNotificationSettings"
              >Save Changes</v-btn
            >
          </v-card-actions>
        </v-card>
      </v-window-item>

      <!-- Templates -->
      <v-window-item value="templates">
        <TemplateManager />
      </v-window-item>

      <!-- API Configuration -->
      <v-window-item value="api">
        <v-card>
          <v-card-title>API and Integrations</v-card-title>
          <v-card-subtitle>Configure API settings and MCP tool integrations</v-card-subtitle>
          <v-card-text>
            <v-alert type="info" variant="tonal" class="mb-4">
              Configure your API endpoints and authentication settings
            </v-alert>

            <v-text-field
              v-model="settings.api.baseUrl"
              label="API Base URL"
              variant="outlined"
              hint="e.g., http://localhost:7272"
              persistent-hint
            />

            <v-text-field
              v-model="settings.api.wsUrl"
              label="WebSocket URL"
              variant="outlined"
              hint="e.g., ws://localhost:7272/ws"
              persistent-hint
              class="mt-4"
            />

            <v-divider class="my-6" />

            <h3 class="text-h6 mb-4">MCP Integrations</h3>

            <v-card variant="outlined" class="mb-4">
              <v-list>
                <v-list-item>
                  <template v-slot:prepend>
                    <v-avatar size="40" rounded="0">
                      <v-img src="/Serena.png" alt="Serena MCP" />
                    </v-avatar>
                  </template>

                  <v-list-item-title class="text-h6 mb-1">Serena MCP</v-list-item-title>
                  <v-list-item-subtitle>
                    Enabling adds Serena tool instructions to agent prompts. Disabling removes them from
                    agent tool startup. (Currently only Claude Code)
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
                    />
                  </template>
                </v-list-item>
              </v-list>
            </v-card>

            <v-alert type="info" variant="tonal" class="mb-4">
              <v-icon start>mdi-information</v-icon>
              Serena MCP must be installed separately and configured in your coding tool (e.g., Claude
              Code). This toggle only controls whether Serena instructions are included in agent prompts.
            </v-alert>

            <v-divider class="my-6" />

            <h3 class="text-h6 mb-4">Authentication</h3>
            <v-text-field
              v-model="settings.api.apiKey"
              label="API Key"
              variant="outlined"
              type="password"
              hint="Your API authentication key"
              persistent-hint
            />

            <v-divider class="my-6" />

            <h3 class="text-h6 mb-4">Request Settings</h3>
            <v-text-field
              v-model="settings.api.timeout"
              label="Request Timeout (ms)"
              type="number"
              variant="outlined"
              hint="Maximum time to wait for API responses"
              persistent-hint
            />

            <v-text-field
              v-model="settings.api.retryAttempts"
              label="Retry Attempts"
              type="number"
              variant="outlined"
              hint="Number of retries for failed requests"
              persistent-hint
              class="mt-4"
            />
          </v-card-text>
          <v-card-actions>
            <v-btn variant="outlined" @click="testApiConnection">
              <v-icon start>mdi-connection</v-icon>
              Test Connection
            </v-btn>
            <v-spacer />
            <v-btn variant="text" @click="resetApiSettings">Reset</v-btn>
            <v-btn color="primary" variant="flat" @click="saveApiSettings">Save Changes</v-btn>
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
                  <v-chip :color="modeColor" size="small" class="ml-2">
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
              hint="127.0.0.1 = localhost only, 0.0.0.0 = network accessible"
              persistent-hint
              class="mb-4"
            />

            <v-text-field
              :model-value="networkSettings.apiPort"
              label="API Port"
              variant="outlined"
              readonly
              hint="Default: 7272"
              persistent-hint
              class="mb-4"
            />

            <!-- CORS Origins Management -->
            <v-divider class="my-6" />

            <h3 class="text-h6 mb-3">CORS Allowed Origins</h3>

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

            <!-- API Key Info (Readonly for now) -->
            <v-divider class="my-6" />

            <h3 class="text-h6 mb-3">API Key Information</h3>

            <v-alert v-if="currentMode === 'localhost'" type="info" variant="tonal">
              API key authentication is disabled in localhost mode
            </v-alert>

            <template v-else>
              <v-text-field
                v-if="apiKeyInfo"
                :model-value="maskedApiKey"
                label="Active API Key"
                variant="outlined"
                readonly
                hint="Key is masked for security"
                persistent-hint
                class="mb-2"
              />

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

            <!-- Mode Switching (Future Feature) -->
            <v-divider class="my-6" />

            <h3 class="text-h6 mb-3">Deployment Mode</h3>

            <v-alert type="warning" variant="tonal" class="mb-4">
              Changing deployment mode requires restarting services and may affect network
              accessibility.
            </v-alert>

            <v-select
              v-model="selectedMode"
              :items="availableModes"
              label="Deployment Mode"
              variant="outlined"
              hint="Select how this server should be accessed"
              persistent-hint
              disabled
            />

            <v-alert type="info" variant="tonal" class="mt-2">
              Mode switching will be available in a future update. Use the Setup Wizard to
              reconfigure.
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
            <v-btn
              color="primary"
              :disabled="!networkSettingsChanged"
              @click="saveNetworkSettings"
            >
              Save Changes
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-window-item>
    </v-window>
  </v-container>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useSettingsStore } from '@/stores/settings'
import { useTheme } from 'vuetify'
import TemplateManager from '@/components/TemplateManager.vue'
import DatabaseConnection from '@/components/DatabaseConnection.vue'
import { API_CONFIG } from '@/config/api'
import setupService from '@/services/setupService'

// Stores and Router
const settingsStore = useSettingsStore()
const theme = useTheme()
const router = useRouter()

// State
const activeTab = ref('general')
const generalForm = ref(null)
const setupCompleted = ref(false)
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
const selectedMode = ref('localhost')
const availableModes = ref([
  { title: 'Localhost (Single User)', value: 'localhost' },
  { title: 'LAN (Team Network)', value: 'lan' },
  { title: 'WAN (Internet) - Coming Soon', value: 'wan', disabled: true },
])
const networkSettingsChanged = ref(false)
const showRegenerateDialog = ref(false)

// Settings object
const settings = ref({
  general: {
    projectName: 'GiljoAI MCP Orchestrator',
    contextBudget: 150000,
    defaultPriority: 'normal',
    autoRefresh: true,
    refreshInterval: 10,
  },
  appearance: {
    theme: 'dark',
    showMascot: true,
    useBlueVariant: false,
    compactMode: false,
    showAnimations: true,
    showTooltips: true,
    highContrast: false,
  },
  notifications: {
    newMessages: true,
    urgentOnly: false,
    agentStatus: true,
    agentErrors: true,
    taskComplete: true,
    taskOverdue: true,
    position: 'bottom-right',
    duration: 5,
  },
  api: {
    baseUrl: 'http://localhost:7272',
    wsUrl: 'ws://localhost:7272/ws',
    apiKey: '',
    timeout: 30000,
    retryAttempts: 3,
  },
  database: {
    type: 'postgresql',
    host: 'localhost',
    port: 5432,
    name: 'giljo_mcp',
    user: 'postgres',
    password: '',
  },
})

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
    console.log('[SETTINGS] Serena prompt injection status:', serenaEnabled.value)
  } catch (error) {
    console.error('[SETTINGS] Failed to check Serena status:', error)
    serenaEnabled.value = false
  }
}

async function toggleSerena(enabled) {
  toggling.value = true
  try {
    const result = await setupService.toggleSerena(enabled)
    if (result.success) {
      serenaEnabled.value = result.enabled
      console.log('[SETTINGS] Serena prompt injection toggled:', result.enabled)
    } else {
      // Revert on failure
      serenaEnabled.value = !enabled
      console.error('[SETTINGS] Failed to toggle Serena:', result.message)
    }
  } catch (error) {
    console.error('[SETTINGS] Error toggling Serena:', error)
    // Revert on error
    serenaEnabled.value = !enabled
  } finally {
    toggling.value = false
  }
}

// Methods
async function saveGeneralSettings() {
  try {
    await settingsStore.updateSettings({ general: settings.value.general })
    console.log('General settings saved')
  } catch (error) {
    console.error('Failed to save general settings:', error)
  }
}

async function saveAppearanceSettings() {
  try {
    // Apply theme immediately
    if (settings.value.appearance.theme !== 'system') {
      theme.global.name.value = settings.value.appearance.theme
      document.documentElement.setAttribute('data-theme', settings.value.appearance.theme)
      localStorage.setItem('theme-preference', settings.value.appearance.theme)
    }

    await settingsStore.updateSettings({ appearance: settings.value.appearance })
    console.log('Appearance settings saved')
  } catch (error) {
    console.error('Failed to save appearance settings:', error)
  }
}

async function saveNotificationSettings() {
  try {
    await settingsStore.updateSettings({ notifications: settings.value.notifications })
    console.log('Notification settings saved')
  } catch (error) {
    console.error('Failed to save notification settings:', error)
  }
}

async function saveApiSettings() {
  try {
    await settingsStore.updateSettings({ api: settings.value.api })
    console.log('API settings saved')
  } catch (error) {
    console.error('Failed to save API settings:', error)
  }
}

async function saveDatabaseSettings() {
  try {
    await settingsStore.updateSettings({ database: settings.value.database })
    console.log('Database settings saved')
  } catch (error) {
    console.error('Failed to save database settings:', error)
  }
}

function resetGeneralSettings() {
  settings.value.general = {
    projectName: 'GiljoAI MCP Orchestrator',
    contextBudget: 150000,
    defaultPriority: 'normal',
    autoRefresh: true,
    refreshInterval: 10,
  }
}

function resetAppearanceSettings() {
  settings.value.appearance = {
    theme: 'dark',
    showMascot: true,
    useBlueVariant: false,
    compactMode: false,
    showAnimations: true,
    showTooltips: true,
    highContrast: false,
  }
}

function resetNotificationSettings() {
  settings.value.notifications = {
    newMessages: true,
    urgentOnly: false,
    agentStatus: true,
    agentErrors: true,
    taskComplete: true,
    taskOverdue: true,
    position: 'bottom-right',
    duration: 5,
  }
}

function resetApiSettings() {
  settings.value.api = {
    baseUrl: 'http://localhost:7272',
    wsUrl: 'ws://localhost:7272/ws',
    apiKey: '',
    timeout: 30000,
    retryAttempts: 3,
  }
}

async function loadDatabaseSettings() {
  try {
    // Fetch database config from API
    const response = await fetch(`${API_CONFIG.REST_API.baseURL}/api/v1/config/database`)
    const config = await response.json()

    settings.value.database = {
      type: 'postgresql',
      host: config.host || 'localhost',
      port: config.port || 5432,
      name: config.name || 'giljo_mcp',
      user: config.user || 'postgres',
      password: '********', // Always masked for security
    }

    console.log('Database settings reloaded from config')
  } catch (error) {
    console.error('Failed to load database settings:', error)
  }
}

async function testApiConnection() {
  console.log('Testing API connection...')
  // Implementation would test the API connection
}

// Database connection event handlers
function handleDatabaseSuccess(result) {
  console.log('Database connection successful:', result)
}

function handleDatabaseError(error) {
  console.error('Database connection failed:', error)
}

// Network Settings Methods
async function loadNetworkSettings() {
  try {
    // Load config from API
    const response = await fetch(`${API_CONFIG.REST_API.baseURL}/api/v1/config`)
    const config = await response.json()

    // Set mode
    currentMode.value = config.installation?.mode || 'localhost'
    selectedMode.value = currentMode.value

    // Set API settings
    networkSettings.value.apiHost = config.services?.api?.host || '127.0.0.1'
    networkSettings.value.apiPort = config.services?.api?.port || 7272

    // Set CORS origins
    corsOrigins.value = config.security?.cors?.allowed_origins || []

    // Load API key info for LAN mode
    if (currentMode.value === 'lan') {
      apiKeyInfo.value = {
        created_at: new Date().toISOString(),
        key_preview: 'gk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
      }
    }

    console.log('[SETTINGS] Network settings loaded')
  } catch (error) {
    console.error('Failed to load network settings:', error)
  }
}

function isDefaultOrigin(origin) {
  return origin.includes('localhost') || origin.includes('127.0.0.1')
}

function copyOrigin(origin) {
  navigator.clipboard.writeText(origin)
  console.log('[SETTINGS] Origin copied to clipboard:', origin)
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
      console.log('[SETTINGS] Origin added successfully')
    }
  } catch (error) {
    console.error('Invalid origin format:', error)
  }
}

function removeOrigin(index) {
  corsOrigins.value.splice(index, 1)
  networkSettingsChanged.value = true
  console.log('[SETTINGS] Origin removed')
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
      console.log('[SETTINGS] Network settings saved successfully')
    }
  } catch (error) {
    console.error('Failed to save network settings:', error)
  }
}

// Setup Wizard Navigation
const navigateToSetupWizard = () => {
  router.push('/setup')
}

const checkSetupStatus = async () => {
  try {
    const status = await setupService.checkStatus()
    setupCompleted.value = status.completed || false
    console.log('[SETTINGS] Setup status:', setupCompleted.value ? 'completed' : 'not completed')
  } catch (error) {
    console.error('[SETTINGS] Failed to check setup status:', error)
    // If check fails, assume not completed
    setupCompleted.value = false
  }
}

// Lifecycle
onMounted(async () => {
  // Check setup status
  await checkSetupStatus()

  // Check Serena MCP status
  await checkSerenaStatus()

  // Load database settings from config on mount
  await loadDatabaseSettings()

  // Load network settings from config on mount
  await loadNetworkSettings()

  // Load settings from store
  const storedSettings = await settingsStore.loadSettings()
  if (storedSettings) {
    Object.assign(settings.value, storedSettings)
  }
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
