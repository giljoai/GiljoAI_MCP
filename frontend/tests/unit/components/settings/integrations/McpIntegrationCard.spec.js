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

    it('renders as an intg-line row', () => {
      const html = wrapper.html()
      expect(html).toContain('intg-line')
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

    it('contains image element for GiljoAI logo', () => {
      // Redesign: v-avatar replaced by v-img with giljo_YW_Face.svg
      const html = wrapper.html()
      expect(html).toContain('giljo_YW_Face.svg')
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
    it('has clickable icon that opens the configurator', () => {
      // Redesign (commits 4848bebf6→1d03663c5→3db8a1cdb): intg-card--clickable removed;
      // click handler now lives on the intg-line-icon element via @click="wizardRef?.open()"
      const html = wrapper.html()
      expect(html).toContain('Open the Configurator')
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
    it('has title-row section for header', () => {
      // Redesign: d-flex.align-center replaced by intg-line-title-row
      const titleRow = wrapper.find('.intg-line-title-row')
      expect(titleRow.exists()).toBe(true)
    })

    it('has action section for wizard', () => {
      // Redesign: d-flex.justify-center replaced by intg-line-action
      const actionDiv = wrapper.find('.intg-line-action')
      expect(actionDiv.exists()).toBe(true)
    })
  })

  describe('Typography', () => {
    it('title is in intg-line-title element', () => {
      // Redesign: intg-card-title renamed to intg-line-title
      const title = wrapper.find('.intg-line-title')
      expect(title.exists()).toBe(true)
      expect(title.text()).toContain('GiljoAI MCP')
    })

    it('description is in intg-line-sub element', () => {
      // Redesign: intg-card-desc renamed to intg-line-sub
      const desc = wrapper.find('.intg-line-sub')
      expect(desc.exists()).toBe(true)
      expect(desc.text()).toContain('Attach your AI coding agents')
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

  describe('Connect button presence (FE-2003 regression)', () => {
    it('renders AiToolConfigWizard\'s visible Configurator (Connect) button in the action slot', () => {
      // FE-2003: the card's ONLY visible action control is the wizard's built-in
      // Configurator pill. Regression 2e09fde79 (tsk-8001) passed :no-activator,
      // which suppressed that pill and left the action slot empty -- the card
      // "lost its Connect button" while sibling cards kept their visible controls.
      // Every other connect card exposes a visible action control; this one must too.
      //
      // Uses the REAL AiToolConfigWizard (not stubbed) with a VDialog stub that
      // renders the "activator" scoped slot -- the global VDialog mock in
      // tests/setup.js drops named slots entirely, which would hide the pill.
      // This reproduces AiToolConfigWizard's own template decision
      // (`v-if="!noActivator"` on the #activator slot).
      const realWrapper = mount(McpIntegrationCard, {
        global: {
          plugins: [vuetify],
          stubs: {
            'v-dialog': {
              template: '<div class="v-dialog-stub"><slot name="activator" :props="{}" /><slot /></div>',
            },
          },
        },
      })

      // The visible Connect/Configurator button must render in the action slot.
      const configuratorPill = realWrapper.find('.intg-line-action .configurator-pill')
      expect(configuratorPill.exists()).toBe(true)

      // The brand-icon trigger stays as an additional affordance.
      const cardTrigger = realWrapper.find('.intg-line-icon--link')
      expect(cardTrigger.exists()).toBe(true)

      realWrapper.unmount()
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
      expect(html).toContain('Supports Claude Code CLI, Claude Desktop, Codex CLI, and Gemini CLI')
    })

    it('card description mentions Configurator', () => {
      const text = wrapper.text()
      expect(text).toContain('Configurator')
    })
  })
})
