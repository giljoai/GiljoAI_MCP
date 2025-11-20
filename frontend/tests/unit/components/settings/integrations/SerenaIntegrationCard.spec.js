import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import SerenaIntegrationCard from '@/components/settings/integrations/SerenaIntegrationCard.vue'

// Mock the setupService
vi.mock('@/services/setupService', () => ({
  default: {
    getSerenaStatus: vi.fn(),
    toggleSerena: vi.fn(),
    getSerenaConfig: vi.fn(),
    updateSerenaConfig: vi.fn(),
  },
}))

describe('SerenaIntegrationCard.vue', () => {
  let vuetify
  let wrapper
  let setupService

  const defaultConfig = {
    use_in_prompts: true,
    tailor_by_mission: true,
    dynamic_catalog: true,
    prefer_ranges: true,
    max_range_lines: 180,
    context_halo: 12,
  }

  beforeEach(async () => {
    vuetify = createVuetify({
      components,
      directives,
    })

    setupService = (await import('@/services/setupService')).default

    // Setup default mock responses
    setupService.getSerenaStatus.mockResolvedValue({ enabled: false })
    setupService.toggleSerena.mockResolvedValue({ success: true, enabled: true })
    setupService.getSerenaConfig.mockResolvedValue(defaultConfig)
    setupService.updateSerenaConfig.mockResolvedValue(defaultConfig)
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
    vi.clearAllMocks()
  })

  function mountComponent(props = {}) {
    return mount(SerenaIntegrationCard, {
      props: {
        enabled: false,
        config: defaultConfig,
        loading: false,
        ...props,
      },
      global: {
        plugins: [vuetify],
        stubs: {
          SerenaAdvancedSettingsDialog: true,
        },
      },
    })
  }

  describe('Component Rendering', () => {
    it('renders as a v-card', () => {
      wrapper = mountComponent()
      expect(wrapper.find('.v-card').exists()).toBe(true)
    })

    it('displays "Serena MCP" title', () => {
      wrapper = mountComponent()
      const text = wrapper.text()
      expect(text).toContain('Serena MCP')
    })

    it('displays description about symbolic code intelligence', () => {
      wrapper = mountComponent()
      const text = wrapper.text()
      expect(text).toContain('Intelligent codebase understanding')
    })

    it('displays Serena avatar/icon', () => {
      wrapper = mountComponent()
      const avatar = wrapper.find('.v-avatar')
      expect(avatar.exists()).toBe(true)
    })

    it('displays the Serena image', () => {
      wrapper = mountComponent()
      const img = wrapper.find('.v-img')
      expect(img.exists()).toBe(true)
    })

    it('displays GitHub repository link', () => {
      wrapper = mountComponent()
      const link = wrapper.find('a[href="https://github.com/oraios/serena"]')
      expect(link.exists()).toBe(true)
    })

    it('displays credit to Oraios', () => {
      wrapper = mountComponent()
      const text = wrapper.text()
      expect(text).toContain('Oraios')
    })

    it('displays help tooltip with detailed description', () => {
      wrapper = mountComponent()
      const helpIcon = wrapper.find('.mdi-help-circle-outline')
      expect(helpIcon.exists()).toBe(true)
    })
  })

  describe('Toggle Switch', () => {
    it('has enable/disable toggle switch', () => {
      wrapper = mountComponent()
      const switchElement = wrapper.find('.v-switch')
      expect(switchElement.exists()).toBe(true)
    })

    it('toggle reflects enabled prop when false', () => {
      wrapper = mountComponent({ enabled: false })
      const switchInput = wrapper.find('.v-switch input')
      expect(switchInput.element.checked).toBe(false)
    })

    it('toggle reflects enabled prop when true', () => {
      wrapper = mountComponent({ enabled: true })
      const switchInput = wrapper.find('.v-switch input')
      expect(switchInput.element.checked).toBe(true)
    })

    it('emits update:enabled when toggle changes', async () => {
      wrapper = mountComponent({ enabled: false })
      const switchElement = wrapper.find('.v-switch')

      // Find the switch input and trigger change
      await switchElement.find('input').setValue(true)

      expect(wrapper.emitted('update:enabled')).toBeTruthy()
      expect(wrapper.emitted('update:enabled')[0]).toEqual([true])
    })

    it('shows loading state when toggling', () => {
      wrapper = mountComponent({ loading: true })
      const switchElement = wrapper.find('.v-switch')
      expect(switchElement.classes()).toContain('v-input--loading')
    })
  })

  describe('Advanced Settings Button', () => {
    it('has "Advanced" button when enabled', () => {
      wrapper = mountComponent({ enabled: true })
      const buttons = wrapper.findAll('.v-btn')
      const advancedBtn = buttons.find(btn => btn.text().includes('Advanced'))
      expect(advancedBtn).toBeDefined()
    })

    it('Advanced button is disabled when loading', () => {
      wrapper = mountComponent({ enabled: true, loading: true })
      const buttons = wrapper.findAll('.v-btn')
      const advancedBtn = buttons.find(btn => btn.text().includes('Advanced'))
      expect(advancedBtn.attributes('disabled')).toBeDefined()
    })

    it('emits openAdvanced when Advanced button clicked', async () => {
      wrapper = mountComponent({ enabled: true })
      const buttons = wrapper.findAll('.v-btn')
      const advancedBtn = buttons.find(btn => btn.text().includes('Advanced'))

      await advancedBtn.trigger('click')

      expect(wrapper.emitted('openAdvanced')).toBeTruthy()
    })
  })

  describe('Props Validation', () => {
    it('accepts enabled prop as Boolean', () => {
      wrapper = mountComponent({ enabled: true })
      expect(wrapper.props('enabled')).toBe(true)
    })

    it('accepts config prop as Object', () => {
      const customConfig = { ...defaultConfig, max_range_lines: 200 }
      wrapper = mountComponent({ config: customConfig })
      expect(wrapper.props('config').max_range_lines).toBe(200)
    })

    it('accepts loading prop as Boolean', () => {
      wrapper = mountComponent({ loading: true })
      expect(wrapper.props('loading')).toBe(true)
    })

    it('uses default config when not provided', () => {
      wrapper = mountComponent({ config: undefined })
      expect(wrapper.props('config')).toBeDefined()
    })
  })

  describe('Events', () => {
    it('defines update:enabled event', () => {
      wrapper = mountComponent()
      // Component should have emits defined
      expect(wrapper.vm.$options.emits).toContain('update:enabled')
    })

    it('defines openAdvanced event', () => {
      wrapper = mountComponent()
      expect(wrapper.vm.$options.emits).toContain('openAdvanced')
    })
  })

  describe('UI States', () => {
    it('displays instruction text about enabling/disabling', () => {
      wrapper = mountComponent()
      const text = wrapper.text()
      expect(text).toContain('Enabling adds Serena tool instructions')
    })

    it('displays "Enable Serena MCP" label', () => {
      wrapper = mountComponent()
      const text = wrapper.text()
      expect(text).toContain('Enable Serena MCP')
    })
  })

  describe('Accessibility', () => {
    it('has proper card structure', () => {
      wrapper = mountComponent()
      const card = wrapper.find('.v-card')
      const cardText = wrapper.find('.v-card-text')
      expect(card.exists()).toBe(true)
      expect(cardText.exists()).toBe(true)
    })

    it('external link opens in new tab', () => {
      wrapper = mountComponent()
      const link = wrapper.find('a[href="https://github.com/oraios/serena"]')
      expect(link.attributes('target')).toBe('_blank')
    })
  })

  describe('Integration with Parent', () => {
    it('can be controlled externally via props', async () => {
      wrapper = mountComponent({ enabled: false })
      expect(wrapper.find('.v-switch input').element.checked).toBe(false)

      await wrapper.setProps({ enabled: true })
      expect(wrapper.find('.v-switch input').element.checked).toBe(true)
    })

    it('loading prop disables toggle interaction', () => {
      wrapper = mountComponent({ loading: true })
      const switchElement = wrapper.find('.v-switch')
      expect(switchElement.classes()).toContain('v-input--loading')
    })
  })
})
