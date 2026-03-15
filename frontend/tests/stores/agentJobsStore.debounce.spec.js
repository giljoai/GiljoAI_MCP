/**
 * agentJobsStore - Deep equality and debounced WebSocket update tests
 *
 * Phase 1: Validates that isEqual (lodash-es) replaces JSON.stringify
 * for proper deep equality detection, preventing unnecessary reactivity.
 *
 * Phase 2: Validates that minor WebSocket event handlers (progress,
 * message sent/received/acknowledged) use debounced updates while
 * lifecycle handlers (status changed, created, updated) flush immediately.
 *
 * Edition Scope: CE
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAgentJobsStore } from '@/stores/agentJobsStore'

/** Seed a store with a standard working job and return the store. */
function seedJob(store, overrides = {}) {
  const defaults = {
    job_id: 'job-1',
    agent_id: 'agent-1',
    agent_display_name: 'implementer',
    agent_name: 'Implementer Agent',
    status: 'working',
    progress: 50,
    messages_sent_count: 2,
    messages_waiting_count: 1,
    messages_read_count: 1,
  }
  store.setJobs([{ ...defaults, ...overrides }])
  return store
}

describe('agentJobsStore - Phase 1: Deep equality check', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useAgentJobsStore()
  })

  it('upsertJob with identical data does not trigger reactivity', () => {
    seedJob(store)

    const mapBefore = store.jobsById.value

    // Act: upsert with the exact same data
    store.upsertJob({
      job_id: 'job-1',
      agent_id: 'agent-1',
      agent_display_name: 'implementer',
      agent_name: 'Implementer Agent',
      status: 'working',
      progress: 50,
      messages_sent_count: 2,
      messages_waiting_count: 1,
      messages_read_count: 1,
    })

    // Assert: Map reference should be unchanged (no new Map created)
    expect(store.jobsById.value).toBe(mapBefore)
  })

  it('upsertJob with changed data triggers reactivity', () => {
    seedJob(store)

    const mapBefore = store.jobsById.value

    // Act: upsert with different progress value
    store.upsertJob({
      job_id: 'job-1',
      agent_id: 'agent-1',
      progress: 75,
    })

    // Assert: Map reference should be different (new Map was created)
    expect(store.jobsById.value).not.toBe(mapBefore)
    expect(store.getJob('agent-1').progress).toBe(75)
  })
})

describe('agentJobsStore - Phase 2: Debounced store updates', () => {
  let store

  beforeEach(() => {
    vi.useFakeTimers()
    setActivePinia(createPinia())
    store = useAgentJobsStore()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('handleProgressUpdate queues debounced updates', () => {
    seedJob(store)
    const mapBefore = store.jobsById.value

    // Act: fire a progress update
    store.handleProgressUpdate({
      job_id: 'job-1',
      agent_id: 'agent-1',
      progress: 80,
      current_task: 'Writing tests',
      last_progress_at: '2026-03-14T10:00:00Z',
    })

    // Assert: Map reference should NOT have changed yet (debounced)
    expect(store.jobsById.value).toBe(mapBefore)

    // Act: flush debounce timer
    vi.advanceTimersByTime(300)

    // Assert: Now it should have changed
    expect(store.jobsById.value).not.toBe(mapBefore)
    expect(store.getJob('agent-1').progress).toBe(80)
    expect(store.getJob('agent-1').current_task).toBe('Writing tests')
  })

  it('handleMessageSent queues debounced updates', () => {
    seedJob(store)
    const mapBefore = store.jobsById.value

    // Act: fire a message sent event
    store.handleMessageSent({
      from_job_id: 'agent-1',
      sender_sent_count: 5,
    })

    // Assert: Map reference should NOT have changed yet (debounced)
    expect(store.jobsById.value).toBe(mapBefore)

    // Act: flush debounce timer
    vi.advanceTimersByTime(300)

    // Assert: Now it should have changed
    expect(store.jobsById.value).not.toBe(mapBefore)
    expect(store.getJob('agent-1').messages_sent_count).toBe(5)
  })

  it('handleMessageReceived queues debounced updates', () => {
    seedJob(store)
    const mapBefore = store.jobsById.value

    // Act: fire a message received event
    store.handleMessageReceived({
      to_agent_ids: ['agent-1'],
      waiting_count: 3,
    })

    // Assert: Map reference should NOT have changed yet (debounced)
    expect(store.jobsById.value).toBe(mapBefore)

    // Act: flush debounce timer
    vi.advanceTimersByTime(300)

    // Assert: Now it should have changed
    expect(store.jobsById.value).not.toBe(mapBefore)
    expect(store.getJob('agent-1').messages_waiting_count).toBe(3)
  })

  it('handleMessageAcknowledged queues debounced updates', () => {
    seedJob(store)
    const mapBefore = store.jobsById.value

    // Act: fire a message acknowledged event
    store.handleMessageAcknowledged({
      agent_id: 'agent-1',
      waiting_count: 0,
      read_count: 5,
    })

    // Assert: Map reference should NOT have changed yet (debounced)
    expect(store.jobsById.value).toBe(mapBefore)

    // Act: flush debounce timer
    vi.advanceTimersByTime(300)

    // Assert: Now it should have changed
    expect(store.jobsById.value).not.toBe(mapBefore)
    expect(store.getJob('agent-1').messages_waiting_count).toBe(0)
    expect(store.getJob('agent-1').messages_read_count).toBe(5)
  })

  it('multiple rapid debounced updates batch into single Map change', () => {
    seedJob(store)

    // Capture initial Map reference
    const mapAfterSeed = store.jobsById.value
    let changeCount = 0

    // Track Map reference changes by checking after each timer tick
    const checkRef = store.jobsById.value

    // Act: fire 3 rapid progress updates
    store.handleProgressUpdate({
      job_id: 'job-1',
      agent_id: 'agent-1',
      progress: 60,
      last_progress_at: '2026-03-14T10:00:01Z',
    })
    store.handleProgressUpdate({
      job_id: 'job-1',
      agent_id: 'agent-1',
      progress: 70,
      last_progress_at: '2026-03-14T10:00:02Z',
    })
    store.handleProgressUpdate({
      job_id: 'job-1',
      agent_id: 'agent-1',
      progress: 80,
      last_progress_at: '2026-03-14T10:00:03Z',
    })

    // Assert: no changes yet
    expect(store.jobsById.value).toBe(mapAfterSeed)

    // Act: flush
    vi.advanceTimersByTime(300)

    // Assert: only the final merged state is applied (single Map swap)
    expect(store.jobsById.value).not.toBe(mapAfterSeed)
    expect(store.getJob('agent-1').progress).toBe(80)
    expect(store.getJob('agent-1').last_progress_at).toBe('2026-03-14T10:00:03Z')
  })

  it('handleStatusChanged flushes immediately', () => {
    seedJob(store)
    const mapBefore = store.jobsById.value

    // Act: fire a status change (should be immediate, no debounce)
    store.handleStatusChanged({
      job_id: 'job-1',
      new_status: 'silent',
    })

    // Assert: Map reference should have changed immediately
    expect(store.jobsById.value).not.toBe(mapBefore)
    expect(store.getJob('agent-1').status).toBe('silent')
  })

  it('handleCreated flushes immediately', () => {
    // Act: create a new job (should be immediate, no debounce)
    store.handleCreated({
      job_id: 'new-job',
      agent_id: 'new-agent',
      agent_display_name: 'reviewer',
      status: 'working',
    })

    // Assert: job should exist immediately
    expect(store.getJob('new-agent')).toBeTruthy()
    expect(store.getJob('new-agent').status).toBe('working')
  })

  it('debounced updates merge correctly', () => {
    seedJob(store)

    // Act: queue two updates for the same job with different fields
    store.handleProgressUpdate({
      job_id: 'job-1',
      agent_id: 'agent-1',
      progress: 90,
      last_progress_at: '2026-03-14T10:00:00Z',
    })
    store.handleMessageSent({
      from_job_id: 'agent-1',
      sender_sent_count: 10,
    })

    // Assert: no changes yet
    const mapBefore = store.jobsById.value

    // Act: flush
    vi.advanceTimersByTime(300)

    // Assert: both fields should be present after merge
    expect(store.jobsById.value).not.toBe(mapBefore)
    const job = store.getJob('agent-1')
    expect(job.progress).toBe(90)
    expect(job.messages_sent_count).toBe(10)
  })

  it('handleStatusChanged flushes pending debounced updates for same job', () => {
    seedJob(store)

    // Act: queue a progress update (debounced)
    store.handleProgressUpdate({
      job_id: 'job-1',
      agent_id: 'agent-1',
      progress: 95,
      last_progress_at: '2026-03-14T10:00:00Z',
    })

    // No time has passed -- progress update is still pending
    expect(store.getJob('agent-1').progress).toBe(50) // original value

    // Act: fire a status change (immediate) -- should flush pending first
    store.handleStatusChanged({
      job_id: 'job-1',
      new_status: 'complete',
    })

    // Assert: both the pending progress update AND the status change should be applied
    const job = store.getJob('agent-1')
    expect(job.status).toBe('complete')
    expect(job.progress).toBe(95)
  })

  it('flushPendingUpdates is exposed and works synchronously', () => {
    seedJob(store)

    // Act: queue a progress update
    store.handleProgressUpdate({
      job_id: 'job-1',
      agent_id: 'agent-1',
      progress: 42,
      last_progress_at: '2026-03-14T10:00:00Z',
    })

    // Assert: not applied yet
    expect(store.getJob('agent-1').progress).toBe(50)

    // Act: explicit flush
    store.flushPendingUpdates()

    // Assert: applied after explicit flush
    expect(store.getJob('agent-1').progress).toBe(42)
  })
})
