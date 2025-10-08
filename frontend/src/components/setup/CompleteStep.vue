<template>
  <v-card-text class="pa-8">
    <!-- Success header -->
    <div class="text-center mb-6">
      <v-icon color="success" size="80">mdi-check-circle</v-icon>
      <h2 class="text-h4 mt-4">Setup Complete! [DEBUG]</h2>
      <p class="text-h6 text-medium-emphasis mt-2">GiljoAI MCP is ready to use</p>
    </div>

    <!-- Configuration Summary -->
    <h3 class="text-h6 mb-4">Your Configuration Summary:</h3>

    <!-- System Status -->
    <v-card variant="outlined" class="mb-3">
      <v-card-text class="d-flex align-center">
        <v-icon color="success" class="mr-3">mdi-check-circle</v-icon>
        <div class="flex-grow-1">
          <div class="text-subtitle-1 font-weight-medium">Database: Connected</div>
          <div class="text-caption text-medium-emphasis">PostgreSQL on localhost:5432</div>
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

    <!-- Admin Account (if LAN mode) -->
    <v-card v-if="isLanMode && config.adminAccount" variant="outlined" class="mb-3">
      <v-card-text class="d-flex align-center">
        <v-icon color="success" class="mr-3">mdi-check-circle</v-icon>
        <div class="flex-grow-1">
          <div class="text-subtitle-1 font-weight-medium">
            Admin Account: {{ config.adminAccount.username }}
          </div>
          <div v-if="config.adminAccount.email" class="text-caption text-medium-emphasis">
            {{ config.adminAccount.email }}
          </div>
        </div>
      </v-card-text>
    </v-card>

    <!-- AI Tools -->
    <v-card variant="outlined" class="mb-3">
      <v-card-text class="d-flex align-center">
        <v-icon color="success" class="mr-3">mdi-check-circle</v-icon>
        <div class="flex-grow-1">
          <div class="text-subtitle-1 font-weight-medium">AI Tools: {{ toolCount }} configured</div>
          <div v-if="toolNames.length > 0" class="text-caption text-medium-emphasis">
            {{ toolNames.join(', ') }}
          </div>
          <div v-else class="text-caption text-medium-emphasis">
            No tools configured (can be added later in Settings)
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
          <div class="text-caption text-error">
            DEBUG: serverIp from prop = {{ config.lanSettings?.serverIp }}
          </div>
          <div class="text-caption text-error">
            DEBUG: Full lanSettings = {{ JSON.stringify(config.lanSettings) }}
          </div>
          <div v-if="config.lanSettings.hostname" class="text-caption text-medium-emphasis">
            Hostname: {{ config.lanSettings.hostname }}
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
        <li>Create your first project</li>
        <li>Explore agent templates</li>
        <li v-if="isLanMode">Share access URL with team members</li>
        <li v-else>Configure additional AI tools in Settings</li>
        <li>Review documentation to learn more</li>
      </ul>
    </v-alert>

    <!-- Progress (100%) -->
    <v-card variant="outlined" class="mb-6">
      <v-card-text>
        <div class="d-flex justify-space-between mb-2">
          <span class="text-caption">
            Progress: Step {{ isLanMode ? '7' : '5' }} of {{ isLanMode ? '7' : '5' }}
          </span>
          <span class="text-caption">100%</span>
        </div>
        <v-progress-linear :model-value="100" color="success" />
      </v-card-text>
    </v-card>

    <!-- Finish button -->
    <div class="text-center">
      <v-btn color="primary" size="large" @click="$emit('finish')" aria-label="Go to dashboard">
        Go to Dashboard
        <v-icon end>mdi-arrow-right</v-icon>
      </v-btn>
    </div>
  </v-card-text>
</template>

<script setup>
import { computed, watch } from 'vue'

/**
 * CompleteStep - Final setup completion step
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

// DEBUG: Log what IP we're actually receiving
watch(
  () => props.config.lanSettings,
  (newSettings) => {
    console.error('[COMPLETE_STEP] ===== lanSettings changed:', newSettings)
    if (newSettings) {
      console.error('[COMPLETE_STEP] ===== serverIp:', newSettings.serverIp)
      console.error('[COMPLETE_STEP] ===== Full object:', JSON.stringify(newSettings, null, 2))
    }
  },
  { immediate: true, deep: true },
)

console.error('[COMPLETE_STEP] ===== Component loaded!')

// Computed
const isLanMode = computed(() => props.config.deploymentMode === 'lan')

const deploymentModeLabel = computed(() => {
  const modes = {
    localhost: 'Localhost',
    lan: 'LAN (Local Area Network)',
    wan: 'WAN (Wide Area Network)',
  }
  return modes[props.config.deploymentMode] || 'Unknown'
})

const deploymentModeDescription = computed(() => {
  const descriptions = {
    localhost: 'Single-user mode on this computer',
    lan: 'Team access on local network',
    wan: 'Internet access for remote teams',
  }
  return descriptions[props.config.deploymentMode] || ''
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
</style>
