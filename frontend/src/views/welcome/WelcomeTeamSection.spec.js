/**
 * WelcomeTeamSection.spec.js — FE-6006 unit 3a
 *
 * Tests team section rendering: orchestrator card, template cards, empty slots.
 * Edition scope: CE
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import WelcomeTeamSection from './WelcomeTeamSection.vue'

const globalStubs = {
  'v-icon': { template: '<i class="v-icon"><slot /></i>' },
  'v-tooltip': { template: '<div><slot name="activator" :props="{}" /><slot /></div>' },
  'router-link': { template: '<a><slot /></a>' },
}

describe('WelcomeTeamSection', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  const sampleTemplates = [
    { id: 'tmpl-1', name: 'implementer', description: 'Writes code', badge: 'IM', color: '#6db3e4' },
    { id: 'tmpl-2', name: 'tester', description: 'Tests code', badge: 'TS', color: '#a87cce' },
  ]

  function mountTeam(props = {}) {
    return mount(WelcomeTeamSection, {
      props: {
        activeTemplates: sampleTemplates,
        emptySlots: 2,
        totalSlots: 16,
        hasStaleAgents: false,
        ...props,
      },
      global: { stubs: globalStubs },
    })
  }

  it('renders the orchestrator card', () => {
    const wrapper = mountTeam()
    expect(wrapper.text()).toContain('orchestrator')
  })

  it('renders one card per active template', () => {
    const wrapper = mountTeam()
    // orchestrator + 2 templates
    const cards = wrapper.findAll('.team-card:not(.empty-slot)')
    expect(cards).toHaveLength(3)
  })

  it('renders empty slots', () => {
    const wrapper = mountTeam({ emptySlots: 3 })
    expect(wrapper.findAll('.team-card.empty-slot')).toHaveLength(3)
  })

  it('shows stale-agents warning when hasStaleAgents is true', () => {
    const wrapper = mountTeam({ hasStaleAgents: true })
    expect(wrapper.find('.stale-agents-warning').exists()).toBe(true)
  })

  it('hides stale-agents warning when hasStaleAgents is false', () => {
    const wrapper = mountTeam({ hasStaleAgents: false })
    expect(wrapper.find('.stale-agents-warning').exists()).toBe(false)
  })

  it('shows slot count as "activeTemplates+1 / totalSlots slots"', () => {
    const wrapper = mountTeam()
    // 2 templates + orchestrator = 3; totalSlots = 16
    expect(wrapper.find('.team-slots').text()).toContain('3')
    expect(wrapper.find('.team-slots').text()).toContain('16')
  })
})
