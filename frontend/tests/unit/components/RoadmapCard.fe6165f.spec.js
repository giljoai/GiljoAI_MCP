/**
 * RoadmapCard.vue — FE-6165f (locked "In chain" checkbox merge)
 *
 * Verifies the inChain prop behavior on top of the existing election-fade
 * behavior (FE-6165a), WITHOUT modifying the existing RoadmapCard.spec.js.
 *
 * Edition Scope: CE
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import RoadmapCard from '@/components/RoadmapCard.vue'

// Reuse the same minimal stubs as the existing RoadmapCard.spec.js.
const stubs = {
  'v-btn': {
    template: '<button class="v-btn" v-bind="$attrs" @click="$emit(\'click\')"><slot /></button>',
  },
  'v-icon': { template: '<i class="v-icon"><slot /></i>' },
  'v-tooltip': {
    props: ['text'],
    template: '<div class="v-tooltip" :data-text="text"><slot name="activator" :props="{}" /></div>',
  },
  'v-checkbox-btn': {
    inheritAttrs: false,
    props: ['modelValue', 'disabled'],
    template: '<input type="checkbox" :checked="modelValue" :disabled="disabled" class="v-checkbox-btn" v-bind="$attrs" />',
  },
}

const PROJECT_ITEM = {
  id: 'rmi-1',
  item_type: 'project',
  project_id: 'p-1',
  task_id: null,
  title: 'Core database schema',
  taxonomy_alias: 'BE-0001',
  status: 'inactive',
  priority: 0,
  risk: 'low',
  complexity: 'heavy',
}

function mountCard(extraProps = {}) {
  return mount(RoadmapCard, {
    props: { item: PROJECT_ITEM, rank: 1, ...extraProps },
    global: { stubs },
  })
}

describe('RoadmapCard.vue — FE-6165f inChain prop', () => {
  it('renders the checkbox ticked AND disabled when inChain=true (FE-6180: disabled = inChain membership, back-out via kebab)', () => {
    // FE-6180: disabled is driven by inChain membership, not lockedInChain.
    // Any in-chain project is force-ticked + disabled. Back-out via kebab (Deactivate Chain).
    // linkMode=true is required for the checkbox to render (it replaces the Activate button).
    const w = mountCard({ linkMode: true, inChain: true, lockedInChain: true })
    const cb = w.find('[data-testid="roadmap-select-checkbox-rmi-1"]')
    expect(cb.exists()).toBe(true)
    expect(cb.element.checked).toBe(true)
    expect(cb.element.disabled).toBe(true)
  })

  it('renders the checkbox ticked AND disabled when inChain=true and lockedInChain=false (FE-6180: in-chain => force-ticked + disabled, back-out via kebab)', () => {
    // FE-6180: there is no "Editing tier" exception. inChain alone drives disable.
    // The "unlocked → enabled so user can untick" premise no longer exists.
    const w = mountCard({ linkMode: true, inChain: true, lockedInChain: false })
    const cb = w.find('[data-testid="roadmap-select-checkbox-rmi-1"]')
    expect(cb.element.checked).toBe(true)
    expect(cb.element.disabled).toBe(true)
  })

  it('renders the "In chain" pill when inChain=true', () => {
    const w = mountCard({ inChain: true })
    const pill = w.find('[data-testid="roadmap-in-chain-pill"]')
    expect(pill.exists()).toBe(true)
    expect(pill.text()).toBe('In chain')
  })

  it('does NOT render the pill when inChain=false (default)', () => {
    const w = mountCard({ inChain: false })
    expect(w.find('[data-testid="roadmap-in-chain-pill"]').exists()).toBe(false)
  })

  it('renders the checkbox ticked but NOT disabled when selected=true and inChain=false', () => {
    const w = mountCard({ linkMode: true, selected: true, inChain: false })
    const cb = w.find('[data-testid="roadmap-select-checkbox-rmi-1"]')
    expect(cb.element.checked).toBe(true)
    expect(cb.element.disabled).toBe(false)
  })

  it('checkbox is ticked (selected || inChain) — inChain alone forces ticked', () => {
    const w = mountCard({ linkMode: true, selected: false, inChain: true })
    const cb = w.find('[data-testid="roadmap-select-checkbox-rmi-1"]')
    expect(cb.element.checked).toBe(true)
  })

  it('chain member shows the In-chain badge in place of the Activate button (FE-6170)', () => {
    // FE-6170: for a chain member the action-rail Activate button is REPLACED by
    // the "In chain" badge (v-if/v-else-if), so there is no faded Activate button.
    const w = mountCard({ inChain: true, electionActive: true })
    expect(w.find('[data-testid="roadmap-in-chain-pill"]').exists()).toBe(true)
    expect(w.find('.rm-primary-btn--election-faded').exists()).toBe(false)
  })

  it('election-fade applies to the Activate button for a NON-chain card when election active (FE-6170)', () => {
    // A non-chain, activatable project keeps its Activate button, faded while an
    // election is active so the only launch affordance is Run Sequential.
    const w = mountCard({ inChain: false, electionActive: true })
    expect(w.find('.rm-primary-btn--election-faded').exists()).toBe(true)
  })
})
