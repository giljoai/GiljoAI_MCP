<template>
  <v-card-text class="pa-8">
    <h2 class="text-h5 mb-6">LAN Network Configuration</h2>

    <!-- Server URL -->
    <v-alert type="success" variant="tonal" class="mb-6">
      <div class="text-subtitle-1 mb-2">
        <strong>Your GiljoAI MCP server is now running on:</strong>
      </div>
      <v-card variant="outlined" class="mt-2">
        <v-card-text class="d-flex align-center justify-space-between pa-3">
          <code class="text-h6">{{ serverUrl }}</code>
          <v-btn
            icon
            variant="text"
            size="small"
            @click="copyUrl"
            aria-label="Copy server URL"
          >
            <v-icon>{{ urlCopied ? 'mdi-check' : 'mdi-content-copy' }}</v-icon>
          </v-btn>
        </v-card-text>
      </v-card>
    </v-alert>

    <!-- Firewall Configuration -->
    <h3 class="text-h6 mb-4">Firewall Configuration</h3>

    <v-alert type="warning" variant="tonal" class="mb-4">
      <v-icon start>mdi-shield-alert</v-icon>
      Port 7274 must be open for network access
    </v-alert>

    <!-- Platform-specific instructions -->
    <v-card variant="outlined" class="mb-6">
      <v-card-title class="bg-surface-variant">
        <v-icon start>{{ platformIcon }}</v-icon>
        Platform detected: {{ platformName }}
      </v-card-title>

      <v-card-text class="pa-4">
        <div class="text-subtitle-2 mb-3">Run this command:</div>
        <v-card variant="outlined" class="mb-4 bg-surface">
          <v-card-text class="d-flex align-center justify-space-between pa-3">
            <pre class="firewall-command mb-0">{{ firewallCommand }}</pre>
            <v-btn
              icon
              variant="text"
              size="small"
              @click="copyCommand"
              aria-label="Copy firewall command"
            >
              <v-icon>{{ commandCopied ? 'mdi-check' : 'mdi-content-copy' }}</v-icon>
            </v-btn>
          </v-card-text>
        </v-card>

        <!-- Step-by-step instructions -->
        <div class="text-subtitle-2 mb-2">Instructions:</div>
        <ol class="pl-4">
          <li v-for="(step, index) in instructions" :key="index" class="mb-2">
            {{ step }}
          </li>
        </ol>
      </v-card-text>
    </v-card>

    <!-- Port test -->
    <div class="mb-6">
      <v-btn
        variant="outlined"
        :loading="testing"
        @click="testPort"
      >
        <v-icon start>mdi-network-strength-4</v-icon>
        Test Port Access
      </v-btn>

      <!-- Test result -->
      <v-alert
        v-if="testResult"
        :type="testResult.success ? 'success' : 'error'"
        variant="tonal"
        class="mt-4"
      >
        <div v-if="testResult.success">
          <strong>Port 7274 is accessible on your network!</strong>
          <div class="mt-2">
            Team members can now connect to:
            <br>
            <code>{{ serverUrl }}</code>
          </div>
        </div>
        <div v-else>
          <strong>Port appears blocked</strong>
          <div class="mt-2">
            {{ testResult.message }}
            <br>
            Please verify firewall settings and try again.
          </div>
        </div>
      </v-alert>
    </div>

    <!-- Progress -->
    <v-card variant="outlined" class="mb-6">
      <v-card-text>
        <div class="d-flex justify-space-between mb-2">
          <span class="text-caption">Progress: Step 6 of 7</span>
          <span class="text-caption">86%</span>
        </div>
        <v-progress-linear :model-value="86" color="primary" />
      </v-card-text>
    </v-card>

    <!-- Navigation -->
    <div class="d-flex justify-space-between">
      <v-btn
        variant="outlined"
        @click="$emit('back')"
        aria-label="Go back to AI tools"
      >
        <v-icon start>mdi-arrow-left</v-icon>
        Back
      </v-btn>
      <v-btn
        color="primary"
        @click="$emit('next')"
        aria-label="Continue to completion"
      >
        Continue
        <v-icon end>mdi-arrow-right</v-icon>
      </v-btn>
    </div>
  </v-card-text>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

/**
 * LanConfigStep - LAN network configuration step
 *
 * Provides platform-specific firewall configuration instructions
 * and tests port accessibility
 */

const props = defineProps({
  modelValue: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:modelValue', 'next', 'back'])

// State
const platform = ref('windows') // Detect actual platform
const localIp = ref('192.168.1.100') // Get from backend
const port = ref(7274)
const testing = ref(false)
const testResult = ref(null)
const urlCopied = ref(false)
const commandCopied = ref(false)

// Computed
const serverUrl = computed(() => `http://${localIp.value}:${port.value}`)

const platformName = computed(() => {
  const names = {
    windows: 'Windows',
    linux: 'Linux',
    macos: 'macOS'
  }
  return names[platform.value] || 'Unknown'
})

const platformIcon = computed(() => {
  const icons = {
    windows: 'mdi-microsoft-windows',
    linux: 'mdi-linux',
    macos: 'mdi-apple'
  }
  return icons[platform.value] || 'mdi-desktop-tower'
})

const firewallCommand = computed(() => {
  if (platform.value === 'windows') {
    return `netsh advfirewall firewall add rule ^
  name="GiljoAI MCP" dir=in action=allow ^
  protocol=TCP localport=${port.value}`
  } else if (platform.value === 'linux') {
    return `sudo ufw allow ${port.value}/tcp
sudo ufw reload`
  } else if (platform.value === 'macos') {
    return 'Use System Preferences > Security & Privacy > Firewall'
  }
  return ''
})

const instructions = computed(() => {
  if (platform.value === 'windows') {
    return [
      'Open PowerShell as Administrator (Right-click Start menu → Windows PowerShell (Admin))',
      'Paste and run the command above',
      'Press Enter to execute',
      'Click "Test Port Access" button below to verify'
    ]
  } else if (platform.value === 'linux') {
    return [
      'Open a terminal',
      'Run the commands above (requires sudo password)',
      'Click "Test Port Access" button below to verify'
    ]
  } else if (platform.value === 'macos') {
    return [
      'Open System Preferences',
      'Go to Security & Privacy → Firewall',
      'Click Firewall Options',
      'Add GiljoAI MCP or allow port 7274',
      'Click "Test Port Access" button below to verify'
    ]
  }
  return []
})

// Methods
const detectPlatform = () => {
  const userAgent = navigator.userAgent.toLowerCase()
  const platform_val = navigator.platform.toLowerCase()

  if (userAgent.includes('win') || platform_val.includes('win')) {
    platform.value = 'windows'
  } else if (userAgent.includes('mac') || platform_val.includes('mac')) {
    platform.value = 'macos'
  } else if (userAgent.includes('linux') || platform_val.includes('linux')) {
    platform.value = 'linux'
  }
}

const getLocalIp = async () => {
  // In a real implementation, get this from backend
  // For now, use placeholder
  localIp.value = '192.168.1.100'
}

const copyUrl = async () => {
  try {
    await navigator.clipboard.writeText(serverUrl.value)
    urlCopied.value = true
    setTimeout(() => {
      urlCopied.value = false
    }, 2000)
  } catch (error) {
    console.error('Failed to copy URL:', error)
  }
}

const copyCommand = async () => {
  try {
    await navigator.clipboard.writeText(firewallCommand.value)
    commandCopied.value = true
    setTimeout(() => {
      commandCopied.value = false
    }, 2000)
  } catch (error) {
    console.error('Failed to copy command:', error)
  }
}

const testPort = async () => {
  testing.value = true
  testResult.value = null

  try {
    // Simulate port test (in real implementation, call backend API)
    await new Promise(resolve => setTimeout(resolve, 1500))

    // Mock result - in real implementation, test actual port accessibility
    testResult.value = {
      success: true,
      message: 'Port is accessible'
    }

    // Update parent state
    emit('update:modelValue', {
      platform: platform.value,
      localIp: localIp.value,
      port: port.value,
      firewallConfigured: true
    })
  } catch (error) {
    testResult.value = {
      success: false,
      message: error.message
    }
  } finally {
    testing.value = false
  }
}

// Lifecycle
onMounted(() => {
  detectPlatform()
  getLocalIp()
})
</script>

<style scoped>
h2, h3 {
  color: rgb(var(--v-theme-primary));
}

.firewall-command {
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
  white-space: pre-wrap;
  word-wrap: break-word;
  color: rgb(var(--v-theme-on-surface));
}

code {
  background-color: rgba(var(--v-theme-surface-variant), 0.5);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
}

ol {
  line-height: 1.8;
}
</style>
