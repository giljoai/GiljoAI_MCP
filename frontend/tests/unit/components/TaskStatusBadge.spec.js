import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'

import TaskStatusBadge from '@/components/TaskStatusBadge.vue'

// The six canonical task statuses (backend `TaskUpdate` schema). Hex
// values mirror the Luminous Pastels palette in `design-tokens.scss`
// and are reproduced here only for assertion purposes — production
// code never embeds them outside the component itself.
const STATUSES = [
  { value: 'pending', label: 'Pending', expectedHex: '#9e9e9e' },
  { value: 'in_progress', label: 'In Progress', expectedHex: '#6db3e4' },
  { value: 'completed', label: 'Completed', expectedHex: '#5ec48e' },
  { value: 'blocked', label: 'Blocked', expectedHex: '#e07872' },
  { value: 'cancelled', label: 'Cancelled', expectedHex: '#8895a8' },
  { value: 'converted', label: 'Converted', expectedHex: '#ac80cc' },
]

function mountBadge(status) {
  const vuetify = createVuetify()
  return mount(TaskStatusBadge, {
    props: { status },
    global: { plugins: [vuetify] },
  })
}

describe('TaskStatusBadge', () => {
  it.each(STATUSES)('renders the human label for $value', ({ value, label }) => {
    const wrapper = mountBadge(value)
    expect(wrapper.text()).toBe(label)
  })

  it.each(STATUSES)(
    'applies tinted background + full-brightness color for $value',
    ({ value, expectedHex }) => {
      const wrapper = mountBadge(value)
      const el = wrapper.find('.task-status-badge').element
      // Inline style is set as object → DOM serializes color/background.
      expect(el.style.background.toLowerCase()).toContain(
        `rgba(${parseInt(expectedHex.slice(1, 3), 16)}, ${parseInt(
          expectedHex.slice(3, 5),
          16,
        )}, ${parseInt(expectedHex.slice(5, 7), 16)}, 0.15)`,
      )
      expect(el.style.color.toLowerCase()).toBe(
        `rgb(${parseInt(expectedHex.slice(1, 3), 16)}, ${parseInt(
          expectedHex.slice(3, 5),
          16,
        )}, ${parseInt(expectedHex.slice(5, 7), 16)})`,
      )
    },
  )

  it('uses 8px border-radius (square-cornered pill)', () => {
    const wrapper = mountBadge('pending')
    const el = wrapper.find('.task-status-badge').element
    expect(el.style.borderRadius).toBe('8px')
  })

  it('applies the smooth-border class (no raw CSS border on rounded element)', () => {
    const wrapper = mountBadge('pending')
    expect(wrapper.find('.task-status-badge').classes()).toContain('smooth-border')
  })

  it('falls back to neutral label for an unknown status', () => {
    const wrapper = mountBadge('whatever_orphan_value')
    expect(wrapper.text()).toBe('Unknown')
  })

  it('exposes an aria-label for screen readers', () => {
    const wrapper = mountBadge('in_progress')
    expect(
      wrapper.find('.task-status-badge').attributes('aria-label'),
    ).toBe('Task status: In Progress')
  })
})
