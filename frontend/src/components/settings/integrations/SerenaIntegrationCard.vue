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
                  <strong>Note:</strong> Serena must be installed separately in your AI coding tool.
                </p>
              </div>
            </v-tooltip>
          </div>
          <p class="text-caption text-medium-emphasis mb-0">
            Intelligent codebase understanding and navigation
          </p>
        </div>
      </div>

      <p class="text-body-2 text-medium-emphasis mb-3">
        Enabling adds Serena tool instructions to agent prompts. Disabling removes them from agent
        tool startup.
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

      <!-- Serena Controls -->
      <v-card variant="tonal" class="mb-0">
        <v-card-text class="pa-3">
          <div class="d-flex align-center justify-between">
            <div class="flex-grow-1 d-flex align-center">
              <div class="text-subtitle-2 font-weight-medium mr-4">Enable Serena MCP</div>
              <v-switch
                :model-value="enabled"
                @update:model-value="$emit('update:enabled', $event)"
                :loading="loading"
                hide-details
                density="compact"
                class="serena-toggle-inline"
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
      use_in_prompts: true,
      tailor_by_mission: true,
      dynamic_catalog: true,
      prefer_ranges: true,
      max_range_lines: 180,
      context_halo: 12,
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
/* Make Serena toggle inline */
.serena-toggle-inline {
  flex: 0 0 auto;
}
</style>
