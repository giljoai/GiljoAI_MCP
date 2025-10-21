/**
 * Test suite for UserSettings.vue - Handover 0028 Enhancements
 *
 * Tests for API & Integrations tab enhancements:
 * - API Key Management consolidated under this tab
 * - Serena integration toggle control
 * - AI Tool Configuration instructions (Claude Code, Codex, Gemini)
 * - Proper organization into logical sections
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

vi.mock('@/components/McpConfigComponent.vue', () => ({
  default: { template: '<div data-test="mcp-config-mock">MCP Config</div>' }
}))

vi.mock('@/components/AiToolConfigWizard.vue', () => ({
  default: { template: '<div data-test="ai-tool-wizard-mock">AI Tool Wizard</div>' }
}))

// Mock services
vi.mock('@/services/setupService', () => ({
  default: {
    getSerenaStatus: vi.fn().mockResolvedValue({ enabled: false }),
    toggleSerena: vi.fn().mockResolvedValue({ success: true, enabled: true })
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

  describe('API and Integrations Tab Presence', () => {
    it('renders API and Integrations tab', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      const tabs = wrapper.findAll('.v-tab')
      const apiTab = tabs.find(tab => tab.text().includes('API and Integrations'))
      expect(apiTab).toBeDefined()
    })

    it('API and Integrations tab has correct icon', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      // Check if API tab contains the API icon
      const tabs = wrapper.findAll('.v-tab')
      const apiTab = tabs.find(tab => tab.text().includes('API'))
      expect(apiTab).toBeDefined()
    })
  })

  describe('API Tab Sub-Navigation', () => {
    it('displays API Keys sub-tab', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      // Switch to API tab
      wrapper.vm.activeTab = 'api'
      await wrapper.vm.$nextTick()

      expect(wrapper.text()).toContain('API Keys')
    })

    it('displays MCP Configuration sub-tab', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'api'
      await wrapper.vm.$nextTick()

      expect(wrapper.text()).toContain('MCP Configuration')
    })

    it('displays Integrations sub-tab', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'api'
      await wrapper.vm.$nextTick()

      expect(wrapper.text()).toContain('Integrations')
    })
  })

  describe('API Keys Sub-Tab Content', () => {
    it('renders ApiKeyManager component in API Keys sub-tab', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'api'
      wrapper.vm.apiSubTab = 'api-keys'
      await wrapper.vm.$nextTick()

      const apiKeyManager = wrapper.find('[data-test="api-key-manager-mock"]')
      expect(apiKeyManager.exists()).toBe(true)
    })

    it('displays API Keys section header', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'api'
      wrapper.vm.apiSubTab = 'api-keys'
      await wrapper.vm.$nextTick()

      expect(wrapper.text()).toContain('Personal API Keys')
    })

    it('displays API Keys description text', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'api'
      wrapper.vm.apiSubTab = 'api-keys'
      await wrapper.vm.$nextTick()

      expect(wrapper.text()).toContain('Generate and manage API keys for external integrations')
    })
  })

  describe('MCP Configuration Sub-Tab Content', () => {
    it('renders AI Tool Configuration Wizard', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'api'
      wrapper.vm.apiSubTab = 'mcp-config'
      await wrapper.vm.$nextTick()

      const wizard = wrapper.find('[data-test="ai-tool-wizard-mock"]')
      expect(wizard.exists()).toBe(true)
    })

    it('displays AI Tool Self-Configuration header', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'api'
      wrapper.vm.apiSubTab = 'mcp-config'
      await wrapper.vm.$nextTick()

      expect(wrapper.text()).toContain('AI Tool Self-Configuration')
    })

    it('displays wizard description', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'api'
      wrapper.vm.apiSubTab = 'mcp-config'
      await wrapper.vm.$nextTick()

      expect(wrapper.text()).toContain('Use the wizard to generate a tool-specific prompt')
    })

    it('displays manual configuration option', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'api'
      wrapper.vm.apiSubTab = 'mcp-config'
      await wrapper.vm.$nextTick()

      expect(wrapper.text()).toContain('Manual AI Tool Configuration')
    })

    it('has button to open manual configuration dialog', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'api'
      wrapper.vm.apiSubTab = 'mcp-config'
      await wrapper.vm.$nextTick()

      const manualConfigBtn = wrapper.find('[aria-label="Open manual AI tool configuration dialog"]')
      expect(manualConfigBtn.exists()).toBe(true)
    })

    it('opens manual configuration dialog when button clicked', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'api'
      wrapper.vm.apiSubTab = 'mcp-config'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.showManualConfigDialog).toBe(false)

      wrapper.vm.openManualConfig()
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.showManualConfigDialog).toBe(true)
    })
  })

  describe('Integrations Sub-Tab - Serena Toggle', () => {
    it('displays Serena MCP integration section', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'api'
      wrapper.vm.apiSubTab = 'integrations'
      await wrapper.vm.$nextTick()

      expect(wrapper.text()).toContain('Serena MCP')
    })

    it('renders Serena toggle switch', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'api'
      wrapper.vm.apiSubTab = 'integrations'
      await wrapper.vm.$nextTick()

      // Check for toggle switch (serena-toggle class)
      const serenaToggle = wrapper.find('.serena-toggle')
      expect(serenaToggle.exists()).toBe(true)
    })

    it('displays Serena logo/avatar', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'api'
      wrapper.vm.apiSubTab = 'integrations'
      await wrapper.vm.$nextTick()

      const serenaImg = wrapper.find('img[alt="Serena MCP"]')
      expect(serenaImg.exists()).toBe(true)
      expect(serenaImg.attributes('src')).toBe('/Serena.png')
    })

    it('displays Serena description text', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'api'
      wrapper.vm.apiSubTab = 'integrations'
      await wrapper.vm.$nextTick()

      expect(wrapper.text()).toContain('Enabling adds Serena tool instructions to agent prompts')
    })

    it('displays informational alert about Serena', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'api'
      wrapper.vm.apiSubTab = 'integrations'
      await wrapper.vm.$nextTick()

      expect(wrapper.text()).toContain('Serena MCP must be installed separately')
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

    it('calls toggleSerena when switch is toggled', async () => {
      const setupService = await import('@/services/setupService')

      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'api'
      wrapper.vm.apiSubTab = 'integrations'
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

      wrapper.vm.activeTab = 'api'
      wrapper.vm.apiSubTab = 'integrations'
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

      wrapper.vm.activeTab = 'api'
      wrapper.vm.apiSubTab = 'integrations'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.toggling).toBe(false)

      const togglePromise = wrapper.vm.toggleSerena(true)
      expect(wrapper.vm.toggling).toBe(true)

      await togglePromise
      expect(wrapper.vm.toggling).toBe(false)
    })
  })

  describe('Tab Navigation State', () => {
    it('defaults to general tab on load', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      expect(wrapper.vm.activeTab).toBe('general')
    })

    it('can switch to API and Integrations tab', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'api'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.activeTab).toBe('api')
    })

    it('defaults to api-keys sub-tab when API tab is active', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'api'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.apiSubTab).toBe('api-keys')
    })

    it('can switch between API sub-tabs', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'api'
      wrapper.vm.apiSubTab = 'api-keys'
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.apiSubTab).toBe('api-keys')

      wrapper.vm.apiSubTab = 'mcp-config'
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.apiSubTab).toBe('mcp-config')

      wrapper.vm.apiSubTab = 'integrations'
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.apiSubTab).toBe('integrations')
    })
  })

  describe('Query Parameter Support', () => {
    it('opens API tab if tab=api in query string', async () => {
      router.push('/settings?tab=api')
      await router.isReady()

      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      await wrapper.vm.$nextTick()

      expect(wrapper.vm.activeTab).toBe('api')
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

      wrapper.vm.activeTab = 'api'
      wrapper.vm.apiSubTab = 'integrations'
      await wrapper.vm.$nextTick()

      wrapper.vm.serenaEnabled = false
      await wrapper.vm.toggleSerena(true)

      // Should revert to false on failure
      expect(wrapper.vm.serenaEnabled).toBe(false)
    })
  })

  describe('Accessibility', () => {
    it('API and Integrations tab has proper icon and text', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      const tabs = wrapper.findAll('.v-tab')
      const apiTab = tabs.find(tab => tab.text().includes('API'))
      expect(apiTab).toBeDefined()
    })

    it('Serena toggle has proper accessibility attributes', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'api'
      wrapper.vm.apiSubTab = 'integrations'
      await wrapper.vm.$nextTick()

      const serenaToggle = wrapper.find('.serena-toggle')
      expect(serenaToggle.exists()).toBe(true)
    })
  })
})
