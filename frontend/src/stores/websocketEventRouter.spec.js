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
        data: { job_id: 'job-1', agent_type: 'tester' },
      },
      { eventMap: EVENT_MAP, storeRegistry },
    )

    expect(agentJobsStore.handleCreated).toHaveBeenCalledTimes(1)
    expect(agentsStore.handleAgentSpawn).toHaveBeenCalledTimes(1)
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
})
