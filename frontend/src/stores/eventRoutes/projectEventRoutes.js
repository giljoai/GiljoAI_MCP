import { useAgentJobsStore } from '../agentJobsStore'
import { useProductStore } from '../products'
import { useProjectStore } from '../projects'
import { useProjectStateStore } from '../projectStateStore'
import { useTaskStore } from '../tasks'

/**
 * Project and entity update event route definitions.
 */
export const PROJECT_EVENT_ROUTES = {
  project_update: { store: 'projects', action: 'handleRealtimeUpdate' }, // legacy
  'project:mission_updated': { store: 'projectState', action: 'handleMissionUpdated' },
  // Handover 0826: Server-side staging completion signal
  'project:staging_complete': { store: 'projectState', action: 'handleStagingComplete' },
  // CE-0029 Item 3: symmetric signal emitted by the launch_implementation endpoint.
  // FE-6174c: the mission-control roster patch was removed with Mission Control's
  // retirement; this now routes solely to projectStateStore (the solo/jobs surface
  // flips its own "Implementing" state from there).
  'project:implementation_launched': {
    handler: async (payload) => {
      try {
        const projectStateStore = useProjectStateStore()
        projectStateStore.handleImplementationLaunched?.(payload)
      } catch {
        // projectStateStore may not be initialized — ignore silently
      }
    },
  },

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

      if (payload.entity_type === 'agent') {
        const agentJobsStore = useAgentJobsStore()
        agentJobsStore.handleUpdated?.(payload)
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
      // refreshList() replays the active filter/sort/page. A bare fetchProjects()
      // here refetches the active-lifecycle default and, landing after the user's
      // filter fetch, clobbers it (the "Completed flashes then reverts" bug).
      await projectStore.refreshList()
    },
  },
}
