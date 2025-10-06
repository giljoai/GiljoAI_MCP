<template>
  <v-card-text class="pa-8">
    <h2 class="text-h5 mb-6">Database Verification</h2>

    <!-- Info banner -->
    <v-alert type="info" variant="tonal" class="mb-6">
      <div class="d-flex align-center">
        <v-icon start>mdi-information</v-icon>
        <div>
          Verifying database setup from CLI installation. Your credentials are stored securely in .env and will not be displayed.
        </div>
      </div>
    </v-alert>

    <!-- Verification in progress -->
    <v-card
      v-if="verifying"
      variant="outlined"
      class="mt-4"
    >
      <v-card-text>
        <div class="text-subtitle-2 mb-2">Verifying database connection...</div>
        <v-progress-linear indeterminate color="primary" />
        <div class="text-caption text-medium-emphasis mt-2">
          Testing connection to PostgreSQL and checking schema migration status.
        </div>
      </v-card-text>
    </v-card>

    <!-- Verification Success -->
    <v-alert
      v-if="verificationComplete && verificationSuccess"
      type="success"
      variant="tonal"
      class="mt-4"
      aria-live="polite"
    >
      <div class="d-flex align-center">
        <v-icon start size="large">mdi-check-circle</v-icon>
        <div>
          <div class="font-weight-bold text-h6">Database Verified!</div>
          <div class="mt-2">
            <strong>Database:</strong> {{ dbInfo.database }}<br>
            <strong>Host:</strong> {{ dbInfo.host }}:{{ dbInfo.port }}<br>
            <strong>PostgreSQL Version:</strong> {{ dbInfo.postgresql_version }}<br>
            <strong>Schema Migration:</strong> {{ dbInfo.schema_migrated ? '✓ Complete' : '✗ Pending' }}<br>
            <strong>Tables:</strong> {{ dbInfo.tables_count }} tables
          </div>
        </div>
      </div>
    </v-alert>

    <!-- Verification Failed -->
    <v-alert
      v-if="verificationComplete && !verificationSuccess"
      type="error"
      variant="tonal"
      class="mt-4"
      aria-live="polite"
    >
      <div class="d-flex align-center">
        <v-icon start>mdi-alert-circle</v-icon>
        <div>
          <div class="font-weight-bold">{{ errorMessage }}</div>
          <div class="text-caption mt-2">
            <strong>Troubleshooting:</strong>
            <ul class="ml-4 mt-1">
              <li v-if="errorType === 'missing_credentials'">
                Please run the CLI installer first: <code>python installer/cli/install.py</code>
              </li>
              <li v-else-if="errorType === 'database_missing'">
                The database was not created. Please re-run the CLI installer.
              </li>
              <li v-else-if="errorType === 'auth_failed'">
                Credentials in .env may be incorrect. Check .env file.
              </li>
              <li v-else-if="errorType === 'connection_refused'">
                Ensure PostgreSQL is running and accessible.
              </li>
              <li v-else>
                Check API server logs for details.
              </li>
            </ul>
          </div>
          <div class="mt-3">
            <v-btn
              color="primary"
              variant="outlined"
              @click="retryVerification"
              prepend-icon="mdi-refresh"
            >
              Retry Verification
            </v-btn>
          </div>
        </div>
      </div>
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
        :disabled="verifying"
        @click="$emit('back')"
        aria-label="Go back to welcome"
      >
        <v-icon start>mdi-arrow-left</v-icon>
        Back
      </v-btn>
      <v-btn
        color="primary"
        :disabled="!verificationSuccess"
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
 * DatabaseStep - Database verification step (VERIFICATION ONLY)
 *
 * This step verifies the database setup that was already completed
 * by the CLI installer. It does NOT ask for credentials or create
 * the database - that was already done.
 *
 * Security: Credentials are stored in .env server-side and never
 * sent to the frontend.
 */

defineEmits(['next', 'back'])

// Verification state
const verifying = ref(false)
const verificationComplete = ref(false)
const verificationSuccess = ref(false)
const errorMessage = ref('')
const errorType = ref(null)

// Database info (non-sensitive metadata only)
const dbInfo = ref({
  database: '',
  host: '',
  port: null,
  postgresql_version: null,
  schema_migrated: false,
  tables_count: 0
})

/**
 * Verify database connection
 * Called automatically on mount
 */
async function verifyDatabaseConnection() {
  verifying.value = true
  verificationComplete.value = false
  verificationSuccess.value = false
  errorType.value = null

  try {
    console.log('[DatabaseStep] Verifying database setup...')
    const result = await setupService.verifyDatabaseSetup()

    if (result.success) {
      console.log('[DatabaseStep] Verification successful:', result)
      verificationSuccess.value = true
      dbInfo.value = {
        database: result.database,
        host: result.host,
        port: result.port,
        postgresql_version: result.postgresql_version,
        schema_migrated: result.schema_migrated,
        tables_count: result.tables_count
      }
    } else {
      console.error('[DatabaseStep] Verification failed:', result)
      verificationSuccess.value = false
      errorMessage.value = result.message || 'Database verification failed'
      errorType.value = result.status
    }

    verificationComplete.value = true
  } catch (error) {
    console.error('[DatabaseStep] Verification error:', error)
    verificationSuccess.value = false
    errorMessage.value = `Verification error: ${error.message}`
    errorType.value = 'network_error'
    verificationComplete.value = true
  } finally {
    verifying.value = false
  }
}

/**
 * Retry verification
 */
function retryVerification() {
  console.log('[DatabaseStep] Retrying verification...')
  verifyDatabaseConnection()
}

// Auto-verify on mount
onMounted(() => {
  console.log('[DatabaseStep] Component mounted, starting verification...')
  verifyDatabaseConnection()
})
</script>

<style scoped>
code {
  background-color: rgba(0, 0, 0, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
}
</style>
