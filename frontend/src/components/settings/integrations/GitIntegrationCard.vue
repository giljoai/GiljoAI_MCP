<template>
  <v-card variant="outlined" class="mb-4">
    <v-card-text>
      <div class="d-flex align-center mb-3">
        <v-icon size="40" class="mr-2" color="white">mdi-github</v-icon>
        <div class="flex-grow-1">
          <div class="d-flex align-center">
            <h3 class="text-h6 mb-0 mr-2">Git + GiljoAI 360 Memory</h3>
            <v-tooltip location="top" max-width="400">
              <template #activator="{ props }">
                <v-icon v-bind="props" size="small" color="medium-emphasis"
                  >mdi-help-circle-outline</v-icon
                >
              </template>
              <div>
                <strong>Cumulative product knowledge tracking</strong>
                <p class="mt-2 mb-0">
                  When enabled, GiljoAI captures git commit history at project closeout and stores
                  it in 360 Memory. This provides orchestrators with cumulative context across all
                  projects, including what was built, decisions made, and implementation patterns
                  used.
                </p>
                <p class="mt-2 mb-0 text-caption">
                  <strong>Note:</strong> Git must be configured on your system with access to your
                  repositories. 360 Memory is always added to the project.
                </p>
              </div>
            </v-tooltip>
          </div>
        </div>
      </div>

      <p class="text-body-2 text-medium-emphasis mb-3">
        Enable to automatically include git commit history in project summaries.
      </p>

      <div class="d-flex align-center mb-3">
        <v-btn
          variant="text"
          size="small"
          color="light-blue"
          href="https://docs.github.com/en/get-started/quickstart/set-up-git"
          target="_blank"
        >
          <v-icon start>mdi-book-open-variant</v-icon>
          GitHub Setup Guide
        </v-btn>
      </div>

      <!-- Git Integration Controls -->
      <v-card variant="tonal" class="mb-0">
        <v-card-text class="pa-3">
          <div class="d-flex align-center justify-between">
            <div class="flex-grow-1 d-flex align-center">
              <div class="text-subtitle-2 font-weight-medium mr-4">Enable Git Integration</div>
              <v-switch
                :model-value="enabled"
                :loading="loading"
                hide-details
                density="compact"
                data-testid="github-integration-toggle"
                class="git-toggle-inline"
                @update:model-value="$emit('update:enabled', $event)"
              />
            </div>
          </div>
        </v-card-text>
      </v-card>

      <v-alert type="info" variant="tonal" density="compact" class="mt-4">
        <div class="text-body-2">
          Git configuration is your responsibility on your local system.
        </div>
      </v-alert>
    </v-card-text>
  </v-card>
</template>

<script setup>
defineProps({
  enabled: {
    type: Boolean,
    default: false,
  },
  loading: {
    type: Boolean,
    default: false,
  },
})

defineEmits(['update:enabled'])
</script>

<style scoped>
/* Make Git toggle inline */
.git-toggle-inline {
  flex: 0 0 auto;
}
</style>
