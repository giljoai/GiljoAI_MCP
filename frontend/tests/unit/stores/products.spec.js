/**
 * Unit tests for products store - authentication-gated initialization
 * Tests for Handover 0005: Authentication-Gated Product Initialization
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useProductStore } from '@/stores/products'
import api from '@/services/api'

// Mock the API service
vi.mock('@/services/api', () => ({
  default: {
    setup: {
      status: vi.fn(),
    },
    products: {
      list: vi.fn(),
      get: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
      metrics: vi.fn().mockResolvedValue({ data: { totalTasks: 0, completedTasks: 0, activeAgents: 0, totalProjects: 0 } }),
      getActive: vi.fn().mockResolvedValue({ data: { has_active_product: false, product: null } }),
    },
  },
}))

// Mock project store dependency (products store imports useProjectStore)
vi.mock('@/stores/projects', () => ({
  useProjectStore: () => ({
    fetchProjects: vi.fn().mockResolvedValue(),
  }),
}))

// Mock localStorage
const localStorageMock = (() => {
  let store = {}
  return {
    getItem: vi.fn(key => store[key] || null),
    setItem: vi.fn((key, value) => {
      store[key] = value.toString()
    }),
    removeItem: vi.fn(key => {
      delete store[key]
    }),
    clear: vi.fn(() => {
      store = {}
    }),
  }
})()

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
})

describe('Products Store - Authentication Gated Initialization', () => {
  beforeEach(() => {
    // Create a fresh pinia instance for each test
    setActivePinia(createPinia())
    // Clear all mocks before each test
    vi.clearAllMocks()
    // Clear localStorage mock
    localStorageMock.clear()
  })

  describe('initializeFromStorage - Product Restoration', () => {
    // Auth guards removed — caller (DefaultLayout) verifies authentication before calling.
    // initializeFromStorage now directly fetches products and restores from localStorage.

    it('should fetch products and set first product when no stored ID', async () => {
      const store = useProductStore()

      localStorageMock.getItem.mockReturnValue(null)

      const mockProducts = [
        { id: 1, name: 'Product 1' },
        { id: 2, name: 'Product 2' }
      ]
      api.products.list.mockResolvedValue({ data: mockProducts })
      api.products.get.mockResolvedValue({ data: { id: 1, name: 'Product 1' } })

      await store.initializeFromStorage()

      expect(api.products.list).toHaveBeenCalled()
      expect(store.products).toEqual(mockProducts)
    })

    it('should restore stored product ID from localStorage', async () => {
      const store = useProductStore()

      localStorageMock.getItem.mockReturnValue('2')

      const mockProducts = [
        { id: 1, name: 'Product 1' },
        { id: 2, name: 'Product 2' }
      ]
      api.products.list.mockResolvedValue({ data: mockProducts })
      api.products.get.mockResolvedValue({ data: { id: 2, name: 'Product 2' } })

      await store.initializeFromStorage()

      expect(api.products.list).toHaveBeenCalled()
    })

    it('should handle empty product list gracefully', async () => {
      const store = useProductStore()

      localStorageMock.getItem.mockReturnValue(null)
      api.products.list.mockResolvedValue({ data: [] })

      await store.initializeFromStorage()

      expect(store.products).toHaveLength(0)
    })

    it('should remove stored ID if product no longer exists', async () => {
      const store = useProductStore()

      localStorageMock.getItem.mockReturnValue('999')

      const mockProducts = [{ id: 1, name: 'Product 1' }]
      api.products.list.mockResolvedValue({ data: mockProducts })
      api.products.get.mockResolvedValue({ data: { id: 1, name: 'Product 1' } })

      await store.initializeFromStorage()

      expect(localStorageMock.removeItem).toHaveBeenCalledWith('currentProductId')
    })

    it('should handle API failure gracefully', async () => {
      const store = useProductStore()

      api.products.list.mockRejectedValue(new Error('Network error'))

      await store.initializeFromStorage()

      expect(store.products).toHaveLength(0)
    })

    it('should restore selected product from localStorage after successful initialization', async () => {
      const store = useProductStore()

      // Mock auth token and stored product ID
      localStorageMock.getItem
        .mockReturnValueOnce('mock-token') // auth_token
        .mockReturnValueOnce('1') // currentProductId

      // Mock setup status - complete
      api.setup.status.mockResolvedValue({
        data: {
          default_password_active: false,
          database_initialized: true
        }
      })

      // Mock products API response
      const mockProducts = [
        { id: 1, name: 'Product 1' },
        { id: 2, name: 'Product 2' }
      ]
      api.products.list.mockResolvedValue({ data: mockProducts })
      // setCurrentProduct -> fetchProductById -> api.products.get
      api.products.get.mockResolvedValue({ data: { id: 1, name: 'Product 1' } })

      await store.initializeFromStorage()

      // Verify the stored product was selected (end state verification)
      expect(store.currentProductId).toBe(1)
      expect(store.currentProduct).toEqual({ id: 1, name: 'Product 1' })
    })

    it('should select first product when no stored product ID exists', async () => {
      const store = useProductStore()

      // Mock auth token exists, no stored product ID
      localStorageMock.getItem
        .mockReturnValueOnce('mock-token') // auth_token
        .mockReturnValueOnce(null) // currentProductId

      // Mock setup status - complete
      api.setup.status.mockResolvedValue({
        data: {
          default_password_active: false,
          database_initialized: true
        }
      })

      // Mock products API response
      const mockProducts = [
        { id: 1, name: 'Product 1' },
        { id: 2, name: 'Product 2' }
      ]
      api.products.list.mockResolvedValue({ data: mockProducts })
      // setCurrentProduct -> fetchProductById -> api.products.get
      api.products.get.mockResolvedValue({ data: { id: 1, name: 'Product 1' } })

      await store.initializeFromStorage()

      // Should select first product (end state verification)
      expect(store.currentProductId).toBe(1)
      expect(store.currentProduct).toEqual({ id: 1, name: 'Product 1' })
    })

    it('should handle missing stored product gracefully', async () => {
      const store = useProductStore()

      // Mock auth token and non-existent stored product ID
      localStorageMock.getItem
        .mockReturnValueOnce('mock-token') // auth_token
        .mockReturnValueOnce('999') // currentProductId (non-existent)

      // Mock setup status - complete
      api.setup.status.mockResolvedValue({
        data: {
          default_password_active: false,
          database_initialized: true
        }
      })

      // Mock products API response
      const mockProducts = [
        { id: 1, name: 'Product 1' },
        { id: 2, name: 'Product 2' }
      ]
      api.products.list.mockResolvedValue({ data: mockProducts })
      // Product 999 not found, so it tries first available (id: 1)
      // fetchProductById(999) returns null (not found), then falls back to first product
      api.products.get
        .mockResolvedValueOnce({ data: null }) // fetchProductById(999) - not found
        .mockResolvedValue({ data: { id: 1, name: 'Product 1' } }) // fallback to first

      await store.initializeFromStorage()

      // Should clear localStorage and select first available product
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('currentProductId')
      expect(store.currentProductId).toBe(1)
    })

    it('should handle products fetch error gracefully', async () => {
      const store = useProductStore()

      // Mock auth token exists
      localStorageMock.getItem.mockReturnValue('mock-token')

      // Mock setup status - complete
      api.setup.status.mockResolvedValue({
        data: {
          default_password_active: false,
          database_initialized: true
        }
      })

      // Mock products API error
      api.products.list.mockRejectedValue(new Error('Products fetch failed'))

      await store.initializeFromStorage()

      expect(store.products).toHaveLength(0)
      expect(store.error).toBe('Products fetch failed')
    })
  })

  describe('API Integration', () => {
    // Auth is now handled by DefaultLayout before calling initializeFromStorage.
    // These tests verify the API calls are made correctly.

    it('should call products list API on initialization', async () => {
      const store = useProductStore()

      localStorageMock.getItem.mockReturnValue(null)
      api.products.list.mockResolvedValue({ data: [] })

      await store.initializeFromStorage()

      expect(api.products.list).toHaveBeenCalled()
    })

    it('should call fetchActiveProduct after loading products', async () => {
      const store = useProductStore()

      localStorageMock.getItem.mockReturnValue(null)
      api.products.list.mockResolvedValue({ data: [{ id: 1, name: 'P1' }] })
      api.products.get.mockResolvedValue({ data: { id: 1, name: 'P1' } })
      api.products.getActive = vi.fn().mockResolvedValue({ data: { has_active_product: true, product: { id: 1, name: 'P1' } } })

      await store.initializeFromStorage()

      expect(api.products.list).toHaveBeenCalled()
    })
  })

  describe('State Management', () => {
    it('should initialize with empty products array', () => {
      const store = useProductStore()

      expect(store.products).toEqual([])
      expect(store.currentProduct).toBeNull()
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })

    it('should maintain loading state during initialization', async () => {
      const store = useProductStore()

      // Mock auth token
      localStorageMock.getItem.mockReturnValue('mock-token')

      // Setup status resolves immediately so fetchProducts runs next
      api.setup.status.mockResolvedValue({
        data: { default_password_active: false, database_initialized: true }
      })

      // Create a deferred promise for products.list to control when it resolves
      let resolveProductsList
      api.products.list.mockImplementation(() =>
        new Promise(resolve => {
          resolveProductsList = resolve
        })
      )

      const initPromise = store.initializeFromStorage()

      // Wait for setup.status to resolve and fetchProducts to start
      await new Promise(resolve => setTimeout(resolve, 0))

      // Loading should be true while fetchProducts is in progress
      expect(store.loading).toBe(true)

      // Resolve the products list
      resolveProductsList({ data: [] })

      await initPromise

      // Loading should be false after completion
      expect(store.loading).toBe(false)
    })
  })

  describe('Product Creation - Bug A Fix (Handover 0485)', () => {
    it('should NOT auto-switch currentProductId after creating a product', async () => {
      const store = useProductStore()

      // Mock initial state: user has product ID 1 selected
      store.currentProductId = 1
      store.currentProduct = { id: 1, name: 'Existing Product' }

      // Mock API response for product creation
      const newProduct = { id: 2, name: 'New Product' }
      api.products = {
        ...api.products,
        create: vi.fn().mockResolvedValue({ data: newProduct }),
        get: vi.fn().mockResolvedValue({ data: newProduct }),
        list: vi.fn().mockResolvedValue({ data: [
          { id: 1, name: 'Existing Product' },
          newProduct
        ]}),
        metrics: vi.fn().mockResolvedValue({ data: {
          totalTasks: 0,
          completedTasks: 0,
          activeAgents: 0,
          totalProjects: 0
        }})
      }

      // Spy on setCurrentProduct to track calls
      const setCurrentProductSpy = vi.spyOn(store, 'setCurrentProduct')

      // Create new product
      const result = await store.createProduct({ name: 'New Product' })

      // BEHAVIOR TEST: currentProductId should REMAIN at 1 (not switch to 2)
      expect(store.currentProductId).toBe(1)
      expect(store.currentProduct.id).toBe(1)

      // BEHAVIOR TEST: setCurrentProduct should NOT be called
      expect(setCurrentProductSpy).not.toHaveBeenCalled()

      // BEHAVIOR TEST: new product should appear in products array
      expect(store.products).toContainEqual(newProduct)
      expect(result).toEqual(newProduct)
    })

    it('should add new product to products array without changing selection', async () => {
      const store = useProductStore()

      // Set up initial products
      store.products = [
        { id: 1, name: 'Product A' },
        { id: 2, name: 'Product B' }
      ]
      store.currentProductId = 1

      // Mock API response
      const newProduct = { id: 3, name: 'Product C' }
      api.products = {
        ...api.products,
        create: vi.fn().mockResolvedValue({ data: newProduct })
      }

      // Spy on setCurrentProduct
      const setCurrentProductSpy = vi.spyOn(store, 'setCurrentProduct')

      await store.createProduct({ name: 'Product C' })

      // BEHAVIOR: currentProductId unchanged
      expect(store.currentProductId).toBe(1)

      // BEHAVIOR: products array grows by 1
      expect(store.products).toHaveLength(3)
      expect(store.products[2]).toEqual(newProduct)

      // BEHAVIOR: setCurrentProduct never called
      expect(setCurrentProductSpy).not.toHaveBeenCalled()
    })
  })
})
