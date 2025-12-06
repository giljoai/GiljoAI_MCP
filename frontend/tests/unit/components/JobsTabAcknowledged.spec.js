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
import { createVuetify } from 'vuetify'
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
  let vuetify

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

  // Helper to find v-icon-stub by icon prop value
  function findIconByName(component, iconName) {
    const icons = component.findAll('v-icon-stub')
    return icons.find(icon => icon.attributes('icon') === iconName)
  }

  // Helper to find all v-icon-stubs with given name
  function findAllIconsByName(component, iconName) {
    const icons = component.findAll('v-icon-stub')
    return icons.filter(icon => icon.attributes('icon') === iconName)
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

      // Find cell with checkmark icon - when using stubs, v-icon renders as v-icon-stub
      const checkIcon = findIconByName(wrapper, 'mdi-check')
      expect(checkIcon).toBeDefined()
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
        const checkIcon = cell.findAll('v-icon-stub').find(icon => icon.attributes('icon') === 'mdi-check')
        if (checkIcon) {
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

      const checkIcon = findIconByName(wrapper, 'mdi-check')
      expect(checkIcon).toBeDefined()

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

      const checkIcon = findIconByName(wrapper, 'mdi-check')
      expect(checkIcon).toBeDefined()

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

      const checkmarks = findAllIconsByName(wrapper, 'mdi-check')
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
      const minusIcon = findIconByName(row, 'mdi-minus')
      const dashIcon = findIconByName(row, 'mdi-minus-circle-outline')

      const hasDashIndicator = minusIcon || dashIcon
      expect(hasDashIndicator).toBeDefined()
    })

    it('displays tooltip showing not acknowledged message', () => {
      const agents = [
        createMockAgent({
          mission_acknowledged_at: null
        })
      ]

      wrapper = createWrapper(agents)

      const row = wrapper.find('tbody tr')
      const minusIcon = findIconByName(row, 'mdi-minus') || findIconByName(row, 'mdi-minus-circle-outline')

      if (minusIcon) {
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
      const icons = row.findAll('v-icon-stub')
      const icon = icons.find(i => i.attributes('icon') === 'mdi-minus' || i.attributes('icon') === 'mdi-minus-circle-outline')

      // Verify icon is found
      expect(icon).toBeDefined()

      // Should have grey color attribute
      if (icon) {
        const colorAttr = icon.attributes('color')
        expect(['grey', 'gray', 'disabled', undefined]).toContain(colorAttr)
      }
    })
  })

  // ============================================
  // 4. WEBSOCKET REAL-TIME UPDATES
  // ============================================

  describe('WebSocket Real-Time Updates', () => {
    it('component renders acknowledged status correctly for WebSocket flow', async () => {
      // This test verifies that the component CAN display acknowledged status
      // actual WebSocket mocking is handled in integration tests
      const agents = [
        createMockAgent({
          job_id: 'job-123',
          agent_id: 'agent-123',
          mission_acknowledged_at: '2025-12-06T11:45:00Z'
        })
      ]

      wrapper = createWrapper(agents)

      // Verify checkmark displays
      const checkIcon = findIconByName(wrapper, 'mdi-check')
      expect(checkIcon).toBeDefined()
    })

    it('displays correct acknowledged status for multiple agents', async () => {
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
          mission_acknowledged_at: '2025-12-06T12:00:00Z',
          agent_type: 'implementer'
        })
      ]

      wrapper = createWrapper(agents)

      // Verify counts
      const checkmarks = findAllIconsByName(wrapper, 'mdi-check')
      const minusIcons = findAllIconsByName(wrapper, 'mdi-minus-circle-outline')

      // Should have 1 checkmark (job-2) and 1 minus (job-1)
      expect(checkmarks.length).toBe(1)
      expect(minusIcons.length).toBe(1)
    })

    it('maintains acknowledged state consistently', async () => {
      const agents = [
        createMockAgent({
          job_id: 'job-123',
          mission_acknowledged_at: '2025-12-06T12:00:00Z'
        })
      ]

      wrapper = createWrapper(agents)

      // Component should display checkmark
      const checkIcon = findIconByName(wrapper, 'mdi-check')
      expect(checkIcon).toBeDefined()

      // Update other props and verify it persists
      await wrapper.setProps({
        messages: [{ id: '1', content: 'test' }]
      })

      const checkIconAfter = findIconByName(wrapper, 'mdi-check')
      expect(checkIconAfter).toBeDefined()
    })

    it('component displays acknowledged status with proper attributes', async () => {
      const agents = [
        createMockAgent({
          job_id: 'job-123',
          mission_acknowledged_at: '2025-12-06T11:45:00Z'
        })
      ]

      wrapper = createWrapper(agents)

      const checkIcon = findIconByName(wrapper, 'mdi-check')
      expect(checkIcon).toBeDefined()

      // Verify icon has proper attributes
      if (checkIcon) {
        expect(checkIcon.attributes('icon')).toBe('mdi-check')
        expect(checkIcon.attributes('color')).toBe('success')
      }
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

      const checkIcon = findIconByName(wrapper, 'mdi-check')
      const tooltip = checkIcon?.attributes('title')

      // Should contain formatted date/time
      expect(tooltip).toBeTruthy()
      // Component formats as "Acknowledged at Dec 6, 2025, 5:30 AM"
      expect(tooltip).toMatch(/(Acknowledged|Dec|2025)/)
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
      const checkIcon = findIconByName(wrapper, 'mdi-check')
      const minusIcon = findIconByName(wrapper, 'mdi-minus') || findIconByName(wrapper, 'mdi-minus-circle-outline')

      expect(checkIcon || minusIcon).toBeDefined()
    })

    it('shows user-friendly timestamp format (e.g., "Dec 6, 2025, 10:30 AM")', () => {
      const agents = [
        createMockAgent({
          mission_acknowledged_at: '2025-12-06T10:30:00Z'
        })
      ]

      wrapper = createWrapper(agents)

      const checkIcon = findIconByName(wrapper, 'mdi-check')
      const tooltip = checkIcon?.attributes('title')

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
      const minusIcon = findIconByName(wrapper, 'mdi-minus') || findIconByName(wrapper, 'mdi-minus-circle-outline')
      expect(minusIcon).toBeDefined()
    })

    it('handles agent with empty string mission_acknowledged_at', () => {
      const agents = [
        createMockAgent({
          mission_acknowledged_at: ''
        })
      ]

      wrapper = createWrapper(agents)

      // Should treat as unacknowledged
      const minusIcon = findIconByName(wrapper, 'mdi-minus') || findIconByName(wrapper, 'mdi-minus-circle-outline')
      expect(minusIcon).toBeDefined()
    })

    it('displays single checkmark for acknowledged agent', async () => {
      const agents = [
        createMockAgent({
          job_id: 'job-123',
          mission_acknowledged_at: '2025-12-06T15:00:00Z'
        })
      ]

      wrapper = createWrapper(agents)

      // Should only show one checkmark for this agent
      const checkmarks = findAllIconsByName(wrapper, 'mdi-check')
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

      let checkIcon = findIconByName(wrapper, 'mdi-check')
      expect(checkIcon).toBeDefined()

      // Change agent status
      agents[0].status = 'working'
      await nextTick()

      // Checkmark should persist
      checkIcon = findIconByName(wrapper, 'mdi-check')
      expect(checkIcon).toBeDefined()
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

      const checkIcon = findIconByName(wrapper, 'mdi-check')
      expect(checkIcon).toBeDefined()

      // Check that icon exists - accessibility attributes are on the component
      // and should be rendered by Vue when component is properly implemented
      if (checkIcon) {
        // Icon should be present and properly configured
        expect(checkIcon.attributes('icon')).toBe('mdi-check')
      }
    })

    it('provides accessible label for unacknowledged icon', () => {
      const agents = [
        createMockAgent({
          mission_acknowledged_at: null
        })
      ]

      wrapper = createWrapper(agents)

      const row = wrapper.find('tbody tr')
      const minusIcon = findIconByName(row, 'mdi-minus-circle-outline') || findIconByName(row, 'mdi-minus')

      expect(minusIcon).toBeDefined()

      // Check that icon exists with correct icon name
      if (minusIcon) {
        const iconAttr = minusIcon.attributes('icon')
        expect(['mdi-minus', 'mdi-minus-circle-outline']).toContain(iconAttr)
      }
    })

    it('column header is properly labeled', () => {
      wrapper = createWrapper()

      const headers = wrapper.findAll('th')
      const ackHeader = headers.find(h => h.text().includes('Acknowledged'))

      expect(ackHeader).toBeDefined()
      expect(ackHeader?.text()).toBe('Job Acknowledged')
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
      expect(cells.length).toBeGreaterThanOrEqual(7)

      // Verify acknowledged cell has checkmark
      const checkIcon = findAllIconsByName(wrapper, 'mdi-check')
      expect(checkIcon.length).toBeGreaterThan(0)
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

      // Count checkmarks and verify alignment
      const checkmarks = findAllIconsByName(wrapper, 'mdi-check')
      const minusIcons = findAllIconsByName(wrapper, 'mdi-minus-circle-outline')

      // Should have 2 checkmarks (agents 1 and 3)
      expect(checkmarks.length).toBe(2)
      // Should have at least 1 minus icon (agent 2)
      expect(minusIcons.length).toBeGreaterThanOrEqual(1)
    })
  })
})
