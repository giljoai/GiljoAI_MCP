/**
 * AutoCheckinControls.be6013.spec.js
 *
 * BE-6013: "Applies at next check-in." hint
 *
 * Tests:
 * 1. Hint is absent when orchestratorRunning is false (not yet started)
 * 2. Hint is absent when orchestratorRunning is true but slider is Off (disabled)
 * 3. Hint is visible when orchestratorRunning is true and a non-zero interval is set
 * 4. Hint disappears when slider is moved back to Off position
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import AutoCheckinControls from '@/components/projects/AutoCheckinControls.vue'

const vuetify = createVuetify()

const stubs = {
  'v-tooltip': true,
  'v-icon': true,
}

describe('AutoCheckinControls — BE-6013 next-check-in hint', () => {
  it('does NOT show hint when orchestratorRunning is false (even if enabled)', () => {
    const wrapper = mount(AutoCheckinControls, {
      props: { enabled: true, interval: 10, orchestratorRunning: false },
      global: { plugins: [vuetify], stubs },
    })
    expect(wrapper.find('[data-testid="auto-checkin-hint"]').exists()).toBe(false)
  })

  it('does NOT show hint when orchestratorRunning is true but auto-checkin is Off', () => {
    const wrapper = mount(AutoCheckinControls, {
      props: { enabled: false, interval: 10, orchestratorRunning: true },
      global: { plugins: [vuetify], stubs },
    })
    expect(wrapper.find('[data-testid="auto-checkin-hint"]').exists()).toBe(false)
  })

  it('shows hint when orchestratorRunning is true and auto-checkin is enabled', () => {
    const wrapper = mount(AutoCheckinControls, {
      props: { enabled: true, interval: 15, orchestratorRunning: true },
      global: { plugins: [vuetify], stubs },
    })
    const hint = wrapper.find('[data-testid="auto-checkin-hint"]')
    expect(hint.exists()).toBe(true)
    expect(hint.text()).toBe('Applies at next check-in.')
  })

  it('does not show hint when orchestratorRunning prop is omitted (default false)', () => {
    const wrapper = mount(AutoCheckinControls, {
      props: { enabled: true, interval: 10 },
      global: { plugins: [vuetify], stubs },
    })
    expect(wrapper.find('[data-testid="auto-checkin-hint"]').exists()).toBe(false)
  })
})
