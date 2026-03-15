/**
 * agentJobsStore - handleStatusChanged new_status mapping tests
 *
 * Validates the fix where EventFactory.agent_status_changed() sends `new_status`
 * but the store's job object uses `status`. Without the mapping, status changes
 * from the silence detector (and auto-clear) were silently ignored.
 *
 * Edition Scope: CE
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAgentJobsStore } from '@/stores/agentJobsStore'

describe('agentJobsStore - handleStatusChanged new_status mapping', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useAgentJobsStore()
  })

  it('maps new_status to status when payload has new_status but no status', () => {
    // Setup: Add a job that is currently working
    store.setJobs([
      {
        job_id: 'job-1',
        agent_id: 'agent-1',
        agent_display_name: 'implementer',
        status: 'working',
      },
    ])

    // Act: Receive a status change with new_status (as EventFactory sends)
    store.handleStatusChanged({
      job_id: 'job-1',
      new_status: 'silent',
    })

    // Assert: The job should now have status 'silent'
    const job = store.getJob('job-1')
    expect(job).toBeTruthy()
    expect(job.status).toBe('silent')
  })

  it('preserves explicit status when both status and new_status are present', () => {
    // Setup: Add a working job
    store.setJobs([
      {
        job_id: 'job-2',
        agent_id: 'agent-2',
        agent_display_name: 'orchestrator',
        status: 'working',
      },
    ])

    // Act: Receive a payload with both fields -- explicit status should win
    store.handleStatusChanged({
      job_id: 'job-2',
      status: 'complete',
      new_status: 'silent',
    })

    // Assert: Explicit status field takes precedence
    const job = store.getJob('job-2')
    expect(job).toBeTruthy()
    expect(job.status).toBe('complete')
  })

  it('ignores status changes for unknown jobs (prevents ghost rows)', () => {
    // Setup: Add one known job
    store.setJobs([
      {
        job_id: 'known-job',
        agent_id: 'known-agent',
        agent_display_name: 'implementer',
        status: 'working',
      },
    ])

    const countBefore = store.jobCount

    // Act: Receive a status change for a job_id NOT in the store
    store.handleStatusChanged({
      job_id: 'unknown-job-from-other-project',
      new_status: 'silent',
    })

    // Assert: No new job was created -- store size unchanged
    expect(store.jobCount).toBe(countBefore)
    expect(store.getJob('unknown-job-from-other-project')).toBeNull()
  })

  it('transitions a working job to silent via new_status mapping', () => {
    // Setup: A job that is actively working
    store.setJobs([
      {
        job_id: 'job-active',
        agent_id: 'agent-active',
        agent_display_name: 'tester',
        status: 'working',
      },
    ])

    // Pre-condition: verify it is working
    expect(store.getJob('job-active').status).toBe('working')

    // Act: Silence detector fires agent_status_changed with new_status
    store.handleStatusChanged({
      job_id: 'job-active',
      new_status: 'silent',
      project_id: 'proj-1',
      agent_display_name: 'tester',
    })

    // Assert: Status is now silent
    const job = store.getJob('job-active')
    expect(job.status).toBe('silent')
  })

  it('does not overwrite other fields when mapping new_status', () => {
    // Setup: A job with identity fields
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

    // Act: Status change via new_status
    store.handleStatusChanged({
      job_id: 'job-identity',
      new_status: 'silent',
    })

    // Assert: Identity and progress fields preserved
    const job = store.getJob('job-identity')
    expect(job.status).toBe('silent')
    expect(job.agent_display_name).toBe('reviewer')
    expect(job.agent_name).toBe('Code Reviewer')
    expect(job.progress).toBe(75)
  })

  it('handles new_status with agent_id resolution (not just job_id)', () => {
    // Setup: Add a job keyed by agent_id
    store.setJobs([
      {
        job_id: 'job-uuid-1',
        agent_id: 'executor-uuid-1',
        agent_display_name: 'analyzer',
        status: 'working',
      },
    ])

    // Act: Status change referencing both job_id and agent_id
    // Real events typically include job_id, but agent_id is used for resolution fallback
    store.handleStatusChanged({
      job_id: 'job-uuid-1',
      agent_id: 'executor-uuid-1',
      new_status: 'complete',
    })

    // Assert: Job resolved and status updated
    const job = store.getJob('job-uuid-1')
    expect(job).toBeTruthy()
    expect(job.status).toBe('complete')
  })

  it('handles payload with no new_status and no status gracefully', () => {
    // Setup: Add a job
    store.setJobs([
      {
        job_id: 'job-noop',
        agent_id: 'agent-noop',
        agent_display_name: 'implementer',
        status: 'working',
      },
    ])

    // Act: Status change with neither field -- should be a no-op on status
    store.handleStatusChanged({
      job_id: 'job-noop',
    })

    // Assert: Status unchanged (upsert merges but no status field provided)
    const job = store.getJob('job-noop')
    expect(job.status).toBe('working')
  })
})
