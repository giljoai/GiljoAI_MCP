<template>
  <v-card class="websocket-test ma-4 pa-4">
    <v-card-title>
      WebSocket V2 Test Component
      <v-spacer />
      <v-chip :color="statusColor" :prepend-icon="statusIcon" label>
        {{ connectionStatus }}
      </v-chip>
    </v-card-title>

    <v-card-text>
      <!-- Connection Info -->
      <v-row>
        <v-col cols="12" md="6">
          <h3>Connection Info</h3>
          <v-list density="compact">
            <v-list-item>
              <v-list-item-title>Status:</v-list-item-title>
              <v-list-item-subtitle>{{ connectionStatus }}</v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>Client ID:</v-list-item-title>
              <v-list-item-subtitle>{{ clientId || 'Not connected' }}</v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>Reconnect Attempts:</v-list-item-title>
              <v-list-item-subtitle>{{ reconnectAttempts }}</v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>Message Queue:</v-list-item-title>
              <v-list-item-subtitle>{{ messageQueueSize }} messages</v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>Subscriptions:</v-list-item-title>
              <v-list-item-subtitle>{{ subscriptions.length }} active</v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </v-col>

        <!-- Test Actions -->
        <v-col cols="12" md="6">
          <h3>Test Actions</h3>
          <v-btn
            class="ma-2"
            color="primary"
            prepend-icon="mdi-connection"
            :disabled="isConnected || isConnecting"
            @click="testConnect"
          >
            Connect
          </v-btn>
          <v-btn
            class="ma-2"
            color="error"
            prepend-icon="mdi-connection"
            :disabled="!isConnected"
            @click="testDisconnect"
          >
            Disconnect
          </v-btn>
          <v-btn
            class="ma-2"
            color="info"
            prepend-icon="mdi-send"
            :disabled="!isConnected"
            @click="testSendMessage"
          >
            Send Test Message
          </v-btn>
          <v-btn
            class="ma-2"
            color="success"
            prepend-icon="mdi-bell-ring"
            :disabled="!isConnected"
            @click="testSubscribe"
          >
            Test Subscribe
          </v-btn>
          <v-btn
            class="ma-2"
            color="warning"
            prepend-icon="mdi-bell-off"
            :disabled="!isConnected"
            @click="testUnsubscribe"
          >
            Test Unsubscribe
          </v-btn>
          <v-btn
            class="ma-2"
            color="secondary"
            prepend-icon="mdi-information"
            @click="showDebugInfo"
          >
            Show Debug Info
          </v-btn>
        </v-col>
      </v-row>

      <!-- Active Subscriptions -->
      <v-row v-if="subscriptions.length > 0">
        <v-col cols="12">
          <h3>Active Subscriptions</h3>
          <v-chip-group>
            <v-chip
              v-for="sub in subscriptions"
              :key="sub"
              closable
              @click:close="unsubscribeFrom(sub)"
            >
              {{ sub }}
            </v-chip>
          </v-chip-group>
        </v-col>
      </v-row>

      <!-- Received Messages -->
      <v-row>
        <v-col cols="12">
          <h3>Received Messages ({{ messages.length }})</h3>
          <v-btn size="small" color="error" @click="messages = []"> Clear Messages </v-btn>
          <v-virtual-scroll :items="messages" height="400" item-height="80" class="mt-2">
            <template #default="{ item }">
              <v-card class="ma-2" variant="outlined">
                <v-card-text>
                  <div class="text-caption text-grey">
                    {{ new Date(item.timestamp).toLocaleTimeString() }}
                  </div>
                  <div class="font-weight-bold">{{ item.type }}</div>
                  <pre class="text-caption mt-1">{{ JSON.stringify(item.data, null, 2) }}</pre>
                </v-card-text>
              </v-card>
            </template>
          </v-virtual-scroll>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useWebSocketV2 } from '@/composables/useWebSocketV2'

// ============================================
// WEBSOCKET
// ============================================

const {
  isConnected,
  isConnecting,
  connectionStatus,
  clientId,
  reconnectAttempts,
  messageQueueSize,
  subscriptions,
  connect,
  disconnect,
  send,
  on,
  subscribe,
  unsubscribe,
  getDebugInfo,
} = useWebSocketV2()

// ============================================
// STATE
// ============================================

const messages = ref([])
const testSubscriptionKey = ref(null)

// ============================================
// COMPUTED
// ============================================

const statusColor = computed(() => {
  switch (connectionStatus.value) {
    case 'connected':
      return 'success'
    case 'connecting':
      return 'info'
    case 'reconnecting':
      return 'warning'
    case 'disconnected':
      return 'error'
    default:
      return 'grey'
  }
})

const statusIcon = computed(() => {
  switch (connectionStatus.value) {
    case 'connected':
      return 'mdi-wifi'
    case 'connecting':
      return 'mdi-wifi-sync'
    case 'reconnecting':
      return 'mdi-wifi-refresh'
    case 'disconnected':
      return 'mdi-wifi-off'
    default:
      return 'mdi-wifi-alert'
  }
})

// ============================================
// WEBSOCKET LISTENERS
// ============================================

// Listen for all messages
on('*', (data) => {
  messages.value.unshift({
    type: data.type || 'unknown',
    data: data,
    timestamp: new Date().toISOString(),
  })

  // Limit message history
  if (messages.value.length > 100) {
    messages.value.pop()
  }
})

// ============================================
// TEST ACTIONS
// ============================================

async function testConnect() {
  try {
    await connect()
    console.log('✅ Connected successfully')
  } catch (error) {
    console.error('❌ Connection failed:', error)
  }
}

function testDisconnect() {
  disconnect()
  console.log('✅ Disconnected')
}

function testSendMessage() {
  const message = {
    type: 'test_message',
    payload: {
      message: 'Hello from WebSocket V2 Test Component',
      timestamp: new Date().toISOString(),
      random: Math.random(),
    },
  }

  const success = send(message)
  console.log(success ? '✅ Message sent' : '❌ Message queued (not connected)')
}

function testSubscribe() {
  const projectId = 'test-project-' + Math.random().toString(36).substr(2, 9)
  testSubscriptionKey.value = subscribe('project', projectId)
  console.log(`✅ Subscribed to project: ${projectId}`)
}

function testUnsubscribe() {
  if (testSubscriptionKey.value) {
    const [entityType, entityId] = testSubscriptionKey.value.split(':')
    unsubscribe(entityType, entityId)
    console.log(`✅ Unsubscribed from: ${testSubscriptionKey.value}`)
    testSubscriptionKey.value = null
  } else {
    console.log('⚠️ No active test subscription')
  }
}

function unsubscribeFrom(key) {
  const [entityType, entityId] = key.split(':')
  unsubscribe(entityType, entityId)
  console.log(`✅ Unsubscribed from: ${key}`)
}

function showDebugInfo() {
  const debugInfo = getDebugInfo()
  console.log('🐛 WebSocket Debug Info:', debugInfo)
  alert('Debug info logged to console')
}
</script>

<style scoped>
.websocket-test {
  max-width: 1400px;
  margin: 0 auto;
}

pre {
  background: #f5f5f5;
  padding: 8px;
  border-radius: 4px;
  overflow-x: auto;
  max-height: 150px;
}
</style>
