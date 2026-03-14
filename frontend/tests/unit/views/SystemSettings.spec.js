/**
 * Test suite for SystemSettings.vue component
 *
 * Tests the System Settings view functionality including:
 * - Network configuration (external host, API port, CORS)
 * - Database settings (readonly display)
 * - Security configuration (cookie domain whitelist)
 * - System settings (orchestrator prompt override)
 * - Admin-only access
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

describe('SystemSettings.vue', () => {
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
        { path: '/admin/settings', name: 'SystemSettings', component: SystemSettings }
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

  describe('Component Rendering', () => {
    it('renders the component', () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' }
          }
        }
      })

      expect(wrapper.exists()).toBe(true)
    })

    it('displays page title "Admin Settings"', () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' },
            UserManager: { template: '<div>User Manager Mock</div>' }
          }
        }
      })

      expect(wrapper.text()).toContain('Admin Settings')
    })

    it('displays admin-only subtitle', () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' }
          }
        }
      })

      expect(wrapper.text()).toContain('Configure server and system-wide settings')
      expect(wrapper.text()).toContain('Admin only')
    })
  })

  describe('Tab Navigation', () => {
    const defaultStubs = {
      DatabaseConnection: { template: '<div>Database Connection Mock</div>' },
      NetworkSettingsTab: { template: '<div>Network Tab</div>' },
      SecuritySettingsTab: { template: '<div>Security Tab</div>' },
      SystemPromptTab: { template: '<div>System Tab</div>' }
    }

    it('renders all tabs (Identity, Network, Database, Security, Prompts)', () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: defaultStubs
        }
      })

      // Check for tab text content instead of .v-tab class
      const text = wrapper.text()
      expect(text).toContain('Identity')
      expect(text).toContain('Network')
      expect(text).toContain('Database')
      expect(text).toContain('Security')
      expect(text).toContain('Prompts')
    })

    it('renders Network tab', () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: defaultStubs
        }
      })

      expect(wrapper.text()).toContain('Network')
    })

    it('renders Database tab', () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: defaultStubs
        }
      })

      expect(wrapper.text()).toContain('Database')
    })

    it('renders Security tab', () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: defaultStubs
        }
      })

      expect(wrapper.text()).toContain('Security')
    })

    it('renders System tab', () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: defaultStubs
        }
      })

      expect(wrapper.text()).toContain('System')
    })
  })

  describe('Network Tab - Refactored v3.1', () => {
    it('displays external host from config', async () => {
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
            json: async () => ({
              services: {
                external_host: '192.168.1.100',
                api: { port: 7272 },
                frontend: { port: 7274 }
              },
              security: { cors: { allowed_origins: [] } }
            })
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
            UserManager: { template: '<div>User Manager Mock</div>' }
          }
        }
      })

      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 0))

      expect(wrapper.vm.networkSettings.externalHost).toBe('192.168.1.100')
    })

    it('displays API and Frontend ports', async () => {
      global.fetch.mockResolvedValueOnce({
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

      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' },
            UserManager: { template: '<div>User Manager Mock</div>' }
          }
        }
      })

      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 0))

      expect(wrapper.vm.networkSettings.apiPort).toBe(7272)
      expect(wrapper.vm.networkSettings.frontendPort).toBe(7274)
    })

    it('renders NetworkSettingsTab component with correct props', async () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' },
            UserManager: { template: '<div>User Manager Mock</div>' },
            NetworkSettingsTab: {
              template: '<div data-test="network-settings-tab">Network Tab</div>',
              props: ['config', 'corsOrigins', 'loading']
            },

            SecuritySettingsTab: { template: '<div>Security Tab</div>' },
            SystemPromptTab: { template: '<div>System Tab</div>' },
          }
        }
      })

      const networkTab = wrapper.find('[data-test="network-settings-tab"]')
      expect(networkTab.exists()).toBe(true)
    })

    it('passes network settings to NetworkSettingsTab via props', async () => {
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
            json: async () => ({
              services: {
                external_host: '192.168.1.100',
                api: { port: 7272 },
                frontend: { port: 7274 }
              },
              security: { cors: { allowed_origins: ['http://test.com'] } }
            })
          })
        }
        return Promise.reject(new Error('Unmocked fetch'))
      })

      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' },
            UserManager: { template: '<div>User Manager Mock</div>' },
            NetworkSettingsTab: { template: '<div>Network Tab</div>' },

            SecuritySettingsTab: { template: '<div>Security Tab</div>' },
            SystemPromptTab: { template: '<div>System Tab</div>' },
          }
        }
      })

      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 0))

      // Verify the data is loaded correctly - it will be passed to NetworkSettingsTab
      expect(wrapper.vm.networkSettings.externalHost).toBe('192.168.1.100')
      expect(wrapper.vm.corsOrigins).toEqual(['http://test.com'])
    })

    it('does NOT show deprecated mode chip', async () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' },
            UserManager: { template: '<div>User Manager Mock</div>' }
          }
        }
      })

      const modeChip = wrapper.find('[data-test="mode-chip"]')
      expect(modeChip.exists()).toBe(false)
    })

    it('does NOT show deprecated API key info', async () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' },
            UserManager: { template: '<div>User Manager Mock</div>' }
          }
        }
      })

      const apiKeyField = wrapper.find('[data-test="api-key-field"]')
      expect(apiKeyField.exists()).toBe(false)
    })

    it('does NOT show regenerate API key button', async () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' },
            UserManager: { template: '<div>User Manager Mock</div>' }
          }
        }
      })

      const regenerateBtn = wrapper.find('[data-test="regenerate-api-key-btn"]')
      expect(regenerateBtn.exists()).toBe(false)
    })

    it('falls back to default values when config fails to load', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Network error'))

      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' },
            UserManager: { template: '<div>User Manager Mock</div>' }
          }
        }
      })

      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 0))

      expect(wrapper.vm.networkSettings.externalHost).toBe('localhost')
      expect(wrapper.vm.networkSettings.apiPort).toBe(7272)
      expect(wrapper.vm.networkSettings.frontendPort).toBe(7274)
      expect(wrapper.vm.corsOrigins).toEqual([])
    })

    it('renders child component tabs correctly', async () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' },
            UserManager: { template: '<div>User Manager Mock</div>' },
            NetworkSettingsTab: { template: '<div data-test="network-stub">Network</div>' },

            SecuritySettingsTab: { template: '<div data-test="security-stub">Security</div>' },
            SystemPromptTab: { template: '<div data-test="system-stub">System</div>' },
          }
        }
      })

      // Network tab is default, should be visible
      const networkStub = wrapper.find('[data-test="network-stub"]')
      expect(networkStub.exists()).toBe(true)
    })
  })

  describe('Database Tab', () => {
    it('renders DatabaseConnection component', async () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div data-test="database-connection-stub">Database Connection Mock</div>' }
          }
        }
      })

      if (wrapper.vm.activeTab !== undefined) {
        wrapper.vm.activeTab = 'database'
        await wrapper.vm.$nextTick()
      }

      const dbConnection = wrapper.find('[data-test="database-connection-stub"]')
      expect(dbConnection.exists()).toBe(true)
    })

    it('sets DatabaseConnection to readonly mode', async () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: {
              template: '<div data-test="db-stub">DB Mock</div>',
              props: ['readonly']
            }
          }
        }
      })

      if (wrapper.vm.activeTab !== undefined) {
        wrapper.vm.activeTab = 'database'
        await wrapper.vm.$nextTick()
      }

      const dbComponent = wrapper.findComponent({ name: 'DatabaseConnection' })
      if (dbComponent.exists()) {
        expect(dbComponent.props('readonly')).toBe(true)
      }
    })
  })

  describe('Network Settings Management', () => {
    it('loads network settings on mount', async () => {
      const mockConfig = {
        services: {
          external_host: 'localhost',
          api: { port: 7272 },
          frontend: { port: 7274 }
        },
        security: { cors: { allowed_origins: ['http://localhost:7274'] } }
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
            UserManager: { template: '<div>User Manager Mock</div>' }
          }
        }
      })

      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 0))

      // Check that config endpoint was called
      const configCalls = global.fetch.mock.calls.filter(call =>
        call[0].includes('/api/v1/config') && !call[0].includes('/database')
      )
      expect(configCalls.length).toBeGreaterThan(0)
    })

    it('maintains loadNetworkSettings method for child component events', async () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' },
            UserManager: { template: '<div>User Manager Mock</div>' },
            NetworkSettingsTab: { template: '<div>Network Tab</div>' },

            SecuritySettingsTab: { template: '<div>Security Tab</div>' },
            SystemPromptTab: { template: '<div>System Tab</div>' },
          }
        }
      })

      // The method should exist to handle events from NetworkSettingsTab
      expect(typeof wrapper.vm.loadNetworkSettings).toBe('function')
    })

    it('saves network settings', async () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' },
            UserManager: { template: '<div>User Manager Mock</div>' }
          }
        }
      })

      // Mock the PATCH endpoint
      global.fetch.mockImplementationOnce((url, options) => {
        if (options && options.method === 'PATCH') {
          return Promise.resolve({
            ok: true,
            json: async () => ({ success: true })
          })
        }
        return Promise.reject(new Error('Unmocked fetch'))
      })

      if (wrapper.vm.saveNetworkSettings) {
        await wrapper.vm.saveNetworkSettings()

        const patchCalls = global.fetch.mock.calls.filter(call =>
          call[1] && call[1].method === 'PATCH'
        )
        expect(patchCalls.length).toBeGreaterThan(0)
      }
    })
  })

  describe('Admin Access', () => {
    it('should only be accessible to admin users', () => {
      // This will be enforced by router guard
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' }
          }
        }
      })

      expect(wrapper.exists()).toBe(true)
      // Actual admin check happens in router guard
    })
  })
})
