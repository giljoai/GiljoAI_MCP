import { describe, it, expect, beforeEach, vi } from 'vitest'
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

describe('LaunchTab Component - Simplified UI Production Tests', () => {
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
    agent_type: 'orchestrator',
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

    vi.clearAllMocks()
  })

  describe('UI Simplification - No Metrics Dialog', () => {
    it('should render without metrics dialog in DOM', () => {
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

      // Key validation: no metrics dialog exists
      expect(wrapper.vm.$el.innerHTML).not.toContain('Token Efficiency Breakdown')
      expect(wrapper.vm.$el.innerHTML).not.toContain('Thin Client Architecture Benefits')
    })

    it('should have Stage Project button ready to click', () => {
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
  })

  describe('Simplified Button Behavior', () => {
    it('should call API to generate thin prompt', async () => {
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

      // Spy on clipboard to prevent errors
      vi.spyOn(document, 'execCommand').mockReturnValue(true)

      await wrapper.find('button').trigger('click')
      await wrapper.vm.$nextTick()

      // Verify API was called
      expect(api.prompts.staging).toHaveBeenCalledWith(mockProject.id, {
        tool: 'claude-code',
      })
    })

    it('should show loading state during API call', async () => {
      api.prompts.staging.mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve(mockPromptResponse), 50)),
      )

      vi.spyOn(document, 'execCommand').mockReturnValue(true)

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

      // Click and immediately check loading state
      const clickPromise = wrapper.find('button').trigger('click')
      expect(wrapper.vm.loadingStageProject).toBe(true)

      // Wait for completion
      await clickPromise
      await new Promise((resolve) => setTimeout(resolve, 100))

      // After completion, loading should be false
      expect(wrapper.vm.loadingStageProject).toBe(false)
    })

    it('should show success toast after copy', async () => {
      api.prompts.staging.mockResolvedValue(mockPromptResponse)
      vi.spyOn(document, 'execCommand').mockReturnValue(true)

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
      expect(wrapper.vm.toastMessage).toContain('copied to clipboard')
    })

    it('should emit stage-project event', async () => {
      api.prompts.staging.mockResolvedValue(mockPromptResponse)
      vi.spyOn(document, 'execCommand').mockReturnValue(true)

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

  describe('Error Handling', () => {
    it('should handle API errors gracefully', async () => {
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

      expect(wrapper.vm.showToast).toBe(true)
      expect(wrapper.vm.toastMessage).toContain('Staging failed')
      expect(wrapper.vm.loadingStageProject).toBe(false)
    })
  })

  describe('State Management', () => {
    it('should reset state when resetStaging is called', () => {
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

      // Set some state
      wrapper.vm.missionText = 'Test mission'
      wrapper.vm.missionError = 'Test error'
      wrapper.vm.agents.push({ id: 'agent-1', agent_type: 'Tester' })

      // Reset
      wrapper.vm.resetStaging()

      // Verify state is cleared
      expect(wrapper.vm.missionText).toBe('')
      expect(wrapper.vm.missionError).toBe(null)
      expect(wrapper.vm.agents).toHaveLength(0)
      expect(wrapper.vm.stagingInProgress).toBe(false)
    })
  })
})
