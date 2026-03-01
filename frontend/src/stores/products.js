import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'
import { useProjectStore } from './projects'  // Product/Project State Fix

export const useProductStore = defineStore('products', () => {
  // Get project store for cross-store integration
  const projectStore = useProjectStore()  // Product/Project State Fix
  // State
  const products = ref([])
  const currentProductId = ref(null)
  const currentProduct = ref(null)
  const loading = ref(false)
  const error = ref(null)
  const productMetrics = ref({})
  const activeProduct = ref(null)

  // Getters
  const hasProducts = computed(() => products.value.length > 0)
  const productCount = computed(() => products.value.length)
  // Computed: Returns effective product ID for task operations
  // Prefers user-selected product (currentProductId) over active product
  const effectiveProductId = computed(() => {
    return currentProductId.value || activeProduct.value?.id || null
  })

  // Actions
  async function fetchProducts() {
    loading.value = true
    error.value = null
    try {
      const response = (await api.products?.list()) || { data: [] }
      products.value = response.data
    } catch (err) {
      error.value = err.message
      console.error('Failed to fetch products:', err)
    } finally {
      loading.value = false
    }
  }

  async function fetchProductById(productId) {
    if (!productId) {
      return null
    }

    loading.value = true
    error.value = null
    try {
      const response = (await api.products?.get(productId)) || { data: null }
      return response.data
    } catch (err) {
      error.value = err.message
      console.error('Failed to fetch product:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  async function setCurrentProduct(productId) {
    if (productId === currentProductId.value && productId !== null) {
      return
    }

    await fetchProducts()

    // Handle null productId or no products available - switch to first available or clear
    if (!productId || products.value.length === 0) {
      if (products.value.length > 0) {
        // Switch to first available product
        productId = products.value[0].id
      } else {
        // No products available - clear everything
        currentProductId.value = null
        currentProduct.value = null
        localStorage.removeItem('currentProductId')
        console.warn('No products available to set as current product')
        return
      }
    }

    const product = await fetchProductById(productId)
    if (!product) {
      console.warn(`Product ${productId} not found, switching to first available`)

      if (products.value.length > 0) {
        productId = products.value[0].id
        const fallbackProduct = await fetchProductById(productId)
        if (fallbackProduct) {
          currentProductId.value = productId
          currentProduct.value = fallbackProduct
          localStorage.setItem('currentProductId', productId)
          await fetchProductMetrics(productId)
          await projectStore.fetchProjects()
          window.dispatchEvent(
            new CustomEvent('product-changed', {
              detail: { productId, product: fallbackProduct },
            }),
          )
        }
        return
      } else {
        currentProductId.value = null
        currentProduct.value = null
        localStorage.removeItem('currentProductId')
        return
      }
    }

    currentProductId.value = productId
    currentProduct.value = product

    localStorage.setItem('currentProductId', productId)

    await fetchProductMetrics(productId)

    // Product/Project State Fix: Refresh projects when product changes
    // This ensures project list reflects the new product and deactivates old projects
    await projectStore.fetchProjects()

    window.dispatchEvent(
      new CustomEvent('product-changed', {
        detail: { productId, product },
      }),
    )
  }

  async function fetchProductMetrics(productId) {
    if (!productId) {
      return
    }

    try {
      const response = (await api.products?.metrics?.(productId)) || {
        data: {
          totalTasks: 0,
          completedTasks: 0,
          activeAgents: 0,
          totalProjects: 0,
        },
      }
      productMetrics.value[productId] = response.data
    } catch (err) {
      console.error('Failed to fetch product metrics:', err)
    }
  }

  async function createProduct(productData) {
    loading.value = true
    error.value = null
    try {
      const response = (await api.products?.create(productData)) || { data: null }
      if (response.data) {
        products.value.push(response.data)
      }
      return response.data
    } catch (err) {
      error.value = err.message
      console.error('Failed to create product:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateProduct(productId, updates) {
    loading.value = true
    error.value = null
    try {
      const response = (await api.products?.update(productId, updates)) || { data: null }
      if (response.data) {
        const index = products.value.findIndex((p) => p.id === productId)
        if (index !== -1) {
          products.value[index] = response.data
        }
        if (productId === currentProductId.value) {
          currentProduct.value = response.data
        }
      }
      return response.data
    } catch (err) {
      error.value = err.message
      console.error('Failed to update product:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteProduct(productId) {
    loading.value = true
    error.value = false
    try {
      await api.products?.delete(productId)
      products.value = products.value.filter((p) => p.id !== productId)

      if (productId === currentProductId.value) {
        await setCurrentProduct(null)
      }
    } catch (err) {
      error.value = err.message
      console.error('Failed to delete product:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchActiveProduct() {
    try {
      // Use dedicated active-product endpoint for accurate status
      const response = await api.products.getActive()
      const data = response?.data || { has_active_product: false, product: null }
      if (data.has_active_product && data.product) {
        activeProduct.value = data.product
      } else {
        activeProduct.value = null
      }
    } catch (err) {
      console.error('Failed to fetch active product:', err)
      activeProduct.value = null
    }
  }

  async function initializeFromStorage() {
    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) {
        return
      }

      try {
        const response = await api.setup.status()
        const setupStatus = response.data

        if (setupStatus.default_password_active || !setupStatus.database_initialized) {
          localStorage.removeItem('currentProductId')
          return
        }
      } catch (error) {
        console.warn(
          '[PRODUCTS] Setup status check failed - skipping product initialization:',
          error,
        )
        return
      }

      await fetchProducts()

      const storedProductId = localStorage.getItem('currentProductId')
      if (storedProductId && products.value.length > 0) {
        const product = products.value.find((p) => p.id === parseInt(storedProductId))
        if (product) {
          await setCurrentProduct(parseInt(storedProductId))
        } else {
          localStorage.removeItem('currentProductId')
          await setCurrentProduct(products.value[0].id)
        }
      } else if (products.value.length > 0) {
        await setCurrentProduct(products.value[0].id)
      }

      await fetchActiveProduct()
    } catch (error) {
      console.error('[PRODUCTS] Failed to initialize from storage:', error)
    }
  }

  function clearProductData() {
    products.value = []
    currentProductId.value = null
    currentProduct.value = null
    productMetrics.value = {}
    activeProduct.value = null
    localStorage.removeItem('currentProductId')
  }

  // ============================================
  // WEBSOCKET EVENT HANDLERS (Handover 0139b)
  // ============================================

  /**
   * Handle product:memory:updated event
   * Updates product memory when backend emits changes
   */
  function handleProductMemoryUpdated(payload) {
    if (!payload?.product_id) {
      console.warn('[PRODUCTS] product:memory:updated missing product_id', payload)
      return
    }

    const product = products.value.find((p) => p.id === payload.product_id)
    const nextMemory = payload.product_memory || payload.data?.product_memory

    if (product && nextMemory) {
      // Update product memory
      product.product_memory = nextMemory

      // Also update currentProduct if it matches
      if (currentProduct.value?.id === payload.product_id) {
        currentProduct.value.product_memory = nextMemory
      }

    }
  }

  /**
   * Handle product:learning:added event
   * Appends new learning to sequential_history
   */
  function handleProductLearningAdded(payload) {
    if (!payload?.product_id) {
      console.warn('[PRODUCTS] product:learning:added missing product_id', payload)
      return
    }

    const product = products.value.find((p) => p.id === payload.product_id)
    const learning = payload.learning || payload.data?.learning

    if (product && learning) {
      // Initialize sequential_history if missing
      if (!product.product_memory) {
        product.product_memory = {}
      }
      if (!product.product_memory.sequential_history) {
        product.product_memory.sequential_history = []
      }

      // Append new learning
      product.product_memory.sequential_history.push(learning)

      // Also update currentProduct if it matches
      if (currentProduct.value?.id === payload.product_id) {
        if (!currentProduct.value.product_memory) {
          currentProduct.value.product_memory = {}
        }
        if (!currentProduct.value.product_memory.sequential_history) {
          currentProduct.value.product_memory.sequential_history = []
        }
        currentProduct.value.product_memory.sequential_history.push(learning)
      }

    }
  }

  /**
   * Handle product status change events by refreshing the active product.
   */
  async function handleProductStatusChanged() {
    try {
      await fetchActiveProduct()
    } catch (e) {
      console.warn('[PRODUCTS] Failed to refresh active product on WS event:', e)
    }
  }

  return {
    // State
    products,
    currentProductId,
    currentProduct,
    loading,
    error,
    productMetrics,
    activeProduct,

    // Getters
    hasProducts,
    productCount,
    effectiveProductId,

    // Actions
    fetchProducts,
    fetchProductById,
    setCurrentProduct,
    fetchProductMetrics,
    createProduct,
    updateProduct,
    deleteProduct,
    fetchActiveProduct,
    initializeFromStorage,
    clearProductData,

    // WebSocket router handlers (0379a)
    handleProductMemoryUpdated,
    handleProductLearningAdded,
    handleProductStatusChanged,
  }
})
