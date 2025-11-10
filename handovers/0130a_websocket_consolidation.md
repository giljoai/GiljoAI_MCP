# Handover 0130a: WebSocket Consolidation (CAREFUL - IT WORKS!)

**Status:** Ready to Execute
**Priority:** P1 - HIGH (But CAREFUL)
**Estimated Duration:** 2-3 days
**Agent Budget:** 150K tokens
**Depends On:** Backend stable (0127-0128 complete)

---

## 🚨 CRITICAL WARNING

### The WebSocket System WORKS PERFECTLY

The current 4-layer WebSocket implementation is functioning flawlessly. Any changes must be:
1. **Incremental** - Small steps with validation
2. **Backward compatible** - Keep old files as backup
3. **Thoroughly tested** - Every feature must still work
4. **Reversible** - Easy rollback if issues arise

**IF IT BREAKS, ROLLBACK IMMEDIATELY**

---

## Executive Summary

### Current Architecture (4 Layers - 1,344 lines)

```
1. websocket.js (507 lines)        - Base WebSocket service
   ↓
2. flowWebSocket.js (377 lines)    - Flow-specific wrapper
   ↓
3. stores/websocket.js (318 lines) - Pinia store
   ↓
4. useWebSocket.js (142 lines)     - Vue composable
```

### Problem

- **Excessive indirection** - 4 layers for what should be 2
- **Multiple reconnection systems** - Each layer has its own
- **Subscription tracking chaos** - 4 different tracking systems
- **Memory leak risk** - Cleanup spread across layers
- **Developer confusion** - Unclear which layer to use

### Target Architecture (2 Layers - ~600 lines)

```
1. stores/websocket.js (~400 lines)
   - Pinia store for state management
   - Single reconnection system
   - Centralized subscription tracking

2. composables/useWebSocket.js (~200 lines)
   - Vue composable for components
   - Thin wrapper around store
   - Component lifecycle management
```

---

## Implementation Strategy

### Approach: Create New, Test, Then Switch

**DO NOT DELETE OLD FILES IMMEDIATELY**

1. Create new consolidated version alongside old
2. Test new version thoroughly
3. Switch one component at a time
4. Keep old files as .backup for 1 week
5. Delete only after proven stable

---

## Phase 1: Analysis and Documentation (4-6 hours)

### Step 1.1: Map Current Functionality

**Document EVERYTHING the current system does:**

```javascript
// websocket.js features:
- [ ] Connection management
- [ ] Reconnection with exponential backoff
- [ ] Event subscription/unsubscription
- [ ] Message queuing while disconnected
- [ ] Error handling
- [ ] Connection state tracking

// flowWebSocket.js features:
- [ ] Project-specific subscriptions
- [ ] Agent job updates
- [ ] Flow status updates
- [ ] Orchestrator events
- [ ] Completion events

// stores/websocket.js features:
- [ ] Pinia state management
- [ ] Reactive connection status
- [ ] Message history
- [ ] Subscription registry
- [ ] Auto-cleanup on disconnect

// useWebSocket.js features:
- [ ] Component lifecycle integration
- [ ] Auto-unsubscribe on unmount
- [ ] Typed event handlers
- [ ] Connection status reactivity
```

### Step 1.2: Trace Component Usage

```bash
# Find all components using WebSocket
grep -r "useWebSocket\|flowWebSocket\|websocket" frontend/src/components/ --include="*.vue"

# Document which layer each component uses
```

Critical components to check:
- ProjectOrchestrator.vue
- AgentCardEnhanced.vue
- AgentJobMonitor.vue
- SuccessionTimeline.vue
- LaunchTab.vue

### Step 1.3: Document Message Types

```javascript
// Current message types handled:
const MESSAGE_TYPES = {
  // Connection
  'connection:open': {},
  'connection:close': {},
  'connection:error': {},

  // Jobs
  'job:created': { job_id, agent_type, status },
  'job:status_changed': { job_id, old_status, new_status },
  'job:completed': { job_id, result },
  'job:failed': { job_id, error },

  // Projects
  'project:updated': { project_id, changes },
  'project:completed': { project_id },

  // Agents
  'agent:spawned': { agent_id, type },
  'agent:message': { from_agent, to_agent, message },

  // Orchestrator
  'orchestrator:progress': { orchestrator_id, progress },
  'orchestrator:succession': { old_id, new_id },
};
```

---

## Phase 2: Create New Consolidated Store (6-8 hours)

### Step 2.1: Create New WebSocket Store

Create `frontend/src/stores/websocketV2.js`:

```javascript
/**
 * Consolidated WebSocket Store v2
 * Combines functionality from all 4 layers into clean Pinia store
 */

import { defineStore } from 'pinia';
import { ref, computed } from 'vue';

export const useWebSocketV2Store = defineStore('websocketV2', () => {
  // State
  const socket = ref(null);
  const connectionStatus = ref('disconnected'); // disconnected, connecting, connected
  const reconnectAttempts = ref(0);
  const messageQueue = ref([]);
  const subscriptions = ref(new Map());
  const eventHandlers = ref(new Map());

  // Configuration
  const config = {
    url: computed(() => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      return `${protocol}//${window.location.host}/ws`;
    }),
    reconnectDelay: 1000,
    maxReconnectDelay: 30000,
    reconnectDecay: 1.5,
    messageQueueSize: 100,
  };

  // Connection Management
  function connect() {
    if (socket.value?.readyState === WebSocket.OPEN) {
      return Promise.resolve();
    }

    return new Promise((resolve, reject) => {
      connectionStatus.value = 'connecting';

      try {
        socket.value = new WebSocket(config.url.value);

        socket.value.onopen = () => {
          console.log('WebSocket connected');
          connectionStatus.value = 'connected';
          reconnectAttempts.value = 0;
          flushMessageQueue();
          resolve();
        };

        socket.value.onclose = (event) => {
          console.log('WebSocket closed:', event);
          connectionStatus.value = 'disconnected';
          handleReconnect();
        };

        socket.value.onerror = (error) => {
          console.error('WebSocket error:', error);
          reject(error);
        };

        socket.value.onmessage = (event) => {
          handleMessage(event);
        };
      } catch (error) {
        connectionStatus.value = 'disconnected';
        reject(error);
      }
    });
  }

  function disconnect() {
    if (socket.value) {
      socket.value.close();
      socket.value = null;
    }
    connectionStatus.value = 'disconnected';
    subscriptions.value.clear();
    eventHandlers.value.clear();
  }

  // Reconnection Logic
  function handleReconnect() {
    if (connectionStatus.value === 'connecting') return;

    const delay = Math.min(
      config.reconnectDelay * Math.pow(config.reconnectDecay, reconnectAttempts.value),
      config.maxReconnectDelay
    );

    reconnectAttempts.value++;

    setTimeout(() => {
      if (connectionStatus.value === 'disconnected') {
        connect();
      }
    }, delay);
  }

  // Message Handling
  function handleMessage(event) {
    try {
      const data = JSON.parse(event.data);
      const { type, payload } = data;

      // Emit to specific handlers
      const handlers = eventHandlers.value.get(type) || [];
      handlers.forEach(handler => {
        try {
          handler(payload);
        } catch (error) {
          console.error(`Handler error for ${type}:`, error);
        }
      });

      // Emit to wildcard handlers
      const wildcardHandlers = eventHandlers.value.get('*') || [];
      wildcardHandlers.forEach(handler => {
        try {
          handler(type, payload);
        } catch (error) {
          console.error('Wildcard handler error:', error);
        }
      });
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  }

  // Subscription Management
  function subscribe(channel, params = {}) {
    const subscription = {
      channel,
      params,
      id: `${channel}-${Date.now()}`,
    };

    subscriptions.value.set(subscription.id, subscription);

    if (connectionStatus.value === 'connected') {
      send('subscribe', { channel, ...params });
    }

    return subscription.id;
  }

  function unsubscribe(subscriptionId) {
    const subscription = subscriptions.value.get(subscriptionId);
    if (subscription) {
      subscriptions.value.delete(subscriptionId);

      if (connectionStatus.value === 'connected') {
        send('unsubscribe', { channel: subscription.channel });
      }
    }
  }

  // Event Handler Management
  function on(event, handler) {
    if (!eventHandlers.value.has(event)) {
      eventHandlers.value.set(event, []);
    }
    eventHandlers.value.get(event).push(handler);

    // Return cleanup function
    return () => off(event, handler);
  }

  function off(event, handler) {
    const handlers = eventHandlers.value.get(event);
    if (handlers) {
      const index = handlers.indexOf(handler);
      if (index !== -1) {
        handlers.splice(index, 1);
      }
    }
  }

  // Send Messages
  function send(type, payload = {}) {
    const message = { type, payload, timestamp: Date.now() };

    if (connectionStatus.value === 'connected' && socket.value?.readyState === WebSocket.OPEN) {
      socket.value.send(JSON.stringify(message));
    } else {
      // Queue message
      messageQueue.value.push(message);
      if (messageQueue.value.length > config.messageQueueSize) {
        messageQueue.value.shift(); // Remove oldest
      }
    }
  }

  // Flush Queued Messages
  function flushMessageQueue() {
    while (messageQueue.value.length > 0 && connectionStatus.value === 'connected') {
      const message = messageQueue.value.shift();
      socket.value.send(JSON.stringify(message));
    }
  }

  // Computed
  const isConnected = computed(() => connectionStatus.value === 'connected');
  const isConnecting = computed(() => connectionStatus.value === 'connecting');
  const isDisconnected = computed(() => connectionStatus.value === 'disconnected');

  return {
    // State
    connectionStatus,
    reconnectAttempts,
    subscriptions,

    // Computed
    isConnected,
    isConnecting,
    isDisconnected,

    // Actions
    connect,
    disconnect,
    subscribe,
    unsubscribe,
    on,
    off,
    send,
  };
});
```

### Step 2.2: Create New Composable

Create `frontend/src/composables/useWebSocketV2.js`:

```javascript
/**
 * Vue Composable for WebSocket v2
 * Thin wrapper around store with component lifecycle management
 */

import { onMounted, onUnmounted } from 'vue';
import { storeToRefs } from 'pinia';
import { useWebSocketV2Store } from '@/stores/websocketV2';

export function useWebSocketV2() {
  const store = useWebSocketV2Store();
  const { isConnected, isConnecting, connectionStatus } = storeToRefs(store);

  const subscriptions = [];
  const handlers = [];

  // Auto-connect on mount
  onMounted(() => {
    store.connect();
  });

  // Auto-cleanup on unmount
  onUnmounted(() => {
    // Unsubscribe all
    subscriptions.forEach(id => store.unsubscribe(id));

    // Remove all handlers
    handlers.forEach(cleanup => cleanup());
  });

  // Wrapped subscribe that auto-cleans
  function subscribe(channel, params) {
    const id = store.subscribe(channel, params);
    subscriptions.push(id);
    return id;
  }

  // Wrapped event handler that auto-cleans
  function on(event, handler) {
    const cleanup = store.on(event, handler);
    handlers.push(cleanup);
    return cleanup;
  }

  return {
    // State
    isConnected,
    isConnecting,
    connectionStatus,

    // Methods
    subscribe,
    on,
    send: store.send,
    connect: store.connect,
    disconnect: store.disconnect,
  };
}
```

---

## Phase 3: Test New Implementation (4-6 hours)

### Step 3.1: Create Test Component

Create `frontend/src/components/TestWebSocketV2.vue`:

```vue
<template>
  <div class="websocket-test">
    <h2>WebSocket V2 Test</h2>

    <div>Status: {{ connectionStatus }}</div>
    <div>Connected: {{ isConnected }}</div>

    <button @click="testSubscribe">Test Subscribe</button>
    <button @click="testSend">Test Send</button>

    <div>Messages:</div>
    <pre>{{ messages }}</pre>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useWebSocketV2 } from '@/composables/useWebSocketV2';

const { isConnected, connectionStatus, subscribe, on, send } = useWebSocketV2();
const messages = ref([]);

// Listen for all messages
on('*', (type, payload) => {
  messages.value.push({ type, payload, time: new Date() });
});

function testSubscribe() {
  subscribe('project', { project_id: 'test-123' });
}

function testSend() {
  send('test', { message: 'Hello WebSocket V2' });
}
</script>
```

### Step 3.2: Test All Scenarios

Test checklist:
- [ ] Initial connection
- [ ] Reconnection after disconnect
- [ ] Message sending while connected
- [ ] Message queuing while disconnected
- [ ] Subscription management
- [ ] Event handler registration/cleanup
- [ ] Component unmount cleanup
- [ ] Multiple components using same store
- [ ] Memory leaks (Chrome DevTools)

---

## Phase 4: Gradual Migration (8-10 hours)

### Step 4.1: Create Migration Wrapper

Create a wrapper that mimics old API while using new implementation:

```javascript
// frontend/src/services/websocketCompat.js

import { useWebSocketV2Store } from '@/stores/websocketV2';

// Compatibility layer for old code
export class WebSocketCompat {
  constructor() {
    this.store = useWebSocketV2Store();
  }

  connect() {
    return this.store.connect();
  }

  disconnect() {
    return this.store.disconnect();
  }

  // Mimic old flowWebSocket API
  subscribeToProject(projectId) {
    return this.store.subscribe('project', { project_id: projectId });
  }

  subscribeToAgentJobs(agentType) {
    return this.store.subscribe('agent_jobs', { agent_type: agentType });
  }

  // ... add other compatibility methods
}
```

### Step 4.2: Migrate One Component

Start with a simple component:

```javascript
// Before (using old system)
import { useWebSocket } from '@/composables/useWebSocket';

// After (using new system)
import { useWebSocketV2 } from '@/composables/useWebSocketV2';
```

Test thoroughly before proceeding to next component.

### Step 4.3: Migration Order

Migrate in this order (simplest to most complex):
1. StatusIndicator.vue (simple connection status)
2. NotificationHandler.vue (receives messages)
3. AgentCard.vue (subscriptions)
4. AgentJobMonitor.vue (complex subscriptions)
5. ProjectOrchestrator.vue (most complex)

---

## Phase 5: Cleanup (2-3 hours)

### Step 5.1: Backup Old Files

```bash
# After all components migrated and tested
mv frontend/src/services/websocket.js frontend/src/services/websocket.js.backup
mv frontend/src/services/flowWebSocket.js frontend/src/services/flowWebSocket.js.backup
mv frontend/src/stores/websocket.js frontend/src/stores/websocket.old.backup
mv frontend/src/composables/useWebSocket.js frontend/src/composables/useWebSocket.old.backup
```

### Step 5.2: Rename New Files

```bash
# Rename V2 files to production names
mv frontend/src/stores/websocketV2.js frontend/src/stores/websocket.js
mv frontend/src/composables/useWebSocketV2.js frontend/src/composables/useWebSocket.js
```

### Step 5.3: Update Imports

Update all imports to use new names (remove V2 suffix).

---

## Validation Checklist

- [ ] All WebSocket features still work
- [ ] Project orchestration updates work
- [ ] Agent job monitoring works
- [ ] Succession timeline updates work
- [ ] Reconnection works properly
- [ ] No memory leaks
- [ ] No console errors
- [ ] Performance improved or same
- [ ] Code reduction achieved (~40%)

---

## Rollback Plan

If ANYTHING breaks:

```bash
# Immediate rollback
git checkout -- frontend/src/

# Or restore backups
mv frontend/src/services/websocket.js.backup frontend/src/services/websocket.js
mv frontend/src/services/flowWebSocket.js.backup frontend/src/services/flowWebSocket.js
# ... restore all backups
```

---

## Risk Assessment

**Risk 1: Breaking Real-Time Updates**
- **Impact:** CRITICAL
- **Mitigation:** Test every update type before migration

**Risk 2: Memory Leaks**
- **Impact:** HIGH
- **Mitigation:** Chrome DevTools heap snapshots

**Risk 3: Lost Messages**
- **Impact:** HIGH
- **Mitigation:** Message queue implementation

---

## Success Metrics

### Before
- 4 files, 1,344 lines
- 4-layer indirection
- Multiple reconnection systems
- Confusing architecture

### After
- 2 files, ~600 lines
- 2-layer clean architecture
- Single reconnection system
- 40% code reduction
- Easier to understand and maintain

---

**REMEMBER: IT WORKS NOW - BE EXTREMELY CAREFUL!**

---

**Created:** 2025-11-10
**Priority:** P1 (But approach with caution)
**Complete After:** Backend is stable