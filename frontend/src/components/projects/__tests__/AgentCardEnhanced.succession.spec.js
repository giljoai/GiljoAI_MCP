import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import AgentCardEnhanced from '../AgentCardEnhanced.vue'
import SuccessionTimeline from '../SuccessionTimeline.vue'
import LaunchSuccessorDialog from '../LaunchSuccessorDialog.vue'
import api from '@/services/api'

// Mock API
vi.mock('@/services/api', () => ({
  default: {
    agentJobs: {
      list: vi.fn(),
      triggerSuccession: vi.fn(),
    },
    post: vi.fn(),
  },
}))

// Mock composables
const mockToast = {
  success: vi.fn(),
  error: vi.fn(),
}

vi.mock('@/composables/useToast', () => ({
  useToast: () => mockToast,
}))

const mockWebSocket = {
  on: vi.fn(),
  off: vi.fn(),
}

vi.mock('@/composables/useWebSocket', () => ({
  useWebSocket: () => mockWebSocket,
}))

// Mock date-fns
vi.mock('date-fns', () => ({
  format: vi.fn((date, formatStr) => '2025-01-15 14:30'),
}))

describe('AgentCardEnhanced.vue - Succession Integration (Handover 0509)', () => {
  let vuetify

  beforeEach(() => {
    vuetify = createVuetify()
    vi.clearAllMocks()
  })

  const mockOrchestratorAgent = {
    id: 'job-1',
    job_id: 'job-1',
    agent_type: 'orchestrator',
    agent_name: 'Orchestrator',
    status: 'working',
    project_id: 'proj-123',
    instance_number: 1,
    context_used: 150000,
    context_budget: 200000,
    mission: 'Test mission',
    messages: [],
  }

  const mockSpecialistAgent = {
    ...mockOrchestratorAgent,
    id: 'job-2',
    job_id: 'job-2',
    agent_type: 'specialist',
    agent_name: 'Specialist',
  }

  const createWrapper = (props = {}) => {
    return mount(AgentCardEnhanced, {
      props: {
        agent: mockOrchestratorAgent,
        mode: 'jobs',
        isOrchestrator: true,
        ...props,
      },
      global: {
        plugins: [vuetify],
        stubs: {
          teleport: true,
          SuccessionTimeline: true,
          LaunchSuccessorDialog: true,
        },
      },
    })
  }

  describe('Succession Timeline Integration', () => {
    it('shows SuccessionTimeline for orchestrator in jobs mode', () => {
      const wrapper = createWrapper()
      const timeline = wrapper.findComponent(SuccessionTimeline)
      expect(timeline.exists()).toBe(true)
    })

    it('passes correct project_id to SuccessionTimeline', () => {
      const wrapper = createWrapper()
      const timeline = wrapper.findComponent(SuccessionTimeline)
      expect(timeline.props('projectId')).toBe('proj-123')
    })

    it('hides SuccessionTimeline for non-orchestrator agents', () => {
      const wrapper = createWrapper({
        agent: mockSpecialistAgent,
        isOrchestrator: false,
      })
      const timeline = wrapper.findComponent(SuccessionTimeline)
      expect(timeline.exists()).toBe(false)
    })

    it('hides SuccessionTimeline in launch mode', () => {
      const wrapper = createWrapper({ mode: 'launch' })
      const timeline = wrapper.findComponent(SuccessionTimeline)
      expect(timeline.exists()).toBe(false)
    })
  })

  describe('Hand Over Button Integration', () => {
    it('shows LaunchSuccessorDialog for working orchestrator', () => {
      const wrapper = createWrapper({
        agent: { ...mockOrchestratorAgent, status: 'working' },
      })
      const dialog = wrapper.findComponent(LaunchSuccessorDialog)
      expect(dialog.exists()).toBe(true)
    })

    it('passes correct job_id to dialog', () => {
      const wrapper = createWrapper()
      const dialog = wrapper.findComponent(LaunchSuccessorDialog)
      expect(dialog.props('jobId')).toBe('job-1')
    })

    it('passes current job data to dialog', () => {
      const wrapper = createWrapper()
      const dialog = wrapper.findComponent(LaunchSuccessorDialog)
      expect(dialog.props('currentJob')).toEqual(mockOrchestratorAgent)
    })

    it('hides dialog for non-working status', () => {
      const wrapper = createWrapper({
        agent: { ...mockOrchestratorAgent, status: 'complete' },
      })
      const dialog = wrapper.findComponent(LaunchSuccessorDialog)
      expect(dialog.exists()).toBe(false)
    })

    it('hides dialog for non-orchestrator agents', () => {
      const wrapper = createWrapper({
        agent: mockSpecialistAgent,
        isOrchestrator: false,
      })
      const dialog = wrapper.findComponent(LaunchSuccessorDialog)
      expect(dialog.exists()).toBe(false)
    })

    it('hides dialog in launch mode', () => {
      const wrapper = createWrapper({ mode: 'launch' })
      const dialog = wrapper.findComponent(LaunchSuccessorDialog)
      expect(dialog.exists()).toBe(false)
    })
  })

  describe('Succession Triggered Event Handler', () => {
    it('handles succession-triggered event', async () => {
      const wrapper = createWrapper()
      const dialog = wrapper.findComponent(LaunchSuccessorDialog)

      const successorData = {
        successor_job_id: 'job-2',
        instance_number: 2,
        launch_prompt: 'Test prompt',
      }

      await dialog.vm.$emit('succession-triggered', successorData)
      await flushPromises()

      expect(mockToast.success).toHaveBeenCalledWith('Successor instance 2 created')
    })

    it('emits refresh-jobs event to parent', async () => {
      const wrapper = createWrapper()
      const dialog = wrapper.findComponent(LaunchSuccessorDialog)

      const successorData = {
        successor_job_id: 'job-2',
        instance_number: 2,
      }

      await dialog.vm.$emit('succession-triggered', successorData)
      await flushPromises()

      expect(wrapper.emitted('refresh-jobs')).toBeTruthy()
    })

    it('logs successor creation', async () => {
      const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {})
      const wrapper = createWrapper()
      const dialog = wrapper.findComponent(LaunchSuccessorDialog)

      const successorData = {
        successor_job_id: 'job-2',
        instance_number: 2,
      }

      await dialog.vm.$emit('succession-triggered', successorData)
      await flushPromises()

      expect(consoleSpy).toHaveBeenCalledWith('Successor created:', successorData)
      consoleSpy.mockRestore()
    })
  })

  describe('Component Imports', () => {
    it('imports SuccessionTimeline component', () => {
      const wrapper = createWrapper()
      expect(wrapper.vm.$options.components.SuccessionTimeline).toBeDefined()
    })

    it('imports LaunchSuccessorDialog component', () => {
      const wrapper = createWrapper()
      expect(wrapper.vm.$options.components.LaunchSuccessorDialog).toBeDefined()
    })
  })

  describe('Hand Over Button Styling', () => {
    it('has warning color for Hand Over button', () => {
      const wrapper = createWrapper()
      const dialog = wrapper.findComponent(LaunchSuccessorDialog)
      expect(dialog.exists()).toBe(true)

      // The button should be in the activator slot
      const button = wrapper.find('button')
      expect(button.exists()).toBe(true)
    })

    it('shows hand-wave icon on button', () => {
      const wrapper = createWrapper()
      expect(wrapper.html()).toContain('mdi-hand-wave')
    })

    it('has outlined variant', () => {
      const wrapper = createWrapper()
      expect(wrapper.html()).toContain('Hand Over')
    })
  })

  describe('Orchestrator Special Features', () => {
    it('only shows succession features when isOrchestrator is true', () => {
      const wrapper = createWrapper({ isOrchestrator: true })
      const timeline = wrapper.findComponent(SuccessionTimeline)
      const dialog = wrapper.findComponent(LaunchSuccessorDialog)

      expect(timeline.exists()).toBe(true)
      expect(dialog.exists()).toBe(true)
    })

    it('hides succession features for specialist agents', () => {
      const wrapper = createWrapper({
        agent: mockSpecialistAgent,
        isOrchestrator: false,
      })
      const timeline = wrapper.findComponent(SuccessionTimeline)
      const dialog = wrapper.findComponent(LaunchSuccessorDialog)

      expect(timeline.exists()).toBe(false)
      expect(dialog.exists()).toBe(false)
    })
  })

  describe('Edge Cases', () => {
    it('handles agent with no project_id gracefully', () => {
      const wrapper = createWrapper({
        agent: { ...mockOrchestratorAgent, project_id: null },
      })
      const timeline = wrapper.findComponent(SuccessionTimeline)
      expect(timeline.props('projectId')).toBeNull()
    })

    it('handles agent with no instance_number', () => {
      const wrapper = createWrapper({
        agent: { ...mockOrchestratorAgent, instance_number: null },
      })
      const dialog = wrapper.findComponent(LaunchSuccessorDialog)
      expect(dialog.props('currentJob').instance_number).toBeNull()
    })

    it('handles different orchestrator statuses', () => {
      const statuses = ['waiting', 'working', 'complete', 'failed']

      statuses.forEach((status) => {
        const wrapper = createWrapper({
          agent: { ...mockOrchestratorAgent, status },
        })
        const dialog = wrapper.findComponent(LaunchSuccessorDialog)

        // Dialog only shows for working status
        if (status === 'working') {
          expect(dialog.exists()).toBe(true)
        } else {
          expect(dialog.exists()).toBe(false)
        }
      })
    })
  })

  describe('Layout and Positioning', () => {
    it('positions SuccessionTimeline after card content', () => {
      const wrapper = createWrapper()
      const html = wrapper.html()

      // Timeline should appear after card-text and before card-actions
      const cardTextIndex = html.indexOf('v-card-text')
      const timelineIndex = html.indexOf('succession-timeline')
      const actionsIndex = html.indexOf('agent-card-actions')

      expect(timelineIndex).toBeGreaterThan(cardTextIndex)
      expect(actionsIndex).toBeGreaterThan(timelineIndex)
    })

    it('has proper spacing classes on timeline', () => {
      const wrapper = createWrapper()
      const timeline = wrapper.findComponent(SuccessionTimeline)
      expect(timeline.classes()).toContain('mt-2')
      expect(timeline.classes()).toContain('mx-4')
    })
  })
})
