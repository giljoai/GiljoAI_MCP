/**
 * ProjectTabs Store - Steps Transformation Tests
 *
 * Handover 0334: Tests for transforming flat steps fields to nested object
 *
 * API returns: { steps_total: 5, steps_completed: 3, current_step: "..." }
 * UI expects:  { steps: { total: 5, completed: 3, current: "..." } }
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useProjectTabsStore } from '@/stores/projectTabs'

describe('ProjectTabs Store - Steps Transformation (Handover 0334)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  describe('transformJobSteps helper', () => {
    it('transforms flat steps fields to nested object', () => {
      const store = useProjectTabsStore()

      // Simulate job data from API with flat fields
      const jobFromApi = {
        job_id: 'job-123',
        agent_type: 'implementer',
        status: 'working',
        steps_total: 5,
        steps_completed: 3,
        current_step: 'Writing tests'
      }

      // Transform job data
      const transformed = store.transformJobSteps(jobFromApi)

      // Verify nested steps object
      expect(transformed.steps).toBeDefined()
      expect(transformed.steps.total).toBe(5)
      expect(transformed.steps.completed).toBe(3)
      expect(transformed.steps.current).toBe('Writing tests')
    })

    it('handles missing steps fields gracefully', () => {
      const store = useProjectTabsStore()

      // Job without steps data
      const jobFromApi = {
        job_id: 'job-456',
        agent_type: 'orchestrator',
        status: 'working'
      }

      const transformed = store.transformJobSteps(jobFromApi)

      // Should have steps object with null/0 values
      expect(transformed.steps).toBeDefined()
      expect(transformed.steps.total).toBe(0)
      expect(transformed.steps.completed).toBe(0)
      expect(transformed.steps.current).toBeNull()
    })

    it('handles null steps values', () => {
      const store = useProjectTabsStore()

      const jobFromApi = {
        job_id: 'job-789',
        agent_type: 'tester',
        status: 'waiting',
        steps_total: null,
        steps_completed: null,
        current_step: null
      }

      const transformed = store.transformJobSteps(jobFromApi)

      expect(transformed.steps.total).toBe(0)
      expect(transformed.steps.completed).toBe(0)
      expect(transformed.steps.current).toBeNull()
    })

    it('preserves existing steps object if already nested', () => {
      const store = useProjectTabsStore()

      // Job that already has nested steps object
      const jobWithNestedSteps = {
        job_id: 'job-abc',
        agent_type: 'analyzer',
        status: 'working',
        steps: {
          total: 8,
          completed: 4,
          current: 'Analyzing dependencies'
        }
      }

      const transformed = store.transformJobSteps(jobWithNestedSteps)

      // Should preserve existing nested structure
      expect(transformed.steps.total).toBe(8)
      expect(transformed.steps.completed).toBe(4)
      expect(transformed.steps.current).toBe('Analyzing dependencies')
    })
  })

  describe('setProject with steps transformation', () => {
    it('transforms agent steps when setting project', () => {
      const store = useProjectTabsStore()

      const project = {
        id: 'project-1',
        name: 'Test Project',
        agents: [
          {
            job_id: 'job-1',
            agent_type: 'orchestrator',
            status: 'working',
            steps_total: 7,
            steps_completed: 2,
            current_step: 'Spawning agents'
          },
          {
            job_id: 'job-2',
            agent_type: 'implementer',
            status: 'waiting',
            steps_total: 10,
            steps_completed: 0,
            current_step: null
          }
        ]
      }

      store.setProject(project)

      // Verify first agent steps transformed
      expect(store.agents[0].steps).toBeDefined()
      expect(store.agents[0].steps.total).toBe(7)
      expect(store.agents[0].steps.completed).toBe(2)
      expect(store.agents[0].steps.current).toBe('Spawning agents')

      // Verify second agent steps transformed
      expect(store.agents[1].steps).toBeDefined()
      expect(store.agents[1].steps.total).toBe(10)
      expect(store.agents[1].steps.completed).toBe(0)
      expect(store.agents[1].steps.current).toBeNull()
    })
  })

  describe('addAgent with steps transformation', () => {
    it('transforms steps when adding agent', () => {
      const store = useProjectTabsStore()

      // Set up project first
      store.setProject({ id: 'project-1', name: 'Test', agents: [] })

      // Add agent with flat steps
      store.addAgent({
        job_id: 'new-job',
        agent_type: 'documenter',
        status: 'waiting',
        steps_total: 3,
        steps_completed: 0,
        current_step: 'Initializing'
      })

      const addedAgent = store.agents.find(a => a.job_id === 'new-job')
      expect(addedAgent.steps).toBeDefined()
      expect(addedAgent.steps.total).toBe(3)
      expect(addedAgent.steps.completed).toBe(0)
      expect(addedAgent.steps.current).toBe('Initializing')
    })
  })

  describe('updateAgent with steps transformation', () => {
    it('transforms steps when updating agent', () => {
      const store = useProjectTabsStore()

      // Set up project with agent
      store.setProject({
        id: 'project-1',
        name: 'Test',
        agents: [
          {
            job_id: 'job-1',
            agent_type: 'implementer',
            status: 'working',
            steps: { total: 5, completed: 2, current: 'Step 2' }
          }
        ]
      })

      // Update agent with flat steps fields (simulating WebSocket update)
      store.updateAgent('job-1', {
        steps_total: 5,
        steps_completed: 4,
        current_step: 'Almost done'
      })

      const agent = store.agents.find(a => a.job_id === 'job-1')
      expect(agent.steps.completed).toBe(4)
      expect(agent.steps.current).toBe('Almost done')
    })
  })
})
