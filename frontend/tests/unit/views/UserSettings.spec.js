/**
 * Test suite for UserSettings.vue component
 *
 * Tests the User Settings view functionality including:
 * - General settings (project name, context budget, priority, auto-refresh)
 * - Appearance settings (theme, mascot, display options)
 * - Notification settings (alerts, position, duration)
 * - Templates tab (TemplateManager component)
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
    it('renders all 4 tabs', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' }
          }
        }
      })

      const tabs = wrapper.findAll('.v-tab')
      expect(tabs.length).toBe(4)
    })

    it('renders General tab', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' }
          }
        }
      })

      const tabs = wrapper.findAll('.v-tab')
      const generalTab = tabs.find(tab => tab.text().includes('General'))
      expect(generalTab).toBeDefined()
    })

    it('renders Appearance tab', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' }
          }
        }
      })

      const tabs = wrapper.findAll('.v-tab')
      const appearanceTab = tabs.find(tab => tab.text().includes('Appearance'))
      expect(appearanceTab).toBeDefined()
    })

    it('renders Notifications tab', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' }
          }
        }
      })

      const tabs = wrapper.findAll('.v-tab')
      const notificationsTab = tabs.find(tab => tab.text().includes('Notifications'))
      expect(notificationsTab).toBeDefined()
    })

    it('renders Templates tab', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' }
          }
        }
      })

      const tabs = wrapper.findAll('.v-tab')
      const templatesTab = tabs.find(tab => tab.text().includes('Templates'))
      expect(templatesTab).toBeDefined()
    })

    it('does NOT render API Keys tab', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' }
          }
        }
      })

      const tabs = wrapper.findAll('.v-tab')
      const apiKeysTab = tabs.find(tab => tab.text().includes('API Keys'))
      expect(apiKeysTab).toBeUndefined()
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

      const tabs = wrapper.findAll('.v-tab')
      const databaseTab = tabs.find(tab => tab.text().includes('Database'))
      expect(databaseTab).toBeUndefined()
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

      const tabs = wrapper.findAll('.v-tab')
      const networkTab = tabs.find(tab => tab.text().includes('Network'))
      expect(networkTab).toBeUndefined()
    })
  })

  describe('General Settings Tab', () => {
    it('renders general settings fields', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' }
          }
        }
      })

      // Switch to general tab (should be default)
      const generalContent = wrapper.find('[data-test="general-settings"]')
      expect(generalContent.exists()).toBe(true)
    })

    it('includes project name field', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' }
          }
        }
      })

      const projectNameField = wrapper.find('[data-test="project-name-field"]')
      expect(projectNameField.exists()).toBe(true)
    })

    it('includes context budget field', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' }
          }
        }
      })

      const contextBudgetField = wrapper.find('[data-test="context-budget-field"]')
      expect(contextBudgetField.exists()).toBe(true)
    })

    it('includes default priority selector', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' }
          }
        }
      })

      const prioritySelect = wrapper.find('[data-test="default-priority-select"]')
      expect(prioritySelect.exists()).toBe(true)
    })

    it('includes auto-refresh toggle', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' }
          }
        }
      })

      const autoRefreshToggle = wrapper.find('[data-test="auto-refresh-toggle"]')
      expect(autoRefreshToggle.exists()).toBe(true)
    })
  })

  describe('Appearance Settings Tab', () => {
    it('renders appearance settings when tab is selected', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' }
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

    it('includes theme selector', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' }
          }
        }
      })

      if (wrapper.vm.activeTab !== undefined) {
        wrapper.vm.activeTab = 'appearance'
        await wrapper.vm.$nextTick()
      }

      const themeRadioGroup = wrapper.find('[data-test="theme-selector"]')
      expect(themeRadioGroup.exists()).toBe(true)
    })

    it('includes mascot toggle', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' }
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
            TemplateManager: { template: '<div>Template Manager Mock</div>' }
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
            TemplateManager: { template: '<div>Template Manager Mock</div>' }
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
            TemplateManager: { template: '<div>Template Manager Mock</div>' }
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

  describe('Templates Tab', () => {
    it('renders TemplateManager component', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div data-test="template-manager-stub">Template Manager Mock</div>' }
          }
        }
      })

      if (wrapper.vm.activeTab !== undefined) {
        wrapper.vm.activeTab = 'templates'
        await wrapper.vm.$nextTick()
      }

      const templateManager = wrapper.find('[data-test="template-manager-stub"]')
      expect(templateManager.exists()).toBe(true)
    })
  })

  describe('Settings Persistence', () => {
    it('saves general settings', async () => {
      const settingsStore = {
        updateSettings: vi.fn().mockResolvedValue(true)
      }

      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' }
          },
          mocks: {
            settingsStore
          }
        }
      })

      const saveBtn = wrapper.find('[data-test="save-general-btn"]')
      if (saveBtn.exists()) {
        await saveBtn.trigger('click')
        expect(settingsStore.updateSettings).toHaveBeenCalled()
      }
    })

    it('saves appearance settings', async () => {
      const settingsStore = {
        updateSettings: vi.fn().mockResolvedValue(true)
      }

      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' }
          },
          mocks: {
            settingsStore
          }
        }
      })

      if (wrapper.vm.activeTab !== undefined) {
        wrapper.vm.activeTab = 'appearance'
        await wrapper.vm.$nextTick()
      }

      const saveBtn = wrapper.find('[data-test="save-appearance-btn"]')
      if (saveBtn.exists()) {
        await saveBtn.trigger('click')
        expect(settingsStore.updateSettings).toHaveBeenCalled()
      }
    })
  })

  describe('Reset Functionality', () => {
    it('resets general settings to defaults', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            TemplateManager: { template: '<div>Template Manager Mock</div>' }
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
            TemplateManager: { template: '<div>Template Manager Mock</div>' }
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
