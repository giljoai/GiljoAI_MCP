import { useAgentStore } from '../agents'
import { useAgentJobsStore } from '../agentJobsStore'
import { useMessageStore } from '../messages'
import { useProductStore } from '../products'
import { useProjectStore } from '../projects'
import { useTaskStore } from '../tasks'

/**
 * Project and entity update event route definitions.
 */
export const PROJECT_EVENT_ROUTES = {
  project_update: { store: 'projects', action: 'handleRealtimeUpdate' }, // legacy
  'project:mission_updated': { store: 'projectState', action: 'handleMissionUpdated' },
  // Handover 0826: Server-side staging completion signal
  'project:staging_complete': { store: 'projectState', action: 'handleStagingComplete' },

  // Entity updates (legacy multiplexed)
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

  // Projects (MCP tool creates — frontend needs refresh)
  'project:created': {
    handler: async () => {
      const projectStore = useProjectStore()
      await projectStore.fetchProjects()
    },
  },
}
