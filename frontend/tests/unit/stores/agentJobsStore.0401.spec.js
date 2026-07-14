/**
 * agentJobsStore Tests - Handover 0401: Unified WebSocket Platform
 *
 * Tests for resolveJobId() and handleProgressUpdate() fixes
 *
 * Test BEHAVIOR, not implementation:
 * - resolveJobId() should resolve by agent_id (executor UUID)
 * - handleProgressUpdate() should transform todo_steps array to steps object
 *
 * Post-refactor notes:
 * - handleProgressUpdate uses upsertJobDebounced (Handover 0818)
 *   so flushPendingUpdates() must be called to apply the updates
 * - steps object now includes { completed, skipped, total } (Handover 0401)
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAgentJobsStore } from '@/stores/agentJobsStore'

describe('agentJobsStore - Handover 0401 Fixes', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useAgentJobsStore()
  })

  describe('resolveJobId() - agent_id resolution', () => {
    it('should resolve job_id when given a direct job_id match', () => {
      // Setup: Add a job with a known job_id
      const jobId = 'job-uuid-123'
      store.setJobs([
        {
          job_id: jobId,
          agent_id: 'agent-uuid-456',
          agent_display_name: 'implementer',
          agent_name: 'analyzer',
          status: 'working',
        },
      ])

      // Action: Resolve by job_id
      const result = store.resolveJobId(jobId)

      // Assert: Should find the job (returns unique_key, not null)
      expect(result).not.toBeNull()
    })

    it('should resolve when given an agent_id (executor UUID)', () => {
      // Setup: Add a job with both job_id and agent_id
      const jobId = 'job-uuid-789'
      const agentId = 'agent-uuid-execution-abc'
      store.setJobs([
        {
          job_id: jobId,
          agent_id: agentId,
          agent_display_name: 'orchestrator',
          agent_name: 'orchestrator',
          status: 'working',
        },
      ])

      // Action: Try to resolve by agent_id
      const resolved = store.resolveJobId(agentId)

      // Assert: Should return a non-null unique_key
      expect(resolved).not.toBeNull()

      // And that key should retrieve the correct job
      const job = store.getJob(jobId)
      expect(job).not.toBeNull()
      expect(job.agent_id).toBe(agentId)
    })

    it('should resolve by agent_display_name for legacy compatibility', () => {
      // Setup: Add a job
      const jobId = 'legacy-job-id'
      store.setJobs([
        {
          job_id: jobId,
          agent_id: 'some-agent-id',
          agent_display_name: 'tester',
          agent_name: 'quality-checker',
          status: 'waiting',
        },
      ])

      // Action: Resolve by agent_display_name (legacy behavior)
      const resolved = store.resolveJobId('tester')

      // Assert: Should find by agent_display_name
      expect(resolved).not.toBeNull()
    })

    it('should return null for unknown identifier', () => {
      // Setup: Add a job
      store.setJobs([
        {
          job_id: 'known-job',
          agent_id: 'known-agent',
          agent_display_name: 'analyzer',
          status: 'complete',
        },
      ])

      // Action: Try to resolve unknown identifier
      const resolved = store.resolveJobId('completely-unknown-uuid')

      // Assert: Should return null
      expect(resolved).toBeNull()
    })
  })

  describe('handleProgressUpdate() - todo_steps transformation', () => {
    it('should transform todo_steps array to steps summary object', () => {
      // Setup: Add a job
      const jobId = 'progress-job-id'
      store.setJobs([
        {
          job_id: jobId,
          agent_display_name: 'implementer',
          status: 'working',
        },
      ])

      // Action: Call handleProgressUpdate with todo_steps then flush
      store.handleProgressUpdate({
        job_id: jobId,
        progress: 40,
        current_task: 'Implementing feature X',
        todo_steps: [
          { name: 'Setup environment', status: 'done' },
          { name: 'Write tests', status: 'done' },
          { name: 'Implement feature', status: 'in_progress' },
          { name: 'Run tests', status: 'pending' },
          { name: 'Documentation', status: 'pending' },
        ],
      })

      // Flush debounced updates
      store.flushPendingUpdates()

      // Assert: Job should have steps summary object
      const job = store.getJob(jobId)
      expect(job).toBeTruthy()

      expect(job.steps).toBeDefined()
      expect(typeof job.steps.completed).toBe('number')
      expect(typeof job.steps.total).toBe('number')
      expect(job.steps.completed).toBe(2) // 'done' count
      expect(job.steps.total).toBe(5) // total steps
    })

    it('should count completed status variations correctly', () => {
      // Setup: Add a job
      const jobId = 'varied-status-job'
      store.setJobs([
        {
          job_id: jobId,
          agent_display_name: 'tester',
          status: 'working',
        },
      ])

      // Action: Call handleProgressUpdate with various status values then flush
      store.handleProgressUpdate({
        job_id: jobId,
        progress: 60,
        todo_steps: [
          { name: 'Task 1', status: 'done' },
          { name: 'Task 2', status: 'completed' }, // Alternative completed status
          { name: 'Task 3', status: 'done' },
          { name: 'Task 4', status: 'pending' },
        ],
      })

      store.flushPendingUpdates()

      // Assert: Should count both 'done' and 'completed' as completed
      const job = store.getJob(jobId)
      expect(job.steps.completed).toBe(3) // 'done' + 'completed'
      expect(job.steps.total).toBe(4)
    })

    it('should preserve job_metadata.todo_steps array alongside steps summary', () => {
      // Setup: Add a job
      const jobId = 'metadata-preservation-job'
      store.setJobs([
        {
          job_id: jobId,
          agent_display_name: 'analyzer',
          status: 'working',
        },
      ])

      const todoSteps = [
        { name: 'Analyze codebase', status: 'done' },
        { name: 'Generate report', status: 'pending' },
      ]

      // Action: Call handleProgressUpdate then flush
      store.handleProgressUpdate({
        job_id: jobId,
        progress: 50,
        todo_steps: todoSteps,
      })

      store.flushPendingUpdates()

      // Assert: Both steps summary AND job_metadata.todo_steps should exist
      const job = store.getJob(jobId)
      expect(job.steps).toBeDefined()
      expect(job.steps.completed).toBe(1)
      expect(job.steps.total).toBe(2)
      expect(job.job_metadata?.todo_steps).toEqual(todoSteps)
    })

    it('should handle empty todo_steps gracefully', () => {
      // Setup: Add a job
      const jobId = 'empty-steps-job'
      store.setJobs([
        {
          job_id: jobId,
          agent_display_name: 'implementer',
          status: 'working',
        },
      ])

      // Action: Call handleProgressUpdate without todo_steps then flush
      store.handleProgressUpdate({
        job_id: jobId,
        progress: 10,
        current_task: 'Starting work',
      })

      store.flushPendingUpdates()

      // Assert: progress should be updated, steps should not be set
      const job = store.getJob(jobId)
      expect(job.progress).toBe(10)
      // steps should remain undefined when no todo_steps provided
    })
  })

  describe('normalizeJob() - agent_id preservation', () => {
    it('should preserve agent_id when normalizing jobs from API', () => {
      // Setup: Create job data with agent_id (as returned from API)
      const rawJob = {
        job_id: 'api-job-id',
        agent_id: 'api-agent-execution-id',
        agent_display_name: 'documenter',
        agent_name: 'documentation-agent',
        status: 'working',
        messages: [],
      }

      // Action: Set jobs (which calls normalizeJob internally)
      store.setJobs([rawJob])

      // Assert: agent_id should be preserved
      const job = store.getJob('api-job-id')
      expect(job).toBeTruthy()
      expect(job.agent_id).toBe('api-agent-execution-id')
    })
  })

})
