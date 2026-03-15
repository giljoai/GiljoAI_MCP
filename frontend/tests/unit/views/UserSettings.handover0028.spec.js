/**
 * Test suite for UserSettings.vue - Handover 0028 Enhancements
 *
 * Post-refactor: The UserSettings component was restructured significantly:
 * - Tab system uses v-btn-toggle with values: startup, notifications, agents, context, api-keys, integrations
 * - The old 'api' tab with sub-tabs (api-keys, mcp-config, integrations) was split into
 *   separate top-level tabs: 'api-keys' and 'integrations'
 * - No apiSubTab state exists
 * - No showManualConfigDialog or openManualConfig methods
 * - Serena toggle is delegated to SerenaIntegrationCard sub-component
 * - Default tab is 'startup' (not 'general')
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { createPinia, setActivePinia } from 'pinia'
import UserSettings from '@/views/UserSettings.vue'

// Mock components
vi.mock('@/components/TemplateManager.vue', () => ({
  default: { template: '<div data-test="template-manager-mock">Template Manager</div>' }
}))

vi.mock('@/components/ApiKeyManager.vue', () => ({
  default: { template: '<div data-test="api-key-manager-mock">API Key Manager</div>' }
}))

vi.mock('@/components/ClaudeCodeExport.vue', () => ({
  default: { template: '<div data-test="claude-code-export-mock">Claude Code Export</div>' }
}))

vi.mock('@/components/SlashCommandSetup.vue', () => ({
  default: { template: '<div data-test="slash-command-setup-mock">Slash Command Setup</div>' }
}))

vi.mock('@/components/GitAdvancedSettingsDialog.vue', () => ({
  default: { template: '<div data-test="git-advanced-mock">Git Advanced</div>' }
}))

vi.mock('@/components/settings/ContextPriorityConfig.vue', () => ({
  default: { template: '<div data-test="context-priority-mock">Context Priority Config</div>' }
}))

vi.mock('@/components/settings/StartupQuickStart.vue', () => ({
  default: { template: '<div data-test="startup-quickstart-mock">Startup Quick Start</div>' }
}))

vi.mock('@/components/settings/ProductIntroTour.vue', () => ({
  default: { template: '<div data-test="product-intro-tour-mock"></div>' }
}))

vi.mock('@/components/settings/integrations/McpIntegrationCard.vue', () => ({
  default: { template: '<div data-test="mcp-integration-mock">MCP Integration</div>' }
}))

vi.mock('@/components/settings/integrations/SerenaIntegrationCard.vue', () => ({
  default: { template: '<div data-test="serena-integration-mock" class="serena-toggle">Serena Integration</div>', props: ['enabled', 'loading'] }
}))

vi.mock('@/components/settings/integrations/GitIntegrationCard.vue', () => ({
  default: { template: '<div data-test="git-integration-mock">Git Integration</div>', props: ['enabled', 'config', 'loading'] }
}))

vi.mock('@/composables/useWebSocket', () => ({
  useWebSocketV2: () => ({
    on: vi.fn(),
    off: vi.fn(),
  }),
}))

vi.mock('@/stores/settings', () => ({
  useSettingsStore: () => ({
    loadSettings: vi.fn().mockResolvedValue(undefined),
    updateSettings: vi.fn().mockResolvedValue(undefined),
    settings: { notifications: {} },
  }),
}))

// Mock services
vi.mock('@/services/setupService', () => ({
  default: {
    getSerenaStatus: vi.fn().mockResolvedValue({ enabled: false }),
    toggleSerena: vi.fn().mockResolvedValue({ success: true, enabled: true }),
    getGitSettings: vi.fn().mockResolvedValue({ enabled: false, use_in_prompts: false, include_commit_history: true, max_commits: 50, branch_strategy: 'main' }),
    toggleGit: vi.fn().mockResolvedValue({ enabled: false }),
    updateGitSettings: vi.fn().mockResolvedValue({ settings: {} }),
  }
}))

describe('UserSettings.vue - Handover 0028 API & Integrations Tab', () => {
  let vuetify
  let router
  let pinia
  let wrapper

  beforeEach(() => {
    // Setup Vuetify
    vuetify = createVuetify({
      components,
      directives
    })

    // Setup Pinia
    pinia = createPinia()
    setActivePinia(pinia)

    // Setup Router
    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/settings', name: 'UserSettings', component: UserSettings }
      ]
    })
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
    vi.clearAllMocks()
  })

  describe('Tab Presence', () => {
    it('renders API Keys tab', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      const html = wrapper.html()
      expect(html).toContain('API Keys')
    })

    it('renders Integrations tab', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      const html = wrapper.html()
      expect(html).toContain('Integrations')
    })
  })

  describe('API Keys Tab Content', () => {
    it('renders ApiKeyManager component in API Keys tab', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'api-keys'
      await wrapper.vm.$nextTick()

      const apiKeyManager = wrapper.find('[data-test="api-key-manager-mock"]')
      expect(apiKeyManager.exists()).toBe(true)
    })

  })

  describe('Integrations Tab - Serena Toggle', () => {
    it('displays Serena integration section in Integrations tab', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'integrations'
      await wrapper.vm.$nextTick()

      const serenaCard = wrapper.find('[data-test="serena-integration-mock"]')
      expect(serenaCard.exists()).toBe(true)
    })

    it('loads Serena status on component mount', async () => {
      const setupService = await import('@/services/setupService')

      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      await wrapper.vm.$nextTick()

      expect(setupService.default.getSerenaStatus).toHaveBeenCalled()
    })

    it('calls toggleSerena when invoked', async () => {
      const setupService = await import('@/services/setupService')

      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'integrations'
      await wrapper.vm.$nextTick()

      // Toggle Serena
      await wrapper.vm.toggleSerena(true)

      expect(setupService.default.toggleSerena).toHaveBeenCalledWith(true)
    })

    it('updates serenaEnabled state after successful toggle', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'integrations'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.serenaEnabled).toBe(false)

      await wrapper.vm.toggleSerena(true)
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.serenaEnabled).toBe(true)
    })

    it('shows loading state while toggling Serena', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'integrations'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.toggling).toBe(false)

      const togglePromise = wrapper.vm.toggleSerena(true)
      expect(wrapper.vm.toggling).toBe(true)

      await togglePromise
      expect(wrapper.vm.toggling).toBe(false)
    })
  })

  describe('Tab Navigation State', () => {
    it('defaults to startup tab on load', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      expect(wrapper.vm.activeTab).toBe('startup')
    })

    it('can switch to integrations tab', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'integrations'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.activeTab).toBe('integrations')
    })

    it('can switch between tabs', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'api-keys'
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.activeTab).toBe('api-keys')

      wrapper.vm.activeTab = 'integrations'
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.activeTab).toBe('integrations')

      wrapper.vm.activeTab = 'notifications'
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.activeTab).toBe('notifications')
    })
  })

  describe('Query Parameter Support', () => {
    it('opens integrations tab if tab=integrations in query string', async () => {
      router.push('/settings?tab=integrations')
      await router.isReady()

      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      await wrapper.vm.$nextTick()

      expect(wrapper.vm.activeTab).toBe('integrations')
    })
  })

  describe('Error Handling', () => {
    it('handles Serena status check failure gracefully', async () => {
      const setupService = await import('@/services/setupService')
      setupService.default.getSerenaStatus.mockRejectedValueOnce(new Error('Network error'))

      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      await wrapper.vm.$nextTick()

      // Should default to false on error
      expect(wrapper.vm.serenaEnabled).toBe(false)
    })

    it('reverts Serena toggle on failure', async () => {
      const setupService = await import('@/services/setupService')
      setupService.default.toggleSerena.mockResolvedValueOnce({ success: false, message: 'Failed' })

      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'integrations'
      await wrapper.vm.$nextTick()

      wrapper.vm.serenaEnabled = false
      await wrapper.vm.toggleSerena(true)

      // Should revert to false on failure
      expect(wrapper.vm.serenaEnabled).toBe(false)
    })
  })

  describe('Accessibility', () => {
    it('API Keys tab has proper icon and text', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      const html = wrapper.html()
      expect(html).toContain('API Keys')
      expect(html).toContain('mdi-key-variant')
    })

    it('Integrations tab has proper icon and text', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      const html = wrapper.html()
      expect(html).toContain('Integrations')
      expect(html).toContain('mdi-puzzle')
    })

  })
})
