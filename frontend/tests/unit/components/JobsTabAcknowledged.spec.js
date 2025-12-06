/**
 * JobsTabAcknowledged.spec.js
 *
 * TDD RED Phase: Write failing tests for Job Acknowledged column
 * Tests will fail until JobsTab implements mission_acknowledged_at column display
 *
 * Feature: Display job acknowledged status via mission_acknowledged_at field
 * Backend provides: mission_acknowledged_at ISO 8601 timestamp in job response
 * WebSocket event: job:mission_acknowledged { job_id, mission_acknowledged_at, timestamp }
 *
 * Tests validate:
 * 1. Column header "Job Acknowledged" is visible
 * 2. Checkmark icon shows when mission_acknowledged_at has a value
 * 3. Empty/dash indicator shows when mission_acknowledged_at is null
 * 4. Real-time updates via WebSocket event
 * 5. Tooltip shows formatted timestamp when acknowledged
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import JobsTab from '@/components/projects/JobsTab.vue'
import { useWebSocketStore } from '@/stores/websocket'
import { createPinia, setActivePinia } from 'pinia'

// Mock composables
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    showToast: vi.fn()
  })
}))

vi.mock('@/composables/useWebSocket', () => ({
  useWebSocketV2: () => ({
    on: vi.fn(),
    off: vi.fn(),
    emit: vi.fn(),
  })
}))

vi.mock('@/services/api', () => ({
  api: {
    prompts: {
      agentPrompt: vi.fn().mockResolvedValue({
        data: { prompt: 'Test agent prompt' }
      })
    }
  }
}))

// Mock navigator.clipboard
Object.assign(navigator, {
  clipboard: {
    writeText: vi.fn().mockResolvedValue(undefined)
  }
})

// Mock window.isSecureContext
Object.defineProperty(window, 'isSecureContext', {
  writable: true,
  value: true
})

describe('JobsTab - Job Acknowledged Column (Handover 0297)', () => {
  let wrapper
  let pinia

  const mockProject = {
    project_id: 'project-123',
    name: 'Test Project',
    description: 'Test Description',
  }

  // Base agent with acknowledged status
  const createMockAgent = (overrides = {}) => ({
    job_id: 'job-123',
    agent_id: 'agent-123',
    agent_type: 'orchestrator',
    status: 'waiting',
    mission_acknowledged_at: null,
    messages_sent: 0,
    messages_waiting: 0,
    messages_read: 0,
    ...overrides
  })

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
  })

  function createWrapper(agents = [createMockAgent()]) {
    return mount(JobsTab, {
      props: {
        project: mockProject,
        agents: agents,
        messages: [],
        allAgentsComplete: false,
      },
      global: {
        plugins: [pinia],
        stubs: {
          'v-btn': true,
          'v-icon': true,
          'v-tooltip': true,
          'v-avatar': true,
          'v-dialog': true,
          'v-card': true,
          'v-card-title': true,
          'v-card-text': true,
          'v-card-actions': true,
          'v-text-field': true,
          'v-spacer': true,
          'LaunchSuccessorDialog': true,
          'AgentDetailsModal': true,
          'CloseoutModal': true,
        },
      },
    })
  }

  // ============================================
  // 1. COLUMN HEADER TESTS
  // ============================================

  describe('Column Header Display', () => {
    it('renders Job Acknowledged column header', () => {
      wrapper = createWrapper()

      const headers = wrapper.findAll('th')
      const headerTexts = headers.map(h => h.text())

      expect(headerTexts).toContain('Job Acknowledged')
    })

    it('displays column header in correct position (before Messages Sent)', () => {
      wrapper = createWrapper()

      const headers = wrapper.findAll('th')
      const headerTexts = headers.map(h => h.text())

      const ackIndex = headerTexts.indexOf('Job Acknowledged')
      const messagesIndex = headerTexts.indexOf('Messages Sent')

      expect(ackIndex).toBeGreaterThan(-1)
      expect(messagesIndex).toBeGreaterThan(-1)
      expect(ackIndex).toBeLessThan(messagesIndex)
    })

    it('displays column header in correct position (after Agent Status)', () => {
      wrapper = createWrapper()

      const headers = wrapper.findAll('th')
      const headerTexts = headers.map(h => h.text())

      const statusIndex = headerTexts.indexOf('Agent Status')
      const ackIndex = headerTexts.indexOf('Job Acknowledged')

      expect(statusIndex).toBeGreaterThan(-1)
      expect(ackIndex).toBeGreaterThan(-1)
      expect(statusIndex).toBeLessThan(ackIndex)
    })
  })

  // ============================================
  // 2. ACKNOWLEDGED STATUS DISPLAY
  // ============================================

  describe('Checkmark Display When Acknowledged', () => {
    it('renders checkmark icon when mission_acknowledged_at is set', () => {
      const acknowledgedTime = '2025-12-06T10:30:00Z'
      const agents = [
        createMockAgent({
          job_id: 'job-ack-1',
          agent_id: 'agent-ack-1',
          mission_acknowledged_at: acknowledgedTime
        })
      ]

      wrapper = createWrapper(agents)

      // Find the acknowledged cell (should be after status cell)
      const rows = wrapper.findAll('tbody tr')
      expect(rows.length).toBeGreaterThan(0)

      const firstRow = rows[0]
      const cells = firstRow.findAll('td')

      // Find cell with checkmark icon
      const checkIcon = firstRow.find('v-icon[icon="mdi-check"]')
      expect(checkIcon.exists()).toBe(true)
    })

    it('shows checkmark in correct cell position', () => {
      const agents = [
        createMockAgent({
          mission_acknowledged_at: '2025-12-06T10:30:00Z'
        })
      ]

      wrapper = createWrapper(agents)

      const row = wrapper.find('tbody tr')
      const cells = row.findAll('td')

      // Find acknowledgment cell - should be after status, before messages_sent
      let ackCellIndex = -1
      cells.forEach((cell, index) => {
        if (cell.find('v-icon[icon="mdi-check"]').exists()) {
          ackCellIndex = index
        }
      })

      expect(ackCellIndex).toBeGreaterThan(-1)
    })

    it('displays checkmark with success color', () => {
      const agents = [
        createMockAgent({
          mission_acknowledged_at: '2025-12-06T10:30:00Z'
        })
      ]

      wrapper = createWrapper(agents)

      const checkIcon = wrapper.find('v-icon[icon="mdi-check"]')
      expect(checkIcon.exists()).toBe(true)

      // Check for success color attribute
      const colorAttr = checkIcon.attributes('color')
      expect(['success', 'green', 'white']).toContain(colorAttr)
    })

    it('displays tooltip showing acknowledged timestamp', () => {
      const acknowledgedTime = '2025-12-06T10:30:00Z'
      const agents = [
        createMockAgent({
          mission_acknowledged_at: acknowledgedTime
        })
      ]

      wrapper = createWrapper(agents)

      const checkIcon = wrapper.find('v-icon[icon="mdi-check"]')
      expect(checkIcon.exists()).toBe(true)

      // Check title or aria-label for timestamp
      const title = checkIcon.attributes('title')
      const ariaLabel = checkIcon.attributes('aria-label')

      const hasTimestamp = title?.includes('Acknowledged') || ariaLabel?.includes('Acknowledged')
      expect(hasTimestamp).toBe(true)
    })

    it('renders multiple agents with different acknowledged statuses', () => {
      const agents = [
        createMockAgent({
          job_id: 'job-1',
          agent_id: 'agent-1',
          mission_acknowledged_at: '2025-12-06T10:30:00Z'
        }),
        createMockAgent({
          job_id: 'job-2',
          agent_id: 'agent-2',
          mission_acknowledged_at: null
        }),
        createMockAgent({
          job_id: 'job-3',
          agent_id: 'agent-3',
          mission_acknowledged_at: '2025-12-06T11:00:00Z'
        })
      ]

      wrapper = createWrapper(agents)

      const checkmarks = wrapper.findAll('v-icon[icon="mdi-check"]')
      expect(checkmarks.length).toBe(2)
    })
  })

  // ============================================
  // 3. NOT ACKNOWLEDGED STATUS DISPLAY
  // ============================================

  describe('Empty/Dash Indicator When Not Acknowledged', () => {
    it('renders empty indicator when mission_acknowledged_at is null', () => {
      const agents = [
        createMockAgent({
          mission_acknowledged_at: null
        })
      ]

      wrapper = createWrapper(agents)

      const row = wrapper.find('tbody tr')
      const cells = row.findAll('td')

      // Should have an acknowledgment cell but without checkmark
      let ackCellIndex = -1
      cells.forEach((cell, index) => {
        const cellHtml = cell.html()
        // Cell should be empty or have dash/minus icon
        if (cellHtml && !cellHtml.includes('mdi-check')) {
          ackCellIndex = index
        }
      })

      expect(ackCellIndex).toBeGreaterThan(-1)
    })

    it('renders dash/minus icon when not acknowledged', () => {
      const agents = [
        createMockAgent({
          mission_acknowledged_at: null
        })
      ]

      wrapper = createWrapper(agents)

      const row = wrapper.find('tbody tr')
      const minusIcon = row.find('v-icon[icon="mdi-minus"]')
      const dashIcon = row.find('v-icon[icon="mdi-minus-circle-outline"]')

      const hasDashIndicator = minusIcon.exists() || dashIcon.exists()
      expect(hasDashIndicator).toBe(true)
    })

    it('displays tooltip showing not acknowledged message', () => {
      const agents = [
        createMockAgent({
          mission_acknowledged_at: null
        })
      ]

      wrapper = createWrapper(agents)

      const row = wrapper.find('tbody tr')
      const minusIcon = row.find('v-icon[icon="mdi-minus"], v-icon[icon="mdi-minus-circle-outline"]')

      if (minusIcon.exists()) {
        const title = minusIcon.attributes('title')
        const ariaLabel = minusIcon.attributes('aria-label')

        const hasNotAckMessage = title?.includes('Not') || ariaLabel?.includes('Not')
        expect(hasNotAckMessage).toBe(true)
      }
    })

    it('shows gray color for unacknowledged indicator', () => {
      const agents = [
        createMockAgent({
          mission_acknowledged_at: null
        })
      ]

      wrapper = createWrapper(agents)

      const row = wrapper.find('tbody tr')
      const icon = row.find('v-icon')

      // Should have grey color
      const colorAttr = icon.attributes('color')
      expect(['grey', 'gray', 'disabled']).toContain(colorAttr)
    })
  })

  // ============================================
  // 4. WEBSOCKET REAL-TIME UPDATES
  // ============================================

  describe('WebSocket Real-Time Updates', () => {
    it('updates job acknowledged status on websocket event', async () => {
      const agents = [
        createMockAgent({
          job_id: 'job-123',
          agent_id: 'agent-123',
          mission_acknowledged_at: null
        })
      ]

      wrapper = createWrapper(agents)

      // Verify no checkmark initially
      let checkIcon = wrapper.find('v-icon[icon="mdi-check"]')
      expect(checkIcon.exists()).toBe(false)

      // Get WebSocket store and emit event
      const wsStore = useWebSocketStore()
      const acknowledgedTime = '2025-12-06T11:45:00Z'

      wsStore.$emit('job:mission_acknowledged', {
        job_id: 'job-123',
        mission_acknowledged_at: acknowledgedTime,
        timestamp: acknowledgedTime
      })

      await flushPromises()
      await nextTick()

      // Verify checkmark now appears
      checkIcon = wrapper.find('v-icon[icon="mdi-check"]')
      expect(checkIcon.exists()).toBe(true)
    })

    it('updates correct agent when multiple agents exist', async () => {
      const agents = [
        createMockAgent({
          job_id: 'job-1',
          agent_id: 'agent-1',
          mission_acknowledged_at: null,
          agent_type: 'orchestrator'
        }),
        createMockAgent({
          job_id: 'job-2',
          agent_id: 'agent-2',
          mission_acknowledged_at: null,
          agent_type: 'implementer'
        })
      ]

      wrapper = createWrapper(agents)

      // Initially both unacknowledged
      let checkmarks = wrapper.findAll('v-icon[icon="mdi-check"]')
      expect(checkmarks.length).toBe(0)

      // Acknowledge only job-2
      const wsStore = useWebSocketStore()
      wsStore.$emit('job:mission_acknowledged', {
        job_id: 'job-2',
        mission_acknowledged_at: '2025-12-06T12:00:00Z',
        timestamp: '2025-12-06T12:00:00Z'
      })

      await flushPromises()
      await nextTick()

      // Only job-2 should have checkmark
      checkmarks = wrapper.findAll('v-icon[icon="mdi-check"]')
      expect(checkmarks.length).toBe(1)
    })

    it('handles out-of-order websocket events', async () => {
      const agents = [
        createMockAgent({
          job_id: 'job-123',
          mission_acknowledged_at: null
        })
      ]

      wrapper = createWrapper(agents)

      const wsStore = useWebSocketStore()

      // Emit multiple acknowledgments (should keep latest)
      wsStore.$emit('job:mission_acknowledged', {
        job_id: 'job-123',
        mission_acknowledged_at: '2025-12-06T11:00:00Z'
      })

      await flushPromises()
      await nextTick()

      wsStore.$emit('job:mission_acknowledged', {
        job_id: 'job-123',
        mission_acknowledged_at: '2025-12-06T12:00:00Z'
      })

      await flushPromises()
      await nextTick()

      // Should still show checkmark
      const checkIcon = wrapper.find('v-icon[icon="mdi-check"]')
      expect(checkIcon.exists()).toBe(true)
    })

    it('emits custom event when acknowledged', async () => {
      const agents = [
        createMockAgent({
          job_id: 'job-123',
          mission_acknowledged_at: null
        })
      ]

      wrapper = createWrapper(agents)

      const customEventSpy = vi.fn()
      window.addEventListener('agent:mission_acknowledged', customEventSpy)

      const wsStore = useWebSocketStore()
      const acknowledgedTime = '2025-12-06T11:45:00Z'

      wsStore.$emit('job:mission_acknowledged', {
        job_id: 'job-123',
        mission_acknowledged_at: acknowledgedTime,
        timestamp: acknowledgedTime
      })

      await flushPromises()

      // Check if custom event was dispatched
      expect(customEventSpy).toHaveBeenCalledTimes(1)
      expect(customEventSpy.mock.calls[0][0].detail).toEqual({
        jobId: 'job-123',
        timestamp: acknowledgedTime
      })

      window.removeEventListener('agent:mission_acknowledged', customEventSpy)
    })

    it('persists acknowledged status across component updates', async () => {
      const agents = [
        createMockAgent({
          job_id: 'job-123',
          mission_acknowledged_at: '2025-12-06T10:00:00Z'
        })
      ]

      wrapper = createWrapper(agents)

      let checkIcon = wrapper.find('v-icon[icon="mdi-check"]')
      expect(checkIcon.exists()).toBe(true)

      // Update other data
      await wrapper.setProps({
        messages: [{ id: '1', content: 'test' }]
      })

      // Checkmark should persist
      checkIcon = wrapper.find('v-icon[icon="mdi-check"]')
      expect(checkIcon.exists()).toBe(true)
    })
  })

  // ============================================
  // 5. TIMESTAMP FORMATTING
  // ============================================

  describe('Timestamp Formatting in Tooltip', () => {
    it('formats ISO 8601 timestamp in tooltip', () => {
      const agents = [
        createMockAgent({
          mission_acknowledged_at: '2025-12-06T10:30:45Z'
        })
      ]

      wrapper = createWrapper(agents)

      const checkIcon = wrapper.find('v-icon[icon="mdi-check"]')
      const tooltip = checkIcon.attributes('title')

      // Should contain formatted date/time
      expect(tooltip).toBeTruthy()
      expect(tooltip).toMatch(/\d{1,2}\/\d{1,2}\/\d{4}|\d{4}-\d{2}-\d{2}/)
    })

    it('handles invalid timestamp gracefully', () => {
      const agents = [
        createMockAgent({
          mission_acknowledged_at: 'invalid-date'
        })
      ]

      wrapper = createWrapper(agents)

      // Component should not crash
      expect(wrapper.exists()).toBe(true)

      // Should either show default message or no icon
      const checkIcon = wrapper.find('v-icon[icon="mdi-check"]')
      const minusIcon = wrapper.find('v-icon[icon="mdi-minus"], v-icon[icon="mdi-minus-circle-outline"]')

      expect(checkIcon.exists() || minusIcon.exists()).toBe(true)
    })

    it('shows user-friendly timestamp format (e.g., "Dec 6, 2025, 10:30 AM")', () => {
      const agents = [
        createMockAgent({
          mission_acknowledged_at: '2025-12-06T10:30:00Z'
        })
      ]

      wrapper = createWrapper(agents)

      const checkIcon = wrapper.find('v-icon[icon="mdi-check"]')
      const tooltip = checkIcon.attributes('title')

      // Should be human-readable
      expect(tooltip).toMatch(/acknowledged|Acknowledged/i)
    })
  })

  // ============================================
  // 6. EDGE CASES
  // ============================================

  describe('Edge Cases', () => {
    it('handles empty agent list', () => {
      wrapper = createWrapper([])

      // Should render without error
      expect(wrapper.exists()).toBe(true)

      // Header should still be present
      const headers = wrapper.findAll('th')
      const headerTexts = headers.map(h => h.text())
      expect(headerTexts).toContain('Job Acknowledged')
    })

    it('handles agent with undefined mission_acknowledged_at', () => {
      const agents = [
        createMockAgent({
          mission_acknowledged_at: undefined
        })
      ]

      wrapper = createWrapper(agents)

      // Should treat as null/unacknowledged
      const minusIcon = wrapper.find('v-icon[icon="mdi-minus"], v-icon[icon="mdi-minus-circle-outline"]')
      expect(minusIcon.exists()).toBe(true)
    })

    it('handles agent with empty string mission_acknowledged_at', () => {
      const agents = [
        createMockAgent({
          mission_acknowledged_at: ''
        })
      ]

      wrapper = createWrapper(agents)

      // Should treat as unacknowledged
      const minusIcon = wrapper.find('v-icon[icon="mdi-minus"], v-icon[icon="mdi-minus-circle-outline"]')
      expect(minusIcon.exists()).toBe(true)
    })

    it('handles rapid successive acknowledgments', async () => {
      const agents = [
        createMockAgent({
          job_id: 'job-123',
          mission_acknowledged_at: null
        })
      ]

      wrapper = createWrapper(agents)

      const wsStore = useWebSocketStore()

      // Rapid fire events
      for (let i = 0; i < 5; i++) {
        wsStore.$emit('job:mission_acknowledged', {
          job_id: 'job-123',
          mission_acknowledged_at: `2025-12-06T${String(10 + i).padStart(2, '0')}:00:00Z`
        })
      }

      await flushPromises()
      await nextTick()

      // Should only show one checkmark, not duplicated
      const checkmarks = wrapper.findAll('v-icon[icon="mdi-check"]')
      expect(checkmarks.length).toBe(1)
    })

    it('correctly displays acknowledged status after agent status change', async () => {
      const agents = [
        createMockAgent({
          job_id: 'job-123',
          status: 'waiting',
          mission_acknowledged_at: '2025-12-06T10:30:00Z'
        })
      ]

      wrapper = createWrapper(agents)

      let checkIcon = wrapper.find('v-icon[icon="mdi-check"]')
      expect(checkIcon.exists()).toBe(true)

      // Change agent status
      agents[0].status = 'working'
      await nextTick()

      // Checkmark should persist
      checkIcon = wrapper.find('v-icon[icon="mdi-check"]')
      expect(checkIcon.exists()).toBe(true)
    })
  })

  // ============================================
  // 7. ACCESSIBILITY TESTS
  // ============================================

  describe('Accessibility', () => {
    it('provides accessible label for acknowledged icon', () => {
      const agents = [
        createMockAgent({
          mission_acknowledged_at: '2025-12-06T10:30:00Z'
        })
      ]

      wrapper = createWrapper(agents)

      const checkIcon = wrapper.find('v-icon[icon="mdi-check"]')
      const ariaLabel = checkIcon.attributes('aria-label')
      const title = checkIcon.attributes('title')

      expect(ariaLabel || title).toBeTruthy()
      expect((ariaLabel || title)).toMatch(/acknowledged|Acknowledged/i)
    })

    it('provides accessible label for unacknowledged icon', () => {
      const agents = [
        createMockAgent({
          mission_acknowledged_at: null
        })
      ]

      wrapper = createWrapper(agents)

      const row = wrapper.find('tbody tr')
      const icon = row.find('v-icon')

      const ariaLabel = icon.attributes('aria-label')
      const title = icon.attributes('title')

      expect(ariaLabel || title).toBeTruthy()
      expect((ariaLabel || title)).toMatch(/not|pending|waiting/i)
    })

    it('column header is properly labeled', () => {
      wrapper = createWrapper()

      const headers = wrapper.findAll('th')
      const ackHeader = headers.find(h => h.text().includes('Acknowledged'))

      expect(ackHeader).toBeDefined()
      expect(ackHeader.text()).toBe('Job Acknowledged')
    })
  })

  // ============================================
  // 8. INTEGRATION WITH OTHER COLUMNS
  // ============================================

  describe('Integration with Other Columns', () => {
    it('displays acknowledged column alongside other job columns', () => {
      const agents = [
        createMockAgent({
          agent_type: 'orchestrator',
          status: 'working',
          mission_acknowledged_at: '2025-12-06T10:30:00Z',
          messages_sent: 5,
          messages_waiting: 2,
          messages_read: 3
        })
      ]

      wrapper = createWrapper(agents)

      const row = wrapper.find('tbody tr')
      const cells = row.findAll('td')

      // Should have all columns: type, id, status, acknowledged, sent, waiting, read, actions
      expect(cells.length).toBeGreaterThanOrEqual(8)

      // Verify acknowledged cell has checkmark
      let foundCheckmark = false
      cells.forEach(cell => {
        if (cell.find('v-icon[icon="mdi-check"]').exists()) {
          foundCheckmark = true
        }
      })

      expect(foundCheckmark).toBe(true)
    })

    it('maintains correct column alignment with multiple agents', () => {
      const agents = [
        createMockAgent({
          job_id: 'job-1',
          mission_acknowledged_at: '2025-12-06T10:00:00Z'
        }),
        createMockAgent({
          job_id: 'job-2',
          mission_acknowledged_at: null
        }),
        createMockAgent({
          job_id: 'job-3',
          mission_acknowledged_at: '2025-12-06T11:00:00Z'
        })
      ]

      wrapper = createWrapper(agents)

      const rows = wrapper.findAll('tbody tr')
      expect(rows.length).toBe(3)

      // Each row should have acknowledged status in same column position
      rows.forEach((row, index) => {
        const cells = row.findAll('td')
        const agent = agents[index]

        if (agent.mission_acknowledged_at) {
          expect(row.find('v-icon[icon="mdi-check"]').exists()).toBe(true)
        } else {
          const minusIcon = row.find('v-icon[icon="mdi-minus"], v-icon[icon="mdi-minus-circle-outline"]')
          expect(minusIcon.exists()).toBe(true)
        }
      })
    })
  })
})
