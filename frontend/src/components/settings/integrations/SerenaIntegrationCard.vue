<template>
  <v-card variant="outlined" class="mb-4">
    <v-card-text>
      <div class="d-flex align-center mb-3">
        <v-avatar size="40" rounded="0" class="mr-2">
          <v-img src="/Serena.png" alt="Serena MCP" />
        </v-avatar>
        <div class="flex-grow-1">
          <div class="d-flex align-center">
            <h3 class="text-h6 mb-0 mr-2">Serena MCP</h3>
            <v-tooltip location="top" max-width="400">
              <template #activator="{ props }">
                <v-icon v-bind="props" size="small" color="medium-emphasis"
                  >mdi-help-circle-outline</v-icon
                >
              </template>
              <div>
                <strong>Intelligent codebase understanding and navigation</strong>
                <p class="mt-2 mb-0">
                  Serena provides deep semantic code analysis, intelligent symbol navigation, and
                  contextual understanding of your codebase. It enables agents to efficiently
                  explore and understand project structure without reading unnecessary code,
                  significantly improving performance and reducing token usage.
                </p>
                <p class="mt-2 mb-0 text-caption">
                  <strong>Note:</strong> Serena must be installed separately in your AI coding agent.
                </p>
              </div>
            </v-tooltip>
          </div>
        </div>
      </div>
      <p class="text-body-2 text-medium-emphasis mb-4">
        Add Serena MCP tool instructions to agent prompts.
      </p>

      <div class="d-flex align-center mb-3">
        <v-btn
          variant="text"
          size="small"
          color="light-blue"
          href="https://github.com/oraios/serena"
          target="_blank"
        >
          <v-icon start>mdi-github</v-icon>
          GitHub Repository
        </v-btn>
        <span class="text-caption text-medium-emphasis ml-3"> Credit: Oraios </span>
      </div>

      <!-- Serena Controls (Handover 0277: Simplified to toggle only) -->
      <v-card variant="tonal" class="mb-0">
        <v-card-text class="pa-3">
          <div class="d-flex align-center">
            <div class="text-subtitle-2 font-weight-medium mr-4">Enable Serena MCP</div>
            <v-switch
              :model-value="enabled"
              :loading="loading"
              hide-details
              density="compact"
              class="serena-toggle-inline"
              @update:model-value="$emit('update:enabled', $event)"
            />
          </div>
        </v-card-text>
      </v-card>
    </v-card-text>
  </v-card>
</template>

<script setup>
// Handover 0277: Simplified to single toggle only (advanced settings removed)
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
/* Make Serena toggle inline */
.serena-toggle-inline {
  flex: 0 0 auto;
}
</style>
