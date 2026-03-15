import { ref, computed } from 'vue'
import api from '@/services/api'

/**
 * Composable for managing field priority/toggle configuration.
 * Controls which fields are visible and their priority in product forms.
 */
export function useFieldPriority() {
  const fieldConfig = ref({})
  const loading = ref(false)
  const error = ref(null)

  function getFieldPriority(fieldName) {
    const config = fieldConfig.value?.priorities || {}
    if (typeof config[fieldName] === 'boolean') {
      return config[fieldName] ? 'normal' : 'hidden'
    }
    if (typeof config[fieldName] === 'object' && config[fieldName] !== null) {
      return config[fieldName].toggle ? 'normal' : 'hidden'
    }
    return 'normal'
  }

  function isFieldHidden(fieldName) {
    return getFieldPriority(fieldName) === 'hidden'
  }

  function isFieldRequired(fieldName) {
    return getFieldPriority(fieldName) === 'required'
  }

  function isFieldOptional(fieldName) {
    return !isFieldHidden(fieldName) && !isFieldRequired(fieldName)
  }

  async function loadConfig() {
    loading.value = true
    error.value = null
    try {
      const response = await api.users.getFieldToggleConfig()
      fieldConfig.value = response.data || {}
    } catch (err) {
      error.value = err
    } finally {
      loading.value = false
    }
  }

  return {
    fieldConfig,
    loading,
    error,
    getFieldPriority,
    isFieldHidden,
    isFieldRequired,
    isFieldOptional,
    loadConfig,
  }
}
