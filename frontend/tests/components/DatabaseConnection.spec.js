/**
 * Test suite for DatabaseConnection component
 * TDD approach: Tests written BEFORE implementation
 *
 * This component is extracted from SettingsView.vue and reusable in:
 * 1. Settings page (database tab)
 * 2. Setup wizard (database verification step)
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import DatabaseConnection from '@/components/DatabaseConnection.vue'
import api from '@/services/api'

describe('DatabaseConnection Component', () => {
  let vuetify
  let wrapper

  beforeEach(() => {
    vuetify = createVuetify({
      components,
      directives,
    })
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
    vi.clearAllMocks()
  })

  describe('Component Rendering', () => {
    it('should render without errors', () => {
      wrapper = mount(DatabaseConnection, {
        global: {
          plugins: [vuetify]
        }
      })

      expect(wrapper.exists()).toBe(true)
    })

    it('should display info banner text as subtitle when showInfoBanner is true', () => {
      wrapper = mount(DatabaseConnection, {
        props: {
          showTitle: true,
          showInfoBanner: true,
          infoBannerText: 'Database settings are configured during installation'
        },
        global: {
          plugins: [vuetify]
        }
      })

      expect(wrapper.text()).toContain('Database settings are configured during installation')
    })

    it('should render all database configuration fields', () => {
      wrapper = mount(DatabaseConnection, {
        global: {
          plugins: [vuetify]
        }
      })

      const hostField = wrapper.find('[data-test="db-host"]')
      const portField = wrapper.find('[data-test="db-port"]')
      const nameField = wrapper.find('[data-test="db-name"]')
      const userField = wrapper.find('[data-test="db-user"]')
      const passwordField = wrapper.find('[data-test="db-password"]')

      expect(hostField.exists()).toBe(true)
      expect(portField.exists()).toBe(true)
      expect(nameField.exists()).toBe(true)
      expect(userField.exists()).toBe(true)
      expect(passwordField.exists()).toBe(true)
    })

    it('should render test connection button', () => {
      wrapper = mount(DatabaseConnection, {
        global: {
          plugins: [vuetify]
        }
      })

      const testButton = wrapper.find('[data-test="test-connection-btn"]')
      expect(testButton.exists()).toBe(true)
      expect(testButton.text()).toContain('Test Connection')
    })
  })

  describe('Props Configuration', () => {
    it('should display readonly fields when readonly prop is true', () => {
      wrapper = mount(DatabaseConnection, {
        props: {
          readonly: true
        },
        global: {
          plugins: [vuetify]
        }
      })

      const hostField = wrapper.find('[data-test="db-host"]')
      // Vuetify adds readonly to the component prop, check HTML includes readonly
      expect(hostField.html()).toContain('readonly')
    })

    it('should display editable fields when readonly prop is false', () => {
      wrapper = mount(DatabaseConnection, {
        props: {
          readonly: false
        },
        global: {
          plugins: [vuetify]
        }
      })

      const hostField = wrapper.find('[data-test="db-host"]')
      expect(hostField.attributes('readonly')).toBeUndefined()
    })

    it('should show lock icons when readonly is true', () => {
      wrapper = mount(DatabaseConnection, {
        props: {
          readonly: true
        },
        global: {
          plugins: [vuetify]
        }
      })

      // The component uses prepend-inner-icon="mdi-lock" on text fields when readonly
      const html = wrapper.html()
      expect(html).toContain('mdi-lock')
    })

    it('should show test button when showTestButton prop is true', () => {
      wrapper = mount(DatabaseConnection, {
        props: {
          showTestButton: true
        },
        global: {
          plugins: [vuetify]
        }
      })

      const testButton = wrapper.find('[data-test="test-connection-btn"]')
      expect(testButton.exists()).toBe(true)
    })

    it('should hide test button when showTestButton prop is false', () => {
      wrapper = mount(DatabaseConnection, {
        props: {
          showTestButton: false
        },
        global: {
          plugins: [vuetify]
        }
      })

      const testButton = wrapper.find('[data-test="test-connection-btn"]')
      expect(testButton.exists()).toBe(false)
    })

    it('should display custom title when provided', () => {
      const customTitle = 'My Custom Database Title'
      wrapper = mount(DatabaseConnection, {
        props: {
          showTitle: true,
          title: customTitle
        },
        global: {
          plugins: [vuetify]
        }
      })

      expect(wrapper.text()).toContain(customTitle)
    })

    it('should display custom info banner text as subtitle', () => {
      const customBannerText = 'Custom banner message here'
      wrapper = mount(DatabaseConnection, {
        props: {
          showTitle: true,
          showInfoBanner: true,
          infoBannerText: customBannerText
        },
        global: {
          plugins: [vuetify]
        }
      })

      expect(wrapper.text()).toContain(customBannerText)
    })
  })

  describe('Connection Testing', () => {
    it('should call API when test button is clicked', async () => {
      api.settings.testDatabase.mockResolvedValue({
        data: { success: true, message: 'Connected successfully' }
      })

      wrapper = mount(DatabaseConnection, {
        global: {
          plugins: [vuetify]
        }
      })

      const testButton = wrapper.find('[data-test="test-connection-btn"]')
      await testButton.trigger('click')
      await wrapper.vm.$nextTick()

      expect(api.settings.testDatabase).toHaveBeenCalled()
    })

    it('should show loading state during connection test', async () => {
      api.settings.testDatabase.mockImplementation(() =>
        new Promise(resolve =>
          setTimeout(() =>
            resolve({ data: { success: true } }),
            100
          )
        )
      )

      wrapper = mount(DatabaseConnection, {
        global: {
          plugins: [vuetify]
        }
      })

      const testButton = wrapper.find('[data-test="test-connection-btn"]')
      await testButton.trigger('click')

      // Button should be in loading state
      expect(wrapper.vm.testing).toBe(true)

      await vi.waitFor(() => expect(wrapper.vm.testing).toBe(false), { timeout: 200 })
    })

    it('should display success message on successful connection', async () => {
      api.settings.testDatabase.mockResolvedValue({
        data: { success: true, message: 'Connected to PostgreSQL' }
      })

      wrapper = mount(DatabaseConnection, {
        global: {
          plugins: [vuetify]
        }
      })

      const testButton = wrapper.find('[data-test="test-connection-btn"]')
      await testButton.trigger('click')
      await wrapper.vm.$nextTick()

      const successAlert = wrapper.find('[data-test="test-result"]')
      expect(successAlert.exists()).toBe(true)
      expect(successAlert.text()).toContain('Connected to PostgreSQL')
      // Vuetify 3 uses different class naming
      expect(successAlert.html()).toContain('success')
    })

    it('should display error message on failed connection', async () => {
      const errorMessage = 'Database connection failed'
      api.settings.testDatabase.mockResolvedValue({
        data: { success: false, error: errorMessage }
      })

      wrapper = mount(DatabaseConnection, {
        global: {
          plugins: [vuetify]
        }
      })

      const testButton = wrapper.find('[data-test="test-connection-btn"]')
      await testButton.trigger('click')
      await wrapper.vm.$nextTick()

      const errorAlert = wrapper.find('[data-test="test-result"]')
      expect(errorAlert.exists()).toBe(true)
      expect(errorAlert.text()).toContain(errorMessage)
      // Vuetify 3 uses different class naming
      expect(errorAlert.html()).toContain('error')
    })

    it('should handle network errors gracefully', async () => {
      api.settings.testDatabase.mockRejectedValue(new Error('Network error'))

      wrapper = mount(DatabaseConnection, {
        global: {
          plugins: [vuetify]
        }
      })

      const testButton = wrapper.find('[data-test="test-connection-btn"]')
      await testButton.trigger('click')
      await wrapper.vm.$nextTick()

      const errorAlert = wrapper.find('[data-test="test-result"]')
      expect(errorAlert.exists()).toBe(true)
      // Vuetify 3 uses different class naming
      expect(errorAlert.html()).toContain('error')
    })
  })

  describe('Events', () => {
    it('should emit "connection-success" event on successful test', async () => {
      api.settings.testDatabase.mockResolvedValue({
        data: { success: true, message: 'Connected successfully' }
      })

      wrapper = mount(DatabaseConnection, {
        global: {
          plugins: [vuetify]
        }
      })

      const testButton = wrapper.find('[data-test="test-connection-btn"]')
      await testButton.trigger('click')
      await wrapper.vm.$nextTick()

      expect(wrapper.emitted('connection-success')).toBeTruthy()
      expect(wrapper.emitted('connection-success')[0][0]).toEqual(
        expect.objectContaining({
          success: true
        })
      )
    })

    it('should emit "connection-error" event on failed test', async () => {
      api.settings.testDatabase.mockResolvedValue({
        data: { success: false, error: 'Connection failed' }
      })

      wrapper = mount(DatabaseConnection, {
        global: {
          plugins: [vuetify]
        }
      })

      const testButton = wrapper.find('[data-test="test-connection-btn"]')
      await testButton.trigger('click')
      await wrapper.vm.$nextTick()

      expect(wrapper.emitted('connection-error')).toBeTruthy()
      expect(wrapper.emitted('connection-error')[0][0]).toEqual(
        expect.objectContaining({
          success: false
        })
      )
    })

    it('should emit "tested" event when test completes (success or failure)', async () => {
      api.settings.testDatabase.mockResolvedValue({
        data: { success: true }
      })

      wrapper = mount(DatabaseConnection, {
        global: {
          plugins: [vuetify]
        }
      })

      const testButton = wrapper.find('[data-test="test-connection-btn"]')
      await testButton.trigger('click')
      await wrapper.vm.$nextTick()

      expect(wrapper.emitted('tested')).toBeTruthy()
    })
  })

  describe('Accessibility', () => {
    it('should have proper ARIA labels on form fields', () => {
      wrapper = mount(DatabaseConnection, {
        global: {
          plugins: [vuetify]
        }
      })

      const hostField = wrapper.find('[data-test="db-host"]')
      const portField = wrapper.find('[data-test="db-port"]')

      // Vuetify wraps the input, so check for aria-label on the component or its label
      expect(hostField.exists()).toBe(true)
      expect(portField.exists()).toBe(true)

      // Check if labels exist
      const hostLabel = hostField.find('label')
      const portLabel = portField.find('label')
      expect(hostLabel.exists() || hostField.html().includes('aria-label')).toBe(true)
      expect(portLabel.exists() || portField.html().includes('aria-label')).toBe(true)
    })

    it('should be keyboard navigable', async () => {
      wrapper = mount(DatabaseConnection, {
        global: {
          plugins: [vuetify]
        },
        attachTo: document.body
      })

      const testButton = wrapper.find('[data-test="test-connection-btn"]')

      // Tab to focus button
      testButton.element.focus()
      expect(document.activeElement).toBe(testButton.element)

      wrapper.unmount()
    })

    it('should announce status changes to screen readers', async () => {
      api.settings.testDatabase.mockResolvedValue({
        data: { success: true, message: 'Connected successfully' }
      })

      wrapper = mount(DatabaseConnection, {
        global: {
          plugins: [vuetify]
        }
      })

      const testButton = wrapper.find('[data-test="test-connection-btn"]')
      await testButton.trigger('click')
      await wrapper.vm.$nextTick()

      const resultAlert = wrapper.find('[data-test="test-result"]')
      expect(resultAlert.attributes('role')).toBe('alert')
      expect(resultAlert.attributes('aria-live')).toBeTruthy()
    })
  })

  describe('Slots', () => {
    it('should render actions slot content', () => {
      const slotContent = '<button id="custom-action">Custom Action</button>'
      wrapper = mount(DatabaseConnection, {
        slots: {
          actions: slotContent
        },
        global: {
          plugins: [vuetify]
        }
      })

      expect(wrapper.html()).toContain('custom-action')
    })
  })

  describe('Component Reusability', () => {
    it('should work in wizard context with wizard-style props', () => {
      wrapper = mount(DatabaseConnection, {
        props: {
          readonly: true,
          showTestButton: true,
          testButtonText: 'Test Database Connection',
          showTitle: false
        },
        global: {
          plugins: [vuetify]
        }
      })

      const testButton = wrapper.find('[data-test="test-connection-btn"]')
      expect(testButton.exists()).toBe(true)
      expect(testButton.text()).toContain('Test Database Connection')
    })

    it('should work in settings context with settings-style props', () => {
      wrapper = mount(DatabaseConnection, {
        props: {
          readonly: true,
          showTestButton: true,
          showTitle: true,
          title: 'PostgreSQL Database Configuration'
        },
        global: {
          plugins: [vuetify]
        }
      })

      expect(wrapper.text()).toContain('PostgreSQL Database Configuration')
    })
  })

  describe('Initial Settings', () => {
    it('should load settings from config on mount when initialSettings not provided', async () => {
      api.settings.getDatabase.mockResolvedValue({
        data: {
          host: 'localhost',
          port: 5432,
          name: 'giljo_mcp',
          user: 'postgres'
        }
      })

      wrapper = mount(DatabaseConnection, {
        global: {
          plugins: [vuetify]
        }
      })

      await wrapper.vm.$nextTick()

      expect(api.settings.getDatabase).toHaveBeenCalled()
    })

    it('should use initialSettings prop when provided', async () => {
      const initialSettings = {
        host: 'custom-host',
        port: 5433,
        name: 'custom_db',
        user: 'custom_user',
        password: '********'
      }

      wrapper = mount(DatabaseConnection, {
        props: {
          initialSettings
        },
        global: {
          plugins: [vuetify]
        }
      })

      await wrapper.vm.$nextTick()

      // Check the component's internal state instead of DOM
      expect(wrapper.vm.dbConfig.host).toBe(initialSettings.host)
    })
  })

  describe('Password Security', () => {
    it('should mask password field', () => {
      wrapper = mount(DatabaseConnection, {
        global: {
          plugins: [vuetify]
        }
      })

      const passwordField = wrapper.find('[data-test="db-password"]')
      // Check if type="password" exists in the rendered HTML
      expect(passwordField.html()).toContain('type="password"')
    })

    it('should always show masked password (********)', async () => {
      wrapper = mount(DatabaseConnection, {
        props: {
          initialSettings: {
            password: 'any_actual_password'
          }
        },
        global: {
          plugins: [vuetify]
        }
      })

      await wrapper.vm.$nextTick()

      // Check the component's internal state
      expect(wrapper.vm.dbConfig.password).toBe('********')
    })
  })
})
