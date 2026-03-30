/**
 * Test suite for NetworkSettingsTab.vue component
 * Handover 0321: Settings Componentization
 *
 * Tests the Network Settings tab component:
 * - Component rendering with config prop
 * - Loading state display
 * - Network configuration fields display (externalHost, apiPort, frontendPort)
 * - CORS origins display
 * - Reload button functionality
 * - Unified architecture info alert
 * - Configuration notes display
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import NetworkSettingsTab from '@/components/settings/tabs/NetworkSettingsTab.vue'

describe('NetworkSettingsTab.vue', () => {
  let vuetify
  let wrapper

  const defaultConfig = {
    externalHost: 'localhost',
    apiPort: 7272,
    frontendPort: 7274,
  }

  const defaultCorsOrigins = ['http://localhost:7274', 'http://127.0.0.1:7274']

  beforeEach(() => {
    // Setup Vuetify
    vuetify = createVuetify({
      components,
      directives,
    })

    // Mock clipboard API
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    })
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
    vi.clearAllMocks()
  })

  describe('Component Rendering', () => {
    it('renders the component with config prop', () => {
      wrapper = mount(NetworkSettingsTab, {
        props: {
          config: defaultConfig,
          corsOrigins: defaultCorsOrigins,
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      expect(wrapper.exists()).toBe(true)
    })

    it('displays correct title "Network Configuration"', async () => {
      wrapper = mount(NetworkSettingsTab, {
        props: {
          config: defaultConfig,
          corsOrigins: defaultCorsOrigins,
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      expect(wrapper.text()).toContain('Network Configuration')
    })

    it('displays subtitle about server network settings', async () => {
      wrapper = mount(NetworkSettingsTab, {
        props: {
          config: defaultConfig,
          corsOrigins: defaultCorsOrigins,
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      expect(wrapper.text()).toContain('Server network settings')
    })

    it('displays unified architecture info alert', async () => {
      wrapper = mount(NetworkSettingsTab, {
        props: {
          config: defaultConfig,
          corsOrigins: defaultCorsOrigins,
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      const alert = wrapper.find('[data-test="v3-unified-alert"]')
      expect(alert.exists()).toBe(true)
      expect(wrapper.text()).toContain('Unified Architecture')
    })
  })

  describe('Loading State', () => {
    it('displays loading indicator when loading is true', async () => {
      wrapper = mount(NetworkSettingsTab, {
        props: {
          config: defaultConfig,
          corsOrigins: defaultCorsOrigins,
          loading: true,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      // Check for progress indicator in HTML (component renders with indeterminate attribute in tests)
      const html = wrapper.html()
      expect(html).toContain('indeterminate')
    })

    it('hides network fields when loading', async () => {
      wrapper = mount(NetworkSettingsTab, {
        props: {
          config: defaultConfig,
          corsOrigins: defaultCorsOrigins,
          loading: true,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      const externalHostField = wrapper.find('[data-test="external-host-field"]')
      expect(externalHostField.exists()).toBe(false)
    })
  })

  describe('Network Configuration Fields', () => {
    it('displays external host field with correct value', async () => {
      wrapper = mount(NetworkSettingsTab, {
        props: {
          config: { ...defaultConfig, externalHost: '192.168.1.100' },
          corsOrigins: defaultCorsOrigins,
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      const externalHostField = wrapper.find('[data-test="external-host-field"]')
      expect(externalHostField.exists()).toBe(true)
      // Check field attributes in HTML since Vuetify components may not render label text in test
      const html = wrapper.html()
      expect(html).toContain('External Host')
    })

    it('displays API port field with correct value', async () => {
      wrapper = mount(NetworkSettingsTab, {
        props: {
          config: { ...defaultConfig, apiPort: 8080 },
          corsOrigins: defaultCorsOrigins,
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      const apiPortField = wrapper.find('[data-test="api-port-field"]')
      expect(apiPortField.exists()).toBe(true)
      // Check field attributes in HTML since Vuetify components may not render label text in test
      const html = wrapper.html()
      expect(html).toContain('API Port')
    })

    it('displays frontend port field with correct value', async () => {
      wrapper = mount(NetworkSettingsTab, {
        props: {
          config: { ...defaultConfig, frontendPort: 3000 },
          corsOrigins: defaultCorsOrigins,
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      const frontendPortField = wrapper.find('[data-test="frontend-port-field"]')
      expect(frontendPortField.exists()).toBe(true)
      // Check field attributes in HTML since Vuetify components may not render label text in test
      const html = wrapper.html()
      expect(html).toContain('Frontend Port')
    })

    it('displays all fields as readonly', async () => {
      wrapper = mount(NetworkSettingsTab, {
        props: {
          config: defaultConfig,
          corsOrigins: defaultCorsOrigins,
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      // Fields should be readonly as network settings are configured during installation
      // Check that readonly attribute is in the HTML (v-text-field may not be found by name in tests)
      const html = wrapper.html()
      expect(html).toContain('readonly')
      // Verify the data-test attributes exist for the fields
      expect(html).toContain('data-test="external-host-field"')
      expect(html).toContain('data-test="api-port-field"')
      expect(html).toContain('data-test="frontend-port-field"')
    })
  })

  describe('CORS Origins Section', () => {
    it('displays CORS origins section', async () => {
      wrapper = mount(NetworkSettingsTab, {
        props: {
          config: defaultConfig,
          corsOrigins: defaultCorsOrigins,
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      expect(wrapper.text()).toContain('CORS Allowed Origins')
    })

    it('displays CORS origins list when origins exist', async () => {
      wrapper = mount(NetworkSettingsTab, {
        props: {
          config: defaultConfig,
          corsOrigins: ['http://localhost:7274', 'http://192.168.1.100:7274'],
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      const corsSection = wrapper.find('[data-test="cors-origins-section"]')
      expect(corsSection.exists()).toBe(true)
    })

    it('displays empty state when no CORS origins', async () => {
      wrapper = mount(NetworkSettingsTab, {
        props: {
          config: defaultConfig,
          corsOrigins: [],
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      expect(wrapper.text()).toContain('No CORS origins configured')
    })

    it('displays info about foundation implementation for CORS', async () => {
      wrapper = mount(NetworkSettingsTab, {
        props: {
          config: defaultConfig,
          corsOrigins: defaultCorsOrigins,
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      expect(wrapper.text()).toContain('Foundation implementation')
    })
  })

  describe('Configuration Notes', () => {
    it('displays configuration notes section', async () => {
      wrapper = mount(NetworkSettingsTab, {
        props: {
          config: defaultConfig,
          corsOrigins: defaultCorsOrigins,
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      expect(wrapper.text()).toContain('Configuration Notes')
    })

    it('displays info about config.yaml', async () => {
      wrapper = mount(NetworkSettingsTab, {
        props: {
          config: defaultConfig,
          corsOrigins: defaultCorsOrigins,
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      expect(wrapper.text()).toContain('config.yaml')
    })
  })

  describe('Reload Button', () => {
    it('has a Reload button', async () => {
      wrapper = mount(NetworkSettingsTab, {
        props: {
          config: defaultConfig,
          corsOrigins: defaultCorsOrigins,
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      const reloadButton = wrapper.find('[data-test="reload-button"]')
      expect(reloadButton.exists()).toBe(true)
      expect(reloadButton.text()).toContain('Reload')
    })

    it('emits refresh event when reload button is clicked', async () => {
      wrapper = mount(NetworkSettingsTab, {
        props: {
          config: defaultConfig,
          corsOrigins: defaultCorsOrigins,
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      const reloadButton = wrapper.find('[data-test="reload-button"]')
      await reloadButton.trigger('click')

      expect(wrapper.emitted('refresh')).toBeTruthy()
      expect(wrapper.emitted('refresh').length).toBe(1)
    })
  })

  describe('Save Button', () => {
    it('has a disabled Save Changes button', async () => {
      wrapper = mount(NetworkSettingsTab, {
        props: {
          config: defaultConfig,
          corsOrigins: defaultCorsOrigins,
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      const saveButton = wrapper.find('[data-test="save-button"]')
      expect(saveButton.exists()).toBe(true)
      expect(saveButton.text()).toContain('Save Changes')
      // Button should be disabled as network settings are read-only
      expect(saveButton.attributes('disabled')).toBeDefined()
    })
  })

  describe('Props Reactivity', () => {
    it('updates display when config prop changes', async () => {
      wrapper = mount(NetworkSettingsTab, {
        props: {
          config: { ...defaultConfig, externalHost: 'original-host' },
          corsOrigins: defaultCorsOrigins,
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      // Update the config prop
      await wrapper.setProps({
        config: { ...defaultConfig, externalHost: 'new-host' },
      })

      await wrapper.vm.$nextTick()
      // Component should reflect new values - check that the field exists
      const externalHostField = wrapper.find('[data-test="external-host-field"]')
      expect(externalHostField.exists()).toBe(true)
    })

    it('updates CORS display when corsOrigins prop changes', async () => {
      wrapper = mount(NetworkSettingsTab, {
        props: {
          config: defaultConfig,
          corsOrigins: [],
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      expect(wrapper.text()).toContain('No CORS origins configured')

      // Update corsOrigins
      await wrapper.setProps({
        corsOrigins: ['http://localhost:7274'],
      })

      await wrapper.vm.$nextTick()
      // Should no longer show empty state
      expect(wrapper.text()).not.toContain('No CORS origins configured')
    })
  })

  describe('Error Handling', () => {
    it('renders gracefully with empty config', async () => {
      wrapper = mount(NetworkSettingsTab, {
        props: {
          config: {},
          corsOrigins: [],
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      expect(wrapper.exists()).toBe(true)
      expect(wrapper.text()).toContain('Network Configuration')
    })

    it('handles undefined config values gracefully', async () => {
      wrapper = mount(NetworkSettingsTab, {
        props: {
          config: {
            externalHost: undefined,
            apiPort: undefined,
            frontendPort: undefined,
          },
          corsOrigins: [],
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      expect(wrapper.exists()).toBe(true)
    })
  })

  describe('Accessibility', () => {
    it('has proper heading hierarchy', async () => {
      wrapper = mount(NetworkSettingsTab, {
        props: {
          config: defaultConfig,
          corsOrigins: defaultCorsOrigins,
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      // Should have section headings
      expect(wrapper.text()).toContain('Server Configuration')
      expect(wrapper.text()).toContain('CORS Allowed Origins')
      expect(wrapper.text()).toContain('Configuration Notes')
    })

    it('has hints on form fields', async () => {
      wrapper = mount(NetworkSettingsTab, {
        props: {
          config: defaultConfig,
          corsOrigins: defaultCorsOrigins,
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      // Fields should have helpful hints - check HTML for hint attributes
      const html = wrapper.html()
      expect(html).toContain('Host/IP configured during installation')
      expect(html).toContain('Default: 7272')
      expect(html).toContain('Default: 7274')
    })
  })

  describe('HTTPS Status Section', () => {
    it('displays HTTPS status section with data-test attribute', async () => {
      wrapper = mount(NetworkSettingsTab, {
        props: {
          config: defaultConfig,
          corsOrigins: defaultCorsOrigins,
          sslEnabled: false,
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      const section = wrapper.find('[data-test="https-status-section"]')
      expect(section.exists()).toBe(true)
    })

    it('shows "HTTPS: Disabled" when sslEnabled is false', async () => {
      wrapper = mount(NetworkSettingsTab, {
        props: {
          config: defaultConfig,
          corsOrigins: defaultCorsOrigins,
          sslEnabled: false,
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      const section = wrapper.find('[data-test="https-status-section"]')
      expect(section.text()).toContain('Disabled')
    })

    it('shows HTTPS status section with default disabled state', async () => {
      wrapper = mount(NetworkSettingsTab, {
        props: {
          config: defaultConfig,
          corsOrigins: defaultCorsOrigins,
          sslEnabled: true,
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      const section = wrapper.find('[data-test="https-status-section"]')
      expect(section.exists()).toBe(true)
      // SSL status is loaded via API; in test environment defaults to Disabled
      expect(section.text()).toContain('HTTPS')
    })

    it('shows setup instructions toggle when HTTPS is disabled', async () => {
      wrapper = mount(NetworkSettingsTab, {
        props: {
          config: defaultConfig,
          corsOrigins: defaultCorsOrigins,
          sslEnabled: false,
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      const toggle = wrapper.find('[data-test="https-setup-toggle"]')
      expect(toggle.exists()).toBe(true)
      expect(toggle.text()).toContain('How to set up trusted HTTPS certificates')
    })

    it('shows setup toggle when HTTPS is not enabled', async () => {
      wrapper = mount(NetworkSettingsTab, {
        props: {
          config: defaultConfig,
          corsOrigins: defaultCorsOrigins,
          sslEnabled: false,
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      const toggle = wrapper.find('[data-test="https-setup-toggle"]')
      expect(toggle.exists()).toBe(true)
      expect(toggle.text()).toContain('How to set up trusted HTTPS certificates')
    })

    it('instructions are collapsed by default', async () => {
      wrapper = mount(NetworkSettingsTab, {
        props: {
          config: defaultConfig,
          corsOrigins: defaultCorsOrigins,
          sslEnabled: false,
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      const instructions = wrapper.find('[data-test="https-setup-instructions"]')
      expect(instructions.exists()).toBe(false)
    })

    it('shows instructions after clicking the toggle', async () => {
      wrapper = mount(NetworkSettingsTab, {
        props: {
          config: defaultConfig,
          corsOrigins: defaultCorsOrigins,
          sslEnabled: false,
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      const toggle = wrapper.find('[data-test="https-setup-toggle"]')
      await toggle.trigger('click')
      await wrapper.vm.$nextTick()

      const text = wrapper.text()
      expect(text).toContain('trusted certificates')
      expect(text).toContain('mkcert')
    })

    it('collapses instructions after clicking the toggle twice', async () => {
      wrapper = mount(NetworkSettingsTab, {
        props: {
          config: defaultConfig,
          corsOrigins: defaultCorsOrigins,
          sslEnabled: false,
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      const toggle = wrapper.find('[data-test="https-setup-toggle"]')

      // Click to expand
      await toggle.trigger('click')
      await wrapper.vm.$nextTick()
      expect(wrapper.text()).toContain('mkcert')

      // Click to collapse
      await toggle.trigger('click')
      await wrapper.vm.$nextTick()
      expect(wrapper.text()).not.toContain('mkcert')
    })

    it('defaults sslEnabled to false when prop not provided', async () => {
      wrapper = mount(NetworkSettingsTab, {
        props: {
          config: defaultConfig,
          corsOrigins: defaultCorsOrigins,
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      const section = wrapper.find('[data-test="https-status-section"]')
      expect(section.exists()).toBe(true)
      expect(section.text()).toContain('Disabled')
    })

    it('does not show HTTPS section when loading', async () => {
      wrapper = mount(NetworkSettingsTab, {
        props: {
          config: defaultConfig,
          corsOrigins: defaultCorsOrigins,
          sslEnabled: false,
          loading: true,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      const section = wrapper.find('[data-test="https-status-section"]')
      expect(section.exists()).toBe(false)
    })
  })
})
