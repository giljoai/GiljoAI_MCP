<template>
  <v-card-text class="pa-8">
    <h2 class="text-h5 mb-2">Network Configuration</h2>
    <p class="text-body-1 mb-6">Configure how your team will access GiljoAI MCP</p>

    <!-- Mode Selection -->
    <v-radio-group v-model="selectedMode" class="mb-4">
      <v-row dense>
        <!-- Localhost Mode -->
        <v-col cols="12" md="4">
          <v-card
            variant="outlined"
            class="h-100 mode-card"
            :class="{ selected: selectedMode === 'localhost' }"
            @click="selectedMode = 'localhost'"
            role="button"
            tabindex="0"
            aria-label="Select localhost mode for single user"
          >
            <v-card-text class="pa-4">
              <v-radio value="localhost">
                <template #label>
                  <div class="ml-2">
                    <div class="text-h6 d-flex align-center">
                      <v-icon class="mr-2">mdi-laptop</v-icon>
                      Localhost
                    </div>
                    <div class="text-caption text-medium-emphasis">
                      (Recommended)
                    </div>
                  </div>
                </template>
              </v-radio>

              <v-list density="compact" class="mt-3 bg-transparent">
                <v-list-item
                  prepend-icon="mdi-check"
                  title="No network configuration"
                  class="text-caption"
                />
                <v-list-item
                  prepend-icon="mdi-check"
                  title="No authentication"
                  class="text-caption"
                />
                <v-list-item
                  prepend-icon="mdi-check"
                  title="Fastest performance"
                  class="text-caption"
                />
                <v-list-item
                  prepend-icon="mdi-check"
                  title="Most secure"
                  class="text-caption"
                />
              </v-list>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- LAN Mode -->
        <v-col cols="12" md="4">
          <v-card
            variant="outlined"
            class="h-100 mode-card"
            :class="{ selected: selectedMode === 'lan' }"
            @click="selectedMode = 'lan'"
            role="button"
            tabindex="0"
            aria-label="Select LAN mode for team access"
          >
            <v-card-text class="pa-4">
              <v-radio value="lan">
                <template #label>
                  <div class="ml-2">
                    <div class="text-h6 d-flex align-center">
                      <v-icon class="mr-2">mdi-network</v-icon>
                      LAN
                    </div>
                    <div class="text-caption text-medium-emphasis">
                      Team access on your network
                    </div>
                  </div>
                </template>
              </v-radio>

              <v-list density="compact" class="mt-3 bg-transparent">
                <v-list-item
                  prepend-icon="mdi-check"
                  title="Multiple users"
                  class="text-caption"
                />
                <v-list-item
                  prepend-icon="mdi-check"
                  title="Network configuration"
                  class="text-caption"
                />
                <v-list-item
                  prepend-icon="mdi-check"
                  title="Authentication enabled"
                  class="text-caption"
                />
                <v-list-item
                  prepend-icon="mdi-check"
                  title="Small teams (2-10)"
                  class="text-caption"
                />
              </v-list>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- WAN/Hosted Mode (Future) -->
        <v-col cols="12" md="4">
          <v-card
            variant="outlined"
            class="h-100 mode-card disabled-card"
            disabled
            aria-label="WAN/Hosted mode coming soon"
          >
            <v-card-text class="pa-4">
              <div class="d-flex align-center mb-1">
                <v-icon class="mr-2" color="disabled" size="large">mdi-cloud</v-icon>
                <div>
                  <div class="text-h6 text-disabled">
                    WAN/Hosted
                  </div>
                  <v-chip size="small" color="info" class="mt-1">Future</v-chip>
                </div>
              </div>

              <v-list density="compact" class="mt-3 bg-transparent">
                <v-list-item
                  prepend-icon="mdi-check"
                  title="Global internet access"
                  class="text-caption text-disabled"
                />
                <v-list-item
                  prepend-icon="mdi-check"
                  title="Cloud deployment"
                  class="text-caption text-disabled"
                />
                <v-list-item
                  prepend-icon="mdi-check"
                  title="Enterprise security"
                  class="text-caption text-disabled"
                />
                <v-list-item
                  prepend-icon="mdi-check"
                  title="Unlimited users"
                  class="text-caption text-disabled"
                />
              </v-list>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-radio-group>

    <!-- LAN Configuration Panel (Expandable) -->
    <v-expand-transition>
      <v-card v-if="selectedMode === 'lan'" variant="outlined" class="lan-config-panel mb-4">
        <v-card-title class="bg-surface-variant">
          <v-icon start>mdi-cog</v-icon>
          LAN Configuration
        </v-card-title>
        <v-card-text class="pt-4">
          <!-- Server IP -->
          <v-row>
            <v-col cols="12" md="8">
              <v-text-field
                v-model="lanConfig.serverIp"
                label="Server IP Address"
                variant="outlined"
                hint="The IP address of this computer on your network"
                persistent-hint
                :rules="[rules.required, rules.ipAddress]"
              />
            </v-col>
            <v-col cols="12" md="4" class="d-flex align-center">
              <v-btn
                variant="outlined"
                block
                :loading="detectingIp"
                @click="detectServerIp"
                aria-label="Auto-detect server IP address"
              >
                <v-icon start>mdi-auto-fix</v-icon>
                Auto-Detect
              </v-btn>
            </v-col>
          </v-row>

          <!-- Port -->
          <v-text-field
            v-model="lanConfig.port"
            label="API Port"
            variant="outlined"
            type="number"
            hint="Default: 7272"
            persistent-hint
            class="mb-4"
            :rules="[rules.required, rules.port]"
          />

          <!-- Admin Credentials -->
          <h3 class="text-h6 mb-3">Administrator Account</h3>

          <v-text-field
            v-model="lanConfig.adminUsername"
            label="Admin Username"
            variant="outlined"
            hint="Username for the administrator account"
            persistent-hint
            class="mb-4"
            :rules="[rules.required]"
          />

          <v-text-field
            v-model="lanConfig.adminPassword"
            label="Admin Password"
            variant="outlined"
            type="password"
            hint="Strong password for the administrator account"
            persistent-hint
            class="mb-4"
            :rules="[rules.required, rules.password]"
          />

          <!-- Firewall Configuration -->
          <h3 class="text-h6 mb-3">Firewall Configuration</h3>

          <v-checkbox
            v-model="lanConfig.firewallConfigured"
            label="I have configured my firewall to allow access on the API port"
            color="primary"
            hide-details
            class="mb-2"
          />

          <v-checkbox
            v-model="lanConfig.networkAccessible"
            label="This computer is accessible from other devices on my network"
            color="primary"
            hide-details
            class="mb-2"
          />

          <!-- Optional Hostname -->
          <v-text-field
            v-model="lanConfig.hostname"
            label="Custom Hostname (Optional)"
            variant="outlined"
            hint="Friendly name for this server (e.g., giljo-dev-server)"
            persistent-hint
            class="mt-4"
          />

          <!-- LAN Warning -->
          <v-alert type="warning" variant="tonal" class="mt-4">
            <v-icon start>mdi-shield-alert</v-icon>
            <strong>Security Notice:</strong> LAN mode enables network access with API key
            authentication. Ensure your network is trusted and secure.
          </v-alert>
        </v-card-text>
      </v-card>
    </v-expand-transition>

    <!-- Info Alert -->
    <v-alert type="info" variant="tonal" class="mb-6">
      You can change deployment mode later in Settings, but this may require service restart.
    </v-alert>

    <!-- Progress -->
    <v-card variant="outlined" class="mb-6">
      <v-card-text>
        <div class="d-flex justify-space-between mb-2">
          <span class="text-caption">Progress: Step 3 of 4</span>
          <span class="text-caption">75%</span>
        </div>
        <v-progress-linear :model-value="75" color="primary" />
      </v-card-text>
    </v-card>

    <!-- Navigation -->
    <div class="d-flex justify-space-between">
      <v-btn variant="outlined" @click="$emit('back')" aria-label="Go back to tool attachment">
        <v-icon start>mdi-arrow-left</v-icon>
        Back
      </v-btn>
      <v-btn
        color="primary"
        :disabled="!canProceed"
        @click="handleNext"
        aria-label="Continue to completion"
      >
        Continue
        <v-icon end>mdi-arrow-right</v-icon>
      </v-btn>
    </div>
  </v-card-text>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import setupService from '@/services/setupService'

/**
 * NetworkConfigStep - Network configuration step (Step 2 of 3)
 *
 * Allows user to choose between localhost and LAN modes
 */

const props = defineProps({
  mode: {
    type: String,
    required: true,
    validator: (value) => ['localhost', 'lan'].includes(value),
  },
  lanSettings: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['update:mode', 'update:lanSettings', 'next', 'back'])

// State
const selectedMode = ref(props.mode)
const detectingIp = ref(false)

const lanConfig = ref({
  serverIp: props.lanSettings?.serverIp || '',
  port: props.lanSettings?.port || 7272,
  adminUsername: props.lanSettings?.adminUsername || '',
  adminPassword: props.lanSettings?.adminPassword || '',
  firewallConfigured: props.lanSettings?.firewallConfigured || false,
  networkAccessible: props.lanSettings?.networkAccessible || false,
  hostname: props.lanSettings?.hostname || '',
})

// Validation rules
const rules = {
  required: (value) => !!value || 'This field is required',
  ipAddress: (value) => {
    if (!value) return true
    const ipPattern = /^(\d{1,3}\.){3}\d{1,3}$/
    return ipPattern.test(value) || 'Invalid IP address format'
  },
  port: (value) => {
    const port = parseInt(value)
    return (port >= 1 && port <= 65535) || 'Port must be between 1 and 65535'
  },
  password: (value) => {
    if (!value) return true
    return value.length >= 8 || 'Password must be at least 8 characters'
  },
}

// Computed
const canProceed = computed(() => {
  if (selectedMode.value === 'localhost') {
    return true
  }

  // For LAN mode, require all fields and checkboxes
  return !!(
    lanConfig.value.serverIp &&
    lanConfig.value.port &&
    lanConfig.value.adminUsername &&
    lanConfig.value.adminPassword &&
    lanConfig.value.adminPassword.length >= 8 &&
    lanConfig.value.firewallConfigured &&
    lanConfig.value.networkAccessible
  )
})

// Watch for mode changes
watch(selectedMode, (newMode) => {
  emit('update:mode', newMode)
})

// Watch for LAN config changes
watch(
  lanConfig,
  (newConfig) => {
    if (selectedMode.value === 'lan') {
      emit('update:lanSettings', { ...newConfig })
    }
  },
  { deep: true },
)

// Methods
const detectServerIp = async () => {
  detectingIp.value = true

  try {
    // Try backend endpoint first
    const response = await setupService.detectIp()

    if (response.local_ips && response.local_ips.length > 0) {
      lanConfig.value.serverIp = response.primary_ip
      lanConfig.value.hostname = response.hostname

      // If multiple IPs, log them (could show dropdown in future)
      if (response.local_ips.length > 1) {
        console.log('[NETWORK_CONFIG] Multiple IPs detected:', response.local_ips)
      }

      detectingIp.value = false
      return // Success
    }
  } catch (error) {
    console.warn('[NETWORK_CONFIG] Backend IP detection failed, using WebRTC fallback:', error)
  }

  // Fallback to existing WebRTC method
  try {
    const pc = new RTCPeerConnection({ iceServers: [] })
    pc.createDataChannel('')
    const offer = await pc.createOffer()
    await pc.setLocalDescription(offer)

    // Wait for ICE gathering
    await new Promise((resolve) => {
      pc.onicecandidate = (ice) => {
        if (!ice || !ice.candidate || !ice.candidate.candidate) {
          resolve()
          return
        }

        const candidateString = ice.candidate.candidate
        const ipMatch = candidateString.match(/([0-9]{1,3}\.){3}[0-9]{1,3}/)

        if (ipMatch) {
          const detectedIp = ipMatch[0]
          // Filter out localhost IPs
          if (detectedIp && !detectedIp.startsWith('127.')) {
            lanConfig.value.serverIp = detectedIp
            resolve()
          }
        }
      }
    })

    pc.close()
  } catch (error) {
    console.error('[NETWORK_CONFIG] WebRTC IP detection failed:', error)
    // Fallback to manual entry
  } finally {
    detectingIp.value = false
  }
}

const handleNext = () => {
  // Emit final configuration
  if (selectedMode.value === 'lan') {
    emit('update:lanSettings', { ...lanConfig.value })
  } else {
    emit('update:lanSettings', null)
  }

  console.log('[NETWORK_CONFIG] Moving to next step with mode:', selectedMode.value)
  emit('next')
}

// Lifecycle - load existing config
onMounted(async () => {
  console.log('[NETWORK_CONFIG] Loading existing configuration')
  
  try {
    const status = await setupService.checkStatus()
    console.log('[NETWORK_CONFIG] Current status:', status)
    
    // Set mode from existing config
    if (status.network_mode) {
      selectedMode.value = status.network_mode
      console.log('[NETWORK_CONFIG] Loaded mode:', status.network_mode)
    }
    
    // Load existing config from config.yaml
    const response = await fetch(`${setupService.baseURL}/api/v1/config`)
    if (response.ok) {
      const config = await response.json()
      console.log('[NETWORK_CONFIG] Loaded config:', config)
      
      // If LAN mode, populate fields from server config
      if (config.server) {
        lanConfig.value.serverIp = config.server.ip || lanConfig.value.serverIp
        lanConfig.value.hostname = config.server.hostname || lanConfig.value.hostname
        lanConfig.value.adminUsername = config.server.admin_user || lanConfig.value.adminUsername
        lanConfig.value.firewallConfigured = config.server.firewall_configured || false
        console.log('[NETWORK_CONFIG] Loaded LAN settings from config')
      }
      
      // Load API port if available
      if (config.services?.api?.port) {
        lanConfig.value.port = config.services.api.port
      }
    }
  } catch (error) {
    console.error('[NETWORK_CONFIG] Failed to load existing config:', error)
    // Non-fatal, continue with defaults
  }
})
</script>

<style scoped>
h2 {
  color: rgb(var(--v-theme-primary));
}

.mode-card {
  cursor: pointer;
  transition: all 0.2s ease;
  border-width: 2px;
}

.mode-card:hover {
  border-color: rgba(var(--v-theme-primary), 0.5);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.mode-card.selected {
  border-color: rgb(var(--v-theme-primary));
  background-color: rgba(var(--v-theme-primary), 0.05);
}

.lan-config-panel {
  border-color: rgb(var(--v-theme-primary));
  border-width: 2px;
}

.disabled-card {
  opacity: 0.6;
  cursor: not-allowed;
}

.disabled-card:hover {
  border-color: rgba(var(--v-theme-surface-variant), 0.5) !important;
  box-shadow: none !important;
}
</style>
