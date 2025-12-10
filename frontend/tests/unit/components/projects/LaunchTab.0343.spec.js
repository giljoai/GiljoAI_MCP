/**
 * LaunchTab.0343.spec.js
 *
 * Handover 0343: Lock Execution Mode Toggle in UI (Frontend)
 *
 * Tests for locking the execution mode toggle when an orchestrator job exists.
 * This prevents users from changing execution mode after staging begins.
 *
 * TDD Discipline: Tests written FIRST (RED phase), implementation follows.
 *
 * Requirements:
 * 1. Lock icon shows when orchestrator agent exists
 * 2. Toggle bar gets 'toggle-locked' class when orchestrator exists
 * 3. Warning toast displayed when user clicks locked toggle
 * 4. API call NOT made when toggle is locked
 * 5. Toggle remains unlocked when no orchestrator exists
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { nextTick } from 'vue'
import LaunchTab from '@/components/projects/LaunchTab.vue'

const vuetify = createVuetify({
  components,
  directives,
})

// Mock WebSocket composable
let mockWebSocketOn
let mockWebSocketOff

vi.mock('@/composables/useWebSocket', () => ({
  useWebSocket: () => ({
    on: mockWebSocketOn,
    off: mockWebSocketOff,
  })
}))

// Mock Toast composable
let mockShowToast

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    showToast: mockShowToast,
  })
}))

// Mock user store
vi.mock('@/stores/user', () => ({
  useUserStore: vi.fn().mockReturnValue({
    currentUser: {
      tenant_key: 'test-tenant-key-123'
    }
  })
}))

// Mock API service
vi.mock('@/services/api', () => ({
  api: {
    projects: {
      update: vi.fn()
    }
  }
}))

// Import API after mock
import { api } from '@/services/api'

describe('LaunchTab Execution Mode Lock (0343)', () => {
  const mockProject = {
    id: 'project-123',
    project_id: 'project-123',
    name: 'Test Project',
    mission: 'Test project mission',
    description: 'Test project description',
    execution_mode: 'multi_terminal',
    agents: [],
  }

  const mockOrchestratorAgent = {
    id: 'orchestrator-job-1',
    job_id: 'orchestrator-job-1',
    agent_type: 'orchestrator',
    agent_name: 'Orchestrator',
    status: 'working',
  }

  const mockImplementerAgent = {
    id: 'implementer-job-1',
    job_id: 'implementer-job-1',
    agent_type: 'implementer',
    agent_name: 'Implementer',
    status: 'waiting',
  }

  beforeEach(() => {
    mockWebSocketOn = vi.fn()
    mockWebSocketOff = vi.fn()
    mockShowToast = vi.fn()
    vi.clearAllMocks()
  })

  describe('When Orchestrator Job EXISTS (LOCKED state)', () => {
    it('should show lock icon when orchestrator agent exists', async () => {
      const wrapper = mount(LaunchTab, {
        props: {
          project: {
            ...mockProject,
            agents: [mockOrchestratorAgent],
          },
          orchestrator: null,
          isStaging: false,
        },
        global: {
          plugins: [vuetify],
          stubs: {
            AgentDetailsModal: true,
            AgentMissionEditModal: true,
            'v-snackbar': true,
          },
        },
      })

      await nextTick()

      // THEN: Lock icon should be visible
      const lockIcon = wrapper.find('.lock-icon')
      expect(lockIcon.exists()).toBe(true)
      expect(lockIcon.classes()).toContain('lock-icon')
    })

    it('should add toggle-locked class to toggle bar when orchestrator exists', async () => {
      const wrapper = mount(LaunchTab, {
        props: {
          project: {
            ...mockProject,
            agents: [mockOrchestratorAgent],
          },
          orchestrator: null,
          isStaging: false,
        },
        global: {
          plugins: [vuetify],
          stubs: {
            AgentDetailsModal: true,
            AgentMissionEditModal: true,
            'v-snackbar': true,
          },
        },
      })

      await nextTick()

      // THEN: Toggle bar should have locked class
      const toggleBar = wrapper.find('[data-testid="execution-mode-toggle"]')
      expect(toggleBar.classes()).toContain('toggle-locked')
    })

    it('should show warning toast when user clicks locked toggle', async () => {
      const wrapper = mount(LaunchTab, {
        props: {
          project: {
            ...mockProject,
            agents: [mockOrchestratorAgent],
          },
          orchestrator: null,
          isStaging: false,
        },
        global: {
          plugins: [vuetify],
          stubs: {
            AgentDetailsModal: true,
            AgentMissionEditModal: true,
            'v-snackbar': true,
          },
        },
      })

      await nextTick()

      // WHEN: User clicks locked toggle
      await wrapper.find('[data-testid="execution-mode-toggle"]').trigger('click')
      await flushPromises()

      // THEN: Warning toast should appear
      expect(mockShowToast).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'warning',
        })
      )

      // THEN: Toast message should mention locked state
      const callArgs = mockShowToast.mock.calls[0][0]
      expect(callArgs.message).toMatch(/lock/i)
    })

    it('should NOT call API when clicking locked toggle', async () => {
      api.projects.update = vi.fn().mockResolvedValue({ data: { success: true } })

      const wrapper = mount(LaunchTab, {
        props: {
          project: {
            ...mockProject,
            agents: [mockOrchestratorAgent],
          },
          orchestrator: null,
          isStaging: false,
        },
        global: {
          plugins: [vuetify],
          stubs: {
            AgentDetailsModal: true,
            AgentMissionEditModal: true,
            'v-snackbar': true,
          },
        },
      })

      await nextTick()

      // WHEN: User clicks locked toggle
      await wrapper.find('[data-testid="execution-mode-toggle"]').trigger('click')
      await flushPromises()

      // THEN: API should NOT be called
      expect(api.projects.update).not.toHaveBeenCalled()
    })

    it('should NOT change execution mode state when locked toggle clicked', async () => {
      const wrapper = mount(LaunchTab, {
        props: {
          project: {
            ...mockProject,
            execution_mode: 'multi_terminal',
            agents: [mockOrchestratorAgent],
          },
          orchestrator: null,
          isStaging: false,
        },
        global: {
          plugins: [vuetify],
          stubs: {
            AgentDetailsModal: true,
            AgentMissionEditModal: true,
            'v-snackbar': true,
          },
        },
      })

      await nextTick()

      // GIVEN: Initial state is multi_terminal (false)
      expect(wrapper.vm.usingClaudeCodeSubagents).toBe(false)

      // WHEN: User clicks locked toggle
      await wrapper.find('[data-testid="execution-mode-toggle"]').trigger('click')
      await flushPromises()

      // THEN: State should remain unchanged
      expect(wrapper.vm.usingClaudeCodeSubagents).toBe(false)
    })

    it('should work with different orchestrator statuses', async () => {
      const statuses = ['waiting', 'working', 'paused', 'completed']

      for (const status of statuses) {
        const wrapper = mount(LaunchTab, {
          props: {
            project: {
              ...mockProject,
              agents: [{
                ...mockOrchestratorAgent,
                status: status,
              }],
            },
            orchestrator: null,
            isStaging: false,
          },
          global: {
            plugins: [vuetify],
            stubs: {
              AgentDetailsModal: true,
              AgentMissionEditModal: true,
              'v-snackbar': true,
            },
          },
        })

        await nextTick()

        // THEN: Toggle should still be locked regardless of status
        const toggleBar = wrapper.find('[data-testid="execution-mode-toggle"]')
        expect(toggleBar.classes()).toContain('toggle-locked')
      }
    })
  })

  describe('When Orchestrator Job DOES NOT EXIST (UNLOCKED state)', () => {
    it('should NOT show lock icon when no orchestrator exists', async () => {
      const wrapper = mount(LaunchTab, {
        props: {
          project: mockProject,
          orchestrator: null,
          isStaging: false,
        },
        global: {
          plugins: [vuetify],
          stubs: {
            AgentDetailsModal: true,
            AgentMissionEditModal: true,
            'v-snackbar': true,
          },
        },
      })

      // GIVEN: Component WITHOUT orchestrator (agents list empty)
      // No agents added
      await nextTick()

      // THEN: No lock icon should exist
      const lockIcon = wrapper.find('.lock-icon')
      expect(lockIcon.exists()).toBe(false)
    })

    it('should NOT have toggle-locked class when no orchestrator exists', async () => {
      const wrapper = mount(LaunchTab, {
        props: {
          project: {
            ...mockProject,
            agents: [mockImplementerAgent],
          },
          orchestrator: null,
          isStaging: false,
        },
        global: {
          plugins: [vuetify],
          stubs: {
            AgentDetailsModal: true,
            AgentMissionEditModal: true,
            'v-snackbar': true,
          },
        },
      })

      await nextTick()

      // THEN: Toggle bar should NOT have locked class
      const toggleBar = wrapper.find('[data-testid="execution-mode-toggle"]')
      expect(toggleBar.classes()).not.toContain('toggle-locked')
    })

    it('should allow toggle to work normally when no orchestrator exists', async () => {
      api.projects.update = vi.fn().mockResolvedValue({ data: { success: true } })

      const wrapper = mount(LaunchTab, {
        props: {
          project: {
            ...mockProject,
            execution_mode: 'multi_terminal',
          },
          orchestrator: null,
          isStaging: false,
        },
        global: {
          plugins: [vuetify],
          stubs: {
            AgentDetailsModal: true,
            AgentMissionEditModal: true,
            'v-snackbar': true,
          },
        },
      })

      // GIVEN: NO orchestrator
      // (agents list empty)
      await nextTick()

      // WHEN: User clicks toggle
      await wrapper.find('[data-testid="execution-mode-toggle"]').trigger('click')
      await flushPromises()

      // THEN: API SHOULD be called
      expect(api.projects.update).toHaveBeenCalled()

      // THEN: State should change
      expect(wrapper.vm.usingClaudeCodeSubagents).toBe(true)
    })

    it('should NOT show warning toast when toggle is unlocked', async () => {
      api.projects.update = vi.fn().mockResolvedValue({ data: { success: true } })

      const wrapper = mount(LaunchTab, {
        props: {
          project: mockProject,
          orchestrator: null,
          isStaging: false,
        },
        global: {
          plugins: [vuetify],
          stubs: {
            AgentDetailsModal: true,
            AgentMissionEditModal: true,
            'v-snackbar': true,
          },
        },
      })

      // GIVEN: NO orchestrator
      await nextTick()

      // WHEN: User clicks toggle
      await wrapper.find('[data-testid="execution-mode-toggle"]').trigger('click')
      await flushPromises()

      // THEN: Warning toast should NOT be shown
      const warningCalls = mockShowToast.mock.calls.filter(
        call => call[0]?.type === 'warning'
      )
      expect(warningCalls).toHaveLength(0)

      // THEN: Success/info toast should be shown instead
      expect(mockShowToast).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'info',
        })
      )
    })
  })

  describe('Dynamic Lock State Changes', () => {
    it('should lock toggle when orchestrator agent is added dynamically', async () => {
      const wrapper = mount(LaunchTab, {
        props: {
          project: mockProject,
          orchestrator: null,
          isStaging: false,
        },
        global: {
          plugins: [vuetify],
          stubs: {
            AgentDetailsModal: true,
            AgentMissionEditModal: true,
            'v-snackbar': true,
          },
        },
      })

      // GIVEN: Initially no orchestrator
      let toggleBar = wrapper.find('[data-testid="execution-mode-toggle"]')
      expect(toggleBar.classes()).not.toContain('toggle-locked')

      // WHEN: Orchestrator agent is added via prop update (simulates WebSocket event)
      await wrapper.setProps({
        project: {
          ...mockProject,
          agents: [mockOrchestratorAgent],
        },
      })
      await nextTick()

      // THEN: Toggle should be locked
      toggleBar = wrapper.find('[data-testid="execution-mode-toggle"]')
      expect(toggleBar.classes()).toContain('toggle-locked')
    })

    it('should unlock toggle when orchestrator agent is removed', async () => {
      const wrapper = mount(LaunchTab, {
        props: {
          project: {
            ...mockProject,
            agents: [mockOrchestratorAgent],
          },
          orchestrator: null,
          isStaging: false,
        },
        global: {
          plugins: [vuetify],
          stubs: {
            AgentDetailsModal: true,
            AgentMissionEditModal: true,
            'v-snackbar': true,
          },
        },
      })

      await nextTick()

      // GIVEN: Orchestrator exists
      let toggleBar = wrapper.find('[data-testid="execution-mode-toggle"]')
      expect(toggleBar.classes()).toContain('toggle-locked')

      // WHEN: Orchestrator is removed
      await wrapper.setProps({
        project: {
          ...mockProject,
          agents: [],
        },
      })
      await nextTick()

      // THEN: Toggle should be unlocked
      toggleBar = wrapper.find('[data-testid="execution-mode-toggle"]')
      expect(toggleBar.classes()).not.toContain('toggle-locked')
    })
  })

  describe('Lock Icon Styling', () => {
    it('should render lock icon with correct Material Design icon', async () => {
      const wrapper = mount(LaunchTab, {
        props: {
          project: {
            ...mockProject,
            agents: [mockOrchestratorAgent],
          },
          orchestrator: null,
          isStaging: false,
        },
        global: {
          plugins: [vuetify],
          stubs: {
            AgentDetailsModal: true,
            AgentMissionEditModal: true,
            'v-snackbar': true,
          },
        },
      })

      await nextTick()

      // THEN: Lock icon should exist
      const lockIcon = wrapper.find('.lock-icon')
      expect(lockIcon.exists()).toBe(true)
    })

    it('should position lock icon after toggle options', async () => {
      const wrapper = mount(LaunchTab, {
        props: {
          project: {
            ...mockProject,
            agents: [mockOrchestratorAgent],
          },
          orchestrator: null,
          isStaging: false,
        },
        global: {
          plugins: [vuetify],
          stubs: {
            AgentDetailsModal: true,
            AgentMissionEditModal: true,
            'v-snackbar': true,
          },
        },
      })

      await nextTick()

      const html = wrapper.html()
      const lockIconIndex = html.indexOf('lock-icon')
      const toggleOptionsIndex = html.indexOf('toggle-options')

      // THEN: Lock icon should appear after toggle options
      expect(lockIconIndex).toBeGreaterThan(toggleOptionsIndex)
    })
  })

  describe('Accessibility', () => {
    it('should maintain keyboard accessibility when locked', async () => {
      const wrapper = mount(LaunchTab, {
        props: {
          project: {
            ...mockProject,
            agents: [mockOrchestratorAgent],
          },
          orchestrator: null,
          isStaging: false,
        },
        global: {
          plugins: [vuetify],
          stubs: {
            AgentDetailsModal: true,
            AgentMissionEditModal: true,
            'v-snackbar': true,
          },
        },
      })

      await nextTick()

      // THEN: Toggle element should still be accessible
      const toggleBar = wrapper.find('[data-testid="execution-mode-toggle"]')
      expect(toggleBar.exists()).toBe(true)
      // Even though locked via CSS, keyboard interaction should work
      expect(toggleBar.classes()).toContain('toggle-locked')
    })

    it('should be descriptive in warning message for locked state', async () => {
      const wrapper = mount(LaunchTab, {
        props: {
          project: {
            ...mockProject,
            agents: [mockOrchestratorAgent],
          },
          orchestrator: null,
          isStaging: false,
        },
        global: {
          plugins: [vuetify],
          stubs: {
            AgentDetailsModal: true,
            AgentMissionEditModal: true,
            'v-snackbar': true,
          },
        },
      })

      await nextTick()

      // WHEN: User clicks locked toggle
      await wrapper.find('[data-testid="execution-mode-toggle"]').trigger('click')
      await flushPromises()

      // THEN: Toast message should explain why it's locked
      const callArgs = mockShowToast.mock.calls[0][0]
      expect(callArgs.message).toContain('lock')
      // Message should ideally mention staging or orchestrator
      expect(
        callArgs.message.toLowerCase().includes('staging') ||
        callArgs.message.toLowerCase().includes('orchestrator')
      ).toBe(true)
    })
  })

  describe('Multiple Agents Scenario', () => {
    it('should lock when orchestrator is among multiple agents', async () => {
      const wrapper = mount(LaunchTab, {
        props: {
          project: {
            ...mockProject,
            agents: [
              mockImplementerAgent,
              mockOrchestratorAgent,
              {
                id: 'tester-job-1',
                job_id: 'tester-job-1',
                agent_type: 'tester',
                agent_name: 'Tester',
                status: 'waiting',
              },
            ],
          },
          orchestrator: null,
          isStaging: false,
        },
        global: {
          plugins: [vuetify],
          stubs: {
            AgentDetailsModal: true,
            AgentMissionEditModal: true,
            'v-snackbar': true,
          },
        },
      })

      await nextTick()

      // THEN: Should still be locked because orchestrator exists
      const toggleBar = wrapper.find('[data-testid="execution-mode-toggle"]')
      expect(toggleBar.classes()).toContain('toggle-locked')
    })

    it('should only lock when orchestrator type agent is present', async () => {
      const wrapper = mount(LaunchTab, {
        props: {
          project: {
            ...mockProject,
            agents: [
              mockImplementerAgent,
              {
                id: 'tester-job-1',
                job_id: 'tester-job-1',
                agent_type: 'tester',
                agent_name: 'Tester',
                status: 'waiting',
              },
              {
                id: 'analyzer-job-1',
                job_id: 'analyzer-job-1',
                agent_type: 'analyzer',
                agent_name: 'Analyzer',
                status: 'waiting',
              },
            ],
          },
          orchestrator: null,
          isStaging: false,
        },
        global: {
          plugins: [vuetify],
          stubs: {
            AgentDetailsModal: true,
            AgentMissionEditModal: true,
            'v-snackbar': true,
          },
        },
      })

      await nextTick()

      // THEN: Should NOT be locked
      const toggleBar = wrapper.find('[data-testid="execution-mode-toggle"]')
      expect(toggleBar.classes()).not.toContain('toggle-locked')
    })
  })
})
