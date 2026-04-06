import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import McpIntegrationCard from '@/components/settings/integrations/McpIntegrationCard.vue'

describe('McpIntegrationCard.vue', () => {
  let vuetify
  let wrapper

  beforeEach(() => {
    vuetify = createVuetify({
      components,
      directives,
      theme: {
        defaultTheme: 'dark',
      },
    })

    wrapper = mount(McpIntegrationCard, {
      global: {
        plugins: [vuetify],
        stubs: {
          AiToolConfigWizard: {
            template: '<button class="ai-tool-config-wizard-stub">Configurator</button>',
          },
        },
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
    it('renders the component without errors', () => {
      expect(wrapper.exists()).toBe(true)
      expect(wrapper.vm).toBeDefined()
    })

    it('renders as an intg-card div', () => {
      const html = wrapper.html()
      expect(html).toContain('intg-card')
      expect(html).toContain('smooth-border')
    })

    it('displays "GiljoAI MCP" title', () => {
      const text = wrapper.text()
      expect(text).toContain('GiljoAI MCP')
    })

    it('displays description about MCP configuration', () => {
      const text = wrapper.text()
      expect(text).toContain('Connect your AI coding agent to GiljoAI orchestration')
    })

    it('displays supported tools in description', () => {
      const text = wrapper.text()
      expect(text).toContain('Claude Code')
      expect(text).toContain('Codex CLI')
      expect(text).toContain('Gemini CLI')
    })

    it('contains avatar element for GiljoAI logo', () => {
      const html = wrapper.html()
      expect(html).toContain('v-avatar')
    })
  })

  describe('MCP Configuration Tool Section', () => {
    it('displays configuration tool description', () => {
      const text = wrapper.text()
      expect(text).toContain('Creates an MCP integration CLI command')
    })

    it('includes AiToolConfigWizard component', () => {
      const wizardButton = wrapper.find('.ai-tool-config-wizard-stub')
      expect(wizardButton.exists()).toBe(true)
    })

    it('displays configure/setup button from AiToolConfigWizard', () => {
      const wizardButton = wrapper.find('.ai-tool-config-wizard-stub')
      expect(wizardButton.exists()).toBe(true)
      expect(wizardButton.text()).toContain('Configurator')
    })

    it('displays card description about the configurator', () => {
      const text = wrapper.text()
      expect(text).toContain('Configurator')
    })
  })

  describe('Card Structure', () => {
    it('has intg-card--clickable modifier class', () => {
      const html = wrapper.html()
      expect(html).toContain('intg-card--clickable')
    })

    it('has smooth-border class', () => {
      const html = wrapper.html()
      expect(html).toContain('smooth-border')
    })

    it('applies card accent color via CSS variable', () => {
      const html = wrapper.html()
      expect(html).toContain('--card-accent')
    })
  })

  describe('Layout and Alignment', () => {
    it('has flex layout for header section', () => {
      const flexDiv = wrapper.find('.d-flex.align-center')
      expect(flexDiv.exists()).toBe(true)
    })

    it('has centered flex layout for wizard section', () => {
      const centerDiv = wrapper.find('.d-flex.justify-center')
      expect(centerDiv.exists()).toBe(true)
    })
  })

  describe('Typography', () => {
    it('title is in intg-card-title element', () => {
      const title = wrapper.find('.intg-card-title')
      expect(title.exists()).toBe(true)
      expect(title.text()).toContain('GiljoAI MCP')
    })

    it('description is in intg-card-desc element', () => {
      const desc = wrapper.find('.intg-card-desc')
      expect(desc.exists()).toBe(true)
      expect(desc.text()).toContain('Configurator')
    })
  })

  describe('Accessibility', () => {
    it('has proper text content for screen readers', () => {
      const text = wrapper.text()
      expect(text.length).toBeGreaterThan(0)
      expect(text).toContain('GiljoAI MCP')
    })

    it('contains image element for accessibility', () => {
      const html = wrapper.html()
      expect(html).toContain('alt="GiljoAI MCP"')
    })

    it('tooltip has descriptive text', () => {
      const html = wrapper.html()
      expect(html).toContain('v-tooltip')
    })
  })

  describe('Component Integration', () => {
    it('component can be mounted independently', () => {
      const independentWrapper = mount(McpIntegrationCard, {
        global: {
          plugins: [vuetify],
          stubs: {
            AiToolConfigWizard: true,
          },
        },
      })

      expect(independentWrapper.exists()).toBe(true)
      independentWrapper.unmount()
    })

    it('does not have any props (standalone component)', () => {
      const propsKeys = Object.keys(wrapper.vm.$props || {})
      expect(propsKeys.length).toBe(0)
    })

    it('does not emit any events (standalone component)', async () => {
      await wrapper.vm.$nextTick()
      const emitted = wrapper.emitted()
      expect(Object.keys(emitted || {}).length).toBe(0)
    })
  })

  describe('Content Accuracy', () => {
    it('title matches component definition', () => {
      const text = wrapper.text()
      expect(text).toContain('GiljoAI MCP')
    })

    it('tooltip contains full description text', () => {
      const html = wrapper.html()
      expect(html).toContain('Connect your AI coding agent to GiljoAI orchestration')
      expect(html).toContain('Supports Claude Code, Codex CLI, and Gemini CLI')
    })

    it('card description mentions Configurator', () => {
      const text = wrapper.text()
      expect(text).toContain('Configurator')
    })
  })
})
