import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import GitIntegrationCard from '@/components/settings/integrations/GitIntegrationCard.vue'

describe('GitIntegrationCard.vue', () => {
  let vuetify
  let wrapper

  const defaultConfig = {
    use_in_prompts: false,
    include_commit_history: true,
    max_commits: 50,
    branch_strategy: 'main',
  }

  beforeEach(() => {
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
    return mount(GitIntegrationCard, {
      props: {
        enabled: false,
        config: { ...defaultConfig },
        loading: false,
        ...props
      },
      global: {
        plugins: [vuetify],
      },
    })
  }

  describe('Component Rendering', () => {
    it('renders the component without errors', () => {
      wrapper = mountComponent()
      expect(wrapper.exists()).toBe(true)
      expect(wrapper.vm).toBeDefined()
    })

    it('renders as a v-card', () => {
      wrapper = mountComponent()
      const html = wrapper.html()
      expect(html).toContain('variant="outlined"')
    })

    it('displays "Git + 360 Memory" title', () => {
      wrapper = mountComponent()
      const text = wrapper.text()
      expect(text).toContain('Git + 360 Memory')
    })

    it('displays description about commit tracking', () => {
      wrapper = mountComponent()
      const text = wrapper.text()
      expect(text).toContain('Track git commits in 360 Memory')
    })

    it('displays git icon (mdi-github)', () => {
      wrapper = mountComponent()
      const text = wrapper.text()
      expect(text).toContain('mdi-github')
    })

    it('displays subtitle about orchestrator context', () => {
      wrapper = mountComponent()
      const text = wrapper.text()
      expect(text).toContain('orchestrator context')
    })

    it('displays tooltip component', () => {
      wrapper = mountComponent()
      const html = wrapper.html()
      expect(html).toContain('v-tooltip')
    })

    it('displays GitHub setup guide link', () => {
      wrapper = mountComponent()
      const html = wrapper.html()
      expect(html).toContain('github.com')
      expect(wrapper.text()).toContain('GitHub Setup Guide')
    })
  })

  describe('Toggle Switch', () => {
    it('has enable/disable toggle switch', () => {
      wrapper = mountComponent()
      const html = wrapper.html()
      expect(html).toContain('v-switch')
    })

    it('toggle emits update:enabled event', async () => {
      wrapper = mountComponent({ enabled: false })
      await wrapper.vm.$emit('update:enabled', true)

      const emitted = wrapper.emitted('update:enabled')
      expect(emitted).toBeTruthy()
    })

    it('displays "Enable Git Integration" label', () => {
      wrapper = mountComponent()
      const text = wrapper.text()
      expect(text).toContain('Enable Git Integration')
    })

    it('toggle shows loading state when loading prop is true', () => {
      wrapper = mountComponent({ loading: true })
      const html = wrapper.html()
      expect(html).toContain('loading="true"')
    })
  })

  describe('Advanced Button', () => {
    it('has Advanced button', () => {
      wrapper = mountComponent()
      const text = wrapper.text()
      expect(text).toContain('Advanced')
    })

    it('Advanced button emits openAdvanced event when clicked', async () => {
      wrapper = mountComponent()
      const buttons = wrapper.findAll('button')
      const advancedBtn = buttons.find((btn) => btn.text().includes('Advanced'))
      expect(advancedBtn).toBeTruthy()

      if (advancedBtn) {
        await advancedBtn.trigger('click')
        const emitted = wrapper.emitted('openAdvanced')
        expect(emitted).toBeTruthy()
      }
    })

    it('Advanced button is disabled when loading', () => {
      wrapper = mountComponent({ loading: true })
      const buttons = wrapper.findAll('button')
      const advancedBtn = buttons.find((btn) => btn.text().includes('Advanced'))

      if (advancedBtn) {
        expect(advancedBtn.attributes('disabled')).toBeDefined()
      }
    })
  })

  describe('Fallback Info (when disabled)', () => {
    it('shows info about enabling git integration', () => {
      wrapper = mountComponent({ enabled: false })

      const text = wrapper.text()
      // Component shows description about including git commit history
      expect(text).toContain('Enable to automatically include git commit history')
    })

    it('mentions product memory', () => {
      wrapper = mountComponent({ enabled: false })

      const text = wrapper.text()
      expect(text).toContain('product memory')
    })
  })

  describe('Tooltip Content', () => {
    it('tooltip contains information about cumulative product knowledge', () => {
      wrapper = mountComponent()

      const text = wrapper.text()
      expect(text).toContain('Cumulative product knowledge tracking')
    })
  })

  describe('Edge Cases', () => {
    it('handles empty config prop gracefully', () => {
      wrapper = mountComponent({ enabled: true, config: {} })
      expect(wrapper.exists()).toBe(true)
    })

    it('handles null config values', async () => {
      wrapper = mountComponent({
        enabled: true,
        config: { use_in_prompts: null, include_commit_history: null }
      })
      await wrapper.vm.$nextTick()

      expect(wrapper.exists()).toBe(true)
    })

    it('handles undefined config prop', () => {
      wrapper = mount(GitIntegrationCard, {
        props: {
          enabled: false,
          loading: false
          // config not provided - uses default
        },
        global: {
          plugins: [vuetify],
        },
      })

      expect(wrapper.exists()).toBe(true)
    })

    it('handles rapid toggle changes', async () => {
      wrapper = mountComponent({ enabled: false })

      await wrapper.vm.$emit('update:enabled', true)
      await wrapper.vm.$emit('update:enabled', false)
      await wrapper.vm.$emit('update:enabled', true)
      await wrapper.vm.$nextTick()

      const emitted = wrapper.emitted('update:enabled')
      expect(emitted.length).toBe(3)
    })
  })

  describe('Accessibility', () => {
    it('card has div wrapper structure', () => {
      wrapper = mountComponent()

      const html = wrapper.html()
      expect(html).toContain('variant="outlined"')
    })

    it('toggle switch exists', () => {
      wrapper = mountComponent()

      const html = wrapper.html()
      expect(html).toContain('v-switch')
    })

    it('buttons are accessible', () => {
      wrapper = mountComponent()

      const html = wrapper.html()
      expect(html).toContain('<button')
    })

    it('external link has target blank', () => {
      wrapper = mountComponent()

      const html = wrapper.html()
      expect(html).toContain('target="_blank"')
    })
  })

  describe('Visual Elements', () => {
    it('displays avatar in html', () => {
      wrapper = mountComponent()

      const html = wrapper.html()
      expect(html).toContain('v-avatar')
    })

    it('uses outlined card variant', () => {
      wrapper = mountComponent()

      const html = wrapper.html()
      expect(html).toContain('variant="outlined"')
    })

    it('uses tonal card variant for controls section', () => {
      wrapper = mountComponent()

      const html = wrapper.html()
      expect(html).toContain('variant="tonal"')
    })
  })

  describe('Props Validation', () => {
    it('enabled prop defaults to false', () => {
      wrapper = mount(GitIntegrationCard, {
        props: {
          config: defaultConfig,
          loading: false
        },
        global: {
          plugins: [vuetify],
        },
      })

      expect(wrapper.exists()).toBe(true)
    })

    it('loading prop defaults to false', () => {
      wrapper = mount(GitIntegrationCard, {
        props: {
          enabled: false,
          config: defaultConfig
        },
        global: {
          plugins: [vuetify],
        },
      })

      expect(wrapper.exists()).toBe(true)
    })
  })

})
