/**
 * Integration Status Composable (Handover 0427)
 *
 * Fetches and manages Git and Serena MCP integration status.
 * Used to display integration status icons in the UI.
 */

import { ref, onMounted } from 'vue'
import setupService from '@/services/setupService'

/**
 * @param {Object} [options]
 * @param {boolean} [options.immediate=true] - fetch git/serena status on mount.
 *   Pass `false` to defer the fetch (FE-6059): callers that only show
 *   integration status conditionally (e.g. Home's onboarding reminder) can
 *   invoke the returned `refresh()` when the consuming UI actually renders,
 *   keeping /api/git/settings + /api/serena/status off the cold first paint.
 */
export function useIntegrationStatus({ immediate = true } = {}) {
  const gitEnabled = ref(false)
  const serenaEnabled = ref(false)
  const loading = ref(immediate)

  async function loadStatus() {
    loading.value = true
    try {
      const [gitSettings, serenaStatus] = await Promise.all([
        setupService.getGitSettings(),
        setupService.getSerenaStatus(),
      ])
      gitEnabled.value = gitSettings.enabled || false
      serenaEnabled.value = serenaStatus.enabled || false
    } catch (error) {
      console.error('[useIntegrationStatus] Failed to load:', error)
      // Keep defaults (false) on error
    } finally {
      loading.value = false
    }
  }

  if (immediate) {
    onMounted(loadStatus)
  }

  return { gitEnabled, serenaEnabled, loading, refresh: loadStatus }
}
