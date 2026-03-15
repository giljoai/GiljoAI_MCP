/**
 * Test suite for SerenaAttachStep component
 *
 * Tests the Serena MCP detection and attachment flow:
 * - Detection states (not_detected, detected, configured)
 * - Installation instructions modal
 * - Check Again button functionality
 * - Skip button functionality
 * - Error handling
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
// import SerenaAttachStep from '@/components/setup/SerenaAttachStep.vue' // module deleted/moved
import setupService from '@/services/setupService'

// Mock setupService
vi.mock('@/services/setupService', () => ({
  default: {
    detectSerena: vi.fn(),
    attachSerena: vi.fn(),
    detachSerena: vi.fn(),
    getSerenaStatus: vi.fn()
  }
}))

describe.skip('SerenaAttachStep.vue - module deleted/moved', () => {
  let vuetify
  let wrapper

  beforeEach(() => {
    vuetify = createVuetify({
      components,
      directives
    })

    // Reset mocks before each test
    vi.clearAllMocks()
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
  })

  describe('Initial Detection', () => {
    it('detects Serena on mount', async () => {
      setupService.detectSerena.mockResolvedValue({ installed: false })

      wrapper = mount(SerenaAttachStep, {
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      expect(setupService.detectSerena).toHaveBeenCalledTimes(1)
    })

    it('shows not_detected state when Serena is not installed', async () => {
      setupService.detectSerena.mockResolvedValue({ installed: false })

      wrapper = mount(SerenaAttachStep, {
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      expect(wrapper.vm.state).toBe('not_detected')
    })

    it('shows detected state when Serena is installed', async () => {
      setupService.detectSerena.mockResolvedValue({ installed: true })

      wrapper = mount(SerenaAttachStep, {
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      expect(wrapper.vm.state).toBe('detected')
    })

    it('handles detection errors gracefully', async () => {
      setupService.detectSerena.mockRejectedValue(new Error('Detection failed'))

      wrapper = mount(SerenaAttachStep, {
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      expect(wrapper.vm.errorMessage).toContain('Detection failed')
    })
  })

  describe('State: Not Detected', () => {
    beforeEach(async () => {
      setupService.detectSerena.mockResolvedValue({ installed: false })

      wrapper = mount(SerenaAttachStep, {
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()
    })

    it('displays installation instructions button', () => {
      const instructionsBtn = wrapper.find('[aria-label="Open installation instructions"]')
      expect(instructionsBtn.exists()).toBe(true)
    })

    it('displays skip button', () => {
      const skipBtn = wrapper.find('[aria-label="Skip Serena MCP setup"]')
      expect(skipBtn.exists()).toBe(true)
    })

    it('opens installation dialog when "How to Install" is clicked', async () => {
      const instructionsBtn = wrapper.find('[aria-label="Open installation instructions"]')
      await instructionsBtn.trigger('click')
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.showInstallDialog).toBe(true)
    })

    it('emits skip event when skip button is clicked', async () => {
      const skipBtn = wrapper.find('[aria-label="Skip Serena MCP setup"]')
      await skipBtn.trigger('click')

      expect(wrapper.emitted('skip')).toBeTruthy()
    })
  })

  describe('State: Detected', () => {
    beforeEach(async () => {
      setupService.detectSerena.mockResolvedValue({ installed: true })

      wrapper = mount(SerenaAttachStep, {
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()
    })

    it('displays attach button', () => {
      const attachBtn = wrapper.find('[aria-label="Attach Serena MCP"]')
      expect(attachBtn.exists()).toBe(true)
    })

    it('shows success chip indicating detection', () => {
      const successChip = wrapper.find('.v-chip')
      expect(successChip.exists()).toBe(true)
      expect(successChip.text()).toContain('Detected')
    })

    it('attaches Serena when attach button is clicked', async () => {
      setupService.attachSerena.mockResolvedValue({ success: true })

      const attachBtn = wrapper.find('[aria-label="Attach Serena MCP"]')
      await attachBtn.trigger('click')
      await flushPromises()

      expect(setupService.attachSerena).toHaveBeenCalledTimes(1)
    })

    it('shows loading state during attachment', async () => {
      setupService.attachSerena.mockImplementation(() =>
        new Promise(resolve => setTimeout(() => resolve({ success: true }), 100))
      )

      const attachBtn = wrapper.find('[aria-label="Attach Serena MCP"]')
      await attachBtn.trigger('click')

      expect(wrapper.vm.attaching).toBe(true)

      await flushPromises()

      expect(wrapper.vm.attaching).toBe(false)
    })

    it('transitions to configured state on successful attachment', async () => {
      setupService.attachSerena.mockResolvedValue({ success: true })

      const attachBtn = wrapper.find('[aria-label="Attach Serena MCP"]')
      await attachBtn.trigger('click')
      await flushPromises()

      expect(wrapper.vm.state).toBe('configured')
      expect(wrapper.vm.isConfigured).toBe(true)
    })

    it('emits update:modelValue on successful attachment', async () => {
      setupService.attachSerena.mockResolvedValue({ success: true })

      const attachBtn = wrapper.find('[aria-label="Attach Serena MCP"]')
      await attachBtn.trigger('click')
      await flushPromises()

      expect(wrapper.emitted('update:modelValue')).toBeTruthy()
      expect(wrapper.emitted('update:modelValue')[0][0]).toBe(true)
    })

    it('handles attachment errors gracefully', async () => {
      setupService.attachSerena.mockRejectedValue(new Error('Attachment failed'))

      const attachBtn = wrapper.find('[aria-label="Attach Serena MCP"]')
      await attachBtn.trigger('click')
      await flushPromises()

      expect(wrapper.vm.errorMessage).toContain('Attachment failed')
      expect(wrapper.vm.state).toBe('detected') // Remains in detected state
    })

    it('handles API error responses', async () => {
      setupService.attachSerena.mockResolvedValue({
        success: false,
        error: 'Configuration error'
      })

      const attachBtn = wrapper.find('[aria-label="Attach Serena MCP"]')
      await attachBtn.trigger('click')
      await flushPromises()

      expect(wrapper.vm.errorMessage).toContain('Configuration error')
    })
  })

  describe('State: Configured', () => {
    beforeEach(async () => {
      setupService.detectSerena.mockResolvedValue({ installed: true })
      setupService.attachSerena.mockResolvedValue({ success: true })

      wrapper = mount(SerenaAttachStep, {
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      // Attach Serena to reach configured state
      const attachBtn = wrapper.find('[aria-label="Attach Serena MCP"]')
      await attachBtn.trigger('click')
      await flushPromises()
    })

    it('displays configured state', () => {
      expect(wrapper.vm.state).toBe('configured')
      expect(wrapper.vm.isConfigured).toBe(true)
    })

    it('shows configured chip', () => {
      const configuredChip = wrapper.find('.v-chip')
      expect(configuredChip.exists()).toBe(true)
      expect(configuredChip.text()).toContain('Configured')
    })

    it('shows success alert', () => {
      const successAlert = wrapper.find('.v-alert[type="success"]')
      expect(successAlert.exists()).toBe(true)
    })

    it('does not show attach button in configured state', () => {
      const attachBtn = wrapper.find('[aria-label="Attach Serena MCP"]')
      expect(attachBtn.exists()).toBe(false)
    })
  })

  describe('Installation Dialog', () => {
    beforeEach(async () => {
      setupService.detectSerena.mockResolvedValue({ installed: false })

      wrapper = mount(SerenaAttachStep, {
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()
    })

    it('opens dialog when "How to Install" is clicked', async () => {
      const instructionsBtn = wrapper.find('[aria-label="Open installation instructions"]')
      await instructionsBtn.trigger('click')
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.showInstallDialog).toBe(true)
    })

    it('closes dialog when close button is clicked', async () => {
      wrapper.vm.showInstallDialog = true
      await wrapper.vm.$nextTick()

      const closeBtn = wrapper.find('[aria-label="Close installation dialog"]')
      await closeBtn.trigger('click')

      expect(wrapper.vm.showInstallDialog).toBe(false)
    })

    it('has tabs for uvx and local installation', async () => {
      wrapper.vm.showInstallDialog = true
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.installTab).toBeDefined()
    })

    it('shows "Check Again" button in dialog', async () => {
      wrapper.vm.showInstallDialog = true
      await wrapper.vm.$nextTick()

      const checkAgainBtn = wrapper.find('[aria-label="Re-check Serena installation"]')
      expect(checkAgainBtn.exists()).toBe(true)
    })

    it('re-detects Serena when "Check Again" is clicked', async () => {
      wrapper.vm.showInstallDialog = true
      await wrapper.vm.$nextTick()

      vi.clearAllMocks()
      setupService.detectSerena.mockResolvedValue({ installed: true })

      const checkAgainBtn = wrapper.find('[aria-label="Re-check Serena installation"]')
      await checkAgainBtn.trigger('click')
      await flushPromises()

      expect(setupService.detectSerena).toHaveBeenCalledTimes(1)
      expect(wrapper.vm.state).toBe('detected')
    })

    it('shows loading state during "Check Again"', async () => {
      wrapper.vm.showInstallDialog = true
      await wrapper.vm.$nextTick()

      setupService.detectSerena.mockImplementation(() =>
        new Promise(resolve => setTimeout(() => resolve({ installed: false }), 100))
      )

      const checkAgainBtn = wrapper.find('[aria-label="Re-check Serena installation"]')
      await checkAgainBtn.trigger('click')

      expect(wrapper.vm.checking).toBe(true)

      await flushPromises()

      expect(wrapper.vm.checking).toBe(false)
    })
  })

  describe('Navigation', () => {
    beforeEach(async () => {
      setupService.detectSerena.mockResolvedValue({ installed: false })

      wrapper = mount(SerenaAttachStep, {
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()
    })

    it('emits next event when Continue is clicked', async () => {
      const nextBtn = wrapper.find('[aria-label="Continue to next step"]')
      await nextBtn.trigger('click')

      expect(wrapper.emitted('next')).toBeTruthy()
    })

    it('emits back event when Back is clicked', async () => {
      const backBtn = wrapper.find('[aria-label="Go back to previous step"]')
      await backBtn.trigger('click')

      expect(wrapper.emitted('back')).toBeTruthy()
    })
  })

  describe('Progress Indicator', () => {
    it('shows step 2 of 4 progress', async () => {
      setupService.detectSerena.mockResolvedValue({ installed: false })

      wrapper = mount(SerenaAttachStep, {
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      const progressText = wrapper.find('.text-caption')
      expect(progressText.text()).toContain('Step 2 of 4')
      expect(progressText.text()).toContain('50%')
    })

    it('shows 50% progress bar', async () => {
      setupService.detectSerena.mockResolvedValue({ installed: false })

      wrapper = mount(SerenaAttachStep, {
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      const progressBar = wrapper.find('.v-progress-linear')
      expect(progressBar.exists()).toBe(true)
    })
  })

  describe('Error Handling', () => {
    it('displays error alert when error occurs', async () => {
      setupService.detectSerena.mockRejectedValue(new Error('Network error'))

      wrapper = mount(SerenaAttachStep, {
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      const errorAlert = wrapper.find('.v-alert[type="error"]')
      expect(errorAlert.exists()).toBe(true)
      expect(errorAlert.text()).toContain('Network error')
    })

    it('allows closing error alerts', async () => {
      setupService.detectSerena.mockRejectedValue(new Error('Test error'))

      wrapper = mount(SerenaAttachStep, {
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      expect(wrapper.vm.errorMessage).toBeTruthy()

      // Error alert should be closable
      const errorAlert = wrapper.find('.v-alert[type="error"]')
      expect(errorAlert.attributes('closable')).toBeDefined()
    })
  })

  describe('Props and Events', () => {
    it('accepts modelValue prop', () => {
      wrapper = mount(SerenaAttachStep, {
        global: {
          plugins: [vuetify]
        },
        props: {
          modelValue: false
        }
      })

      expect(wrapper.props('modelValue')).toBe(false)
    })

    it('emits all required events', async () => {
      setupService.detectSerena.mockResolvedValue({ installed: false })

      wrapper = mount(SerenaAttachStep, {
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      // Test next event
      const nextBtn = wrapper.find('[aria-label="Continue to next step"]')
      await nextBtn.trigger('click')
      expect(wrapper.emitted('next')).toBeTruthy()

      // Test back event
      const backBtn = wrapper.find('[aria-label="Go back to previous step"]')
      await backBtn.trigger('click')
      expect(wrapper.emitted('back')).toBeTruthy()

      // Test skip event
      const skipBtn = wrapper.find('[aria-label="Skip Serena MCP setup"]')
      await skipBtn.trigger('click')
      expect(wrapper.emitted('skip')).toBeTruthy()
    })
  })

  describe('Style and Accessibility', () => {
    it('applies correct CSS class when configured', async () => {
      setupService.detectSerena.mockResolvedValue({ installed: true })
      setupService.attachSerena.mockResolvedValue({ success: true })

      wrapper = mount(SerenaAttachStep, {
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      const attachBtn = wrapper.find('[aria-label="Attach Serena MCP"]')
      await attachBtn.trigger('click')
      await flushPromises()

      const card = wrapper.find('.serena-card')
      expect(card.classes()).toContain('serena-configured')
    })

    it('has proper aria-labels on all buttons', async () => {
      setupService.detectSerena.mockResolvedValue({ installed: false })

      wrapper = mount(SerenaAttachStep, {
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      const buttons = wrapper.findAll('button')
      buttons.forEach(button => {
        expect(button.attributes('aria-label')).toBeTruthy()
      })
    })
  })
})
