import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createVuetify } from 'vuetify'
import LaunchTab from '@/components/projects/LaunchTab.vue'
import { useUserStore } from '@/stores/user'
import api from '@/services/api'

// Mock API service
vi.mock('@/services/api', () => ({
  default: {
    prompts: {
      staging: vi.fn(),
    },
  },
}))

// Mock WebSocket composable
vi.mock('@/composables/useWebSocket', () => ({
  useWebSocket: () => ({
    on: vi.fn(),
    off: vi.fn(),
    emit: vi.fn(),
    disconnect: vi.fn(),
  }),
}))

// Mock AgentCardEnhanced component
vi.mock('@/components/projects/AgentCardEnhanced.vue', () => ({
  default: {
    name: 'AgentCardEnhanced',
    template: '<div class="agent-card-mock"><slot name="actions" /></div>',
    props: ['agent', 'mode', 'isOrchestrator', 'instanceNumber'],
    emits: ['edit-mission'],
  },
}))

describe('LaunchTab Component - Simplified UI (No Dialog)', () => {
  let pinia
  let vuetify
  let userStore

  const mockProject = {
    id: 'proj-test-123',
    name: 'Test Project',
    description: 'A test project for staging',
    status: 'active',
    product_id: 'prod-1',
  }

  const mockOrchestrator = {
    job_id: 'orch-uuid-12345',
    agent_display_name: 'orchestrator',
    agent_name: 'Test Orchestrator',
    mission: 'Test mission',
    status: 'waiting',
    progress: 0,
  }

  const mockPromptResponse = {
    data: {
      prompt: 'You are an orchestrator...\nTask: Build the project\n...',
      estimated_prompt_tokens: 450,
      orchestrator_id: 'orch-uuid-12345',
      project_name: 'Test Project',
      mcp_tool_name: 'get_orchestrator_instructions',
      instructions_stored: true,
      thin_client: true,
    },
  }

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vuetify = createVuetify()

    userStore = useUserStore()
    userStore.currentUser = {
      id: 'user-1',
      username: 'testuser',
      tenant_key: 'tenant-123',
    }

    // Reset mocks
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Component Rendering', () => {
    it('should render the Stage Project button in initial state', () => {
      const wrapper = mount(LaunchTab, {
        props: {
          project: mockProject,
          orchestrator: mockOrchestrator,
          isStaging: false,
        },
        global: {
          plugins: [pinia, vuetify],
          stubs: {
            AgentCardEnhanced: true,
            VIcon: true,
            VBtn: true,
            VCard: true,
            VCardTitle: true,
            VCardText: true,
            VDivider: true,
            VRow: true,
            VCol: true,
            VSnackbar: true,
            VDialog: true,
            VAlert: true,
            VChip: true,
            VSpacer: true,
            VProgressCircular: true,
            VList: true,
            VListItem: true,
            VListItemTitle: true,
            VCardActions: true,
          },
        },
      })

      expect(wrapper.find('button').exists()).toBe(true)
      expect(wrapper.text()).toContain('Stage Project')
    })

    it('should not render the metrics dialog in simplified UI', () => {
      const wrapper = mount(LaunchTab, {
        props: {
          project: mockProject,
          orchestrator: mockOrchestrator,
          isStaging: false,
        },
        global: {
          plugins: [pinia, vuetify],
          stubs: {
            AgentCardEnhanced: true,
            VIcon: true,
            VBtn: true,
            VCard: true,
            VCardTitle: true,
            VCardText: true,
            VDivider: true,
            VRow: true,
            VCol: true,
            VSnackbar: true,
            VDialog: true,
            VAlert: true,
            VChip: true,
            VSpacer: true,
            VProgressCircular: true,
            VList: true,
            VListItem: true,
            VListItemTitle: true,
            VCardActions: true,
          },
        },
      })

      // The simplified version should NOT have a metrics dialog
      // Check that token stats and educational content don't exist
      expect(wrapper.text()).not.toContain('Token Efficiency Breakdown')
      expect(wrapper.text()).not.toContain('Thin Client Architecture Benefits')
      expect(wrapper.text()).not.toContain('context prioritization and orchestration')
    })

    it('should show project description in middle panel', () => {
      const wrapper = mount(LaunchTab, {
        props: {
          project: mockProject,
          orchestrator: mockOrchestrator,
          isStaging: false,
        },
        global: {
          plugins: [pinia, vuetify],
          stubs: {
            AgentCardEnhanced: true,
            VIcon: true,
            VBtn: true,
            VCard: true,
            VCardTitle: true,
            VCardText: true,
            VDivider: true,
            VRow: true,
            VCol: true,
            VSnackbar: true,
            VDialog: true,
            VAlert: true,
            VChip: true,
            VSpacer: true,
            VProgressCircular: true,
            VList: true,
            VListItem: true,
            VListItemTitle: true,
            VCardActions: true,
          },
        },
      })

      expect(wrapper.text()).toContain('A test project for staging')
    })
  })

  describe('Stage Project Button - Simplified Flow', () => {
    beforeEach(() => {
      // Setup clipboard mock for all tests in this suite
      Object.defineProperty(navigator, 'clipboard', {
        value: {
          writeText: vi.fn().mockResolvedValue(undefined),
        },
        configurable: true,
      })
    })

    it('should call API and copy prompt on button click', async () => {
      api.prompts.staging.mockResolvedValue(mockPromptResponse)

      const wrapper = mount(LaunchTab, {
        props: {
          project: mockProject,
          orchestrator: mockOrchestrator,
          isStaging: false,
        },
        global: {
          plugins: [pinia, vuetify],
          stubs: {
            AgentCardEnhanced: true,
            VIcon: true,
            VBtn: true,
            VCard: true,
            VCardTitle: true,
            VCardText: true,
            VDivider: true,
            VRow: true,
            VCol: true,
            VSnackbar: true,
            VDialog: true,
            VAlert: true,
            VChip: true,
            VSpacer: true,
            VProgressCircular: true,
            VList: true,
            VListItem: true,
            VListItemTitle: true,
            VCardActions: true,
          },
        },
      })

      await wrapper.find('button').trigger('click')
      await wrapper.vm.$nextTick()

      expect(api.prompts.staging).toHaveBeenCalledWith(mockProject.id, {
        tool: 'claude-code',
      })
    })

    it('should show success toast when clipboard copy succeeds', async () => {
      api.prompts.staging.mockResolvedValue(mockPromptResponse)

      Object.assign(navigator, {
        clipboard: {
          writeText: vi.fn().mockResolvedValue(undefined),
        },
      })

      const wrapper = mount(LaunchTab, {
        props: {
          project: mockProject,
          orchestrator: mockOrchestrator,
          isStaging: false,
        },
        global: {
          plugins: [pinia, vuetify],
          stubs: {
            AgentCardEnhanced: true,
            VIcon: true,
            VBtn: true,
            VCard: true,
            VCardTitle: true,
            VCardText: true,
            VDivider: true,
            VRow: true,
            VCol: true,
            VSnackbar: true,
            VDialog: true,
            VAlert: true,
            VChip: true,
            VSpacer: true,
            VProgressCircular: true,
            VList: true,
            VListItem: true,
            VListItemTitle: true,
            VCardActions: true,
          },
        },
      })

      await wrapper.find('button').trigger('click')
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.toastMessage).toContain('Orchestrator prompt copied to clipboard')
      expect(wrapper.vm.showToast).toBe(true)
    })

    it('should show error toast on API failure', async () => {
      const error = new Error('Failed to generate prompt')
      api.prompts.staging.mockRejectedValue(error)

      const wrapper = mount(LaunchTab, {
        props: {
          project: mockProject,
          orchestrator: mockOrchestrator,
          isStaging: false,
        },
        global: {
          plugins: [pinia, vuetify],
          stubs: {
            AgentCardEnhanced: true,
            VIcon: true,
            VBtn: true,
            VCard: true,
            VCardTitle: true,
            VCardText: true,
            VDivider: true,
            VRow: true,
            VCol: true,
            VSnackbar: true,
            VDialog: true,
            VAlert: true,
            VChip: true,
            VSpacer: true,
            VProgressCircular: true,
            VList: true,
            VListItem: true,
            VListItemTitle: true,
            VCardActions: true,
          },
        },
      })

      await wrapper.find('button').trigger('click')
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.showToast).toBe(true)
      expect(wrapper.vm.toastMessage).toContain('Staging failed')
    })

    it('should emit stage-project event after successful copy', async () => {
      api.prompts.staging.mockResolvedValue(mockPromptResponse)

      Object.assign(navigator, {
        clipboard: {
          writeText: vi.fn().mockResolvedValue(undefined),
        },
      })

      const wrapper = mount(LaunchTab, {
        props: {
          project: mockProject,
          orchestrator: mockOrchestrator,
          isStaging: false,
        },
        global: {
          plugins: [pinia, vuetify],
          stubs: {
            AgentCardEnhanced: true,
            VIcon: true,
            VBtn: true,
            VCard: true,
            VCardTitle: true,
            VCardText: true,
            VDivider: true,
            VRow: true,
            VCol: true,
            VSnackbar: true,
            VDialog: true,
            VAlert: true,
            VChip: true,
            VSpacer: true,
            VProgressCircular: true,
            VList: true,
            VListItem: true,
            VListItemTitle: true,
            VCardActions: true,
          },
        },
      })

      await wrapper.find('button').trigger('click')
      await wrapper.vm.$nextTick()

      expect(wrapper.emitted('stage-project')).toBeTruthy()
    })
  })

  describe('Clipboard Copy - Cross-Platform Support', () => {
    it('should attempt to copy prompt to clipboard', async () => {
      api.prompts.staging.mockResolvedValue(mockPromptResponse)

      const execCommandSpy = vi.spyOn(document, 'execCommand').mockReturnValue(true)

      const wrapper = mount(LaunchTab, {
        props: {
          project: mockProject,
          orchestrator: mockOrchestrator,
          isStaging: false,
        },
        global: {
          plugins: [pinia, vuetify],
          stubs: {
            AgentCardEnhanced: true,
            VIcon: true,
            VBtn: true,
            VCard: true,
            VCardTitle: true,
            VCardText: true,
            VDivider: true,
            VRow: true,
            VCol: true,
            VSnackbar: true,
            VDialog: true,
            VAlert: true,
            VChip: true,
            VSpacer: true,
            VProgressCircular: true,
            VList: true,
            VListItem: true,
            VListItemTitle: true,
            VCardActions: true,
          },
        },
      })

      await wrapper.find('button').trigger('click')
      await wrapper.vm.$nextTick()

      // Should show success
      expect(wrapper.vm.showToast).toBe(true)
      expect(execCommandSpy).toHaveBeenCalledWith('copy')

      execCommandSpy.mockRestore()
    })
  })

  describe('Loading States', () => {
    beforeEach(() => {
      Object.defineProperty(navigator, 'clipboard', {
        value: {
          writeText: vi.fn().mockResolvedValue(undefined),
        },
        configurable: true,
      })
    })

    it('should set loading state during API call', async () => {
      api.prompts.staging.mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve(mockPromptResponse), 50)),
      )

      const wrapper = mount(LaunchTab, {
        props: {
          project: mockProject,
          orchestrator: mockOrchestrator,
          isStaging: false,
        },
        global: {
          plugins: [pinia, vuetify],
          stubs: {
            AgentCardEnhanced: true,
            VIcon: true,
            VBtn: true,
            VCard: true,
            VCardTitle: true,
            VCardText: true,
            VDivider: true,
            VRow: true,
            VCol: true,
            VSnackbar: true,
            VDialog: true,
            VAlert: true,
            VChip: true,
            VSpacer: true,
            VProgressCircular: true,
            VList: true,
            VListItem: true,
            VListItemTitle: true,
            VCardActions: true,
          },
        },
      })

      const button = wrapper.find('button')
      button.trigger('click')

      // Should be loading immediately after click
      expect(wrapper.vm.loadingStageProject).toBe(true)

      // Wait for API response
      await new Promise((resolve) => setTimeout(resolve, 100))

      // Should be done loading after response
      expect(wrapper.vm.loadingStageProject).toBe(false)
    })
  })

  describe('Error Handling', () => {
    it('should handle API failure gracefully', async () => {
      const error = new Error('Network error')
      api.prompts.staging.mockRejectedValue(error)

      const wrapper = mount(LaunchTab, {
        props: {
          project: mockProject,
          orchestrator: mockOrchestrator,
          isStaging: false,
        },
        global: {
          plugins: [pinia, vuetify],
          stubs: {
            AgentCardEnhanced: true,
            VIcon: true,
            VBtn: true,
            VCard: true,
            VCardTitle: true,
            VCardText: true,
            VDivider: true,
            VRow: true,
            VCol: true,
            VSnackbar: true,
            VDialog: true,
            VAlert: true,
            VChip: true,
            VSpacer: true,
            VProgressCircular: true,
            VList: true,
            VListItem: true,
            VListItemTitle: true,
            VCardActions: true,
          },
        },
      })

      await wrapper.find('button').trigger('click')
      await wrapper.vm.$nextTick()

      // Should set error state
      expect(wrapper.vm.missionError).toBeTruthy()
      // Should show toast
      expect(wrapper.vm.showToast).toBe(true)
      expect(wrapper.vm.toastMessage).toContain('Staging failed')
    })

    it('should set loading state to false after error', async () => {
      api.prompts.staging.mockRejectedValue(new Error('API Error'))

      const wrapper = mount(LaunchTab, {
        props: {
          project: mockProject,
          orchestrator: mockOrchestrator,
          isStaging: false,
        },
        global: {
          plugins: [pinia, vuetify],
          stubs: {
            AgentCardEnhanced: true,
            VIcon: true,
            VBtn: true,
            VCard: true,
            VCardTitle: true,
            VCardText: true,
            VDivider: true,
            VRow: true,
            VCol: true,
            VSnackbar: true,
            VDialog: true,
            VAlert: true,
            VChip: true,
            VSpacer: true,
            VProgressCircular: true,
            VList: true,
            VListItem: true,
            VListItemTitle: true,
            VCardActions: true,
          },
        },
      })

      await wrapper.find('button').trigger('click')
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.loadingStageProject).toBe(false)
    })
  })

  describe('State Reset on Cancel', () => {
    it('should reset all state when canceling staging', async () => {
      const wrapper = mount(LaunchTab, {
        props: {
          project: mockProject,
          orchestrator: mockOrchestrator,
          isStaging: true,
        },
        global: {
          plugins: [pinia, vuetify],
          stubs: {
            AgentCardEnhanced: true,
            VIcon: true,
            VBtn: true,
            VCard: true,
            VCardTitle: true,
            VCardText: true,
            VDivider: true,
            VRow: true,
            VCol: true,
            VSnackbar: true,
            VDialog: true,
            VAlert: true,
            VChip: true,
            VSpacer: true,
            VProgressCircular: true,
            VList: true,
            VListItem: true,
            VListItemTitle: true,
            VCardActions: true,
          },
        },
      })

      // Set some state
      wrapper.vm.missionText = 'Test mission'
      wrapper.vm.agents.push({ id: 'agent-1', agent_display_name: 'Tester' })
      wrapper.vm.missionError = 'Some error'

      // Reset
      wrapper.vm.resetStaging()

      expect(wrapper.vm.missionText).toBe('')
      expect(wrapper.vm.agents).toHaveLength(0)
      expect(wrapper.vm.missionError).toBe(null)
      expect(wrapper.vm.stagingInProgress).toBe(false)
    })
  })
})
