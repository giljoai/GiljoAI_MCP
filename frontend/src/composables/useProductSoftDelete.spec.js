import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useProductSoftDelete } from './useProductSoftDelete'
import api from '@/services/api'

describe('useProductSoftDelete', () => {
  let loadProducts

  beforeEach(() => {
    setActivePinia(createPinia())
    loadProducts = vi.fn(() => Promise.resolve())
    vi.clearAllMocks()
    api.products.purge = vi.fn(() => Promise.resolve({ data: { success: true } }))
  })

  it('initializes with empty state', () => {
    const {
      showDeletedProductsDialog,
      deletedProducts,
      restoringProductId,
      purgingProductId,
      purgingAllProducts,
    } = useProductSoftDelete(loadProducts)

    expect(showDeletedProductsDialog.value).toBe(false)
    expect(deletedProducts.value).toEqual([])
    expect(restoringProductId.value).toBeNull()
    expect(purgingProductId.value).toBeNull()
    expect(purgingAllProducts.value).toBe(false)
  })

  it('loadDeletedProducts populates deletedProducts from API', async () => {
    const { loadDeletedProducts, deletedProducts } = useProductSoftDelete(loadProducts)

    const mockDeleted = [
      { id: 'prod-1', name: 'Old Product' },
      { id: 'prod-2', name: 'Another Product' },
    ]
    api.products.getDeletedProducts.mockResolvedValue({ data: mockDeleted })

    await loadDeletedProducts()

    expect(deletedProducts.value).toEqual(mockDeleted)
  })

  it('loadDeletedProducts falls back to empty array on error', async () => {
    const { loadDeletedProducts, deletedProducts } = useProductSoftDelete(loadProducts)

    api.products.getDeletedProducts.mockRejectedValue(new Error('Network error'))

    await loadDeletedProducts()

    expect(deletedProducts.value).toEqual([])
  })

  it('restoreProduct calls API and reloads products', async () => {
    const { restoreProduct, deletedProducts } = useProductSoftDelete(loadProducts)

    deletedProducts.value = [{ id: 'prod-1', name: 'Deleted Product' }]

    api.products.restoreProduct.mockResolvedValue({ data: { success: true } })
    api.products.getDeletedProducts.mockResolvedValue({ data: [] })

    await restoreProduct('prod-1')

    expect(api.products.restoreProduct).toHaveBeenCalledWith('prod-1')
    expect(loadProducts).toHaveBeenCalled()
  })

  it('restoreProduct closes dialog when no more deleted products remain', async () => {
    const { restoreProduct, deletedProducts, showDeletedProductsDialog } =
      useProductSoftDelete(loadProducts)

    deletedProducts.value = [{ id: 'prod-1', name: 'Deleted Product' }]
    showDeletedProductsDialog.value = true

    api.products.restoreProduct.mockResolvedValue({ data: { success: true } })
    api.products.getDeletedProducts.mockResolvedValue({ data: [] })

    await restoreProduct('prod-1')

    expect(showDeletedProductsDialog.value).toBe(false)
  })

  it('restoreProduct resets restoringProductId after completion', async () => {
    const { restoreProduct, restoringProductId, deletedProducts } =
      useProductSoftDelete(loadProducts)

    deletedProducts.value = [{ id: 'prod-1', name: 'Product' }]
    api.products.restoreProduct.mockResolvedValue({ data: { success: true } })
    api.products.getDeletedProducts.mockResolvedValue({ data: [] })

    await restoreProduct('prod-1')

    expect(restoringProductId.value).toBeNull()
  })

  it('restoreProduct does not call API if already restoring', async () => {
    const { restoreProduct, restoringProductId, deletedProducts } =
      useProductSoftDelete(loadProducts)

    deletedProducts.value = [{ id: 'prod-1', name: 'Product' }]
    restoringProductId.value = 'prod-1'

    await restoreProduct('prod-1')

    expect(api.products.restoreProduct).not.toHaveBeenCalled()
  })

  it('purgeDeletedProduct calls API and reloads products', async () => {
    const { purgeDeletedProduct, deletedProducts } = useProductSoftDelete(loadProducts)

    deletedProducts.value = [{ id: 'prod-1', name: 'Product' }]
    api.products.purge.mockResolvedValue({ data: { success: true } })
    api.products.getDeletedProducts.mockResolvedValue({ data: [] })

    await purgeDeletedProduct('prod-1')

    expect(api.products.purge).toHaveBeenCalledWith('prod-1')
    expect(loadProducts).toHaveBeenCalled()
  })

  it('purgeDeletedProduct does not call API if already purging', async () => {
    const { purgeDeletedProduct, purgingProductId, deletedProducts } =
      useProductSoftDelete(loadProducts)

    deletedProducts.value = [{ id: 'prod-1', name: 'Product' }]
    purgingProductId.value = 'prod-1'

    await purgeDeletedProduct('prod-1')

    expect(api.products.purge).not.toHaveBeenCalled()
  })

  it('purgeAllDeletedProducts purges each product in sequence', async () => {
    const { purgeAllDeletedProducts, deletedProducts } = useProductSoftDelete(loadProducts)

    deletedProducts.value = [
      { id: 'prod-1', name: 'First' },
      { id: 'prod-2', name: 'Second' },
    ]

    api.products.purge.mockResolvedValue({ data: { success: true } })
    api.products.getDeletedProducts.mockResolvedValue({ data: [] })

    await purgeAllDeletedProducts()

    expect(api.products.purge).toHaveBeenCalledTimes(2)
    expect(api.products.purge).toHaveBeenCalledWith('prod-1')
    expect(api.products.purge).toHaveBeenCalledWith('prod-2')
  })

  it('purgeAllDeletedProducts closes dialog after completion', async () => {
    const { purgeAllDeletedProducts, deletedProducts, showDeletedProductsDialog } =
      useProductSoftDelete(loadProducts)

    deletedProducts.value = [{ id: 'prod-1', name: 'Product' }]
    showDeletedProductsDialog.value = true

    api.products.purge.mockResolvedValue({ data: { success: true } })
    api.products.getDeletedProducts.mockResolvedValue({ data: [] })

    await purgeAllDeletedProducts()

    expect(showDeletedProductsDialog.value).toBe(false)
  })

  it('purgeAllDeletedProducts does not call API if already purging all', async () => {
    const { purgeAllDeletedProducts, purgingAllProducts } = useProductSoftDelete(loadProducts)

    purgingAllProducts.value = true

    await purgeAllDeletedProducts()

    expect(api.products.purge).not.toHaveBeenCalled()
  })
})
