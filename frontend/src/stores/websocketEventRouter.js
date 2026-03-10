import { useWebSocketStore } from './websocket'
import { useAgentStore } from './agents'
import { useAgentJobsStore } from './agentJobsStore'
import { useMessageStore } from './messages'
import { useProjectMessagesStore } from './projectMessagesStore'
import { useProjectStateStore } from './projectStateStore'
import { useProjectStore } from './projects'
import { useSystemStore } from './systemStore'
import { useTaskStore } from './tasks'
import { useProductStore } from './products'
import { useProjectTabsStore } from './projectTabs'
import { useUserStore } from '@/stores/user'
import { useNotificationStore } from '@/stores/notifications'

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

  // If payload is tenant-scoped, enforce match. If missing, allow.
  if (payload?.tenant_key && payload.tenant_key !== currentTenantKey) {
    return false
  }

  // Handover 0463: Project-aware filtering to prevent cross-project ghost rows
  // For project-scoped events, verify the event belongs to the current project
  if (PROJECT_SCOPED_EVENTS.has(type)) {
    const projectTabsStore = useProjectTabsStore()
    const currentProjectId = projectTabsStore?.currentProject?.id

    // If we have a current project and the event has a project_id, filter by project
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

    // If event lacks project_id but we're in a project view, drop it
    // (prevents ghost rows from legacy/incomplete events)
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

function dispatchWindowEvent(name, detail) {
  window.dispatchEvent(new CustomEvent(name, { detail }))
}

export const EVENT_MAP = {
  // =========================
  // Agents
  // =========================
  'agent:update': {
    handler: async (payload, { storeRegistry } = {}) => {
      const agentJobsStore = storeRegistry?.agentJobs?.() ?? useAgentJobsStore()
      const agentsStore = storeRegistry?.agents?.() ?? useAgentStore()

      agentJobsStore.handleUpdated?.(payload)
      agentsStore.handleRealtimeUpdate?.(payload)
    },
  },
  'agent:status_changed': { store: 'agentJobs', action: 'handleStatusChanged' },
  'agent:spawn': {
    handler: async (payload, { storeRegistry } = {}) => {
      const agentJobsStore = storeRegistry?.agentJobs?.() ?? useAgentJobsStore()
      const agentsStore = storeRegistry?.agents?.() ?? useAgentStore()

      const normalized = payload?.agent && typeof payload.agent === 'object'
        ? { ...payload.agent, project_id: payload.project_id, tenant_key: payload.tenant_key }
        : payload

      agentJobsStore.handleCreated?.(normalized)
      agentsStore.handleAgentSpawn?.(normalized)
    },
  },
  'agent:created': {
    handler: async (payload, { storeRegistry } = {}) => {
      const agentJobsStore = storeRegistry?.agentJobs?.() ?? useAgentJobsStore()
      const agentsStore = storeRegistry?.agents?.() ?? useAgentStore()

      const normalized = payload?.agent && typeof payload.agent === 'object'
        ? { ...payload.agent, project_id: payload.project_id, tenant_key: payload.tenant_key }
        : payload

      agentJobsStore.handleCreated?.(normalized)
      agentsStore.handleAgentSpawn?.(normalized)
    },
  },
  'agent:complete': {
    handler: async (payload, { storeRegistry } = {}) => {
      const agentJobsStore = storeRegistry?.agentJobs?.() ?? useAgentJobsStore()
      const agentsStore = storeRegistry?.agents?.() ?? useAgentStore()

      agentJobsStore.handleUpdated?.({ ...payload, status: 'complete' })
      agentsStore.handleAgentComplete?.(payload)
    },
  },
  'agent:mission_updated': { store: 'agentJobs', action: 'handleUpdated' },
  'agent:health_recovered': { store: 'agents', action: 'handleHealthRecovered' },
  'agent:health_alert': {
    handler: async (payload) => {
      const agentsStore = useAgentStore()
      agentsStore.handleHealthAlert?.(payload)

      const {
        health_state,
        agent_display_name,
        issue_description,
        job_id,
        project_name,
        project_id,
        execution_id,
      } = payload

      if (health_state === 'critical' || health_state === 'timeout') {
        // Handover 0259: Include project context in health alert notifications
        const prefix = project_name ? `[${project_name}] ` : ''
        const notificationStore = useNotificationStore()
        notificationStore.addNotification({
          type: 'agent_health',
          title: 'Agent Health Alert',
          message: `${prefix}${agent_display_name} - ${issue_description}`,
          metadata: {
            job_id,
            agent_display_name,
            health_state,
            project_id,
            project_name,
            execution_id,
          },
        })
      }
    },
  },
  // Handover 0491: Replaced agent:auto_failed with agent:silent
  'agent:silent': {
    handler: async (payload) => {
      const { agent_display_name, reason, job_id, project_name, project_id, execution_id } = payload

      // Handover 0259: Include project context in silent agent notifications
      const prefix = project_name ? `[${project_name}] ` : ''
      const notificationStore = useNotificationStore()
      notificationStore.addNotification({
        type: 'agent_health',
        title: 'Agent Silent',
        message: `${prefix}${agent_display_name} - ${reason || 'Agent stopped communicating'}`,
        metadata: {
          job_id,
          agent_display_name,
          reason,
          project_id,
          project_name,
          execution_id,
        },
      })
    },
  },

  // =========================
  // Orchestrator (Handover 0431)
  // =========================
  'orchestrator:prompt_generated': {
    handler: async (payload, { storeRegistry } = {}) => {
      const agentJobsStore = storeRegistry?.agentJobs?.() ?? useAgentJobsStore()

      // Update the existing orchestrator with staging info
      // The orchestrator fixture was created on activation; staging generates the prompt
      // CRITICAL: Include execution_id so the store uses correct unique_key (matches API load)
      // Handover 0700i: Removed instance_number
      agentJobsStore.handleUpdated?.({
        job_id: payload.orchestrator_id,
        agent_id: payload.agent_id,
        execution_id: payload.execution_id, // UNIQUE row ID - prevents duplicate cards
        project_id: payload.project_id,
        agent_display_name: 'orchestrator',
        status: 'waiting', // Still waiting for user to paste prompt
        staged: true, // Mark as staged
      })

    },
  },

  // =========================
  // Messages
  // =========================
  message: { store: 'messages', action: 'handleRealtimeUpdate' }, // legacy
  'message:new': { store: 'messages', action: 'handleRealtimeUpdate' },
  'message:sent': {
    handler: async (payload, { storeRegistry } = {}) => {
      const agentJobsStore = storeRegistry?.agentJobs?.() ?? useAgentJobsStore()
      const projectMessagesStore = storeRegistry?.projectMessages?.() ?? useProjectMessagesStore()
      const projectStateStore = storeRegistry?.projectState?.() ?? useProjectStateStore()
      const projectTabsStore = storeRegistry?.projectTabs?.() ?? useProjectTabsStore()

      agentJobsStore.handleMessageSent?.(payload)
      projectMessagesStore.handleSent?.(payload)
      projectStateStore.handleMessageSent?.(payload)
      projectTabsStore.handleMessageSent?.(payload)

      dispatchWindowEvent('agent:message_sent', payload)
    },
  },
  'message:received': {
    handler: async (payload, { storeRegistry } = {}) => {
      const agentJobsStore = storeRegistry?.agentJobs?.() ?? useAgentJobsStore()
      const projectMessagesStore = storeRegistry?.projectMessages?.() ?? useProjectMessagesStore()
      const projectStateStore = storeRegistry?.projectState?.() ?? useProjectStateStore()
      const projectTabsStore = storeRegistry?.projectTabs?.() ?? useProjectTabsStore()

      agentJobsStore.handleMessageReceived?.(payload)
      projectMessagesStore.handleReceived?.(payload)
      projectStateStore.handleMessageReceived?.(payload)
      projectTabsStore.handleMessageReceived?.(payload)

      dispatchWindowEvent('agent:message_received', payload)
    },
  },
  'message:acknowledged': {
    handler: async (payload, { storeRegistry } = {}) => {
      // Handover 0407: Debug logging to diagnose message counter sync issues
      // eslint-disable-next-line no-console
      console.debug('[websocketEventRouter] message:acknowledged received', {
        agent_id: payload?.agent_id,
        job_id: payload?.job_id,
        from_job_id: payload?.from_job_id,
        message_ids_count: payload?.message_ids?.length || 0,
      })

      const agentJobsStore = storeRegistry?.agentJobs?.() ?? useAgentJobsStore()
      const projectMessagesStore = storeRegistry?.projectMessages?.() ?? useProjectMessagesStore()

      agentJobsStore.handleMessageAcknowledged?.(payload)
      projectMessagesStore.handleAcknowledged?.(payload)

      dispatchWindowEvent('agent:message_acknowledged', payload)
    },
  },

  // =========================
  // Projects
  // =========================
  project_update: { store: 'projects', action: 'handleRealtimeUpdate' }, // legacy
  'project:mission_updated': { store: 'projectState', action: 'handleMissionUpdated' },

  // =========================
  // Entity updates (legacy multiplexed)
  // =========================
  entity_update: {
    handler: async (payload) => {
      if (payload.entity_type === 'task') {
        const productStore = useProductStore()
        const currentProductId = productStore.currentProductId

        if (currentProductId && payload.product_id !== currentProductId) {
          return
        }

        const tasksStore = useTaskStore()
        tasksStore.handleRealtimeUpdate?.(payload)
        return
      }

      if (payload.entity_type === 'message') {
        const messagesStore = useMessageStore()
        messagesStore.handleRealtimeUpdate?.(payload)
        return
      }

      if (payload.entity_type === 'agent') {
        const agentsStore = useAgentStore()
        agentsStore.handleRealtimeUpdate?.(payload)
        useAgentJobsStore().handleUpdated?.(payload)
        return
      }

      if (payload.entity_type === 'agent_job') {
        useAgentJobsStore().handleUpdated?.(payload)
      }
    },
  },

  // =========================
  // System events (legacy)
  // =========================
  progress: {
    handler: async (payload, { storeRegistry } = {}) => {
      const systemStore = storeRegistry?.system?.() ?? useSystemStore()
      systemStore.handleProgress?.(payload)
      dispatchWindowEvent('ws-progress', payload)
    },
  },
  notification: {
    handler: async (payload, { storeRegistry } = {}) => {
      const systemStore = storeRegistry?.system?.() ?? useSystemStore()
      systemStore.handleNotification?.(payload)
      dispatchWindowEvent('ws-notification', payload)
    },
  },

  // =========================
  // Mission tracking
  // =========================
  'mission:started': { handler: async (payload) => dispatchWindowEvent('mission:started', payload) },
  'mission:progress': {
    handler: async (payload) => dispatchWindowEvent('mission:progress', payload),
  },
  'mission:completed': {
    handler: async (payload) => dispatchWindowEvent('mission:completed', payload),
  },
  'mission:failed': { handler: async (payload) => dispatchWindowEvent('mission:failed', payload) },

  // Handover 0386: Progress updates should NOT create messages
  // This handler receives direct WebSocket events from report_progress()
  // Handover 0402: Include todo_items array for Plan/TODOs tab
  // Handover 0462: Include agent_display_name and agent_name to prevent "??" avatar bug
  'job:progress_update': {
    handler: async (payload, { storeRegistry } = {}) => {
      const agentJobsStore = storeRegistry?.agentJobs?.() ?? useAgentJobsStore()

      // Update the job's progress fields
      // CRITICAL: Include identity fields to prevent incomplete entries if this event
      // arrives before agent:created (race condition causing "??" avatars)
      agentJobsStore.handleProgressUpdate?.({
        job_id: payload.job_id,
        agent_id: payload.agent_id,
        agent_display_name: payload.agent_display_name, // Handover 0462: Identity field
        agent_name: payload.agent_name, // Handover 0462: Identity field
        progress: payload.progress_percent,
        current_task: payload.current_task,
        todo_steps: payload.todo_steps,
        todo_items: payload.todo_items, // Handover 0402: TODO items for UI display
        last_progress_at: payload.last_progress_at,
        // Include raw progress object for detailed info
        progress_data: payload.progress,
      })

      dispatchWindowEvent('job:progress_update', payload)
    },
  },

  // =========================
  // Products (aliases; store handlers will be wired in a later phase)
  // =========================
  'product:memory:updated': { store: 'products', action: 'handleProductMemoryUpdated' },
  'product:learning:added': { store: 'products', action: 'handleProductLearningAdded' },
  'product:status:changed': { store: 'products', action: 'handleProductStatusChanged' },
}

/**
 * Normalize payload to handle both:
 * - flat structures: { type, tenant_key, ... }
 * - nested structures: { type, data: { tenant_key, ... } }
 */
function normalizeWebsocketEvent(rawEvent) {
  if (!rawEvent || typeof rawEvent !== 'object') {
    return { type: undefined, payload: {} }
  }

  const { type, ...rest } = rawEvent

  // If `data` is an object, merge it into the top-level payload and drop the nested key.
  if (rest.data && typeof rest.data === 'object' && !Array.isArray(rest.data)) {
    const { data, ...restWithoutData } = rest
    return { type, payload: { ...restWithoutData, ...data } }
  }

  return { type, payload: rest }
}

/**
 * Route a single WebSocket event to the configured store action.
 *
 * Route config shape:
 * - { store, action, filter?, transform?, handler? }
 */
export async function routeWebsocketEvent(
  rawEvent,
  { eventMap, storeRegistry, shouldRoute } = {},
) {
  const { type, payload } = normalizeWebsocketEvent(rawEvent)
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
let unregister = []

/**
 * Initialize the router once for the entire app.
 *
 * This avoids scattered handler registration and provides a single, testable routing path.
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
