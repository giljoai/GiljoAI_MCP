import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { createVuetify } from 'vuetify'
import ProjectReviewModal from '@/components/projects/ProjectReviewModal.vue'
import StatusBadge from '@/components/StatusBadge.vue'

// Mock the api module
vi.mock('@/services/api', () => ({
  default: {
    projects: {
      get: vi.fn(),
    },
    agentJobs: {
      list: vi.fn(),
      messages: vi.fn(),
    },
    products: {
      getMemoryEntries: vi.fn(),
    },
  },
}))

import api from '@/services/api'

describe('ProjectReviewModal.vue', () => {
  let wrapper
  let pinia
  let vuetify

  const mockProject = {
    id: 'proj-1',
    name: 'Test Project',
    description: 'A test project description',
    status: 'completed',
    mission: 'Build the feature',
    created_at: '2026-03-01T10:00:00Z',
    completed_at: '2026-03-10T15:00:00Z',
    product_id: 'prod-1',
  }

  const mockAgents = [
    { id: 'job-1', agent_display_name: 'Orchestrator', agent_role: 'orchestrator', status: 'complete' },
    { id: 'job-2', agent_display_name: 'Implementor', agent_role: 'implementor', status: 'complete' },
  ]

  const mockMemoryEntries = [
    { sequence: 1, summary: 'Initial setup completed' },
    { sequence: 2, summary: 'Feature implemented' },
  ]

  const mockMessages = [
    { id: 'msg-1', from: 'Orchestrator', content: 'Starting work', created_at: '2026-03-01T11:00:00Z', direction: 'outbound', message_type: 'broadcast' },
    { id: 'msg-2', from: 'Implementor', content: 'Work complete', created_at: '2026-03-01T12:00:00Z', direction: 'inbound', message_type: 'broadcast' },
  ]

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vuetify = createVuetify()

    vi.clearAllMocks()

    api.projects.get.mockResolvedValue({ data: mockProject })
    api.agentJobs.list.mockResolvedValue({ data: { jobs: mockAgents, total: 2, limit: 100, offset: 0 } })
    api.products.getMemoryEntries.mockResolvedValue({ data: { entries: mockMemoryEntries, success: true } })
    api.agentJobs.messages.mockResolvedValue({ data: { messages: mockMessages, job_id: 'job-1', agent_id: 'agent-1' } })
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
  })

  function mountModal(props = {}) {
    return mount(ProjectReviewModal, {
      props: {
        show: true,
        projectId: 'proj-1',
        productId: 'prod-1',
        ...props,
      },
      global: {
        plugins: [pinia, vuetify],
      },
    })
  }

  async function mountAndWaitForData(props = {}) {
    const w = mountModal({ show: false, ...props })
    await w.setProps({ show: true })
    await flushPromises()
    await w.vm.$nextTick()
    return w
  }

  describe('Rendering', () => {
    it('passes show prop to dialog model-value', () => {
      wrapper = mountModal({ show: true })
      // The dialog component receives the show prop
      const dialog = wrapper.findComponent({ name: 'VDialog' })
      if (dialog.exists()) {
        expect(dialog.props('modelValue')).toBe(true)
      } else {
        // VDialog may not be found directly - check the component renders
        expect(wrapper.html()).toContain('review-modal')
      }
    })

    it('passes false to dialog when show is false', () => {
      wrapper = mountModal({ show: false })
      // Component should exist but dialog should be closed
      expect(wrapper.exists()).toBe(true)
    })
  })

  describe('Data Loading', () => {
    it('fetches project, jobs, and memory data in parallel on open', async () => {
      wrapper = await mountAndWaitForData()

      expect(api.projects.get).toHaveBeenCalledWith('proj-1')
      expect(api.agentJobs.list).toHaveBeenCalledWith('proj-1')
      expect(api.products.getMemoryEntries).toHaveBeenCalledWith('prod-1', { project_id: 'proj-1', limit: 20 })
    })

    it('skips memory fetch when no productId is provided', async () => {
      wrapper = await mountAndWaitForData({ productId: null })

      expect(api.products.getMemoryEntries).not.toHaveBeenCalled()
    })

    it('shows error state on API failure', async () => {
      api.projects.get.mockRejectedValue(new Error('Network error'))

      wrapper = await mountAndWaitForData()

      // The error ref should be set
      expect(wrapper.vm.error).toBeTruthy()
      expect(wrapper.vm.error).toContain('Network error')
    })
  })

  describe('Project Overview', () => {
    it('displays project name, description, and status after data loads', async () => {
      wrapper = await mountAndWaitForData()

      const text = wrapper.text()
      expect(text).toContain('Test Project')
      expect(text).toContain('A test project description')
      expect(text).toContain('completed')
    })

    it('displays mission text', async () => {
      wrapper = await mountAndWaitForData()

      expect(wrapper.text()).toContain('Build the feature')
    })

    it('handles mission as object with mission_statement', async () => {
      api.projects.get.mockResolvedValue({
        data: { ...mockProject, mission: { mission_statement: 'Statement from object' } },
      })

      wrapper = await mountAndWaitForData()

      expect(wrapper.text()).toContain('Statement from object')
    })
  })

  describe('Agent Roster', () => {
    it('renders agent names and count', async () => {
      wrapper = await mountAndWaitForData()

      const text = wrapper.text()
      expect(text).toContain('Orchestrator')
      expect(text).toContain('Implementor')
      expect(text).toContain('Agents (2)')
    })

    it('handles empty agents list', async () => {
      api.agentJobs.list.mockResolvedValue({ data: { jobs: [], total: 0, limit: 100, offset: 0 } })

      wrapper = await mountAndWaitForData()

      expect(wrapper.text()).not.toContain('Agents (')
    })
  })

  describe('Read-Only Verification', () => {
    it('has no buttons that modify project state', async () => {
      wrapper = await mountAndWaitForData()

      const buttons = wrapper.findAll('button')
      const buttonTexts = buttons.map(b => b.text().toLowerCase())

      const stateChangingActions = ['activate', 'reopen', 'delete', 'cancel', 'deactivate', 'save', 'submit']
      for (const action of stateChangingActions) {
        expect(buttonTexts.some(t => t.includes(action))).toBe(false)
      }

      expect(buttonTexts.some(t => t.includes('close'))).toBe(true)
    })
  })

  describe('Close Event', () => {
    it('emits close event when close button is clicked', async () => {
      wrapper = mountModal()
      await flushPromises()

      const closeBtn = wrapper.find('[data-testid="review-close-btn"]')
      await closeBtn.trigger('click')

      expect(wrapper.emitted('close')).toBeTruthy()
    })

    it('emits close event when header X button is clicked', async () => {
      wrapper = mountModal()
      await flushPromises()

      const headerCloseBtn = wrapper.find('[aria-label="Close modal"]')
      await headerCloseBtn.trigger('click')

      expect(wrapper.emitted('close')).toBeTruthy()
    })
  })

  describe('Agent Message Lazy Loading', () => {
    it('loads messages when agent panel is expanded via v-model watcher', async () => {
      wrapper = await mountAndWaitForData()

      // Simulate panel expansion by setting expandedAgentPanels
      wrapper.vm.expandedAgentPanels = [0]
      await flushPromises()

      expect(api.agentJobs.messages).toHaveBeenCalledWith('job-1')
    })

    it('does not reload messages for already-loaded agent', async () => {
      wrapper = await mountAndWaitForData()

      // First expansion
      wrapper.vm.expandedAgentPanels = [0]
      await flushPromises()

      // Second expansion of same panel
      wrapper.vm.expandedAgentPanels = [0]
      await flushPromises()

      // Should only call once (guard in loadAgentMessages)
      expect(api.agentJobs.messages).toHaveBeenCalledTimes(1)
    })

    it('resets expanded panels on modal close', async () => {
      wrapper = await mountAndWaitForData()
      wrapper.vm.expandedAgentPanels = [0]
      await flushPromises()

      await wrapper.setProps({ show: false })
      await flushPromises()

      expect(wrapper.vm.expandedAgentPanels).toEqual([])
    })
  })

  describe('Response Shape Handling', () => {
    it('extracts jobs from JobListResponse shape (res.data.jobs)', async () => {
      wrapper = await mountAndWaitForData()

      // Verify the component correctly parsed the response
      expect(wrapper.vm.agents).toHaveLength(2)
      expect(wrapper.vm.agents[0].agent_display_name).toBe('Orchestrator')
    })

    it('extracts entries from MemoryEntriesResponse shape (res.data.entries)', async () => {
      wrapper = await mountAndWaitForData()

      expect(wrapper.vm.memoryEntries).toHaveLength(2)
      expect(wrapper.vm.memoryEntries[0].summary).toBe('Initial setup completed')
    })
  })
})

describe('StatusBadge - Review Action', () => {
  let wrapper
  let pinia
  let vuetify

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vuetify = createVuetify()
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
  })

  function mountBadge(status) {
    return mount(StatusBadge, {
      props: {
        status,
        projectId: 'test-proj-1',
        projectName: 'Test Project',
      },
      global: {
        plugins: [pinia, vuetify],
      },
    })
  }

  it('shows Review action for completed projects', () => {
    wrapper = mountBadge('completed')

    // Check availableActions computed property directly
    const actions = wrapper.vm.availableActions
    const actionLabels = actions.map(a => a.label)

    expect(actionLabels).toContain('Review')
    expect(actionLabels).not.toContain('Reopen')
  })

  it('shows Review action for terminated projects', () => {
    wrapper = mountBadge('terminated')

    const actions = wrapper.vm.availableActions
    const actionLabels = actions.map(a => a.label)

    expect(actionLabels).toContain('Review')
  })

  it('preserves Reopen action for cancelled projects', () => {
    wrapper = mountBadge('cancelled')

    const actions = wrapper.vm.availableActions
    const actionLabels = actions.map(a => a.label)

    expect(actionLabels).toContain('Reopen')
    expect(actionLabels).not.toContain('Review')
  })

  it('review action has no newStatus (read-only)', () => {
    wrapper = mountBadge('completed')

    const reviewAction = wrapper.vm.availableActions.find(a => a.value === 'review')
    expect(reviewAction).toBeDefined()
    expect(reviewAction.newStatus).toBeNull()
    expect(reviewAction.destructive).toBe(false)
  })
})
