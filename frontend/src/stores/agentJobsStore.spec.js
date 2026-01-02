import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { useAgentJobsStore } from '@/stores/agentJobsStore'

describe('agentJobsStore (map-based)', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useAgentJobsStore()
    store.$reset?.()
  })

  it('updates immutably on create/update/status change', () => {
    store.handleCreated({ job_id: 'job-1', agent_type: 'implementer', status: 'working' })

    const jobBefore = store.getJob('job-1')
    expect(jobBefore).toBeDefined()

    store.handleUpdated({ job_id: 'job-1', progress: 50 })
    const jobAfterUpdate = store.getJob('job-1')

    expect(jobAfterUpdate).not.toBe(jobBefore)
    expect(jobBefore.progress).toBeUndefined()
    expect(jobAfterUpdate.progress).toBe(50)

    store.handleStatusChanged({ job_id: 'job-1', status: 'complete' })
    const jobAfterStatus = store.getJob('job-1')

    expect(jobAfterStatus).not.toBe(jobAfterUpdate)
    expect(jobAfterStatus.status).toBe('complete')
  })

  it('dedupes duplicate created events by job_id', () => {
    store.handleCreated({ job_id: 'job-1', status: 'waiting' })
    store.handleCreated({ job_id: 'job-1', status: 'working', progress: 10 })

    expect(store.jobCount).toBe(1)
    expect(store.getJob('job-1')).toEqual(expect.objectContaining({ status: 'working', progress: 10 }))
  })

  it('updates message counters for sent/received/acknowledged', () => {
    store.handleCreated({ job_id: 'job-a', agent_type: 'orchestrator', status: 'working' })
    store.handleCreated({ job_id: 'job-b', agent_type: 'implementer', status: 'waiting' })

    const senderBefore = store.getJob('job-a')
    store.handleMessageSent({
      message_id: 'm1',
      from_agent: 'job-a',
      to_agent_ids: ['job-b'],
      message_type: 'direct',
      timestamp: '2025-12-25T00:00:00Z',
    })
    const senderAfter = store.getJob('job-a')

    expect(senderAfter).not.toBe(senderBefore)
    expect(senderAfter.messages_sent_count).toBe(1)

    const recipientBefore = store.getJob('job-b')
    store.handleMessageReceived({
      message_id: 'm1',
      from_agent: 'job-a',
      to_agent_ids: ['job-b'],
      timestamp: '2025-12-25T00:00:00Z',
    })
    const recipientAfterReceived = store.getJob('job-b')
    expect(recipientAfterReceived).not.toBe(recipientBefore)
    expect(recipientAfterReceived.messages_waiting_count).toBe(1)
    expect(recipientAfterReceived.messages_read_count).toBe(0)

    store.handleMessageAcknowledged({
      agent_id: 'job-b',
      message_id: 'm1',
    })
    const recipientAfterAck = store.getJob('job-b')
    expect(recipientAfterAck.messages_waiting_count).toBe(0)
    expect(recipientAfterAck.messages_read_count).toBe(1)
  })

  // Handover 0388: Tests for undefined value filtering
  describe('handleProgressUpdate', () => {
    it('should not overwrite job_metadata when todo_steps is missing', () => {
      // Setup: Job with existing metadata
      store.setJobs([{
        job_id: 'test-1',
        agent_type: 'orchestrator',
        status: 'working',
        job_metadata: { existing: true }
      }])

      // Action: Progress update without todo_steps
      store.handleProgressUpdate({ job_id: 'test-1', progress: 50 })

      // Assert: Existing metadata and agent_type preserved
      const job = store.getJob('test-1')
      expect(job.job_metadata).toEqual({ existing: true })
      expect(job.agent_type).toBe('orchestrator')
      expect(job.progress).toBe(50)
    })

    it('should update job_metadata when todo_steps is provided', () => {
      store.setJobs([{ job_id: 'test-1', status: 'working', job_metadata: null }])

      store.handleProgressUpdate({
        job_id: 'test-1',
        todo_steps: [{ name: 'Step 1', status: 'done' }]
      })

      expect(store.getJob('test-1').job_metadata).toEqual({
        todo_steps: [{ name: 'Step 1', status: 'done' }]
      })
    })

    it('should preserve all existing fields when progress updates arrive', () => {
      // Setup: Complete job with all fields
      store.setJobs([{
        job_id: 'test-1',
        agent_type: 'implementer',
        agent_name: 'frontend-implementer',
        status: 'working',
        mission: 'Implement feature X',
        job_metadata: { priority: 'high' }
      }])

      // Action: Multiple progress updates without todo_steps
      store.handleProgressUpdate({ job_id: 'test-1', progress: 25, current_task: 'Task 1' })
      store.handleProgressUpdate({ job_id: 'test-1', progress: 50, current_task: 'Task 2' })
      store.handleProgressUpdate({ job_id: 'test-1', progress: 75, current_task: 'Task 3' })

      // Assert: All original fields preserved
      const job = store.getJob('test-1')
      expect(job.agent_type).toBe('implementer')
      expect(job.agent_name).toBe('frontend-implementer')
      expect(job.status).toBe('working')
      expect(job.mission).toBe('Implement feature X')
      expect(job.job_metadata).toEqual({ priority: 'high' })
      expect(job.progress).toBe(75)
      expect(job.current_task).toBe('Task 3')
    })
  })

  describe('upsertJob undefined filtering', () => {
    it('should filter undefined values and preserve existing fields', () => {
      store.setJobs([{ job_id: 'test-1', agent_type: 'implementer', status: 'waiting' }])

      // Patch with undefined value - should NOT overwrite agent_type
      store.upsertJob({ job_id: 'test-1', status: 'working', agent_type: undefined })

      const job = store.getJob('test-1')
      expect(job.status).toBe('working')
      expect(job.agent_type).toBe('implementer')  // Preserved, not overwritten
    })

    it('should allow explicit null values (distinct from undefined)', () => {
      store.setJobs([{ job_id: 'test-1', mission: 'Old mission', status: 'waiting' }])

      // Null is intentional clearing, undefined is "no value provided"
      store.upsertJob({ job_id: 'test-1', mission: null })

      const job = store.getJob('test-1')
      expect(job.mission).toBeNull()
    })

    it('should handle multiple undefined fields without corruption', () => {
      store.setJobs([{
        job_id: 'test-1',
        agent_type: 'orchestrator',
        agent_name: 'main-orchestrator',
        status: 'working',
        progress: 50,
        job_metadata: { key: 'value' }
      }])

      // Patch with multiple undefined fields
      store.upsertJob({
        job_id: 'test-1',
        agent_type: undefined,
        agent_name: undefined,
        progress: 75,
        job_metadata: undefined
      })

      const job = store.getJob('test-1')
      expect(job.agent_type).toBe('orchestrator')
      expect(job.agent_name).toBe('main-orchestrator')
      expect(job.progress).toBe(75)
      expect(job.job_metadata).toEqual({ key: 'value' })
    })
  })
})
