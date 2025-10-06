<template>
  <v-card-text class="pa-8">
    <!-- Welcome message -->
    <h1 class="text-h4 text-center mb-2">Welcome to GiljoAI MCP</h1>
    <p class="text-h6 text-center text-medium-emphasis mb-8">Multi-Agent Coding Orchestrator</p>

    <!-- Checklist -->
    <v-card variant="tonal" class="mb-6">
      <v-card-text>
        <p class="text-subtitle-1 mb-4">This wizard will help you:</p>
        <v-list density="compact" class="bg-transparent">
          <v-list-item
            prepend-icon="mdi-check-circle"
            title="Verify PostgreSQL database connection"
          />
          <v-list-item prepend-icon="mdi-check-circle" title="Choose your deployment mode" />
          <v-list-item prepend-icon="mdi-check-circle" title="Configure AI tool integration" />
          <v-list-item prepend-icon="mdi-check-circle" title="Complete initial system setup" />
        </v-list>
        <p class="text-caption mt-4">
          <v-icon size="small" class="mr-1">mdi-clock-outline</v-icon>
          Estimated time: 5-10 minutes
        </p>
      </v-card-text>
    </v-card>

    <!-- Progress -->
    <v-card variant="outlined" class="mb-6">
      <v-card-text>
        <div class="d-flex justify-space-between mb-2">
          <span class="text-caption">Progress: Step 1 of 7</span>
          <span class="text-caption">14%</span>
        </div>
        <v-progress-linear :model-value="14" color="primary" />
      </v-card-text>
    </v-card>

    <!-- Action buttons -->
    <div class="text-center">
      <v-btn
        color="primary"
        size="large"
        @click="$emit('next')"
        aria-label="Get started with setup wizard"
      >
        Get Started
        <v-icon end>mdi-arrow-right</v-icon>
      </v-btn>
    </div>
  </v-card-text>
</template>

<script setup>
/**
 * WelcomeStep - First step of setup wizard
 *
 * Displays welcome message and overview of wizard steps
 */

defineEmits(['next'])
</script>

<style scoped>
h1 {
  color: rgb(var(--v-theme-primary));
}
</style>
