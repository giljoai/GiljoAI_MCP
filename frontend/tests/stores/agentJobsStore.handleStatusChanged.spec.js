/**
 * agentJobsStore - handleStatusChanged tests
 *
 * Validates that agent:status_changed WebSocket events correctly update
 * the store. Backend emits `status` field directly (no mapping needed).
 *
 * Edition Scope: CE
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAgentJobsStore } from '@/stores/agentJobsStore'

describe('agentJobsStore - handleStatusChanged', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useAgentJobsStore()
  })

  it('updates status from payload', () => {
    store.setJobs([
      {
        job_id: 'job-1',
        agent_id: 'agent-1',
        agent_display_name: 'implementer',
        status: 'working',
      },
    ])

    store.handleStatusChanged({
      job_id: 'job-1',
      status: 'silent',
    })

    const job = store.getJob('job-1')
    expect(job).toBeTruthy()
    expect(job.status).toBe('silent')
  })

  it('ignores status changes for unknown jobs (prevents ghost rows)', () => {
    store.setJobs([
      {
        job_id: 'known-job',
        agent_id: 'known-agent',
        agent_display_name: 'implementer',
        status: 'working',
      },
    ])

    const countBefore = store.jobCount

    store.handleStatusChanged({
      job_id: 'unknown-job-from-other-project',
      status: 'silent',
    })

    expect(store.jobCount).toBe(countBefore)
    expect(store.getJob('unknown-job-from-other-project')).toBeNull()
  })

  it('transitions a working job to silent', () => {
    store.setJobs([
      {
        job_id: 'job-active',
        agent_id: 'agent-active',
        agent_display_name: 'tester',
        status: 'working',
      },
    ])

    expect(store.getJob('job-active').status).toBe('working')

    store.handleStatusChanged({
      job_id: 'job-active',
      status: 'silent',
      project_id: 'proj-1',
      agent_display_name: 'tester',
    })

    const job = store.getJob('job-active')
    expect(job.status).toBe('silent')
  })

  it('does not overwrite other fields when updating status', () => {
    store.setJobs([
      {
        job_id: 'job-identity',
        agent_id: 'agent-identity',
        agent_display_name: 'reviewer',
        agent_name: 'Code Reviewer',
        status: 'working',
        progress: 75,
      },
    ])

    store.handleStatusChanged({
      job_id: 'job-identity',
      status: 'silent',
    })

    const job = store.getJob('job-identity')
    expect(job.status).toBe('silent')
    expect(job.agent_display_name).toBe('reviewer')
    expect(job.agent_name).toBe('Code Reviewer')
    expect(job.progress).toBe(75)
  })

  it('handles status with agent_id resolution (not just job_id)', () => {
    store.setJobs([
      {
        job_id: 'job-uuid-1',
        agent_id: 'executor-uuid-1',
        agent_display_name: 'analyzer',
        status: 'working',
      },
    ])

    store.handleStatusChanged({
      job_id: 'job-uuid-1',
      agent_id: 'executor-uuid-1',
      status: 'complete',
    })

    const job = store.getJob('job-uuid-1')
    expect(job).toBeTruthy()
    expect(job.status).toBe('complete')
  })

  it('handles payload with no status gracefully', () => {
    store.setJobs([
      {
        job_id: 'job-noop',
        agent_id: 'agent-noop',
        agent_display_name: 'implementer',
        status: 'working',
      },
    ])

    store.handleStatusChanged({
      job_id: 'job-noop',
    })

    const job = store.getJob('job-noop')
    expect(job.status).toBe('working')
  })
})
