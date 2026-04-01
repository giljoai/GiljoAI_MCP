<template>
  <v-container>
    <!-- Page Header -->
    <h1 class="text-h4 mb-2">Admin Settings</h1>
    <p class="text-subtitle-1 mb-4 settings-subtitle">Configure server and system-wide settings (Admin only)</p>

    <!-- Settings Pills -->
    <div class="pill-toggle-row">
      <button
        class="pill-toggle"
        :class="{ 'pill-toggle--active': activeTab === 'identity' }"
        data-test="identity-tab"
        @click="activeTab = 'identity'"
      >
        <v-icon size="16" class="pill-toggle-icon">mdi-account-group</v-icon>
        Identity
      </button>
      <button
        class="pill-toggle"
        :class="{ 'pill-toggle--active': activeTab === 'network' }"
        @click="activeTab = 'network'"
      >
        <v-icon size="16" class="pill-toggle-icon">mdi-network-outline</v-icon>
        Network
      </button>
      <button
        class="pill-toggle"
        :class="{ 'pill-toggle--active': activeTab === 'database' }"
        @click="activeTab = 'database'"
      >
        <v-icon size="16" class="pill-toggle-icon">mdi-database</v-icon>
        Database
      </button>
      <button
        class="pill-toggle"
        :class="{ 'pill-toggle--active': activeTab === 'security' }"
        @click="activeTab = 'security'"
      >
        <v-icon size="16" class="pill-toggle-icon">mdi-shield-lock</v-icon>
        Security
      </button>
      <button
        class="pill-toggle"
        :class="{ 'pill-toggle--active': activeTab === 'prompts' }"
        @click="activeTab = 'prompts'"
      >
        <v-icon size="16" class="pill-toggle-icon">mdi-file-document-edit</v-icon>
        Prompts
      </button>
    </div>

    <!-- Tab Content -->
    <div class="pill-tabs-content">
      <v-window v-model="activeTab" class="global-tabs-window">
      <!-- Identity (Workspace + Members) - Handover 0434 -->
      <v-window-item value="identity">
        <IdentityTab />
      </v-window-item>

      <!-- Network Settings -->
      <v-window-item value="network">
        <NetworkSettingsTab
          :config="networkSettings"
          :cors-origins="corsOrigins"
          :ssl-enabled="sslEnabled"
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

      <!-- Prompts (Orchestrator System Prompt) - Renamed from "System" in Handover 0434 -->
      <v-window-item value="prompts">
        <SystemPromptTab />
      </v-window-item>
    </v-window>
    </div>

  </v-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getApiBaseURL } from '@/config/api'
import api from '@/services/api'

// Components
import DatabaseConnection from '@/components/DatabaseConnection.vue'
import IdentityTab from '@/components/settings/tabs/IdentityTab.vue'
import NetworkSettingsTab from '@/components/settings/tabs/NetworkSettingsTab.vue'
import SecuritySettingsTab from '@/components/settings/tabs/SecuritySettingsTab.vue'
import SystemPromptTab from '@/components/settings/tabs/SystemPromptTab.vue'

// State
const activeTab = ref('identity')

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
const sslEnabled = ref(false)

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

    // Set SSL/HTTPS status
    sslEnabled.value = Boolean(config.features?.ssl_enabled)

  } catch (error) {
    console.error('[SYSTEM SETTINGS] Failed to load network settings:', error)

    // Fallback to defaults
    networkSettings.value.externalHost = 'localhost'
    networkSettings.value.apiPort = 7272
    networkSettings.value.frontendPort = 7274
    corsOrigins.value = []
    sslEnabled.value = false
  } finally {
    loading.value.network = false
  }
}

async function saveNetworkSettings() {
  try {
    // Save CORS origins back to config
    const csrfToken = document.cookie.match(/csrf_token=([^;]+)/)?.[1]
    await fetch(`${getApiBaseURL()}/api/v1/config`, {
      method: 'PATCH',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...(csrfToken && { 'X-CSRF-Token': csrfToken }),
      },
      body: JSON.stringify({
        security: {
          cors: {
            allowed_origins: corsOrigins.value,
          },
        },
      }),
    })

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
  } catch (error) {
    console.error('Failed to load database settings:', error)
  }
}

function handleDatabaseSuccess(_result) {
  // Database connection successful
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

<style lang="scss" scoped>
@use '../styles/design-tokens' as *;
.settings-subtitle {
  color: #8895a8;
}

/* Pill toggle row */
.pill-toggle-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.pill-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border-radius: $border-radius-pill;
  padding: 8px 18px;
  font-size: 0.78rem;
  font-weight: 500;
  font-family: inherit;
  cursor: pointer;
  transition: background 0.2s, color 0.2s, box-shadow 0.2s;
  background: transparent;
  color: #8895a8;
  border: none;
  box-shadow: inset 0 0 0 1px var(--smooth-border-color, #2a4a6b);
}

.pill-toggle:hover {
  color: #b0bec5;
}

.pill-toggle--active {
  background: rgba(255, 195, 0, 0.12);
  color: #ffc300;
  box-shadow: none;
}

.pill-toggle-icon {
  flex-shrink: 0;
}

.pill-tabs-content {
  padding: 16px 0;
}
</style>
