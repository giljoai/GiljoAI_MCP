<template>
  <div
    class="intg-card smooth-border"
    style="--card-accent: #90CAF9"
  >
    <div class="intg-card-icon" style="background: rgba(144,202,249,0.12); color: #90CAF9">
      <v-icon size="20">mdi-git</v-icon>
    </div>
    <div class="d-flex align-center" style="gap: 8px; margin-bottom: 5px;">
      <div class="intg-card-title" style="margin-bottom: 0">Git + 360 Memory</div>
      <v-tooltip location="top" max-width="400">
        <template #activator="{ props }">
          <v-icon v-bind="props" size="small" style="color: #8895a8">mdi-help-circle-outline</v-icon>
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
    <div class="intg-card-desc">Automatically include git commit history in project summaries.</div>

    <div class="intg-card-body d-flex flex-column align-center">
      <v-btn
        :color="enabled ? 'success' : 'primary'"
        :variant="enabled ? 'flat' : 'outlined'"
        size="small"
        :loading="loading"
        data-testid="github-integration-toggle"
        class="intg-toggle-pill"
        @click="$emit('update:enabled', !enabled)"
      >
        <v-icon v-if="enabled" start size="16">mdi-check</v-icon>
        {{ enabled ? 'Enabled' : 'Disabled' }}
      </v-btn>
      <v-btn
        variant="text"
        size="small"
        color="light-blue"
        href="https://docs.github.com/en/get-started/quickstart/set-up-git"
        target="_blank"
        class="mt-2"
      >
        <v-icon start>mdi-book-open-variant</v-icon>
        GitHub Setup Guide
      </v-btn>
    </div>
  </div>
</template>

<script setup>
defineProps({
  enabled: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
})

defineEmits(['update:enabled'])
</script>

<style lang="scss" scoped>
@import '../../../styles/intg-card';
</style>
