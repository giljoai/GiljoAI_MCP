import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'

export const useProductStore = defineStore('products', () => {
  // State
  const products = ref([])
  const currentProductId = ref(null)
  const currentProduct = ref(null)
  const loading = ref(false)
  const error = ref(null)
  const productMetrics = ref({})

  // Getters
  const hasProducts = computed(() => products.value.length > 0)
  const productCount = computed(() => products.value.length)
  const isProductSelected = computed(() => currentProductId.value !== null)

  const currentProductName = computed(() => {
    return currentProduct.value?.name || 'No Product Selected'
  })

  const currentProductMetrics = computed(() => {
    if (!currentProductId.value) {
      return null
    }
    return (
      productMetrics.value[currentProductId.value] || {
        totalTasks: 0,
        completedTasks: 0,
        activeAgents: 0,
        totalProjects: 0,
      }
    )
  })

  // Actions
  async function fetchProducts() {
    loading.value = true
    error.value = null
    try {
      // This will be connected to the API endpoint when implementer creates it
      // For now, using placeholder logic
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
      // This will be connected to the API endpoint when implementer creates it
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
    if (productId === currentProductId.value) {
      return
    }

    // If no products exist, do nothing
    await fetchProducts()
    if (products.value.length === 0) {
      console.warn('No products available to set as current product')
      return
    }

    // Validate the product ID
    const product = await fetchProductById(productId)
    if (!product) {
      console.warn(`Product ${productId} not found`)

      // If the requested product doesn't exist, set the first available product
      if (products.value.length > 0) {
        productId = products.value[0].id
      } else {
        // Clear current product if no products exist
        currentProductId.value = null
        currentProduct.value = null
        localStorage.removeItem('currentProductId')
        return
      }
    }

    currentProductId.value = productId
    currentProduct.value = product

    // Store in localStorage for persistence
    localStorage.setItem('currentProductId', productId)

    // Fetch metrics for this product
    await fetchProductMetrics(productId)

    // Emit event for other stores to react
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
      // This will be connected to the API endpoint when implementer creates it
      // For now, using placeholder logic
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
      // This will be connected to the API endpoint when implementer creates it
      const response = (await api.products?.create(productData)) || { data: null }
      if (response.data) {
        products.value.push(response.data)
        // Automatically switch to new product
        await setCurrentProduct(response.data.id)
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
      // This will be connected to the API endpoint when implementer creates it
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
    error.value = null
    try {
      // This will be connected to the API endpoint when implementer creates it
      await api.products?.delete(productId)
      products.value = products.value.filter((p) => p.id !== productId)

      if (productId === currentProductId.value) {
        // Clear current product if it was deleted
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

  // Initialize from localStorage
  async function initializeFromStorage() {
    try {
      // CRITICAL: Check setup status before attempting to fetch products
      // During setup flow (password change or wizard), skip product initialization
      const setupResponse = await fetch('/api/setup/status')
      if (setupResponse.ok) {
        const setupStatus = await setupResponse.json()

        // Skip product fetch during:
        // 1. Password change phase (default_password_active=True)
        // 2. Setup wizard phase (completed=False)
        if (setupStatus.default_password_active || !setupStatus.completed) {
          console.log('[PRODUCTS] Skipping product initialization during setup flow')
          localStorage.removeItem('currentProductId')
          return
        }
      }
    } catch (error) {
      console.warn('[PRODUCTS] Failed to check setup status, skipping product initialization:', error)
      return
    }

    const storedProductId = localStorage.getItem('currentProductId')

    // First, check if any products exist
    await fetchProducts()

    // If no products exist, clear localStorage and do nothing
    if (products.value.length === 0) {
      localStorage.removeItem('currentProductId')
      return
    }

    // If a stored product ID exists and there are products, try to set it
    if (storedProductId) {
      const product = await fetchProductById(storedProductId)
      if (product) {
        await setCurrentProduct(storedProductId)
      } else {
        // If the specific product doesn't exist, clear localStorage and optionally set first product
        localStorage.removeItem('currentProductId')
        if (products.value.length > 0) {
          await setCurrentProduct(products.value[0].id)
        }
      }
    } else if (products.value.length > 0) {
      // If no stored product but products exist, set the first product
      await setCurrentProduct(products.value[0].id)
    }
  }

  // Clear all product data
  function clearProductData() {
    products.value = []
    currentProductId.value = null
    currentProduct.value = null
    productMetrics.value = {}
    localStorage.removeItem('currentProductId')
  }

  return {
    // State
    products,
    currentProductId,
    currentProduct,
    loading,
    error,
    productMetrics,

    // Getters
    hasProducts,
    productCount,
    isProductSelected,
    currentProductName,
    currentProductMetrics,

    // Actions
    fetchProducts,
    fetchProductById,
    setCurrentProduct,
    fetchProductMetrics,
    createProduct,
    updateProduct,
    deleteProduct,
    initializeFromStorage,
    clearProductData,
  }
})
