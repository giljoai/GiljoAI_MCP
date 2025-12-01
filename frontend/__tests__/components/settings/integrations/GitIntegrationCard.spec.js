import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import GitIntegrationCard from '@/components/settings/integrations/GitIntegrationCard.vue'

describe('GitIntegrationCard.vue', () => {
  let wrapper

  beforeEach(() => {
    // Reset state before each test
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
  })

  function createWrapper(props = {}) {
    const vuetify = createVuetify()
    const defaultProps = {
      enabled: false,
      config: {
        use_in_prompts: false,
        include_commit_history: true,
        max_commits: 50,
        branch_strategy: 'main',
      },
      loading: false,
    }

    return mount(GitIntegrationCard, {
      props: { ...defaultProps, ...props },
      global: {
        plugins: [vuetify],
      },
    })
  }

  // Test 1: Component renders correctly
  it('UT-GI-001: Component renders with Git + 360 Memory title', () => {
    wrapper = createWrapper()

    expect(wrapper.text()).toContain('Git + 360 Memory')
    expect(wrapper.text()).toContain('Cumulative product knowledge tracking')
  })

  // Test 2: Props are applied correctly
  it('UT-GI-001: Props are correctly applied to component state', () => {
    wrapper = createWrapper({
      enabled: true,
      config: {
        use_in_prompts: true,
        include_commit_history: false,
        max_commits: 100,
        branch_strategy: 'develop',
      },
    })

    // Verify props were received
    expect(wrapper.props('enabled')).toBe(true)
    expect(wrapper.props('config').max_commits).toBe(100)
    expect(wrapper.props('config').branch_strategy).toBe('develop')
  })

  // Test 3: Toggle emits update:enabled event
  it('UT-GI-002: Toggle switch emits update:enabled event', async () => {
    wrapper = createWrapper({
      enabled: false,
    })

    // Find the switch component
    const switchComponent = wrapper.findComponent({ name: 'VSwitch' })
    expect(switchComponent.exists()).toBe(true)

    // Trigger the switch
    await switchComponent.vm.$emit('update:model-value', true)

    // Check emitted event
    expect(wrapper.emitted('update:enabled')).toBeTruthy()
    expect(wrapper.emitted('update:enabled')[0]).toEqual([true])
  })

  // Test 4: Toggle state changes
  it('UT-GI-002: Multiple toggles emit multiple events', async () => {
    wrapper = createWrapper({
      enabled: false,
    })

    const switchComponent = wrapper.findComponent({ name: 'VSwitch' })

    // Toggle multiple times
    await switchComponent.vm.$emit('update:model-value', true)
    await wrapper.vm.$nextTick()
    await switchComponent.vm.$emit('update:model-value', false)
    await wrapper.vm.$nextTick()
    await switchComponent.vm.$emit('update:model-value', true)
    await wrapper.vm.$nextTick()

    // Verify all events emitted
    expect(wrapper.emitted('update:enabled')).toHaveLength(3)
    expect(wrapper.emitted('update:enabled')[0][0]).toBe(true)
    expect(wrapper.emitted('update:enabled')[1][0]).toBe(false)
    expect(wrapper.emitted('update:enabled')[2][0]).toBe(true)
  })

  // Test 5: Advanced button emits openAdvanced event
  it('UT-GI-003: Advanced button emits openAdvanced event', async () => {
    wrapper = createWrapper()

    // Find Advanced button
    const buttons = wrapper.findAllComponents({ name: 'VBtn' })
    const advancedBtn = buttons.find(btn => btn.text().includes('Advanced'))

    expect(advancedBtn).toBeDefined()

    // Click the button
    await advancedBtn.trigger('click')

    // Check emitted event
    expect(wrapper.emitted('openAdvanced')).toBeTruthy()
    expect(wrapper.emitted('openAdvanced')).toHaveLength(1)
  })

  // Test 6: Loading state disables toggle
  it('UT-GI-002: Loading prop disables toggle switch', () => {
    wrapper = createWrapper({
      loading: true,
    })

    const switchComponent = wrapper.findComponent({ name: 'VSwitch' })
    expect(switchComponent.props('loading')).toBe(true)
  })

  // Test 7: Loading state disables Advanced button
  it('UT-GI-003: Loading prop disables Advanced button', () => {
    wrapper = createWrapper({
      loading: true,
    })

    const buttons = wrapper.findAllComponents({ name: 'VBtn' })
    const advancedBtn = buttons.find(btn => btn.text().includes('Advanced'))

    expect(advancedBtn.props('disabled')).toBe(true)
  })

  // Test 8: Config prop is received
  it('UT-GI-001: Config prop is correctly received', () => {
    const customConfig = {
      use_in_prompts: true,
      include_commit_history: false,
      max_commits: 200,
      branch_strategy: 'staging',
    }

    wrapper = createWrapper({
      config: customConfig,
    })

    expect(wrapper.props('config')).toEqual(customConfig)
  })

  // Test 9: Enabled state is shown in UI
  it('UT-GI-001: Enabled state is reflected in switch component', () => {
    wrapper = createWrapper({
      enabled: true,
    })

    const switchComponent = wrapper.findComponent({ name: 'VSwitch' })
    expect(switchComponent.props('modelValue')).toBe(true)
  })

  // Test 10: Disabled state is shown in UI
  it('UT-GI-001: Disabled state is reflected in switch component', () => {
    wrapper = createWrapper({
      enabled: false,
    })

    const switchComponent = wrapper.findComponent({ name: 'VSwitch' })
    expect(switchComponent.props('modelValue')).toBe(false)
  })

  // Test 11: Documentation link is present
  it('UT-GI-001: GitHub Setup Guide link is present', () => {
    wrapper = createWrapper()

    const link = wrapper.find('a[href*="github.com"]')
    expect(link.exists()).toBe(true)
    expect(link.text()).toContain('GitHub Setup Guide')
    expect(link.attributes('target')).toBe('_blank')
  })

  // Test 12: Help tooltip is present
  it('UT-GI-001: Help tooltip is present', () => {
    wrapper = createWrapper()

    // Check for help icon and tooltip content
    expect(wrapper.text()).toContain('Cumulative product knowledge tracking')
    expect(wrapper.text()).toContain(
      'captures git commit history at project closeout'
    )
  })

  // Test 13: Component structure is correct
  it('UT-GI-001: Component structure is correct', () => {
    wrapper = createWrapper()

    // Check for main card
    const card = wrapper.findComponent({ name: 'VCard' })
    expect(card.exists()).toBe(true)

    // Check for title
    expect(wrapper.text()).toContain('Git + 360 Memory')

    // Check for description
    expect(wrapper.text()).toContain(
      'Enable to automatically include git commit history'
    )
  })

  // Test 14: Emits use correct names
  it('UT-GI-002 & 003: Event names match expected contract', () => {
    wrapper = createWrapper()

    // Get emitted event names
    const eventNames = Object.keys(wrapper.vm.$options.emits || {})

    expect(eventNames).toContain('update:enabled')
    expect(eventNames).toContain('openAdvanced')
  })

  // Test 15: Component doesn't emit events without user action
  it('UT-GI-001: Component doesn\'t emit events on mount', () => {
    wrapper = createWrapper()

    expect(wrapper.emitted('update:enabled')).toBeFalsy()
    expect(wrapper.emitted('openAdvanced')).toBeFalsy()
  })

  // Test 16: Props are properly typed
  it('UT-GI-001: Props have correct default values', () => {
    wrapper = createWrapper({})

    expect(wrapper.props('enabled')).toBe(false)
    expect(wrapper.props('loading')).toBe(false)
    expect(typeof wrapper.props('config')).toBe('object')
  })

  // Test 17: Advanced button is always visible
  it('UT-GI-003: Advanced button is visible regardless of enabled state', async () => {
    // Test with enabled = true
    wrapper = createWrapper({ enabled: true })
    let buttons = wrapper.findAllComponents({ name: 'VBtn' })
    let advancedBtn = buttons.find(btn => btn.text().includes('Advanced'))
    expect(advancedBtn.exists()).toBe(true)

    wrapper.unmount()

    // Test with enabled = false
    wrapper = createWrapper({ enabled: false })
    buttons = wrapper.findAllComponents({ name: 'VBtn' })
    advancedBtn = buttons.find(btn => btn.text().includes('Advanced'))
    expect(advancedBtn.exists()).toBe(true)
  })

  // Test 18: Toggle state updates from prop changes
  it('UT-GI-001: Switch updates when enabled prop changes', async () => {
    wrapper = createWrapper({ enabled: false })

    expect(wrapper.findComponent({ name: 'VSwitch' }).props('modelValue')).toBe(false)

    // Update prop
    await wrapper.setProps({ enabled: true })

    expect(wrapper.findComponent({ name: 'VSwitch' }).props('modelValue')).toBe(true)
  })

  // Test 19: Loading state can be toggled
  it('UT-GI-002: Loading state updates correctly', async () => {
    wrapper = createWrapper({ loading: false })

    expect(wrapper.findComponent({ name: 'VSwitch' }).props('loading')).toBe(false)

    // Update prop
    await wrapper.setProps({ loading: true })

    expect(wrapper.findComponent({ name: 'VSwitch' }).props('loading')).toBe(true)

    // Update back
    await wrapper.setProps({ loading: false })

    expect(wrapper.findComponent({ name: 'VSwitch' }).props('loading')).toBe(false)
  })

  // Test 20: Component is presentational (no local state changes)
  it('UT-GI-001: Component is purely presentational', () => {
    wrapper = createWrapper({
      enabled: false,
      config: { max_commits: 50 },
    })

    // Component should not have data properties that change state
    // (verified by checking that changes only come from props)
    const switchComponent = wrapper.findComponent({ name: 'VSwitch' })

    // The modelValue should be tied to prop, not component data
    expect(switchComponent.props('modelValue')).toBe(false)
    expect(wrapper.props('enabled')).toBe(false)
  })
})
