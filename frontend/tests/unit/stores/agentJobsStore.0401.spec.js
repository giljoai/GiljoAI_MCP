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
 * - handleMessageSent/handleMessageReceived also use debounced updates
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

  describe('handleMessageSent() - agent_id resolution', () => {
    it('should resolve sender by agent_id when from_agent is agent_id', () => {
      // Setup: Add a job with both identifiers
      const jobId = 'sender-job-id'
      const agentId = 'sender-agent-execution-id'
      store.setJobs([
        {
          job_id: jobId,
          agent_id: agentId,
          agent_display_name: 'orchestrator',
          status: 'working',
          messages: [],
          messages_sent_count: 0,
        },
      ])

      // Action: Handle message:sent with from_agent as agent_id then flush
      store.handleMessageSent({
        message_id: 'msg-001',
        from_agent: agentId, // This is agent_id, not job_id
        to_agent_ids: ['recipient-agent-id'],
        timestamp: new Date().toISOString(),
        message_type: 'direct',
      })

      store.flushPendingUpdates()

      // Assert: Sender's message count should increment
      const job = store.getJob(jobId)
      expect(job.messages_sent_count).toBe(1)
    })
  })

  describe('handleMessageReceived() - agent_id resolution', () => {
    it('should resolve recipients by agent_id in to_agent_ids', () => {
      // Setup: Add recipient jobs with agent_ids
      const job1Id = 'recipient-job-1'
      const agent1Id = 'recipient-agent-execution-1'
      const job2Id = 'recipient-job-2'
      const agent2Id = 'recipient-agent-execution-2'

      store.setJobs([
        {
          job_id: job1Id,
          agent_id: agent1Id,
          agent_display_name: 'analyzer',
          status: 'working',
          messages: [],
          messages_waiting_count: 0,
        },
        {
          job_id: job2Id,
          agent_id: agent2Id,
          agent_display_name: 'implementer',
          status: 'working',
          messages: [],
          messages_waiting_count: 0,
        },
      ])

      // Action: Handle message:received with agent_ids then flush
      store.handleMessageReceived({
        message_id: 'msg-002',
        from_agent: 'sender-agent-id',
        to_agent_ids: [agent1Id, agent2Id], // These are agent_ids
        timestamp: new Date().toISOString(),
        message_type: 'broadcast',
      })

      store.flushPendingUpdates()

      // Assert: Both recipients should have waiting message
      const job1 = store.getJob(job1Id)
      const job2 = store.getJob(job2Id)
      expect(job1.messages_waiting_count).toBe(1)
      expect(job2.messages_waiting_count).toBe(1)
    })
  })
})
