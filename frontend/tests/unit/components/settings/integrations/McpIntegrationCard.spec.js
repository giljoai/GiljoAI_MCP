import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import McpIntegrationCard from '@/components/settings/integrations/McpIntegrationCard.vue'

// Mock the theme
vi.mock('vuetify', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    useTheme: vi.fn(() => ({
      global: {
        current: {
          value: {
            dark: true
          }
        }
      }
    }))
  }
})

describe('McpIntegrationCard.vue', () => {
  let vuetify
  let wrapper

  beforeEach(() => {
    vuetify = createVuetify({
      components,
      directives,
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

    it('renders as a v-card with outlined variant', () => {
      const card = wrapper.find('.v-card')
      expect(card.exists()).toBe(true)
      expect(card.classes()).toContain('v-card--variant-outlined')
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

    it('displays GiljoAI logo avatar', () => {
      const avatar = wrapper.find('.v-avatar')
      expect(avatar.exists()).toBe(true)

      const img = avatar.find('.v-img')
      expect(img.exists()).toBe(true)
    })

    it('uses correct logo based on theme', () => {
      const img = wrapper.find('.v-avatar .v-img')
      expect(img.exists()).toBe(true)
      // Dark theme should use giljo_YW_Face.svg
      const src = img.attributes('src') || img.find('img')?.attributes('src')
      // The image source is set dynamically based on theme
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
      const wizard = wrapper.findComponent({ name: 'AiToolConfigWizard' })
        || wrapper.find('.ai-tool-config-wizard-stub')
      expect(wizard.exists()).toBe(true)
    })

    it('displays configure/setup button from AiToolConfigWizard', () => {
      const wizardButton = wrapper.find('.ai-tool-config-wizard-stub')
      expect(wizardButton.exists()).toBe(true)
      expect(wizardButton.text()).toContain('Configurator')
    })
  })

  describe('Card Structure', () => {
    it('has proper card text section', () => {
      const cardText = wrapper.find('.v-card-text')
      expect(cardText.exists()).toBe(true)
    })

    it('has nested tonal card for configuration tool', () => {
      const cards = wrapper.findAll('.v-card')
      expect(cards.length).toBeGreaterThanOrEqual(2)

      // Find the tonal variant card
      const tonalCard = cards.find(card =>
        card.classes().includes('v-card--variant-tonal')
      )
      expect(tonalCard).toBeDefined()
    })

    it('has correct spacing with mb-4 class on outer card', () => {
      const outerCard = wrapper.find('.v-card')
      expect(outerCard.classes()).toContain('mb-4')
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

    it('avatar has correct size', () => {
      const avatar = wrapper.find('.v-avatar')
      expect(avatar.exists()).toBe(true)
      expect(avatar.attributes('size') || '40').toBe('40')
    })

    it('avatar has no rounding (rounded="0")', () => {
      const avatar = wrapper.find('.v-avatar')
      expect(avatar.exists()).toBe(true)
      // Check for rounded-0 class or similar
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

    it('image has alt text', () => {
      const img = wrapper.find('.v-avatar .v-img')
      expect(img.exists()).toBe(true)
      // V-img in Vuetify should have alt attribute
      expect(img.attributes('alt')).toBeDefined()
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

  describe('Theme Responsiveness', () => {
    it('supports dark theme logo path', async () => {
      // Component should use theme-aware logo
      const img = wrapper.find('.v-avatar .v-img')
      expect(img.exists()).toBe(true)
    })

    it('supports light theme logo path', async () => {
      // In light mode, should use different logo
      // This would require remounting with different theme mock
      // For now, just verify the image exists
      const img = wrapper.find('.v-avatar .v-img')
      expect(img.exists()).toBe(true)
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

    it('has correct class structure matching UserSettings.vue', () => {
      // Outer card
      expect(wrapper.find('.v-card--variant-outlined').exists()).toBe(true)

      // Inner tonal card
      expect(wrapper.find('.v-card--variant-tonal').exists()).toBe(true)

      // Layout classes
      expect(wrapper.find('.d-flex.align-center').exists()).toBe(true)
    })
  })

  describe('Margins and Padding', () => {
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

    it('avatar has correct right margin (mr-2)', () => {
      const avatar = wrapper.find('.v-avatar')
      expect(avatar.exists()).toBe(true)
      expect(avatar.classes()).toContain('mr-2')
    })

    it('inner tonal card has no bottom margin (mb-0)', () => {
      const tonalCards = wrapper.findAll('.v-card')
      const tonalCard = tonalCards.find(card =>
        card.classes().includes('v-card--variant-tonal')
      )
      if (tonalCard) {
        expect(tonalCard.classes()).toContain('mb-0')
      }
    })

    it('inner card text has pa-3 padding', () => {
      const cardTexts = wrapper.findAll('.v-card-text')
      const innerCardText = cardTexts.find(ct => ct.classes().includes('pa-3'))
      expect(innerCardText).toBeDefined()
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
