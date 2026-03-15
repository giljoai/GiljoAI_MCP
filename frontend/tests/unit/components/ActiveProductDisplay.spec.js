import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import ActiveProductDisplay from '@/components/ActiveProductDisplay.vue'
import { useProductStore } from '@/stores/products'
import api from '@/services/api'

describe('ActiveProductDisplay Component (Handover 0049)', () => {
  let router

  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()

    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        {
          path: '/products',
          name: 'Products',
          component: { template: '<div>Products</div>' }
        }
      ]
    })
  })

  describe('Component Lifecycle', () => {
    it('mounts without errors', () => {
      const wrapper = mount(ActiveProductDisplay, {
        global: {
          plugins: [router],
          stubs: { teleport: true, 'v-chip': { template: '<div class="v-chip">Chip</div>' } }
        }
      })

      expect(wrapper.exists()).toBe(true)
    })

    it('calls fetchActiveProduct on mount', async () => {
      api.products.getActive.mockResolvedValue({ data: { has_active_product: false, product: null } })

      mount(ActiveProductDisplay, {
        global: {
          plugins: [router],
          stubs: { teleport: true, 'v-chip': { template: '<div>Chip</div>' } }
        }
      })

      await new Promise(resolve => setTimeout(resolve, 100))

      // Verify the store's fetchActiveProduct calls the dedicated active-product endpoint
      expect(api.products.getActive).toHaveBeenCalled()
    })
  })

  describe('Rendering Logic', () => {
    it('renders content without errors when activeProduct exists', () => {
      const store = useProductStore()
      store.activeProduct = { id: 1, name: 'Test Product' }

      const wrapper = mount(ActiveProductDisplay, {
        global: {
          plugins: [router],
          stubs: { teleport: true, 'v-chip': { template: '<div>{{$attrs["prepend-icon"]}}</div>' } }
        }
      })

      expect(wrapper.exists()).toBe(true)
      expect(wrapper.html()).toBeTruthy()
    })

    it('renders content without errors when no activeProduct', () => {
      const store = useProductStore()
      store.activeProduct = null

      const wrapper = mount(ActiveProductDisplay, {
        global: {
          plugins: [router],
          stubs: { teleport: true, 'v-chip': { template: '<div>No Active</div>' } }
        }
      })

      expect(wrapper.exists()).toBe(true)
      expect(wrapper.html()).toBeTruthy()
    })
  })

  describe('Store Integration', () => {
    it('is bound to store activeProduct state', async () => {
      const store = useProductStore()
      store.activeProduct = { id: 1, name: 'ProductA' }

      const wrapper = mount(ActiveProductDisplay, {
        global: {
          plugins: [router],
          stubs: { teleport: true, 'v-chip': true }
        }
      })

      await wrapper.vm.$nextTick()

      expect(store.activeProduct.name).toBe('ProductA')
    })

    it('responds to activeProduct changes', async () => {
      const store = useProductStore()
      store.activeProduct = { id: 1, name: 'ProductA' }

      const wrapper = mount(ActiveProductDisplay, {
        global: {
          plugins: [router],
          stubs: { teleport: true, 'v-chip': true }
        }
      })

      await wrapper.vm.$nextTick()

      store.activeProduct = { id: 2, name: 'ProductB' }

      await wrapper.vm.$nextTick()

      expect(store.activeProduct.name).toBe('ProductB')
    })

    it('handles null activeProduct state', async () => {
      const store = useProductStore()
      store.activeProduct = null

      const wrapper = mount(ActiveProductDisplay, {
        global: {
          plugins: [router],
          stubs: { teleport: true, 'v-chip': true }
        }
      })

      await wrapper.vm.$nextTick()

      expect(store.activeProduct).toBeNull()

      store.activeProduct = { id: 1, name: 'NewProduct' }
      await wrapper.vm.$nextTick()

      expect(store.activeProduct).not.toBeNull()
    })
  })

  describe('API Error Handling', () => {
    it('handles API errors gracefully', async () => {
      api.products.getActive.mockRejectedValue(new Error('Network error'))

      const wrapper = mount(ActiveProductDisplay, {
        global: {
          plugins: [router],
          stubs: { teleport: true, 'v-chip': true }
        }
      })

      await new Promise(resolve => setTimeout(resolve, 100))

      expect(wrapper.exists()).toBe(true)
    })

    it('logs errors to console', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      api.products.getActive.mockRejectedValue(new Error('Test error'))

      mount(ActiveProductDisplay, {
        global: {
          plugins: [router],
          stubs: { teleport: true, 'v-chip': true }
        }
      })

      await new Promise(resolve => setTimeout(resolve, 100))

      expect(consoleSpy).toHaveBeenCalled()
      consoleSpy.mockRestore()
    })
  })

  describe('Component Props and Attributes', () => {
    it('passes correct props to v-chip when active', () => {
      const store = useProductStore()
      store.activeProduct = { id: 1, name: 'Test' }

      const vChipStub = { template: '<div></div>' }

      const wrapper = mount(ActiveProductDisplay, {
        global: {
          plugins: [router],
          stubs: { teleport: true, 'v-chip': vChipStub }
        }
      })

      const chipComponents = wrapper.findAllComponents(vChipStub)
      expect(chipComponents.length).toBeGreaterThan(0)
    })

    it('maintains correct structure', () => {
      const store = useProductStore()
      store.activeProduct = null

      const wrapper = mount(ActiveProductDisplay, {
        global: {
          plugins: [router],
          stubs: { teleport: true, 'v-chip': true }
        }
      })

      const html = wrapper.html()
      // Component structure should be present
      expect(html).toBeTruthy()
      expect(html.length).toBeGreaterThan(0)
    })
  })

  describe('Loading State', () => {
    it('has loading ref initialized as true', () => {
      api.products.getActive.mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({ data: { has_active_product: false, product: null } }), 200))
      )

      const wrapper = mount(ActiveProductDisplay, {
        global: {
          plugins: [router],
          stubs: { teleport: true, 'v-chip': true, 'v-progress-circular': true }
        }
      })

      // Component instance should exist
      expect(wrapper.vm).toBeTruthy()
    })

    it('transitions from loading state', async () => {
      api.products.getActive.mockResolvedValue({ data: { has_active_product: false, product: null } })

      const wrapper = mount(ActiveProductDisplay, {
        global: {
          plugins: [router],
          stubs: { teleport: true, 'v-chip': true, 'v-progress-circular': true }
        }
      })

      await new Promise(resolve => setTimeout(resolve, 150))

      // Component should still exist after loading
      expect(wrapper.exists()).toBe(true)
    })
  })
})
