/**
 * Integration Status Composable (Handover 0427)
 *
 * Fetches and manages GitHub and Serena MCP integration status.
 * Used to display integration status icons in the UI.
 */

import { ref, onMounted } from 'vue'
import setupService from '@/services/setupService'

export function useIntegrationStatus() {
  const gitEnabled = ref(false)
  const serenaEnabled = ref(false)
  const loading = ref(true)

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

  onMounted(loadStatus)

  return { gitEnabled, serenaEnabled, loading, refresh: loadStatus }
}
