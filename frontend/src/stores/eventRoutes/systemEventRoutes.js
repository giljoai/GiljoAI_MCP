import { useAgentJobsStore } from '../agentJobsStore'
import { useNotificationStore } from '../notifications'
import { useProductStore } from '../products'
import { useSystemStore } from '../systemStore'
import { useTaskStore } from '../tasks'

function dispatchWindowEvent(name, detail) {
  window.dispatchEvent(new CustomEvent(name, { detail }))
}

/**
 * System, progress, mission, product, and vision event route definitions.
 */
export const SYSTEM_EVENT_ROUTES = {
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

  // Mission tracking
  'mission:started': { handler: async (payload) => dispatchWindowEvent('mission:started', payload) },
  'mission:progress': {
    handler: async (payload) => dispatchWindowEvent('mission:progress', payload),
  },
  'mission:completed': {
    handler: async (payload) => dispatchWindowEvent('mission:completed', payload),
  },
  'mission:failed': { handler: async (payload) => dispatchWindowEvent('mission:failed', payload) },

  // Handover 0386: Progress updates should NOT create messages
  // Handover 0402: Include todo_items array for Plan/TODOs tab
  // Handover 0462: Include agent_display_name and agent_name to prevent "??" avatar bug
  'job:progress_update': {
    handler: async (payload, { storeRegistry } = {}) => {
      const agentJobsStore = storeRegistry?.agentJobs?.() ?? useAgentJobsStore()

      agentJobsStore.handleProgressUpdate?.({
        job_id: payload.job_id,
        agent_id: payload.agent_id,
        agent_display_name: payload.agent_display_name,
        agent_name: payload.agent_name,
        progress: payload.progress_percent,
        current_task: payload.current_task,
        todo_steps: payload.todo_steps,
        todo_items: payload.todo_items,
        last_progress_at: payload.last_progress_at,
        progress_data: payload.progress,
      })

      dispatchWindowEvent('job:progress_update', payload)
    },
  },

  // Products
  'product:memory:updated': { store: 'products', action: 'handleProductMemoryUpdated' },
  'product:learning:added': { store: 'products', action: 'handleProductLearningAdded' },
  'product:status:changed': { store: 'products', action: 'handleProductStatusChanged' },

  // Handover 0831: Product context tuning proposals ready
  'product:tuning:proposals_ready': {
    handler: async (payload) => {
      const notificationStore = useNotificationStore()
      notificationStore.addNotification({
        type: 'context_tuning',
        title: 'Tuning Proposals Ready',
        message: 'Your AI coding agent has submitted context tuning proposals. Review them in the product details.',
        metadata: {
          product_id: payload.product_id,
          product_name: payload.product_name,
        },
      })
    },
  },

  // Vision Document Analysis — agent connected (Handover 0842c)
  'vision:analysis_started': {
    handler: async (payload) => {
      dispatchWindowEvent('vision-analysis-started', payload)
    },
  },

  // Vision Document Analysis — complete (Handover 0842c)
  'vision:analysis_complete': {
    handler: async (payload) => {
      const productStore = useProductStore()
      const notificationStore = useNotificationStore()

      if (payload?.product_id) {
        await productStore.fetchProducts()
      }

      notificationStore.addNotification({
        type: 'vision_analysis',
        title: 'Vision Analysis Complete',
        message: `AI populated ${payload?.fields_written || 0} product fields. Review in Product Info.`,
        metadata: { product_id: payload?.product_id, fields: payload?.fields },
      })

      dispatchWindowEvent('vision-analysis-complete', payload)
    },
  },

  // Tasks (MCP tool creates — frontend needs refresh)
  'task:created': {
    handler: async () => {
      const taskStore = useTaskStore()
      await taskStore.fetchTasks()
    },
  },
}
