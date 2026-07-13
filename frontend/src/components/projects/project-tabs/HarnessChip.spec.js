/**
 * HarnessChip.spec.js — TSK-9038
 *
 * Smoke tests: detected concrete harness / generic / absent.
 * Edition scope: Both
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import HarnessChip from './HarnessChip.vue'

describe('HarnessChip', () => {
  it('renders "detected: Claude Code" for a concrete recognized harness', () => {
    const wrapper = mount(HarnessChip, { props: { harness: 'claude-code' } })
    expect(wrapper.find('[data-testid="harness-chip"]').exists()).toBe(true)
    expect(wrapper.text()).toBe('detected: Claude Code')
  })

  it('renders nothing for the generic fail-safe token', () => {
    const wrapper = mount(HarnessChip, { props: { harness: 'generic' } })
    expect(wrapper.find('[data-testid="harness-chip"]').exists()).toBe(false)
  })

  it('renders nothing when no harness has been detected (null)', () => {
    const wrapper = mount(HarnessChip, { props: { harness: null } })
    expect(wrapper.find('[data-testid="harness-chip"]').exists()).toBe(false)
  })
})
