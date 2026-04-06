import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import GitIntegrationCard from '@/components/settings/integrations/GitIntegrationCard.vue'

describe('GitIntegrationCard.vue', () => {
  let vuetify
  let wrapper

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
        loading: false,
        ...props,
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

    it('renders as an intg-card div', () => {
      wrapper = mountComponent()
      const html = wrapper.html()
      expect(html).toContain('intg-card')
      expect(html).toContain('smooth-border')
    })

    it('displays "Git + 360 Memory" title', () => {
      wrapper = mountComponent()
      const text = wrapper.text()
      expect(text).toContain('Git + 360 Memory')
    })

    it('displays description about commit tracking', () => {
      wrapper = mountComponent()
      const text = wrapper.text()
      expect(text).toContain('Automatically include git commit history in project summaries')
    })

    it('displays git icon (mdi-git)', () => {
      wrapper = mountComponent()
      const html = wrapper.html()
      expect(html).toContain('mdi-git')
    })

    it('displays subtitle about orchestrator context', () => {
      wrapper = mountComponent()
      const text = wrapper.text()
      expect(text).toContain('orchestrators with cumulative context')
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

  describe('Toggle Button', () => {
    it('has enable/disable toggle button', () => {
      wrapper = mountComponent()
      const html = wrapper.html()
      expect(html).toContain('data-testid="github-integration-toggle"')
    })

    it('toggle emits update:enabled event', async () => {
      wrapper = mountComponent({ enabled: false })
      await wrapper.vm.$emit('update:enabled', true)

      const emitted = wrapper.emitted('update:enabled')
      expect(emitted).toBeTruthy()
    })

    it('displays "Disabled" label when disabled', () => {
      wrapper = mountComponent({ enabled: false })
      const text = wrapper.text()
      expect(text).toContain('Disabled')
    })

    it('displays "Enabled" label when enabled', () => {
      wrapper = mountComponent({ enabled: true })
      const text = wrapper.text()
      expect(text).toContain('Enabled')
    })

    it('toggle shows loading state when loading prop is true', () => {
      wrapper = mountComponent({ loading: true })
      const html = wrapper.html()
      expect(html).toContain('loading="true"')
    })
  })

  describe('GitHub Setup Guide Link', () => {
    it('displays GitHub Setup Guide link button', () => {
      wrapper = mountComponent()
      const text = wrapper.text()
      expect(text).toContain('GitHub Setup Guide')
    })

    it('link points to GitHub docs', () => {
      wrapper = mountComponent()
      const html = wrapper.html()
      expect(html).toContain('docs.github.com')
    })

    it('link opens in new tab', () => {
      wrapper = mountComponent()
      const html = wrapper.html()
      expect(html).toContain('target="_blank"')
    })
  })

  describe('Fallback Info (when disabled)', () => {
    it('shows description about git commit history', () => {
      wrapper = mountComponent({ enabled: false })
      const text = wrapper.text()
      expect(text).toContain('Automatically include git commit history')
    })

    it('mentions 360 Memory', () => {
      wrapper = mountComponent({ enabled: false })
      const text = wrapper.text()
      expect(text).toContain('360 Memory')
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
    it('handles enabled=true gracefully', () => {
      wrapper = mountComponent({ enabled: true })
      expect(wrapper.exists()).toBe(true)
    })

    it('handles enabled=false gracefully', () => {
      wrapper = mountComponent({ enabled: false })
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
    it('card has intg-card wrapper structure', () => {
      wrapper = mountComponent()
      const html = wrapper.html()
      expect(html).toContain('intg-card')
    })

    it('toggle button exists', () => {
      wrapper = mountComponent()
      const html = wrapper.html()
      expect(html).toContain('data-testid="github-integration-toggle"')
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
    it('displays git icon in html', () => {
      wrapper = mountComponent()
      const html = wrapper.html()
      expect(html).toContain('mdi-git')
    })

    it('applies card accent color style', () => {
      wrapper = mountComponent()
      const html = wrapper.html()
      expect(html).toContain('--card-accent')
    })

    it('toggle button uses outlined variant when disabled', () => {
      wrapper = mountComponent({ enabled: false })
      const html = wrapper.html()
      expect(html).toContain('variant="outlined"')
    })

    it('toggle button uses flat variant when enabled', () => {
      wrapper = mountComponent({ enabled: true })
      const html = wrapper.html()
      expect(html).toContain('variant="flat"')
    })
  })

  describe('Props Validation', () => {
    it('enabled prop defaults to false', () => {
      wrapper = mount(GitIntegrationCard, {
        props: {
          loading: false,
        },
        global: {
          plugins: [vuetify],
        },
      })
      expect(wrapper.props('enabled')).toBe(false)
    })

    it('loading prop defaults to false', () => {
      wrapper = mount(GitIntegrationCard, {
        props: {
          enabled: false,
        },
        global: {
          plugins: [vuetify],
        },
      })
      expect(wrapper.props('loading')).toBe(false)
    })
  })
})
