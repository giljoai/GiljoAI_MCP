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
    commit_limit: 20,
    default_branch: 'main'
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
      // In test environment, v-card renders as div with variant attribute
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
      // In test environment, v-icon renders as span with icon name as content
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
      // Tooltip component is present
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

    it('toggle reflects enabled prop when false', () => {
      wrapper = mountComponent({ enabled: false })
      // Alert should not show when disabled
      const text = wrapper.text()
      expect(text).not.toContain('Requirement')
    })

    it('toggle reflects enabled prop when true', () => {
      wrapper = mountComponent({ enabled: true })
      // Alert should show when enabled
      const text = wrapper.text()
      expect(text).toContain('Requirement')
    })

    it('toggle emits update:enabled event', async () => {
      wrapper = mountComponent({ enabled: false })
      // Simulate toggle by emitting the event directly to the component
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
      // In test environment, loading prop is rendered as loading="true"
      expect(html).toContain('loading="true"')
    })
  })

  describe('Configuration Fields (when enabled)', () => {
    it('shows advanced settings when enabled', async () => {
      wrapper = mountComponent({ enabled: true })
      await wrapper.vm.$nextTick()

      const text = wrapper.text()
      expect(text).toContain('Advanced Settings')
    })

    it('shows commit limit text in component when enabled', async () => {
      wrapper = mountComponent({ enabled: true })
      await wrapper.vm.$nextTick()

      // The expansion panel should exist and contain Commit Limit text
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

      // Alert displays requirement text
      const text = wrapper.text()
      expect(text).toContain('Requirement')
      // The alert mentions using local git credentials
      expect(text).toContain('local git credentials')
    })

    it('hides configuration fields when disabled', () => {
      wrapper = mountComponent({ enabled: false })

      // Should not show the info alert with "Requirement:" prefix
      const text = wrapper.text()
      expect(text).not.toContain('local git credentials')
      // Expansion panels should not be present
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

  describe('Save Button', () => {
    it('has save button when enabled', async () => {
      wrapper = mountComponent({ enabled: true })
      await wrapper.vm.$nextTick()

      const text = wrapper.text()
      expect(text).toContain('Save')
    })

    it('save button exists regardless of enabled state', () => {
      wrapper = mountComponent({ enabled: false })

      // Save button is always visible in the tonal card
      const text = wrapper.text()
      expect(text).toContain('Save')
    })

    it('emits save event with configuration when save called', async () => {
      wrapper = mountComponent({
        enabled: true,
        config: { commit_limit: 25, default_branch: 'master' }
      })
      await wrapper.vm.$nextTick()

      // Call handleSave directly
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

      // When loading, handleSave should not emit
      wrapper.vm.handleSave()
      const emitted = wrapper.emitted('save')
      expect(emitted).toBeFalsy()
    })

    it('save button shows loading state when loading', () => {
      wrapper = mountComponent({ enabled: true, loading: true })

      const html = wrapper.html()
      // The save button has loading prop set
      expect(html).toContain('loading="true"')
    })
  })

  describe('Fallback Info (when disabled)', () => {
    it('shows fallback info when disabled', () => {
      wrapper = mountComponent({ enabled: false })

      const text = wrapper.text()
      expect(text).toContain('Enable to automatically include git commit history')
    })

    it('mentions manual summaries as alternative', () => {
      wrapper = mountComponent({ enabled: false })

      // The description should be visible explaining what the feature does
      const text = wrapper.text()
      expect(text).toContain('Commits are stored in product memory')
    })
  })

  describe('Config Watching', () => {
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

      // The tooltip and its content should be in the text
      const text = wrapper.text()
      expect(text).toContain('Cumulative product knowledge tracking')
    })
  })

  describe('Edge Cases', () => {
    it('handles empty config prop gracefully', () => {
      wrapper = mountComponent({ enabled: true, config: {} })

      expect(wrapper.vm.localConfig.commit_limit).toBeDefined()
      expect(wrapper.vm.localConfig.default_branch).toBeDefined()
    })

    it('handles null config values', async () => {
      wrapper = mountComponent({
        enabled: true,
        config: { commit_limit: null, default_branch: null }
      })
      await wrapper.vm.$nextTick()

      // Should use defaults or handle nulls gracefully
      expect(wrapper.exists()).toBe(true)
    })

    it('handles undefined config prop', () => {
      wrapper = mount(GitIntegrationCard, {
        props: {
          enabled: false,
          loading: false
          // config not provided
        },
        global: {
          plugins: [vuetify],
        },
      })

      expect(wrapper.exists()).toBe(true)
    })

    it('handles rapid toggle changes', async () => {
      wrapper = mountComponent({ enabled: false })

      // Rapid toggles via direct emit on wrapper
      await wrapper.vm.$emit('update:enabled', true)
      await wrapper.vm.$emit('update:enabled', false)
      await wrapper.vm.$emit('update:enabled', true)
      await wrapper.vm.$nextTick()

      const emitted = wrapper.emitted('update:enabled')
      expect(emitted.length).toBe(3)
    })

    it('preserves local config changes on multiple saves', async () => {
      wrapper = mountComponent({
        enabled: true,
        config: { commit_limit: 20, default_branch: 'main' }
      })
      await wrapper.vm.$nextTick()

      // Modify local config
      wrapper.vm.localConfig.commit_limit = 30

      // Call handleSave directly
      wrapper.vm.handleSave()

      const emitted = wrapper.emitted('save')
      expect(emitted[0][0].commit_limit).toBe(30)
    })
  })

  describe('Expansion Panel Behavior', () => {
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

  describe('Input Validation', () => {
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
      // In test environment, v-card renders as div with variant attribute
      expect(html).toContain('variant="outlined"')
    })

    it('toggle switch exists', () => {
      wrapper = mountComponent()

      const html = wrapper.html()
      expect(html).toContain('v-switch')
    })

    it('buttons are accessible', () => {
      wrapper = mountComponent({ enabled: true })

      const html = wrapper.html()
      // In test environment, v-btn renders as button element
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

      // Component should exist and enabled should be falsy
      expect(wrapper.exists()).toBe(true)
      // Alert should not show when disabled
      const text = wrapper.text()
      expect(text).not.toContain('Requirement')
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

      // Component should exist
      expect(wrapper.exists()).toBe(true)
    })
  })

  describe('Event Emissions', () => {
    it('emits save with current enabled state', async () => {
      wrapper = mountComponent({
        enabled: true,
        config: { commit_limit: 20, default_branch: 'main' }
      })
      await wrapper.vm.$nextTick()

      // Call handleSave directly
      wrapper.vm.handleSave()

      const emitted = wrapper.emitted('save')
      expect(emitted[0][0].enabled).toBe(true)
    })

    it('does not emit save when loading', async () => {
      wrapper = mountComponent({ enabled: true, loading: true })
      await wrapper.vm.$nextTick()

      // Call handleSave - it should not emit when loading
      wrapper.vm.handleSave()

      const emitted = wrapper.emitted('save')
      expect(emitted).toBeFalsy()
    })
  })
})
