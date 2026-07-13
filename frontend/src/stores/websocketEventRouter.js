import { useWebSocketStore } from './websocket'
import { useAgentJobsStore } from './agentJobsStore'
import { useProjectStateStore } from './projectStateStore'
import { useProjectStore } from './projects'
import { useTaskStore } from './tasks'
import { useProductStore } from './products'
import { useProjectTabsStore } from './projectTabs'
import { useUserStore } from '@/stores/user'
import { normalizeWebsocketPayload } from '@/utils/normalizeWebsocketPayload'

import { AGENT_EVENT_ROUTES } from './eventRoutes/agentEventRoutes'
import { COMM_HUB_EVENT_ROUTES } from './eventRoutes/commHubEventRoutes'
import { PROJECT_EVENT_ROUTES } from './eventRoutes/projectEventRoutes'
import { SEQUENCE_EVENT_ROUTES } from './eventRoutes/sequenceEventRoutes'
import { SYSTEM_EVENT_ROUTES } from './eventRoutes/systemEventRoutes'
import { useCommHubStore } from './commHubStore'
import { useSequenceRunStore } from './sequenceRunStore'

const STORE_REGISTRY = {
  agentJobs: () => useAgentJobsStore(),
  agents: () => useAgentJobsStore(),
  commHub: () => useCommHubStore(),
  projectState: () => useProjectStateStore(),
  projects: () => useProjectStore(),
  tasks: () => useTaskStore(),
  products: () => useProductStore(),
  projectTabs: () => useProjectTabsStore(),
  sequenceRun: () => useSequenceRunStore(),
}

// =========================================================================
// FE-3007b: generalized reconnect-resync registry
// =========================================================================
// Any store/view registers a resync callback; on a WS reconnect (automatic OR
// manual) EVERY registered callback refetches. This replaces the previous
// hardcoded "messages-only" single callback and the scattered per-view
// onConnectionChange resync blocks (DefaultLayout, useProjectTabsLifecycle,
// JobsTab). The router owns the ONE connection listener; views just register.
const reconnectResyncCallbacks = new Set()

/**
 * Register a resync callback fired on every WS reconnect.
 * @param {Function} callback - invoked (no args) on reconnect; may be async.
 * @returns {Function} unregister fn (call on teardown/unmount).
 */
export function registerReconnectResync(callback) {
  if (typeof callback !== 'function') return () => {}
  reconnectResyncCallbacks.add(callback)
  return () => reconnectResyncCallbacks.delete(callback)
}

/**
 * Run every registered resync callback. allSettled so one store's failed
 * refetch never blocks the others from refreshing. Internal — fired by the
 * router's single connection listener; tests drive it through that listener.
 */
async function runReconnectResyncs() {
  await Promise.allSettled(
    Array.from(reconnectResyncCallbacks).map((cb) => {
      try {
        return Promise.resolve(cb())
      } catch (error) {
        return Promise.reject(error)
      }
    }),
  )
}

// Handover 0463: Project-scoped event types that require project filtering
const PROJECT_SCOPED_EVENTS = new Set([
  'agent:status_changed',
  'agent:created',
  'agent:removed', // BE-6123: project-filtered like agent:created
  'agent:update',
  'job:progress_update',
])

// eslint-disable-next-line giljo-internal/no-orphaned-exports -- imported in tests/stores/websocketEventRouter.*.spec.js (outside src/)
export function defaultShouldRoute(type, payload) {
  const currentTenantKey = useUserStore()?.currentUser?.tenant_key

  if (!currentTenantKey) {
    return true
  }

  if (payload?.tenant_key && payload.tenant_key !== currentTenantKey) {
    return false
  }

  // Handover 0463: Project-aware filtering to prevent cross-project ghost rows
  if (PROJECT_SCOPED_EVENTS.has(type)) {
    const projectTabsStore = useProjectTabsStore()
    const currentProjectId = projectTabsStore?.currentProject?.id

    if (currentProjectId && payload?.project_id) {
      if (payload.project_id !== currentProjectId) {
        // eslint-disable-next-line no-console
        console.debug('[websocketEventRouter] Dropping cross-project event:', {
          type,
          event_project: payload.project_id,
          current_project: currentProjectId,
        })
        return false
      }
    }

    if (currentProjectId && !payload?.project_id && type === 'agent:status_changed') {
      // eslint-disable-next-line no-console
      console.debug('[websocketEventRouter] Dropping status event without project_id:', {
        type,
        job_id: payload?.job_id,
      })
      return false
    }
  }

  return true
}

/** Composed event map from domain-specific route files */
// eslint-disable-next-line giljo-internal/no-orphaned-exports -- imported in tests/stores/websocketEventRouter.*.spec.js (outside src/)
export const EVENT_MAP = {
  ...AGENT_EVENT_ROUTES,
  ...COMM_HUB_EVENT_ROUTES,
  ...PROJECT_EVENT_ROUTES,
  ...SEQUENCE_EVENT_ROUTES,
  ...SYSTEM_EVENT_ROUTES,
}

/**
 * Route a single WebSocket event to the configured store action.
 */
// eslint-disable-next-line giljo-internal/no-orphaned-exports -- imported in tests/stores/websocketEventRouter.*.spec.js (outside src/)
export async function routeWebsocketEvent(
  rawEvent,
  { eventMap, storeRegistry, shouldRoute } = {},
) {
  const { type, payload } = normalizeWebsocketPayload(rawEvent)
  if (!type) return false

  const routeConfig = eventMap?.[type]
  if (!routeConfig) return false

  if (typeof shouldRoute === 'function' && !shouldRoute(type, payload)) {
    return false
  }

  if (typeof routeConfig.filter === 'function' && !routeConfig.filter(payload)) {
    return false
  }

  const transformedPayload =
    typeof routeConfig.transform === 'function' ? routeConfig.transform(payload) : payload

  if (typeof routeConfig.handler === 'function') {
    await routeConfig.handler(transformedPayload, {
      type,
      payload: transformedPayload,
      storeRegistry,
    })
    return true
  }

  const storeFactory = storeRegistry?.[routeConfig.store]
  if (typeof storeFactory !== 'function') return false

  const store = storeFactory()
  const action = store?.[routeConfig.action]
  if (typeof action !== 'function') return false

  await action.call(store, transformedPayload)
  return true
}

let isInitialized = false
const unregister = []

/**
 * Initialize the router once for the entire app.
 */
export function initWebsocketEventRouter({
  wsStore = null,
  eventMap = EVENT_MAP,
  storeRegistry = STORE_REGISTRY,
  shouldRoute = null,
} = {}) {
  if (isInitialized) {
    return
  }

  const resolvedWsStore = wsStore || useWebSocketStore()
  const resolvedShouldRoute = shouldRoute || defaultShouldRoute

  unregister.push(
    resolvedWsStore.on('*', (event) =>
      routeWebsocketEvent(event, {
        eventMap,
        storeRegistry,
        shouldRoute: resolvedShouldRoute,
      }).catch((error) => {

        console.error('[websocketEventRouter] Unhandled routing error:', error)
      }),
    ),
  )

  // FE-3007b: the SINGLE reconnect listener. On any reconnect (automatic via
  // backoff, or manual via wsStore.reconnect() which flags isReconnect=true)
  // fan out to every store/view that registered a resync callback.
  unregister.push(
    resolvedWsStore.onConnectionChange((connectionEvent) => {
      if (connectionEvent?.state === 'connected' && connectionEvent?.isReconnect) {
        return runReconnectResyncs()
      }
    }),
  )

  isInitialized = true
}
