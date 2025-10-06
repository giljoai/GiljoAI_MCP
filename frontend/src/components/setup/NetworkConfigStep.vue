<template>
  <v-card-text class="pa-8">
    <h2 class="text-h5 mb-2">Network Configuration</h2>
    <p class="text-body-1 mb-6">
      Configure how your team will access GiljoAI MCP
    </p>

    <!-- Mode Selection -->
    <v-radio-group v-model="selectedMode" class="mb-4">
      <!-- Localhost Mode -->
      <v-card
        variant="outlined"
        class="mb-4 mode-card"
        :class="{ 'selected': selectedMode === 'localhost' }"
        @click="selectedMode = 'localhost'"
        role="button"
        tabindex="0"
        aria-label="Select localhost mode for single user"
      >
        <v-card-text>
          <v-radio value="localhost">
            <template #label>
              <div class="ml-4">
                <div class="text-h6 d-flex align-center">
                  <v-icon class="mr-2">mdi-laptop</v-icon>
                  Localhost (Recommended)
                </div>
                <div class="text-caption text-medium-emphasis">
                  Single user on this computer only
                </div>
              </div>
            </template>
          </v-radio>

          <v-list density="compact" class="mt-4 bg-transparent">
            <v-list-item
              prepend-icon="mdi-check"
              title="No network configuration needed"
              class="text-caption"
            />
            <v-list-item
              prepend-icon="mdi-check"
              title="No authentication required"
              class="text-caption"
            />
            <v-list-item
              prepend-icon="mdi-check"
              title="Fastest performance"
              class="text-caption"
            />
            <v-list-item
              prepend-icon="mdi-check"
              title="Most secure (localhost only)"
              class="text-caption"
            />
          </v-list>
        </v-card-text>
      </v-card>

      <!-- LAN Mode -->
      <v-card
        variant="outlined"
        class="mb-4 mode-card"
        :class="{ 'selected': selectedMode === 'lan' }"
        @click="selectedMode = 'lan'"
        role="button"
        tabindex="0"
        aria-label="Select LAN mode for team access"
      >
        <v-card-text>
          <v-radio value="lan">
            <template #label>
              <div class="ml-4">
                <div class="text-h6 d-flex align-center">
                  <v-icon class="mr-2">mdi-network</v-icon>
                  LAN (Local Network)
                </div>
                <div class="text-caption text-medium-emphasis">
                  Team access on your local network
                </div>
              </div>
            </template>
          </v-radio>

          <v-list density="compact" class="mt-4 bg-transparent">
            <v-list-item
              prepend-icon="mdi-check"
              title="Multiple users can connect"
              class="text-caption"
            />
            <v-list-item
              prepend-icon="mdi-check"
              title="Network configuration required"
              class="text-caption"
            />
            <v-list-item
              prepend-icon="mdi-check"
              title="Authentication enabled"
              class="text-caption"
            />
            <v-list-item
              prepend-icon="mdi-check"
              title="Recommended for small teams (2-10 users)"
              class="text-caption"
            />
          </v-list>
        </v-card-text>
      </v-card>
    </v-radio-group>

    <!-- LAN Configuration Panel (Expandable) -->
    <v-expand-transition>
      <v-card
        v-if="selectedMode === 'lan'"
        variant="outlined"
        class="lan-config-panel mb-4"
      >
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
            <strong>Security Notice:</strong> LAN mode enables network access with API key authentication. Ensure your network is trusted and secure.
          </v-alert>
        </v-card-text>
      </v-card>
    </v-expand-transition>

    <!-- Info Alert -->
    <v-alert type="info" variant="tonal" class="mb-6">
      <v-icon start>mdi-information</v-icon>
      You can change deployment mode later in Settings, but this may require service restart.
    </v-alert>

    <!-- Progress -->
    <v-card variant="outlined" class="mb-6">
      <v-card-text>
        <div class="d-flex justify-space-between mb-2">
          <span class="text-caption">Progress: Step 2 of 3</span>
          <span class="text-caption">67%</span>
        </div>
        <v-progress-linear :model-value="67" color="primary" />
      </v-card-text>
    </v-card>

    <!-- Navigation -->
    <div class="d-flex justify-space-between">
      <v-btn
        variant="outlined"
        @click="$emit('back')"
        aria-label="Go back to tool attachment"
      >
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
import { ref, computed, watch } from 'vue'

/**
 * NetworkConfigStep - Network configuration step (Step 2 of 3)
 *
 * Allows user to choose between localhost and LAN modes
 */

const props = defineProps({
  mode: {
    type: String,
    required: true,
    validator: (value) => ['localhost', 'lan'].includes(value)
  },
  lanSettings: {
    type: Object,
    default: null
  }
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
  hostname: props.lanSettings?.hostname || ''
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
  }
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
watch(lanConfig, (newConfig) => {
  if (selectedMode.value === 'lan') {
    emit('update:lanSettings', { ...newConfig })
  }
}, { deep: true })

// Methods
const detectServerIp = async () => {
  detectingIp.value = true

  try {
    // Simple method: Get local IP via RTCPeerConnection
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
    console.error('[NETWORK_CONFIG] Failed to detect IP:', error)
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
</style>
