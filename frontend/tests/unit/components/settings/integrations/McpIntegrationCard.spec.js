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
        defaultTheme: 'dark'
      }
    })

    wrapper = mount(McpIntegrationCard, {
      global: {
        plugins: [vuetify],
        stubs: {
          AiToolConfigWizard: {
            template: '<button class="ai-tool-config-wizard-stub">Configurator</button>'
          }
        }
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

    it('renders v-card component', () => {
      // Check for card element - in test environment, v-card renders as div with variant
      const html = wrapper.html()
      expect(html).toContain('variant="outlined"')
    })

    it('displays "GiljoAI MCP Integration" title', () => {
      const title = wrapper.find('h3')
      expect(title.exists()).toBe(true)
      expect(title.text()).toBe('GiljoAI MCP Integration')
    })

    it('displays description about MCP configuration', () => {
      const text = wrapper.text()
      expect(text).toContain('Connect your AI coding tool to GiljoAI orchestration')
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
    it('displays MCP Configuration Tool heading', () => {
      const text = wrapper.text()
      expect(text).toContain('MCP Configuration Tool')
    })

    it('displays configuration tool description', () => {
      const text = wrapper.text()
      expect(text).toContain('Creates MCP integration CLI command')
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
  })

  describe('Card Structure', () => {
    it('has proper card text section', () => {
      const html = wrapper.html()
      // In test environment, v-card-text renders as div
      expect(html).toContain('pa-3')
    })

    it('has nested cards in structure', () => {
      const html = wrapper.html()
      // Should have multiple cards (outer outlined, inner tonal)
      // Check for variant attributes which indicate card components
      expect(html).toContain('variant="outlined"')
      expect(html).toContain('variant="tonal"')
    })

    it('outer card has mb-4 spacing class', () => {
      const html = wrapper.html()
      expect(html).toContain('mb-4')
    })
  })

  describe('Layout and Alignment', () => {
    it('has proper flex layout for header section', () => {
      const headerDiv = wrapper.find('.d-flex.align-center.mb-3')
      expect(headerDiv.exists()).toBe(true)
    })

    it('has proper flex layout for configuration tool section', () => {
      const configDiv = wrapper.find('.d-flex.align-center.justify-between')
      expect(configDiv.exists()).toBe(true)
    })
  })

  describe('Typography', () => {
    it('title uses text-h6 class', () => {
      const title = wrapper.find('h3')
      expect(title.exists()).toBe(true)
      expect(title.classes()).toContain('text-h6')
    })

    it('title has no bottom margin (mb-0)', () => {
      const title = wrapper.find('h3')
      expect(title.exists()).toBe(true)
      expect(title.classes()).toContain('mb-0')
    })

    it('description uses text-body-2 class', () => {
      const paragraphs = wrapper.findAll('p')
      const descriptionP = paragraphs.find(p =>
        p.text().includes('Connect your AI coding tool')
      )
      expect(descriptionP).toBeDefined()
      if (descriptionP) {
        expect(descriptionP.classes()).toContain('text-body-2')
      }
    })

    it('description uses text-medium-emphasis class', () => {
      const paragraphs = wrapper.findAll('p')
      const descriptionP = paragraphs.find(p =>
        p.text().includes('Connect your AI coding tool')
      )
      if (descriptionP) {
        expect(descriptionP.classes()).toContain('text-medium-emphasis')
      }
    })

    it('config tool title uses text-subtitle-2 class', () => {
      const subtitle = wrapper.find('.text-subtitle-2')
      expect(subtitle.exists()).toBe(true)
      expect(subtitle.text()).toBe('MCP Configuration Tool')
    })

    it('config tool description uses text-body-2 class', () => {
      const configTexts = wrapper.findAll('.text-body-2')
      const configDesc = configTexts.find(el =>
        el.text().includes('Creates MCP integration CLI command')
      )
      expect(configDesc).toBeDefined()
    })
  })

  describe('Accessibility', () => {
    it('uses semantic h3 heading for title', () => {
      const heading = wrapper.find('h3')
      expect(heading.exists()).toBe(true)
    })

    it('has proper text content for screen readers', () => {
      const text = wrapper.text()
      expect(text.length).toBeGreaterThan(0)
      expect(text).toContain('GiljoAI MCP Integration')
      expect(text).toContain('MCP Configuration Tool')
    })

    it('contains image element for accessibility', () => {
      const html = wrapper.html()
      // Should have image element with alt text
      // In test environment, v-img renders as div with src and alt
      expect(html).toContain('alt="GiljoAI MCP"')
    })
  })

  describe('Component Integration', () => {
    it('component can be mounted independently', () => {
      const independentWrapper = mount(McpIntegrationCard, {
        global: {
          plugins: [vuetify],
          stubs: {
            AiToolConfigWizard: true
          }
        },
      })

      expect(independentWrapper.exists()).toBe(true)
      independentWrapper.unmount()
    })

    it('does not have any props (standalone component)', () => {
      // McpIntegrationCard should be a standalone component with no required props
      const propsKeys = Object.keys(wrapper.vm.$props || {})
      expect(propsKeys.length).toBe(0)
    })

    it('does not emit any events (standalone component)', async () => {
      await wrapper.vm.$nextTick()
      const emitted = wrapper.emitted()
      // Component should not emit events by itself on mount
      expect(Object.keys(emitted || {}).length).toBe(0)
    })
  })

  describe('Content Accuracy', () => {
    it('matches content from UserSettings.vue MCP integration section', () => {
      const text = wrapper.text()

      // Title
      expect(text).toContain('GiljoAI MCP Integration')

      // Description
      expect(text).toContain('Connect your AI coding tool to GiljoAI orchestration')
      expect(text).toContain('Supports Claude Code, Codex CLI, and Gemini CLI')

      // Configuration tool section
      expect(text).toContain('MCP Configuration Tool')
      expect(text).toContain('Creates MCP integration CLI command')
    })

    it('has correct class structure for layout', () => {
      // Layout classes
      expect(wrapper.find('.d-flex.align-center').exists()).toBe(true)
      expect(wrapper.find('.flex-grow-1').exists()).toBe(true)
      expect(wrapper.find('.justify-between').exists()).toBe(true)
    })
  })

  describe('Margins and Spacing', () => {
    it('description has correct bottom margin (mb-4)', () => {
      const paragraphs = wrapper.findAll('p')
      const descriptionP = paragraphs.find(p =>
        p.text().includes('Connect your AI coding tool')
      )
      if (descriptionP) {
        expect(descriptionP.classes()).toContain('mb-4')
      }
    })

    it('header section has correct bottom margin (mb-3)', () => {
      const headerDiv = wrapper.find('.d-flex.align-center.mb-3')
      expect(headerDiv.exists()).toBe(true)
    })

    it('inner tonal card has no bottom margin (mb-0)', () => {
      const html = wrapper.html()
      // Check that mb-0 is present for inner card
      expect(html).toContain('mb-0')
    })
  })

  describe('Flex Container Properties', () => {
    it('flex-grow-1 applied to content section', () => {
      const flexGrow = wrapper.find('.flex-grow-1')
      expect(flexGrow.exists()).toBe(true)
    })

    it('justify-between applied to configuration tool row', () => {
      const justifyBetween = wrapper.find('.justify-between')
      expect(justifyBetween.exists()).toBe(true)
    })
  })
})
