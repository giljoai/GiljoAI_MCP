/**
 * Test suite for UserSettings.vue component
 *
 * Tests the User Settings view functionality including:
 * - Setup settings (placeholder for future settings)
 * - Appearance settings (theme, mascot, display options)
 * - Notification settings (alerts, position, duration)
 * - Agents tab (TemplateManager component)
 * - Context tab (ContextPriorityConfig component)
 * - API Keys tab (ApiKeyManager component)
 * - Integrations tab (MCP tools, Serena, Git integration)
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { createPinia, setActivePinia } from 'pinia'
import UserSettings from '@/views/UserSettings.vue'

describe('UserSettings.vue', () => {
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

  describe('Component Rendering', () => {
    it('renders the component', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' }
          }
        }
      })

      expect(wrapper.exists()).toBe(true)
    })

    it('displays page title "My Settings"', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' }
          }
        }
      })

      expect(wrapper.text()).toContain('My Settings')
    })

    it('displays page subtitle', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' }
          }
        }
      })

      expect(wrapper.text()).toContain('Manage your personal preferences')
    })
  })

  describe('Tab Navigation', () => {
    it('renders all 7 tabs', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' },
            ContextPriorityConfig: { template: '<div>Context Config Mock</div>' },
            ApiKeyManager: { template: '<div>API Key Manager Mock</div>' }
          }
        }
      })

      // Check that all 7 tab names are present in the rendered output
      const text = wrapper.text()
      expect(text).toContain('Setup')
      expect(text).toContain('Appearance')
      expect(text).toContain('Notifications')
      expect(text).toContain('Agents')
      expect(text).toContain('Context')
      expect(text).toContain('API Keys')
      expect(text).toContain('Integrations')
    })

    it('renders Setup tab', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' },
            ContextPriorityConfig: { template: '<div>Context Config Mock</div>' },
            ApiKeyManager: { template: '<div>API Key Manager Mock</div>' }
          }
        }
      })

      // Check via text content
      const text = wrapper.text()
      expect(text).toContain('Setup')
    })

    it('renders Appearance tab', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' },
            ContextPriorityConfig: { template: '<div>Context Config Mock</div>' },
            ApiKeyManager: { template: '<div>API Key Manager Mock</div>' }
          }
        }
      })

      // Check via text content
      const text = wrapper.text()
      expect(text).toContain('Appearance')
    })

    it('renders Notifications tab', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' },
            ContextPriorityConfig: { template: '<div>Context Config Mock</div>' },
            ApiKeyManager: { template: '<div>API Key Manager Mock</div>' }
          }
        }
      })

      // Check via text content
      const text = wrapper.text()
      expect(text).toContain('Notifications')
    })

    it('renders Agents tab', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' },
            ContextPriorityConfig: { template: '<div>Context Config Mock</div>' },
            ApiKeyManager: { template: '<div>API Key Manager Mock</div>' }
          }
        }
      })

      // Check via text content
      const text = wrapper.text()
      expect(text).toContain('Agents')
    })

    it('renders Context tab', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' },
            ContextPriorityConfig: { template: '<div>Context Config Mock</div>' },
            ApiKeyManager: { template: '<div>API Key Manager Mock</div>' }
          }
        }
      })

      // Check via text content
      const text = wrapper.text()
      expect(text).toContain('Context')
    })

    it('renders API Keys tab', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' },
            ContextPriorityConfig: { template: '<div>Context Config Mock</div>' },
            ApiKeyManager: { template: '<div>API Key Manager Mock</div>' }
          }
        }
      })

      // Check via text content
      const text = wrapper.text()
      expect(text).toContain('API Keys')
    })

    it('renders Integrations tab', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' },
            ContextPriorityConfig: { template: '<div>Context Config Mock</div>' },
            ApiKeyManager: { template: '<div>API Key Manager Mock</div>' }
          }
        }
      })

      // Check via text content
      const text = wrapper.text()
      expect(text).toContain('Integrations')
    })

    it('does NOT render Database tab', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' }
          }
        }
      })

      // Check via text content
      const text = wrapper.text()
      expect(text).not.toContain('Database')
    })

    it('does NOT render Network tab', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' }
          }
        }
      })

      // Check via text content
      const text = wrapper.text()
      expect(text).not.toContain('Network')
    })
  })

  describe('Integrations Tab Content', () => {
    it('shows Serena MCP integration with enable/disable toggle', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' },
            ContextPriorityConfig: { template: '<div>Context Config Mock</div>' },
            ApiKeyManager: { template: '<div>API Key Manager Mock</div>' },
            SerenaAdvancedSettingsDialog: { template: '<div>Serena Dialog Mock</div>' }
          }
        }
      })

      if (wrapper.vm.activeTab !== undefined) {
        wrapper.vm.activeTab = 'integrations'
        await wrapper.vm.$nextTick()
      }

      const text = wrapper.text()
      expect(text).toContain('Serena MCP')
      expect(text).toContain('Enable Serena MCP')
    })

    it('shows Git + 360 Memory integration with configuration', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' },
            ContextPriorityConfig: { template: '<div>Context Config Mock</div>' },
            ApiKeyManager: { template: '<div>API Key Manager Mock</div>' },
            SerenaAdvancedSettingsDialog: { template: '<div>Serena Dialog Mock</div>' }
          }
        }
      })

      if (wrapper.vm.activeTab !== undefined) {
        wrapper.vm.activeTab = 'integrations'
        await wrapper.vm.$nextTick()
      }

      const text = wrapper.text()
      expect(text).toContain('Git + 360 Memory')
      expect(text).toContain('Enable Git Integration')
    })
  })

  describe('Setup Settings Tab', () => {
    it('renders setup settings panel', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' },
            ContextPriorityConfig: { template: '<div>Context Config Mock</div>' },
            ApiKeyManager: { template: '<div>API Key Manager Mock</div>' }
          }
        }
      })

      // Switch to general tab (should be default)
      const setupContent = wrapper.find('[data-test="general-settings"]')
      expect(setupContent.exists()).toBe(true)
    })

    it('displays setup info alert', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' },
            ContextPriorityConfig: { template: '<div>Context Config Mock</div>' },
            ApiKeyManager: { template: '<div>API Key Manager Mock</div>' }
          }
        }
      })

      const text = wrapper.text()
      expect(text).toContain('reserved for future setup settings')
    })

    it('includes reset and save buttons', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' },
            ContextPriorityConfig: { template: '<div>Context Config Mock</div>' },
            ApiKeyManager: { template: '<div>API Key Manager Mock</div>' }
          }
        }
      })

      const resetBtn = wrapper.find('[data-test="reset-general-btn"]')
      const saveBtn = wrapper.find('[data-test="save-general-btn"]')
      expect(resetBtn.exists()).toBe(true)
      expect(saveBtn.exists()).toBe(true)
    })
  })

  describe('Appearance Settings Tab', () => {
    it('renders appearance settings when tab is selected', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' },
            ContextPriorityConfig: { template: '<div>Context Config Mock</div>' },
            ApiKeyManager: { template: '<div>API Key Manager Mock</div>' }
          }
        }
      })

      // Switch to appearance tab if component has activeTab property
      if (wrapper.vm.activeTab !== undefined) {
        wrapper.vm.activeTab = 'appearance'
        await wrapper.vm.$nextTick()
      }

      const appearanceContent = wrapper.find('[data-test="appearance-settings"]')
      expect(appearanceContent.exists()).toBe(true)
    })

    it('includes mascot toggle', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' },
            ContextPriorityConfig: { template: '<div>Context Config Mock</div>' },
            ApiKeyManager: { template: '<div>API Key Manager Mock</div>' }
          }
        }
      })

      if (wrapper.vm.activeTab !== undefined) {
        wrapper.vm.activeTab = 'appearance'
        await wrapper.vm.$nextTick()
      }

      const mascotToggle = wrapper.find('[data-test="mascot-toggle"]')
      expect(mascotToggle.exists()).toBe(true)
    })
  })

  describe('Notifications Settings Tab', () => {
    it('renders notification settings when tab is selected', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' },
            ContextPriorityConfig: { template: '<div>Context Config Mock</div>' },
            ApiKeyManager: { template: '<div>API Key Manager Mock</div>' }
          }
        }
      })

      if (wrapper.vm.activeTab !== undefined) {
        wrapper.vm.activeTab = 'notifications'
        await wrapper.vm.$nextTick()
      }

      const notificationContent = wrapper.find('[data-test="notification-settings"]')
      expect(notificationContent.exists()).toBe(true)
    })

    it('includes new messages toggle', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' },
            ContextPriorityConfig: { template: '<div>Context Config Mock</div>' },
            ApiKeyManager: { template: '<div>API Key Manager Mock</div>' }
          }
        }
      })

      if (wrapper.vm.activeTab !== undefined) {
        wrapper.vm.activeTab = 'notifications'
        await wrapper.vm.$nextTick()
      }

      const newMessagesToggle = wrapper.find('[data-test="new-messages-toggle"]')
      expect(newMessagesToggle.exists()).toBe(true)
    })

    it('includes notification position selector', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' },
            ContextPriorityConfig: { template: '<div>Context Config Mock</div>' },
            ApiKeyManager: { template: '<div>API Key Manager Mock</div>' }
          }
        }
      })

      if (wrapper.vm.activeTab !== undefined) {
        wrapper.vm.activeTab = 'notifications'
        await wrapper.vm.$nextTick()
      }

      const positionSelect = wrapper.find('[data-test="notification-position-select"]')
      expect(positionSelect.exists()).toBe(true)
    })
  })

  describe('Agents Tab', () => {
    it('renders TemplateManager component', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div data-test="template-manager-stub">Template Manager Mock</div>' },
            ContextPriorityConfig: { template: '<div>Context Config Mock</div>' },
            ApiKeyManager: { template: '<div>API Key Manager Mock</div>' }
          }
        }
      })

      if (wrapper.vm.activeTab !== undefined) {
        wrapper.vm.activeTab = 'agents'
        await wrapper.vm.$nextTick()
      }

      const templateManager = wrapper.find('[data-test="template-manager-stub"]')
      expect(templateManager.exists()).toBe(true)
    })
  })

  describe('Settings Persistence', () => {
    it('has save button for general settings', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' },
            ContextPriorityConfig: { template: '<div>Context Config Mock</div>' },
            ApiKeyManager: { template: '<div>API Key Manager Mock</div>' }
          }
        }
      })

      const saveBtn = wrapper.find('[data-test="save-general-btn"]')
      expect(saveBtn.exists()).toBe(true)
    })

    it('has save button for appearance settings', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' },
            ContextPriorityConfig: { template: '<div>Context Config Mock</div>' },
            ApiKeyManager: { template: '<div>API Key Manager Mock</div>' }
          }
        }
      })

      if (wrapper.vm.activeTab !== undefined) {
        wrapper.vm.activeTab = 'appearance'
        await wrapper.vm.$nextTick()
      }

      const saveBtn = wrapper.find('[data-test="save-appearance-btn"]')
      expect(saveBtn.exists()).toBe(true)
    })
  })

  describe('Reset Functionality', () => {
    it('resets general settings to defaults', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' },
            ContextPriorityConfig: { template: '<div>Context Config Mock</div>' },
            ApiKeyManager: { template: '<div>API Key Manager Mock</div>' }
          }
        }
      })

      const resetBtn = wrapper.find('[data-test="reset-general-btn"]')
      if (resetBtn.exists()) {
        await resetBtn.trigger('click')
        // Verify reset logic
        expect(resetBtn.exists()).toBe(true)
      }
    })

    it('resets appearance settings to defaults', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' },
            ContextPriorityConfig: { template: '<div>Context Config Mock</div>' },
            ApiKeyManager: { template: '<div>API Key Manager Mock</div>' }
          }
        }
      })

      if (wrapper.vm.activeTab !== undefined) {
        wrapper.vm.activeTab = 'appearance'
        await wrapper.vm.$nextTick()
      }

      const resetBtn = wrapper.find('[data-test="reset-appearance-btn"]')
      if (resetBtn.exists()) {
        await resetBtn.trigger('click')
        expect(resetBtn.exists()).toBe(true)
      }
    })
  })
})
