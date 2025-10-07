<template>
  <v-card-text class="pa-8">
    <h2 class="text-h5 mb-2">Database Connection</h2>
    <p class="text-body-1 mb-6">
      Verify your PostgreSQL database connection
    </p>

    <!-- Advanced Configuration Warning -->
    <v-alert type="warning" variant="tonal" class="mb-6">
      <div class="text-center">
        <div class="text-subtitle-2 font-weight-medium mb-2">
          <v-icon color="warning" size="small" class="mr-2">mdi-lock</v-icon>
          Database Settings Locked
        </div>
        <div class="text-body-2 mb-3">
          Database configuration is managed by the installer. To modify database settings,
          re-run the installer:
        </div>
        <div class="mb-3">
          <code class="px-2 py-1">python installer/cli/install.py</code>
        </div>
        <div class="text-caption text-warning">
          <v-icon size="x-small" class="mr-1">mdi-alert</v-icon>
          <strong>Warning:</strong> Re-running the installer with different database settings
          will reset the application to factory defaults.
        </div>
      </div>
    </v-alert>

    <!-- Database Connection Component -->
    <div class="db-component-wrapper">
      <DatabaseConnection
        :readonly="true"
        :show-test-button="true"
        :show-title="false"
        :show-info-banner="false"
        :center-button="true"
        @connection-success="handleConnectionSuccess"
        @connection-error="handleConnectionFailure"
      />
    </div>

    <!-- Troubleshooting -->
    <v-alert type="info" variant="tonal" class="mt-4">
      <div class="text-body-2">
        <strong>Connection issues?</strong>
        <a @click="openTroubleshootingGuide" class="troubleshooting-link cursor-pointer ml-1">
          <v-icon size="small" class="mr-1">mdi-download</v-icon>
          Download troubleshooting guide
        </a>
        or verify PostgreSQL is running.
      </div>
    </v-alert>

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

    <!-- Navigation -->
    <div class="d-flex justify-end navigation-buttons">
      <v-btn
        color="primary"
        @click="$emit('next')"
        aria-label="Continue to attach tools"
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

defineEmits(['next'])

const connectionVerified = ref(false)

const handleConnectionSuccess = () => {
  connectionVerified.value = true
}

const handleConnectionFailure = () => {
  connectionVerified.value = false
}

const openTroubleshootingGuide = () => {
  // Download the troubleshooting guide as a markdown file
  const link = document.createElement('a')
  link.href = '/docs/troubleshooting/database.md'
  link.download = 'database-troubleshooting.md'
  link.click()
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

.cursor-pointer {
  cursor: pointer;
}

.troubleshooting-link {
  color: #ffc300 !important; /* Giljo yellow for maximum visibility */
  font-weight: 600;
}

.troubleshooting-link:hover {
  color: #ffffff !important; /* Pure white on hover */
  text-decoration: underline;
}

/* Isolate database component to prevent overflow/layering issues */
.db-component-wrapper {
  position: relative;
  z-index: 1;
  overflow: hidden;
}

/* Ensure navigation is on top and clickable */
.navigation-buttons {
  position: relative;
  z-index: 100;
  margin-top: 16px;
}

/* Force proper button styling */
.navigation-buttons .v-btn {
  pointer-events: all !important;
}

/* Don't override cursor on disabled buttons */
.navigation-buttons .v-btn:not(:disabled) {
  cursor: pointer !important;
}
</style>
