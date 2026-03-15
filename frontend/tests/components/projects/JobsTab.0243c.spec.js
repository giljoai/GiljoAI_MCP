/**
 * JobsTab Dynamic Status Tests - Handover 0243c
 * CRITICAL BUG FIX: Status must display from agent.status field, not hardcoded "Waiting."
 *
 * TDD Workflow:
 * Phase 1 (RED): Write failing tests that validate dynamic status display
 * Phase 2 (GREEN): Implement functionality to make tests pass
 * Phase 3 (REFACTOR): Polish and optimize code
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import JobsTab from './JobsTab.vue'
import { useUserStore } from '@/stores/user'
import { useWebSocketV2 } from '@/composables/useWebSocket'

// Mock WebSocket V2 composable
vi.mock('@/composables/useWebSocket', () => ({
  useWebSocketV2: vi.fn(),
  useWebSocket: vi.fn(),
}))

// Mock API
vi.mock('@/services/api', () => ({
  default: {
    prompts: {
      execution: vi.fn(),
      agentPrompt: vi.fn(),
    },
  },
}))

// Mock Toast composable
vi.mock('@/composables/useToast', () => ({
  useToast: vi.fn(() => ({
    showToast: vi.fn(),
  })),
}))

describe('JobsTab Dynamic Status (Handover 0243c - CRITICAL)', () => {
  let wrapper
  let pinia
  let userStore
  let mockOn, mockOff
  let statusUpdateHandlers = {}

  const mockAgents = [
    {
      job_id: 'agent-1',
      agent_display_name: 'orchestrator',
      agent_name: 'Orchestrator',
      status: 'working',
      tenant_key: 'test-tenant',
      mission_read_at: '2025-11-23T10:00:00Z',
      mission_acknowledged_at: '2025-11-23T10:00:00Z',
      messages_sent: 5,
      messages_waiting: 2,
      messages_read: 4,
    },
    {
      job_id: 'agent-2',
      agent_display_name: 'implementor',
      agent_name: 'Implementor',
      status: 'waiting',
      tenant_key: 'test-tenant',
      mission_read_at: null,
      mission_acknowledged_at: null,
      messages_sent: 0,
      messages_waiting: 0,
      messages_read: 0,
    },
    {
      job_id: 'agent-3',
      agent_display_name: 'tester',
      agent_name: 'Tester',
      status: 'complete',
      tenant_key: 'test-tenant',
      mission_read_at: '2025-11-23T10:00:00Z',
      mission_acknowledged_at: '2025-11-23T10:00:00Z',
      messages_sent: 3,
      messages_waiting: 0,
      messages_read: 3,
    },
    {
      job_id: 'agent-4',
      agent_display_name: 'analyzer',
      agent_name: 'Analyzer',
      status: 'failed',
      tenant_key: 'test-tenant',
      mission_read_at: '2025-11-23T10:00:00Z',
      mission_acknowledged_at: null,
      messages_sent: 1,
      messages_waiting: 0,
      messages_read: 0,
    },
    {
      job_id: 'agent-5',
      agent_display_name: 'reviewer',
      agent_name: 'Reviewer',
      status: 'cancelled',
      tenant_key: 'test-tenant',
      mission_read_at: null,
      mission_acknowledged_at: null,
      messages_sent: 0,
      messages_waiting: 0,
      messages_read: 0,
    },
  ]

  beforeEach(() => {
    // Setup Pinia store
    pinia = createPinia()
    setActivePinia(pinia)

    // Setup user store with tenant key
    userStore = useUserStore()
    userStore.currentUser = {
      id: 'user-123',
      username: 'testuser',
      tenant_key: 'test-tenant',
      role: 'user',
    }

    // Setup WebSocket mock
    statusUpdateHandlers = {}
    mockOn = vi.fn((event, handler) => {
      if (!statusUpdateHandlers[event]) {
        statusUpdateHandlers[event] = []
      }
      statusUpdateHandlers[event].push(handler)
      return () => {
        const index = statusUpdateHandlers[event].indexOf(handler)
        if (index > -1) {
          statusUpdateHandlers[event].splice(index, 1)
        }
      }
    })

    mockOff = vi.fn((event, handler) => {
      if (statusUpdateHandlers[event]) {
        const index = statusUpdateHandlers[event].indexOf(handler)
        if (index > -1) {
          statusUpdateHandlers[event].splice(index, 1)
        }
      }
    })

    vi.mocked(useWebSocketV2).mockReturnValue({
      isConnected: { value: true },
      on: mockOn,
      off: mockOff,
      send: vi.fn(),
      subscribe: vi.fn(),
      unsubscribe: vi.fn(),
    })

    // Mount component
    wrapper = mount(JobsTab, {
      props: {
        project: { id: 'project-uuid', name: 'Test Project' },
        agents: [...mockAgents],
        messages: [],
        allAgentsComplete: false,
      },
      global: {
        plugins: [pinia],
        stubs: {
          'v-avatar': true,
          'v-icon': true,
          'v-btn': true,
          'v-chip': true,
        },
      },
    })
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
    vi.clearAllMocks()
  })

  // ========================================
  // CRITICAL: RED PHASE TESTS (should fail)
  // ========================================

  describe('Status Display - Dynamic Binding', () => {
    it('displays "Working..." for working agents (yellow italic)', () => {
      const rows = wrapper.findAll('.agents-table tbody tr')
      // Find the working agent (agent-1) in the sorted list
      // Agents are sorted: failed (1) → waiting (3) → working (4) → complete (5)
      const workingRow = rows.find((row) => {
        const cell = row.find('.status-cell')
        return cell.text() === 'Working...'
      })

      expect(workingRow).toBeTruthy()
      const statusCell = workingRow.find('.status-cell')
      expect(statusCell.text()).toBe('Working...')
      expect(statusCell.element.style.color).toBe('rgb(255, 215, 0)') // #ffd700
      expect(statusCell.element.style.fontStyle).toBe('italic')
    })

    it('displays "Waiting." for waiting agents (yellow italic)', () => {
      const rows = wrapper.findAll('.agents-table tbody tr')
      const waitingRow = rows.find((row) => {
        const cell = row.find('.status-cell')
        return cell.text() === 'Waiting.'
      })

      expect(waitingRow).toBeTruthy()
      const statusCell = waitingRow.find('.status-cell')
      expect(statusCell.text()).toBe('Waiting.')
      expect(statusCell.element.style.color).toBe('rgb(255, 215, 0)')
      expect(statusCell.element.style.fontStyle).toBe('italic')
    })

    it('displays "Complete" for completed agents (green, NOT italic)', () => {
      const rows = wrapper.findAll('.agents-table tbody tr')
      const completeRow = rows.find((row) => {
        const cell = row.find('.status-cell')
        return cell.text() === 'Complete'
      })

      expect(completeRow).toBeTruthy()
      const statusCell = completeRow.find('.status-cell')
      expect(statusCell.text()).toBe('Complete')
      expect(statusCell.element.style.color).toBe('rgb(103, 189, 109)') // #67bd6d
      expect(statusCell.element.style.fontStyle).toBe('normal')
    })

    it('displays "Failed" for failed agents (red, NOT italic)', () => {
      const rows = wrapper.findAll('.agents-table tbody tr')
      const failedRow = rows.find((row) => {
        const cell = row.find('.status-cell')
        return cell.text() === 'Failed'
      })

      expect(failedRow).toBeTruthy()
      const statusCell = failedRow.find('.status-cell')
      expect(statusCell.text()).toBe('Failed')
      expect(statusCell.element.style.color).toBe('rgb(229, 57, 53)') // #e53935
      expect(statusCell.element.style.fontStyle).toBe('normal')
    })

    it('displays "Cancelled" for cancelled agents (orange, NOT italic)', () => {
      const rows = wrapper.findAll('.agents-table tbody tr')
      const cancelledRow = rows.find((row) => {
        const cell = row.find('.status-cell')
        return cell.text() === 'Cancelled'
      })

      expect(cancelledRow).toBeTruthy()
      const statusCell = cancelledRow.find('.status-cell')
      expect(statusCell.text()).toBe('Cancelled')
      expect(statusCell.element.style.color).toBe('rgb(255, 152, 0)') // #ff9800
      expect(statusCell.element.style.fontStyle).toBe('normal')
    })

    it('displays "Unknown" for invalid status values (graceful degradation)', () => {
      const invalidAgent = {
        job_id: 'agent-6',
        agent_display_name: 'invalid',
        agent_name: 'Invalid',
        status: 'invalid-status',
        tenant_key: 'test-tenant',
      }

      wrapper = mount(JobsTab, {
        props: {
          project: { id: 'project-uuid', name: 'Test' },
          agents: [invalidAgent],
          messages: [],
          allAgentsComplete: false,
        },
        global: {
          plugins: [pinia],
          stubs: {
            'v-avatar': true,
            'v-icon': true,
            'v-btn': true,
            'v-chip': true,
          },
        },
      })

      const statusCell = wrapper.find('.status-cell')
      expect(statusCell.text()).toBe('Unknown')
      expect(statusCell.element.style.color).toBe('rgb(102, 102, 102)') // #666
    })
  })

  describe('WebSocket Event Handling', () => {
    it('registers WebSocket listener on mount', () => {
      expect(mockOn).toHaveBeenCalledWith('agent:status_changed', expect.any(Function))
    })

    it('removes WebSocket listener on unmount', () => {
      wrapper.unmount()
      expect(mockOff).toHaveBeenCalledWith('agent:status_changed', expect.any(Function))
    })

    it('updates status when WebSocket event received', async () => {
      // Get the handler function passed to 'on'
      const handlers = mockOn.mock.calls.find((call) => call[0] === 'agent:status_changed')
      if (!handlers) throw new Error('No status_changed handler registered')

      const handler = handlers[1]

      // Initial state: agent-1 is "working"
      let rows = wrapper.findAll('.agents-table tbody tr')
      const workingRow = rows.find((row) => row.find('.status-cell').text() === 'Working...')
      expect(workingRow).toBeTruthy()

      // Simulate WebSocket event - agent-1 changes from "working" to "complete"
      handler({
        job_id: 'agent-1',
        tenant_key: 'test-tenant',
        status: 'complete',
        timestamp: new Date().toISOString(),
      })

      await wrapper.vm.$nextTick()

      // Verify UI updated - now complete row should exist
      rows = wrapper.findAll('.agents-table tbody tr')
      const completeRow = rows.find((row) => row.find('.status-cell').text() === 'Complete')
      expect(completeRow).toBeTruthy()
      const statusCell = completeRow.find('.status-cell')
      expect(statusCell.element.style.color).toBe('rgb(103, 189, 109)')
      expect(statusCell.element.style.fontStyle).toBe('normal')
    })

    it('rejects status updates from different tenant (multi-tenant isolation)', async () => {
      const handlers = mockOn.mock.calls.find((call) => call[0] === 'agent:status_changed')
      if (!handlers) throw new Error('No status_changed handler registered')

      const handler = handlers[1]
      const agent1 = wrapper.props('agents').find((a) => a.job_id === 'agent-1')
      const originalStatus = agent1.status

      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

      // Simulate WebSocket event from DIFFERENT tenant
      handler({
        job_id: 'agent-1',
        tenant_key: 'other-tenant', // Different tenant!
        status: 'complete',
        timestamp: new Date().toISOString(),
      })

      await wrapper.vm.$nextTick()

      // Verify warning logged (security check)
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        expect.stringContaining('tenant mismatch'),
        expect.any(Object)
      )

      // Verify agent-1 still has original status (not updated)
      expect(agent1.status).toBe(originalStatus) // Still original status, NOT 'complete'

      consoleWarnSpy.mockRestore()
    })

    it('handles status update for non-existent agent gracefully', async () => {
      const handlers = mockOn.mock.calls.find((call) => call[0] === 'agent:status_changed')
      if (!handlers) throw new Error('No status_changed handler registered')

      const handler = handlers[1]
      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

      // Send update for agent that doesn't exist
      handler({
        job_id: 'non-existent-agent',
        tenant_key: 'test-tenant',
        status: 'complete',
        timestamp: new Date().toISOString(),
      })

      await wrapper.vm.$nextTick()

      // Verify warning logged
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        expect.stringContaining('Agent not found for status update')
      )

      // Verify no errors thrown
      expect(wrapper.html()).toBeTruthy()

      consoleWarnSpy.mockRestore()
    })

    it('updates multiple agents sequentially via WebSocket', async () => {
      const handlers = mockOn.mock.calls.find((call) => call[0] === 'agent:status_changed')
      if (!handlers) throw new Error('No status_changed handler registered')

      const handler = handlers[1]
      const agents = wrapper.props('agents')

      // Update agent-2: waiting → working
      handler({
        job_id: 'agent-2',
        tenant_key: 'test-tenant',
        status: 'working',
        timestamp: new Date().toISOString(),
      })
      await wrapper.vm.$nextTick()

      // Verify agent-2 updated
      const agent2 = agents.find((a) => a.job_id === 'agent-2')
      expect(agent2.status).toBe('working')

      // Update agent-2: working → complete
      handler({
        job_id: 'agent-2',
        tenant_key: 'test-tenant',
        status: 'complete',
        timestamp: new Date().toISOString(),
      })
      await wrapper.vm.$nextTick()

      // Verify agent-2 is now complete
      expect(agent2.status).toBe('complete')

      // Update agent-4: failed → working (retry scenario)
      handler({
        job_id: 'agent-4',
        tenant_key: 'test-tenant',
        status: 'working',
        timestamp: new Date().toISOString(),
      })
      await wrapper.vm.$nextTick()

      // Verify agent-4 is now working
      const agent4 = agents.find((a) => a.job_id === 'agent-4')
      expect(agent4.status).toBe('working')
    })
  })

  describe('Status Color and Style Consistency', () => {
    it('applies correct color classes for all status types', async () => {
      const rows = wrapper.findAll('.agents-table tbody tr')

      // Check all color values from statusConfig
      const colorMap = {
        'failed': 'rgb(229, 57, 53)', // #e53935
        'waiting': 'rgb(255, 215, 0)', // #ffd700
        'working': 'rgb(255, 215, 0)', // #ffd700
        'complete': 'rgb(103, 189, 109)', // #67bd6d
        'cancelled': 'rgb(255, 152, 0)', // #ff9800
      }

      rows.forEach((row) => {
        const statusCell = row.find('.status-cell')
        const text = statusCell.text()
        // Map text to status for lookup
        const statusMap = {
          'Failed': 'failed',
          'Waiting.': 'waiting',
          'Working...': 'working',
          'Complete': 'complete',
          'Cancelled': 'cancelled',
        }
        const status = statusMap[text]
        const expectedColor = colorMap[status]
        expect(statusCell.element.style.color).toBe(expectedColor)
      })
    })

    it('applies italic style only to waiting and working statuses', async () => {
      const rows = wrapper.findAll('.agents-table tbody tr')

      rows.forEach((row) => {
        const statusCell = row.find('.status-cell')
        const text = statusCell.text()
        const isItalic = ['Waiting.', 'Working...'].includes(text)
        const expectedFontStyle = isItalic ? 'italic' : 'normal'
        expect(statusCell.element.style.fontStyle).toBe(expectedFontStyle)
      })
    })
  })
})
