/**
 * Test suite for AdminIntegrationsTab.vue component
 * Handover 0321: Settings Componentization
 *
 * Tests the Admin Integrations tab:
 * - Component renders integration cards
 * - Displays Claude Code integration card with description
 * - Displays Codex CLI integration card with description
 * - Displays Gemini CLI integration card with description
 * - Shows Serena MCP native integration section
 * - Shows "More Coming Soon" placeholder
 * - Displays info alert about user configuration in My Settings
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import AdminIntegrationsTab from '@/components/settings/tabs/AdminIntegrationsTab.vue'

// Mock router-link
const RouterLinkStub = {
  name: 'RouterLink',
  template: '<a><slot /></a>',
  props: ['to']
}

describe('AdminIntegrationsTab.vue', () => {
  let vuetify
  let wrapper

  beforeEach(() => {
    // Setup Vuetify
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

  const mountComponent = () => {
    return mount(AdminIntegrationsTab, {
      global: {
        plugins: [vuetify],
        stubs: {
          'router-link': RouterLinkStub,
          'CodexMarkIcon': {
            name: 'CodexMarkIcon',
            template: '<span class="codex-icon-stub">Codex</span>'
          }
        }
      }
    })
  }

  describe('Component Rendering', () => {
    it('renders the component', () => {
      wrapper = mountComponent()
      expect(wrapper.exists()).toBe(true)
    })

    it('displays card title "Integrations"', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()
      expect(wrapper.text()).toContain('Integrations')
    })

    it('displays card subtitle about admin overview', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()
      expect(wrapper.text()).toContain('Agent coding tools and native integrations')
      expect(wrapper.text()).toContain('Admin overview')
    })

    it('displays info alert about configuring AI tools in My Settings', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()
      expect(wrapper.text()).toContain('Configure AI Coding Tools')
      expect(wrapper.text()).toContain('My Settings')
      expect(wrapper.text()).toContain('MCP Configuration')
    })
  })

  describe('Agent Coding Tools Section', () => {
    it('displays "Agent Coding Tools" section header', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()
      expect(wrapper.text()).toContain('Agent Coding Tools')
    })

    describe('Claude Code Card', () => {
      it('displays Claude Code CLI card', async () => {
        wrapper = mountComponent()
        await wrapper.vm.$nextTick()
        expect(wrapper.text()).toContain('Claude Code CLI')
      })

      it('shows Claude Code description', async () => {
        wrapper = mountComponent()
        await wrapper.vm.$nextTick()
        expect(wrapper.text()).toContain('AI-powered development with MCP integration')
      })

      it('mentions MCP configuration in description', async () => {
        wrapper = mountComponent()
        await wrapper.vm.$nextTick()
        expect(wrapper.text()).toContain('GiljoAI Agent Orchestration MCP Server')
        expect(wrapper.text()).toContain('integrates seamlessly with Claude Code CLI')
      })

      it('describes sub-agent architecture', async () => {
        wrapper = mountComponent()
        await wrapper.vm.$nextTick()
        expect(wrapper.text()).toContain('Sub-agent Architecture')
        expect(wrapper.text()).toContain('Claude Code native sub-agent tools')
      })
    })

    describe('Codex CLI Card', () => {
      it('displays Codex CLI card', async () => {
        wrapper = mountComponent()
        await wrapper.vm.$nextTick()
        expect(wrapper.text()).toContain('Codex CLI')
      })

      it('shows Codex CLI description', async () => {
        wrapper = mountComponent()
        await wrapper.vm.$nextTick()
        expect(wrapper.text()).toContain('Advanced code generation and analysis')
      })

      it('describes sub-agent coordination', async () => {
        wrapper = mountComponent()
        await wrapper.vm.$nextTick()
        expect(wrapper.text()).toContain('sub-agent architecture')
        expect(wrapper.text()).toContain('complex development workflows')
      })

      it('describes integration model', async () => {
        wrapper = mountComponent()
        await wrapper.vm.$nextTick()
        expect(wrapper.text()).toContain('Integration model')
        expect(wrapper.text()).toContain('Multiple terminal windows')
      })
    })

    describe('Gemini CLI Card', () => {
      it('displays Gemini CLI card', async () => {
        wrapper = mountComponent()
        await wrapper.vm.$nextTick()
        expect(wrapper.text()).toContain('Gemini CLI')
      })

      it('shows Gemini CLI description', async () => {
        wrapper = mountComponent()
        await wrapper.vm.$nextTick()
        expect(wrapper.text()).toContain("Google's advanced AI development platform")
      })

      it('mentions multi-modal capabilities', async () => {
        wrapper = mountComponent()
        await wrapper.vm.$nextTick()
        expect(wrapper.text()).toContain('enhanced reasoning and multi-modal capabilities')
      })

      it('describes integration model', async () => {
        wrapper = mountComponent()
        await wrapper.vm.$nextTick()
        // Gemini has same integration model text
        const text = wrapper.text()
        expect(text).toContain('orchestrator session')
        expect(text).toContain('activation prompts')
      })
    })
  })

  describe('Native Integrations Section', () => {
    it('displays "Native Integrations" section header', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()
      expect(wrapper.text()).toContain('Native Integrations')
    })

    describe('Serena MCP Card', () => {
      it('displays Serena MCP card', async () => {
        wrapper = mountComponent()
        await wrapper.vm.$nextTick()
        expect(wrapper.text()).toContain('Serena MCP')
      })

      it('shows Serena MCP description', async () => {
        wrapper = mountComponent()
        await wrapper.vm.$nextTick()
        expect(wrapper.text()).toContain('Intelligent codebase understanding and navigation')
      })

      it('describes Serena capabilities', async () => {
        wrapper = mountComponent()
        await wrapper.vm.$nextTick()
        expect(wrapper.text()).toContain('semantic code analysis')
        expect(wrapper.text()).toContain('symbol navigation')
      })

      it('has GitHub repository link', async () => {
        wrapper = mountComponent()
        await wrapper.vm.$nextTick()
        expect(wrapper.text()).toContain('GitHub Repository')
        expect(wrapper.html()).toContain('https://github.com/oraios/serena')
      })

      it('credits Oraios', async () => {
        wrapper = mountComponent()
        await wrapper.vm.$nextTick()
        expect(wrapper.text()).toContain('Credit: Oraios')
      })

      it('mentions user configuration in User Settings', async () => {
        wrapper = mountComponent()
        await wrapper.vm.$nextTick()
        expect(wrapper.text()).toContain('User Configuration')
        expect(wrapper.text()).toContain('User Settings')
        expect(wrapper.text()).toContain('Integrations')
      })
    })

    describe('More Coming Soon Card', () => {
      it('displays "More Integrations Coming Soon" placeholder', async () => {
        wrapper = mountComponent()
        await wrapper.vm.$nextTick()
        expect(wrapper.text()).toContain('More Integrations Coming Soon')
      })

      it('shows placeholder message about future releases', async () => {
        wrapper = mountComponent()
        await wrapper.vm.$nextTick()
        expect(wrapper.text()).toContain('Additional native integrations')
        expect(wrapper.text()).toContain('future releases')
      })
    })
  })

  describe('Layout and Structure', () => {
    it('contains v-card wrapper', () => {
      wrapper = mountComponent()
      // Check for v-card class in the HTML
      expect(wrapper.html()).toContain('v-card')
    })

    it('has multiple integration cards', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()

      // Should have integration cards for Claude, Codex, Gemini, Serena, Coming Soon
      // Verify by checking for card text content that identifies each integration
      const text = wrapper.text()
      expect(text).toContain('Claude Code CLI')
      expect(text).toContain('Codex CLI')
      expect(text).toContain('Gemini CLI')
      expect(text).toContain('Serena MCP')
      expect(text).toContain('More Integrations Coming Soon')
    })

    it('has section divider between Agent Coding Tools and Native Integrations', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()

      // Verify both sections exist, implying a divider between them
      const text = wrapper.text()
      expect(text).toContain('Agent Coding Tools')
      expect(text).toContain('Native Integrations')
      // Also verify template includes divider element
      expect(wrapper.html()).toMatch(/<hr|divider/i)
    })

    it('displays avatars for each integration', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()

      // Check for v-avatar in HTML
      const avatarCount = (wrapper.html().match(/v-avatar/g) || []).length
      // Should have avatars for Claude, Codex, Gemini, Serena
      expect(avatarCount).toBeGreaterThanOrEqual(4)
    })
  })

  describe('Links and Navigation', () => {
    it('has router-link to My Settings', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()

      const links = wrapper.findAllComponents(RouterLinkStub)
      const settingsLinks = links.filter(link => link.props('to') === '/settings')
      expect(settingsLinks.length).toBeGreaterThan(0)
    })
  })

  describe('Icons', () => {
    it('displays icon for info alert', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()

      // Check for mdi icons in HTML
      expect(wrapper.html()).toContain('mdi-')
    })

    it('displays plus icon for More Coming Soon card', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()

      expect(wrapper.html()).toContain('mdi-plus-circle-outline')
    })
  })
})
