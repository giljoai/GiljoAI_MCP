<template>
  <v-card-text class="pa-8">
    <h2 class="text-h5 mb-6">Database Setup</h2>

    <!-- Info banner -->
    <v-alert type="info" variant="tonal" class="mb-6">
      <div class="d-flex align-center">
        <v-icon start>mdi-information</v-icon>
        <div>
          Enter your PostgreSQL credentials. We'll test the connection and set up the database automatically.
        </div>
      </div>
    </v-alert>

    <!-- Database Configuration Form -->
    <v-form ref="formRef" v-model="formValid" @submit.prevent="testConnection">
      <v-row>
        <v-col cols="12" md="8">
          <v-text-field
            v-model="dbConfig.host"
            label="PostgreSQL Host"
            placeholder="localhost"
            :rules="[rules.required]"
            prepend-inner-icon="mdi-server"
            variant="outlined"
            density="comfortable"
            aria-label="PostgreSQL host address"
          />
        </v-col>
        <v-col cols="12" md="4">
          <v-text-field
            v-model.number="dbConfig.port"
            label="Port"
            type="number"
            :rules="[rules.required, rules.validPort]"
            prepend-inner-icon="mdi-ethernet"
            variant="outlined"
            density="comfortable"
            aria-label="PostgreSQL port number"
          />
        </v-col>
      </v-row>

      <v-row>
        <v-col cols="12" md="6">
          <v-text-field
            v-model="dbConfig.admin_user"
            label="Admin Username"
            placeholder="postgres"
            :rules="[rules.required]"
            prepend-inner-icon="mdi-account"
            variant="outlined"
            density="comfortable"
            aria-label="PostgreSQL admin username"
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-text-field
            ref="passwordFieldRef"
            v-model="dbConfig.admin_password"
            :type="showPassword ? 'text' : 'password'"
            label="Admin Password"
            placeholder="Enter PostgreSQL password"
            :rules="[rules.required]"
            prepend-inner-icon="mdi-lock"
            :append-inner-icon="showPassword ? 'mdi-eye-off' : 'mdi-eye'"
            @click:append-inner="showPassword = !showPassword"
            variant="outlined"
            density="comfortable"
            aria-label="PostgreSQL admin password"
          />
        </v-col>
      </v-row>

      <v-row>
        <v-col cols="12">
          <v-text-field
            v-model="dbConfig.database_name"
            label="Database Name"
            placeholder="giljo_mcp"
            :rules="[rules.required, rules.validDbName]"
            prepend-inner-icon="mdi-database"
            variant="outlined"
            density="comfortable"
            hint="Database will be created if it doesn't exist"
            persistent-hint
            aria-label="Database name to create"
          />
        </v-col>
      </v-row>
    </v-form>

    <!-- Action Buttons -->
    <div class="mt-6 d-flex flex-column gap-3">
      <!-- Test Connection Button -->
      <v-btn
        color="primary"
        variant="outlined"
        size="large"
        :loading="testing"
        :disabled="!formValid || settingUp || setupComplete"
        @click="testConnection"
        prepend-icon="mdi-connection"
        block
      >
        Test Connection
      </v-btn>

      <!-- Setup Database Button (shown after successful test) -->
      <v-btn
        v-if="connectionSuccess"
        color="success"
        size="large"
        :loading="settingUp"
        :disabled="setupComplete"
        @click="setupDatabase"
        prepend-icon="mdi-database-cog"
        block
      >
        Setup Database
      </v-btn>
    </div>

    <!-- Connection Test Result -->
    <v-alert
      v-if="connectionTested"
      :type="connectionSuccess ? 'success' : 'error'"
      variant="tonal"
      class="mt-4"
      aria-live="polite"
    >
      <div class="d-flex align-center">
        <v-icon start>{{ connectionSuccess ? 'mdi-check-circle' : 'mdi-alert-circle' }}</v-icon>
        <div>
          <div class="font-weight-bold">{{ connectionMessage }}</div>
          <div v-if="connectionSuccess && postgresVersion" class="text-caption mt-1">
            PostgreSQL {{ postgresVersion }} detected
          </div>
          <div v-if="!connectionSuccess" class="text-caption mt-2">
            <strong>Troubleshooting:</strong>
            <ul class="ml-4 mt-1">
              <li v-if="errorType === 'auth_failed'">
                Verify your PostgreSQL password is correct
              </li>
              <li v-else-if="errorType === 'connection_refused'">
                Ensure PostgreSQL is running and accessible on {{ dbConfig.host }}:{{ dbConfig.port }}
              </li>
              <li v-else>
                Check PostgreSQL logs for more details
              </li>
              <li>
                <a href="/docs/troubleshooting/database" target="_blank" class="text-primary">
                  View detailed troubleshooting guide
                </a>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </v-alert>

    <!-- Setup Progress -->
    <v-card
      v-if="settingUp"
      variant="outlined"
      class="mt-4"
    >
      <v-card-text>
        <div class="text-subtitle-2 mb-2">Setting up database...</div>
        <v-progress-linear indeterminate color="primary" />
        <div class="text-caption text-medium-emphasis mt-2">
          This may take a few moments. Creating database, roles, and running migrations.
        </div>
      </v-card-text>
    </v-card>

    <!-- Setup Complete -->
    <v-alert
      v-if="setupComplete"
      type="success"
      variant="tonal"
      class="mt-4"
      aria-live="polite"
    >
      <div class="d-flex align-center">
        <v-icon start size="large">mdi-check-circle</v-icon>
        <div>
          <div class="font-weight-bold text-h6">Database Setup Complete!</div>
          <div class="mt-2">
            Database <strong>{{ dbConfig.database_name }}</strong> has been created and configured.
          </div>
          <div v-if="credentialsPath" class="text-caption mt-2">
            Credentials saved to: <code>{{ credentialsPath }}</code>
          </div>
        </div>
      </div>
    </v-alert>

    <!-- Setup Warnings (if any) -->
    <v-alert
      v-if="setupWarnings.length > 0"
      type="warning"
      variant="tonal"
      class="mt-4"
    >
      <div class="font-weight-bold mb-2">Warnings:</div>
      <ul class="ml-4">
        <li v-for="(warning, index) in setupWarnings" :key="index">
          {{ warning }}
        </li>
      </ul>
    </v-alert>

    <!-- Progress Indicator -->
    <v-card variant="outlined" class="mt-6 mb-6">
      <v-card-text>
        <div class="d-flex justify-space-between mb-2">
          <span class="text-caption">Progress: Step 2 of 7</span>
          <span class="text-caption">29%</span>
        </div>
        <v-progress-linear :model-value="29" color="primary" />
      </v-card-text>
    </v-card>

    <!-- Navigation Buttons -->
    <div class="d-flex justify-space-between">
      <v-btn
        variant="outlined"
        :disabled="settingUp"
        @click="$emit('back')"
        aria-label="Go back to welcome"
      >
        <v-icon start>mdi-arrow-left</v-icon>
        Back
      </v-btn>
      <v-btn
        color="primary"
        :disabled="!setupComplete"
        @click="$emit('next')"
        aria-label="Continue to deployment mode"
      >
        Continue
        <v-icon end>mdi-arrow-right</v-icon>
      </v-btn>
    </div>
  </v-card-text>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import setupService from '@/services/setupService'

/**
 * DatabaseStep - PostgreSQL database setup step
 *
 * Handles:
 * - PostgreSQL connection testing
 * - Database creation
 * - Schema migration
 * - Configuration updates
 */

defineEmits(['next', 'back'])

// Form references
const formRef = ref(null)
const passwordFieldRef = ref(null)

// Form state
const formValid = ref(false)
const showPassword = ref(false)

// Database configuration
const dbConfig = ref({
  host: 'localhost',
  port: 5432,
  admin_user: 'postgres',
  admin_password: '',
  database_name: 'giljo_mcp'
})

// Connection test state
const testing = ref(false)
const connectionTested = ref(false)
const connectionSuccess = ref(false)
const connectionMessage = ref('')
const postgresVersion = ref(null)
const errorType = ref(null)

// Setup state
const settingUp = ref(false)
const setupComplete = ref(false)
const credentialsPath = ref(null)
const setupWarnings = ref([])

// Validation rules
const rules = {
  required: (value) => !!value || 'This field is required',
  validPort: (value) => {
    const port = parseInt(value)
    return (port >= 1024 && port <= 65535) || 'Port must be between 1024 and 65535'
  },
  validDbName: (value) => {
    const regex = /^[a-zA-Z_][a-zA-Z0-9_]*$/
    return regex.test(value) || 'Database name must start with letter or underscore and contain only alphanumeric characters'
  }
}

/**
 * Test PostgreSQL connection
 */
async function testConnection() {
  if (!formValid.value) {
    return
  }

  testing.value = true
  connectionTested.value = false
  connectionSuccess.value = false
  errorType.value = null

  try {
    const result = await setupService.testPostgresConnection(dbConfig.value)

    if (result.success) {
      connectionSuccess.value = true
      connectionMessage.value = result.message || 'Connection successful!'
      postgresVersion.value = result.postgres_version
    } else {
      connectionSuccess.value = false
      connectionMessage.value = result.error || 'Connection failed'
      errorType.value = result.error_type
    }
    connectionTested.value = true
  } catch (error) {
    connectionSuccess.value = false
    connectionMessage.value = `Connection error: ${error.message}`
    errorType.value = 'network_error'
    connectionTested.value = true
  } finally {
    testing.value = false
  }
}

/**
 * Setup PostgreSQL database
 */
async function setupDatabase() {
  if (!connectionSuccess.value) {
    return
  }

  settingUp.value = true
  setupWarnings.value = []

  try {
    const result = await setupService.setupPostgresDatabase(dbConfig.value)

    if (result.success) {
      setupComplete.value = true
      credentialsPath.value = result.credentials_path

      // Capture any warnings
      if (result.warnings && result.warnings.length > 0) {
        setupWarnings.value = result.warnings
      }
    } else {
      // Show error
      connectionSuccess.value = false
      connectionMessage.value = result.error || 'Database setup failed'
      connectionTested.value = true
    }
  } catch (error) {
    connectionSuccess.value = false
    connectionMessage.value = `Setup error: ${error.message}`
    connectionTested.value = true
  } finally {
    settingUp.value = false
  }
}

// Auto-focus password field on mount
onMounted(() => {
  if (passwordFieldRef.value) {
    passwordFieldRef.value.focus()
  }
})
</script>

<style scoped>
h2 {
  color: rgb(var(--v-theme-primary));
}

a {
  text-decoration: none;
}

a:hover {
  text-decoration: underline;
}

code {
  background-color: rgb(var(--v-theme-surface-variant));
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.875em;
}

.gap-3 {
  gap: 12px;
}
</style>
