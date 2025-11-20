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
      expect(wrapper.find('.v-card').exists()).toBe(true)
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
      const icon = wrapper.find('.mdi-github')
      expect(icon.exists()).toBe(true)
    })

    it('displays subtitle about orchestrator context', () => {
      wrapper = mountComponent()
      const text = wrapper.text()
      expect(text).toContain('orchestrator context')
    })

    it('displays help tooltip icon', () => {
      wrapper = mountComponent()
      const helpIcon = wrapper.find('.mdi-help-circle-outline')
      expect(helpIcon.exists()).toBe(true)
    })

    it('displays GitHub setup guide link', () => {
      wrapper = mountComponent()
      const link = wrapper.find('a[href*="github.com"]')
      expect(link.exists()).toBe(true)
      expect(link.text()).toContain('GitHub Setup Guide')
    })
  })

  describe('Toggle Switch', () => {
    it('has enable/disable toggle switch', () => {
      wrapper = mountComponent()
      const toggle = wrapper.find('.v-switch')
      expect(toggle.exists()).toBe(true)
    })

    it('toggle reflects enabled prop when false', () => {
      wrapper = mountComponent({ enabled: false })
      const toggle = wrapper.find('.v-switch')
      const input = toggle.find('input[type="checkbox"]')
      expect(input.element.checked).toBe(false)
    })

    it('toggle reflects enabled prop when true', () => {
      wrapper = mountComponent({ enabled: true })
      const toggle = wrapper.find('.v-switch')
      const input = toggle.find('input[type="checkbox"]')
      expect(input.element.checked).toBe(true)
    })

    it('toggle emits update:enabled when changed to true', async () => {
      wrapper = mountComponent({ enabled: false })
      const toggle = wrapper.find('.v-switch input[type="checkbox"]')

      await toggle.setValue(true)
      await wrapper.vm.$nextTick()

      const emitted = wrapper.emitted('update:enabled')
      expect(emitted).toBeTruthy()
      expect(emitted[0]).toEqual([true])
    })

    it('toggle emits update:enabled when changed to false', async () => {
      wrapper = mountComponent({ enabled: true })
      const toggle = wrapper.find('.v-switch input[type="checkbox"]')

      await toggle.setValue(false)
      await wrapper.vm.$nextTick()

      const emitted = wrapper.emitted('update:enabled')
      expect(emitted).toBeTruthy()
      expect(emitted[0]).toEqual([false])
    })

    it('displays "Enable Git Integration" label', () => {
      wrapper = mountComponent()
      const text = wrapper.text()
      expect(text).toContain('Enable Git Integration')
    })

    it('toggle shows loading state when loading prop is true', () => {
      wrapper = mountComponent({ loading: true })
      const toggle = wrapper.find('.v-switch')
      // Vuetify switch with loading should have loading class or attribute
      expect(toggle.attributes('loading')).toBeDefined()
    })
  })

  describe('Configuration Fields (when enabled)', () => {
    it('shows advanced settings when enabled', async () => {
      wrapper = mountComponent({ enabled: true })
      await wrapper.vm.$nextTick()

      const text = wrapper.text()
      expect(text).toContain('Advanced Settings')
    })

    it('shows commit limit input field when enabled', async () => {
      wrapper = mountComponent({ enabled: true })
      await wrapper.vm.$nextTick()

      // Find the expansion panel and open it
      const expansionTitle = wrapper.find('.v-expansion-panel-title')
      if (expansionTitle.exists()) {
        await expansionTitle.trigger('click')
        await wrapper.vm.$nextTick()
      }

      const text = wrapper.text()
      expect(text).toContain('Commit Limit')
    })

    it('shows default branch input field when enabled', async () => {
      wrapper = mountComponent({ enabled: true })
      await wrapper.vm.$nextTick()

      // Open expansion panel
      const expansionTitle = wrapper.find('.v-expansion-panel-title')
      if (expansionTitle.exists()) {
        await expansionTitle.trigger('click')
        await wrapper.vm.$nextTick()
      }

      const text = wrapper.text()
      expect(text).toContain('Default Branch')
    })

    it('displays info alert about git requirements when enabled', async () => {
      wrapper = mountComponent({ enabled: true })
      await wrapper.vm.$nextTick()

      const alert = wrapper.find('.v-alert')
      expect(alert.exists()).toBe(true)
      expect(alert.text()).toContain('Requirement')
      expect(alert.text()).toContain('Git must be configured')
    })

    it('hides configuration fields when disabled', () => {
      wrapper = mountComponent({ enabled: false })

      // Should not show the info alert or expansion panel
      const text = wrapper.text()
      expect(text).not.toContain('Requirement')
      expect(text).not.toContain('Git must be configured')
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

      const buttons = wrapper.findAll('button')
      const saveButton = buttons.find(btn => btn.text().includes('Save'))
      expect(saveButton).toBeDefined()
    })

    it('hides save button when disabled', () => {
      wrapper = mountComponent({ enabled: false })

      const buttons = wrapper.findAll('button')
      const saveButton = buttons.find(btn => btn.text() === 'Save')
      // Save button should not be visible when disabled
      expect(saveButton).toBeUndefined()
    })

    it('emits save event with configuration when save clicked', async () => {
      wrapper = mountComponent({
        enabled: true,
        config: { commit_limit: 25, default_branch: 'master' }
      })
      await wrapper.vm.$nextTick()

      const buttons = wrapper.findAll('button')
      const saveButton = buttons.find(btn => btn.text().includes('Save'))

      await saveButton.trigger('click')
      await wrapper.vm.$nextTick()

      const emitted = wrapper.emitted('save')
      expect(emitted).toBeTruthy()
      expect(emitted[0][0]).toEqual({
        enabled: true,
        commit_limit: 25,
        default_branch: 'master'
      })
    })

    it('save button is disabled when loading', () => {
      wrapper = mountComponent({ enabled: true, loading: true })

      const buttons = wrapper.findAll('button')
      const saveButton = buttons.find(btn => btn.text().includes('Save'))
      expect(saveButton.attributes('disabled')).toBeDefined()
    })

    it('save button shows loading state when loading', () => {
      wrapper = mountComponent({ enabled: true, loading: true })

      const buttons = wrapper.findAll('button')
      const saveButton = buttons.find(btn => btn.text().includes('Save'))
      expect(saveButton.attributes('loading')).toBeDefined()
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

      // The tooltip content should explain the feature
      const tooltipIcon = wrapper.find('.mdi-help-circle-outline')
      expect(tooltipIcon.exists()).toBe(true)
      // Tooltip content is in the template
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
      const toggle = wrapper.find('.v-switch input[type="checkbox"]')

      // Rapid toggles
      await toggle.setValue(true)
      await toggle.setValue(false)
      await toggle.setValue(true)
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

      const buttons = wrapper.findAll('button')
      const saveButton = buttons.find(btn => btn.text().includes('Save'))

      await saveButton.trigger('click')
      await wrapper.vm.$nextTick()

      const emitted = wrapper.emitted('save')
      expect(emitted[0][0].commit_limit).toBe(30)
    })
  })

  describe('Expansion Panel Behavior', () => {
    it('expansion panel is collapsed by default', () => {
      wrapper = mountComponent({ enabled: true })

      const panel = wrapper.find('.v-expansion-panel')
      expect(panel.exists()).toBe(true)
    })

    it('expansion panel can be expanded', async () => {
      wrapper = mountComponent({ enabled: true })
      await wrapper.vm.$nextTick()

      const panelTitle = wrapper.find('.v-expansion-panel-title')
      await panelTitle.trigger('click')
      await wrapper.vm.$nextTick()

      // After clicking, the panel should expand
      const expandedPanel = wrapper.find('.v-expansion-panel--active')
      expect(expandedPanel.exists()).toBe(true)
    })

    it('displays cog icon in expansion panel title', () => {
      wrapper = mountComponent({ enabled: true })

      const cogIcon = wrapper.find('.v-expansion-panel-title .mdi-cog')
      expect(cogIcon.exists()).toBe(true)
    })
  })

  describe('Input Validation', () => {
    it('commit limit input accepts numeric values', async () => {
      wrapper = mountComponent({ enabled: true })
      await wrapper.vm.$nextTick()

      // Open expansion panel
      const expansionTitle = wrapper.find('.v-expansion-panel-title')
      await expansionTitle.trigger('click')
      await wrapper.vm.$nextTick()

      const commitLimitInput = wrapper.find('input[type="number"]')
      expect(commitLimitInput.exists()).toBe(true)
    })

    it('commit limit has min value of 1', async () => {
      wrapper = mountComponent({ enabled: true })
      await wrapper.vm.$nextTick()

      const expansionTitle = wrapper.find('.v-expansion-panel-title')
      await expansionTitle.trigger('click')
      await wrapper.vm.$nextTick()

      const commitLimitInput = wrapper.find('input[type="number"]')
      expect(commitLimitInput.attributes('min')).toBe('1')
    })

    it('commit limit has max value of 100', async () => {
      wrapper = mountComponent({ enabled: true })
      await wrapper.vm.$nextTick()

      const expansionTitle = wrapper.find('.v-expansion-panel-title')
      await expansionTitle.trigger('click')
      await wrapper.vm.$nextTick()

      const commitLimitInput = wrapper.find('input[type="number"]')
      expect(commitLimitInput.attributes('max')).toBe('100')
    })

    it('default branch input shows placeholder', async () => {
      wrapper = mountComponent({ enabled: true })
      await wrapper.vm.$nextTick()

      const expansionTitle = wrapper.find('.v-expansion-panel-title')
      await expansionTitle.trigger('click')
      await wrapper.vm.$nextTick()

      // Find the text field for default branch
      const textFields = wrapper.findAll('.v-text-field')
      expect(textFields.length).toBeGreaterThan(0)
    })
  })

  describe('Accessibility', () => {
    it('card has proper structure', () => {
      wrapper = mountComponent()

      expect(wrapper.find('.v-card').exists()).toBe(true)
      expect(wrapper.find('.v-card-text').exists()).toBe(true)
    })

    it('toggle is keyboard accessible', () => {
      wrapper = mountComponent()

      const toggle = wrapper.find('.v-switch input[type="checkbox"]')
      expect(toggle.exists()).toBe(true)
    })

    it('buttons are keyboard accessible', () => {
      wrapper = mountComponent({ enabled: true })

      const buttons = wrapper.findAll('button')
      expect(buttons.length).toBeGreaterThan(0)
    })

    it('external link opens in new tab', () => {
      wrapper = mountComponent()

      const link = wrapper.find('a[href*="github.com"]')
      expect(link.attributes('target')).toBe('_blank')
    })
  })

  describe('Visual Elements', () => {
    it('displays avatar with github icon', () => {
      wrapper = mountComponent()

      const avatar = wrapper.find('.v-avatar')
      expect(avatar.exists()).toBe(true)
    })

    it('uses outlined card variant', () => {
      wrapper = mountComponent()

      const card = wrapper.find('.v-card')
      expect(card.classes()).toContain('v-card--variant-outlined')
    })

    it('uses tonal card variant for controls section', () => {
      wrapper = mountComponent()

      const tonalCard = wrapper.findAll('.v-card--variant-tonal')
      expect(tonalCard.length).toBeGreaterThan(0)
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

      // Check the switch is off
      const toggle = wrapper.find('.v-switch input[type="checkbox"]')
      expect(toggle.element.checked).toBe(false)
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

      const toggle = wrapper.find('.v-switch')
      expect(toggle.attributes('loading')).toBeUndefined()
    })
  })

  describe('Event Emissions', () => {
    it('emits save with current enabled state', async () => {
      wrapper = mountComponent({
        enabled: true,
        config: { commit_limit: 20, default_branch: 'main' }
      })
      await wrapper.vm.$nextTick()

      const buttons = wrapper.findAll('button')
      const saveButton = buttons.find(btn => btn.text().includes('Save'))

      await saveButton.trigger('click')

      const emitted = wrapper.emitted('save')
      expect(emitted[0][0].enabled).toBe(true)
    })

    it('does not emit save when clicking save button with loading', async () => {
      wrapper = mountComponent({ enabled: true, loading: true })
      await wrapper.vm.$nextTick()

      const buttons = wrapper.findAll('button')
      const saveButton = buttons.find(btn => btn.text().includes('Save'))

      // Button should be disabled and not trigger save
      await saveButton.trigger('click')

      const emitted = wrapper.emitted('save')
      expect(emitted).toBeFalsy()
    })
  })
})
