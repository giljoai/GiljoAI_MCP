import { ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/services/api'
import { useProductStore } from '@/stores/products'
import { useToast } from '@/composables/useToast'

export function useProductActivation(loadProducts) {
  const productStore = useProductStore()
  const { showToast } = useToast()
  const router = useRouter()

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
        await productStore.setCurrentProduct(product.id)

        showToast({
          message: `${product.name} activated`,
          type: 'success',
          timeout: 3000,
        })

        await loadProducts()
        // Activation is the universal entry point to per-product onboarding:
        // route to /home so the user sees New Project + bootstrap cards
        // (when applicable -- gated by Product.first_project_created_at).
        router.push('/home')
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
      await productStore.setCurrentProduct(pendingActivation.value.id)

      showToast({
        message: `${pendingActivation.value?.name} activated`,
        type: 'success',
        timeout: 3000,
      })

      await loadProducts()

      showActivationWarning.value = false
      pendingActivation.value = null
      currentActiveProduct.value = null

      // Same destination as the no-confirmation activation path.
      router.push('/home')
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
