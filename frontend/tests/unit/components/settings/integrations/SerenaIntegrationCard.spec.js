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
    it('renders the component', () => {
      wrapper = mountComponent()
      expect(wrapper.exists()).toBe(true)
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

    it('displays GitHub repository link text', () => {
      wrapper = mountComponent()
      const text = wrapper.text()
      expect(text).toContain('GitHub Repository')
    })

    it('displays credit to Oraios', () => {
      wrapper = mountComponent()
      const text = wrapper.text()
      expect(text).toContain('Oraios')
    })

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

    it('displays GitHub Repository link', () => {
      wrapper = mountComponent()
      const text = wrapper.text()
      expect(text).toContain('GitHub Repository')
    })
  })

  describe('Props Validation', () => {
    it('accepts enabled prop as Boolean - false', () => {
      wrapper = mountComponent({ enabled: false })
      expect(wrapper.props('enabled')).toBe(false)
    })

    it('accepts enabled prop as Boolean - true', () => {
      wrapper = mountComponent({ enabled: true })
      expect(wrapper.props('enabled')).toBe(true)
    })

    it('accepts enabled prop with default value false', () => {
      wrapper = mountComponent()
      expect(wrapper.props('enabled')).toBe(false)
    })

    it('accepts loading prop as Boolean', () => {
      wrapper = mountComponent({ loading: true })
      expect(wrapper.props('loading')).toBe(true)
    })

    it('uses default enabled value when not provided', () => {
      wrapper = mount(SerenaIntegrationCard, {
        props: {
          loading: false,
        },
        global: {
          plugins: [vuetify],
          stubs: {
            SerenaAdvancedSettingsDialog: true,
          },
        },
      })
      expect(wrapper.props('enabled')).toBe(false)
    })
  })

  describe('Events', () => {
    it('defines update:enabled event', () => {
      wrapper = mountComponent()
      const emits = wrapper.vm.$options.emits || []
      expect(emits).toContain('update:enabled')
    })

    it('does not define openAdvanced event (removed in Handover 0277)', () => {
      wrapper = mountComponent()
      const emits = wrapper.vm.$options.emits || []
      expect(emits).not.toContain('openAdvanced')
    })
  })

  describe('Component Integration', () => {
    it('can be controlled externally via props', async () => {
      wrapper = mountComponent({ enabled: false })
      expect(wrapper.props('enabled')).toBe(false)

      await wrapper.setProps({ enabled: true })
      expect(wrapper.props('enabled')).toBe(true)
    })

    it('enabled prop is reactive', async () => {
      wrapper = mountComponent({ enabled: false })
      expect(wrapper.props('enabled')).toBe(false)

      await wrapper.setProps({ enabled: true })
      expect(wrapper.props('enabled')).toBe(true)
    })

    it('loading prop is reactive', async () => {
      wrapper = mountComponent({ loading: false })
      expect(wrapper.props('loading')).toBe(false)

      await wrapper.setProps({ loading: true })
      expect(wrapper.props('loading')).toBe(true)
    })
  })

  describe('Template Structure', () => {
    it('contains GitHub link with correct URL', () => {
      wrapper = mountComponent()
      const html = wrapper.html()
      expect(html).toContain('https://github.com/oraios/serena')
    })

    it('contains target="_blank" for external link', () => {
      wrapper = mountComponent()
      const html = wrapper.html()
      expect(html).toContain('target="_blank"')
    })

    it('contains Serena image reference', () => {
      wrapper = mountComponent()
      const html = wrapper.html()
      expect(html).toContain('Serena.png')
    })
  })

  describe('Semantic Content', () => {
    it('includes tooltip text about semantic code analysis', () => {
      wrapper = mountComponent()
      const html = wrapper.html()
      expect(html).toContain('semantic code analysis')
    })

    it('includes note about separate installation', () => {
      wrapper = mountComponent()
      const html = wrapper.html()
      expect(html).toContain('installed separately')
    })

    it('mentions agent prompts', () => {
      wrapper = mountComponent()
      const text = wrapper.text()
      expect(text).toContain('agent prompts')
    })
  })
})
