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

    <!-- Serena MCP Status -->
    <v-card variant="outlined" class="mb-3">
      <v-card-text class="d-flex align-center">
        <v-icon :color="serenaEnabled ? 'success' : 'grey'" class="mr-3">
          {{ serenaEnabled ? 'mdi-check-circle' : 'mdi-circle-outline' }}
        </v-icon>
        <div class="flex-grow-1">
          <div class="text-subtitle-1 font-weight-medium">
            Serena: {{ serenaEnabled ? 'Enabled' : 'Not enabled' }}
          </div>
          <div class="text-caption text-medium-emphasis">
            {{
              serenaEnabled
                ? 'Agent prompts include Serena MCP instructions'
                : 'You can enable this later in Settings'
            }}
          </div>
        </div>
      </v-card-text>
    </v-card>

    <!-- Next Steps -->
    <v-alert type="info" variant="tonal" class="mb-6">
      <div class="text-subtitle-1 mb-2">
        <strong>Next Steps:</strong>
      </div>
      <ol class="pl-4 mb-0">
        <li v-if="hasTools">Relaunch Claude Code CLI to load MCP configuration</li>
        <li v-if="hasTools">Type <code>/mcp</code> to verify giljo-mcp tools are loaded</li>
        <li>
          Access dashboard at <code>{{ detectedServerUrl.replace(':7272', ':7274') }}</code>
        </li>
        <li>Create your first project and start orchestrating agents</li>
      </ol>
    </v-alert>

    <!-- Progress (100%) -->
    <v-card variant="outlined" class="mb-6">
      <v-card-text>
        <div class="d-flex justify-space-between mb-2">
          <span class="text-caption">Progress: Step 5 of 5</span>
          <span class="text-caption">100%</span>
        </div>
        <v-progress-linear :model-value="100" color="warning" />
      </v-card-text>
    </v-card>

    <!-- Navigation -->
    <div class="d-flex justify-space-between">
      <v-btn
        variant="outlined"
        @click="$emit('back')"
        aria-label="Go back to network configuration"
      >
        <v-icon start>mdi-arrow-left</v-icon>
        Back
      </v-btn>
      <v-btn
        color="primary"
        size="large"
        @click="$emit('finish')"
        aria-label="Finish setup and close wizard"
      >
        <span class="text-white">Finish & Close Wizard</span>
        <v-icon end color="white">mdi-check</v-icon>
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

import { ref, onMounted } from 'vue'
import SetupService from '@/services/setupService'

const props = defineProps({
  config: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['finish', 'back'])

// v3.0 Unified: Default to current host
const detectedServerUrl = ref(`${window.location.protocol}//${window.location.hostname}:7272`)

// Lifecycle
onMounted(async () => {
  try {
    // v3.0 Unified: Use current host (already set in ref default)
    console.log('[COMPLETE_STEP] Setup complete, server URL:', detectedServerUrl.value)
    console.log('[COMPLETE_STEP] Serena enabled:', props.config.serenaEnabled)
  } catch (error) {
    console.error('Setup completion error:', error)
    // Fallback already handled by ref default
  }
})

// Computed
const isLanMode = computed(() => false)

const deploymentModeLabel = computed(() => 'Localhost')

const deploymentModeDescription = computed(() => 'Single-user mode on this computer (127.0.0.1)')

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

const serenaEnabled = computed(() => {
  return props.config.serenaEnabled || false
})

const copyDashboardUrl = () => {
  const dashboardUrl = detectedServerUrl.value.replace(':7272', ':7274')
  try {
    navigator.clipboard.writeText(dashboardUrl)
  } catch (err) {
    console.error('Failed to copy dashboard URL:', err)
  }
}
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
