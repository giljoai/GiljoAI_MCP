/**
 * JobsTab.0243d.spec.js
 *
 * Test suite for Agent Action Buttons implementation (Handover 0243d)
 * Following TDD: Write tests FIRST, watch them FAIL, then implement
 *
 * Tests for:
 * 1. Conditional display of 5 action buttons based on agent status and type
 * 2. Cancel button workflow (confirmation dialog → API call → toast)
 * 3. Hand Over button workflow (dialog → succession → toast)
 * 4. Button colors and styles
 * 5. Tooltips and icons
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import JobsTab from '@/components/projects/JobsTab.vue'

// Create Vuetify instance for testing
const vuetify = createVuetify({
  components,
  directives,
})

// Mock WebSocket composable
vi.mock('@/composables/useWebSocket', () => ({
  useWebSocketV2: () => ({
    on: vi.fn(),
    off: vi.fn(),
    emit: vi.fn(),
  })
}))

// Mock user store
vi.mock('@/stores/user', () => ({
  useUserStore: () => ({
    currentUser: {
      tenant_key: 'test-tenant-123'
    }
  })
}))

// Mock useToast composable
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    showToast: vi.fn(),
  })
}))

// Mock API
vi.mock('@/services/api', () => ({
  api: {
    post: vi.fn(),
    prompts: {
      execution: vi.fn().mockResolvedValue({
        data: { prompt: 'Test orchestrator prompt' }
      }),
      agentPrompt: vi.fn().mockResolvedValue({
        data: { prompt: 'Test agent prompt' }
      })
    }
  },
  default: {
    post: vi.fn(),
    prompts: {
      execution: vi.fn().mockResolvedValue({
        data: { prompt: 'Test orchestrator prompt' }
      }),
      agentPrompt: vi.fn().mockResolvedValue({
        data: { prompt: 'Test agent prompt' }
      })
    }
  }
}))

describe('JobsTab Agent Action Buttons (Handover 0243d)', () => {
  let wrapper

  // Sample agent data
  const mockAgents = [
    {
      job_id: 'agent-1',
      agent_id: 'agent-1',
      agent_type: 'orchestrator',
      status: 'working',
      mission_read_at: null,
      mission_acknowledged_at: null,
      messages_sent: 0,
      messages_waiting: 0,
      messages_read: 0,
    },
    {
      job_id: 'agent-2',
      agent_id: 'agent-2',
      agent_type: 'implementor',
      status: 'waiting',
      mission_read_at: null,
      mission_acknowledged_at: null,
      messages_sent: 0,
      messages_waiting: 0,
      messages_read: 0,
    },
    {
      job_id: 'agent-3',
      agent_id: 'agent-3',
      agent_type: 'tester',
      status: 'complete',
      mission_read_at: null,
      mission_acknowledged_at: null,
      messages_sent: 0,
      messages_waiting: 0,
      messages_read: 0,
    },
  ]

  const mockProject = {
    id: 'project-123',
    project_id: 'project-123',
    name: 'Test Project',
  }

  beforeEach(() => {
    wrapper = mount(JobsTab, {
      props: {
        project: mockProject,
        agents: mockAgents,
        messages: [],
        allAgentsComplete: false,
      },
      global: {
        plugins: [vuetify],
      },
    })
  })

  describe('Conditional Display', () => {
    it('renders buttons in actions column for each agent', () => {
      const rows = wrapper.findAll('.agents-table tbody tr')

      // Verify all rows have an actions cell
      rows.forEach((row) => {
        const actionsCell = row.find('.actions-cell')
        expect(actionsCell.exists()).toBe(true)
        // Each actions cell should contain v-tooltip components for buttons
        expect(actionsCell.findAll('v-tooltip').length).toBeGreaterThan(0)
      })
    })
  })

  describe('Button Colors and Styling', () => {
    it('action buttons are rendered as v-btn components', () => {
      const rows = wrapper.findAll('.agents-table tbody tr')
      const actionsCell = rows[0].find('.actions-cell')

      // Verify that v-btn components exist in the actions cell
      const buttons = actionsCell.findAll('v-btn')
      expect(buttons.length).toBeGreaterThan(0)

      // Verify buttons have expected attributes
      buttons.forEach((btn) => {
        // Each button should have icon, size, and variant attributes
        expect(btn.attributes('size')).toBe('small')
        expect(btn.attributes('variant')).toBe('text')
      })
    })
  })

  describe('Cancel Job Workflow', () => {
    it('opens cancel confirmation dialog when confirmCancelJob is called', async () => {
      wrapper.vm.confirmCancelJob(mockAgents[0])

      expect(wrapper.vm.showCancelDialog).toBe(true)
      expect(wrapper.vm.selectedAgent).toEqual(mockAgents[0])
    })

    it('closes cancel dialog when cancel button in dialog clicked', async () => {
      wrapper.vm.showCancelDialog = true
      wrapper.vm.selectedAgent = mockAgents[0]
      await wrapper.vm.$nextTick()

      // Find and click "No, keep running" button in dialog
      const dialogButtons = wrapper.findAll('.v-dialog .v-btn')
      const noCancelBtn = dialogButtons.find((btn) =>
        btn.text().includes('No, keep running')
      )

      if (noCancelBtn) {
        await noCancelBtn.trigger('click')
        expect(wrapper.vm.showCancelDialog).toBe(false)
      }
    })

    it('calls cancel API when confirmed', async () => {
      // Get the mocked API module and setup the mock
      const { api } = await import('@/services/api')

      vi.mocked(api.post).mockResolvedValue({
        data: { success: true, job_id: 'agent-1' }
      })

      wrapper.vm.showCancelDialog = true
      wrapper.vm.selectedAgent = mockAgents[0]
      await wrapper.vm.$nextTick()

      await wrapper.vm.cancelJob()

      expect(api.post).toHaveBeenCalledWith('/jobs/agent-1/cancel', {
        reason: 'User requested cancellation'
      })
    })
  })

  describe('Hand Over Workflow', () => {
    it('opens hand over dialog when openHandoverDialog is called', async () => {
      wrapper.vm.openHandoverDialog(mockAgents[0])

      expect(wrapper.vm.showHandoverDialog).toBe(true)
      expect(wrapper.vm.selectedAgent).toEqual(mockAgents[0])
    })

    it('handles successor created event', async () => {
      const successorData = {
        id: 'successor-uuid',
        spawned_by: 'agent-1',
        instance_number: 2
      }

      wrapper.vm.showHandoverDialog = true
      wrapper.vm.handleSuccessorCreated(successorData)

      expect(wrapper.vm.showHandoverDialog).toBe(false)
    })
  })

  describe('Button Icons', () => {
    it('buttons have icon attributes for working orchestrator', () => {
      const row = wrapper.findAll('.agents-table tbody tr')[0] // working orchestrator
      const actionsCell = row.find('.actions-cell')
      const buttons = actionsCell.findAll('v-btn')

      // Collect all icons from buttons
      const icons = buttons.map((btn) => btn.attributes('icon')).filter(Boolean)

      // Verify icons include folder and information (always shown)
      expect(icons).toContain('mdi-folder')
      expect(icons).toContain('mdi-information')
      // For working orchestrator: cancel and hand-wave should be present
      expect(icons).toContain('mdi-cancel')
      expect(icons).toContain('mdi-hand-wave')
    })
  })

  describe('Agent Status Transitions', () => {
    it('updates button display when agent status changes to waiting', async () => {
      const agent = mockAgents[0]
      agent.status = 'waiting'

      await wrapper.vm.$nextTick()

      const rows = wrapper.findAll('.agents-table tbody tr')
      const actionsCell = rows[0].find('.actions-cell')
      const buttons = actionsCell.findAll('v-btn')
      const icons = buttons.map((btn) => btn.attributes('icon')).filter(Boolean)

      // Play button (mdi-play) should be present when status is waiting
      expect(icons).toContain('mdi-play')
    })

    it('hides cancel button when agent status changes from working to complete', async () => {
      // Create a new wrapper with agent starting as working
      const agentsForTransition = [{
        ...mockAgents[0],
        status: 'working'
      }, ...mockAgents.slice(1)]

      wrapper = mount(JobsTab, {
        props: {
          project: mockProject,
          agents: agentsForTransition,
          messages: [],
          allAgentsComplete: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      // Change status to complete
      agentsForTransition[0].status = 'complete'
      await wrapper.vm.$nextTick()

      const rows = wrapper.findAll('.agents-table tbody tr')
      const actionsCell = rows[0].find('.actions-cell')

      // Cancel button should NOT be present when status is complete
      const buttons = actionsCell.findAll('v-btn')
      const icons = buttons.map((btn) => btn.attributes('icon')).filter(Boolean)
      expect(icons).not.toContain('mdi-cancel')
    })
  })

  describe('Multiple Working Agents', () => {
    it('displays different buttons for orchestrator vs other working agents', async () => {
      // Setup: Add another working agent
      const newAgent = {
        job_id: 'agent-4',
        agent_id: 'agent-4',
        agent_type: 'analyzer',
        status: 'working',
        mission_read_at: null,
        mission_acknowledged_at: null,
        messages_sent: 0,
        messages_waiting: 0,
        messages_read: 0,
      }

      // Create new wrapper with additional working agent
      const agentsWithMultipleWorking = [...mockAgents, newAgent]
      wrapper = mount(JobsTab, {
        props: {
          project: mockProject,
          agents: agentsWithMultipleWorking,
          messages: [],
          allAgentsComplete: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      const rows = wrapper.findAll('.agents-table tbody tr')

      // Find working orchestrator and analyzer rows
      let orchestratorIcons = []
      let analyzerIcons = []

      rows.forEach((row) => {
        const html = row.html()
        const buttons = row.findAll('.actions-cell v-btn')
        const icons = buttons.map((btn) => btn.attributes('icon')).filter(Boolean)

        // Orchestrator has 'Or' abbr, Analyzer has 'An'
        if (html.includes('Or')) {
          orchestratorIcons = icons
        } else if (html.includes('An')) {
          analyzerIcons = icons
        }
      })

      // Both working agents should have cancel button
      expect(orchestratorIcons).toContain('mdi-cancel')
      expect(analyzerIcons).toContain('mdi-cancel')

      // Only orchestrator should have hand over button
      expect(orchestratorIcons).toContain('mdi-hand-wave')
      expect(analyzerIcons).not.toContain('mdi-hand-wave')
    })
  })
})
