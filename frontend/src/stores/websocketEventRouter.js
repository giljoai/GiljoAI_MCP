import { useWebSocketStore } from './websocket'
import { useAgentJobsStore } from './agentJobsStore'
import { useAgentStore } from './agents'
import { useMessageStore } from './messages'
import { useProjectMessagesStore } from './projectMessagesStore'
import { useProjectStateStore } from './projectStateStore'
import { useProjectStore } from './projects'
import { useSystemStore } from './systemStore'
import { useTaskStore } from './tasks'
import { useProductStore } from './products'
import { useProjectTabsStore } from './projectTabs'
import { useUserStore } from '@/stores/user'
import { normalizeWebsocketPayload } from '@/utils/normalizeWebsocketPayload'

import { AGENT_EVENT_ROUTES } from './eventRoutes/agentEventRoutes'
import { MESSAGE_EVENT_ROUTES } from './eventRoutes/messageEventRoutes'
import { PROJECT_EVENT_ROUTES } from './eventRoutes/projectEventRoutes'
import { SYSTEM_EVENT_ROUTES } from './eventRoutes/systemEventRoutes'

const STORE_REGISTRY = {
  agentJobs: () => useAgentJobsStore(),
  agents: () => useAgentStore(),
  messages: () => useMessageStore(),
  projectMessages: () => useProjectMessagesStore(),
  projectState: () => useProjectStateStore(),
  projects: () => useProjectStore(),
  system: () => useSystemStore(),
  tasks: () => useTaskStore(),
  products: () => useProductStore(),
  projectTabs: () => useProjectTabsStore(),
}

// Handover 0463: Project-scoped event types that require project filtering
const PROJECT_SCOPED_EVENTS = new Set([
  'agent:status_changed',
  'agent:created',
  'agent:spawn',
  'agent:update',
  'job:progress_update',
])

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
export const EVENT_MAP = {
  ...AGENT_EVENT_ROUTES,
  ...MESSAGE_EVENT_ROUTES,
  ...PROJECT_EVENT_ROUTES,
  ...SYSTEM_EVENT_ROUTES,
}

/**
 * Route a single WebSocket event to the configured store action.
 */
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
  onReconnectResync = null,
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

  if (typeof onReconnectResync === 'function') {
    unregister.push(
      resolvedWsStore.onConnectionChange((connectionEvent) => {
        if (connectionEvent?.state === 'connected' && connectionEvent?.isReconnect) {
          return onReconnectResync()
        }
      }),
    )
  }

  isInitialized = true
}
