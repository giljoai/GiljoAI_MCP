import { ref } from 'vue'
import api from '@/services/api'
import { useProductStore } from '@/stores/products'
import { useToast } from '@/composables/useToast'

export function useProductActivation(loadProducts) {
  const productStore = useProductStore()
  const { showToast } = useToast()

  const showActivationWarning = ref(false)
  const pendingActivation = ref(null)
  const currentActiveProduct = ref(null)

  async function toggleProductActivation(product) {
    try {
      if (productStore.activeProduct?.id === product.id) {
        await api.products.deactivate(product.id)
        await productStore.fetchActiveProduct()

        showToast({
          message: `${product.name} deactivated`,
          type: 'info',
          timeout: 3000,
        })

        await loadProducts()
      } else {
        const currentActive = productStore.activeProduct

        if (currentActive && currentActive.id !== product.id) {
          currentActiveProduct.value = currentActive
          pendingActivation.value = product
          showActivationWarning.value = true
          return
        }

        await api.products.activate(product.id)
        await productStore.fetchActiveProduct()

        showToast({
          message: `${product.name} activated`,
          type: 'success',
          timeout: 3000,
        })

        await loadProducts()
      }
    } catch (error) {
      console.error('Failed to toggle product activation:', error)
      showToast({
        message: 'Failed to change product status. Try again or refresh the page.',
        type: 'error',
        timeout: 5000,
      })
    }
  }

  async function confirmActivation() {
    try {
      await api.products.activate(pendingActivation.value.id)
      await productStore.fetchActiveProduct()

      showToast({
        message: `${pendingActivation.value?.name} activated`,
        type: 'success',
        timeout: 3000,
      })

      await loadProducts()

      showActivationWarning.value = false
      pendingActivation.value = null
      currentActiveProduct.value = null
    } catch (error) {
      console.error('Failed to confirm activation:', error)
      showToast({
        message: 'Failed to activate product. Try again or refresh the page.',
        type: 'error',
        timeout: 5000,
      })
    }
  }

  function cancelActivation() {
    showActivationWarning.value = false
    pendingActivation.value = null
    currentActiveProduct.value = null
  }

  return {
    showActivationWarning,
    pendingActivation,
    currentActiveProduct,
    toggleProductActivation,
    confirmActivation,
    cancelActivation,
  }
}
