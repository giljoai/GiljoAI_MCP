/**
 * Test suite for UserSettings.vue component
 *
 * Tests the User Settings view functionality including:
 * - Startup settings (quick start, intro tour)
 * - Notification settings (position, duration, silence threshold)
 * - Agents tab (TemplateManager component)
 * - Context tab (ContextPriorityConfig component)
 * - API Keys tab (ApiKeyManager component)
 * - Integrations tab (MCP, Serena, Git, Claude Code Export)
 *
 * Post-refactor notes:
 * - Tab names: Startup, Notifications, Agents, Context, API Keys, Integrations (6 tabs)
 * - "Setup" renamed to "Startup", "Appearance" tab removed
 * - Uses v-btn-toggle for tab navigation (not v-tabs)
 * - data-test="startup-settings" (not "general-settings")
 * - data-test="notification-settings", "notification-position-select"
 * - data-test="reset-notification-btn", "save-notification-btn"
 * - Uses useWebSocketV2 composable and setupService
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { createPinia, setActivePinia } from 'pinia'
import UserSettings from '@/views/UserSettings.vue'

// Mock dependencies
vi.mock('vue-router', () => ({
  useRouter: () => ({
    currentRoute: { value: { query: {} } },
    push: vi.fn(),
    replace: vi.fn(),
  }),
}))

vi.mock('@/services/api', () => ({
  default: {
    products: {
      getGitIntegration: vi.fn().mockResolvedValue({ data: { enabled: false } }),
      updateGitIntegration: vi.fn().mockResolvedValue({ data: { enabled: false } }),
    },
  },
}))

vi.mock('@/services/setupService', () => ({
  default: {
    getSerenaStatus: vi.fn().mockResolvedValue({ enabled: false }),
    toggleSerena: vi.fn().mockResolvedValue({ success: true, enabled: false }),
  },
}))

vi.mock('@/composables/useWebSocket', () => ({
  useWebSocketV2: () => ({
    on: vi.fn(),
    off: vi.fn(),
  }),
}))

describe('UserSettings.vue', () => {
  let vuetify
  let pinia
  let wrapper

  // Stubs for child components
  const childStubs = {
    TemplateManager: { template: '<div>Template Manager Mock</div>' },
    ApiKeyManager: { template: '<div>API Key Manager Mock</div>' },
    ContextPriorityConfig: { template: '<div>Context Config Mock</div>' },
    ClaudeCodeExport: true,
    SlashCommandSetup: true,
    McpIntegrationCard: true,
    SerenaIntegrationCard: true,
    GitIntegrationCard: true,
    GitAdvancedSettingsDialog: true,
    StartupQuickStart: true,
    ProductIntroTour: true,
  }

  beforeEach(() => {
    vuetify = createVuetify({ components, directives })
    pinia = createPinia()
    setActivePinia(pinia)
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
          plugins: [vuetify, pinia],
          stubs: childStubs,
        }
      })

      expect(wrapper.exists()).toBe(true)
    })

    it('displays page title "My Settings"', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, pinia],
          stubs: childStubs,
        }
      })

      expect(wrapper.text()).toContain('My Settings')
    })

    it('displays page subtitle', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, pinia],
          stubs: childStubs,
        }
      })

      expect(wrapper.text()).toContain('Manage your personal preferences')
    })
  })

  describe('Tab Navigation', () => {
    it('renders all 6 tabs', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, pinia],
          stubs: childStubs,
        }
      })

      const text = wrapper.text()
      expect(text).toContain('Startup')
      expect(text).toContain('Notifications')
      expect(text).toContain('Agents')
      expect(text).toContain('Context')
      expect(text).toContain('API Keys')
      expect(text).toContain('Integrations')
    })

    it('defaults to Startup tab', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, pinia],
          stubs: childStubs,
        }
      })

      expect(wrapper.vm.activeTab).toBe('startup')
    })

    it('does NOT render Database tab', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, pinia],
          stubs: childStubs,
        }
      })

      expect(wrapper.text()).not.toContain('Database')
    })

    it('does NOT render Network tab', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, pinia],
          stubs: childStubs,
        }
      })

      expect(wrapper.text()).not.toContain('Network')
    })

    it('does NOT render Appearance tab', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, pinia],
          stubs: childStubs,
        }
      })

      expect(wrapper.text()).not.toContain('Appearance')
    })
  })

  describe('Startup Settings Tab', () => {
    it('renders startup settings panel', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, pinia],
          stubs: childStubs,
        }
      })

      wrapper.vm.activeTab = 'startup'
      await wrapper.vm.$nextTick()

      const startupContent = wrapper.find('[data-test="startup-settings"]')
      expect(startupContent.exists()).toBe(true)
    })
  })

  describe('Notifications Settings Tab', () => {
    it('renders notification settings when tab is selected', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, pinia],
          stubs: childStubs,
        }
      })

      wrapper.vm.activeTab = 'notifications'
      await wrapper.vm.$nextTick()

      const notificationContent = wrapper.find('[data-test="notification-settings"]')
      expect(notificationContent.exists()).toBe(true)
    })

    it('includes notification position selector', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, pinia],
          stubs: childStubs,
        }
      })

      wrapper.vm.activeTab = 'notifications'
      await wrapper.vm.$nextTick()

      const positionSelect = wrapper.find('[data-test="notification-position-select"]')
      expect(positionSelect.exists()).toBe(true)
    })

    it('includes save button for notification settings', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, pinia],
          stubs: childStubs,
        }
      })

      wrapper.vm.activeTab = 'notifications'
      await wrapper.vm.$nextTick()

      const saveBtn = wrapper.find('[data-test="save-notification-btn"]')
      expect(saveBtn.exists()).toBe(true)
    })

    it('includes reset button for notification settings', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, pinia],
          stubs: childStubs,
        }
      })

      wrapper.vm.activeTab = 'notifications'
      await wrapper.vm.$nextTick()

      const resetBtn = wrapper.find('[data-test="reset-notification-btn"]')
      expect(resetBtn.exists()).toBe(true)
    })

    it('includes silence threshold input', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, pinia],
          stubs: childStubs,
        }
      })

      wrapper.vm.activeTab = 'notifications'
      await wrapper.vm.$nextTick()

      const thresholdInput = wrapper.find('[data-test="silence-threshold-input"]')
      expect(thresholdInput.exists()).toBe(true)
    })
  })

  describe('Agents Tab', () => {
    it('renders TemplateManager component', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, pinia],
          stubs: {
            ...childStubs,
            TemplateManager: { template: '<div data-test="template-manager-stub">Template Manager Mock</div>' },
          },
        }
      })

      wrapper.vm.activeTab = 'agents'
      await wrapper.vm.$nextTick()

      const templateManager = wrapper.find('[data-test="template-manager-stub"]')
      expect(templateManager.exists()).toBe(true)
    })
  })

  describe('Integrations Tab Content', () => {
    it('renders Integrations content', async () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, pinia],
          stubs: childStubs,
        }
      })

      wrapper.vm.activeTab = 'integrations'
      await wrapper.vm.$nextTick()

      expect(wrapper.text()).toContain('Integrations')
    })
  })

  describe('Settings State', () => {
    it('has notification settings with default values', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, pinia],
          stubs: childStubs,
        }
      })

      expect(wrapper.vm.settings.notifications.position).toBe('bottom-right')
      expect(wrapper.vm.settings.notifications.duration).toBe(5)
      expect(wrapper.vm.settings.notifications.agent_silence_threshold_minutes).toBe(10)
    })

    it('has serenaEnabled ref', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, pinia],
          stubs: childStubs,
        }
      })

      expect(wrapper.vm.serenaEnabled).toBe(false)
    })

    it('has toggleSerena method', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, pinia],
          stubs: childStubs,
        }
      })

      expect(typeof wrapper.vm.toggleSerena).toBe('function')
    })

    it('has resetNotificationSettings method', () => {
      wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify, pinia],
          stubs: childStubs,
        }
      })

      expect(typeof wrapper.vm.resetNotificationSettings).toBe('function')
    })
  })
})
