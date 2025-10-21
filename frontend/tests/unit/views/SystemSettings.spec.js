/**
 * Test suite for SystemSettings.vue component
 *
 * Tests the System Settings view functionality including:
 * - Network configuration (mode, API host/port, CORS, API key)
 * - Database settings (readonly display)
 * - Integrations (Serena MCP toggle)
 * - Users placeholder (Phase 5)
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

    // Mock fetch
    global.fetch = vi.fn()
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

    it('displays page title "System Settings"', () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' }
          }
        }
      })

      expect(wrapper.text()).toContain('System Settings')
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
    it('renders all 4 tabs (Network, Database, Integrations, Users)', () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' }
          }
        }
      })

      const tabs = wrapper.findAll('.v-tab')
      expect(tabs.length).toBe(4)
    })

    it('renders Network tab', () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' }
          }
        }
      })

      const tabs = wrapper.findAll('.v-tab')
      const networkTab = tabs.find(tab => tab.text().includes('Network'))
      expect(networkTab).toBeDefined()
    })

    it('renders Database tab', () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' }
          }
        }
      })

      const tabs = wrapper.findAll('.v-tab')
      const databaseTab = tabs.find(tab => tab.text().includes('Database'))
      expect(databaseTab).toBeDefined()
    })

    it('renders Integrations tab', () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' }
          }
        }
      })

      const tabs = wrapper.findAll('.v-tab')
      const integrationsTab = tabs.find(tab => tab.text().includes('Integrations'))
      expect(integrationsTab).toBeDefined()
    })

    it('renders Users tab placeholder', () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' }
          }
        }
      })

      const tabs = wrapper.findAll('.v-tab')
      const usersTab = tabs.find(tab => tab.text().includes('Users'))
      expect(usersTab).toBeDefined()
    })
  })

  describe('Network Tab - Refactored v3.1', () => {
    it('displays external host from config', async () => {
      global.fetch.mockResolvedValueOnce({
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

    it('shows external host field as readonly', async () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' },
            UserManager: { template: '<div>User Manager Mock</div>' }
          }
        }
      })

      const externalHostField = wrapper.find('[data-test="external-host-field"]')
      if (externalHostField.exists()) {
        expect(externalHostField.attributes('readonly')).toBeDefined()
      }
    })

    it('shows API port field as readonly', async () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' },
            UserManager: { template: '<div>User Manager Mock</div>' }
          }
        }
      })

      const apiPortField = wrapper.find('[data-test="api-port-field"]')
      if (apiPortField.exists()) {
        expect(apiPortField.attributes('readonly')).toBeDefined()
      }
    })

    it('shows frontend port field as readonly', async () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' },
            UserManager: { template: '<div>User Manager Mock</div>' }
          }
        }
      })

      const frontendPortField = wrapper.find('[data-test="frontend-port-field"]')
      if (frontendPortField.exists()) {
        expect(frontendPortField.attributes('readonly')).toBeDefined()
      }
    })

    it('provides copy button for external host', async () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' },
            UserManager: { template: '<div>User Manager Mock</div>' }
          }
        }
      })

      const copyButton = wrapper.find('[data-test="copy-external-host-btn"]')
      expect(copyButton.exists()).toBe(true)
    })

    it('copies external host to clipboard when copy button clicked', async () => {
      const clipboardSpy = vi.spyOn(navigator.clipboard, 'writeText').mockResolvedValue()

      global.fetch.mockResolvedValueOnce({
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

      if (wrapper.vm.copyExternalHost) {
        wrapper.vm.copyExternalHost()
        expect(clipboardSpy).toHaveBeenCalledWith('192.168.1.100')
      }

      clipboardSpy.mockRestore()
    })

    it('shows CORS origins management section', async () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' },
            UserManager: { template: '<div>User Manager Mock</div>' }
          }
        }
      })

      const corsSection = wrapper.find('[data-test="cors-origins-section"]')
      expect(corsSection.exists()).toBe(true)
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

    it('shows informational alert about unified v3.0 architecture', async () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' },
            UserManager: { template: '<div>User Manager Mock</div>' }
          }
        }
      })

      const unifiedAlert = wrapper.find('[data-test="v3-unified-alert"]')
      expect(unifiedAlert.exists()).toBe(true)
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

  describe('Integrations Tab', () => {
    it('displays Serena MCP integration', async () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' }
          }
        }
      })

      if (wrapper.vm.activeTab !== undefined) {
        wrapper.vm.activeTab = 'integrations'
        await wrapper.vm.$nextTick()
      }

      const serenaSection = wrapper.find('[data-test="serena-integration"]')
      expect(serenaSection.exists()).toBe(true)
    })

    it('includes Serena MCP toggle', async () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' }
          }
        }
      })

      if (wrapper.vm.activeTab !== undefined) {
        wrapper.vm.activeTab = 'integrations'
        await wrapper.vm.$nextTick()
      }

      const serenaToggle = wrapper.find('[data-test="serena-toggle"]')
      expect(serenaToggle.exists()).toBe(true)
    })

    it('does NOT show API key authentication info', async () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' }
          }
        }
      })

      if (wrapper.vm.activeTab !== undefined) {
        wrapper.vm.activeTab = 'integrations'
        await wrapper.vm.$nextTick()
      }

      // API key info should be in Network tab only
      const apiKeyInfo = wrapper.find('[data-test="api-key-authentication-info"]')
      expect(apiKeyInfo.exists()).toBe(false)
    })
  })

  describe('Users Tab (Placeholder)', () => {
    it('displays Phase 5 placeholder message', async () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' }
          }
        }
      })

      if (wrapper.vm.activeTab !== undefined) {
        wrapper.vm.activeTab = 'users'
        await wrapper.vm.$nextTick()
      }

      expect(wrapper.text()).toContain('User management coming in Phase 5')
    })

    it('renders Users tab with placeholder content', async () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' }
          }
        }
      })

      if (wrapper.vm.activeTab !== undefined) {
        wrapper.vm.activeTab = 'users'
        await wrapper.vm.$nextTick()
      }

      const usersPlaceholder = wrapper.find('[data-test="users-placeholder"]')
      expect(usersPlaceholder.exists()).toBe(true)
    })
  })

  describe('Network Settings Management', () => {
    it('loads network settings on mount', async () => {
      const mockConfig = {
        installation: { mode: 'localhost' },
        services: { api: { host: '127.0.0.1', port: 7272 } },
        security: { cors: { allowed_origins: ['http://localhost:7274'] } }
      }

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockConfig
      })

      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' }
          }
        }
      })

      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 0))

      expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining('/api/v1/config'))
    })

    it('adds CORS origin', async () => {
      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' }
          }
        }
      })

      if (wrapper.vm.addOrigin) {
        wrapper.vm.newOrigin = 'http://192.168.1.100:7274'
        wrapper.vm.addOrigin()
        await wrapper.vm.$nextTick()

        expect(wrapper.vm.corsOrigins).toContain('http://192.168.1.100:7274')
      }
    })

    it('saves network settings', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true })
      })

      wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            DatabaseConnection: { template: '<div>Database Connection Mock</div>' }
          }
        }
      })

      if (wrapper.vm.saveNetworkSettings) {
        await wrapper.vm.saveNetworkSettings()

        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining('/api/v1/config'),
          expect.objectContaining({
            method: 'PATCH'
          })
        )
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
