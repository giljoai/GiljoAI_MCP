<template>
  <v-container>
    <!-- Page Header -->
    <h1 class="text-h4 mb-2">Admin Settings</h1>
    <p class="text-subtitle-1 mb-4">Configure server and system-wide settings (Admin only)</p>

    <!-- Settings Tabs -->
    <v-tabs v-model="activeTab" class="mb-6 global-tabs">
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

      <v-tab value="security">
        <v-icon start>mdi-shield-lock</v-icon>
        Security
      </v-tab>
      <v-tab value="system">
        <v-icon start>mdi-cog</v-icon>
        System
      </v-tab>
    </v-tabs>

    <!-- Tab Content -->
    <v-window v-model="activeTab" class="global-tabs-window">
      <!-- Network Settings -->
      <v-window-item value="network">
        <NetworkSettingsTab
          :config="networkSettings"
          :cors-origins="corsOrigins"
          :loading="loading.network"
          @refresh="loadNetworkSettings"
          @save="saveNetworkSettings"
        />
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
        <AdminIntegrationsTab />
      </v-window-item>

      <!-- Security Settings -->
      <v-window-item value="security">
        <SecuritySettingsTab
          :cookie-domains="cookieDomains"
          :loading="loading.security"
          :feedback="securityFeedback"
          @add-domain="addCookieDomain"
          @remove-domain="removeCookieDomain"
          @reload="loadCookieDomains"
          @clear-feedback="clearSecurityFeedback"
        />
      </v-window-item>

      <!-- System Prompt -->
      <v-window-item value="system">
        <SystemPromptTab />
      </v-window-item>
    </v-window>

    <!-- Configuration Modals -->
    <ClaudeConfigModal v-model="showClaudeConfigModal" />
    <CodexConfigModal v-model="showCodexConfigModal" />
    <GeminiConfigModal v-model="showGeminiConfigModal" />
  </v-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getApiBaseURL } from '@/config/api'
import api from '@/services/api'

// Components
import DatabaseConnection from '@/components/DatabaseConnection.vue'
import NetworkSettingsTab from '@/components/settings/tabs/NetworkSettingsTab.vue'
import AdminIntegrationsTab from '@/components/settings/tabs/AdminIntegrationsTab.vue'
import SecuritySettingsTab from '@/components/settings/tabs/SecuritySettingsTab.vue'
import SystemPromptTab from '@/components/settings/tabs/SystemPromptTab.vue'
import ClaudeConfigModal from '@/components/settings/modals/ClaudeConfigModal.vue'
import CodexConfigModal from '@/components/settings/modals/CodexConfigModal.vue'
import GeminiConfigModal from '@/components/settings/modals/GeminiConfigModal.vue'

// State
const activeTab = ref('network')

// Loading states
const loading = ref({
  network: false,
  security: false,
})

// Network settings state
const networkSettings = ref({
  externalHost: 'localhost',
  apiPort: 7272,
  frontendPort: 7274,
})
const corsOrigins = ref([])

// Configuration modal state
const showClaudeConfigModal = ref(false)
const showCodexConfigModal = ref(false)
const showGeminiConfigModal = ref(false)

// Cookie Domain Whitelist state
const cookieDomains = ref([])
const securityFeedback = ref(null)

// Network Settings Methods
async function loadNetworkSettings() {
  loading.value.network = true
  try {
    // Load from /api/v1/config endpoint only
    const response = await fetch(`${getApiBaseURL()}/api/v1/config`, {
      credentials: 'include',
      timeout: 5000,
    })

    if (!response.ok) {
      throw new Error(`Config endpoint failed: ${response.statusText}`)
    }

    const config = await response.json()

    // Set external host (configured during installation)
    networkSettings.value.externalHost = config.services?.external_host || 'localhost'

    // Set API port
    networkSettings.value.apiPort = config.services?.api?.port || 7272

    // Set Frontend port
    networkSettings.value.frontendPort = config.services?.frontend?.port || 7274

    // Set CORS origins
    corsOrigins.value = config.security?.cors?.allowed_origins || []

    console.log('[SYSTEM SETTINGS] Network settings loaded successfully')
  } catch (error) {
    console.error('[SYSTEM SETTINGS] Failed to load network settings:', error)

    // Fallback to defaults
    networkSettings.value.externalHost = 'localhost'
    networkSettings.value.apiPort = 7272
    networkSettings.value.frontendPort = 7274
    corsOrigins.value = []
  } finally {
    loading.value.network = false
  }
}

async function saveNetworkSettings() {
  try {
    // Save CORS origins back to config
    const response = await fetch(`${getApiBaseURL()}/api/v1/config`, {
      method: 'PATCH',
      credentials: 'include',
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
      console.log('[SYSTEM SETTINGS] Network settings saved successfully')
    }
  } catch (error) {
    console.error('Failed to save network settings:', error)
  }
}

// Database Methods
async function loadDatabaseSettings() {
  try {
    // Fetch database config from API
    const response = await fetch(`${getApiBaseURL()}/api/v1/config/database`, {
      credentials: 'include',
    })
    await response.json()

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

// Cookie Domain Whitelist Methods
async function loadCookieDomains() {
  loading.value.security = true
  try {
    const response = await api.settings.getCookieDomains()
    cookieDomains.value = response.data.domains || []
    console.log('[SECURITY] Cookie domains loaded:', cookieDomains.value.length)
  } catch (error) {
    console.error('[SECURITY] Failed to load cookie domains:', error)
    securityFeedback.value = {
      type: 'error',
      message: 'Failed to load cookie domains. Please try again.',
    }
  } finally {
    loading.value.security = false
  }
}

async function addCookieDomain(domain) {
  // Check for duplicates
  if (cookieDomains.value.includes(domain)) {
    securityFeedback.value = {
      type: 'warning',
      message: `Domain "${domain}" is already in the whitelist.`,
    }
    return
  }

  try {
    await api.settings.addCookieDomain(domain)
    cookieDomains.value.push(domain)
    securityFeedback.value = {
      type: 'success',
      message: `Domain "${domain}" added successfully.`,
    }
    console.log('[SECURITY] Cookie domain added:', domain)
  } catch (error) {
    console.error('[SECURITY] Failed to add cookie domain:', error)
    securityFeedback.value = {
      type: 'error',
      message: error.response?.data?.detail || 'Failed to add domain. Please try again.',
    }
  }
}

async function removeCookieDomain(domain) {
  try {
    await api.settings.removeCookieDomain(domain)
    cookieDomains.value = cookieDomains.value.filter((d) => d !== domain)
    securityFeedback.value = {
      type: 'success',
      message: `Domain "${domain}" removed successfully.`,
    }
    console.log('[SECURITY] Cookie domain removed:', domain)
  } catch (error) {
    console.error('[SECURITY] Failed to remove cookie domain:', error)
    securityFeedback.value = {
      type: 'error',
      message: error.response?.data?.detail || 'Failed to remove domain. Please try again.',
    }
  }
}

function clearSecurityFeedback() {
  securityFeedback.value = null
}

// Lifecycle
onMounted(async () => {
  // Load database settings from config on mount
  await loadDatabaseSettings()

  // Load network settings from config on mount
  await loadNetworkSettings()

  // Load cookie domains
  await loadCookieDomains()
})
</script>
