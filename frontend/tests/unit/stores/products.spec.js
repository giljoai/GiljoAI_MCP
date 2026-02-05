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
    },
  },
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

  describe('initializeFromStorage - Auth Guards', () => {
    it('should skip initialization without auth token', async () => {
      const store = useProductStore()
      
      // No auth token in localStorage
      localStorageMock.getItem.mockReturnValue(null)
      
      await store.initializeFromStorage()
      
      expect(store.products).toHaveLength(0)
      expect(api.setup.status).not.toHaveBeenCalled()
      expect(api.products.list).not.toHaveBeenCalled()
    })

    it('should skip initialization during setup (default password active)', async () => {
      const store = useProductStore()
      
      // Mock auth token exists
      localStorageMock.getItem.mockReturnValue('mock-token')
      
      // Mock setup status - default password active
      api.setup.status.mockResolvedValue({
        data: {
          default_password_active: true,
          database_initialized: true
        }
      })
      
      await store.initializeFromStorage()
      
      expect(store.products).toHaveLength(0)
      expect(api.setup.status).toHaveBeenCalledTimes(1)
      expect(api.products.list).not.toHaveBeenCalled()
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('currentProductId')
    })

    it('should skip initialization during setup (database not initialized)', async () => {
      const store = useProductStore()
      
      // Mock auth token exists
      localStorageMock.getItem.mockReturnValue('mock-token')
      
      // Mock setup status - database not initialized
      api.setup.status.mockResolvedValue({
        data: {
          default_password_active: false,
          database_initialized: false
        }
      })
      
      await store.initializeFromStorage()
      
      expect(store.products).toHaveLength(0)
      expect(api.setup.status).toHaveBeenCalledTimes(1)
      expect(api.products.list).not.toHaveBeenCalled()
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('currentProductId')
    })

    it('should skip initialization when setup status check fails', async () => {
      const store = useProductStore()
      
      // Mock auth token exists
      localStorageMock.getItem.mockReturnValue('mock-token')
      
      // Mock setup status failure
      api.setup.status.mockRejectedValue(new Error('API error'))
      
      await store.initializeFromStorage()
      
      expect(store.products).toHaveLength(0)
      expect(api.setup.status).toHaveBeenCalledTimes(1)
      expect(api.products.list).not.toHaveBeenCalled()
    })

    it('should initialize products after authentication when setup is complete', async () => {
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
      
      // Mock products API response
      const mockProducts = [
        { id: 1, name: 'Product 1' },
        { id: 2, name: 'Product 2' }
      ]
      api.products.list.mockResolvedValue({ data: mockProducts })
      
      await store.initializeFromStorage()
      
      expect(api.setup.status).toHaveBeenCalledTimes(1)
      expect(api.products.list).toHaveBeenCalledTimes(1)
      expect(store.products).toEqual(mockProducts)
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
      
      // Spy on setCurrentProduct
      const setCurrentProductSpy = vi.spyOn(store, 'setCurrentProduct').mockResolvedValue()
      
      await store.initializeFromStorage()
      
      expect(setCurrentProductSpy).toHaveBeenCalledWith(1)
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
      
      // Spy on setCurrentProduct
      const setCurrentProductSpy = vi.spyOn(store, 'setCurrentProduct').mockResolvedValue()
      
      await store.initializeFromStorage()
      
      expect(setCurrentProductSpy).toHaveBeenCalledWith(1)
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
      
      // Spy on setCurrentProduct
      const setCurrentProductSpy = vi.spyOn(store, 'setCurrentProduct').mockResolvedValue()
      
      await store.initializeFromStorage()
      
      // Should clear localStorage and select first available product
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('currentProductId')
      expect(setCurrentProductSpy).toHaveBeenCalledWith(1)
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

  describe('Authentication Integration', () => {
    it('should use API client for setup status check (not direct fetch)', async () => {
      const store = useProductStore()
      
      // Mock auth token exists
      localStorageMock.getItem.mockReturnValue('mock-token')
      
      // Mock setup status
      api.setup.status.mockResolvedValue({
        data: {
          default_password_active: false,
          database_initialized: true
        }
      })
      
      // Mock products response (empty to focus on setup check)
      api.products.list.mockResolvedValue({ data: [] })
      
      await store.initializeFromStorage()
      
      // Verify that api.setup.status is called (uses API client with auth headers)
      expect(api.setup.status).toHaveBeenCalledTimes(1)
    })

    it('should respect authentication token for all API calls', async () => {
      const store = useProductStore()
      const mockToken = 'bearer-token-123'
      
      // Mock auth token exists
      localStorageMock.getItem.mockReturnValue(mockToken)
      
      // Mock setup and products responses
      api.setup.status.mockResolvedValue({
        data: { default_password_active: false, database_initialized: true }
      })
      api.products.list.mockResolvedValue({ data: [] })
      
      await store.initializeFromStorage()
      
      // Both API calls should have been made (indicating auth token was present)
      expect(api.setup.status).toHaveBeenCalledTimes(1)
      expect(api.products.list).toHaveBeenCalledTimes(1)
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
      
      // Mock slow API responses
      api.setup.status.mockImplementation(() => 
        new Promise(resolve => 
          setTimeout(() => resolve({ 
            data: { default_password_active: false, database_initialized: true }
          }), 50)
        )
      )
      api.products.list.mockImplementation(() =>
        new Promise(resolve => 
          setTimeout(() => resolve({ data: [] }), 50)
        )
      )
      
      const initPromise = store.initializeFromStorage()
      
      // Loading should be true during fetch
      expect(store.loading).toBe(true)
      
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