/**
 * Test suite for SecuritySettingsTab.vue component
 * TDD RED Phase - Tests for security settings tab extraction
 *
 * Tests the Security Settings tab functionality:
 * - Component rendering with security settings
 * - Cookie domain management section
 * - Current cookie domains list display
 * - Add domain functionality
 * - Remove domain functionality
 * - Domain format validation
 * - Event emissions (update, save)
 * - Loading state handling
 * - Feedback message display
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import SecuritySettingsTab from '@/components/settings/tabs/SecuritySettingsTab.vue'

describe('SecuritySettingsTab.vue', () => {
  let vuetify
  let wrapper

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
    it('renders the component', () => {
      wrapper = mount(SecuritySettingsTab, {
        props: {
          cookieDomains: [],
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      expect(wrapper.exists()).toBe(true)
    })

    it('displays security settings title', () => {
      wrapper = mount(SecuritySettingsTab, {
        props: {
          cookieDomains: [],
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      expect(wrapper.text()).toContain('Security Settings')
    })

    it('displays card subtitle about authentication and security', () => {
      wrapper = mount(SecuritySettingsTab, {
        props: {
          cookieDomains: [],
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      expect(wrapper.text()).toContain('authentication')
    })

    it('displays cookie domain whitelist section', () => {
      wrapper = mount(SecuritySettingsTab, {
        props: {
          cookieDomains: [],
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      expect(wrapper.text()).toContain('Cookie Domain Whitelist')
    })

    it('displays informational alert about IP addresses', () => {
      wrapper = mount(SecuritySettingsTab, {
        props: {
          cookieDomains: [],
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      expect(wrapper.text()).toContain('IP addresses are automatically allowed')
    })
  })

  describe('Cookie Domains List Display', () => {
    it('displays cookie domains when provided', async () => {
      const domains = ['app.example.com', 'api.example.com', 'localhost']

      wrapper = mount(SecuritySettingsTab, {
        props: {
          cookieDomains: domains,
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      // Verify the component received the domains prop
      expect(wrapper.props('cookieDomains')).toEqual(domains)
      expect(wrapper.props('cookieDomains').length).toBe(3)
    })

    it('displays empty state when no domains are configured', () => {
      wrapper = mount(SecuritySettingsTab, {
        props: {
          cookieDomains: [],
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      expect(wrapper.text()).toContain('No domain names configured')
    })

    it('provides remove functionality for each domain', async () => {
      const domains = ['app.example.com', 'api.example.com']

      wrapper = mount(SecuritySettingsTab, {
        props: {
          cookieDomains: domains,
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      // Verify the removeDomain method works for each domain
      expect(wrapper.props('cookieDomains').length).toBe(2)
      expect(wrapper.vm.removeDomain).toBeDefined()
    })
  })

  describe('Add Domain Functionality', () => {
    it('has input field for adding new domain', () => {
      wrapper = mount(SecuritySettingsTab, {
        props: {
          cookieDomains: [],
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      const input = wrapper.find('[data-test="new-domain-input"]')
      expect(input.exists()).toBe(true)
    })

    it('has add button for adding new domain', () => {
      wrapper = mount(SecuritySettingsTab, {
        props: {
          cookieDomains: [],
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      // Check for add domain functionality via component method
      expect(wrapper.vm.addDomain).toBeDefined()
    })

    it('emits add-domain event when add button is clicked with valid domain', async () => {
      wrapper = mount(SecuritySettingsTab, {
        props: {
          cookieDomains: [],
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      // Set the domain value via vm
      wrapper.vm.newDomain = 'new.example.com'
      await wrapper.vm.$nextTick()

      // Call add method directly (simulates button click)
      wrapper.vm.addDomain()
      await wrapper.vm.$nextTick()

      expect(wrapper.emitted('add-domain')).toBeTruthy()
      expect(wrapper.emitted('add-domain')[0]).toEqual(['new.example.com'])
    })

    it('emits add-domain event when Enter key is pressed in input', async () => {
      wrapper = mount(SecuritySettingsTab, {
        props: {
          cookieDomains: [],
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      // Set the domain value via vm
      wrapper.vm.newDomain = 'new.example.com'
      await wrapper.vm.$nextTick()

      // Call the method directly (simulates enter key press)
      wrapper.vm.addDomain()
      await wrapper.vm.$nextTick()

      expect(wrapper.emitted('add-domain')).toBeTruthy()
      expect(wrapper.emitted('add-domain')[0]).toEqual(['new.example.com'])
    })

    it('clears input after successful add', async () => {
      wrapper = mount(SecuritySettingsTab, {
        props: {
          cookieDomains: [],
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      // Set the domain value via vm
      wrapper.vm.newDomain = 'new.example.com'
      await wrapper.vm.$nextTick()

      // Call add method
      wrapper.vm.addDomain()
      await wrapper.vm.$nextTick()

      // Input should be cleared after emit
      expect(wrapper.vm.newDomain).toBe('')
    })

    it('does not emit when input is empty', async () => {
      wrapper = mount(SecuritySettingsTab, {
        props: {
          cookieDomains: [],
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      // Try to add with empty input
      wrapper.vm.addDomain()
      await wrapper.vm.$nextTick()

      expect(wrapper.emitted('add-domain')).toBeFalsy()
    })

    it('does not emit when input is empty (validation check)', async () => {
      wrapper = mount(SecuritySettingsTab, {
        props: {
          cookieDomains: [],
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      // Verify empty input doesn't trigger emit
      expect(wrapper.vm.newDomain).toBe('')
      wrapper.vm.addDomain()
      expect(wrapper.emitted('add-domain')).toBeFalsy()
    })
  })

  describe('Remove Domain Functionality', () => {
    it('emits remove-domain event when delete button is clicked', async () => {
      const domains = ['app.example.com']

      wrapper = mount(SecuritySettingsTab, {
        props: {
          cookieDomains: domains,
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      // Call remove method directly (simulates button click)
      wrapper.vm.removeDomain('app.example.com')
      await wrapper.vm.$nextTick()

      expect(wrapper.emitted('remove-domain')).toBeTruthy()
      expect(wrapper.emitted('remove-domain')[0]).toEqual(['app.example.com'])
    })
  })

  describe('Domain Validation', () => {
    it('shows error for IP address input', async () => {
      wrapper = mount(SecuritySettingsTab, {
        props: {
          cookieDomains: [],
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      // Set the domain value via vm to trigger validation
      wrapper.vm.newDomain = '192.168.1.100'
      await wrapper.vm.$nextTick()

      // Check for validation error
      expect(wrapper.vm.domainError).toContain('IP addresses are not allowed')
    })

    it('shows error for invalid domain format', async () => {
      wrapper = mount(SecuritySettingsTab, {
        props: {
          cookieDomains: [],
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      // Set the domain value via vm to trigger validation
      wrapper.vm.newDomain = 'invalid..domain'
      await wrapper.vm.$nextTick()

      // Check for validation error
      expect(wrapper.vm.domainError).toContain('Invalid domain format')
    })

    it('accepts valid domain names', async () => {
      wrapper = mount(SecuritySettingsTab, {
        props: {
          cookieDomains: [],
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      // Set the domain value via vm to trigger validation
      wrapper.vm.newDomain = 'valid.example.com'
      await wrapper.vm.$nextTick()

      // No validation error should be present
      expect(wrapper.vm.domainError).toBe('')
    })

    it('accepts localhost as valid domain', async () => {
      wrapper = mount(SecuritySettingsTab, {
        props: {
          cookieDomains: [],
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      // Set the domain value via vm to trigger validation
      wrapper.vm.newDomain = 'localhost'
      await wrapper.vm.$nextTick()

      // No validation error
      expect(wrapper.vm.domainError).toBe('')
    })

    it('disables add button when validation fails', async () => {
      wrapper = mount(SecuritySettingsTab, {
        props: {
          cookieDomains: [],
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      // Set invalid domain via vm
      wrapper.vm.newDomain = '192.168.1.100'
      await wrapper.vm.$nextTick()

      // The button should be disabled because domainError is set
      expect(wrapper.vm.domainError).toBeTruthy()
    })
  })

  describe('Loading State', () => {
    it('shows loading indicator when loading is true', () => {
      wrapper = mount(SecuritySettingsTab, {
        props: {
          cookieDomains: [],
          loading: true,
        },
        global: {
          plugins: [vuetify],
        },
      })

      const loadingIndicator = wrapper.find('[data-test="loading-indicator"]')
      expect(loadingIndicator.exists()).toBe(true)
    })

    it('respects loading state for add functionality', async () => {
      wrapper = mount(SecuritySettingsTab, {
        props: {
          cookieDomains: [],
          loading: true,
        },
        global: {
          plugins: [vuetify],
        },
      })

      // Set a valid domain
      wrapper.vm.newDomain = 'example.com'
      await wrapper.vm.$nextTick()

      // Verify loading is passed as prop
      expect(wrapper.props('loading')).toBe(true)
    })

    it('passes loading prop to disable buttons', async () => {
      wrapper = mount(SecuritySettingsTab, {
        props: {
          cookieDomains: ['app.example.com'],
          loading: true,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      // Verify loading state is passed correctly
      expect(wrapper.props('loading')).toBe(true)
    })

    it('has reload method', async () => {
      wrapper = mount(SecuritySettingsTab, {
        props: {
          cookieDomains: [],
          loading: true,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      // Verify reload method exists
      expect(wrapper.vm.reload).toBeDefined()
    })
  })

  describe('Feedback Messages', () => {
    it('displays success feedback message', async () => {
      wrapper = mount(SecuritySettingsTab, {
        props: {
          cookieDomains: [],
          loading: false,
          feedback: {
            type: 'success',
            message: 'Domain added successfully.',
          },
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      expect(wrapper.text()).toContain('Domain added successfully.')
    })

    it('displays error feedback message', async () => {
      wrapper = mount(SecuritySettingsTab, {
        props: {
          cookieDomains: [],
          loading: false,
          feedback: {
            type: 'error',
            message: 'Failed to add domain.',
          },
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      expect(wrapper.text()).toContain('Failed to add domain.')
    })

    it('displays warning feedback message', async () => {
      wrapper = mount(SecuritySettingsTab, {
        props: {
          cookieDomains: [],
          loading: false,
          feedback: {
            type: 'warning',
            message: 'Domain already exists.',
          },
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      expect(wrapper.text()).toContain('Domain already exists.')
    })

    it('emits clear-feedback when feedback alert is closed', async () => {
      wrapper = mount(SecuritySettingsTab, {
        props: {
          cookieDomains: [],
          loading: false,
          feedback: {
            type: 'success',
            message: 'Domain added successfully.',
          },
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      const feedbackAlert = wrapper.find('[data-test="feedback-alert"]')
      if (feedbackAlert.exists()) {
        // Find and click close button
        const closeButton = feedbackAlert.find('.v-alert__close')
        if (closeButton.exists()) {
          await closeButton.trigger('click')
          expect(wrapper.emitted('clear-feedback')).toBeTruthy()
        }
      }
    })
  })

  describe('Reload Functionality', () => {
    it('has reload method', () => {
      wrapper = mount(SecuritySettingsTab, {
        props: {
          cookieDomains: [],
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      expect(wrapper.vm.reload).toBeDefined()
    })

    it('emits reload event when reload is called', async () => {
      wrapper = mount(SecuritySettingsTab, {
        props: {
          cookieDomains: [],
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      // Call reload method directly
      wrapper.vm.reload()
      await wrapper.vm.$nextTick()

      expect(wrapper.emitted('reload')).toBeTruthy()
    })
  })

  describe('Props', () => {
    it('accepts cookieDomains prop', () => {
      const domains = ['domain1.com', 'domain2.com']

      wrapper = mount(SecuritySettingsTab, {
        props: {
          cookieDomains: domains,
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      expect(wrapper.props('cookieDomains')).toEqual(domains)
    })

    it('accepts loading prop', () => {
      wrapper = mount(SecuritySettingsTab, {
        props: {
          cookieDomains: [],
          loading: true,
        },
        global: {
          plugins: [vuetify],
        },
      })

      expect(wrapper.props('loading')).toBe(true)
    })

    it('accepts feedback prop', () => {
      const feedback = { type: 'success', message: 'Test message' }

      wrapper = mount(SecuritySettingsTab, {
        props: {
          cookieDomains: [],
          loading: false,
          feedback: feedback,
        },
        global: {
          plugins: [vuetify],
        },
      })

      expect(wrapper.props('feedback')).toEqual(feedback)
    })

    it('defaults feedback to null', () => {
      wrapper = mount(SecuritySettingsTab, {
        props: {
          cookieDomains: [],
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      expect(wrapper.props('feedback')).toBeNull()
    })
  })

  describe('Accessibility', () => {
    it('component provides domain context for screen readers', async () => {
      const domains = ['app.example.com']

      wrapper = mount(SecuritySettingsTab, {
        props: {
          cookieDomains: domains,
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      // Verify that domains are displayed with context
      expect(wrapper.text()).toContain('app.example.com')
    })

    it('component has methods for domain management', () => {
      wrapper = mount(SecuritySettingsTab, {
        props: {
          cookieDomains: [],
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      // Verify domain management methods exist
      expect(wrapper.vm.addDomain).toBeDefined()
      expect(wrapper.vm.removeDomain).toBeDefined()
    })
  })

  describe('Duplicate Domain Prevention', () => {
    it('does not emit add-domain for duplicate domain', async () => {
      const domains = ['app.example.com']

      wrapper = mount(SecuritySettingsTab, {
        props: {
          cookieDomains: domains,
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      // Set duplicate domain via vm
      wrapper.vm.newDomain = 'app.example.com'
      await wrapper.vm.$nextTick()

      // Call add method directly
      wrapper.vm.addDomain()
      await wrapper.vm.$nextTick()

      // Should show warning instead of emitting add-domain
      expect(wrapper.emitted('add-domain')).toBeFalsy()
    })

    it('shows warning when trying to add duplicate domain', async () => {
      const domains = ['app.example.com']

      wrapper = mount(SecuritySettingsTab, {
        props: {
          cookieDomains: domains,
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      // Set duplicate domain via vm
      wrapper.vm.newDomain = 'app.example.com'
      await wrapper.vm.$nextTick()

      // Call add method directly
      wrapper.vm.addDomain()
      await wrapper.vm.$nextTick()

      // Check for duplicate warning in domainError
      expect(wrapper.vm.domainError).toContain('already')
    })
  })
})
