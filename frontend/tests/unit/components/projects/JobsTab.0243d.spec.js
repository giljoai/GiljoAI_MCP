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

  describe('Conditional Display: Play Button', () => {
    it('shows play button only when status is waiting', () => {
      const rows = wrapper.findAll('.agents-table tbody tr')

      // Row 0 (working orchestrator): NO play button
      const playBtnsRow0 = rows[0].findAll('[icon="mdi-play"]')
      expect(playBtnsRow0.length).toBe(0)

      // Row 1 (waiting implementor): YES play button
      const playBtnsRow1 = rows[1].findAll('[icon="mdi-play"]')
      expect(playBtnsRow1.length).toBe(1)

      // Row 2 (complete tester): NO play button
      const playBtnsRow2 = rows[2].findAll('[icon="mdi-play"]')
      expect(playBtnsRow2.length).toBe(0)
    })
  })

  describe('Conditional Display: Folder Button', () => {
    it('shows folder button for all agents', () => {
      const rows = wrapper.findAll('.agents-table tbody tr')

      rows.forEach((row) => {
        const folderBtns = row.findAll('[icon="mdi-folder"]')
        expect(folderBtns.length).toBe(1)
      })
    })
  })

  describe('Conditional Display: Info Button', () => {
    it('shows info button for all agents', () => {
      const rows = wrapper.findAll('.agents-table tbody tr')

      rows.forEach((row) => {
        const infoBtns = row.findAll('[icon="mdi-information"]')
        expect(infoBtns.length).toBe(1)
      })
    })
  })

  describe('Conditional Display: Cancel Button', () => {
    it('shows cancel button only when status is working', () => {
      const rows = wrapper.findAll('.agents-table tbody tr')

      // Row 0 (working orchestrator): YES cancel button
      const cancelBtnsRow0 = rows[0].findAll('[icon="mdi-cancel"]')
      expect(cancelBtnsRow0.length).toBe(1)

      // Row 1 (waiting implementor): NO cancel button
      const cancelBtnsRow1 = rows[1].findAll('[icon="mdi-cancel"]')
      expect(cancelBtnsRow1.length).toBe(0)

      // Row 2 (complete tester): NO cancel button
      const cancelBtnsRow2 = rows[2].findAll('[icon="mdi-cancel"]')
      expect(cancelBtnsRow2.length).toBe(0)
    })
  })

  describe('Conditional Display: Hand Over Button', () => {
    it('shows hand over button only for working orchestrators', () => {
      const rows = wrapper.findAll('.agents-table tbody tr')

      // Row 0 (working orchestrator): YES hand over button
      const handoverBtnsRow0 = rows[0].findAll('[icon="mdi-hand-wave"]')
      expect(handoverBtnsRow0.length).toBe(1)

      // Row 1 (waiting implementor): NO hand over button (not orchestrator)
      const handoverBtnsRow1 = rows[1].findAll('[icon="mdi-hand-wave"]')
      expect(handoverBtnsRow1.length).toBe(0)

      // Row 2 (complete tester): NO hand over button (not working)
      const handoverBtnsRow2 = rows[2].findAll('[icon="mdi-hand-wave"]')
      expect(handoverBtnsRow2.length).toBe(0)
    })
  })

  describe('Button Colors', () => {
    it('play and folder buttons have yellow-darken-2 color', () => {
      const row = wrapper.findAll('.agents-table tbody tr')[1] // waiting implementor (has play button)

      const playBtn = row.findAll('[icon="mdi-play"]')[0]
      const folderBtn = row.findAll('[icon="mdi-folder"]')[0]

      expect(playBtn.attributes('color')).toBe('yellow-darken-2')
      expect(folderBtn.attributes('color')).toBe('yellow-darken-2')
    })

    it('info button has white color', () => {
      const row = wrapper.findAll('.agents-table tbody tr')[0]
      const infoBtn = row.findAll('[icon="mdi-information"]')[0]

      expect(infoBtn.attributes('color')).toBe('white')
    })

    it('cancel and hand over buttons have warning color', () => {
      const row = wrapper.findAll('.agents-table tbody tr')[0] // working orchestrator

      const cancelBtn = row.findAll('[icon="mdi-cancel"]')[0]
      const handoverBtn = row.findAll('[icon="mdi-hand-wave"]')[0]

      expect(cancelBtn.attributes('color')).toBe('warning')
      expect(handoverBtn.attributes('color')).toBe('warning')
    })
  })

  describe('Cancel Job Workflow', () => {
    it('opens cancel confirmation dialog when cancel button clicked', async () => {
      const row = wrapper.findAll('.agents-table tbody tr')[0]
      const cancelBtn = row.findAll('[icon="mdi-cancel"]')[0]

      await cancelBtn.trigger('click')

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
      const { api } = await import('@/services/api')
      const mockPost = vi.spyOn(api, 'post').mockResolvedValue({
        data: { success: true, job_id: 'agent-1' }
      })

      wrapper.vm.showCancelDialog = true
      wrapper.vm.selectedAgent = mockAgents[0]
      await wrapper.vm.$nextTick()

      await wrapper.vm.cancelJob()

      expect(mockPost).toHaveBeenCalledWith('/jobs/agent-1/cancel', {
        reason: 'User requested cancellation'
      })

      mockPost.mockRestore()
    })
  })

  describe('Hand Over Workflow', () => {
    it('opens hand over dialog when hand over button clicked', async () => {
      const row = wrapper.findAll('.agents-table tbody tr')[0]
      const handoverBtn = row.findAll('[icon="mdi-hand-wave"]')[0]

      await handoverBtn.trigger('click')

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
    it('displays correct icons for all buttons', () => {
      const row = wrapper.findAll('.agents-table tbody tr')[0] // working orchestrator

      const icons = ['mdi-play', 'mdi-folder', 'mdi-information', 'mdi-cancel', 'mdi-hand-wave']
      const buttons = row.findAll('[size="small"]')

      icons.forEach((icon) => {
        const matchingBtns = buttons.filter((btn) => btn.attributes('icon') === icon)
        expect(matchingBtns.length).toBeGreaterThan(0)
      })
    })
  })

  describe('Agent Status Transitions', () => {
    it('shows play button when agent status changes from working to waiting', async () => {
      const agent = mockAgents[0]
      agent.status = 'waiting'

      await wrapper.vm.$nextTick()

      const rows = wrapper.findAll('.agents-table tbody tr')
      const playBtns = rows[0].findAll('[icon="mdi-play"]')

      expect(playBtns.length).toBe(1)
    })

    it('hides cancel button when agent status changes from working to complete', async () => {
      const agent = mockAgents[0]
      agent.status = 'complete'

      await wrapper.vm.$nextTick()

      const rows = wrapper.findAll('.agents-table tbody tr')
      const cancelBtns = rows[0].findAll('[icon="mdi-cancel"]')

      expect(cancelBtns.length).toBe(0)
    })
  })

  describe('Multiple Working Agents', () => {
    it('correctly displays action buttons for multiple working agents', async () => {
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

      // Both working agents should have cancel buttons
      const cancelBtnsRow0 = rows[0].findAll('[icon="mdi-cancel"]')
      const cancelBtnsRow3 = rows[3].findAll('[icon="mdi-cancel"]')

      expect(cancelBtnsRow0.length).toBe(1)
      expect(cancelBtnsRow3.length).toBe(1)

      // Only orchestrator should have hand over button
      const handoverBtnsRow0 = rows[0].findAll('[icon="mdi-hand-wave"]')
      const handoverBtnsRow3 = rows[3].findAll('[icon="mdi-hand-wave"]')

      expect(handoverBtnsRow0.length).toBe(1)
      expect(handoverBtnsRow3.length).toBe(0)
    })
  })
})
