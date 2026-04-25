/**
 * SAAS-022: DangerPage card-based redesign.
 *
 * Verifies the two-card layout (export + delete), data-test selectors,
 * and that clicking the enabled Delete button surfaces the confirmation
 * modal trigger.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { createPinia, setActivePinia } from 'pinia'

import DangerPage from '@/views/account/DangerPage.vue'

vi.mock('@/services/configService', () => ({
  default: {
    getEdition: () => 'saas',
    getGiljoMode: () => 'saas',
  },
}))

// Stub the lazily-loaded SaaS modal so the spec runs without real deletion logic.
vi.mock('@/saas/components/DeleteAccountDialog.vue', () => ({
  default: {
    name: 'DeleteAccountDialog',
    props: ['modelValue'],
    emits: ['update:modelValue'],
    template: '<div data-test="delete-account-dialog-stub" :data-open="modelValue ? \'1\' : \'0\'" />',
  },
}))

describe('DangerPage.vue (SAAS-022 redesign)', () => {
  let vuetify
  let pinia

  beforeEach(() => {
    vuetify = createVuetify({ components, directives })
    pinia = createPinia()
    setActivePinia(pinia)
  })

  function makeWrapper() {
    return mount(DangerPage, {
      global: { plugins: [vuetify, pinia] },
    })
  }

  it('renders the two danger-zone cards with new selectors', async () => {
    const wrapper = makeWrapper()
    await flushPromises()

    expect(wrapper.find('[data-test="export-data-card"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="delete-account-card"]').exists()).toBe(true)
  })

  it('keeps the legacy data-test names off the page', async () => {
    const wrapper = makeWrapper()
    await flushPromises()

    expect(wrapper.find('[data-test="export-data-row"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="delete-account-row"]').exists()).toBe(false)
  })

  it('shows the new subtitle copy', async () => {
    const wrapper = makeWrapper()
    await flushPromises()

    expect(wrapper.text()).toContain('Account-level actions. These are permanent — proceed carefully.')
  })

  it('keeps the export card disabled with a "Coming soon" chip', async () => {
    const wrapper = makeWrapper()
    await flushPromises()

    const exportCard = wrapper.find('[data-test="export-data-card"]')
    expect(exportCard.text()).toContain('Coming soon')
  })

  it('exposes an enabled delete button on the delete card', async () => {
    const wrapper = makeWrapper()
    await flushPromises()

    const deleteBtn = wrapper.find('[data-test="open-delete-account-dialog"]')
    expect(deleteBtn.exists()).toBe(true)
    expect(deleteBtn.attributes('disabled')).toBeFalsy()
  })

  it('opens the delete confirmation dialog when the delete button is clicked', async () => {
    const wrapper = makeWrapper()
    await flushPromises()

    expect(wrapper.find('[data-test="delete-account-dialog-stub"]').attributes('data-open')).toBe('0')

    await wrapper.find('[data-test="open-delete-account-dialog"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-test="delete-account-dialog-stub"]').attributes('data-open')).toBe('1')
  })

  it('hides the delete card on Community Edition', async () => {
    vi.resetModules()
    vi.doMock('@/services/configService', () => ({
      default: { getEdition: () => 'community', getGiljoMode: () => 'ce' },
    }))
    const { default: CeDangerPage } = await import('@/views/account/DangerPage.vue')
    const wrapper = mount(CeDangerPage, { global: { plugins: [vuetify, pinia] } })
    await flushPromises()

    // Export card stays visible (it is edition-neutral),
    // but the delete card is SaaS-only and must be absent in CE.
    expect(wrapper.find('[data-test="export-data-card"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="delete-account-card"]').exists()).toBe(false)
  })
})
