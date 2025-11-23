/**
 * Field Priority Composable (Handover 0049)
 *
 * Provides helpers for displaying field priority badges and tooltips
 * in the Product edit forms.
 */

import { computed } from 'vue'
import { useSettingsStore } from '@/stores/settings'

export function useFieldPriority() {
  const settingsStore = useSettingsStore()

  /**
   * Get priority level for a field path
   * @param {string} fieldPath - Field path (e.g., 'tech_stack.languages')
   * @returns {number|null} - Priority level (1, 2, 3) or null if not prioritized
   */
  const getPriorityForField = (fieldPath) => {
    if (!settingsStore.fieldPriorityConfig) {
      return null
    }

    const config = settingsStore.fieldPriorityConfig

    // Check Priority 1
    if (config.priority_1?.includes(fieldPath)) {
      return 1
    }

    // Check Priority 2
    if (config.priority_2?.includes(fieldPath)) {
      return 2
    }

    // Check Priority 3
    if (config.priority_3?.includes(fieldPath)) {
      return 3
    }

    return null
  }

  /**
   * Get label text for priority badge
   * @param {number} priority - Priority level (1, 2, 3)
   * @returns {string|null} - Badge label or null
   */
  const getPriorityLabel = (priority) => {
    if (!priority) return null

    switch (priority) {
      case 1:
        return 'Priority 1'
      case 2:
        return 'Priority 2'
      case 3:
        return 'Priority 3'
      default:
        return null
    }
  }

  /**
   * Get Vuetify color for priority badge
   * @param {number} priority - Priority level (1, 2, 3)
   * @returns {string} - Vuetify color name
   */
  const getPriorityColor = (priority) => {
    if (!priority) return 'default'

    switch (priority) {
      case 1:
        return 'error' // Red - Always Included
      case 2:
        return 'warning' // Orange - High Priority
      case 3:
        return 'info' // Blue - Medium Priority
      default:
        return 'default'
    }
  }

  /**
   * Get tooltip content for priority badge
   * @param {number} priority - Priority level (1, 2, 3)
   * @returns {string|null} - Formatted tooltip text
   */
  const getPriorityTooltip = (priority) => {
    if (!priority) return null

    const descriptions = {
      1: 'Priority 1 - Always Included\nThis field is always sent to AI agents in missions.',
      2: 'Priority 2 - High Priority\nThis field is sent to AI agents if token budget allows.',
      3: 'Priority 3 - Medium Priority\nThis field is sent to AI agents if token budget allows.',
    }

    const desc = descriptions[priority]
    return desc
      ? `${desc}\n\nYou can change field priorities in:\nUser Settings → General → Field Priority Configuration`
      : null
  }

  /**
   * Check if field priority config is loaded
   */
  const isConfigLoaded = computed(() => {
    return settingsStore.fieldPriorityConfig !== null
  })

  return {
    getPriorityForField,
    getPriorityLabel,
    getPriorityColor,
    getPriorityTooltip,
    isConfigLoaded,
  }
}
