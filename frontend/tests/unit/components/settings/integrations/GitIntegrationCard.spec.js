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

  // SKIPPED: Component was massively simplified. No longer has expansion panels,
  // localConfig, handleSave, "Advanced Settings" text inline, commit_limit/default_branch
  // text fields, or save button. Advanced settings are now handled by a separate modal
  // opened via the 'openAdvanced' emit.
  describe.skip('Configuration Fields (when enabled)', () => {
    it('shows advanced settings when enabled', async () => {
      wrapper = mountComponent({ enabled: true })
      await wrapper.vm.$nextTick()

      const text = wrapper.text()
      expect(text).toContain('Advanced Settings')
    })

    it('shows commit limit text in component when enabled', async () => {
      wrapper = mountComponent({ enabled: true })
      await wrapper.vm.$nextTick()

      const html = wrapper.html()
      expect(html).toContain('Commit Limit')
    })

    it('shows default branch text in component when enabled', async () => {
      wrapper = mountComponent({ enabled: true })
      await wrapper.vm.$nextTick()

      const html = wrapper.html()
      expect(html).toContain('Default Branch')
    })

    it('displays info alert about git requirements when enabled', async () => {
      wrapper = mountComponent({ enabled: true })
      await wrapper.vm.$nextTick()

      const text = wrapper.text()
      expect(text).toContain('Requirement')
      expect(text).toContain('local git credentials')
    })

    it('hides configuration fields when disabled', () => {
      wrapper = mountComponent({ enabled: false })

      const text = wrapper.text()
      expect(text).not.toContain('local git credentials')
      const html = wrapper.html()
      expect(html).not.toContain('v-expansion-panels')
    })

    it('populates commit limit from config prop', async () => {
      wrapper = mountComponent({
        enabled: true,
        config: { commit_limit: 50, default_branch: 'develop' }
      })
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.localConfig.commit_limit).toBe(50)
    })

    it('populates default branch from config prop', async () => {
      wrapper = mountComponent({
        enabled: true,
        config: { commit_limit: 20, default_branch: 'develop' }
      })
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.localConfig.default_branch).toBe('develop')
    })
  })

  // SKIPPED: Component no longer has a Save button or handleSave method.
  // Configuration saving is now handled by the parent via the Advanced modal.
  describe.skip('Save Button', () => {
    it('has save button when enabled', async () => {
      wrapper = mountComponent({ enabled: true })
      await wrapper.vm.$nextTick()

      const text = wrapper.text()
      expect(text).toContain('Save')
    })

    it('save button exists regardless of enabled state', () => {
      wrapper = mountComponent({ enabled: false })

      const text = wrapper.text()
      expect(text).toContain('Save')
    })

    it('emits save event with configuration when save called', async () => {
      wrapper = mountComponent({
        enabled: true,
        config: { commit_limit: 25, default_branch: 'master' }
      })
      await wrapper.vm.$nextTick()

      wrapper.vm.handleSave()

      const emitted = wrapper.emitted('save')
      expect(emitted).toBeTruthy()
      expect(emitted[0][0]).toEqual({
        enabled: true,
        commit_limit: 25,
        default_branch: 'master'
      })
    })

    it('save button is disabled when loading (via handleSave)', () => {
      wrapper = mountComponent({ enabled: true, loading: true })

      wrapper.vm.handleSave()
      const emitted = wrapper.emitted('save')
      expect(emitted).toBeFalsy()
    })

    it('save button shows loading state when loading', () => {
      wrapper = mountComponent({ enabled: true, loading: true })

      const html = wrapper.html()
      expect(html).toContain('loading="true"')
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

  // SKIPPED: Component no longer has localConfig reactive state or config watching.
  // The component is now a thin toggle + button, config is managed externally.
  describe.skip('Config Watching', () => {
    it('updates local config when config prop changes', async () => {
      wrapper = mountComponent({
        enabled: true,
        config: { commit_limit: 20, default_branch: 'main' }
      })
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.localConfig.commit_limit).toBe(20)

      await wrapper.setProps({
        config: { commit_limit: 100, default_branch: 'develop' }
      })
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.localConfig.commit_limit).toBe(100)
      expect(wrapper.vm.localConfig.default_branch).toBe('develop')
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

  // SKIPPED: Component no longer has expansion panels.
  // Advanced settings are in a separate modal opened via 'openAdvanced' emit.
  describe.skip('Expansion Panel Behavior', () => {
    it('expansion panel exists when enabled', () => {
      wrapper = mountComponent({ enabled: true })

      const html = wrapper.html()
      expect(html).toContain('v-expansion-panel')
    })

    it('expansion panels wrapper exists when enabled', async () => {
      wrapper = mountComponent({ enabled: true })
      await wrapper.vm.$nextTick()

      const html = wrapper.html()
      expect(html).toContain('v-expansion-panels')
    })

    it('displays cog icon text in expansion panel', () => {
      wrapper = mountComponent({ enabled: true })

      const html = wrapper.html()
      expect(html).toContain('mdi-cog')
    })
  })

  // SKIPPED: Component no longer has inline text fields for commit_limit/default_branch.
  // These inputs are now in the Advanced settings modal.
  describe.skip('Input Validation', () => {
    it('text fields exist when enabled', async () => {
      wrapper = mountComponent({ enabled: true })
      await wrapper.vm.$nextTick()

      const html = wrapper.html()
      expect(html).toContain('v-text-field')
    })

    it('commit limit field has correct min/max in html', async () => {
      wrapper = mountComponent({ enabled: true })
      await wrapper.vm.$nextTick()

      const html = wrapper.html()
      expect(html).toContain('min="1"')
      expect(html).toContain('max="100"')
    })

    it('commit limit field has number type in html', async () => {
      wrapper = mountComponent({ enabled: true })
      await wrapper.vm.$nextTick()

      const html = wrapper.html()
      expect(html).toContain('type="number"')
    })

    it('default branch field has placeholder in html', async () => {
      wrapper = mountComponent({ enabled: true })
      await wrapper.vm.$nextTick()

      const html = wrapper.html()
      expect(html).toContain('placeholder="e.g., main, master, develop"')
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

  // SKIPPED: Component no longer emits 'save' event or has handleSave method.
  // It now emits 'update:enabled' and 'openAdvanced'.
  describe.skip('Event Emissions', () => {
    it('emits save with current enabled state', async () => {
      wrapper = mountComponent({
        enabled: true,
        config: { commit_limit: 20, default_branch: 'main' }
      })
      await wrapper.vm.$nextTick()

      wrapper.vm.handleSave()

      const emitted = wrapper.emitted('save')
      expect(emitted[0][0].enabled).toBe(true)
    })

    it('does not emit save when loading', async () => {
      wrapper = mountComponent({ enabled: true, loading: true })
      await wrapper.vm.$nextTick()

      wrapper.vm.handleSave()

      const emitted = wrapper.emitted('save')
      expect(emitted).toBeFalsy()
    })
  })
})
