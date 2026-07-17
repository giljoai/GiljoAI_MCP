/**
 * Unit tests for TutorialRail (FE-9200) — per CODE_GUIDANCE §7: 6 stops,
 * click-to-jump, done/active dot states follow the state machine.
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import TutorialRail from '@/components/tutorial/TutorialRail.vue'

const vuetify = createVuetify({ components, directives })

function mountRail(props = {}) {
  return mount(TutorialRail, {
    props: { activeStop: 1, ...props },
    global: { plugins: [vuetify] },
  })
}

describe('TutorialRail', () => {
  it('renders exactly 6 stops with the approved labels', () => {
    const wrapper = mountRail()
    const labels = wrapper.findAll('.rail-label')

    expect(labels).toHaveLength(6)
    expect(labels.map((l) => l.text())).toEqual([
      'How it works',
      'Product & crew',
      'Missions',
      '360 Memory',
      'The destination',
      'Get started',
    ])
  })

  it('marks the active stop and the ones before it as done', () => {
    const wrapper = mountRail({ activeStop: 3 })

    expect(wrapper.find('[data-testid="tutorial-rail-stop-3"]').classes()).toContain(
      'rail-stop--active',
    )
    expect(wrapper.find('[data-testid="tutorial-rail-stop-1"]').classes()).toContain(
      'rail-stop--done',
    )
    expect(wrapper.find('[data-testid="tutorial-rail-stop-2"]').classes()).toContain(
      'rail-stop--done',
    )
    const pending = wrapper.find('[data-testid="tutorial-rail-stop-5"]')
    expect(pending.classes()).not.toContain('rail-stop--active')
    expect(pending.classes()).not.toContain('rail-stop--done')
  })

  it('sets aria-current on the active stop only', () => {
    const wrapper = mountRail({ activeStop: 2 })

    expect(
      wrapper.find('[data-testid="tutorial-rail-stop-2"]').attributes('aria-current'),
    ).toBe('step')
    expect(
      wrapper.find('[data-testid="tutorial-rail-stop-1"]').attributes('aria-current'),
    ).toBeUndefined()
  })

  it('click-to-jump emits go with the 1-based stop number', async () => {
    const wrapper = mountRail({ activeStop: 1 })

    await wrapper.find('[data-testid="tutorial-rail-stop-4"]').trigger('click')

    expect(wrapper.emitted('go')).toBeTruthy()
    expect(wrapper.emitted('go')[0]).toEqual([4])
  })

  it('keyboard enter also emits go', async () => {
    const wrapper = mountRail({ activeStop: 1 })

    await wrapper.find('[data-testid="tutorial-rail-stop-6"]').trigger('keydown.enter')

    expect(wrapper.emitted('go')[0]).toEqual([6])
  })
})
