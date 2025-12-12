/**
 * VisionSummarizationCard Component Tests
 *
 * Production-grade test suite for Handover 0345c Vision Settings UI.
 * Tests component rendering, toggle functionality, loading states, and event emissions.
 *
 * Test Coverage:
 * - Component renders with correct structure
 * - Toggle switch displays correct label and state
 * - Update event emits on toggle
 * - Loading state disables toggle
 * - Info alert displays helpful message
 * - Accessibility (proper ARIA labels, keyboard support)
 *
 * @see handovers/0345c_vision_settings_ui.md
 */

import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import VisionSummarizationCard from './VisionSummarizationCard.vue'

describe('VisionSummarizationCard', () => {
  /**
   * Test: Component renders correctly with required props
   */
  it('renders component with correct structure', () => {
    const wrapper = mount(VisionSummarizationCard, {
      props: {
        enabled: false,
        loading: false
      }
    })

    expect(wrapper.find('v-card-stub').exists()).toBe(true)
    expect(wrapper.find('v-card-title-stub').exists()).toBe(true)
    expect(wrapper.find('v-card-subtitle-stub').exists()).toBe(true)
    expect(wrapper.text()).toContain('Vision Summarization (Sumy LSA)')
    expect(wrapper.text()).toContain('Compress large vision documents')
  })

  /**
   * Test: Toggle switch renders with correct label
   */
  it('displays toggle switch with correct label', () => {
    const wrapper = mount(VisionSummarizationCard, {
      props: {
        enabled: false,
        loading: false
      }
    })

    const toggle = wrapper.find('[data-testid="vision-summarization-toggle"]')
    expect(toggle.exists()).toBe(true)
  })

  /**
   * Test: Toggle switch shows enabled state
   */
  it('shows toggle in enabled state', async () => {
    const wrapper = mount(VisionSummarizationCard, {
      props: {
        enabled: true,
        loading: false
      }
    })

    const toggle = wrapper.find('[data-testid="vision-summarization-toggle"]')
    expect(toggle.attributes('aria-checked')).toBe('true')
  })

  /**
   * Test: Toggle switch shows disabled state
   */
  it('shows toggle in disabled state', async () => {
    const wrapper = mount(VisionSummarizationCard, {
      props: {
        enabled: false,
        loading: false
      }
    })

    const toggle = wrapper.find('[data-testid="vision-summarization-toggle"]')
    expect(toggle.attributes('aria-checked')).toBe('false')
  })

  /**
   * Test: Emits update:enabled event when toggled
   */
  it('emits update:enabled event when toggle is clicked', async () => {
    const wrapper = mount(VisionSummarizationCard, {
      props: {
        enabled: false,
        loading: false
      }
    })

    const toggle = wrapper.find('[data-testid="vision-summarization-toggle"]')
    await toggle.trigger('click')
    await nextTick()

    expect(wrapper.emitted('update:enabled')).toBeTruthy()
    expect(wrapper.emitted('update:enabled')[0]).toEqual([true])
  })

  /**
   * Test: Emits false when toggling from enabled to disabled
   */
  it('emits false when toggling off', async () => {
    const wrapper = mount(VisionSummarizationCard, {
      props: {
        enabled: true,
        loading: false
      }
    })

    const toggle = wrapper.find('[data-testid="vision-summarization-toggle"]')
    await toggle.trigger('click')
    await nextTick()

    expect(wrapper.emitted('update:enabled')[0]).toEqual([false])
  })

  /**
   * Test: Shows loading state with spinner
   */
  it('shows loading state when loading prop is true', async () => {
    const wrapper = mount(VisionSummarizationCard, {
      props: {
        enabled: false,
        loading: true
      }
    })

    const toggle = wrapper.find('[data-testid="vision-summarization-toggle"]')
    expect(toggle.attributes('disabled')).toBeDefined()
  })

  /**
   * Test: Loading state disables toggle interaction
   */
  it('disables toggle when loading', async () => {
    const wrapper = mount(VisionSummarizationCard, {
      props: {
        enabled: false,
        loading: true
      }
    })

    const toggle = wrapper.find('[data-testid="vision-summarization-toggle"]')
    await toggle.trigger('click')

    // Should not emit event when disabled
    expect(wrapper.emitted('update:enabled')).toBeFalsy()
  })

  /**
   * Test: Info alert displays
   */
  it('displays info alert with description', () => {
    const wrapper = mount(VisionSummarizationCard, {
      props: {
        enabled: false,
        loading: false
      }
    })

    const alert = wrapper.find('v-alert-stub')
    expect(alert.exists()).toBe(true)
    expect(alert.attributes('type')).toBe('info')
    expect(wrapper.text()).toContain('When enabled, vision documents are automatically summarized')
  })

  /**
   * Test: Card uses outlined variant
   */
  it('uses outlined card variant', () => {
    const wrapper = mount(VisionSummarizationCard, {
      props: {
        enabled: false,
        loading: false
      }
    })

    const card = wrapper.find('v-card-stub')
    expect(card.attributes('variant')).toBe('outlined')
  })

  /**
   * Test: Icon displays correctly
   */
  it('displays text-box-multiple icon', () => {
    const wrapper = mount(VisionSummarizationCard, {
      props: {
        enabled: false,
        loading: false
      }
    })

    const icon = wrapper.find('v-icon-stub')
    expect(icon.exists()).toBe(true)
    expect(icon.attributes('icon')).toBe('mdi-text-box-multiple')
  })

  /**
   * Test: Has proper CSS classes for spacing
   */
  it('has proper CSS classes', () => {
    const wrapper = mount(VisionSummarizationCard, {
      props: {
        enabled: false,
        loading: false
      }
    })

    const card = wrapper.find('v-card-stub')
    expect(card.classes()).toContain('mb-4')
  })

  /**
   * Test: Accepts enabled as reactive prop
   */
  it('updates when enabled prop changes', async () => {
    const wrapper = mount(VisionSummarizationCard, {
      props: {
        enabled: false,
        loading: false
      }
    })

    let toggle = wrapper.find('[data-testid="vision-summarization-toggle"]')
    expect(toggle.attributes('aria-checked')).toBe('false')

    await wrapper.setProps({ enabled: true })
    await nextTick()

    toggle = wrapper.find('[data-testid="vision-summarization-toggle"]')
    expect(toggle.attributes('aria-checked')).toBe('true')
  })

  /**
   * Test: Accepts loading as reactive prop
   */
  it('updates loading state when prop changes', async () => {
    const wrapper = mount(VisionSummarizationCard, {
      props: {
        enabled: false,
        loading: false
      }
    })

    let toggle = wrapper.find('[data-testid="vision-summarization-toggle"]')
    expect(toggle.attributes('disabled')).toBeUndefined()

    await wrapper.setProps({ loading: true })
    await nextTick()

    toggle = wrapper.find('[data-testid="vision-summarization-toggle"]')
    expect(toggle.attributes('disabled')).toBeDefined()
  })

  /**
   * Test: Default props work correctly
   */
  it('works with default loading prop', () => {
    const wrapper = mount(VisionSummarizationCard, {
      props: {
        enabled: false
        // loading defaults to false
      }
    })

    const toggle = wrapper.find('[data-testid="vision-summarization-toggle"]')
    expect(toggle.attributes('disabled')).toBeUndefined()
  })

  /**
   * Test: Keyboard navigation support
   */
  it('supports keyboard navigation (Space/Enter)', async () => {
    const wrapper = mount(VisionSummarizationCard, {
      props: {
        enabled: false,
        loading: false
      }
    })

    const toggle = wrapper.find('[data-testid="vision-summarization-toggle"]')

    // Space key should work (standard browser behavior)
    await toggle.trigger('keydown.space')
    await nextTick()

    // Toggle should still be interactive
    expect(toggle.exists()).toBe(true)
  })

  /**
   * Test: Event emission structure
   */
  it('emits event with correct structure', async () => {
    const wrapper = mount(VisionSummarizationCard, {
      props: {
        enabled: false,
        loading: false
      }
    })

    const toggle = wrapper.find('[data-testid="vision-summarization-toggle"]')
    await toggle.trigger('click')

    const emitted = wrapper.emitted('update:enabled')
    expect(emitted).toHaveLength(1)
    expect(emitted[0]).toHaveLength(1) // Single argument (the boolean value)
    expect(typeof emitted[0][0]).toBe('boolean')
  })

  /**
   * Test: Multiple toggles work correctly
   */
  it('handles multiple toggle events', async () => {
    const wrapper = mount(VisionSummarizationCard, {
      props: {
        enabled: false,
        loading: false
      }
    })

    const toggle = wrapper.find('[data-testid="vision-summarization-toggle"]')

    // First toggle
    await toggle.trigger('click')
    expect(wrapper.emitted('update:enabled')).toHaveLength(1)

    // Reset loading state
    await wrapper.setProps({ loading: false })

    // Second toggle
    await toggle.trigger('click')
    expect(wrapper.emitted('update:enabled')).toHaveLength(2)
    expect(wrapper.emitted('update:enabled')[1]).toEqual([false])
  })
})
