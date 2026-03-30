/**
 * Composable for field priority display in ProductForm.
 *
 * Fetches the user's field toggle configuration from the backend
 * and provides lookup functions for displaying priority indicators
 * on product form fields.
 *
 * Post-0820: The backend uses a toggle-only system (v3.0).
 * Fields are either "Included" (enabled) or "Excluded" (disabled)
 * in the orchestrator context. There are no priority levels.
 *
 * Related:
 *   - Handover 0820: Remove Context Priority Framing
 *   - src/giljo_mcp/config/defaults.py: DEFAULT_FIELD_PRIORITY
 *   - api/endpoints/users.py: field-priority endpoints
 *   - components/settings/ContextPriorityConfig.vue: Settings UI
 */

import { ref, onMounted } from 'vue'
import api from '@/services/api'

/**
 * Maps product form field paths to backend category keys.
 *
 * ProductForm uses dotted field paths (e.g. 'tech_stack.languages'),
 * while the backend stores toggles per category (e.g. 'tech_stack').
 * This map resolves the first segment of each field path to the
 * corresponding backend category.
 */
const FIELD_TO_CATEGORY_MAP = {
  features: 'product_core',
  tech_stack: 'tech_stack',
  architecture: 'architecture',
  test_config: 'testing',
}

export function useFieldPriority() {
  const priorities = ref({})
  const loaded = ref(false)

  /**
   * Fetch the user's field priority config from the backend.
   * Silently defaults to empty on error (all fields show no priority chip).
   */
  async function fetchPriorities() {
    try {
      const response = await api.users.getFieldToggleConfig()
      const data = response?.data?.priorities || {}

      // Normalize v3.0 format: { category: { toggle: true } } -> { category: true }
      const normalized = {}
      for (const [key, value] of Object.entries(data)) {
        if (typeof value === 'object' && value !== null && 'toggle' in value) {
          normalized[key] = value.toggle
        } else if (typeof value === 'boolean') {
          normalized[key] = value
        } else {
          normalized[key] = true
        }
      }

      priorities.value = normalized
      loaded.value = true
    } catch {
      // Silently fail -- fields will show no priority chips
      priorities.value = {}
      loaded.value = true
    }
  }

  /**
   * Get the toggle state for a product form field.
   *
   * @param {string} fieldPath - Dotted field path (e.g. 'tech_stack.languages')
   * @returns {boolean|null} true if included, false if excluded, null if unknown
   */
  function getPriorityForField(fieldPath) {
    if (!loaded.value) return null

    const category = FIELD_TO_CATEGORY_MAP[fieldPath.split('.')[0]]
    if (!category) return null

    const toggle = priorities.value[category]
    if (toggle === undefined) return null

    return toggle
  }

  /**
   * Get a display label for a priority/toggle value.
   *
   * @param {boolean|null} priority - Toggle state from getPriorityForField
   * @returns {string} Human-readable label
   */
  function getPriorityLabel(priority) {
    if (priority === true) return 'Included'
    if (priority === false) return 'Excluded'
    return ''
  }

  /**
   * Get a Vuetify color for a priority/toggle value.
   *
   * @param {boolean|null} priority - Toggle state from getPriorityForField
   * @returns {string} Vuetify color name
   */
  function getPriorityColor(priority) {
    if (priority === true) return 'success'
    if (priority === false) return 'grey'
    return 'default'
  }

  onMounted(() => {
    fetchPriorities()
  })

  return {
    getPriorityForField,
    getPriorityLabel,
    getPriorityColor,
    fetchPriorities,
    loaded,
  }
}
