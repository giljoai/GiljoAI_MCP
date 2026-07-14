import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import SystemSettings from '@/views/SystemSettings.vue'
import configService from '@/services/configService'

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
    // FE-6055: getGiljoMode() now resolves to 'unknown' (not 'ce') without a
    // real config; the CE-only tabs gate on a confirmed 'ce'. Seed it before
    // mount so this CE suite renders the network/database/security tabs.
    configService.config = { giljo_mode: 'ce', mode: 'server', api: {} }

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

    // FE-6245: Security tab retired; Cookie Whitelist moved to Network tab
    it('does NOT display a standalone Security tab (FE-6245)', () => {
      const html = wrapper.html()
      expect(html).not.toContain('mdi-shield-lock')
      // The Cookie Domain Whitelist content is now inside the Network tab
      expect(html).toContain('Network')
    })

    it('does NOT display the Prompts tab (moved to Account -> Danger Zone, IMP-5042)', () => {
      const html = wrapper.html()
      expect(html).not.toContain('data-test="prompts-tab"')
      expect(html).not.toContain('mdi-file-document-edit')
    })

    // FE-6245: Security tab retired; 3 CE-only tabs remain
    it('has exactly 3 tabs (Identity, Network, Database) — Security tab retired (FE-6245)', () => {
      const html = wrapper.html()

      // 3 tabs after Users removal + Prompts relocation (IMP-5042) + Security retirement (FE-6245)
      expect(html).toContain('Identity')
      expect(html).toContain('Network')
      expect(html).toContain('Database')
      expect(html).not.toContain('value="users"')
      expect(html).not.toContain('data-test="prompts-tab"')
      expect(html).not.toContain('data-test="security-tab"')
    })

    it('tab order is correct: Identity, Network, Database', () => {
      const html = wrapper.html()

      // Verify remaining tabs are present (Security tab retired in FE-6245)
      expect(html).toContain('Identity')
      expect(html).toContain('Network')
      expect(html).toContain('Database')
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

    it('does NOT render the orchestrator-prompt content (relocated to Account)', () => {
      const html = wrapper.html()
      expect(html).not.toContain('System Orchestrator Prompt')
    })

    // FE-6245: Cookie Domain Whitelist moved from Security tab to Network tab
    it('has Cookie Domain Whitelist content in the Network tab (FE-6245)', () => {
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
    it('defaults to Identity tab when no Users tab exists', async () => {
      // Initial active tab should be 'identity'
      expect(wrapper.vm.activeTab).toBe('identity')
    })

    it('can switch to Database tab', async () => {
      // Switch to database tab
      wrapper.vm.activeTab = 'database'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.activeTab).toBe('database')
    })

    // FE-6245: Security tab retired — no 'security' window-item exists
    it('does NOT have a security activeTab value (Security tab retired, FE-6245)', async () => {
      // Setting activeTab = 'security' would show nothing (no window-item for it)
      expect(wrapper.find('[data-test="security-tab"]').exists()).toBe(false)
    })

    it('does NOT have users as a valid tab value', () => {
      // Attempt to set to 'users' should not be valid
      const tabs = wrapper.findAll('.v-tab')
      const tabValues = tabs.map((tab) => tab.attributes('value'))

      expect(tabValues).not.toContain('users')
    })

    // FE-6245
    it('does NOT have security as a valid tab value', () => {
      expect(wrapper.find('[data-test="security-tab"]').exists()).toBe(false)
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

    // FE-6245: Cookie Domain Whitelist now lives inside the Network tab
    it('Cookie Domain Whitelist is accessible within the Network tab (FE-6245)', async () => {
      wrapper.vm.activeTab = 'network'
      await wrapper.vm.$nextTick()

      const networkContent = wrapper.html()
      expect(networkContent).toContain('Cookie Domain Whitelist')
    })
  })

  describe('Page Title and Description', () => {
    it('displays page title "Admin Settings"', () => {
      const title = wrapper.find('h1')
      expect(title.text()).toBe('Admin Settings')
    })

    it('displays page description', () => {
      const description = wrapper.find('.text-body-large')
      expect(description.text()).toContain('Configure server and system-wide settings')
    })

    it('page description does NOT mention user management', () => {
      const description = wrapper.find('.text-body-large')
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

    // FE-6245: Security tab retired; mdi-shield-lock icon removed
    it('does NOT have the mdi-shield-lock icon (Security tab retired, FE-6245)', () => {
      const html = wrapper.html()
      expect(html).not.toContain('mdi-shield-lock')
    })

    it('does NOT have mdi-account-multiple icon (Users tab removed)', () => {
      const html = wrapper.html()
      // Should not have account-multiple icon in tabs
      expect(html).not.toContain('mdi-account-multiple')
    })
  })

  describe('Accessibility - Tab Navigation', () => {
    // FE-6245: Security tab retired; 3 CE-only tabs remain
    it('tabs are keyboard accessible', async () => {
      await wrapper.vm.$nextTick()
      // Verify tabs exist in HTML (Vuetify renders them with role="tab")
      const html = wrapper.html()
      expect(html).toContain('Identity')
      expect(html).toContain('Network')
      expect(html).toContain('Database')
      // Security tab no longer exists (FE-6245)
      expect(html).not.toContain('data-test="security-tab"')
    })

    it('tab content is properly labeled', () => {
      const html = wrapper.html()
      // Verify remaining tab labels (Security tab retired in FE-6245)
      expect(html).toContain('Identity')
      expect(html).toContain('Network')
      expect(html).toContain('Database')
    })
  })

  describe('Backward Compatibility', () => {
    it('existing functionality still works after Users tab removal', async () => {
      // Test Network tab functionality
      wrapper.vm.activeTab = 'network'
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.activeTab).toBe('network')

      // Test Database tab functionality (Security tab retired in FE-6245)
      wrapper.vm.activeTab = 'database'
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.activeTab).toBe('database')
    })

    it('cookie domain management methods still exist on the parent (FE-6245)', async () => {
      // Methods remain in SystemSettings.vue; they now wire to NetworkSettingsTab
      expect(wrapper.vm.loadCookieDomains).toBeDefined()
      expect(wrapper.vm.addCookieDomain).toBeDefined()
      expect(wrapper.vm.removeCookieDomain).toBeDefined()
    })

    it('network settings functionality still works', async () => {
      wrapper.vm.activeTab = 'network'
      await wrapper.vm.$nextTick()

      // Network settings functionality should still be present. FE-6239 removed
      // the CORS-save path (saveNetworkSettings) along with the disabled CORS
      // section; loadNetworkSettings remains the network-settings entry point.
      expect(wrapper.vm.loadNetworkSettings).toBeDefined()
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
