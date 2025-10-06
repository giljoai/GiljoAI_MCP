<template>
  <v-card-text class="pa-8">
    <h2 class="text-h5 mb-6">Database Connection</h2>

    <!-- Reusable Database Connection Component -->
    <DatabaseConnection
      :readonly="true"
      :show-test-button="true"
      :show-title="false"
      :show-info-banner="true"
      info-banner-text="Database settings are configured during installation. This step verifies connectivity."
      @connection-success="handleConnectionSuccess"
      @connection-error="handleConnectionFailure"
    />

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
      </p>
    </div>

    <!-- Progress -->
    <v-card variant="outlined" class="mt-6 mb-6">
      <v-card-text>
        <div class="d-flex justify-space-between mb-2">
          <span class="text-caption">Progress: Step 2 of 7</span>
          <span class="text-caption">29%</span>
        </div>
        <v-progress-linear :model-value="29" color="primary" />
      </v-card-text>
    </v-card>

    <!-- Navigation buttons -->
    <div class="d-flex justify-space-between">
      <v-btn
        variant="outlined"
        @click="$emit('back')"
        aria-label="Go back to welcome"
      >
        <v-icon start>mdi-arrow-left</v-icon>
        Back
      </v-btn>
      <v-btn
        color="primary"
        :disabled="!connectionVerified"
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
</style>
