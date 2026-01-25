import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import {
  EVENT_MAP,
  routeWebsocketEvent,
  defaultShouldRoute,
} from '@/stores/websocketEventRouter'
import { useProjectTabsStore } from '@/stores/projectTabs'
import { useUserStore } from '@/stores/user'

describe('websocketEventRouter - defaultShouldRoute (Handover 0463)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    // Reset the mocked user store to ensure tenant key is set
    const userStore = useUserStore()
    if (!userStore.currentUser) {
      userStore.currentUser = {}
    }
    userStore.currentUser.tenant_key = 'test-tenant'
  })

  describe('Project-scoped event filtering', () => {
    it('routes events when project_id matches current project', async () => {
      const projectTabsStore = useProjectTabsStore()
      projectTabsStore.setCurrentProject({ id: 'project-1' })

      const agentJobsStore = { handleStatusChanged: vi.fn() }
      const storeRegistry = { agentJobs: () => agentJobsStore }

      await routeWebsocketEvent(
        {
          type: 'agent:status_changed',
          data: { job_id: 'job-1', status: 'complete', project_id: 'project-1', tenant_key: 'test-tenant' },
        },
        {
          eventMap: EVENT_MAP,
          storeRegistry,
          shouldRoute: defaultShouldRoute,
        },
      )

      expect(agentJobsStore.handleStatusChanged).toHaveBeenCalledTimes(1)
    })

    it('drops events when project_id does not match current project', async () => {
      const projectTabsStore = useProjectTabsStore()
      projectTabsStore.setCurrentProject({ id: 'project-1' })

      const userStore = useUserStore()
      userStore.currentUser = { tenant_key: 'test-tenant' }

      const agentJobsStore = { handleStatusChanged: vi.fn() }
      const storeRegistry = { agentJobs: () => agentJobsStore }

      await routeWebsocketEvent(
        {
          type: 'agent:status_changed',
          data: { job_id: 'job-1', status: 'complete', project_id: 'project-2', tenant_key: 'test-tenant' },
        },
        {
          eventMap: EVENT_MAP,
          storeRegistry,
          shouldRoute: defaultShouldRoute,
        },
      )

      expect(agentJobsStore.handleStatusChanged).not.toHaveBeenCalled()
    })

    it('drops agent:status_changed without project_id when viewing project', async () => {
      const projectTabsStore = useProjectTabsStore()
      projectTabsStore.setCurrentProject({ id: 'project-1' })

      const userStore = useUserStore()
      userStore.currentUser = { tenant_key: 'test-tenant' }

      const agentJobsStore = { handleStatusChanged: vi.fn() }
      const storeRegistry = { agentJobs: () => agentJobsStore }

      await routeWebsocketEvent(
        {
          type: 'agent:status_changed',
          data: { job_id: 'job-1', status: 'complete', tenant_key: 'test-tenant' },
        },
        {
          eventMap: EVENT_MAP,
          storeRegistry,
          shouldRoute: defaultShouldRoute,
        },
      )

      expect(agentJobsStore.handleStatusChanged).not.toHaveBeenCalled()
    })

    it('routes agent:status_changed without project_id when no project is active', async () => {
      const projectTabsStore = useProjectTabsStore()
      projectTabsStore.setCurrentProject(null)

      const userStore = useUserStore()
      userStore.currentUser = { tenant_key: 'test-tenant' }

      const agentJobsStore = { handleStatusChanged: vi.fn() }
      const storeRegistry = { agentJobs: () => agentJobsStore }

      await routeWebsocketEvent(
        {
          type: 'agent:status_changed',
          data: { job_id: 'job-1', status: 'complete', tenant_key: 'test-tenant' },
        },
        {
          eventMap: EVENT_MAP,
          storeRegistry,
          shouldRoute: defaultShouldRoute,
        },
      )

      expect(agentJobsStore.handleStatusChanged).toHaveBeenCalledTimes(1)
    })

    it('routes agent:created when project_id matches current project', async () => {
      const projectTabsStore = useProjectTabsStore()
      projectTabsStore.setCurrentProject({ id: 'project-1' })

      const userStore = useUserStore()
      userStore.currentUser = { tenant_key: 'test-tenant' }

      const agentJobsStore = { handleCreated: vi.fn() }
      const agentsStore = { handleAgentSpawn: vi.fn() }
      const storeRegistry = {
        agentJobs: () => agentJobsStore,
        agents: () => agentsStore,
      }

      await routeWebsocketEvent(
        {
          type: 'agent:created',
          data: {
            job_id: 'job-1',
            agent_display_name: 'tester',
            project_id: 'project-1',
            tenant_key: 'test-tenant',
          },
        },
        {
          eventMap: EVENT_MAP,
          storeRegistry,
          shouldRoute: defaultShouldRoute,
        },
      )

      expect(agentJobsStore.handleCreated).toHaveBeenCalledTimes(1)
      expect(agentsStore.handleAgentSpawn).toHaveBeenCalledTimes(1)
    })

    it('drops agent:created when project_id does not match current project', async () => {
      const projectTabsStore = useProjectTabsStore()
      projectTabsStore.setCurrentProject({ id: 'project-1' })

      const userStore = useUserStore()
      userStore.currentUser = { tenant_key: 'test-tenant' }

      const agentJobsStore = { handleCreated: vi.fn() }
      const agentsStore = { handleAgentSpawn: vi.fn() }
      const storeRegistry = {
        agentJobs: () => agentJobsStore,
        agents: () => agentsStore,
      }

      await routeWebsocketEvent(
        {
          type: 'agent:created',
          data: {
            job_id: 'job-1',
            agent_display_name: 'tester',
            project_id: 'project-2',
            tenant_key: 'test-tenant',
          },
        },
        {
          eventMap: EVENT_MAP,
          storeRegistry,
          shouldRoute: defaultShouldRoute,
        },
      )

      expect(agentJobsStore.handleCreated).not.toHaveBeenCalled()
      expect(agentsStore.handleAgentSpawn).not.toHaveBeenCalled()
    })

    it('drops job:progress_update when project_id does not match current project', async () => {
      const projectTabsStore = useProjectTabsStore()
      projectTabsStore.setCurrentProject({ id: 'project-1' })

      const userStore = useUserStore()
      userStore.currentUser = { tenant_key: 'test-tenant' }

      const agentJobsStore = { handleProgressUpdate: vi.fn() }
      const storeRegistry = { agentJobs: () => agentJobsStore }

      await routeWebsocketEvent(
        {
          type: 'job:progress_update',
          data: {
            job_id: 'job-1',
            project_id: 'project-2',
            agent_display_name: 'orchestrator',
            progress_percent: 50,
            tenant_key: 'test-tenant',
          },
        },
        {
          eventMap: EVENT_MAP,
          storeRegistry,
          shouldRoute: defaultShouldRoute,
        },
      )

      expect(agentJobsStore.handleProgressUpdate).not.toHaveBeenCalled()
    })

    it('routes job:progress_update when project_id matches current project', async () => {
      const projectTabsStore = useProjectTabsStore()
      projectTabsStore.setCurrentProject({ id: 'project-1' })

      const userStore = useUserStore()
      userStore.currentUser = { tenant_key: 'test-tenant' }

      const agentJobsStore = { handleProgressUpdate: vi.fn() }
      const storeRegistry = { agentJobs: () => agentJobsStore }

      await routeWebsocketEvent(
        {
          type: 'job:progress_update',
          data: {
            job_id: 'job-1',
            project_id: 'project-1',
            agent_display_name: 'orchestrator',
            progress_percent: 50,
            tenant_key: 'test-tenant',
          },
        },
        {
          eventMap: EVENT_MAP,
          storeRegistry,
          shouldRoute: defaultShouldRoute,
        },
      )

      expect(agentJobsStore.handleProgressUpdate).toHaveBeenCalledTimes(1)
    })

    it('routes all PROJECT_SCOPED_EVENTS when project_id matches', async () => {
      const projectTabsStore = useProjectTabsStore()
      projectTabsStore.setCurrentProject({ id: 'project-1' })

      const userStore = useUserStore()
      userStore.currentUser = { tenant_key: 'test-tenant' }

      const agentJobsStore = {
        handleStatusChanged: vi.fn(),
        handleUpdated: vi.fn(),
        handleCreated: vi.fn(),
      }
      const agentsStore = {
        handleRealtimeUpdate: vi.fn(),
        handleAgentSpawn: vi.fn(),
      }
      const storeRegistry = {
        agentJobs: () => agentJobsStore,
        agents: () => agentsStore,
      }

      // Test agent:status_changed (store/action pattern)
      await routeWebsocketEvent(
        {
          type: 'agent:status_changed',
          data: {
            job_id: 'job-1',
            status: 'working',
            project_id: 'project-1',
            tenant_key: 'test-tenant',
          },
        },
        {
          eventMap: EVENT_MAP,
          storeRegistry,
          shouldRoute: defaultShouldRoute,
        },
      )
      expect(agentJobsStore.handleStatusChanged).toHaveBeenCalled()

      vi.clearAllMocks()

      // Test agent:spawn (custom handler pattern - calls handleCreated)
      await routeWebsocketEvent(
        {
          type: 'agent:spawn',
          data: {
            job_id: 'job-1',
            status: 'working',
            project_id: 'project-1',
            tenant_key: 'test-tenant',
          },
        },
        {
          eventMap: EVENT_MAP,
          storeRegistry,
          shouldRoute: defaultShouldRoute,
        },
      )
      expect(agentJobsStore.handleCreated).toHaveBeenCalled()

      vi.clearAllMocks()

      // Test agent:update (custom handler pattern - calls handleUpdated)
      await routeWebsocketEvent(
        {
          type: 'agent:update',
          data: {
            job_id: 'job-1',
            status: 'working',
            project_id: 'project-1',
            tenant_key: 'test-tenant',
          },
        },
        {
          eventMap: EVENT_MAP,
          storeRegistry,
          shouldRoute: defaultShouldRoute,
        },
      )
      expect(agentJobsStore.handleUpdated).toHaveBeenCalled()
    })
  })
})

describe('websocketEventRouter - normalization + routing', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('normalizes {type, data} and calls mapped store action once', async () => {
    const handleUpdated = vi.fn()

    const storeRegistry = {
      agents: () => ({ handleUpdated }),
    }

    const eventMap = {
      'agent:update': {
        store: 'agents',
        action: 'handleUpdated',
      },
    }

    await routeWebsocketEvent(
      {
        type: 'agent:update',
        tenant_key: 'test-tenant',
        data: { job_id: 'job-1', status: 'working' },
      },
      { eventMap, storeRegistry },
    )

    expect(handleUpdated).toHaveBeenCalledTimes(1)
    expect(handleUpdated).toHaveBeenCalledWith(
      expect.objectContaining({
        tenant_key: 'test-tenant',
        job_id: 'job-1',
        status: 'working',
      }),
    )
  })

  it('routes agent:update to both agentJobs + agents handlers', async () => {
    const agentJobsStore = { handleUpdated: vi.fn() }
    const agentsStore = { handleRealtimeUpdate: vi.fn() }

    const storeRegistry = {
      agentJobs: () => agentJobsStore,
      agents: () => agentsStore,
    }

    await routeWebsocketEvent(
      {
        type: 'agent:update',
        data: { job_id: 'job-1', status: 'working' },
      },
      { eventMap: EVENT_MAP, storeRegistry },
    )

    expect(agentJobsStore.handleUpdated).toHaveBeenCalledTimes(1)
    expect(agentsStore.handleRealtimeUpdate).toHaveBeenCalledTimes(1)
  })

  it('routes agent:created to agentJobs.create + agents.spawn handlers', async () => {
    const agentJobsStore = { handleCreated: vi.fn() }
    const agentsStore = { handleAgentSpawn: vi.fn() }

    const storeRegistry = {
      agentJobs: () => agentJobsStore,
      agents: () => agentsStore,
    }

    await routeWebsocketEvent(
      {
        type: 'agent:created',
        data: { job_id: 'job-1', agent_display_name: 'tester' },
      },
      { eventMap: EVENT_MAP, storeRegistry },
    )

    expect(agentJobsStore.handleCreated).toHaveBeenCalledTimes(1)
    expect(agentsStore.handleAgentSpawn).toHaveBeenCalledTimes(1)
  })

  it('routes nested agent:created payloads into agentJobs store', async () => {
    const agentJobsStore = { handleCreated: vi.fn() }
    const agentsStore = { handleAgentSpawn: vi.fn() }

    const storeRegistry = {
      agentJobs: () => agentJobsStore,
      agents: () => agentsStore,
    }

    await routeWebsocketEvent(
      {
        type: 'agent:created',
        data: {
          project_id: 'project-1',
          tenant_key: 'test-tenant',
          agent: {
            id: 'job-1',
            job_id: 'job-1',
            agent_display_name: 'tester',
            agent_name: 'Tester',
            status: 'waiting',
          },
        },
      },
      { eventMap: EVENT_MAP, storeRegistry },
    )

    expect(agentJobsStore.handleCreated).toHaveBeenCalledTimes(1)
    expect(agentJobsStore.handleCreated).toHaveBeenCalledWith(
      expect.objectContaining({ job_id: 'job-1', agent_display_name: 'tester' }),
    )
  })

  it('routes agent:status_changed via store/action mapping to agentJobs', async () => {
    const agentJobsStore = { handleStatusChanged: vi.fn() }

    const storeRegistry = {
      agentJobs: () => agentJobsStore,
    }

    await routeWebsocketEvent(
      {
        type: 'agent:status_changed',
        data: { job_id: 'job-1', status: 'complete' },
      },
      { eventMap: EVENT_MAP, storeRegistry },
    )

    expect(agentJobsStore.handleStatusChanged).toHaveBeenCalledTimes(1)
  })

  it('routes project:mission_updated into projectState store handler', async () => {
    const projectStateStore = { handleMissionUpdated: vi.fn() }

    const storeRegistry = {
      projectState: () => projectStateStore,
    }

    await routeWebsocketEvent(
      {
        type: 'project:mission_updated',
        data: { project_id: 'project-1', tenant_key: 'test-tenant', mission: 'Hello' },
      },
      { eventMap: EVENT_MAP, storeRegistry },
    )

    expect(projectStateStore.handleMissionUpdated).toHaveBeenCalledTimes(1)
    expect(projectStateStore.handleMissionUpdated).toHaveBeenCalledWith(
      expect.objectContaining({ project_id: 'project-1', mission: 'Hello' }),
    )
  })

  it('routes message:sent into agentJobs + projectMessages + projectState', async () => {
    const agentJobsStore = { handleMessageSent: vi.fn() }
    const projectMessagesStore = { handleSent: vi.fn() }
    const projectStateStore = { handleMessageSent: vi.fn() }

    const storeRegistry = {
      agentJobs: () => agentJobsStore,
      projectMessages: () => projectMessagesStore,
      projectState: () => projectStateStore,
    }

    await routeWebsocketEvent(
      {
        type: 'message:sent',
        data: {
          message_id: 'm1',
          project_id: 'project-1',
          from_agent: 'orchestrator',
          message_type: 'broadcast',
        },
      },
      { eventMap: EVENT_MAP, storeRegistry },
    )

    expect(agentJobsStore.handleMessageSent).toHaveBeenCalledTimes(1)
    expect(projectMessagesStore.handleSent).toHaveBeenCalledTimes(1)
    expect(projectStateStore.handleMessageSent).toHaveBeenCalledTimes(1)
  })
})
