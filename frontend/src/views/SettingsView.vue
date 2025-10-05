<template>
  <v-container>
    <h1 class="text-h4 mb-6">Settings</h1>

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
        API Configuration
      </v-tab>
      <v-tab value="database">
        <v-icon start>mdi-database</v-icon>
        Database
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
          <v-card-title>API Configuration</v-card-title>
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
        <v-card>
          <v-card-title>PostgreSQL Database Configuration</v-card-title>
          <v-card-text>
            <v-alert type="info" variant="tonal" class="mb-4">
              GiljoAI MCP requires PostgreSQL 18. Settings are auto-detected from config.yaml.
            </v-alert>

            <v-row>
              <v-col cols="12" md="6">
                <v-text-field
                  v-model="settings.database.host"
                  label="Host"
                  variant="outlined"
                  hint="Auto-detected from config"
                  persistent-hint
                  readonly
                >
                  <template v-slot:append>
                    <v-btn
                      icon="mdi-refresh"
                      size="small"
                      variant="text"
                      @click="loadDatabaseSettings"
                      title="Reload from config"
                    />
                  </template>
                </v-text-field>
              </v-col>

              <v-col cols="12" md="6">
                <v-text-field
                  v-model="settings.database.port"
                  label="Port"
                  type="number"
                  variant="outlined"
                  hint="Default: 5432"
                  persistent-hint
                >
                  <template v-slot:append>
                    <v-btn
                      icon="mdi-check-circle"
                      size="small"
                      variant="text"
                      @click="validatePort"
                      title="Validate port"
                      :loading="validatingPort"
                    />
                  </template>
                </v-text-field>
              </v-col>

              <v-col cols="12" md="6">
                <v-text-field
                  v-model="settings.database.name"
                  label="Database Name"
                  variant="outlined"
                  hint="Auto-detected from config"
                  persistent-hint
                  readonly
                />
              </v-col>

              <v-col cols="12" md="6">
                <v-text-field
                  v-model="settings.database.user"
                  label="Username"
                  variant="outlined"
                  hint="Database user"
                  persistent-hint
                  readonly
                />
              </v-col>

              <v-col cols="12" md="6">
                <v-text-field
                  v-model="settings.database.password"
                  label="Password"
                  :type="showPassword ? 'text' : 'password'"
                  variant="outlined"
                  hint="Min 12 chars: uppercase, lowercase, number, special char (@$!%*?&)"
                  persistent-hint
                  @input="passwordChanged = true"
                  :rules="passwordChanged ? passwordRules : []"
                >
                  <template v-slot:append>
                    <v-btn
                      :icon="showPassword ? 'mdi-eye-off' : 'mdi-eye'"
                      size="small"
                      variant="text"
                      @click="showPassword = !showPassword"
                      title="Toggle password visibility"
                    />
                  </template>
                </v-text-field>
                <v-progress-linear
                  v-if="passwordChanged && settings.database.password"
                  :model-value="passwordStrength.score"
                  :color="passwordStrength.color"
                  height="4"
                  class="mt-1"
                />
                <div v-if="passwordChanged && settings.database.password" class="text-caption mt-1" :style="{ color: passwordStrength.color }">
                  Password Strength: {{ passwordStrength.label }}
                </div>
              </v-col>

              <v-col cols="12" md="6" v-if="passwordChanged">
                <v-btn
                  color="warning"
                  variant="outlined"
                  @click="updateDatabasePassword"
                  :loading="updatingPassword"
                >
                  <v-icon start>mdi-lock-reset</v-icon>
                  Update Password in Config
                </v-btn>
              </v-col>
            </v-row>

            <v-divider class="my-6" />

            <v-alert
              v-if="connectionTestResult"
              :type="connectionTestResult.success ? 'success' : 'error'"
              variant="tonal"
              class="mb-4"
            >
              {{ connectionTestResult.message }}
            </v-alert>
          </v-card-text>
          <v-card-actions>
            <v-btn
              variant="outlined"
              @click="testDatabaseConnection"
              :loading="testingConnection"
            >
              <v-icon start>mdi-database-check</v-icon>
              Test Connection
            </v-btn>
            <v-spacer />
            <v-btn variant="text" @click="loadDatabaseSettings">
              <v-icon start>mdi-refresh</v-icon>
              Reload from Config
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-window-item>
    </v-window>
  </v-container>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useSettingsStore } from '@/stores/settings'
import { useTheme } from 'vuetify'
import TemplateManager from '@/components/TemplateManager.vue'
import { API_CONFIG } from '@/config/api'

// Stores
const settingsStore = useSettingsStore()
const theme = useTheme()

// State
const activeTab = ref('general')
const generalForm = ref(null)
const testingConnection = ref(false)
const validatingPort = ref(false)
const connectionTestResult = ref(null)
const showPassword = ref(false)
const passwordChanged = ref(false)
const updatingPassword = ref(false)

// Password validation rules
const passwordRules = [
  (v) => !!v || 'Password is required',
  (v) => v.length >= 12 || 'Minimum 12 characters required',
  (v) => /[A-Z]/.test(v) || 'Must contain uppercase letter',
  (v) => /[a-z]/.test(v) || 'Must contain lowercase letter',
  (v) => /\d/.test(v) || 'Must contain number',
  (v) => /[@$!%*?&]/.test(v) || 'Must contain special character (@$!%*?&)',
]

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
      password: config.password_masked || '****', // Masked password from backend
    }

    passwordChanged.value = false
    showPassword.value = false
    connectionTestResult.value = { success: true, message: 'Settings loaded from config' }
  } catch (error) {
    console.error('Failed to load database settings:', error)
    connectionTestResult.value = { success: false, message: 'Failed to load settings from config' }
  }
}

async function updateDatabasePassword() {
  updatingPassword.value = true
  connectionTestResult.value = null

  try {
    const response = await fetch(`${API_CONFIG.REST_API.baseURL}/api/v1/config/database/password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: settings.value.database.password })
    })

    const result = await response.json()

    if (result.success) {
      connectionTestResult.value = {
        success: true,
        message: 'Database password updated successfully in configuration'
      }
      passwordChanged.value = false
      // Reload to show masked password
      await loadDatabaseSettings()
    } else {
      connectionTestResult.value = {
        success: false,
        message: result.error || 'Failed to update password'
      }
    }
  } catch (error) {
    connectionTestResult.value = {
      success: false,
      message: `Failed to update password: ${error.message}`
    }
  } finally {
    updatingPassword.value = false
  }
}

async function validatePort() {
  validatingPort.value = true
  connectionTestResult.value = null

  try {
    const port = settings.value.database.port
    if (port < 1024 || port > 65535) {
      connectionTestResult.value = { success: false, message: 'Invalid port number (must be 1024-65535)' }
      return
    }

    // Simple validation - check if port is the standard PostgreSQL port
    if (port !== 5432) {
      connectionTestResult.value = { success: true, message: `Custom port ${port} - ensure PostgreSQL is configured for this port` }
    } else {
      connectionTestResult.value = { success: true, message: 'Standard PostgreSQL port (5432)' }
    }
  } catch (error) {
    connectionTestResult.value = { success: false, message: 'Port validation failed' }
  } finally {
    validatingPort.value = false
  }
}

async function testApiConnection() {
  console.log('Testing API connection...')
  // Implementation would test the API connection
}

async function testDatabaseConnection() {
  testingConnection.value = true
  connectionTestResult.value = null

  try {
    const response = await fetch(`${API_CONFIG.REST_API.baseURL}/api/v1/health/database`)
    const result = await response.json()

    if (result.success) {
      connectionTestResult.value = {
        success: true,
        message: `Connected to PostgreSQL database '${settings.value.database.name}' on ${settings.value.database.host}:${settings.value.database.port}`
      }
    } else {
      connectionTestResult.value = {
        success: false,
        message: result.error || 'Database connection failed'
      }
    }
  } catch (error) {
    connectionTestResult.value = {
      success: false,
      message: `Connection test failed: ${error.message}`
    }
  } finally {
    testingConnection.value = false
  }
}

// Computed password strength
const passwordStrength = computed(() => {
  const pwd = settings.value.database.password
  if (!pwd || !passwordChanged.value) return { score: 0, label: '', color: '' }

  let score = 0
  if (pwd.length >= 12) score += 20
  if (pwd.length >= 16) score += 10
  if (/[A-Z]/.test(pwd)) score += 20
  if (/[a-z]/.test(pwd)) score += 20
  if (/\d/.test(pwd)) score += 15
  if (/[@$!%*?&]/.test(pwd)) score += 15

  if (score < 60) return { score, label: 'Weak', color: '#f44336' }
  if (score < 85) return { score, label: 'Medium', color: '#ff9800' }
  return { score: 100, label: 'Strong', color: '#4caf50' }
})

// Lifecycle
onMounted(async () => {
  // Load database settings from config on mount
  await loadDatabaseSettings()
  // Load settings from store
  const storedSettings = await settingsStore.loadSettings()
  if (storedSettings) {
    Object.assign(settings.value, storedSettings)
  }
})
</script>
