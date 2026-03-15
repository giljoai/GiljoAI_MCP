import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ProductsView from '@/views/ProductsView.vue'
import { useProductStore } from '@/stores/products'

describe('ProductsView - active products count uses is_active', () => {
  let pinia

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
  })

  it('counts only items with is_active === true', async () => {
    const store = useProductStore()
    store.products = [
      { id: 1, name: 'A', is_active: true },
      { id: 2, name: 'B', is_active: false },
      { id: 3, name: 'C', is_active: true },
      // status field should be ignored by the view logic
      { id: 4, name: 'D', status: 'active', is_active: false },
    ]

    const wrapper = mount(ProductsView, {
      global: { plugins: [pinia] },
    })

    const vm = wrapper.vm
    // Access computed via instance proxy
    expect(vm.activeProducts).toBe(2)
  })
})
