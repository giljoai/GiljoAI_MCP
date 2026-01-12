import { describe, expect, it, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { EVENT_MAP, routeWebsocketEvent } from '@/stores/websocketEventRouter'

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
        tenant_key: 'tk_test',
        data: { job_id: 'job-1', status: 'working' },
      },
      { eventMap, storeRegistry },
    )

    expect(handleUpdated).toHaveBeenCalledTimes(1)
    expect(handleUpdated).toHaveBeenCalledWith(
      expect.objectContaining({
        tenant_key: 'tk_test',
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
          tenant_key: 'tk_test',
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
        data: { project_id: 'project-1', tenant_key: 'tk_test', mission: 'Hello' },
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
