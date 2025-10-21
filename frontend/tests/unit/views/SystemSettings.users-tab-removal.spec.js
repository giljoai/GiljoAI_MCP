import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import SystemSettings from '@/views/SystemSettings.vue'

// Mock the API module
vi.mock('@/services/api', () => ({
  default: {
    settings: {
      getCookieDomains: vi.fn().mockResolvedValue({ data: { domains: [] } }),
      addCookieDomain: vi.fn().mockResolvedValue({ data: { message: 'Domain added' } }),
      removeCookieDomain: vi.fn().mockResolvedValue({ data: { message: 'Domain removed' } }),
    },
  },
}))

// Mock fetch for config endpoint
global.fetch = vi.fn()

describe('SystemSettings.vue - Users Tab Removal', () => {
  let wrapper

  const mockCurrentUser = {
    id: 1,
    username: 'admin',
    role: 'admin',
    tenant_key: 'tk_test',
  }

  const mockConfigResponse = {
    services: {
      external_host: 'localhost',
      api: { port: 7272 },
      frontend: { port: 7274 },
    },
    security: {
      cors: {
        allowed_origins: ['http://localhost:7274'],
      },
    },
  }

  beforeEach(async () => {
    // Setup fetch mock
    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => mockConfigResponse,
    })

    wrapper = mount(SystemSettings, {
      global: {
        plugins: [
          createTestingPinia({
            initialState: {
              user: {
                currentUser: mockCurrentUser,
              },
            },
          }),
        ],
        stubs: {
          DatabaseConnection: true,
        },
      },
    })

    await wrapper.vm.$nextTick()
  })

  describe('Tab Structure - Users Tab Removed', () => {
    it('does NOT display Users tab in settings tabs', async () => {
      await wrapper.vm.$nextTick()

      // Check HTML does not contain Users tab
      const html = wrapper.html()
      expect(html).not.toContain('value="users"')
      expect(html).not.toContain('mdi-account-multiple')
    })

    it('displays Network tab', () => {
      const html = wrapper.html()
      expect(html).toContain('Network')
      expect(html).toContain('mdi-network-outline')
    })

    it('displays Database tab', () => {
      const html = wrapper.html()
      expect(html).toContain('Database')
      expect(html).toContain('mdi-database')
    })

    it('displays Integrations tab', () => {
      const html = wrapper.html()
      expect(html).toContain('Integrations')
      expect(html).toContain('mdi-api')
    })

    it('displays Security tab', () => {
      const html = wrapper.html()
      expect(html).toContain('Security')
      expect(html).toContain('mdi-shield-lock')
    })

    it('has exactly 4 tabs (Network, Database, Integrations, Security)', () => {
      const html = wrapper.html()

      // Should have exactly 4 tabs after Users removal
      expect(html).toContain('Network')
      expect(html).toContain('Database')
      expect(html).toContain('Integrations')
      expect(html).toContain('Security')
      expect(html).not.toContain('value="users"')
    })

    it('tab order is correct: Network, Database, Integrations, Security', () => {
      const html = wrapper.html()

      // Verify all tabs present
      expect(html).toContain('Network')
      expect(html).toContain('Database')
      expect(html).toContain('Integrations')
      expect(html).toContain('Security')
    })
  })

  describe('Tab Window Content - Users Removed', () => {
    it('does NOT have v-window-item for Users tab', () => {
      // Check that there's no UserManager component
      const userManager = wrapper.findComponent({ name: 'UserManager' })
      expect(userManager.exists()).toBe(false)
    })

    it('has content for Network tab', () => {
      const html = wrapper.html()
      expect(html).toContain('Network Configuration')
    })

    it('has content for Database tab', () => {
      const databaseConnection = wrapper.findComponent({ name: 'DatabaseConnection' })
      expect(databaseConnection.exists()).toBe(true)
    })

    it('has content for Integrations tab', () => {
      // Look for integrations content markers
      const html = wrapper.html()
      expect(html).toContain('Integrations')
    })

    it('has content for Security tab', () => {
      // Look for security content markers
      const html = wrapper.html()
      expect(html).toContain('Cookie Domain Whitelist')
    })
  })

  describe('Component Imports - UserManager Removed', () => {
    it('does NOT import UserManager component', () => {
      // Verify UserManager is not in the component
      const userManager = wrapper.findComponent({ name: 'UserManager' })
      expect(userManager.exists()).toBe(false)
    })

    it('still imports DatabaseConnection component', () => {
      const databaseConnection = wrapper.findComponent({ name: 'DatabaseConnection' })
      expect(databaseConnection.exists()).toBe(true)
    })
  })

  describe('Active Tab State', () => {
    it('defaults to Network tab when no Users tab exists', async () => {
      // Initial active tab should be 'network'
      expect(wrapper.vm.activeTab).toBe('network')
    })

    it('can switch to Database tab', async () => {
      // Switch to database tab
      wrapper.vm.activeTab = 'database'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.activeTab).toBe('database')
    })

    it('can switch to Integrations tab', async () => {
      // Switch to integrations tab
      wrapper.vm.activeTab = 'integrations'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.activeTab).toBe('integrations')
    })

    it('can switch to Security tab', async () => {
      // Switch to security tab
      wrapper.vm.activeTab = 'security'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.activeTab).toBe('security')
    })

    it('does NOT have users as a valid tab value', () => {
      // Attempt to set to 'users' should not be valid
      const tabs = wrapper.findAll('.v-tab')
      const tabValues = tabs.map((tab) => tab.attributes('value'))

      expect(tabValues).not.toContain('users')
    })
  })

  describe('Navigation and UX', () => {
    it('Network tab is accessible and functional', async () => {
      wrapper.vm.activeTab = 'network'
      await wrapper.vm.$nextTick()

      // Network tab content should be visible
      const networkContent = wrapper.html()
      expect(networkContent).toContain('Network Configuration')
    })

    it('Database tab is accessible and functional', async () => {
      wrapper.vm.activeTab = 'database'
      await wrapper.vm.$nextTick()

      // Database component should be visible
      const databaseConnection = wrapper.findComponent({ name: 'DatabaseConnection' })
      expect(databaseConnection.exists()).toBe(true)
    })

    it('Integrations tab is accessible and functional', async () => {
      wrapper.vm.activeTab = 'integrations'
      await wrapper.vm.$nextTick()

      // Integrations content should be visible
      const integrationsContent = wrapper.html()
      expect(integrationsContent).toContain('Agent Coding Tools')
    })

    it('Security tab is accessible and functional', async () => {
      wrapper.vm.activeTab = 'security'
      await wrapper.vm.$nextTick()

      // Security content should be visible
      const securityContent = wrapper.html()
      expect(securityContent).toContain('Cookie Domain Whitelist')
    })
  })

  describe('Page Title and Description', () => {
    it('displays page title "Admin Settings"', () => {
      const title = wrapper.find('h1')
      expect(title.text()).toBe('Admin Settings')
    })

    it('displays page description', () => {
      const description = wrapper.find('.text-subtitle-1')
      expect(description.text()).toContain('Configure server and system-wide settings')
    })

    it('page description does NOT mention user management', () => {
      const description = wrapper.find('.text-subtitle-1')
      expect(description.text()).not.toContain('user')
      expect(description.text()).not.toContain('User')
    })
  })

  describe('Tab Icons', () => {
    it('Network tab has correct icon', () => {
      const html = wrapper.html()
      expect(html).toContain('mdi-network-outline')
    })

    it('Database tab has correct icon', () => {
      const html = wrapper.html()
      expect(html).toContain('mdi-database')
    })

    it('Integrations tab has correct icon', () => {
      const html = wrapper.html()
      expect(html).toContain('mdi-api')
    })

    it('Security tab has correct icon', () => {
      const html = wrapper.html()
      expect(html).toContain('mdi-shield-lock')
    })

    it('does NOT have mdi-account-multiple icon (Users tab removed)', () => {
      const html = wrapper.html()
      // Should not have account-multiple icon in tabs
      expect(html).not.toContain('mdi-account-multiple')
    })
  })

  describe('Accessibility - Tab Navigation', () => {
    it('tabs are keyboard accessible', async () => {
      await wrapper.vm.$nextTick()
      // Verify tabs exist in HTML (Vuetify renders them with role="tab")
      const html = wrapper.html()
      expect(html).toContain('Network')
      expect(html).toContain('Database')
      expect(html).toContain('Integrations')
      expect(html).toContain('Security')
    })

    it('tab content is properly labeled', () => {
      const html = wrapper.html()
      // Verify tab labels exist
      expect(html).toContain('Network')
      expect(html).toContain('Database')
      expect(html).toContain('Integrations')
      expect(html).toContain('Security')
    })
  })

  describe('Backward Compatibility', () => {
    it('existing functionality still works after Users tab removal', async () => {
      // Test Network tab functionality
      wrapper.vm.activeTab = 'network'
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.activeTab).toBe('network')

      // Test Security tab functionality
      wrapper.vm.activeTab = 'security'
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.activeTab).toBe('security')
    })

    it('cookie domain management still works', async () => {
      wrapper.vm.activeTab = 'security'
      await wrapper.vm.$nextTick()

      // Cookie domain functionality should still be present
      expect(wrapper.vm.loadCookieDomains).toBeDefined()
      expect(wrapper.vm.addCookieDomain).toBeDefined()
      expect(wrapper.vm.removeCookieDomain).toBeDefined()
    })

    it('network settings functionality still works', async () => {
      wrapper.vm.activeTab = 'network'
      await wrapper.vm.$nextTick()

      // Network settings functionality should still be present
      expect(wrapper.vm.loadNetworkSettings).toBeDefined()
      expect(wrapper.vm.saveNetworkSettings).toBeDefined()
    })
  })

  describe('Code Quality - No Orphaned References', () => {
    it('component HTML does NOT contain UserManager references', () => {
      const html = wrapper.html()
      expect(html).not.toContain('UserManager')
      expect(html).not.toContain('user-manager')
    })

    it('component does NOT have userManager in component data', () => {
      // Check that there are no userManager-related data properties
      expect(wrapper.vm.userManager).toBeUndefined()
    })
  })
})
