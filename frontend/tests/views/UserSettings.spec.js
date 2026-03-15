import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createVuetify } from 'vuetify'
import UserSettings from '@/views/UserSettings.vue'
import { useSettingsStore } from '@/stores/settings'
import api from '@/services/api'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

// Mock the API
vi.mock('@/services/api', () => ({
  default: {
    users: {
      getFieldToggleConfig: vi.fn(),
      updateFieldToggleConfig: vi.fn(),
      resetFieldToggleConfig: vi.fn(),
    },
    products: {
      getGitIntegration: vi.fn(() => Promise.resolve({ data: { enabled: false, commit_limit: 20, default_branch: 'main' } })),
      updateGitIntegration: vi.fn(() => Promise.resolve({ data: { enabled: true, commit_limit: 20, default_branch: 'main' } })),
    },
    settings: {
      get: vi.fn(),
      update: vi.fn(),
    },
  },
}))

// Mock setupService
vi.mock('@/services/setupService', () => ({
  default: {
    getSerenaStatus: vi.fn(() => Promise.resolve({ enabled: false })),
    toggleSerena: vi.fn(() => Promise.resolve({ success: true, enabled: false })),
    getSerenaConfig: vi.fn(() => Promise.resolve({
      use_in_prompts: true,
      tailor_by_mission: true,
      dynamic_catalog: true,
      prefer_ranges: true,
      max_range_lines: 180,
      context_halo: 12,
    })),
  },
}))

// Mock router
const mockRouter = {
  currentRoute: {
    value: { query: {} },
  },
  push: vi.fn(),
  replace: vi.fn(),
}

// Mock vue-router
vi.mock('vue-router', () => ({
  useRouter: () => mockRouter,
}))

// Mock WebSocket composable
vi.mock('@/composables/useWebSocket', () => ({
  useWebSocketV2: () => ({
    on: vi.fn(),
    off: vi.fn(),
  }),
}))

// Setup vuetify
const vuetify = createVuetify({
  components,
  directives,
})

describe('UserSettings.vue', () => {
  let wrapper

  beforeEach(() => {
    setActivePinia(createPinia())

    api.users.getFieldToggleConfig.mockResolvedValue({
      data: {
        version: '3.0',
        priorities: {
          product_core: { toggle: true },
          agent_templates: { toggle: true },
          vision_documents: { toggle: true },
        },
      },
    })

    api.settings.get.mockResolvedValue({
      data: {
        theme: 'dark',
        notifications: true,
      },
    })
  })

  // Helper function to mount component
  function mountComponent() {
    return mount(UserSettings, {
      global: {
        plugins: [createPinia(), vuetify],
        mocks: {
          $router: mockRouter,
        },
        stubs: {
          TemplateManager: true,
          ApiKeyManager: true,
          McpConfigComponent: true,
          AiToolConfigWizard: true,
          ClaudeCodeExport: true,
          SlashCommandSetup: true,
          SerenaAdvancedSettingsDialog: true,
          ContextPriorityConfig: true,
          StartupQuickStart: true,
          ProductIntroTour: true,
          GitAdvancedSettingsDialog: true,
          McpIntegrationCard: {
            name: 'McpIntegrationCard',
            template: '<div class="mcp-integration-card-stub"></div>',
          },
          SerenaIntegrationCard: {
            name: 'SerenaIntegrationCard',
            template: '<div class="serena-integration-card-stub"></div>',
            props: ['enabled', 'config', 'loading'],
            emits: ['update:enabled', 'openAdvanced'],
          },
          GitIntegrationCard: {
            name: 'GitIntegrationCard',
            template: '<div class="git-integration-card-stub"></div>',
            props: ['enabled', 'config', 'loading'],
            emits: ['update:enabled', 'save'],
          },
          draggable: {
            template: '<div><slot></slot></div>',
            props: ['modelValue', 'group', 'itemKey', 'handle'],
            emits: ['update:modelValue', 'change'],
          },
        },
      },
    })
  }

  describe('Integration Cards Extraction (Refactoring)', () => {
    it('should render McpIntegrationCard component in integrations tab', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()

      // Navigate to integrations tab
      wrapper.vm.activeTab = 'integrations'
      await wrapper.vm.$nextTick()

      // Check that the McpIntegrationCard stub is rendered
      const mcpCard = wrapper.findComponent({ name: 'McpIntegrationCard' })
      expect(mcpCard.exists()).toBe(true)
    })

    it('should render SerenaIntegrationCard component with correct props', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()

      // Navigate to integrations tab
      wrapper.vm.activeTab = 'integrations'
      await wrapper.vm.$nextTick()

      // Check that the SerenaIntegrationCard stub is rendered
      const serenaCard = wrapper.findComponent({ name: 'SerenaIntegrationCard' })
      expect(serenaCard.exists()).toBe(true)

      // Verify props are passed correctly
      expect(serenaCard.props('enabled')).toBe(false) // Initial state from mock
      expect(serenaCard.props('loading')).toBe(false)
    })

    it('should render GitIntegrationCard component with correct props', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()

      // Navigate to integrations tab
      wrapper.vm.activeTab = 'integrations'
      await wrapper.vm.$nextTick()

      // Check that the GitIntegrationCard stub is rendered
      const gitCard = wrapper.findComponent({ name: 'GitIntegrationCard' })
      expect(gitCard.exists()).toBe(true)

      // Verify props are passed correctly
      expect(gitCard.props('enabled')).toBe(false) // Initial state from mock
      expect(gitCard.props('loading')).toBe(false)
    })

    it('should handle SerenaIntegrationCard update:enabled event via toggleSerena', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()

      // Call the toggleSerena handler directly (this is what the component would call)
      await wrapper.vm.toggleSerena(true)
      await wrapper.vm.$nextTick()

      // The serenaEnabled state should be updated based on mock response
      // Mock returns success: true, enabled: false
      expect(wrapper.vm.serenaEnabled).toBe(false)
    })

    // Tests for openSerenaAdvanced, onGitToggle, and handleGitSave removed:
    // These functions were removed in the Handover 0277 integration card refactor.
    // SerenaIntegrationCard and GitIntegrationCard now manage their own state internally.

    it('should keep SlashCommandSetup and ClaudeCodeExport inline', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()

      // Navigate to integrations tab
      wrapper.vm.activeTab = 'integrations'
      await wrapper.vm.$nextTick()

      // These components should still be rendered (as stubs)
      const slashCommandSetup = wrapper.findComponent({ name: 'SlashCommandSetup' })
      const claudeCodeExport = wrapper.findComponent({ name: 'ClaudeCodeExport' })

      expect(slashCommandSetup.exists()).toBe(true)
      expect(claudeCodeExport.exists()).toBe(true)
    })
  })
})
