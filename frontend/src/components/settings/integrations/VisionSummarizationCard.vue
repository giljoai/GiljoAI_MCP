<template>
  <v-card class="mb-4" variant="outlined">
    <v-card-title class="d-flex align-center">
      <v-icon start color="primary">mdi-text-box-multiple</v-icon>
      Vision Summarization (Sumy LSA)
    </v-card-title>
    <v-card-subtitle>
      Compress large vision documents at upload time using Sumy LSA extraction
    </v-card-subtitle>
    <v-card-text>
      <v-alert type="info" variant="tonal" density="compact" class="mb-3">
        When enabled, vision documents are automatically summarized to reduce token usage while preserving key information.
      </v-alert>

      <v-switch
        :model-value="enabled"
        @update:model-value="$emit('update:enabled', $event)"
        :loading="loading"
        :disabled="loading"
        label="Enable vision summarization at upload"
        color="primary"
        hide-details
        data-testid="vision-summarization-toggle"
      />
    </v-card-text>
  </v-card>
</template>

<script setup>
defineProps({
  enabled: {
    type: Boolean,
    required: true
  },
  loading: {
    type: Boolean,
    default: false
  }
})

defineEmits(['update:enabled'])
</script>
