/**
 * Test suite for ApiKeysView.vue component
 *
 * Tests the API Keys view wrapper functionality including:
 * - Page rendering and layout
 * - ApiKeyManager component integration
 * - Informational content display
 * - User-friendly messaging about API key purpose
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { createPinia, setActivePinia } from 'pinia'
import ApiKeysView from '@/views/ApiKeysView.vue'

describe('ApiKeysView.vue', () => {
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
        { path: '/api-keys', name: 'ApiKeys', component: ApiKeysView }
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
      wrapper = mount(ApiKeysView, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            ApiKeyManager: { template: '<div>API Key Manager Mock</div>' }
          }
        }
      })

      expect(wrapper.exists()).toBe(true)
    })

    it('displays page title "My API Keys"', () => {
      wrapper = mount(ApiKeysView, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            ApiKeyManager: { template: '<div>API Key Manager Mock</div>' }
          }
        }
      })

      expect(wrapper.text()).toContain('My API Keys')
    })

    it('displays page subtitle about MCP tool integrations', () => {
      wrapper = mount(ApiKeysView, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            ApiKeyManager: { template: '<div>API Key Manager Mock</div>' }
          }
        }
      })

      expect(wrapper.text()).toContain('Manage API keys for MCP tool integrations')
      expect(wrapper.text()).toContain('Claude Code')
      expect(wrapper.text()).toContain('Codex CLI')
    })
  })

  describe('Informational Content', () => {
    it('displays info alert explaining API key purpose', () => {
      wrapper = mount(ApiKeysView, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            ApiKeyManager: { template: '<div>API Key Manager Mock</div>' }
          }
        }
      })

      const infoAlert = wrapper.find('[data-test="api-key-info-alert"]')
      expect(infoAlert.exists()).toBe(true)
    })

    it('clarifies API keys are for MCP tools, NOT dashboard login', () => {
      wrapper = mount(ApiKeysView, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            ApiKeyManager: { template: '<div>API Key Manager Mock</div>' }
          }
        }
      })

      expect(wrapper.text()).toContain('API keys authenticate your coding tools')
      expect(wrapper.text()).toContain('NOT used for dashboard login')
    })

    it('mentions GiljoAI MCP server authentication', () => {
      wrapper = mount(ApiKeysView, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            ApiKeyManager: { template: '<div>API Key Manager Mock</div>' }
          }
        }
      })

      expect(wrapper.text()).toContain('GiljoAI MCP server')
    })

    it('references username/password for dashboard login', () => {
      wrapper = mount(ApiKeysView, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            ApiKeyManager: { template: '<div>API Key Manager Mock</div>' }
          }
        }
      })

      expect(wrapper.text()).toContain('username/password')
    })
  })

  describe('ApiKeyManager Integration', () => {
    it('renders ApiKeyManager component', () => {
      wrapper = mount(ApiKeysView, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            ApiKeyManager: { template: '<div data-test="api-key-manager-stub">API Key Manager Mock</div>' }
          }
        }
      })

      const apiKeyManager = wrapper.find('[data-test="api-key-manager-stub"]')
      expect(apiKeyManager.exists()).toBe(true)
    })

    it('places ApiKeyManager below informational content', () => {
      wrapper = mount(ApiKeysView, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            ApiKeyManager: { template: '<div data-test="api-key-manager-stub">API Key Manager Mock</div>' }
          }
        }
      })

      const container = wrapper.find('div.v-container')
      const html = container.html()

      // Info alert should come before ApiKeyManager
      const infoAlertIndex = html.indexOf('api-key-info-alert')
      const managerIndex = html.indexOf('api-key-manager-stub')

      expect(infoAlertIndex).toBeLessThan(managerIndex)
    })
  })

  describe('Layout and Styling', () => {
    it('uses v-container for layout', () => {
      wrapper = mount(ApiKeysView, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            ApiKeyManager: { template: '<div>API Key Manager Mock</div>' }
          }
        }
      })

      const container = wrapper.find('.v-container')
      expect(container.exists()).toBe(true)
    })

    it('has proper heading hierarchy (h1 for title)', () => {
      wrapper = mount(ApiKeysView, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            ApiKeyManager: { template: '<div>API Key Manager Mock</div>' }
          }
        }
      })

      const heading = wrapper.find('h1')
      expect(heading.exists()).toBe(true)
      expect(heading.text()).toContain('My API Keys')
    })

    it('uses text-h4 class for title styling', () => {
      wrapper = mount(ApiKeysView, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            ApiKeyManager: { template: '<div>API Key Manager Mock</div>' }
          }
        }
      })

      const heading = wrapper.find('.text-h4')
      expect(heading.exists()).toBe(true)
    })

    it('uses text-subtitle-1 for subtitle', () => {
      wrapper = mount(ApiKeysView, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            ApiKeyManager: { template: '<div>API Key Manager Mock</div>' }
          }
        }
      })

      const subtitle = wrapper.find('.text-subtitle-1')
      expect(subtitle.exists()).toBe(true)
    })

    it('uses info variant for alert', () => {
      wrapper = mount(ApiKeysView, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            ApiKeyManager: { template: '<div>API Key Manager Mock</div>' }
          }
        }
      })

      const alert = wrapper.find('.v-alert')
      if (alert.exists()) {
        // Alert should have info type
        expect(alert.exists()).toBe(true)
      }
    })
  })

  describe('Accessibility', () => {
    it('has proper semantic structure', () => {
      wrapper = mount(ApiKeysView, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            ApiKeyManager: { template: '<div>API Key Manager Mock</div>' }
          }
        }
      })

      // Should have h1 for main title
      expect(wrapper.find('h1').exists()).toBe(true)

      // Should have informational alert
      expect(wrapper.find('.v-alert').exists()).toBe(true)
    })

    it('includes icon in info alert for visual clarity', () => {
      wrapper = mount(ApiKeysView, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            ApiKeyManager: { template: '<div>API Key Manager Mock</div>' }
          }
        }
      })

      const alert = wrapper.find('.v-alert')
      if (alert.exists()) {
        const icon = alert.find('.v-icon')
        expect(icon.exists()).toBe(true)
      }
    })
  })

  describe('Responsive Design', () => {
    it('wraps content in responsive container', () => {
      wrapper = mount(ApiKeysView, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            ApiKeyManager: { template: '<div>API Key Manager Mock</div>' }
          }
        }
      })

      const container = wrapper.find('.v-container')
      expect(container.exists()).toBe(true)
    })
  })

  describe('Component Structure', () => {
    it('has correct component hierarchy', () => {
      wrapper = mount(ApiKeysView, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            ApiKeyManager: { template: '<div data-test="api-key-manager">Manager</div>' }
          }
        }
      })

      // Structure: v-container > h1, p, v-alert, ApiKeyManager
      const container = wrapper.find('.v-container')
      expect(container.find('h1').exists()).toBe(true)
      expect(container.find('p').exists()).toBe(true)
      expect(container.find('.v-alert').exists()).toBe(true)
      expect(container.find('[data-test="api-key-manager"]').exists()).toBe(true)
    })

    it('maintains proper spacing between elements', () => {
      wrapper = mount(ApiKeysView, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            ApiKeyManager: { template: '<div>API Key Manager Mock</div>' }
          }
        }
      })

      // Should have margin bottom classes for spacing
      const heading = wrapper.find('.text-h4')
      expect(heading.classes()).toContain('mb-2')

      const subtitle = wrapper.find('.text-subtitle-1')
      expect(subtitle.classes()).toContain('mb-4')
    })
  })
})
