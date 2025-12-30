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
})
