import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import SuccessionTimeline from '../SuccessionTimeline.vue'
import api from '@/services/api'

// Mock API
vi.mock('@/services/api', () => ({
  default: {
    agentJobs: {
      list: vi.fn(),
    },
  },
}))

// Mock date-fns
vi.mock('date-fns', () => ({
  format: vi.fn((date, formatStr) => '2025-01-15 14:30'),
}))

describe.skip('SuccessionTimeline (DEPRECATED - Handover 0461d)', () => {
  let vuetify

  beforeEach(() => {
    vuetify = createVuetify()
    vi.clearAllMocks()
  })

  const mockInstances = [
    {
      id: 'job-1',
      agent_display_name: 'orchestrator',
      agent_name: 'Orchestrator',
      instance_number: 1,
      status: 'complete',
      created_at: '2025-01-15T14:00:00Z',
      context_used: 150000,
      context_budget: 200000,
      succession_reason: 'context_limit',
      handover_summary: 'Completed phase 1',
      handover_to: 'job-2',
    },
    {
      id: 'job-2',
      agent_display_name: 'orchestrator',
      agent_name: 'Orchestrator',
      instance_number: 2,
      status: 'working',
      created_at: '2025-01-15T15:00:00Z',
      context_used: 50000,
      context_budget: 200000,
      succession_reason: null,
      handover_summary: null,
      handover_to: null,
    },
  ]

  const createWrapper = (props = {}) => {
    return mount(SuccessionTimeline, {
      props: {
        projectId: 'proj-123',
        ...props,
      },
      global: {
        plugins: [vuetify],
        stubs: {
          teleport: true,
        },
      },
    })
  }

  describe('Rendering', () => {
    it('renders component with title', () => {
      api.agentJobs.list.mockResolvedValue({ data: [] })
      const wrapper = createWrapper()
      expect(wrapper.text()).toContain('Orchestrator Succession Timeline')
    })

    it('shows info alert when no instances exist', async () => {
      api.agentJobs.list.mockResolvedValue({ data: [] })
      const wrapper = createWrapper()
      await flushPromises()

      expect(wrapper.text()).toContain('No succession history yet')
    })

    it('displays timeline items for instances', async () => {
      api.agentJobs.list.mockResolvedValue({ data: mockInstances })
      const wrapper = createWrapper()
      await flushPromises()

      const timelineItems = wrapper.findAllComponents({ name: 'VTimelineItem' })
      expect(timelineItems).toHaveLength(2)
    })

    it('displays instance numbers correctly', async () => {
      api.agentJobs.list.mockResolvedValue({ data: mockInstances })
      const wrapper = createWrapper()
      await flushPromises()

      expect(wrapper.text()).toContain('Instance 1')
      expect(wrapper.text()).toContain('Instance 2')
    })
  })

  describe('Data Fetching', () => {
    it('fetches succession history on mount', async () => {
      api.agentJobs.list.mockResolvedValue({ data: mockInstances })
      const wrapper = createWrapper({ projectId: 'proj-123' })
      await flushPromises()

      expect(api.agentJobs.list).toHaveBeenCalledWith('proj-123')
    })

    it('filters only orchestrator instances', async () => {
      const mixedJobs = [
        ...mockInstances,
        {
          id: 'job-3',
          agent_display_name: 'specialist',
          instance_number: 1,
        },
      ]
      api.agentJobs.list.mockResolvedValue({ data: mixedJobs })
      const wrapper = createWrapper()
      await flushPromises()

      expect(wrapper.vm.instances).toHaveLength(2)
      expect(wrapper.vm.instances.every((i) => i.agent_display_name === 'orchestrator')).toBe(true)
    })

    it('sorts instances by instance_number', async () => {
      const unsortedInstances = [mockInstances[1], mockInstances[0]]
      api.agentJobs.list.mockResolvedValue({ data: unsortedInstances })
      const wrapper = createWrapper()
      await flushPromises()

      expect(wrapper.vm.instances[0].instance_number).toBe(1)
      expect(wrapper.vm.instances[1].instance_number).toBe(2)
    })

    it('handles API errors gracefully', async () => {
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
      api.agentJobs.list.mockRejectedValue(new Error('API Error'))
      const wrapper = createWrapper()
      await flushPromises()

      expect(wrapper.vm.instances).toHaveLength(0)
      expect(consoleError).toHaveBeenCalled()
      consoleError.mockRestore()
    })
  })

  describe('Context Usage Display', () => {
    it('displays context usage progress bar', async () => {
      api.agentJobs.list.mockResolvedValue({ data: [mockInstances[0]] })
      const wrapper = createWrapper()
      await flushPromises()

      const progressBar = wrapper.findComponent({ name: 'VProgressLinear' })
      expect(progressBar.exists()).toBe(true)
    })

    it('calculates context percentage correctly', async () => {
      api.agentJobs.list.mockResolvedValue({ data: [mockInstances[0]] })
      const wrapper = createWrapper()
      await flushPromises()

      const percentage = wrapper.vm.getContextPercentage(mockInstances[0])
      expect(percentage).toBe(75) // 150000/200000 * 100
    })

    it('shows correct context color for usage levels', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      // Green for < 70%
      expect(wrapper.vm.getContextColor({ context_used: 50000, context_budget: 200000 })).toBe(
        'success',
      )

      // Warning for 70-89%
      expect(wrapper.vm.getContextColor({ context_used: 150000, context_budget: 200000 })).toBe(
        'warning',
      )

      // Error for >= 90%
      expect(wrapper.vm.getContextColor({ context_used: 190000, context_budget: 200000 })).toBe(
        'error',
      )
    })

    it('displays token counts with formatting', async () => {
      api.agentJobs.list.mockResolvedValue({ data: [mockInstances[0]] })
      const wrapper = createWrapper()
      await flushPromises()

      expect(wrapper.text()).toContain('150,000')
      expect(wrapper.text()).toContain('200,000')
    })
  })

  describe('Status Display', () => {
    it('shows correct status chip color', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      expect(wrapper.vm.getStatusColor({ status: 'working' })).toBe('primary')
      expect(wrapper.vm.getStatusColor({ status: 'complete' })).toBe('success')
      expect(wrapper.vm.getStatusColor({ status: 'failed' })).toBe('error')
      expect(wrapper.vm.getStatusColor({ status: 'waiting' })).toBe('grey')
    })

    it('displays succession reason chip when present', async () => {
      api.agentJobs.list.mockResolvedValue({ data: [mockInstances[0]] })
      const wrapper = createWrapper()
      await flushPromises()

      expect(wrapper.text()).toContain('Succession: context_limit')
    })

    it('hides succession reason when not present', async () => {
      api.agentJobs.list.mockResolvedValue({ data: [mockInstances[1]] })
      const wrapper = createWrapper()
      await flushPromises()

      const chips = wrapper.findAllComponents({ name: 'VChip' })
      const successionChip = chips.find((c) => c.text().includes('Succession:'))
      expect(successionChip).toBeUndefined()
    })
  })

  describe('Handover Summary', () => {
    it('displays handover summary in expansion panel', async () => {
      api.agentJobs.list.mockResolvedValue({ data: [mockInstances[0]] })
      const wrapper = createWrapper()
      await flushPromises()

      const expansionPanel = wrapper.findComponent({ name: 'VExpansionPanel' })
      expect(expansionPanel.exists()).toBe(true)
      expect(wrapper.text()).toContain('Handover Summary')
    })

    it('hides handover summary when not present', async () => {
      api.agentJobs.list.mockResolvedValue({ data: [mockInstances[1]] })
      const wrapper = createWrapper()
      await flushPromises()

      const expansionPanels = wrapper.findAllComponents({ name: 'VExpansionPanels' })
      expect(expansionPanels).toHaveLength(0)
    })
  })

  describe('Successor Navigation', () => {
    it('shows view successor button when handover_to exists', async () => {
      api.agentJobs.list.mockResolvedValue({ data: [mockInstances[0]] })
      const wrapper = createWrapper()
      await flushPromises()

      expect(wrapper.text()).toContain('View Successor')
    })

    it('hides view successor button when handover_to is null', async () => {
      api.agentJobs.list.mockResolvedValue({ data: [mockInstances[1]] })
      const wrapper = createWrapper()
      await flushPromises()

      const actions = wrapper.findAllComponents({ name: 'VCardActions' })
      expect(actions).toHaveLength(0)
    })

    it('scrolls to instance when view successor is clicked', async () => {
      const scrollIntoView = vi.fn()
      const querySelector = vi.spyOn(document, 'querySelector').mockReturnValue({
        scrollIntoView,
      })

      api.agentJobs.list.mockResolvedValue({ data: [mockInstances[0]] })
      const wrapper = createWrapper()
      await flushPromises()

      wrapper.vm.scrollToInstance('job-2')
      expect(scrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth' })

      querySelector.mockRestore()
    })
  })

  describe('Timeline Icons', () => {
    it('shows account-circle icon for current (last) instance', async () => {
      api.agentJobs.list.mockResolvedValue({ data: mockInstances })
      const wrapper = createWrapper()
      await flushPromises()

      const timelineItems = wrapper.findAllComponents({ name: 'VTimelineItem' })
      expect(timelineItems[1].props('icon')).toBe('mdi-account-circle')
    })

    it('shows check icon for previous instances', async () => {
      api.agentJobs.list.mockResolvedValue({ data: mockInstances })
      const wrapper = createWrapper()
      await flushPromises()

      const timelineItems = wrapper.findAllComponents({ name: 'VTimelineItem' })
      expect(timelineItems[0].props('icon')).toBe('mdi-check')
    })
  })

  describe('Helper Functions', () => {
    it('formatNumber adds thousand separators', () => {
      const wrapper = createWrapper()
      expect(wrapper.vm.formatNumber(150000)).toBe('150,000')
      expect(wrapper.vm.formatNumber(1500)).toBe('1,500')
      expect(wrapper.vm.formatNumber(0)).toBe(0)
      expect(wrapper.vm.formatNumber(null)).toBe(0)
    })

    it('formatDate uses date-fns format', () => {
      const wrapper = createWrapper()
      const result = wrapper.vm.formatDate('2025-01-15T14:30:00Z')
      expect(result).toBe('2025-01-15 14:30')
    })
  })

  describe('Scrollable Content', () => {
    it('has max-height and scrollable styling', () => {
      api.agentJobs.list.mockResolvedValue({ data: [] })
      const wrapper = createWrapper()

      const card = wrapper.findComponent({ name: 'VCard' })
      expect(card.classes()).toContain('succession-timeline')
    })
  })
})
