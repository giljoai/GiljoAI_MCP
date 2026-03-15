/**
 * LaunchTab.0333.spec.js
 *
 * Handover 0333: Execution Mode Toggle Migration (Phase 1)
 *
 * Tests for moving the execution mode toggle from JobsTab to LaunchTab.
 *
 * Following TDD: Write tests FIRST, implement to pass tests.
 *
 * Requirements:
 * 1. Toggle appears on LaunchTab BEFORE the three-panels section
 * 2. Toggle default is Multi-Terminal mode
 * 3. Toggle persists to backend via API call
 * 4. Toggle selection is maintained during session
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

// Mock API service - no top-level variable reference
vi.mock('@/services/api', () => ({
  api: {
    projects: {
      update: vi.fn()
    }
  }
}))

// Import API after mock
import { api } from '@/services/api'

// Execution mode toggle was removed from LaunchTab. It is now controlled via
// project.execution_mode prop read-only in JobsTab (Handover 0333 Phase 3).
// These tests reference data-testid="execution-mode-toggle", toggleExecutionMode(),
// and usingClaudeCodeSubagents which no longer exist in LaunchTab.
describe.skip('LaunchTab Execution Mode Toggle (0333 Phase 1) - REMOVED FEATURE', () => {
  const mockProject = {
    id: 'project-123',
    project_id: 'project-123',
    name: 'Test Project',
    mission: 'Test project mission',
    description: 'Test project description',
    execution_mode: 'multi_terminal',
    agents: [],
  }

  beforeEach(() => {
    mockWebSocketOn = vi.fn()
    mockWebSocketOff = vi.fn()
    mockShowToast = vi.fn()
    vi.clearAllMocks()
  })

  describe('Toggle UI Rendering', () => {
    it('should render execution mode toggle element with test ID', async () => {
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

      // Check that the execution mode toggle exists
      const executionToggle = wrapper.find('[data-testid="execution-mode-toggle"]')
      expect(executionToggle.exists()).toBe(true)
    })

    it('should render toggle BEFORE the three-panels section', async () => {
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

      const html = wrapper.html()
      const toggleIndex = html.indexOf('data-testid="execution-mode-toggle"')
      const panelsIndex = html.indexOf('three-panels')

      expect(toggleIndex).toBeGreaterThan(-1)
      expect(panelsIndex).toBeGreaterThan(-1)
      expect(toggleIndex).toBeLessThan(panelsIndex)
    })
  })

  describe('Toggle Default State', () => {
    it('should default indicator to inactive (Multi-Terminal mode)', async () => {
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

      const toggleIndicator = wrapper.find('[data-testid="execution-mode-indicator"]')
      expect(toggleIndicator.classes()).not.toContain('active')
    })

    it('should set indicator to active when execution_mode is claude_code_cli', async () => {
      const wrapper = mount(LaunchTab, {
        props: {
          project: {
            ...mockProject,
            execution_mode: 'claude_code_cli',
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

      const toggleIndicator = wrapper.find('[data-testid="execution-mode-indicator"]')
      expect(toggleIndicator.classes()).toContain('active')
    })
  })

  describe('Toggle Interaction', () => {
    it('should have toggleExecutionMode method', async () => {
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

      expect(typeof wrapper.vm.toggleExecutionMode).toBe('function')
    })

    it('should toggle mode when called', async () => {
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

      // Initially Multi-Terminal
      expect(wrapper.vm.usingClaudeCodeSubagents).toBe(false)

      // Call toggle
      await wrapper.vm.toggleExecutionMode()
      await flushPromises()

      // Should change to Claude Code CLI mode
      expect(wrapper.vm.usingClaudeCodeSubagents).toBe(true)

      // API should be called
      expect(api.projects.update).toHaveBeenCalledWith(
        'project-123',
        expect.objectContaining({
          execution_mode: 'claude_code_cli',
        })
      )
    })

    it('should show success toast when toggle succeeds', async () => {
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

      await wrapper.vm.toggleExecutionMode()
      await flushPromises()

      expect(mockShowToast).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'info',
        })
      )
    })

    it('should revert toggle state if API fails', async () => {
      api.projects.update = vi.fn().mockRejectedValue(new Error('API Error'))

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

      const initialState = wrapper.vm.usingClaudeCodeSubagents

      await wrapper.vm.toggleExecutionMode()
      await flushPromises()

      // Should revert to initial state
      expect(wrapper.vm.usingClaudeCodeSubagents).toBe(initialState)

      // Error toast should be shown
      expect(mockShowToast).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'error',
        })
      )
    })
  })

  describe('Toggle Persistence', () => {
    it('should sync toggle state when project prop changes', async () => {
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

      // Initial state
      expect(wrapper.vm.usingClaudeCodeSubagents).toBe(false)

      // Update project to Claude Code CLI mode
      await wrapper.setProps({
        project: {
          ...mockProject,
          execution_mode: 'claude_code_cli',
        },
      })
      await nextTick()

      // Toggle should sync
      expect(wrapper.vm.usingClaudeCodeSubagents).toBe(true)
    })
  })
})
