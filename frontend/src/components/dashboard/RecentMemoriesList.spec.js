/**
 * RecentMemoriesList.spec.js — BE-6078 PART 2.
 *
 * Edition Scope: CE.
 *
 * The dashboard 360-memory list rendered TWO visually-distinct badges
 * (closeout / completion) for what is the same project-finish milestone, split
 * only by write path. BE-6078 collapses the finish family
 * (project_closeout + project_completion + handover_closeout) into ONE
 * "Completed" badge with one shared color, while keeping session_handover and
 * the structural types (decision/architecture/...) distinct. UI tolerance — no
 * migration; legacy rows just render "Completed".
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import RecentMemoriesList from '@/components/dashboard/RecentMemoriesList.vue'

function makeMemory(entry_type, overrides = {}) {
  return {
    project_name: `proj-${entry_type}`,
    product_name: 'Demo',
    summary: 'did the thing',
    timestamp: '2026-06-13T00:00:00Z',
    entry_type,
    ...overrides,
  }
}

function mountList(memories) {
  return mount(RecentMemoriesList, { props: { memories } })
}

function badgeColor(el) {
  // typeStyle binds an inline `color: ...` — the badge's foreground hue is the
  // single color identity we collapse the finish family onto.
  return el.element.style.color
}

describe('RecentMemoriesList.vue (BE-6078 finish-family badge collapse)', () => {
  const FINISH = ['project_closeout', 'project_completion', 'handover_closeout']

  it.each(FINISH)('renders a single "Completed" badge for finish-family type %s', (entry_type) => {
    const wrapper = mountList([makeMemory(entry_type)])
    const badge = wrapper.find('.memory-type')
    expect(badge.text()).toBe('Completed')
  })

  it('renders ONE shared color for all three finish-family types', () => {
    const wrapper = mountList(FINISH.map((t) => makeMemory(t)))
    const badges = wrapper.findAll('.memory-type')
    expect(badges).toHaveLength(3)
    const colors = badges.map(badgeColor)
    // All three collapse onto the same color identity.
    expect(new Set(colors).size).toBe(1)
    expect(colors[0]).toBeTruthy()
  })

  it('keeps session_handover distinct (label + color) from the finish family', () => {
    const wrapper = mountList([makeMemory('project_closeout'), makeMemory('session_handover')])
    const badges = wrapper.findAll('.memory-type')
    expect(badges[0].text()).toBe('Completed')
    expect(badges[1].text()).toBe('handover')
    expect(badgeColor(badges[0])).not.toBe(badgeColor(badges[1]))
  })

  it('keeps structural types (decision) distinct — not collapsed to Completed', () => {
    const wrapper = mountList([makeMemory('decision')])
    const badge = wrapper.find('.memory-type')
    expect(badge.text()).toBe('decision')
    expect(badge.text()).not.toBe('Completed')
  })

  it('renders nothing when there are no memories', () => {
    const wrapper = mountList([])
    expect(wrapper.find('.memory-type').exists()).toBe(false)
    expect(wrapper.text()).toContain('No recent memories')
  })
})
