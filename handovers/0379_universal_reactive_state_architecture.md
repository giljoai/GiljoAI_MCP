# Handover 0379: Universal Reactive State Architecture (MERGED with 0377)

**Priority**: CRITICAL
**Effort**: 50-60 hours (5 phases)
**Risk**: Medium (architectural change, high complexity)
**Created**: 2025-12-25
**Updated**: 2025-12-25 (merged with 0377 backend unification)
**Renumbered From**: 0375 (renamed to avoid collision with completed 0375)
**Scope**: LAN/WAN MVP + SaaS-Ready Architecture
**Supersedes**: Handovers 0292, 0358, 0362, 0377 (consolidated approach)
**User Requirement**: "Robust LAN/WAN implementation with frameworks for SaaS in 6 months. Exceptional foundation for MVP launch."

---

## CRITICAL: Why Original 0375 (Pre-Merge) Would Have Failed

### Gaps Identified by 0377 (Codex GPT-5.2 Deep Review)

| Gap | Original 0375 Status | Why It Matters |
|-----|----------------------|----------------|
| **Loopback ws-bridge** | Not addressed | 12+ files POST to `localhost:7272`, breaks in hosted/proxy |
| **Event name drift** | Not addressed | `agent_update` vs `agent:update` causes silent failures |
| **Multiple broadcast paths** | Partially addressed | 4 different emitters still active |
| **Reconnect resync** | Not addressed | Missed events = stale UI until manual refresh |
| **Subscription refcount** | Not addressed | One unmount can unsubscribe all components |
| **SaaS/multi-worker** | Not addressed | In-memory connections fail with workers > 1 |
| **Wrong file reference** | Phase 4 error | Says `api/websocket_manager.py`, should be `api/websocket.py` |

### VERIFIED ISSUES (Confirmed via Grep)

1. **Event name mismatch**:
   - `frontend/src/stores/websocketIntegrations.js:39` listens for `agent_update` (underscore)
   - `frontend/src/stores/agents.js:373` listens for `agent:update` (colon)

2. **12 files use ws-bridge loopback**: project_service, orchestration_service, tools/*

3. **WebSocketManager is in `api/websocket.py`** (40 methods), NOT `api/websocket_manager.py` (which is a shim)

---

## User Challenge (MANDATORY - Read First)

> "I bet, after you do this implementation it will not work, and I will ask you to diagnose, and again you will try and bandaid it and revert, so I want you to write a handover document... Prove me wrong. Research this in depth, make plan, follow TDD principles red-green but only moderately, you also tend to get stuck in just test building mode."

> "Does this project address the ENTIRE application's websocket updates for every aspect, every state, every toggle, every auto update in backend etc, this is not just about jobs and agents... I want a singular, scalable, easily maintainable and reliable websocket platform."

**This challenge must be addressed.** The implementation team must:
1. NOT revert to bandaids when issues arise
2. Fix root causes, not symptoms
3. Build a foundation that works for ALL future WebSocket scenarios
4. Follow TDD but not get stuck in test-only mode
5. Cover ENTIRE application: buttons, states, backend updates, toggles, badges, cards

---

## Executive Summary
 
Complete WebSocket state management overhaul to create a singular, scalable, reliable platform. This merged approach combines 0375's frontend architecture with 0377's backend unification for a complete solution.
 
## Execution Breakdown (Read This Before Coding)
This master document is intentionally comprehensive. Implementation should be executed via the split handovers:
- `handovers/0379a_event_router_infrastructure_and_resync.md` (Phase 1)
- `handovers/0379b_agent_jobs_domain_migration.md` (Phase 2)
- `handovers/0379c_messages_and_project_state_migration.md` (Phase 3)
- `handovers/0379d_backend_event_contract_and_broadcast_unification.md` (Phase 4)
- `handovers/0379e_saas_broker_and_loopback_elimination.md` (Phase 5)
 
Backend deep reference (optional): `handovers/Reference_docs/0379_reference_backend_realtime_unification_and_saas_hardening.md`

### What Makes This Different

1. **EVENT_MAP**: Single source of truth for ALL 35 WebSocket events
2. **Map-Based Stores**: O(1) lookups, not array scanning
3. **Immutable Updates**: Never mutate, always replace
4. **Composables**: Direct store subscription, no props drilling
5. **Reconnect Resync**: Automatic state refresh after disconnect
6. **Subscription Refcount**: Safe shared subscriptions
7. **Broker Abstraction**: SaaS-ready from day one
8. **5-Phase Rollout**: Explicit rollback per phase

---

## Root Cause Analysis (7 Fundamental Design Flaws)

### Flaw 1: Duplicate Handler Registration

**Location**: `frontend/src/stores/agents.js:58-82`, `messages.js:45-67`

```javascript
// CURRENT BUG: Handlers auto-register at module import
const wsStore = useWebSocketStore()
wsStore.on('agent:updated', (data) => {  // Registers on EVERY import
  // Handler logic
})
```

**Why it fails**: Every component importing the store registers another handler. After 3 tab switches = 3 duplicate handlers = 3 UI updates per event.

### Flaw 2: Props Mutation Pattern

**Location**: `frontend/src/components/projects/JobsTab.vue:1173`

```javascript
// CURRENT BUG: Component mutates received props
props.agents[i].messages.push(newMessage)  // Direct mutation
```

**Why it fails**: Vue can't track mutations on props received from parent. Parent's computed getter returns new array reference, breaking the chain.

### Flaw 3: Spread Operator Reactivity Break

**Location**: `frontend/src/stores/projectTabs.js:74`

```javascript
// CURRENT BUG: Getter creates new array every call
sortedAgents: (state) => {
  return [...state.agents].sort((a, b) => { ... })  // NEW reference
}
```

**Why it fails**: Nested object mutations (`agent.messages.push()`) don't trigger getter recalculation. Vue sees same array length, skips re-render.

### Flaw 4: Split Handler Architecture

**Current flow causes missed updates**:
```
WebSocket Event
    |
websocketIntegrations.js -> projectTabsStore.handleMessageSent()
    |
store.agents[i].messages.push(...)  // Mutates in place
    |
store.sortedAgents (getter) -> creates new array
    |
:agents="store.sortedAgents" -> JobsTab receives prop
    |
JobsTab uses props.agents -> MAY NOT see mutation
```

### Flaw 5: Event Name Drift (FROM 0377)

**Location**: `frontend/src/stores/websocketIntegrations.js:39` vs `frontend/src/stores/agents.js:373`

```javascript
// websocketIntegrations.js:39
case 'agent_update':  // UNDERSCORE

// agents.js:373
wsStore.on('agent:update', ...)  // COLON
```

**Why it fails**: Backend may emit one format, frontend listens for another. Events silently dropped.

### Flaw 6: HTTP Loopback for In-Process Code (FROM 0377)

**Location**: `src/giljo_mcp/services/project_service.py:2602`

```python
# CURRENT BUG: In-process code uses HTTP loopback
async def _broadcast_mission_update(self, project_id: str, mission: str):
    async with httpx.AsyncClient() as client:
        await client.post("http://localhost:7272/api/v1/ws-bridge/emit", ...)
```

**Why it fails**:
- Wrong host/port in hosted/proxy installs
- Extra network hop and timeout
- Breaks under multi-worker routing (request lands on worker with zero sockets)

### Flaw 7: No Reconnect Resync (FROM 0377)

**Location**: `frontend/src/stores/websocket.js`

**Why it fails**: When WebSocket reconnects after brief disconnect, any events missed during disconnect leave UI stale until manual page refresh.

---

## Architectural Solution: Centralized Event Router + Backend Unification

### Design Principles

1. **Single Source of Truth**: EVENT_MAP defines all routing
2. **Map-Based Storage**: O(1) lookups by ID
3. **Immutable Updates**: Replace objects, never mutate
4. **Composables**: Direct store subscription
5. **No Auto-Init**: Explicit initialization only
6. **Reconnect Resync**: Refetch critical state after reconnect
7. **Subscription Refcount**: Safe shared subscriptions
8. **Broker Abstraction**: SaaS-ready pub/sub

### New Architecture

```
                    WEBSOCKET LAYER (existing)
                    websocket.js -> receives events from backend
                              |
                              v
                    EVENT ROUTER (NEW)
                    websocketEventRouter.js -> Central routing via EVENT_MAP
                    - Single source of truth for all 35 events
                    - Payload normalization
                    - Filter & transform support
                    - Reconnect resync trigger
                              |
                              v
                    DOMAIN STORES (Map-Based)
                    agentJobsStore.js     -> Agent/job state (Map<id, AgentJob>)
                    projectMessagesStore.js -> Messages (Map<projectId, Message[]>)
                    projectStateStore.js  -> Project state (activation, staging)
                    systemStore.js        -> System notifications, progress
                              |
                              v
                    COMPOSABLES
                    useAgentJobs(projectId)    -> Reactive agent data
                    useProjectMessages(projectId) -> Reactive messages
                    useProjectState(projectId) -> Aggregated project state
                              |
                              v
                    COMPONENTS
                    JobsTab.vue       -> Uses composables directly
                    LaunchTab.vue     -> Uses composables directly
                    ProjectTabs.vue   -> Uses composables directly
                    AgentTableView.vue -> Uses composables directly


                    BACKEND UNIFICATION (FROM 0377)

Application Code -> broker.publish("agent:updated", payload, tenant)
                              |
                              v
                    BROKER ABSTRACTION
                    WebSocketEventBroker (interface)
                    |-- InMemoryBroker (default - single server LAN)
                    |-- PostgresNotifyBroker (LISTEN/NOTIFY - no new infra)
                    +-- RedisPubSubBroker (optional - high scale)
                              |
                              v
                    PER-WORKER BROADCAST
                    Each worker subscribes to broker
                    On receive: broadcast to local WebSocket connections
```

---

## PHASE 1: Infrastructure Foundation + Reconnect Resync (10-12 hours)

### Goal
Build reactive infrastructure without touching existing components. Zero risk - all new files.

### Files to Create

#### 1. `frontend/src/stores/websocketEventRouter.js`

**Purpose**: Single event-to-store mapping, replaces scattered handlers

```javascript
// frontend/src/stores/websocketEventRouter.js
import { useAgentJobsStore } from './agentJobsStore'
import { useProjectMessagesStore } from './projectMessagesStore'
import { useProjectStateStore } from './projectStateStore'
import { useProductsStore } from './products'
import { useSystemStore } from './systemStore'

/**
 * EVENT_MAP: Single source of truth for WebSocket event routing
 *
 * Structure:
 * - key: WebSocket event type (string)
 * - value: { store, action, filter?, transform?, description }
 */
const EVENT_MAP = {
  // ============================================
  // AGENT EVENTS (10)
  // ============================================
  'agent:created': {
    store: 'agentJobs',
    action: 'handleCreated',
    description: 'New agent job created'
  },
  'agent:updated': {
    store: 'agentJobs',
    action: 'handleUpdated',
    description: 'Agent job updated (status, progress, etc.)'
  },
  'agent_update': {
    store: 'agentJobs',
    action: 'handleUpdated',
    description: 'LEGACY: Alias for agent:updated'
  },
  'agent:status_changed': {
    store: 'agentJobs',
    action: 'handleStatusChanged',
    description: 'Agent status transition (waiting -> working -> completed)'
  },
  'agent:health_alert': {
    store: 'agentJobs',
    action: 'handleHealthAlert',
    description: 'Agent health degraded (staleness, errors)'
  },
  'agent:health_recovered': {
    store: 'agentJobs',
    action: 'handleHealthRecovered',
    description: 'Agent health restored'
  },
  'agent:auto_failed': {
    store: 'agentJobs',
    action: 'handleAutoFailed',
    description: 'Agent failed due to timeout/error'
  },
  'agent:complete': {
    store: 'agentJobs',
    action: 'handleComplete',
    description: 'Agent completed its work'
  },
  'agent:spawn': {
    store: 'agentJobs',
    action: 'handleCreated',
    description: 'LEGACY: Alias for agent:created'
  },
  'agent:mission_acknowledged': {
    store: 'agentJobs',
    action: 'handleMissionAcknowledged',
    description: 'Agent acknowledged its mission'
  },

  // ============================================
  // MESSAGE EVENTS (5)
  // ============================================
  'message:sent': {
    store: 'projectMessages',
    action: 'handleSent',
    description: 'Message sent by agent'
  },
  'message:received': {
    store: 'projectMessages',
    action: 'handleReceived',
    description: 'Message received by agent'
  },
  'message:acknowledged': {
    store: 'projectMessages',
    action: 'handleAcknowledged',
    description: 'Message marked as read'
  },
  'message:new': {
    store: 'projectMessages',
    action: 'handleNew',
    description: 'New message in system'
  },
  'message': {
    store: 'projectMessages',
    action: 'handleNew',
    description: 'LEGACY: Alias for message:new'
  },

  // ============================================
  // PROJECT EVENTS (5)
  // ============================================
  'project:activated': {
    store: 'projectState',
    action: 'handleActivated',
    description: 'Project activated for orchestration'
  },
  'project:deactivated': {
    store: 'projectState',
    action: 'handleDeactivated',
    description: 'Project deactivated'
  },
  'project:mission_updated': {
    store: 'projectState',
    action: 'handleMissionUpdated',
    description: 'Project mission/plan updated'
  },
  'project:completed': {
    store: 'projectState',
    action: 'handleCompleted',
    description: 'Project marked complete'
  },
  'project_update': {
    store: 'projectState',
    action: 'handleUpdated',
    description: 'LEGACY: General project update'
  },

  // ============================================
  // PRODUCT EVENTS (3)
  // ============================================
  'product:memory_updated': {
    store: 'products',
    action: 'handleMemoryUpdated',
    description: '360 Memory updated'
  },
  'product:learning_added': {
    store: 'products',
    action: 'handleLearningAdded',
    description: 'New learning added to product'
  },
  'product:status_changed': {
    store: 'products',
    action: 'handleStatusChanged',
    description: 'Product status changed'
  },

  // ============================================
  // JOB EVENTS (2)
  // ============================================
  'job:mission_acknowledged': {
    store: 'agentJobs',
    action: 'handleMissionAcknowledged',
    description: 'Job mission acknowledged'
  },
  'entity_update': {
    store: 'agentJobs',
    action: 'handleEntityUpdate',
    filter: (payload) => payload.entity_type === 'agent_job',
    description: 'DEPRECATED: Use domain-specific events'
  },

  // ============================================
  // SYSTEM EVENTS (4)
  // ============================================
  'system:progress': {
    store: 'system',
    action: 'handleProgress',
    description: 'Operation progress update'
  },
  'system:notification': {
    store: 'system',
    action: 'handleNotification',
    description: 'System notification'
  },
  'progress': {
    store: 'system',
    action: 'handleProgress',
    description: 'LEGACY: Alias for system:progress'
  },
  'notification': {
    store: 'system',
    action: 'handleNotification',
    description: 'LEGACY: Alias for system:notification'
  },

  // ============================================
  // ORCHESTRATOR EVENTS (4)
  // ============================================
  'orchestrator:staging_started': {
    store: 'projectState',
    action: 'handleStagingStarted',
    description: 'Orchestrator began staging'
  },
  'orchestrator:staging_complete': {
    store: 'projectState',
    action: 'handleStagingComplete',
    description: 'Orchestrator finished staging'
  },
  'orchestrator:succession': {
    store: 'agentJobs',
    action: 'handleSuccession',
    description: 'Orchestrator succession triggered'
  },
  'orchestrator:context_warning': {
    store: 'agentJobs',
    action: 'handleContextWarning',
    description: 'Context limit approaching'
  },

  // ============================================
  // WORKFLOW EVENTS (2)
  // ============================================
  'workflow:status_changed': {
    store: 'projectState',
    action: 'handleWorkflowStatusChanged',
    description: 'Workflow status changed'
  },
  'workflow:progress': {
    store: 'projectState',
    action: 'handleWorkflowProgress',
    description: 'Workflow progress update'
  }
}

// Store registry for lazy loading
const STORE_REGISTRY = {
  agentJobs: () => useAgentJobsStore(),
  projectMessages: () => useProjectMessagesStore(),
  projectState: () => useProjectStateStore(),
  products: () => useProductsStore(),
  system: () => useSystemStore()
}

// State
let isInitialized = false
const registeredHandlers = new Set()
let debugMode = false

/**
 * Normalize payload to handle both { data: {...} } and flat structures
 */
function normalizePayload(rawData) {
  if (!rawData) return {}

  // Handle wrapped payloads: { type: 'x', data: { ... } }
  if (rawData.data && typeof rawData.data === 'object') {
    return { ...rawData.data, _originalType: rawData.type }
  }

  // Flat payload
  return rawData
}

/**
 * Get store instance by name
 */
function getStore(storeName) {
  const factory = STORE_REGISTRY[storeName]
  if (!factory) {
    console.error(`[EventRouter] Unknown store: ${storeName}`)
    return null
  }
  return factory()
}

/**
 * Perform resync after reconnection
 * Called automatically when WebSocket reconnects
 */
async function performReconnectResync() {
  if (debugMode) {
    console.log('[EventRouter] Performing reconnect resync...')
  }

  try {
    const projectStateStore = getStore('projectState')
    const agentJobsStore = getStore('agentJobs')

    // Get current project context
    const currentProjectId = projectStateStore?.currentProjectId

    if (currentProjectId) {
      // Refetch critical state in parallel
      await Promise.all([
        agentJobsStore?.fetchJobsByProject(currentProjectId),
        projectStateStore?.refreshProjectState()
      ])

      if (debugMode) {
        console.log('[EventRouter] Reconnect resync complete for project:', currentProjectId)
      }
    }
  } catch (error) {
    console.error('[EventRouter] Reconnect resync failed:', error)
  }
}

/**
 * Initialize the event router
 *
 * @param {Object} wsStore - The WebSocket store instance
 * @param {Object} options - Configuration options
 * @param {boolean} options.debug - Enable debug logging
 */
export function initEventRouter(wsStore, options = {}) {
  if (isInitialized) {
    console.warn('[EventRouter] Already initialized, skipping')
    return
  }

  debugMode = options.debug || false

  if (debugMode) {
    console.log('[EventRouter] Initializing with', Object.keys(EVENT_MAP).length, 'events')
  }

  // Register reconnect handler for resync
  wsStore.onReconnected(performReconnectResync)

  // Register handlers for each event type
  Object.entries(EVENT_MAP).forEach(([eventType, config]) => {
    if (registeredHandlers.has(eventType)) {
      console.warn(`[EventRouter] Handler already registered for ${eventType}`)
      return
    }

    wsStore.on(eventType, (rawData) => {
      try {
        // Normalize payload
        const payload = normalizePayload(rawData)

        // Apply filter if present
        if (config.filter && !config.filter(payload, STORE_REGISTRY)) {
          if (debugMode) {
            console.log(`[EventRouter] ${eventType} filtered out`)
          }
          return
        }

        // Transform if needed
        const finalPayload = config.transform ? config.transform(payload) : payload

        // Get store and call action
        const store = getStore(config.store)
        if (store && typeof store[config.action] === 'function') {
          store[config.action](finalPayload)

          if (debugMode) {
            console.log(`[EventRouter] ${eventType} -> ${config.store}.${config.action}()`, finalPayload)
          }
        } else {
          console.error(`[EventRouter] Missing action: ${config.store}.${config.action}`)
        }
      } catch (error) {
        console.error(`[EventRouter] Error handling ${eventType}:`, error)
      }
    })

    registeredHandlers.add(eventType)
  })

  isInitialized = true

  if (debugMode) {
    console.log('[EventRouter] Initialization complete')
  }
}

/**
 * Cleanup event router (for testing or logout)
 */
export function cleanupEventRouter(wsStore) {
  registeredHandlers.forEach(eventType => {
    wsStore.off(eventType)
  })
  registeredHandlers.clear()
  isInitialized = false

  if (debugMode) {
    console.log('[EventRouter] Cleanup complete')
  }
}

/**
 * Check if event router is initialized
 */
export function isEventRouterInitialized() {
  return isInitialized
}

/**
 * Get list of registered event types (for debugging)
 */
export function getRegisteredEvents() {
  return Array.from(registeredHandlers)
}

/**
 * Enable/disable debug mode
 */
export function setDebugMode(enabled) {
  debugMode = enabled
}

/**
 * Manually trigger reconnect resync (for testing)
 */
export function triggerResync() {
  return performReconnectResync()
}

export { EVENT_MAP }
```

#### 2. `frontend/src/utils/immutableHelpers.js`

**Purpose**: Safe update utilities that guarantee Vue reactivity

```javascript
// frontend/src/utils/immutableHelpers.js

/**
 * Immutable array operations for Vue 3 reactivity
 *
 * These helpers ensure Vue's reactivity system detects changes
 * by always returning new array/object references.
 */

/**
 * Add item to array (immutable)
 * @param {Array} array - Source array
 * @param {*} item - Item to add
 * @returns {Array} New array with item added
 */
export function addToArray(array, item) {
  return [...(array || []), item]
}

/**
 * Remove item from array by predicate (immutable)
 * @param {Array} array - Source array
 * @param {Function} predicate - Function to match item to remove
 * @returns {Array} New array without matched items
 */
export function removeFromArray(array, predicate) {
  return (array || []).filter(item => !predicate(item))
}

/**
 * Remove item from array by ID (immutable)
 * @param {Array} array - Source array
 * @param {string} id - ID of item to remove
 * @param {string} idField - Field name for ID (default: 'id')
 * @returns {Array} New array without item
 */
export function removeById(array, id, idField = 'id') {
  return removeFromArray(array, item => item[idField] === id)
}

/**
 * Update item in array (immutable)
 * @param {Array} array - Source array
 * @param {string} id - ID of item to update
 * @param {Object} updates - Fields to update
 * @param {string} idField - Field name for ID (default: 'id')
 * @returns {Array} New array with updated item
 */
export function updateInArray(array, id, updates, idField = 'id') {
  return (array || []).map(item =>
    item[idField] === id ? { ...item, ...updates } : item
  )
}

/**
 * Upsert item in array (immutable)
 * @param {Array} array - Source array
 * @param {Object} item - Item to upsert
 * @param {string} idField - Field name for ID (default: 'id')
 * @returns {Array} New array with item added or updated
 */
export function upsertInArray(array, item, idField = 'id') {
  const existing = (array || []).find(i => i[idField] === item[idField])
  if (existing) {
    return updateInArray(array, item[idField], item, idField)
  }
  return addToArray(array, item)
}

/**
 * Update Map entry (immutable object replacement)
 * @param {Map} map - Source Map
 * @param {string} key - Key to update
 * @param {Object} updates - Fields to update
 * @returns {void} Mutates Map with new object reference
 */
export function updateMapEntry(map, key, updates) {
  const existing = map.get(key)
  if (existing) {
    map.set(key, { ...existing, ...updates })
  }
}

/**
 * Add nested array item (immutable)
 * @param {Map} map - Source Map
 * @param {string} key - Key of parent object
 * @param {string} arrayField - Field name of nested array
 * @param {*} item - Item to add
 * @returns {void} Mutates Map with new object reference
 */
export function addToNestedArray(map, key, arrayField, item) {
  const existing = map.get(key)
  if (existing) {
    map.set(key, {
      ...existing,
      [arrayField]: [...(existing[arrayField] || []), item]
    })
  }
}

/**
 * Update nested array item (immutable)
 * @param {Map} map - Source Map
 * @param {string} key - Key of parent object
 * @param {string} arrayField - Field name of nested array
 * @param {string} itemId - ID of item to update
 * @param {Object} updates - Fields to update
 * @param {string} idField - Field name for ID (default: 'id')
 * @returns {void} Mutates Map with new object reference
 */
export function updateNestedArrayItem(map, key, arrayField, itemId, updates, idField = 'id') {
  const existing = map.get(key)
  if (existing && existing[arrayField]) {
    map.set(key, {
      ...existing,
      [arrayField]: updateInArray(existing[arrayField], itemId, updates, idField)
    })
  }
}

/**
 * Deep clone object (for safety when needed)
 * @param {Object} obj - Object to clone
 * @returns {Object} Deep cloned object
 */
export function deepClone(obj) {
  return JSON.parse(JSON.stringify(obj))
}

/**
 * Merge objects shallowly (for updates)
 * @param {Object} target - Target object
 * @param {Object} source - Source object
 * @returns {Object} New merged object
 */
export function shallowMerge(target, source) {
  return { ...target, ...source }
}
```

#### 3. WebSocket Store Updates for Subscription Refcounting

**Add to `frontend/src/stores/websocket.js`**:

```javascript
// Add subscription refcounting (Phase 1 addition from 0377)

// BEFORE (fragile - boolean tracking)
// subscriptions: { 'project:123': true }

// AFTER (safe - refcount tracking)
const subscriptionRefCounts = ref(new Map())  // key -> count

/**
 * Subscribe to a channel with refcounting
 * Multiple components can subscribe; actual unsubscribe only when count reaches 0
 */
function subscribe(channel) {
  const currentCount = subscriptionRefCounts.value.get(channel) || 0
  subscriptionRefCounts.value.set(channel, currentCount + 1)

  // Only actually subscribe on first subscription
  if (currentCount === 0) {
    _actuallySubscribe(channel)
  }
}

/**
 * Unsubscribe from a channel with refcounting
 * Only actually unsubscribes when refcount reaches 0
 */
function unsubscribe(channel) {
  const currentCount = subscriptionRefCounts.value.get(channel) || 0

  if (currentCount <= 1) {
    subscriptionRefCounts.value.delete(channel)
    _actuallyUnsubscribe(channel)
  } else {
    subscriptionRefCounts.value.set(channel, currentCount - 1)
  }
}

/**
 * Get subscription count for a channel (for debugging)
 */
function getSubscriptionCount(channel) {
  return subscriptionRefCounts.value.get(channel) || 0
}

/**
 * Register reconnect callback
 */
const reconnectCallbacks = []
function onReconnected(callback) {
  reconnectCallbacks.push(callback)
}

/**
 * Called internally when WebSocket reconnects
 */
function _handleReconnect() {
  // Execute all reconnect callbacks
  reconnectCallbacks.forEach(cb => {
    try {
      cb()
    } catch (error) {
      console.error('[WebSocket] Reconnect callback error:', error)
    }
  })
}
```

#### 4. `frontend/src/stores/templates/domainStoreTemplate.js`

**Purpose**: Reference implementation for domain stores (see original handover for full code)

#### 5. `frontend/src/composables/templates/domainComposableTemplate.js`

**Purpose**: Reference implementation for domain composables (see original handover for full code)

### Phase 1 Tests

```javascript
// frontend/src/stores/__tests__/websocketEventRouter.spec.js
// (See original handover for full test suite)

// Additional tests for reconnect resync
describe('reconnect resync', () => {
  it('should call resync on reconnection', async () => {
    const mockAgentStore = { fetchJobsByProject: vi.fn() }
    const mockProjectStore = { currentProjectId: 'proj-1', refreshProjectState: vi.fn() }

    // Mock store registry
    vi.spyOn(STORE_REGISTRY, 'agentJobs').mockReturnValue(mockAgentStore)
    vi.spyOn(STORE_REGISTRY, 'projectState').mockReturnValue(mockProjectStore)

    await triggerResync()

    expect(mockAgentStore.fetchJobsByProject).toHaveBeenCalledWith('proj-1')
    expect(mockProjectStore.refreshProjectState).toHaveBeenCalled()
  })
})
```

```javascript
// frontend/src/stores/__tests__/subscriptionRefcount.spec.js

describe('subscription refcounting', () => {
  it('should track multiple subscriptions', () => {
    const store = useWebSocketStore()

    store.subscribe('project:123')
    store.subscribe('project:123')

    expect(store.getSubscriptionCount('project:123')).toBe(2)
  })

  it('should only unsubscribe when count reaches zero', () => {
    const store = useWebSocketStore()
    const unsubSpy = vi.spyOn(store, '_actuallyUnsubscribe')

    store.subscribe('project:123')
    store.subscribe('project:123')
    store.unsubscribe('project:123')

    expect(unsubSpy).not.toHaveBeenCalled()
    expect(store.getSubscriptionCount('project:123')).toBe(1)

    store.unsubscribe('project:123')

    expect(unsubSpy).toHaveBeenCalledWith('project:123')
  })
})
```

### Phase 1 Rollback

**If Phase 1 fails**: Delete new files only. Zero impact on existing code.
- Delete: `websocketEventRouter.js`, `immutableHelpers.js`, template files
- Time: 5 minutes

---

## PHASE 2: Agent/Job Domain (10-12 hours)

### Goal
Fix user-reported bugs: message counters, tab switching, agent status updates

### Files to Create

#### 1. `frontend/src/stores/agentJobsStore.js`

```javascript
// frontend/src/stores/agentJobsStore.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { addToNestedArray, updateMapEntry } from '@/utils/immutableHelpers'
import api from '@/services/api'

export const useAgentJobsStore = defineStore('agentJobs', () => {
  // ============================================
  // STATE
  // ============================================
  const jobsMap = ref(new Map())
  const isLoading = ref(false)
  const error = ref(null)
  const currentProjectId = ref(null)

  // ============================================
  // COMPUTED
  // ============================================
  const jobs = computed(() => Array.from(jobsMap.value.values()))

  const jobsByProject = computed(() => {
    if (!currentProjectId.value) return jobs.value
    return jobs.value.filter(job => job.project_id === currentProjectId.value)
  })

  const sortedJobs = computed(() => {
    return [...jobsByProject.value].sort((a, b) => {
      // Orchestrator first
      if (a.agent_type === 'orchestrator') return -1
      if (b.agent_type === 'orchestrator') return 1
      // Then by created_at
      return new Date(a.created_at) - new Date(b.created_at)
    })
  })

  const orchestrator = computed(() =>
    jobsByProject.value.find(job => job.agent_type === 'orchestrator')
  )

  const activeJobsCount = computed(() =>
    jobsByProject.value.filter(job =>
      ['waiting', 'working', 'staging'].includes(job.status)
    ).length
  )

  const completedJobsCount = computed(() =>
    jobsByProject.value.filter(job => job.status === 'completed').length
  )

  const allJobsComplete = computed(() =>
    jobsByProject.value.length > 0 &&
    jobsByProject.value.every(job => job.status === 'completed')
  )

  // ============================================
  // GETTERS
  // ============================================
  function getById(id) {
    return jobsMap.value.get(id)
  }

  function getMessagesSent(jobId) {
    const job = jobsMap.value.get(jobId)
    if (!job || !job.messages) return 0
    return job.messages.filter(m => m.direction === 'outbound').length
  }

  function getMessagesReceived(jobId) {
    const job = jobsMap.value.get(jobId)
    if (!job || !job.messages) return 0
    return job.messages.filter(m => m.direction === 'inbound').length
  }

  function getMessagesWaiting(jobId) {
    const job = jobsMap.value.get(jobId)
    if (!job || !job.messages) return 0
    return job.messages.filter(m =>
      m.direction === 'inbound' && m.status !== 'read'
    ).length
  }

  // ============================================
  // ACTIONS (API)
  // ============================================
  async function fetchJobs(filters = {}) {
    isLoading.value = true
    error.value = null

    try {
      const response = await api.get('/agent-jobs', { params: filters })
      const newMap = new Map()
      response.data.forEach(job => {
        // Ensure messages array exists
        if (!job.messages) job.messages = []
        newMap.set(job.id, job)
      })
      jobsMap.value = newMap

      if (filters.project_id) {
        currentProjectId.value = filters.project_id
      }
    } catch (err) {
      error.value = err.message
      console.error('[AgentJobsStore] Fetch error:', err)
    } finally {
      isLoading.value = false
    }
  }

  async function fetchJobsByProject(projectId) {
    currentProjectId.value = projectId
    return fetchJobs({ project_id: projectId })
  }

  // ============================================
  // WEBSOCKET HANDLERS
  // ============================================
  function handleCreated(payload) {
    const { id, agent_id } = payload
    const jobId = id || agent_id
    if (!jobId) return

    // Ensure messages array
    const job = { ...payload, id: jobId, messages: payload.messages || [] }
    jobsMap.value.set(jobId, job)
  }

  function handleUpdated(payload) {
    const { id, agent_id, ...updates } = payload
    const jobId = id || agent_id
    if (!jobId) return

    updateMapEntry(jobsMap.value, jobId, updates)
  }

  function handleStatusChanged(payload) {
    const { id, agent_id, status, previous_status } = payload
    const jobId = id || agent_id
    if (!jobId) return

    updateMapEntry(jobsMap.value, jobId, {
      status,
      previous_status,
      status_changed_at: new Date().toISOString()
    })
  }

  function handleHealthAlert(payload) {
    const { id, agent_id, health_status, alert_message } = payload
    const jobId = id || agent_id
    if (!jobId) return

    updateMapEntry(jobsMap.value, jobId, {
      health_status,
      health_alert: alert_message,
      health_alert_at: new Date().toISOString()
    })
  }

  function handleHealthRecovered(payload) {
    const { id, agent_id } = payload
    const jobId = id || agent_id
    if (!jobId) return

    updateMapEntry(jobsMap.value, jobId, {
      health_status: 'healthy',
      health_alert: null,
      health_recovered_at: new Date().toISOString()
    })
  }

  function handleAutoFailed(payload) {
    const { id, agent_id, reason } = payload
    const jobId = id || agent_id
    if (!jobId) return

    updateMapEntry(jobsMap.value, jobId, {
      status: 'failed',
      failure_reason: reason,
      failed_at: new Date().toISOString()
    })
  }

  function handleComplete(payload) {
    const { id, agent_id, result } = payload
    const jobId = id || agent_id
    if (!jobId) return

    updateMapEntry(jobsMap.value, jobId, {
      status: 'completed',
      result,
      completed_at: new Date().toISOString()
    })
  }

  function handleMissionAcknowledged(payload) {
    const { id, agent_id, job_id } = payload
    const jobId = id || agent_id || job_id
    if (!jobId) return

    updateMapEntry(jobsMap.value, jobId, {
      mission_acknowledged: true,
      mission_acknowledged_at: new Date().toISOString()
    })
  }

  function handleEntityUpdate(payload) {
    // Legacy handler for entity_update events
    if (payload.entity_type !== 'agent_job') return
    handleUpdated(payload)
  }

  function handleSuccession(payload) {
    const { old_orchestrator_id, new_orchestrator_id, reason } = payload
    if (old_orchestrator_id) {
      updateMapEntry(jobsMap.value, old_orchestrator_id, {
        status: 'succeeded',
        succession_reason: reason,
        succeeded_at: new Date().toISOString()
      })
    }
    // New orchestrator will be added via agent:created event
  }

  function handleContextWarning(payload) {
    const { id, agent_id, context_percent, threshold } = payload
    const jobId = id || agent_id
    if (!jobId) return

    updateMapEntry(jobsMap.value, jobId, {
      context_warning: true,
      context_percent,
      context_threshold: threshold
    })
  }

  // ============================================
  // MESSAGE HANDLERS (from projectMessages cross-reference)
  // ============================================
  function addMessageToJob(jobId, message) {
    addToNestedArray(jobsMap.value, jobId, 'messages', message)
  }

  function markMessageRead(jobId, messageId) {
    const job = jobsMap.value.get(jobId)
    if (!job || !job.messages) return

    const updatedMessages = job.messages.map(m =>
      m.id === messageId ? { ...m, status: 'read' } : m
    )

    jobsMap.value.set(jobId, { ...job, messages: updatedMessages })
  }

  // ============================================
  // UTILITY
  // ============================================
  function clear() {
    jobsMap.value = new Map()
    currentProjectId.value = null
    error.value = null
  }

  function setCurrentProject(projectId) {
    currentProjectId.value = projectId
  }

  // ============================================
  // RETURN
  // ============================================
  return {
    // State
    jobsMap,
    isLoading,
    error,
    currentProjectId,

    // Computed
    jobs,
    jobsByProject,
    sortedJobs,
    orchestrator,
    activeJobsCount,
    completedJobsCount,
    allJobsComplete,

    // Getters
    getById,
    getMessagesSent,
    getMessagesReceived,
    getMessagesWaiting,

    // API Actions
    fetchJobs,
    fetchJobsByProject,

    // WebSocket Handlers
    handleCreated,
    handleUpdated,
    handleStatusChanged,
    handleHealthAlert,
    handleHealthRecovered,
    handleAutoFailed,
    handleComplete,
    handleMissionAcknowledged,
    handleEntityUpdate,
    handleSuccession,
    handleContextWarning,

    // Message Handlers
    addMessageToJob,
    markMessageRead,

    // Utility
    clear,
    setCurrentProject
  }
})
```

#### 2. `frontend/src/composables/useAgentJobs.js`

(See original handover for full implementation)

### Phase 2 Rollback

**If Phase 2 fails**: Revert JobsTab.vue changes only.
- Restore original props-based implementation
- Keep Phase 1 infrastructure (still useful)
- Time: 30 minutes

---

## PHASE 3: Messages + Subscription Refcounting (10-12 hours)

### Goal
Complete message system, project state management, and subscription safety.

### Files to Create

1. `frontend/src/stores/projectMessagesStore.js`
2. `frontend/src/stores/projectStateStore.js`
3. `frontend/src/stores/systemStore.js`
4. `frontend/src/composables/useProjectMessages.js`
5. `frontend/src/composables/useProjectState.js`

### Files to Refactor

1. `frontend/src/stores/projectTabs.js` - Remove agent/message state, keep navigation only
2. `frontend/src/stores/websocketIntegrations.js` - Remove, replaced by EventRouter
3. `frontend/src/stores/websocket.js` - Add subscription refcounting
4. `frontend/src/components/projects/ProjectTabs.vue` - Use composables
5. `frontend/src/components/projects/LaunchTab.vue` - Use composables

### Phase 3 Rollback

**If Phase 3 fails**: Revert LaunchTab.vue, ProjectTabs.vue, websocket.js changes.
- Restore original implementations
- Keep Phases 1-2 (they work independently)
- Time: 30 minutes

---

## PHASE 4: Backend Event Unification (FROM 0377) (12-14 hours)

### Goal
Single event contract, single broadcast path, no loopback for in-process code.

### 4A: Fix Event Name Drift

**Problem**: `agent_update` (underscore) vs `agent:update` (colon) causes silent failures.

**Solution**: Standardize on colon-delimited names everywhere.

**Files to update**:
- `api/websocket.py` - Use canonical names (CORRECT file, not websocket_manager.py)
- `frontend/src/stores/websocketIntegrations.js` - Fix `agent_update` -> `agent:updated`
- `frontend/src/stores/agents.js` - Fix `agent:update` -> `agent:updated`

```python
# api/websocket.py - CANONICAL NAMES
EVENT_NAMES = {
    'agent:created', 'agent:updated', 'agent:status_changed',
    'message:sent', 'message:received', 'message:acknowledged',
    'project:activated', 'project:mission_updated', 'project:completed'
}

# Event name standardization map (emit BOTH during migration)
EVENT_ALIASES = {
    # Old name -> New name
    'agent_update': 'agent:updated',
    'project_update': 'project:updated',
    'message': 'message:new',
    'progress': 'system:progress',
    'notification': 'system:notification',
}

EMIT_LEGACY_EVENTS = True  # Set to False after 6-month migration

async def broadcast_event(event_type: str, data: dict, tenant_key: str):
    """
    Broadcast WebSocket event with automatic aliasing.
    During migration period, emits BOTH old and new event names.
    """
    # Emit canonical event
    await _broadcast_to_tenant(tenant_key, event_type, data)

    # Emit legacy alias if it exists and legacy mode enabled
    if EMIT_LEGACY_EVENTS:
        for old_name, new_name in EVENT_ALIASES.items():
            if new_name == event_type:
                await _broadcast_to_tenant(tenant_key, old_name, data)
                break
```

### 4B: Centralize Broadcasting in WebSocketManager

**Problem**: 4 different broadcast paths (WebSocketManager, WebSocketDependency, ws-bridge, event listener).

**Solution**: All broadcasts go through `api/websocket.py:WebSocketManager`:

```python
# api/dependencies/websocket.py - DELEGATE to WebSocketManager
async def broadcast_agent_update(self, tenant_key: str, agent_data: dict):
    # BEFORE: Duplicate broadcast logic
    # AFTER: Delegate
    await self.websocket_manager.broadcast_event('agent:updated', agent_data, tenant_key)
```

```python
# api/websocket_event_listener.py - DELEGATE to WebSocketManager
async def handle_event(self, event_type: str, payload: dict):
    # BEFORE: Manual iteration + send
    # AFTER: Delegate
    await self.websocket_manager.broadcast_event(event_type, payload, payload.get('tenant_key'))
```

```python
# api/endpoints/websocket_bridge.py - DELEGATE to WebSocketManager
@router.post("/emit")
async def emit_websocket_event(request: EmitRequest, ws_manager: Annotated[WebSocketManager, Depends(get_ws_manager)]):
    # BEFORE: Manual iteration + send
    # AFTER: Delegate
    await ws_manager.broadcast_event(request.event_type, request.payload, request.tenant_key)
```

### 4C: Remove Loopback for In-Process Code

**Problem**: Services POST to `http://localhost:7272/api/v1/ws-bridge/emit` - breaks in hosted/proxy.

**12 Files Currently Using ws-bridge Loopback**:
- `src/giljo_mcp/services/project_service.py`
- `src/giljo_mcp/services/orchestration_service.py`
- `src/giljo_mcp/tools/orchestration.py`
- `src/giljo_mcp/tools/project.py`
- (Search for `ws-bridge/emit` to find all)

**Solution**: Inject `websocket_manager` directly:

```python
# BEFORE (fragile)
class ProjectService:
    async def _broadcast_mission_update(self, project_id: str, mission: str):
        async with httpx.AsyncClient() as client:
            await client.post("http://localhost:7272/api/v1/ws-bridge/emit", json={
                "event_type": "project:mission_updated",
                "payload": {"project_id": project_id, "mission": mission}
            })

# AFTER (robust)
class ProjectService:
    def __init__(self, session: AsyncSession, websocket_manager: WebSocketManager):
        self.session = session
        self.websocket_manager = websocket_manager

    async def _broadcast_mission_update(self, project_id: str, mission: str, tenant_key: str):
        await self.websocket_manager.broadcast_event(
            'project:mission_updated',
            {"project_id": project_id, "mission": mission},
            tenant_key
        )
```

### 4D: Enforce EventFactory for All Events

**Problem**: Ad-hoc payload shaping bypasses `api/events/schemas.py`.

**Solution**: All events MUST use EventFactory:

```python
from api.events.schemas import EventFactory

# BEFORE (ad-hoc)
await ws_manager.broadcast_to_tenant(tenant_key, "agent:updated", {"id": agent_id, "status": status})

# AFTER (enforced)
event = EventFactory.agent_updated(agent_id=agent_id, status=status)
await ws_manager.broadcast_event(event.type, event.model_dump(), tenant_key)
```

### 4E: Fix Concurrency Hazards in Send Loops

**Problem**: Many loops do `for client_id, ws in active_connections.items(): await ws.send_json(...)`. If another coroutine mutates the dict during awaits, runtime errors and partial sends occur.

**Solution**: Snapshot connections before await loops:

```python
# BEFORE (hazard)
async def broadcast_to_tenant(self, tenant_key: str, event_type: str, data: dict):
    for client_id, ws in self.active_connections.items():  # Dict may change during loop
        if self.get_tenant(client_id) == tenant_key:
            await ws.send_json({"type": event_type, "data": data})

# AFTER (safe)
async def broadcast_to_tenant(self, tenant_key: str, event_type: str, data: dict):
    # Snapshot connections at loop start
    connections_snapshot = list(self.active_connections.items())
    for client_id, ws in connections_snapshot:
        if self.get_tenant(client_id) == tenant_key:
            try:
                await asyncio.wait_for(ws.send_json({"type": event_type, "data": data}), timeout=5.0)
            except (asyncio.TimeoutError, WebSocketDisconnect):
                await self._handle_disconnect(client_id)
```

### Phase 4 Rollback

**If Phase 4 fails**: Keep dual-emission, restore loopback.
- Set `EMIT_LEGACY_EVENTS=true`
- Revert service changes
- Time: 1 hour

---

## PHASE 5: SaaS Broker Abstraction (FROM 0377) (8-10 hours)

### Goal
Make multi-worker/multi-instance deployments work without sticky sessions.

### Architecture

```
Application Code -> broker.publish("agent:updated", payload, tenant)
                              |
                              v
                    BROKER ABSTRACTION
                    WebSocketEventBroker (interface)
                    |-- InMemoryBroker (default - single server LAN)
                    |-- PostgresNotifyBroker (LISTEN/NOTIFY - no new infra)
                    +-- RedisPubSubBroker (optional - high scale)
                              |
                              v
                    PER-WORKER BROADCAST
                    Each worker subscribes to broker
                    On receive: broadcast to local WebSocket connections
```

### Files to Create

#### 1. `api/broker/__init__.py`

```python
from .base import WebSocketEventBroker
from .in_memory import InMemoryBroker

# Default factory based on config
def get_broker() -> WebSocketEventBroker:
    from config import settings

    broker_type = getattr(settings, 'WEBSOCKET_BROKER', 'in_memory')

    if broker_type == 'postgres':
        from .postgres_notify import PostgresNotifyBroker
        return PostgresNotifyBroker()
    elif broker_type == 'redis':
        from .redis_pubsub import RedisPubSubBroker
        return RedisPubSubBroker()
    else:
        return InMemoryBroker()

__all__ = ['WebSocketEventBroker', 'InMemoryBroker', 'get_broker']
```

#### 2. `api/broker/base.py`

```python
from abc import ABC, abstractmethod
from typing import Callable, Any

class WebSocketEventBroker(ABC):
    """Abstract base class for WebSocket event brokers."""

    @abstractmethod
    async def publish(self, event_type: str, payload: dict, tenant_key: str) -> None:
        """Publish event to all subscribers."""
        pass

    @abstractmethod
    async def subscribe(self, callback: Callable[[str, dict, str], Any]) -> None:
        """Subscribe to receive events. Callback receives (event_type, payload, tenant_key)."""
        pass

    @abstractmethod
    async def start(self) -> None:
        """Start the broker (connect, subscribe to channels, etc.)."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the broker (disconnect, cleanup)."""
        pass
```

#### 3. `api/broker/in_memory.py`

```python
from .base import WebSocketEventBroker
from typing import Callable, Any, List

class InMemoryBroker(WebSocketEventBroker):
    """
    In-memory broker for single-server LAN deployments.
    No external dependencies - just local event distribution.
    """

    def __init__(self):
        self._subscribers: List[Callable[[str, dict, str], Any]] = []
        self._started = False

    async def publish(self, event_type: str, payload: dict, tenant_key: str) -> None:
        """Immediately deliver to all local subscribers."""
        for callback in self._subscribers:
            try:
                await callback(event_type, payload, tenant_key)
            except Exception as e:
                print(f"[InMemoryBroker] Subscriber error: {e}")

    async def subscribe(self, callback: Callable[[str, dict, str], Any]) -> None:
        """Add subscriber callback."""
        self._subscribers.append(callback)

    async def start(self) -> None:
        """No-op for in-memory broker."""
        self._started = True

    async def stop(self) -> None:
        """Clear subscribers."""
        self._subscribers.clear()
        self._started = False
```

#### 4. `api/broker/postgres_notify.py`

```python
from .base import WebSocketEventBroker
from typing import Callable, Any, List
import asyncio
import json

class PostgresNotifyBroker(WebSocketEventBroker):
    """
    PostgreSQL LISTEN/NOTIFY broker for multi-worker deployments.
    No new infrastructure required - uses existing PostgreSQL.
    """

    CHANNEL = 'websocket_events'

    def __init__(self, database_url: str = None):
        self._database_url = database_url
        self._subscribers: List[Callable[[str, dict, str], Any]] = []
        self._connection = None
        self._listen_task = None

    async def publish(self, event_type: str, payload: dict, tenant_key: str) -> None:
        """Publish via PostgreSQL NOTIFY."""
        message = json.dumps({
            'event_type': event_type,
            'payload': payload,
            'tenant_key': tenant_key
        })

        async with self._get_connection() as conn:
            await conn.execute(f"NOTIFY {self.CHANNEL}, '{message}'")

    async def subscribe(self, callback: Callable[[str, dict, str], Any]) -> None:
        """Add subscriber callback."""
        self._subscribers.append(callback)

    async def start(self) -> None:
        """Start listening for NOTIFY events."""
        self._connection = await self._get_connection()
        await self._connection.execute(f"LISTEN {self.CHANNEL}")
        self._listen_task = asyncio.create_task(self._listen_loop())

    async def stop(self) -> None:
        """Stop listening and cleanup."""
        if self._listen_task:
            self._listen_task.cancel()
        if self._connection:
            await self._connection.execute(f"UNLISTEN {self.CHANNEL}")
            await self._connection.close()
        self._subscribers.clear()

    async def _listen_loop(self) -> None:
        """Background task to receive NOTIFY events."""
        while True:
            try:
                notification = await self._connection.notifies.get()
                message = json.loads(notification.payload)

                event_type = message['event_type']
                payload = message['payload']
                tenant_key = message['tenant_key']

                for callback in self._subscribers:
                    try:
                        await callback(event_type, payload, tenant_key)
                    except Exception as e:
                        print(f"[PostgresNotifyBroker] Subscriber error: {e}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[PostgresNotifyBroker] Listen error: {e}")
                await asyncio.sleep(1)  # Backoff on error
```

### Configuration

```yaml
# config.yaml
websocket:
  broker: "in_memory"  # Default for LAN/WAN
  # broker: "postgres"  # For SaaS/multi-worker
  # broker: "redis"     # For high-scale SaaS
```

### Integration with WebSocketManager

```python
# api/websocket.py
from api.broker import get_broker

class WebSocketManager:
    def __init__(self):
        self._broker = get_broker()
        self._local_connections = {}  # This worker's connections only

    async def start(self):
        """Start the broker and subscribe to events."""
        await self._broker.subscribe(self._handle_broker_event)
        await self._broker.start()

    async def broadcast_event(self, event_type: str, payload: dict, tenant_key: str):
        """Publish to broker (will reach all workers)."""
        await self._broker.publish(event_type, payload, tenant_key)

    async def _handle_broker_event(self, event_type: str, payload: dict, tenant_key: str):
        """Receive event from broker, broadcast to local connections."""
        await self._broadcast_to_local_connections(event_type, payload, tenant_key)
```

### Phase 5 Rollback

**If Phase 5 fails**: Set `broker: in_memory` in config.
- InMemoryBroker is safe and has no external dependencies
- Time: 5 minutes

---

## Success Criteria (EXPANDED)

### From Original 0375
1. **Zero page refreshes** for any WebSocket-driven UI update
2. **Tab switching works** - state persists correctly
3. **Project isolation** - switching projects resets state
4. **No duplicate handlers** - each event processed exactly once

### Added from 0377
5. **Reconnect resync** - UI updates after transient disconnect without refresh
6. **Subscription safety** - Shared subscriptions can't be dropped accidentally
7. **Event name consistency** - No `agent_update` vs `agent:update` drift
8. **No loopback required** - Core flows work without localhost POST
9. **Multi-worker ready** - Works with `--workers > 1` (Phase 5)

### Technical Requirements
1. **60+ tests passing** with >80% coverage on new code
2. **All existing tests pass** - no regressions
3. **Console clean** - no errors or warnings from EventRouter
4. **Performance** - <100ms latency from WebSocket event to UI update

### Manual Verification Checklist

- [ ] Stage a project, verify orchestrator card updates status
- [ ] Send message from orchestrator, verify counter increments
- [ ] Switch to Launch tab, then back to Jobs - counters still correct
- [ ] Switch projects - previous project's state cleared
- [ ] Complete all agents - "All Complete" badge appears
- [ ] Trigger health alert - badge updates without refresh
- [ ] Kill network briefly, reconnect - UI resyncs automatically
- [ ] Two browsers same project - both receive updates
- [ ] (SaaS) Run with `--workers 2` - events still reach all clients

---

## Rollback Strategy Summary

| Phase | How to Rollback | Time | Impact |
|-------|-----------------|------|--------|
| 1 | Delete new files | 5 min | None |
| 2 | Revert JobsTab.vue | 30 min | Phase 1 preserved |
| 3 | Revert LaunchTab, ProjectTabs, websocket.js | 30 min | Phases 1-2 preserved |
| 4 | Keep dual-emission, restore loopback | 1 hour | Phases 1-3 preserved |
| 5 | Set `broker: in_memory` in config | 5 min | Phases 1-4 preserved |

---

## Execution Strategy: LAN/WAN MVP + SaaS Scaffolding

### Implementation Order

| Order | Phase | Hours | Deliverable |
|-------|-------|-------|-------------|
| 1 | **Phase 1** | 10-12h | Infrastructure + Reconnect Resync |
| 2 | **Phase 2** | 10-12h | Agent/Job Domain (fixes message counters) |
| 3 | **Phase 3** | 10-12h | Messages + Subscription Refcount |
| 4 | **Phase 4A-C** | 8-10h | Event drift fix + Loopback removal |
| 5 | **Phase 5** | 8-10h | Broker abstraction (InMemoryBroker default) |
| 6 | **Phase 4D** | 4h | EventFactory enforcement (nice-to-have) |

### MVP Launch Deliverable (Phases 1-5)
- **LAN/WAN**: Works flawlessly on single server
- **SaaS-Ready**: Broker abstraction in place, just swap `in_memory` -> `postgres` in config
- **No Technical Debt**: Clean architecture, not bandaids

### SaaS Upgrade Path (6 months)
1. Implement `PostgresNotifyBroker` (or Redis)
2. Change config: `websocket.broker: "postgres"`
3. Deploy with `--workers > 1`
4. Done.

---

## EVENT_MAP Reference (All 35 Events)

| Event Type | Store | Action | Description |
|------------|-------|--------|-------------|
| `agent:created` | agentJobs | handleCreated | New agent job |
| `agent:updated` | agentJobs | handleUpdated | Agent updated |
| `agent:status_changed` | agentJobs | handleStatusChanged | Status transition |
| `agent:health_alert` | agentJobs | handleHealthAlert | Health degraded |
| `agent:health_recovered` | agentJobs | handleHealthRecovered | Health restored |
| `agent:auto_failed` | agentJobs | handleAutoFailed | Timeout/error |
| `agent:complete` | agentJobs | handleComplete | Work completed |
| `agent:spawn` | agentJobs | handleCreated | LEGACY alias |
| `agent:mission_acknowledged` | agentJobs | handleMissionAcknowledged | Mission acked |
| `agent_update` | agentJobs | handleUpdated | LEGACY alias |
| `message:sent` | projectMessages | handleSent | Message sent |
| `message:received` | projectMessages | handleReceived | Message received |
| `message:acknowledged` | projectMessages | handleAcknowledged | Message read |
| `message:new` | projectMessages | handleNew | New message |
| `message` | projectMessages | handleNew | LEGACY alias |
| `project:activated` | projectState | handleActivated | Project activated |
| `project:deactivated` | projectState | handleDeactivated | Project deactivated |
| `project:mission_updated` | projectState | handleMissionUpdated | Mission updated |
| `project:completed` | projectState | handleCompleted | Project done |
| `project_update` | projectState | handleUpdated | LEGACY alias |
| `product:memory_updated` | products | handleMemoryUpdated | 360 Memory |
| `product:learning_added` | products | handleLearningAdded | Learning added |
| `product:status_changed` | products | handleStatusChanged | Product status |
| `job:mission_acknowledged` | agentJobs | handleMissionAcknowledged | Job acked |
| `entity_update` | agentJobs | handleEntityUpdate | DEPRECATED |
| `system:progress` | system | handleProgress | Progress update |
| `system:notification` | system | handleNotification | Notification |
| `progress` | system | handleProgress | LEGACY alias |
| `notification` | system | handleNotification | LEGACY alias |
| `orchestrator:staging_started` | projectState | handleStagingStarted | Staging began |
| `orchestrator:staging_complete` | projectState | handleStagingComplete | Staging done |
| `orchestrator:succession` | agentJobs | handleSuccession | Succession |
| `orchestrator:context_warning` | agentJobs | handleContextWarning | Context limit |
| `workflow:status_changed` | projectState | handleWorkflowStatusChanged | Workflow status |
| `workflow:progress` | projectState | handleWorkflowProgress | Workflow progress |

---

## Notes for Executing Agent Team

1. **Read the User Challenge section first** - understand why this matters
2. **Don't skip TDD** - but don't get stuck in test-only mode either
3. **Test tab switching explicitly** - this is where previous fixes failed
4. **Immutable updates are KEY** - never `array.push()`, always `array = [...array, item]`
5. **If something doesn't work, dig deeper** - don't revert to bandaids
6. **Use storeToRefs()** - for reactive destructuring from Pinia stores
7. **No auto-init at module level** - explicit initialization only
8. **Follow the 5-phase rollout** - each phase has explicit rollback
9. **api/websocket.py is the correct file** - NOT api/websocket_manager.py (that's a shim)
10. **12 files use ws-bridge loopback** - all must be updated in Phase 4

---

## Execution Checklist

- [ ] Phase 1: Infrastructure created and tested (10-12h)
  - [ ] websocketEventRouter.js created with reconnect resync
  - [ ] immutableHelpers.js created
  - [ ] Subscription refcounting added to websocket.js
  - [ ] Template files created
  - [ ] Unit tests passing
- [ ] Phase 2: Agent/Job domain completed (10-12h)
  - [ ] agentJobsStore.js created
  - [ ] useAgentJobs.js composable created
  - [ ] JobsTab.vue refactored
  - [ ] Message counters working
  - [ ] Tab switching verified
- [ ] Phase 3: Messages & Project state completed (10-12h)
  - [ ] projectMessagesStore.js created
  - [ ] projectStateStore.js created
  - [ ] LaunchTab.vue refactored
  - [ ] ProjectTabs.vue refactored
  - [ ] All WebSocket events routing correctly
- [ ] Phase 4: Backend unification completed (12-14h)
  - [ ] Event name drift fixed (agent_update -> agent:updated)
  - [ ] Broadcasting centralized in WebSocketManager
  - [ ] Loopback removed from 12 files
  - [ ] Concurrency hazards fixed
  - [ ] Dual-emission working for migration
- [ ] Phase 5: SaaS broker abstraction completed (8-10h)
  - [ ] Broker interface created
  - [ ] InMemoryBroker implemented (default)
  - [ ] PostgresNotifyBroker implemented
  - [ ] Configuration added
  - [ ] Multi-worker tested
- [ ] Manual alpha trial passed
  - [ ] Stage project, verify UI updates
  - [ ] Tab switching verified
  - [ ] Project isolation verified
  - [ ] Reconnect resync verified
  - [ ] (Optional) Multi-worker tested
- [ ] Code review completed
- [ ] Merged to master

---

## Related Handovers

This handover supersedes:
- `handovers/0292_websocket_ui_regressions.md`
- `handovers/0358_websocket_ui_state_overhaul.md`
- `handovers/0362_websocket_message_counter_fixes.md`
- `handovers/0377_websocket_realtime_unification_and_saas_hardening.md`

---

**Status**: APPROVED - READY FOR IMPLEMENTATION
**Created**: 2025-12-25
**Last Updated**: 2025-12-25 (Merged with 0377)
