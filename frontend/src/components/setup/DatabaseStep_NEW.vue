<template>
  <v-card-text class="pa-8">
    <h2 class="text-h5 mb-6">Database Connection</h2>

    <!-- Reusable Database Connection Component -->
    <div class="database-step-wrapper">
      <DatabaseConnection
        :readonly="true"
        :show-test-button="true"
        :show-title="false"
        :show-info-banner="true"
        info-banner-text="Database settings are configured during installation. This step verifies connectivity."
        @connection-success="handleConnectionSuccess"
        @connection-error="handleConnectionFailure"
      />
    </div>

    <!-- Troubleshooting link -->
    <div class="text-center mt-4">
      <p class="text-caption text-medium-emphasis">
        <v-icon size="small" class="mr-1">mdi-help-circle-outline</v-icon>
        Need help?
        <a
          href="/docs/troubleshooting/database"
          target="_blank"
          rel="noopener noreferrer"
          class="text-primary"
        >
          View troubleshooting guide
        </a>
        or configure database in
        <a
          href="/settings"
          class="text-primary"
        >
          Settings
        </a>
      </p>
    </div>

    <!-- Progress -->
    <v-card variant="outlined" class="mt-6 mb-6">
      <v-card-text>
        <div class="d-flex justify-space-between mb-2">
          <span class="text-caption">Progress: Step 1 of 5</span>
          <span class="text-caption">20%</span>
        </div>
        <v-progress-linear :model-value="20" color="warning" />
      </v-card-text>
    </v-card>

    <!-- Navigation buttons -->
    <div class="d-flex justify-end">
      <v-btn
        variant="flat"
        color="primary"
        :disabled="!connectionVerified"
        @click="$emit('next')"
        aria-label="Continue to AI tools attachment"
      >
        Continue
        <v-icon end>mdi-arrow-right</v-icon>
      </v-btn>
    </div>
  </v-card-text>
</template>

<script setup>
import { ref } from 'vue'
import DatabaseConnection from '@/components/DatabaseConnection.vue'

/**
 * DatabaseStep - Database connection verification step
 *
 * Reuses DatabaseConnection component to test database connectivity
 */

defineEmits(['next', 'back'])

const connectionVerified = ref(false)

const handleConnectionSuccess = () => {
  connectionVerified.value = true
}

const handleConnectionFailure = () => {
  connectionVerified.value = false
}
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

/* Center and brighten the Test Connection button */
.database-step-wrapper :deep(.v-card-actions) {
  justify-content: center;
  padding: 24px;
}

.database-step-wrapper :deep(.v-btn[data-test="test-connection-btn"]) {
  background-color: rgba(33, 150, 243, 0.12) !important;
  border: 2px solid rgba(33, 150, 243, 0.5) !important;
  color: rgb(var(--v-theme-primary)) !important;
  font-weight: 600;
  min-width: 180px;
}

.database-step-wrapper :deep(.v-btn[data-test="test-connection-btn"]:hover) {
  background-color: rgba(33, 150, 243, 0.2) !important;
  border-color: rgba(33, 150, 243, 0.7) !important;
}
</style>
