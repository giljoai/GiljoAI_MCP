/**
 * ProductCard.spec.js — FE-6006 unit 3b
 *
 * Tests the pure-presentational product card component.
 * Edition scope: CE
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/utils/colorUtils', () => ({
  hexToRgba: (hex, alpha) => `rgba(${hex},${alpha})`,
}))
vi.mock('@/utils/statusConfig', () => ({
  getStatusColor: () => '#67bd6d',
}))
vi.mock('@/config/agentColors', () => ({
  getAgentColor: () => ({ hex: '#ffc300' }),
}))

import ProductCard from './ProductCard.vue'

const baseProduct = {
  id: 'prod-1',
  name: 'My Product',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: null,
  task_count: 3,
  project_count: 5,
  unfinished_projects: 2,
  // BE-6066 P4: the lean list ships pre-aggregated vision_summary, not the
  // full vision_documents array.
  vision_summary: { doc_count: 0, chunked_count: 0, chunk_total: 0, embedded_count: 0 },
  vision_analysis_complete: false,
}

function mountCard(props = {}) {
  return mount(ProductCard, {
    props: {
      product: baseProduct,
      isActive: false,
      ...props,
    },
    global: {
      stubs: {
        'v-icon': { template: '<i class="v-icon"><slot /></i>' },
        'v-btn': { template: '<button class="v-btn" v-bind="$attrs" @click="$emit(\'click\')"><slot /></button>' },
        'v-card': { template: '<div class="v-card"><slot /></div>' },
        'v-card-text': { template: '<div class="v-card-text"><slot /></div>' },
        'v-card-actions': { template: '<div class="v-card-actions"><slot /></div>' },
        'v-divider': { template: '<hr />' },
        'v-row': { template: '<div class="v-row"><slot /></div>' },
        'v-col': { template: '<div class="v-col"><slot /></div>' },
        'v-tooltip': { template: '<div class="v-tooltip"><slot /><slot name="activator" :props="{}" /></div>' },
      },
    },
  })
}

describe('ProductCard', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders product name', () => {
    const wrapper = mountCard()
    expect(wrapper.text()).toContain('My Product')
  })

  it('shows Active chip when isActive is true', () => {
    const wrapper = mountCard({ isActive: true })
    expect(wrapper.text()).toContain('Active')
  })

  it('does not show Active chip when isActive is false', () => {
    const wrapper = mountCard({ isActive: false })
    expect(wrapper.text()).not.toContain('Active')
  })

  it('displays task_count and project_count', () => {
    const wrapper = mountCard()
    expect(wrapper.text()).toContain('3') // task_count
    expect(wrapper.text()).toContain('5') // project_count
  })

  it('computes completed count as project_count - unfinished_projects', () => {
    const wrapper = mountCard()
    expect(wrapper.text()).toContain('3') // 5 - 2 = 3 completed
  })

  it('emits info event when info button clicked', async () => {
    const wrapper = mountCard()
    const btns = wrapper.findAll('.v-btn')
    // Find the info button by aria-label
    const infoBtn = btns.find(b => b.attributes('aria-label') === 'View product details')
    expect(infoBtn).toBeDefined()
    await infoBtn.trigger('click')
    expect(wrapper.emitted('info')).toBeTruthy()
    expect(wrapper.emitted('info')[0][0]).toEqual(baseProduct)
  })

  it('emits tune event when tune button clicked', async () => {
    const wrapper = mountCard()
    const tuneBtn = wrapper.findAll('.v-btn').find(b => b.attributes('aria-label') === 'Tune context')
    expect(tuneBtn).toBeDefined()
    await tuneBtn.trigger('click')
    expect(wrapper.emitted('tune')).toBeTruthy()
  })

  it('emits edit event when edit button clicked', async () => {
    const wrapper = mountCard()
    const editBtn = wrapper.findAll('.v-btn').find(b => b.attributes('aria-label') === 'Edit product')
    expect(editBtn).toBeDefined()
    await editBtn.trigger('click')
    expect(wrapper.emitted('edit')).toBeTruthy()
  })

  it('emits delete event when delete button clicked', async () => {
    const wrapper = mountCard()
    const delBtn = wrapper.findAll('.v-btn').find(b => b.attributes('aria-label') === 'Delete product')
    expect(delBtn).toBeDefined()
    await delBtn.trigger('click')
    expect(wrapper.emitted('delete')).toBeTruthy()
  })

  it('emits toggle-activation event when activate/deactivate button clicked', async () => {
    const wrapper = mountCard()
    const activateBtn = wrapper.findAll('.v-btn').find(b =>
      b.attributes('aria-label') === 'Activate product' || b.attributes('aria-label') === 'Deactivate product'
    )
    expect(activateBtn).toBeDefined()
    await activateBtn.trigger('click')
    expect(wrapper.emitted('toggle-activation')).toBeTruthy()
  })

  it('renders the docs chip and chunks from vision_summary', () => {
    const product = {
      ...baseProduct,
      vision_summary: { doc_count: 1, chunked_count: 1, chunk_total: 10, embedded_count: 1 },
      vision_analysis_complete: true,
    }
    const wrapper = mountCard({ product })
    expect(wrapper.text()).toContain('1 docs')
    expect(wrapper.text()).toContain('10 chunks')
    expect(wrapper.text()).toContain('Analyzed')
  })

  it('hides the vision block when vision_summary doc_count is 0', () => {
    const wrapper = mountCard()
    expect(wrapper.text()).not.toContain('docs')
  })

  it('shows Pending analysis with progress from vision_summary.embedded_count', () => {
    const product = {
      ...baseProduct,
      vision_summary: { doc_count: 3, chunked_count: 0, chunk_total: 0, embedded_count: 1 },
      vision_analysis_complete: false,
    }
    const wrapper = mountCard({ product })
    expect(wrapper.text()).toContain('Pending analysis — 1 of 3 docs analyzed')
  })
})
