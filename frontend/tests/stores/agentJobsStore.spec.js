import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAgentJobsStore } from '@/stores/agentJobs'
import api from '@/services/api'

vi.mock('@/services/api', () => ({
  default: {
    agentJobs: {
      list: vi.fn(),
    },
  },
}))

describe('agentJobs store', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useAgentJobsStore()
    api.agentJobs.list.mockReset()
  })

  it('sets and sorts agents using default sort (last_progress_at desc)', () => {
    store.setAgents([
      { job_id: 'b', status: 'working', last_progress_at: '2025-11-20T10:00:00Z' },
      { job_id: 'a', status: 'waiting', last_progress_at: '2025-11-21T09:00:00Z' },
      { job_id: 'c', status: 'working', last_progress_at: '2025-11-21T11:00:00Z' },
    ])

    const ordered = store.sortedAgents
    expect(ordered[0].job_id).toBe('c') // most recent first
    expect(ordered[1].job_id).toBe('a')
    expect(ordered[2].job_id).toBe('b')
  })

  it('filters by status and computes warning count', () => {
    store.setAgents([
      { job_id: 'a', status: 'working', health_status: 'healthy' },
      { job_id: 'b', status: 'waiting', health_status: 'warning' },
      { job_id: 'c', status: 'failed', health_status: 'critical' },
    ])

    store.tableFilters.status = ['working', 'waiting']
    expect(store.filteredAgents).toHaveLength(2)
    expect(store.warningCount).toBe(2) // warning + critical
  })

  it('updates existing agents and adds new ones', () => {
    store.setAgents([{ job_id: 'a', status: 'working', progress: 10 }])

    store.updateAgent({ job_id: 'a', status: 'complete', progress: 100 })
    expect(store.agents[0].status).toBe('complete')
    expect(store.agents[0].progress).toBe(100)

    store.updateAgent({ job_id: 'b', status: 'waiting' })
    expect(store.agents).toHaveLength(2)
  })

  it('removes agent and clears selection when removed', () => {
    store.setAgents([
      { job_id: 'a', status: 'working' },
      { job_id: 'b', status: 'waiting' },
    ])
    store.selectAgent('b')
    store.removeAgent('b')

    expect(store.agents.map((a) => a.job_id)).toEqual(['a'])
    expect(store.selectedAgentId).toBeNull()
  })

  it('loads agents from API and stores table metadata', async () => {
    api.agentJobs.list.mockResolvedValue({
      data: {
        rows: [{ job_id: 'x', status: 'working' }],
        total: 1,
        limit: 25,
        offset: 0,
      },
    })

    await store.loadAgents('project-1')

    expect(api.agentJobs.list).toHaveBeenCalledWith('project-1', {})
    expect(store.agents).toHaveLength(1)
    expect(store.tableTotal).toBe(1)
    expect(store.tableLimit).toBe(25)
  })

  it('respects custom sort settings', () => {
    store.setAgents([
      { job_id: 'a', status: 'waiting' },
      { job_id: 'b', status: 'working' },
      { job_id: 'c', status: 'failed' },
    ])

    store.setSorting('status', 'asc')
    const ordered = store.sortedAgents.map((a) => a.job_id)
    expect(ordered[0]).toBe('c') // failed (highest priority)
    expect(ordered[2]).toBe('a') // waiting (lower priority)
  })
})
