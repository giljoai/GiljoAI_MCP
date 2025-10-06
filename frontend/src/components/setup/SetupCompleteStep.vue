<template>
  <v-card-text class="pa-8">
    <!-- Success Header -->
    <div class="text-center mb-6">
      <v-icon color="success" size="80">mdi-check-circle</v-icon>
      <h2 class="text-h4 mt-4">Setup Complete!</h2>
      <p class="text-h6 text-medium-emphasis mt-2">
        GiljoAI MCP is ready to orchestrate your coding agents
      </p>
    </div>

    <!-- Configuration Summary -->
    <h3 class="text-h6 mb-4">Configuration Summary:</h3>

    <!-- Database Status -->
    <v-card variant="outlined" class="mb-3">
      <v-card-text class="d-flex align-center">
        <v-icon color="success" class="mr-3">mdi-check-circle</v-icon>
        <div class="flex-grow-1">
          <div class="text-subtitle-1 font-weight-medium">Database: Connected</div>
          <div class="text-caption text-medium-emphasis">
            PostgreSQL configured via CLI installer
          </div>
        </div>
      </v-card-text>
    </v-card>

    <!-- AI Tools Status -->
    <v-card variant="outlined" class="mb-3">
      <v-card-text class="d-flex align-center">
        <v-icon :color="hasTools ? 'success' : 'info'" class="mr-3">
          {{ hasTools ? 'mdi-check-circle' : 'mdi-information' }}
        </v-icon>
        <div class="flex-grow-1">
          <div class="text-subtitle-1 font-weight-medium">AI Tools: {{ toolCount }} configured</div>
          <div v-if="toolNames.length > 0" class="text-caption text-medium-emphasis">
            {{ toolNames.join(', ') }}
          </div>
          <div v-else class="text-caption text-medium-emphasis">
            No tools configured yet (can be added in Settings)
          </div>
        </div>
      </v-card-text>
    </v-card>

    <!-- Deployment Mode -->
    <v-card variant="outlined" class="mb-3">
      <v-card-text class="d-flex align-center">
        <v-icon color="success" class="mr-3">mdi-check-circle</v-icon>
        <div class="flex-grow-1">
          <div class="text-subtitle-1 font-weight-medium">
            Deployment: {{ deploymentModeLabel }}
          </div>
          <div class="text-caption text-medium-emphasis">
            {{ deploymentModeDescription }}
          </div>
        </div>
      </v-card-text>
    </v-card>

    <!-- LAN Settings (if LAN mode) -->
    <v-card v-if="isLanMode && config.lanSettings" variant="outlined" class="mb-6">
      <v-card-text class="d-flex align-center">
        <v-icon color="success" class="mr-3">mdi-check-circle</v-icon>
        <div class="flex-grow-1">
          <div class="text-subtitle-1 font-weight-medium">Network: Configured for LAN access</div>
          <div class="text-caption text-medium-emphasis">
            Server: http://{{ config.lanSettings.serverIp }}:{{ config.lanSettings.port }}
          </div>
          <div class="text-caption text-medium-emphasis">
            Admin: {{ config.lanSettings.adminUsername }}
          </div>
        </div>
      </v-card-text>
    </v-card>

    <!-- Next Steps -->
    <v-alert type="info" variant="tonal" class="mb-6">
      <div class="text-subtitle-1 mb-2">
        <strong>Next Steps:</strong>
      </div>
      <ul class="pl-4 mb-0">
        <li v-if="hasTools">
          Relaunch Claude Code CLI and type <code>/mcp</code> to verify attachment
        </li>
        <li>Create your first project from the dashboard</li>
        <li>Explore agent templates and customize missions</li>
        <li v-if="isLanMode">Share the server URL with your team members</li>
        <li v-else>Configure additional AI tools in Settings if needed</li>
      </ul>
    </v-alert>

    <!-- Progress (100%) -->
    <v-card variant="outlined" class="mb-6">
      <v-card-text>
        <div class="d-flex justify-space-between mb-2">
          <span class="text-caption">Progress: Step 3 of 3</span>
          <span class="text-caption">100%</span>
        </div>
        <v-progress-linear :model-value="100" color="success" />
      </v-card-text>
    </v-card>

    <!-- Finish Button -->
    <div class="text-center">
      <v-btn color="primary" size="large" @click="$emit('finish')" aria-label="Go to dashboard">
        Go to Dashboard
        <v-icon end>mdi-arrow-right</v-icon>
      </v-btn>
    </div>
  </v-card-text>
</template>

<script setup>
import { computed } from 'vue'

/**
 * SetupCompleteStep - Final setup completion step (Step 3 of 3)
 *
 * Displays configuration summary and provides navigation to dashboard
 */

const props = defineProps({
  config: {
    type: Object,
    required: true,
  },
})

defineEmits(['finish'])

// Computed
const isLanMode = computed(() => props.config.deploymentMode === 'lan')

const deploymentModeLabel = computed(() => {
  const modes = {
    localhost: 'Localhost',
    lan: 'LAN (Local Network)',
  }
  return modes[props.config.deploymentMode] || 'Localhost'
})

const deploymentModeDescription = computed(() => {
  const descriptions = {
    localhost: 'Single-user mode on this computer (127.0.0.1)',
    lan: 'Multi-user mode accessible on local network',
  }
  return descriptions[props.config.deploymentMode] || ''
})

const hasTools = computed(() => {
  return props.config.aiTools && props.config.aiTools.length > 0
})

const toolCount = computed(() => {
  return props.config.aiTools?.length || 0
})

const toolNames = computed(() => {
  if (!props.config.aiTools || props.config.aiTools.length === 0) {
    return []
  }
  return props.config.aiTools.map((tool) => tool.name)
})
</script>

<style scoped>
h2 {
  color: rgb(var(--v-theme-success));
}

h3 {
  color: rgb(var(--v-theme-primary));
}

ul {
  line-height: 1.8;
}

code {
  background-color: rgba(var(--v-theme-surface-variant), 0.5);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
}
</style>
