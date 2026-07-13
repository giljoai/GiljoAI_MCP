/**
 * RoadmapCard.spec.js — FE-6165a
 *
 * Regression for the sequential-run checkbox-stick fix + the Activate fade:
 *  - the `:selected` binding renders the checkbox ticked (the bug was that the
 *    selection never reflected because the Map was keyed by the roadmap_item PK
 *    while this binding reads project_id — this pins the card side of that fix);
 *  - toggling emits `toggle-select` with the full item (so the parent keys it by
 *    project_id);
 *  - while an election is active the per-card Activate button is faded + disabled.
 *
 * Edition scope: CE.
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'

import RoadmapCard from './RoadmapCard.vue'

const vBtnStub = {
  template: '<button class="v-btn" :disabled="disabled" v-bind="$attrs"><slot /></button>',
  props: ['disabled'],
}
const vCheckboxStub = {
  template: '<input type="checkbox" :checked="modelValue" v-bind="$attrs" @click="$emit(\'update:model-value\', !modelValue)" />',
  props: ['modelValue'],
}

const stubs = {
  'v-btn': vBtnStub,
  'v-checkbox-btn': vCheckboxStub,
  'v-icon': { template: '<i class="v-icon"><slot /></i>' },
  'v-chip': { template: '<span class="v-chip"><slot /></span>' },
  'v-tooltip': { template: '<div class="v-tooltip"><slot name="activator" :props="{}" /><slot /></div>' },
  'v-menu': { template: '<div class="v-menu"><slot name="activator" :props="{}" /><slot /></div>' },
  'v-list': { template: '<div class="v-list"><slot /></div>' },
  'v-list-item': { template: '<div class="v-list-item" @click="$emit(\'click\')"><slot /></div>', props: ['title'] },
  'v-spacer': { template: '<span />' },
}

const inactiveProject = {
  item_type: 'project',
  status: 'inactive',
  title: 'Fix login',
  taxonomy_alias: 'BE-0001',
  project_id: 'proj-1',
  id: 'rm-item-pk',
}

function mountCard(props = {}) {
  return mount(RoadmapCard, {
    props: { item: inactiveProject, rank: 1, ...props },
    global: { stubs },
  })
}

const checkbox = (w) => w.find('[data-testid^="roadmap-select-checkbox"]')
const activateBtn = (w) => w.find('.rm-primary-btn')

// FE-6176: the selection checkbox moved out of the rank rail into the action
// rail and now renders ONLY in link mode (it replaces the Activate button).
// These tests therefore mount with linkMode: true.
describe('RoadmapCard — selection binding (FE-6165a / FE-6176)', () => {
  it('renders no selection checkbox outside link mode', () => {
    const wrapper = mountCard({ selected: false })
    expect(checkbox(wrapper).exists()).toBe(false)
  })

  it('renders the checkbox UNticked when not selected (link mode)', () => {
    const wrapper = mountCard({ selected: false, linkMode: true })
    expect(checkbox(wrapper).exists()).toBe(true)
    expect(checkbox(wrapper).element.checked).toBe(false)
  })

  it('renders the checkbox TICKED when selected (the stick fix, card side)', () => {
    const wrapper = mountCard({ selected: true, linkMode: true })
    expect(checkbox(wrapper).element.checked).toBe(true)
  })

  it('force-ticks the checkbox for an in-chain project (link mode)', () => {
    const wrapper = mountCard({ selected: false, inChain: true, linkMode: true })
    expect(checkbox(wrapper).element.checked).toBe(true)
  })

  it('emits toggle-select with the full item (carrying project_id) on click', async () => {
    const wrapper = mountCard({ selected: false, linkMode: true })
    await checkbox(wrapper).trigger('click')
    const ev = wrapper.emitted('toggle-select')
    expect(ev).toBeTruthy()
    expect(ev[0][0]).toMatchObject({ project_id: 'proj-1' })
  })

  it('replaces the Activate button with the checkbox in link mode', () => {
    const wrapper = mountCard({ linkMode: true })
    expect(checkbox(wrapper).exists()).toBe(true)
    expect(activateBtn(wrapper).exists()).toBe(false)
  })

  // FE-6180: /roadmap does NO chain management — an in-chain card greys its tickbox
  // and clicking it navigates to /projects (emits open-chain) instead of editing.
  it('disables the tickbox + emits open-chain (not toggle-select) when in a chain', async () => {
    const wrapper = mountCard({ inChain: true, linkMode: true })
    expect(checkbox(wrapper).attributes('disabled')).toBeDefined()
    await wrapper.find('.rm-link-wrap').trigger('click')
    expect(wrapper.emitted('open-chain')).toBeTruthy()
    expect(wrapper.emitted('open-chain')[0][0]).toMatchObject({ project_id: 'proj-1' })
    expect(wrapper.emitted('toggle-select')).toBeFalsy()
  })
})

describe('RoadmapCard — Activate fade on election (FE-6165a)', () => {
  it('Activate is enabled + unfaded when no election is active', () => {
    const wrapper = mountCard({ electionActive: false })
    const btn = activateBtn(wrapper)
    expect(btn.exists()).toBe(true)
    expect(btn.attributes('disabled')).toBeUndefined()
    expect(btn.classes()).not.toContain('rm-primary-btn--election-faded')
  })

  it('fades + disables Activate while an election is active', () => {
    const wrapper = mountCard({ electionActive: true })
    const btn = activateBtn(wrapper)
    expect(btn.attributes('disabled')).toBeDefined()
    expect(btn.classes()).toContain('rm-primary-btn--election-faded')
  })
})
