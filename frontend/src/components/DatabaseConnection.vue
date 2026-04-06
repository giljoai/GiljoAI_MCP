<template>
  <div>
    <!-- Title -->
    <div v-if="showTitle" class="tab-header mb-4">
      <h2 class="text-h6">{{ title }}</h2>
      <p v-if="showInfoBanner" class="text-body-2 text-muted-a11y mt-1">{{ infoBannerText }}</p>
    </div>

    <v-card class="db-card smooth-border">
    <v-card-text>

      <!-- Database Configuration Fields -->
      <v-row>
        <!-- Host -->
        <v-col cols="12" md="6">
          <v-text-field
            v-model="dbConfig.host"
            label="Host"
            variant="outlined"
            :readonly="readonly"
            :prepend-inner-icon="readonly ? 'mdi-lock' : undefined"
            hint="Database host address"
            persistent-hint
            aria-label="Database host"
            data-test="db-host"
          />
        </v-col>

        <!-- Port -->
        <v-col cols="12" md="6">
          <v-text-field
            v-model.number="dbConfig.port"
            label="Port"
            type="number"
            variant="outlined"
            :readonly="readonly"
            :prepend-inner-icon="readonly ? 'mdi-lock' : undefined"
            hint="Database port number"
            persistent-hint
            aria-label="Database port"
            data-test="db-port"
          />
        </v-col>

        <!-- Database Name -->
        <v-col cols="12" md="6">
          <v-text-field
            v-model="dbConfig.name"
            label="Database Name"
            variant="outlined"
            :readonly="readonly"
            :prepend-inner-icon="readonly ? 'mdi-lock' : undefined"
            hint="Name of the database"
            persistent-hint
            aria-label="Database name"
            data-test="db-name"
          />
        </v-col>

        <!-- Username -->
        <v-col cols="12" md="6">
          <v-text-field
            v-model="dbConfig.user"
            label="Username"
            variant="outlined"
            :readonly="readonly"
            :prepend-inner-icon="readonly ? 'mdi-lock' : undefined"
            hint="Database username"
            persistent-hint
            aria-label="Database username"
            data-test="db-user"
          />
        </v-col>

        <!-- Password -->
        <v-col cols="12">
          <v-text-field
            v-model="dbConfig.password"
            label="Password"
            type="password"
            variant="outlined"
            :readonly="readonly"
            :prepend-inner-icon="readonly ? 'mdi-lock' : undefined"
            hint="Database password (masked for security)"
            persistent-hint
            aria-label="Database password"
            data-test="db-password"
          />
        </v-col>
      </v-row>

      <!-- Test Connection Button (moved above divider - Handover 0424d UI tweak) -->
      <div v-if="showTestButton" class="mt-4 mb-4">
        <v-btn
          variant="flat"
          color="primary"
          size="large"
          :loading="testing"
          :disabled="testing"
          aria-label="Test database connection"
          data-test="test-connection-btn"
          @click="testConnection"
        >
          <v-icon start>mdi-database-check</v-icon>
          {{ testButtonText }}
        </v-btn>
      </div>

      <!-- Divider -->
      <v-divider class="my-6" />

      <!-- Connection Test Result Alert -->
      <v-alert
        v-if="connectionTestResult"
        :type="connectionTestResult.success ? 'success' : 'error'"
        variant="tonal"
        class="mb-4"
        role="alert"
        :aria-live="connectionTestResult.success ? 'polite' : 'assertive'"
        data-test="test-result"
      >
        <div v-html="formatTestResultMessage(connectionTestResult)"></div> <!-- DOMPurify-sanitized -->
      </v-alert>
    </v-card-text>

    <!-- Action Buttons (Test Connection moved above divider - Handover 0424d) -->
    <v-card-actions v-if="$slots.actions" :class="{ 'justify-center': centerButton }">
      <v-spacer v-if="!centerButton" />

      <!-- Actions Slot (for custom buttons like "Reload from Config") -->
      <slot name="actions"></slot>
    </v-card-actions>
  </v-card>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import api from '@/services/api'
import DOMPurify from 'dompurify'

/**
 * DatabaseConnection - Reusable database connection testing component
 *
 * Extracted from Settings component for reuse in:
 * 1. Settings page (database tab)
 * 2. Setup wizard (database verification step)
 *
 * @component
 * @example
 * <DatabaseConnection
 *   :readonly="true"
 *   :show-test-button="true"
 *   :auto-test="true"
 *   @connection-success="handleSuccess"
 *   @connection-error="handleFailure"
 * />
 */

// Props
const props = defineProps({
  /** Lock all fields for read-only display */
  readonly: {
    type: Boolean,
    default: false,
  },
  /** Show test connection button */
  showTestButton: {
    type: Boolean,
    default: true,
  },
  /** Show title in card header */
  showTitle: {
    type: Boolean,
    default: false,
  },
  /** Card title text */
  title: {
    type: String,
    default: 'PostgreSQL Database Configuration',
  },
  /** Show info banner */
  showInfoBanner: {
    type: Boolean,
    default: true,
  },
  /** Info banner text */
  infoBannerText: {
    type: String,
    default: 'Database settings are configured during installation',
  },
  /** Test button text */
  testButtonText: {
    type: String,
    default: 'Test Connection',
  },
  /** Initial database settings */
  initialSettings: {
    type: Object,
    default: null,
  },
  /** Center the test button (for wizard mode) */
  centerButton: {
    type: Boolean,
    default: false,
  },
})

// Emits
const emit = defineEmits([
  'connection-success',
  'connection-error',
  'tested',
  'settings-loaded',
  'settings-load-error',
])

// State
const dbConfig = ref({
  type: 'postgresql',
  host: 'localhost',
  port: 5432,
  name: 'giljo_mcp',
  user: 'postgres',
  password: '********',
})

const testing = ref(false)
const connectionTestResult = ref(null)

// Methods
/**
 * Test database connection
 */
const testConnection = async () => {
  testing.value = true
  connectionTestResult.value = null

  try {
    // Use axios client with credentials to avoid cross-origin cookie issues
    const { data: result } = await api.settings.testDatabase()

    if (result.success) {
      connectionTestResult.value = {
        success: true,
        message: `Connected to PostgreSQL database '${dbConfig.value.name}' on ${dbConfig.value.host}:${dbConfig.value.port}`,
        details: {
          host: dbConfig.value.host,
          port: dbConfig.value.port,
          database: dbConfig.value.name,
          user: dbConfig.value.user,
        },
      }
      emit('connection-success', connectionTestResult.value)
    } else {
      connectionTestResult.value = {
        success: false,
        message: result.error || 'Database connection failed',
        error: result.error,
        code: result.code,
        suggestions: generateSuggestions(result),
      }
      emit('connection-error', connectionTestResult.value)
    }
  } catch (error) {
    connectionTestResult.value = {
      success: false,
      message: `Connection test failed: ${error.message}`,
      error: error.message,
      suggestions: generateSuggestions(error),
    }
    emit('connection-error', connectionTestResult.value)
  } finally {
    testing.value = false
    emit('tested', connectionTestResult.value)
  }
}

/**
 * Load database settings from API
 */
const loadSettings = async () => {
  try {
    // Use axios client with credentials for config fetch as well
    const { data: config } = await api.settings.getDatabase()

    dbConfig.value = {
      type: 'postgresql',
      host: config.host || 'localhost',
      port: config.port || 5432,
      name: config.name || 'giljo_mcp',
      user: config.user || 'postgres',
      password: '********', // Always masked
    }

    emit('settings-loaded', dbConfig.value)
  } catch (error) {
    emit('settings-load-error', error)
  }
}

/**
 * Clear test result
 */
const clearTestResult = () => {
  connectionTestResult.value = null
}

/**
 * Format test result message with suggestions
 */
const formatTestResultMessage = (result) => {
  if (result.success) {
    return DOMPurify.sanitize(result.message)
  }

  let html = `<strong>${result.message}</strong>`

  if (result.suggestions && result.suggestions.length > 0) {
    html += '<div class="mt-2 text-caption"><strong>Possible causes:</strong></div>'
    html += '<ul class="mt-1 ml-4">'
    result.suggestions.forEach((suggestion) => {
      html += `<li class="text-caption">${suggestion}</li>`
    })
    html += '</ul>'
  }

  return DOMPurify.sanitize(html)
}

/**
 * Generate helpful suggestions based on error
 */
const generateSuggestions = (error) => {
  const suggestions = []
  const errorMsg = error.message || error.error || ''

  if (errorMsg.includes('ECONNREFUSED') || errorMsg.includes('Connection refused')) {
    suggestions.push('PostgreSQL service may not be running')
    suggestions.push('Verify PostgreSQL is installed and started')
    suggestions.push('Check if port 5432 is in use by another application')
  }

  if (errorMsg.includes('timeout') || errorMsg.includes('ETIMEDOUT')) {
    suggestions.push('Network timeout - check firewall settings')
    suggestions.push('Verify host address is correct')
  }

  if (errorMsg.includes('authentication') || errorMsg.includes('password')) {
    suggestions.push('Check username and password')
    suggestions.push('Verify PostgreSQL authentication configuration (pg_hba.conf)')
  }

  if (errorMsg.includes('database') && errorMsg.includes('does not exist')) {
    suggestions.push('Database may not have been created during installation')
    suggestions.push('Run database initialization script')
  }

  if (suggestions.length === 0) {
    suggestions.push('Check PostgreSQL service status')
    suggestions.push('Verify connection details are correct')
    suggestions.push('Review PostgreSQL logs for errors')
  }

  return suggestions
}

// Watchers
watch(
  () => props.initialSettings,
  (newSettings) => {
    if (newSettings) {
      dbConfig.value = {
        type: newSettings.type || 'postgresql',
        host: newSettings.host || 'localhost',
        port: newSettings.port || 5432,
        name: newSettings.name || 'giljo_mcp',
        user: newSettings.user || 'postgres',
        password: '********', // Always masked
      }
    }
  },
  { immediate: true },
)

// Lifecycle
onMounted(async () => {
  // Load settings if not provided via props
  if (!props.initialSettings) {
    await loadSettings()
  }
})

// Expose methods for parent components
defineExpose({
  testConnection,
  loadSettings,
  clearTestResult,
})
</script>

<style lang="scss" scoped>
@use '../styles/design-tokens' as *;

.db-card {
  background: $elevation-raised;
  border-radius: $border-radius-rounded !important;
}

/* Improve readability of suggestion lists */
:deep(ul) {
  list-style-type: disc;
  padding-left: 1.5rem;
}

:deep(li) {
  margin-bottom: 0.25rem;
}
</style>
