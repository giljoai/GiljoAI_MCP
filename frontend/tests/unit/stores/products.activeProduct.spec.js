import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useProductStore } from '@/stores/products'
import api from '@/services/api'

vi.mock('@/services/api')

describe('Product Store - Active Product (Handover 0049)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('State Initialization', () => {
    it('initializes with activeProduct as null', () => {
      const store = useProductStore()
      expect(store.activeProduct).toBeNull()
    })

    it('initializes with activeProductLoading as false', () => {
      const store = useProductStore()
      expect(store.activeProductLoading).toBe(false)
    })
  })

  describe('fetchActiveProduct()', () => {
    it('fetches and stores active product', async () => {
      const mockProduct = {
        id: 1,
        name: 'TinyContacts',
        is_active: true
      }

      api.products.list.mockResolvedValue({
        data: [mockProduct]
      })

      const store = useProductStore()
      await store.fetchActiveProduct()

      expect(store.activeProduct).toEqual(mockProduct)
    })

    it('calls API with is_active filter', async () => {
      api.products.list.mockResolvedValue({ data: [] })

      const store = useProductStore()
      await store.fetchActiveProduct()

      expect(api.products.list).toHaveBeenCalledWith({ is_active: true })
    })

    it('sets activeProduct to null when no active products exist', async () => {
      api.products.list.mockResolvedValue({
        data: []
      })

      const store = useProductStore()
      await store.fetchActiveProduct()

      expect(store.activeProduct).toBeNull()
    })

    it('handles API errors by setting activeProduct to null', async () => {
      const error = new Error('API Error')
      api.products.list.mockRejectedValue(error)

      const store = useProductStore()
      await store.fetchActiveProduct()

      expect(store.activeProduct).toBeNull()
      expect(store.error).toBe(error.message)
    })

    it('sets loading state during fetch', async () => {
      api.products.list.mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({ data: [] }), 50))
      )

      const store = useProductStore()
      const fetchPromise = store.fetchActiveProduct()

      expect(store.activeProductLoading).toBe(true)

      await fetchPromise

      expect(store.activeProductLoading).toBe(false)
    })

    it('clears error on successful fetch', async () => {
      const store = useProductStore()
      store.error = 'Previous error'

      api.products.list.mockResolvedValue({
        data: [{ id: 1, name: 'Product' }]
      })

      await store.fetchActiveProduct()

      expect(store.error).toBeNull()
    })

    it('uses first product if multiple are active', async () => {
      const mockProducts = [
        { id: 1, name: 'First Active', is_active: true },
        { id: 2, name: 'Second Active', is_active: true }
      ]

      api.products.list.mockResolvedValue({
        data: mockProducts
      })

      const store = useProductStore()
      await store.fetchActiveProduct()

      expect(store.activeProduct).toEqual(mockProducts[0])
    })
  })

  describe('clearProductData()', () => {
    it('clears activeProduct along with other data', async () => {
      const store = useProductStore()

      api.products.list.mockResolvedValue({
        data: [{ id: 1, name: 'Active Product' }]
      })

      await store.fetchActiveProduct()
      expect(store.activeProduct).not.toBeNull()

      store.clearProductData()

      expect(store.activeProduct).toBeNull()
      expect(store.products).toEqual([])
      expect(store.currentProductId).toBeNull()
    })
  })

  describe('Integration with existing product functionality', () => {
    it('maintains activeProduct independently from currentProduct', async () => {
      api.products.list.mockResolvedValue({
        data: [
          { id: 1, name: 'Product 1', is_active: true },
          { id: 2, name: 'Product 2', is_active: false }
        ]
      })

      api.products.get.mockResolvedValue({
        data: { id: 2, name: 'Product 2' }
      })

      const store = useProductStore()

      await store.fetchActiveProduct()
      expect(store.activeProduct.name).toBe('Product 1')

      await store.setCurrentProduct(2)
      expect(store.currentProduct.name).toBe('Product 2')

      // activeProduct should remain unchanged
      expect(store.activeProduct.name).toBe('Product 1')
    })

    it('both states are independent during product operations', async () => {
      api.products.list.mockResolvedValue({
        data: [{ id: 1, name: 'ActiveProduct' }]
      })

      const store = useProductStore()
      await store.fetchActiveProduct()

      const activeProductBefore = store.activeProduct

      // Simulate creating a product
      api.products.create.mockResolvedValue({
        data: { id: 2, name: 'NewProduct' }
      })
      api.products.get.mockResolvedValue({
        data: { id: 2, name: 'NewProduct' }
      })

      await store.createProduct({ name: 'NewProduct' })

      // activeProduct should remain unchanged
      expect(store.activeProduct).toEqual(activeProductBefore)
    })
  })

  describe('Error State Management', () => {
    it('preserves error message from failed fetch', async () => {
      const errorMessage = 'Detailed error message'
      api.products.list.mockRejectedValue(new Error(errorMessage))

      const store = useProductStore()
      await store.fetchActiveProduct()

      expect(store.error).toBe(errorMessage)
    })

    it('clears error when fetch succeeds after failure', async () => {
      const store = useProductStore()

      api.products.list.mockRejectedValue(new Error('First error'))
      await store.fetchActiveProduct()
      expect(store.error).toBe('First error')

      api.products.list.mockResolvedValue({
        data: [{ id: 1, name: 'Product' }]
      })
      await store.fetchActiveProduct()

      expect(store.error).toBeNull()
    })
  })

  describe('Loading State', () => {
    it('properly toggles loading state on success', async () => {
      api.products.list.mockResolvedValue({
        data: [{ id: 1, name: 'Product' }]
      })

      const store = useProductStore()

      expect(store.activeProductLoading).toBe(false)

      const promise = store.fetchActiveProduct()
      expect(store.activeProductLoading).toBe(true)

      await promise
      expect(store.activeProductLoading).toBe(false)
    })

    it('properly toggles loading state on error', async () => {
      api.products.list.mockRejectedValue(new Error('Error'))

      const store = useProductStore()

      expect(store.activeProductLoading).toBe(false)

      const promise = store.fetchActiveProduct()
      expect(store.activeProductLoading).toBe(true)

      await promise
      expect(store.activeProductLoading).toBe(false)
    })
  })

  describe('Active Product Data Structure', () => {
    it('preserves complete product object structure', async () => {
      const mockProduct = {
        id: 123,
        name: 'CompleteProduct',
        is_active: true,
        description: 'Test description',
        created_at: '2025-01-01T00:00:00Z',
        config_data: { field1: 'value1' }
      }

      api.products.list.mockResolvedValue({
        data: [mockProduct]
      })

      const store = useProductStore()
      await store.fetchActiveProduct()

      expect(store.activeProduct).toEqual(mockProduct)
      expect(store.activeProduct.config_data).toEqual({ field1: 'value1' })
    })

    it('handles products with minimal data', async () => {
      const minimalProduct = {
        id: 1,
        name: 'Minimal',
        is_active: true
      }

      api.products.list.mockResolvedValue({
        data: [minimalProduct]
      })

      const store = useProductStore()
      await store.fetchActiveProduct()

      expect(store.activeProduct).toEqual(minimalProduct)
    })
  })
})
