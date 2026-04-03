<template>
  <div>
    <!-- Connection Status Chip -->
    <v-chip
      :color="chipColor"
      :prepend-icon="icon"
      variant="tonal"
      size="small"
      :class="['connection-status cursor-pointer', { reconnecting: wsStore.connectionStatus === 'reconnecting' }]"
      aria-label="Connection status, click for details"
      @click="showDebugPanel = !showDebugPanel"
    >
      <span class="text-caption status-label">{{ statusText }}</span>
      <v-tooltip v-if="showTooltip" activator="parent" location="bottom">
        <div class="text-caption">
          <div v-if="isReconnecting">
            Reconnection attempt {{ reconnectAttempts }}/{{ maxReconnectAttempts }}
          </div>
          <div v-if="connectionError">Error: {{ connectionError }}</div>
          <div v-if="messageQueueSize > 0">{{ messageQueueSize }} messages queued</div>
          <div v-if="clientId">Client ID: {{ clientId }}</div>
        </div>
      </v-tooltip>
    </v-chip>

    <!-- Debug Panel Dialog -->
    <v-dialog v-model="showDebugPanel" max-width="800" scrollable>
      <v-card v-draggable class="smooth-border">
        <v-card-title class="d-flex align-center">
          <v-icon start>mdi-bug</v-icon>
          WebSocket Debug Panel
          <v-spacer></v-spacer>
          <v-btn icon="mdi-close" variant="text" aria-label="Close debug panel" @click="showDebugPanel = false"></v-btn>
        </v-card-title>

        <v-divider></v-divider>

        <v-card-text>
          <!-- Connection Info -->
          <v-expansion-panels v-model="panels" variant="accordion">
            <!-- Connection Status -->
            <v-expansion-panel value="status">
              <v-expansion-panel-title>
                <v-icon start :color="chipColor">{{ icon }}</v-icon>
                Connection Status
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <v-list density="compact">
                  <v-list-item>
                    <v-list-item-title>State</v-list-item-title>
                    <v-list-item-subtitle>{{ connectionState }}</v-list-item-subtitle>
                  </v-list-item>
                  <v-list-item v-if="clientId">
                    <v-list-item-title>Client ID</v-list-item-title>
                    <v-list-item-subtitle>{{ clientId }}</v-list-item-subtitle>
                  </v-list-item>
                  <v-list-item>
                    <v-list-item-title>WebSocket URL</v-list-item-title>
                    <v-list-item-subtitle>{{ wsUrl }}</v-list-item-subtitle>
                  </v-list-item>
                  <v-list-item v-if="debugInfo?.stats?.connectedAt">
                    <v-list-item-title>Connected At</v-list-item-title>
                    <v-list-item-subtitle>{{
                      formatTime(debugInfo.stats.connectedAt)
                    }}</v-list-item-subtitle>
                  </v-list-item>
                  <v-list-item v-if="debugInfo?.stats?.disconnectedAt">
                    <v-list-item-title>Disconnected At</v-list-item-title>
                    <v-list-item-subtitle>{{
                      formatTime(debugInfo.stats.disconnectedAt)
                    }}</v-list-item-subtitle>
                  </v-list-item>
                </v-list>
              </v-expansion-panel-text>
            </v-expansion-panel>

            <!-- Statistics -->
            <v-expansion-panel value="stats">
              <v-expansion-panel-title>
                <v-icon start>mdi-chart-line</v-icon>
                Statistics
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <v-row>
                  <v-col cols="6">
                    <v-card variant="tonal">
                      <v-card-text class="text-center">
                        <div class="text-h4">{{ debugInfo?.stats?.messagesSent || 0 }}</div>
                        <div class="text-caption">Messages Sent</div>
                      </v-card-text>
                    </v-card>
                  </v-col>
                  <v-col cols="6">
                    <v-card variant="tonal">
                      <v-card-text class="text-center">
                        <div class="text-h4">{{ debugInfo?.stats?.messagesReceived || 0 }}</div>
                        <div class="text-caption">Messages Received</div>
                      </v-card-text>
                    </v-card>
                  </v-col>
                  <v-col cols="6">
                    <v-card variant="tonal">
                      <v-card-text class="text-center">
                        <div class="text-h4">{{ messageQueueSize }}</div>
                        <div class="text-caption">Queued Messages</div>
                      </v-card-text>
                    </v-card>
                  </v-col>
                  <v-col cols="6">
                    <v-card variant="tonal">
                      <v-card-text class="text-center">
                        <div class="text-h4">{{ debugInfo?.stats?.connectionAttempts || 0 }}</div>
                        <div class="text-caption">Connection Attempts</div>
                      </v-card-text>
                    </v-card>
                  </v-col>
                </v-row>
              </v-expansion-panel-text>
            </v-expansion-panel>

            <!-- Subscriptions -->
            <v-expansion-panel value="subscriptions">
              <v-expansion-panel-title>
                <v-icon start>mdi-broadcast</v-icon>
                Active Subscriptions ({{ subscriptions.size }})
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <v-list density="compact">
                  <v-list-item v-for="sub in Array.from(subscriptions)" :key="sub">
                    <v-list-item-title>{{ sub }}</v-list-item-title>
                  </v-list-item>
                  <v-list-item v-if="subscriptions.size === 0">
                    <v-list-item-title class="text-grey">No active subscriptions</v-list-item-title>
                  </v-list-item>
                </v-list>
              </v-expansion-panel-text>
            </v-expansion-panel>

            <!-- Event History -->
            <v-expansion-panel value="events">
              <v-expansion-panel-title>
                <v-icon start>mdi-history</v-icon>
                Recent Events (Last 10)
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <v-list density="compact" class="event-list">
                  <v-list-item
                    v-for="(event, index) in recentEvents"
                    :key="index"
                    :class="`event-${event.type}`"
                  >
                    <template v-slot:prepend>
                      <v-icon size="small" :color="getEventColor(event.type)">
                        {{ getEventIcon(event.type) }}
                      </v-icon>
                    </template>
                    <v-list-item-title>{{ event.message }}</v-list-item-title>
                    <v-list-item-subtitle>{{ formatTime(event.timestamp) }}</v-list-item-subtitle>
                  </v-list-item>
                  <v-list-item v-if="!recentEvents?.length">
                    <v-list-item-title class="text-grey">No events recorded</v-list-item-title>
                  </v-list-item>
                </v-list>
              </v-expansion-panel-text>
            </v-expansion-panel>

            <!-- Last Error -->
            <v-expansion-panel v-if="debugInfo?.stats?.lastError" value="error">
              <v-expansion-panel-title color="error">
                <v-icon start color="error">mdi-alert-circle</v-icon>
                Last Error
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <v-alert type="error" variant="tonal">
                  {{ debugInfo.stats.lastError }}
                </v-alert>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-card-text>

        <v-divider></v-divider>

        <!-- Test Actions -->
        <v-card-actions>
          <v-btn color="primary" variant="tonal" :disabled="isConnecting" @click="forceReconnect">
            <v-icon start>mdi-refresh</v-icon>
            Force Reconnect
          </v-btn>
          <v-btn color="warning" variant="tonal" :disabled="!isConnected" @click="simulateDrop">
            <v-icon start>mdi-connection</v-icon>
            Simulate Drop
          </v-btn>
          <v-btn color="info" variant="tonal" :disabled="!isConnected" @click="sendTestMessage">
            <v-icon start>mdi-send</v-icon>
            Send Test
          </v-btn>
          <v-btn
            color="secondary"
            variant="tonal"
            :disabled="messageQueueSize === 0"
            @click="clearQueue"
          >
            <v-icon start>mdi-delete-sweep</v-icon>
            Clear Queue ({{ messageQueueSize }})
          </v-btn>
          <v-spacer></v-spacer>
          <v-switch
            v-model="debugMode"
            label="Debug Mode"
            density="compact"
            hide-details
            @update:model-value="toggleDebugMode"
          ></v-switch>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useWebSocketStore } from '@/stores/websocket'

const wsStore = useWebSocketStore()

// State
const showDebugPanel = ref(false)
const panels = ref(['status'])
const debugInfo = ref({})
const debugMode = ref(false)
const refreshInterval = ref(null)

// Computed
const statusText = computed(() => {
  switch (wsStore.connectionStatus) {
    case 'connected':
      return 'Connected'
    case 'connecting':
      return 'Connecting...'
    case 'reconnecting':
      return `Reconnecting (${wsStore.reconnectAttempts}/${wsStore.maxReconnectAttempts})`
    case 'disconnected':
      return 'Disconnected'
    default:
      return 'Unknown'
  }
})

const chipColor = computed(() => {
  switch (wsStore.connectionStatus) {
    case 'connected':
      return 'success'
    case 'connecting':
    case 'reconnecting':
      return 'warning'
    case 'disconnected':
      return 'error'
    default:
      return 'grey'
  }
})

const icon = computed(() => {
  switch (wsStore.connectionStatus) {
    case 'connected':
      return 'mdi-wifi'
    case 'connecting':
    case 'reconnecting':
      return 'mdi-wifi-sync'
    case 'disconnected':
      return 'mdi-wifi-off'
    default:
      return 'mdi-help-circle'
  }
})

const showTooltip = computed(() => {
  return (
    wsStore.isReconnecting ||
    wsStore.connectionError ||
    wsStore.messageQueueSize > 0 ||
    wsStore.clientId
  )
})

const isReconnecting = computed(() => wsStore.isReconnecting)
const isConnecting = computed(() => wsStore.isConnecting)
const isConnected = computed(() => wsStore.isConnected)
const reconnectAttempts = computed(() => wsStore.reconnectAttempts)
const maxReconnectAttempts = computed(() => wsStore.maxReconnectAttempts)
const connectionError = computed(() => wsStore.connectionError)
const messageQueueSize = computed(() => wsStore.messageQueueSize)
const clientId = computed(() => wsStore.clientId)
const connectionState = computed(() => wsStore.connectionStatus)
const subscriptions = computed(() => wsStore.subscriptions)

const wsUrl = computed(() => {
  const wsProto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const baseUrl = import.meta.env.VITE_WS_URL || `${wsProto}://${window.location.hostname}:${window.location.port || 7272}`
  return `${baseUrl}/ws/${clientId.value || '{client_id}'}`
})

const recentEvents = computed(() => debugInfo.value?.eventHistory?.slice(0, 10) || [])

// Methods
const updateDebugInfo = () => {
  debugInfo.value = wsStore.getDebugInfo()
}

const forceReconnect = async () => {
  await wsStore.disconnect()
  await wsStore.connect()
  updateDebugInfo()
}

const simulateDrop = () => {
  // V2: Simulate by disconnecting
  wsStore.disconnect()
  updateDebugInfo()
}

const sendTestMessage = () => {
  wsStore.send({
    type: 'test',
    timestamp: new Date().toISOString(),
    message: 'Test message from debug panel',
  })
  updateDebugInfo()
}

const clearQueue = () => {
  // V2: Queue is managed internally
  updateDebugInfo()
}

const toggleDebugMode = (value) => {
  wsStore.setDebugMode(value)
  updateDebugInfo()
}

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString()
}

const getEventIcon = (type) => {
  const icons = {
    connection: 'mdi-connection',
    error: 'mdi-alert-circle',
    subscription: 'mdi-broadcast',
    log: 'mdi-text',
    test: 'mdi-test-tube',
  }
  return icons[type] || 'mdi-circle'
}

const getEventColor = (type) => {
  const colors = {
    connection: 'success',
    error: 'error',
    subscription: 'info',
    log: 'grey',
    test: 'warning',
  }
  return colors[type] || 'grey'
}

// Lifecycle
onMounted(() => {
  updateDebugInfo()
  debugMode.value = wsStore.debug || false

  // Update debug info every second when panel is open
  refreshInterval.value = setInterval(() => {
    if (showDebugPanel.value) {
      updateDebugInfo()
    }
  }, 1000)
})

onUnmounted(() => {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value)
  }
})
</script>

<style lang="scss" scoped>
@use '@/styles/design-tokens' as *;
.connection-status {
  transition: all $transition-slow ease;
}

.connection-status.reconnecting {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% {
    opacity: 1;
  }
  50% {
    opacity: 0.6;
  }
  100% {
    opacity: 1;
  }
}

.connection-status:deep(.v-chip__content) {
  font-weight: 500;
}

.event-list {
  max-height: 300px;
  overflow-y: auto;
}

.event-connection {
  border-left: 2px solid rgb(var(--v-theme-success));
}

.event-error {
  border-left: 2px solid rgb(var(--v-theme-error));
}

.event-subscription {
  border-left: 2px solid rgb(var(--v-theme-info));
}

.event-test {
  border-left: 2px solid rgb(var(--v-theme-warning));
}

/* Mobile format: hide status text, show only wifi icon */
@media (max-width: 1024px) {
  .status-label {
    display: none;
  }
}
</style>
