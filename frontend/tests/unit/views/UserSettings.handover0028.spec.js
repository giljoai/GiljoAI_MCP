/**
/**
 * Test suite for UserSettings.vue - Handover 0028 Enhancements
 *
 * Updated for FE-0023 (Settings IA cleanup):
 * - Tab values: connect, agents, context, notifications, startup
 * - 'Integrations' tab renamed to 'Connect'; ApiKeyManager folded into Connect
 *   as a compact "Credentials" section (no longer a peer tab named 'API Keys')
 * - Default tab is 'connect'
 * - Serena toggle still delegated to SerenaIntegrationCard sub-component
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

vi.mock('@/components/AgentExport.vue', () => ({
  default: { template: '<div data-test="agent-export-mock">Agent Export</div>' }
}))


vi.mock('@/components/settings/ContextPriorityConfig.vue', () => ({
  default: { template: '<div data-test="context-priority-mock">Context Priority Config</div>' }
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

  beforeEach(async () => {
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
        { path: '/', redirect: '/settings' },
        { path: '/settings', name: 'UserSettings', component: UserSettings }
      ]
    })
    await router.push('/settings')
    await router.isReady()
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
    vi.clearAllMocks()
  })

  describe('Tab Presence', () => {
    it('renders Connect tab', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      const html = wrapper.html()
      expect(html).toContain('Connect')
    })

    it('does NOT render API Keys as a peer tab (folded into Connect)', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      // No pill-toggle button labelled "API Keys".
      const pillButtons = wrapper.findAll('.pill-toggle')
      const labels = pillButtons.map(b => b.text().trim())
      expect(labels).not.toContain('API Keys')
    })
  })

  describe('Connect Tab - Credentials (folded ApiKeyManager)', () => {
    it('renders ApiKeyManager inside the Connect tab as the Credentials section', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'connect'
      await wrapper.vm.$nextTick()

      const apiKeyManager = wrapper.find('[data-test="api-key-manager-mock"]')
      expect(apiKeyManager.exists()).toBe(true)
    })
  })

  describe('Connect Tab - Serena Toggle', () => {
    it('displays Serena integration section in Connect tab', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'connect'
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

      wrapper.vm.activeTab = 'connect'
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

      wrapper.vm.activeTab = 'connect'
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

      wrapper.vm.activeTab = 'connect'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.toggling).toBe(false)

      const togglePromise = wrapper.vm.toggleSerena(true)
      expect(wrapper.vm.toggling).toBe(true)

      await togglePromise
      expect(wrapper.vm.toggling).toBe(false)
    })
  })

  describe('Tab Navigation State', () => {
    it('defaults to connect tab on load', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      expect(wrapper.vm.activeTab).toBe('connect')
    })

    it('can switch to connect tab', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'connect'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.activeTab).toBe('connect')
    })

    it('can switch between tabs', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'startup'
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.activeTab).toBe('startup')

      wrapper.vm.activeTab = 'connect'
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.activeTab).toBe('connect')

      wrapper.vm.activeTab = 'notifications'
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.activeTab).toBe('notifications')
    })
  })

  describe('Query Parameter Support (legacy redirects)', () => {
    it('normalizes legacy tab=integrations to connect', async () => {
      await router.push('/settings?tab=integrations')
      await router.isReady()

      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      // Wait for onMounted to process route.query.tab
      await wrapper.vm.$nextTick()
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.activeTab).toBe('connect')
    })

    it('normalizes legacy tab=api-keys to connect', async () => {
      await router.push('/settings?tab=api-keys')
      await router.isReady()

      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      await wrapper.vm.$nextTick()
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.activeTab).toBe('connect')
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

      wrapper.vm.activeTab = 'connect'
      await wrapper.vm.$nextTick()

      wrapper.vm.serenaEnabled = false
      await wrapper.vm.toggleSerena(true)

      // Should revert to false on failure
      expect(wrapper.vm.serenaEnabled).toBe(false)
    })
  })

  describe('Accessibility', () => {
    it('Connect tab has proper icon and text', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      const html = wrapper.html()
      expect(html).toContain('Connect')
      expect(html).toContain('mdi-puzzle')
    })

  })
})
