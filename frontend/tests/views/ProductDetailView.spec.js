/**
 * FE-9000e — ProductDetailView.vue regression trap coverage.
 *
 * DefaultLayout's router-view now keys on the matched route record, not the
 * resolved path, so a param-only nav (/products/A -> /products/B) reuses
 * this component instance instead of remounting it. Before this WO, the
 * view only fetched onMounted -- with instance reuse it would silently show
 * the previous product's stale data. This asserts the added param watcher
 * refetches on a route.params.id change.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createVuetify } from 'vuetify'
import { reactive } from 'vue'
import api from '@/services/api'

const mockRoute = reactive({ params: { id: 'product-1' } })
vi.mock('vue-router', () => ({
  useRoute: () => mockRoute,
}))

import ProductDetailView from '@/views/ProductDetailView.vue'

function mountView() {
  const vuetify = createVuetify()
  return mount(ProductDetailView, {
    global: { plugins: [vuetify] },
  })
}

describe('ProductDetailView.vue — refetch on param change (FE-9000e regression trap)', () => {
  let wrapper

  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    mockRoute.params.id = 'product-1'
  })

  afterEach(() => {
    // Unmount so the previous test's watcher on the shared mockRoute doesn't
    // fire again (and steal a queued mockResolvedValueOnce) on the next test.
    if (wrapper) wrapper.unmount()
    wrapper = null
  })

  it('fetches the product for the initial route param on mount', async () => {
    api.products.get.mockResolvedValueOnce({ data: { id: 'product-1', name: 'Product One' } })

    wrapper = mountView()
    await flushPromises()

    expect(api.products.get).toHaveBeenCalledWith('product-1')
    expect(wrapper.vm.product).toEqual({ id: 'product-1', name: 'Product One' })
    expect(wrapper.text()).toContain('Product One')
  })

  it('refetches and swaps displayed data when route.params.id changes (instance-reuse case)', async () => {
    api.products.get.mockResolvedValueOnce({ data: { id: 'product-1', name: 'Product One' } })
    wrapper = mountView()
    await flushPromises()
    expect(wrapper.vm.product).toEqual({ id: 'product-1', name: 'Product One' })

    api.products.get.mockResolvedValueOnce({ data: { id: 'product-2', name: 'Product Two' } })
    mockRoute.params.id = 'product-2'
    await flushPromises()

    expect(api.products.get).toHaveBeenCalledWith('product-2')
    expect(wrapper.vm.product).toEqual({ id: 'product-2', name: 'Product Two' })
    expect(wrapper.text()).toContain('Product Two')
    expect(wrapper.text()).not.toContain('Product One')
  })
})
