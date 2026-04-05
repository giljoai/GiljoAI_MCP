import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useProductActivation } from './useProductActivation'
import api from '@/services/api'

describe('useProductActivation', () => {
  let loadProducts

  beforeEach(() => {
    setActivePinia(createPinia())
    loadProducts = vi.fn(() => Promise.resolve())
    vi.clearAllMocks()
  })

  it('initializes with empty activation state', () => {
    const { showActivationWarning, pendingActivation, currentActiveProduct } =
      useProductActivation(loadProducts)

    expect(showActivationWarning.value).toBe(false)
    expect(pendingActivation.value).toBeNull()
    expect(currentActiveProduct.value).toBeNull()
  })

  it('cancelActivation resets all activation state', () => {
    const { showActivationWarning, pendingActivation, currentActiveProduct, cancelActivation } =
      useProductActivation(loadProducts)

    showActivationWarning.value = true
    pendingActivation.value = { id: 'prod-1', name: 'Product 1' }
    currentActiveProduct.value = { id: 'prod-2', name: 'Product 2' }

    cancelActivation()

    expect(showActivationWarning.value).toBe(false)
    expect(pendingActivation.value).toBeNull()
    expect(currentActiveProduct.value).toBeNull()
  })

  it('toggleProductActivation deactivates an already-active product', async () => {
    const { toggleProductActivation } = useProductActivation(loadProducts)

    const { useProductStore } = await import('@/stores/products')
    const productStore = useProductStore()
    productStore.activeProduct = { id: 'prod-1', name: 'Active Product' }

    api.products.deactivate.mockResolvedValue({ data: { success: true } })
    api.products.getActive = vi.fn(() => Promise.resolve({ data: null }))

    await toggleProductActivation({ id: 'prod-1', name: 'Active Product' })

    expect(api.products.deactivate).toHaveBeenCalledWith('prod-1')
    expect(loadProducts).toHaveBeenCalled()
  })

  it('toggleProductActivation activates a product when no product is currently active', async () => {
    const { toggleProductActivation } = useProductActivation(loadProducts)

    const { useProductStore } = await import('@/stores/products')
    const productStore = useProductStore()
    productStore.activeProduct = null

    api.products.activate.mockResolvedValue({ data: { success: true } })

    await toggleProductActivation({ id: 'prod-2', name: 'New Product' })

    expect(api.products.activate).toHaveBeenCalledWith('prod-2')
    expect(loadProducts).toHaveBeenCalled()
  })

  it('toggleProductActivation shows warning when switching from one active product to another', async () => {
    const { toggleProductActivation, showActivationWarning, pendingActivation, currentActiveProduct } =
      useProductActivation(loadProducts)

    const { useProductStore } = await import('@/stores/products')
    const productStore = useProductStore()
    productStore.activeProduct = { id: 'prod-1', name: 'Currently Active' }

    await toggleProductActivation({ id: 'prod-2', name: 'New Product' })

    expect(showActivationWarning.value).toBe(true)
    expect(pendingActivation.value).toEqual({ id: 'prod-2', name: 'New Product' })
    expect(currentActiveProduct.value).toEqual({ id: 'prod-1', name: 'Currently Active' })
    expect(api.products.activate).not.toHaveBeenCalled()
    expect(loadProducts).not.toHaveBeenCalled()
  })

  it('confirmActivation activates pending product and resets dialog state', async () => {
    const { confirmActivation, showActivationWarning, pendingActivation, currentActiveProduct } =
      useProductActivation(loadProducts)

    pendingActivation.value = { id: 'prod-2', name: 'New Product' }
    currentActiveProduct.value = { id: 'prod-1', name: 'Old Product' }
    showActivationWarning.value = true

    api.products.activate.mockResolvedValue({ data: { success: true } })

    await confirmActivation()

    expect(api.products.activate).toHaveBeenCalledWith('prod-2')
    expect(loadProducts).toHaveBeenCalled()
    expect(showActivationWarning.value).toBe(false)
    expect(pendingActivation.value).toBeNull()
    expect(currentActiveProduct.value).toBeNull()
  })

  it('confirmActivation does not throw on API failure', async () => {
    const { confirmActivation, showActivationWarning, pendingActivation } =
      useProductActivation(loadProducts)

    pendingActivation.value = { id: 'prod-2', name: 'New Product' }
    showActivationWarning.value = true

    api.products.activate.mockRejectedValue(new Error('Network error'))

    await expect(confirmActivation()).resolves.toBeUndefined()
    expect(loadProducts).not.toHaveBeenCalled()
  })

  it('toggleProductActivation does not throw on API failure', async () => {
    const { toggleProductActivation } = useProductActivation(loadProducts)

    const { useProductStore } = await import('@/stores/products')
    const productStore = useProductStore()
    productStore.activeProduct = null

    api.products.activate.mockRejectedValue(new Error('Network error'))

    await expect(toggleProductActivation({ id: 'prod-2', name: 'Product' })).resolves.toBeUndefined()
    expect(loadProducts).not.toHaveBeenCalled()
  })
})
