# Handover 0515c: Complete WebSocket V2 Migration [CCW]

**Execution Environment**: CCW (Claude Code Web)
**Duration**: 1 day
**Branch Name**: `ccw-0515c-websocket-v2`
**Dependencies**: Must complete AFTER 0515a and 0515b are merged

---

## Why CCW?
- Pure frontend WebSocket code
- No backend changes needed
- No database access required
- Can refactor store and components

---

## Background

WebSocket V2 was designed in handover 0130a but never fully migrated. The old system still runs. This completes the migration.

### Current State
- Old WebSocket system in `frontend/src/websocket.js`
- Flow-specific wrapper in `frontend/src/flowWebSocket.js`
- Multiple reconnection systems
- Confusing 4-layer architecture

### Target State
- Single WebSocket V2 implementation
- One reconnection system (exponential backoff)
- Centralized subscription management
- Clean 2-layer architecture

---

## Files to Create/Modify

### 1. WebSocket V2 Core (`frontend/src/websocket/websocketV2.js`)

```javascript
import { ref, computed } from 'vue'

class WebSocketV2 {
  constructor(url) {
    this.url = url
    this.ws = null
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectDelay = 1000
    this.listeners = new Map()
    this.subscriptions = new Map()
    this.isConnected = ref(false)
    this.connectionState = ref('disconnected')
  }

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return
    }

    this.connectionState.value = 'connecting'

    this.ws = new WebSocket(this.url)

    this.ws.onopen = () => {
      console.log('WebSocket V2 connected')
      this.isConnected.value = true
      this.connectionState.value = 'connected'
      this.reconnectAttempts = 0
      this.resubscribeAll()
    }

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        this.handleMessage(data)
      } catch (error) {
        console.error('WebSocket message parse error:', error)
      }
    }

    this.ws.onclose = () => {
      this.isConnected.value = false
      this.connectionState.value = 'disconnected'
      this.handleReconnection()
    }

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      this.connectionState.value = 'error'
    }
  }

  handleReconnection() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached')
      this.connectionState.value = 'failed'
      return
    }

    this.reconnectAttempts++
    const delay = Math.min(this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1), 30000)

    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`)
    this.connectionState.value = 'reconnecting'

    setTimeout(() => {
      this.connect()
    }, delay)
  }

  subscribe(channel, callback) {
    if (!this.listeners.has(channel)) {
      this.listeners.set(channel, new Set())
    }
    this.listeners.get(channel).add(callback)

    // Track subscription for resubscription after reconnect
    this.subscriptions.set(channel, true)

    // Send subscription message if connected
    if (this.isConnected.value) {
      this.send({
        type: 'subscribe',
        channel
      })
    }

    // Return unsubscribe function
    return () => {
      const callbacks = this.listeners.get(channel)
      if (callbacks) {
        callbacks.delete(callback)
        if (callbacks.size === 0) {
          this.listeners.delete(channel)
          this.subscriptions.delete(channel)
        }
      }
    }
  }

  handleMessage(data) {
    const { type, channel, payload } = data

    // Handle system messages
    if (type === 'ping') {
      this.send({ type: 'pong' })
      return
    }

    // Handle channel messages
    if (channel && this.listeners.has(channel)) {
      this.listeners.get(channel).forEach(callback => {
        try {
          callback(payload)
        } catch (error) {
          console.error(`Error in WebSocket listener for ${channel}:`, error)
        }
      })
    }
  }

  resubscribeAll() {
    this.subscriptions.forEach((_, channel) => {
      this.send({
        type: 'subscribe',
        channel
      })
    })
  }

  send(data) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    } else {
      console.warn('WebSocket not connected, cannot send:', data)
    }
  }

  disconnect() {
    this.reconnectAttempts = this.maxReconnectAttempts // Prevent reconnection
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }
}

export default WebSocketV2
```

### 2. Vue Composable (`frontend/src/websocket/useWebSocketV2.js`)

```javascript
import { inject, onUnmounted } from 'vue'
import { useAuthStore } from '@/stores/auth'

export function useWebSocketV2() {
  const ws = inject('websocket')

  if (!ws) {
    console.error('WebSocket V2 not provided')
    return {
      subscribe: () => () => {},
      send: () => {},
      isConnected: ref(false),
      connectionState: ref('disconnected')
    }
  }

  const subscriptions = []

  const subscribe = (channel, callback) => {
    const unsubscribe = ws.subscribe(channel, callback)
    subscriptions.push(unsubscribe)
    return unsubscribe
  }

  // Auto-cleanup on component unmount
  onUnmounted(() => {
    subscriptions.forEach(unsubscribe => unsubscribe())
  })

  return {
    subscribe,
    send: ws.send.bind(ws),
    isConnected: ws.isConnected,
    connectionState: ws.connectionState
  }
}
```

### 3. Store Update (`frontend/src/stores/websocket.js`)

```javascript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import WebSocketV2 from '@/websocket/websocketV2'

export const useWebSocketStore = defineStore('websocket', () => {
  const wsUrl = computed(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = import.meta.env.VITE_API_BASE_URL?.replace(/^https?:\/\//, '') || window.location.host
    return `${protocol}//${host}/ws`
  })

  const ws = new WebSocketV2(wsUrl.value)

  // Auto-connect when store is created
  ws.connect()

  // Provide WebSocket instance for injection
  const provide = (app) => {
    app.provide('websocket', ws)
  }

  return {
    ws,
    provide,
    isConnected: ws.isConnected,
    connectionState: ws.connectionState,
    subscribe: ws.subscribe.bind(ws),
    send: ws.send.bind(ws),
    connect: ws.connect.bind(ws),
    disconnect: ws.disconnect.bind(ws)
  }
})
```

### 4. Main App Integration (`frontend/src/main.js`)

```javascript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import { useWebSocketStore } from '@/stores/websocket'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)

// Initialize WebSocket V2
const wsStore = useWebSocketStore()
wsStore.provide(app)

app.mount('#app')
```

---

## Component Migration Examples

### BEFORE: Using Old WebSocket
```vue
<script setup>
import { onMounted, onUnmounted } from 'vue'
import { useWebSocketStore } from '@/stores/websocket'

const wsStore = useWebSocketStore()

const handleAgentUpdate = (data) => {
  console.log('Agent updated:', data)
}

onMounted(() => {
  wsStore.on('agent:updated', handleAgentUpdate)
})

onUnmounted(() => {
  wsStore.off('agent:updated', handleAgentUpdate)
})
</script>
```

### AFTER: Using WebSocket V2
```vue
<script setup>
import { onMounted } from 'vue'
import { useWebSocketV2 } from '@/websocket/useWebSocketV2'

const { subscribe, isConnected } = useWebSocketV2()

onMounted(() => {
  // Auto-cleanup on unmount handled by composable
  subscribe('agent:updated', (data) => {
    console.log('Agent updated:', data)
  })
})
</script>

<template>
  <div>
    <v-chip v-if="isConnected" color="success">Connected</v-chip>
    <v-chip v-else color="error">Disconnected</v-chip>
  </div>
</template>
```

---

## Components to Update

Find all components using WebSocket:
```bash
grep -r "useWebSocketStore\|websocket\|WebSocket" frontend/src/components/
```

**Known Components**:
1. `frontend/src/components/agents/AgentMonitor.vue`
2. `frontend/src/components/projects/ProjectDashboard.vue`
3. `frontend/src/components/projects/LaunchTab.vue`
4. `frontend/src/components/orchestration/OrchestratorCard.vue`
5. `frontend/src/components/orchestration/MissionDisplay.vue`
6. `frontend/src/views/Dashboard.vue`
7. `frontend/src/App.vue` (connection indicator)

---

## Migration Steps

### Step 1: Create V2 Files
1. Create `websocketV2.js`
2. Create `useWebSocketV2.js`
3. Update store to use V2

### Step 2: Update Main App
1. Import V2 store
2. Initialize and provide to app

### Step 3: Migrate Components (One by One)
1. Find old WebSocket usage
2. Replace with V2 composable
3. Test component still receives updates

### Step 4: Verify All Channels Work
Test these WebSocket channels:
- `agent:created`
- `agent:updated`
- `agent:completed`
- `project:updated`
- `project:mission_updated`
- `orchestrator:status`
- `succession:triggered`

---

## Success Criteria

- [ ] WebSocket V2 connects successfully
- [ ] Exponential backoff reconnection works
- [ ] All components receive real-time updates
- [ ] No duplicate WebSocket connections
- [ ] Clean disconnection on logout
- [ ] Subscription management working
- [ ] No console errors
- [ ] Memory leaks prevented (subscriptions cleaned up)

---

## Testing Checklist

### Connection Testing
```javascript
// In browser console
const wsStore = window.$pinia._s.get('websocket')
console.log(wsStore.isConnected) // Should be true
console.log(wsStore.connectionState) // Should be 'connected'
```

### Reconnection Testing
1. Open Network tab
2. Disconnect network
3. Watch console for reconnection attempts
4. Reconnect network
5. Verify WebSocket reconnects

### Update Testing
1. Create an agent job
2. Verify real-time status updates
3. Update a project
4. Verify mission updates appear

---

## Common Issues

**Issue**: Components not receiving updates
**Solution**: Ensure channel names match backend exactly

**Issue**: Multiple WebSocket connections
**Solution**: Ensure only one store instance created

**Issue**: Memory leaks
**Solution**: Verify unsubscribe called on unmount

**Issue**: Reconnection not working
**Solution**: Check exponential backoff logic

---

**End of 0515c Scope**