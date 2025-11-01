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
  const activeProduct = ref(null)
  const activeProductLoading = ref(false)

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
    if (productId === currentProductId.value) {
      return
    }

    await fetchProducts()
    if (products.value.length === 0) {
      console.warn('No products available to set as current product')
      return
    }

    const product = await fetchProductById(productId)
    if (!product) {
      console.warn(`Product ${productId} not found`)

      if (products.value.length > 0) {
        productId = products.value[0].id
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
    activeProductLoading.value = true
    error.value = null
    try {
      const response = await api.products.list({ is_active: true })
      if (response.data && response.data.length > 0) {
        activeProduct.value = response.data[0]
      } else {
        activeProduct.value = null
      }
    } catch (err) {
      error.value = err.message
      console.error('Failed to fetch active product:', err)
      activeProduct.value = null
    } finally {
      activeProductLoading.value = false
    }
  }

  async function initializeFromStorage() {
    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) {
        console.log('[PRODUCTS] No auth token - skipping product initialization')
        return
      }

      try {
        const response = await api.setup.status()
        const setupStatus = response.data

        if (setupStatus.default_password_active || !setupStatus.database_initialized) {
          console.log('[PRODUCTS] Setup incomplete - skipping product initialization')
          localStorage.removeItem('currentProductId')
          return
        }
      } catch (error) {
        console.warn('[PRODUCTS] Setup status check failed - skipping product initialization:', error)
        return
      }

      await fetchProducts()

      const storedProductId = localStorage.getItem('currentProductId')
      if (storedProductId && products.value.length > 0) {
        const product = products.value.find(p => p.id === parseInt(storedProductId))
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

  return {
    // State
    products,
    currentProductId,
    currentProduct,
    loading,
    error,
    productMetrics,
    activeProduct,
    activeProductLoading,

    // Getters
    hasProducts,
    productCount,
    isProductSelected,
    currentProductName,
    currentProductMetrics,
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
  }
})
