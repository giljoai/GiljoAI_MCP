<template>
  <v-card variant="outlined" class="mb-4">
    <v-card-text>
      <div class="d-flex align-center mb-3">
        <v-avatar size="40" rounded="0" class="mr-2" color="grey-darken-2">
          <v-icon size="28" color="white">mdi-github</v-icon>
        </v-avatar>
        <div class="flex-grow-1">
          <div class="d-flex align-center">
            <h3 class="text-h6 mb-0 mr-2">Git + 360 Memory</h3>
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
                  repositories.
                </p>
              </div>
            </v-tooltip>
          </div>
          <p class="text-caption text-medium-emphasis mb-0">
            Track git commits in 360 Memory for orchestrator context
          </p>
        </div>
      </div>

      <p class="text-body-2 text-medium-emphasis mb-3">
        Enable to automatically include git commit history in project summaries. Commits are stored
        in product memory for future orchestrator reference.
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
                @update:model-value="$emit('update:enabled', $event)"
                :loading="loading"
                hide-details
                density="compact"
                class="git-toggle-inline"
              />
            </div>
            <v-btn
              color="primary"
              variant="flat"
              size="small"
              width="120"
              @click="$emit('openAdvanced')"
              :disabled="loading"
            >
              Advanced
            </v-btn>
          </div>
        </v-card-text>
      </v-card>
    </v-card-text>
  </v-card>
</template>

<script setup>
defineProps({
  enabled: {
    type: Boolean,
    default: false,
  },
  config: {
    type: Object,
    default: () => ({
      use_in_prompts: false,
      include_commit_history: true,
      max_commits: 50,
      branch_strategy: 'main',
    }),
  },
  loading: {
    type: Boolean,
    default: false,
  },
})

defineEmits(['update:enabled', 'openAdvanced'])
</script>

<style scoped>
/* Make Git toggle inline */
.git-toggle-inline {
  flex: 0 0 auto;
}
</style>
