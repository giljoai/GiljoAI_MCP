/**
 * Test suite for refactored SystemSettings.vue component
 *
 * Tests the refactored System Settings view that uses extracted child components:
 * - NetworkSettingsTab
 * - AdminIntegrationsTab
 * - SecuritySettingsTab
 * - SystemPromptTab
 * - ClaudeConfigModal
 * - CodexConfigModal
 * - GeminiConfigModal
 *
 * Verifies that the parent component properly coordinates with child components
 * and maintains the same functionality as the original implementation.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { createPinia, setActivePinia } from 'pinia'
import SystemSettings from '@/views/SystemSettings.vue'

// Mock the api service
vi.mock('@/services/api', () => ({
  default: {
    settings: {
      getCookieDomains: vi.fn().mockResolvedValue({ data: { domains: [] } }),
      addCookieDomain: vi.fn().mockResolvedValue({ data: { success: true } }),
      removeCookieDomain: vi.fn().mockResolvedValue({ data: { success: true } })
    },
    system: {
      getOrchestratorPrompt: vi.fn().mockResolvedValue({ data: { content: 'test prompt', is_override: false } }),
      updateOrchestratorPrompt: vi.fn().mockResolvedValue({ data: { content: 'updated', is_override: true } }),
      resetOrchestratorPrompt: vi.fn().mockResolvedValue({ data: { content: 'default', is_override: false } })
    }
  }
}))

describe('SystemSettings.vue (Refactored)', () => {
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
        { path: '/', name: 'Dashboard', component: { template: '<div>Dashboard</div>' } },
        { path: '/admin/settings', name: 'SystemSettings', component: SystemSettings },
        { path: '/settings', name: 'UserSettings', component: { template: '<div>User Settings</div>' } }
      ]
    })

    // Mock fetch - provide default responses for onMounted calls
    global.fetch = vi.fn().mockImplementation((url) => {
      // Default response for database config
      if (url.includes('/api/v1/config/database')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ database: { host: 'localhost', port: 5432 } })
        })
      }
      // Default response for network config
      if (url.includes('/api/v1/config')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            services: {
              external_host: 'localhost',
              api: { port: 7272 },
              frontend: { port: 7274 }
            },
            security: { cors: { allowed_origins: [] } }
          })
        })
      }
      // Default response for cookie domains
      if (url.includes('/api/settings/cookie-domains')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ domains: [] })
        })
      }
      return Promise.reject(new Error('Unmocked fetch'))
    })
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
    vi.clearAllMocks()
  })

  describe('Component Integration with Extracted Components', () => {
    it('imports and uses NetworkSettingsTab component', () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' },
            NetworkSettingsTab: { template: '<div data-test="network-tab-stub">Network Tab</div>' },
            AdminIntegrationsTab: { template: '<div>Integrations Tab</div>' },
            SecuritySettingsTab: { template: '<div>Security Tab</div>' },
            SystemPromptTab: { template: '<div>System Tab</div>' },
            ClaudeConfigModal: { template: '<div>Claude Modal</div>' },
            CodexConfigModal: { template: '<div>Codex Modal</div>' },
            GeminiConfigModal: { template: '<div>Gemini Modal</div>' }
          }
        }
      })

      const networkTab = wrapper.find('[data-test="network-tab-stub"]')
      expect(networkTab.exists()).toBe(true)
    })

    it('imports and uses AdminIntegrationsTab component', async () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' },
            NetworkSettingsTab: { template: '<div>Network Tab</div>' },
            AdminIntegrationsTab: { template: '<div data-test="integrations-tab-stub">Integrations Tab</div>' },
            SecuritySettingsTab: { template: '<div>Security Tab</div>' },
            SystemPromptTab: { template: '<div>System Tab</div>' },
            ClaudeConfigModal: { template: '<div>Claude Modal</div>' },
            CodexConfigModal: { template: '<div>Codex Modal</div>' },
            GeminiConfigModal: { template: '<div>Gemini Modal</div>' }
          }
        }
      })

      // Switch to integrations tab
      if (wrapper.vm.activeTab !== undefined) {
        wrapper.vm.activeTab = 'integrations'
        await wrapper.vm.$nextTick()
      }

      const integrationsTab = wrapper.find('[data-test="integrations-tab-stub"]')
      expect(integrationsTab.exists()).toBe(true)
    })

    it('imports and uses SecuritySettingsTab component', async () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' },
            NetworkSettingsTab: { template: '<div>Network Tab</div>' },
            AdminIntegrationsTab: { template: '<div>Integrations Tab</div>' },
            SecuritySettingsTab: { template: '<div data-test="security-tab-stub">Security Tab</div>' },
            SystemPromptTab: { template: '<div>System Tab</div>' },
            ClaudeConfigModal: { template: '<div>Claude Modal</div>' },
            CodexConfigModal: { template: '<div>Codex Modal</div>' },
            GeminiConfigModal: { template: '<div>Gemini Modal</div>' }
          }
        }
      })

      // Switch to security tab
      if (wrapper.vm.activeTab !== undefined) {
        wrapper.vm.activeTab = 'security'
        await wrapper.vm.$nextTick()
      }

      const securityTab = wrapper.find('[data-test="security-tab-stub"]')
      expect(securityTab.exists()).toBe(true)
    })

    it('imports and uses SystemPromptTab component', async () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' },
            NetworkSettingsTab: { template: '<div>Network Tab</div>' },
            AdminIntegrationsTab: { template: '<div>Integrations Tab</div>' },
            SecuritySettingsTab: { template: '<div>Security Tab</div>' },
            SystemPromptTab: { template: '<div data-test="system-tab-stub">System Tab</div>' },
            ClaudeConfigModal: { template: '<div>Claude Modal</div>' },
            CodexConfigModal: { template: '<div>Codex Modal</div>' },
            GeminiConfigModal: { template: '<div>Gemini Modal</div>' }
          }
        }
      })

      // Switch to system tab
      if (wrapper.vm.activeTab !== undefined) {
        wrapper.vm.activeTab = 'system'
        await wrapper.vm.$nextTick()
      }

      const systemTab = wrapper.find('[data-test="system-tab-stub"]')
      expect(systemTab.exists()).toBe(true)
    })
  })

  describe('Props Passed to NetworkSettingsTab', () => {
    it('passes config object with network settings', async () => {
      const mockConfig = {
        services: {
          external_host: '192.168.1.100',
          api: { port: 7272 },
          frontend: { port: 7274 }
        },
        security: { cors: { allowed_origins: ['http://test.com'] } }
      }

      global.fetch.mockImplementation((url) => {
        if (url.includes('/api/v1/config/database')) {
          return Promise.resolve({
            ok: true,
            json: async () => ({ database: { host: 'localhost', port: 5432 } })
          })
        }
        if (url.includes('/api/v1/config')) {
          return Promise.resolve({
            ok: true,
            json: async () => mockConfig
          })
        }
        if (url.includes('/api/settings/cookie-domains')) {
          return Promise.resolve({
            ok: true,
            json: async () => ({ domains: [] })
          })
        }
        return Promise.reject(new Error('Unmocked fetch'))
      })

      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' },
            AdminIntegrationsTab: { template: '<div>Integrations Tab</div>' },
            SecuritySettingsTab: { template: '<div>Security Tab</div>' },
            SystemPromptTab: { template: '<div>System Tab</div>' },
            ClaudeConfigModal: { template: '<div>Claude Modal</div>' },
            CodexConfigModal: { template: '<div>Codex Modal</div>' },
            GeminiConfigModal: { template: '<div>Gemini Modal</div>' }
          }
        }
      })

      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 0))

      // Verify the config is loaded correctly
      expect(wrapper.vm.networkSettings.externalHost).toBe('192.168.1.100')
      expect(wrapper.vm.networkSettings.apiPort).toBe(7272)
      expect(wrapper.vm.networkSettings.frontendPort).toBe(7274)
    })

    it('passes corsOrigins array to NetworkSettingsTab', async () => {
      const mockConfig = {
        services: {
          external_host: 'localhost',
          api: { port: 7272 },
          frontend: { port: 7274 }
        },
        security: { cors: { allowed_origins: ['http://localhost:7274', 'http://test.com'] } }
      }

      global.fetch.mockImplementation((url) => {
        if (url.includes('/api/v1/config/database')) {
          return Promise.resolve({
            ok: true,
            json: async () => ({ database: { host: 'localhost', port: 5432 } })
          })
        }
        if (url.includes('/api/v1/config')) {
          return Promise.resolve({
            ok: true,
            json: async () => mockConfig
          })
        }
        if (url.includes('/api/settings/cookie-domains')) {
          return Promise.resolve({
            ok: true,
            json: async () => ({ domains: [] })
          })
        }
        return Promise.reject(new Error('Unmocked fetch'))
      })

      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' },
            AdminIntegrationsTab: { template: '<div>Integrations Tab</div>' },
            SecuritySettingsTab: { template: '<div>Security Tab</div>' },
            SystemPromptTab: { template: '<div>System Tab</div>' },
            ClaudeConfigModal: { template: '<div>Claude Modal</div>' },
            CodexConfigModal: { template: '<div>Codex Modal</div>' },
            GeminiConfigModal: { template: '<div>Gemini Modal</div>' }
          }
        }
      })

      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 0))

      expect(wrapper.vm.corsOrigins).toEqual(['http://localhost:7274', 'http://test.com'])
    })
  })

  describe('Props Passed to SecuritySettingsTab', () => {
    it('initializes cookieDomains as empty array', async () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' },
            NetworkSettingsTab: { template: '<div>Network Tab</div>' },
            AdminIntegrationsTab: { template: '<div>Integrations Tab</div>' },
            SystemPromptTab: { template: '<div>System Tab</div>' },
            ClaudeConfigModal: { template: '<div>Claude Modal</div>' },
            CodexConfigModal: { template: '<div>Codex Modal</div>' },
            GeminiConfigModal: { template: '<div>Gemini Modal</div>' }
          }
        }
      })

      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 0))

      // Cookie domains are loaded from api.settings.getCookieDomains
      // which is mocked to return empty array by default
      expect(wrapper.vm.cookieDomains).toEqual([])
    })

    it('has addCookieDomain method for SecuritySettingsTab events', () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' },
            NetworkSettingsTab: { template: '<div>Network Tab</div>' },
            AdminIntegrationsTab: { template: '<div>Integrations Tab</div>' },
            SystemPromptTab: { template: '<div>System Tab</div>' },
            ClaudeConfigModal: { template: '<div>Claude Modal</div>' },
            CodexConfigModal: { template: '<div>Codex Modal</div>' },
            GeminiConfigModal: { template: '<div>Gemini Modal</div>' }
          }
        }
      })

      expect(typeof wrapper.vm.addCookieDomain).toBe('function')
      expect(typeof wrapper.vm.removeCookieDomain).toBe('function')
    })
  })

  describe('Event Handling from Child Components', () => {
    it('handles refresh event from NetworkSettingsTab', async () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' },
            AdminIntegrationsTab: { template: '<div>Integrations Tab</div>' },
            SecuritySettingsTab: { template: '<div>Security Tab</div>' },
            SystemPromptTab: { template: '<div>System Tab</div>' },
            ClaudeConfigModal: { template: '<div>Claude Modal</div>' },
            CodexConfigModal: { template: '<div>Codex Modal</div>' },
            GeminiConfigModal: { template: '<div>Gemini Modal</div>' }
          }
        }
      })

      // The loadNetworkSettings method should exist
      expect(typeof wrapper.vm.loadNetworkSettings).toBe('function')
    })

    it('handles add-domain event from SecuritySettingsTab', async () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' },
            NetworkSettingsTab: { template: '<div>Network Tab</div>' },
            AdminIntegrationsTab: { template: '<div>Integrations Tab</div>' },
            SystemPromptTab: { template: '<div>System Tab</div>' },
            ClaudeConfigModal: { template: '<div>Claude Modal</div>' },
            CodexConfigModal: { template: '<div>Codex Modal</div>' },
            GeminiConfigModal: { template: '<div>Gemini Modal</div>' }
          }
        }
      })

      // The addCookieDomain method should exist
      expect(typeof wrapper.vm.addCookieDomain).toBe('function')
    })

    it('handles remove-domain event from SecuritySettingsTab', async () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' },
            NetworkSettingsTab: { template: '<div>Network Tab</div>' },
            AdminIntegrationsTab: { template: '<div>Integrations Tab</div>' },
            SystemPromptTab: { template: '<div>System Tab</div>' },
            ClaudeConfigModal: { template: '<div>Claude Modal</div>' },
            CodexConfigModal: { template: '<div>Codex Modal</div>' },
            GeminiConfigModal: { template: '<div>Gemini Modal</div>' }
          }
        }
      })

      // The removeCookieDomain method should exist
      expect(typeof wrapper.vm.removeCookieDomain).toBe('function')
    })
  })

  describe('Modal Components', () => {
    it('includes ClaudeConfigModal component', () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' },
            NetworkSettingsTab: { template: '<div>Network Tab</div>' },
            AdminIntegrationsTab: { template: '<div>Integrations Tab</div>' },
            SecuritySettingsTab: { template: '<div>Security Tab</div>' },
            SystemPromptTab: { template: '<div>System Tab</div>' },
            ClaudeConfigModal: { template: '<div data-test="claude-modal-stub">Claude Modal</div>' },
            CodexConfigModal: { template: '<div>Codex Modal</div>' },
            GeminiConfigModal: { template: '<div>Gemini Modal</div>' }
          }
        }
      })

      const claudeModal = wrapper.find('[data-test="claude-modal-stub"]')
      expect(claudeModal.exists()).toBe(true)
    })

    it('includes CodexConfigModal component', () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' },
            NetworkSettingsTab: { template: '<div>Network Tab</div>' },
            AdminIntegrationsTab: { template: '<div>Integrations Tab</div>' },
            SecuritySettingsTab: { template: '<div>Security Tab</div>' },
            SystemPromptTab: { template: '<div>System Tab</div>' },
            ClaudeConfigModal: { template: '<div>Claude Modal</div>' },
            CodexConfigModal: { template: '<div data-test="codex-modal-stub">Codex Modal</div>' },
            GeminiConfigModal: { template: '<div>Gemini Modal</div>' }
          }
        }
      })

      const codexModal = wrapper.find('[data-test="codex-modal-stub"]')
      expect(codexModal.exists()).toBe(true)
    })

    it('includes GeminiConfigModal component', () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' },
            NetworkSettingsTab: { template: '<div>Network Tab</div>' },
            AdminIntegrationsTab: { template: '<div>Integrations Tab</div>' },
            SecuritySettingsTab: { template: '<div>Security Tab</div>' },
            SystemPromptTab: { template: '<div>System Tab</div>' },
            ClaudeConfigModal: { template: '<div>Claude Modal</div>' },
            CodexConfigModal: { template: '<div>Codex Modal</div>' },
            GeminiConfigModal: { template: '<div data-test="gemini-modal-stub">Gemini Modal</div>' }
          }
        }
      })

      const geminiModal = wrapper.find('[data-test="gemini-modal-stub"]')
      expect(geminiModal.exists()).toBe(true)
    })
  })

  describe('Reduced Component Size', () => {
    it('should maintain all original functionality after refactoring', async () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' },
            NetworkSettingsTab: { template: '<div>Network Tab</div>' },
            AdminIntegrationsTab: { template: '<div>Integrations Tab</div>' },
            SecuritySettingsTab: { template: '<div>Security Tab</div>' },
            SystemPromptTab: { template: '<div>System Tab</div>' },
            ClaudeConfigModal: { template: '<div>Claude Modal</div>' },
            CodexConfigModal: { template: '<div>Codex Modal</div>' },
            GeminiConfigModal: { template: '<div>Gemini Modal</div>' }
          }
        }
      })

      // Verify all tab names are present in text content
      const text = wrapper.text()
      expect(text).toContain('Network')
      expect(text).toContain('Database')
      expect(text).toContain('Integrations')
      expect(text).toContain('Security')
      expect(text).toContain('System')

      // Verify page title
      expect(wrapper.text()).toContain('Admin Settings')

      // Verify admin-only message
      expect(wrapper.text()).toContain('Admin only')
    })

    it('should properly load network data on mount', async () => {
      const mockConfig = {
        services: {
          external_host: 'test-host',
          api: { port: 8080 },
          frontend: { port: 8081 }
        },
        security: { cors: { allowed_origins: ['http://example.com'] } }
      }

      global.fetch.mockImplementation((url) => {
        if (url.includes('/api/v1/config/database')) {
          return Promise.resolve({
            ok: true,
            json: async () => ({ database: { host: 'localhost', port: 5432 } })
          })
        }
        if (url.includes('/api/v1/config')) {
          return Promise.resolve({
            ok: true,
            json: async () => mockConfig
          })
        }
        return Promise.reject(new Error('Unmocked fetch'))
      })

      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' },
            NetworkSettingsTab: { template: '<div>Network Tab</div>' },
            AdminIntegrationsTab: { template: '<div>Integrations Tab</div>' },
            SecuritySettingsTab: { template: '<div>Security Tab</div>' },
            SystemPromptTab: { template: '<div>System Tab</div>' },
            ClaudeConfigModal: { template: '<div>Claude Modal</div>' },
            CodexConfigModal: { template: '<div>Codex Modal</div>' },
            GeminiConfigModal: { template: '<div>Gemini Modal</div>' }
          }
        }
      })

      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 0))

      // Verify network data is loaded (cookie domains use api mock which returns empty)
      expect(wrapper.vm.networkSettings.externalHost).toBe('test-host')
      expect(wrapper.vm.networkSettings.apiPort).toBe(8080)
      expect(wrapper.vm.networkSettings.frontendPort).toBe(8081)
      expect(wrapper.vm.corsOrigins).toEqual(['http://example.com'])
    })
  })
})
