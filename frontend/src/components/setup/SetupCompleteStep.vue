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
    <v-card v-if="isLanMode" variant="outlined" class="mb-6">
      <v-card-text class="d-flex align-center">
        <v-icon color="success" class="mr-3">mdi-check-circle</v-icon>
        <div class="flex-grow-1">
          <div class="text-subtitle-1 font-weight-medium">Network: Configured for LAN access</div>
          <div class="text-caption text-medium-emphasis">Server: {{ detectedServerUrl }}</div>
          <div v-if="isLanMode" class="text-caption text-medium-emphasis">
            Admin: {{ config.adminUsername }}
          </div>
          <div v-if="isLanMode" class="mt-2">
            <v-btn size="small" @click="copyUrl" variant="tonal" color="primary">
              Copy Server URL
              <v-icon end>mdi-content-copy</v-icon>
            </v-btn>
            <v-snackbar
              v-model="showCopyConfirmation"
              timeout="2000"
              location="top right"
              color="success"
            >
              Server URL copied to clipboard!
            </v-snackbar>
          </div>
        </div>
      </v-card-text>
    </v-card>

    <!-- Localhost Mode: Next Steps -->
    <v-alert v-if="!isLanMode" type="info" variant="tonal" class="mb-6">
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

    <!-- LAN Mode: Admin Credentials & Next Steps -->
    <div v-if="isLanMode">
      <!-- Admin Credentials Display -->
      <v-card variant="outlined" class="mb-4">
        <v-card-title class="bg-surface-variant">
          <v-icon start>mdi-account-key</v-icon>
          Administrator Credentials
        </v-card-title>
        <v-card-text>
          <v-row>
            <v-col cols="12" md="6">
              <v-text-field
                :model-value="config.adminUsername || 'admin'"
                label="Admin Username"
                variant="outlined"
                readonly
                density="compact"
                aria-label="Administrator username"
              />
            </v-col>
            <v-col cols="12" md="6">
              <v-text-field
                :model-value="showPassword ? config.adminPassword || '' : '••••••••'"
                label="Admin Password"
                variant="outlined"
                readonly
                density="compact"
                :type="showPassword ? 'text' : 'password'"
                aria-label="Administrator password"
              >
                <template #append-inner>
                  <v-btn
                    :icon="showPassword ? 'mdi-eye-off' : 'mdi-eye'"
                    variant="text"
                    density="compact"
                    @click="showPassword = !showPassword"
                    aria-label="Toggle password visibility"
                  />
                </template>
              </v-text-field>
            </v-col>
          </v-row>
          <v-alert type="warning" variant="tonal" density="compact" class="mt-2">
            <v-icon start size="small">mdi-shield-lock</v-icon>
            Save these credentials securely. You will need them to access the dashboard.
          </v-alert>
        </v-card-text>
      </v-card>

      <!-- Team Access URLs -->
      <v-card variant="outlined" class="mb-4">
        <v-card-title class="bg-surface-variant">
          <v-icon start>mdi-web</v-icon>
          Team Access URLs
        </v-card-title>
        <v-card-text>
          <div class="mb-3">
            <div class="text-caption text-medium-emphasis mb-1">API Server</div>
            <div class="d-flex align-center">
              <code class="flex-grow-1 mr-2">{{ detectedServerUrl }}</code>
              <v-btn
                icon="mdi-content-copy"
                size="small"
                variant="text"
                @click="copyUrl"
                aria-label="Copy API server URL"
              />
            </div>
          </div>
          <div>
            <div class="text-caption text-medium-emphasis mb-1">Dashboard</div>
            <div class="d-flex align-center">
              <code class="flex-grow-1 mr-2">{{
                detectedServerUrl.replace(':7272', ':7274')
              }}</code>
              <v-btn
                icon="mdi-content-copy"
                size="small"
                variant="text"
                @click="copyDashboardUrl"
                aria-label="Copy dashboard URL"
              />
            </div>
          </div>
        </v-card-text>
      </v-card>

      <!-- LAN Next Steps -->
      <v-alert type="info" variant="tonal" class="mb-6">
        <div class="text-subtitle-1 mb-2">
          <strong>Next Steps:</strong>
        </div>
        <ol class="pl-4 mb-0">
          <li>Add MCP configuration to Claude Code CLI (see instructions in Attach Tools step)</li>
          <li>Restart Claude Code CLI and verify with <code>/mcp</code> command</li>
          <li>
            Login at <code>{{ detectedServerUrl.replace(':7272', ':7274') }}</code> with admin
            credentials
          </li>
          <li>Invite team members via Settings → Users (they will need their own API keys)</li>
          <li>Share the dashboard URL with your team for access</li>
        </ol>
      </v-alert>
    </div>

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
        v-if="!isLanMode"
        color="primary"
        size="large"
        @click="$emit('finish')"
        aria-label="Finish setup and close wizard"
      >
        <span class="text-white">Finish & Close Wizard</span>
        <v-icon end color="white">mdi-check</v-icon>
      </v-btn>
      <v-btn
        v-else
        color="primary"
        size="large"
        @click="$emit('finish')"
        aria-label="Finish setup and restart services"
      >
        <span class="text-white">Finish & Restart Services</span>
        <v-icon end color="white">mdi-restart</v-icon>
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

// Ref to store detected IP
const detectedServerUrl = ref('http://localhost:7272')

// IP detection on component mount
onMounted(async () => {
  try {
    // Use the IP the user entered in NetworkConfigStep
    // Config structure: props.config.serverIp (not nested in lanSettings)
    const serverIp = props.config.serverIp || 'localhost'
    const serverPort = 7272

    // Update server URL based on deployment mode
    detectedServerUrl.value =
      props.config.deploymentMode === 'lan'
        ? `http://${serverIp}:${serverPort}`
        : 'http://127.0.0.1:7272'

    console.log('[COMPLETE_STEP] Server IP:', serverIp)
    console.log('[COMPLETE_STEP] Deployment mode:', props.config.deploymentMode)
    console.log('[COMPLETE_STEP] Serena enabled:', props.config.serenaEnabled)
  } catch (error) {
    console.error('IP detection failed:', error)
    // Fallback to default localhost
    detectedServerUrl.value = 'http://127.0.0.1:7272'
  }
})

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

const serenaEnabled = computed(() => {
  return props.config.serenaEnabled || false
})

const showCopyConfirmation = ref(false)
const showPassword = ref(false)

const copyUrl = () => {
  try {
    navigator.clipboard.writeText(detectedServerUrl.value).then(() => {
      showCopyConfirmation.value = true
    })
  } catch (err) {
    console.error('Failed to copy URL:', err)
  }
}

const copyDashboardUrl = () => {
  const dashboardUrl = detectedServerUrl.value.replace(':7272', ':7274')
  try {
    navigator.clipboard.writeText(dashboardUrl).then(() => {
      showCopyConfirmation.value = true
    })
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
