/**
 * useSkillsVersion Composable
 *
 * Compares the local skills_version (from last giljo_setup run, stored in localStorage)
 * against the server's skills_version from the health endpoint.
 *
 * When outdated, surfaces a non-blocking notification badge in the nav.
 * Users can dismiss the notification per-version.
 *
 * Edition Scope: CE
 */
import { ref, computed } from 'vue'
import api from '@/services/api'

const STORAGE_KEY_LOCAL = 'giljo_skills_version'
const STORAGE_KEY_DISMISSED = 'giljo_skills_dismissed_version'

export function useSkillsVersion() {
  const localVersion = ref(localStorage.getItem(STORAGE_KEY_LOCAL) || null)
  const serverVersion = ref(null)
  const hasChecked = ref(false)

  const dismissedVersion = ref(localStorage.getItem(STORAGE_KEY_DISMISSED) || null)
  const isDismissed = ref(false)

  const isOutdated = computed(() => {
    if (!hasChecked.value || !serverVersion.value) return false
    // If local version is null (never ran setup) or different from server, it is outdated
    return localVersion.value !== serverVersion.value
  })

  const showBadge = computed(() => {
    if (!isOutdated.value) return false
    // If user dismissed this specific server version, do not show
    return dismissedVersion.value !== serverVersion.value
  })

  async function checkServerVersion() {
    try {
      const response = await api.health.check()
      const data = response.data || {}
      if (data.skills_version) {
        serverVersion.value = data.skills_version
        hasChecked.value = true
      }
    } catch {
      // Silently fail -- health check is non-critical for UX
    }
  }

  function dismiss(version) {
    const ver = version || serverVersion.value
    if (ver) {
      dismissedVersion.value = ver
      isDismissed.value = true
      localStorage.setItem(STORAGE_KEY_DISMISSED, ver)
    }
  }

  function updateLocalVersion(version) {
    localVersion.value = version
    localStorage.setItem(STORAGE_KEY_LOCAL, version)
  }

  return {
    localVersion,
    serverVersion,
    hasChecked,
    isOutdated,
    isDismissed,
    showBadge,
    checkServerVersion,
    dismiss,
    updateLocalVersion,
  }
}
