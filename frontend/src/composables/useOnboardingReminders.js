import { ref, computed } from 'vue'

/**
 * Manages onboarding reminder banners on the dashboard.
 *
 * Integration reminder:
 *   - Appears after the user creates their first project.
 *   - If dismissed, re-appears after 2 days (once).
 *   - Never appears again after the second dismissal.
 *
 * Agent/context reminder:
 *   - Appears after the user's first project completes.
 *   - Shows once, never again after dismissal.
 */

const LS_INTEG_COUNT = 'giljo_onboard_integ_count'
const LS_INTEG_DISMISSED_AT = 'giljo_onboard_integ_dismissed_at'
const LS_AGENT_DISMISSED = 'giljo_onboard_agent_dismissed'

const TWO_DAYS_MS = 2 * 24 * 60 * 60 * 1000

function readInt(key, fallback = 0) {
  const v = localStorage.getItem(key)
  return v !== null ? parseInt(v, 10) : fallback
}

export function useOnboardingReminders() {
  const integDismissCount = ref(readInt(LS_INTEG_COUNT, 0))
  const integDismissedAt = ref(localStorage.getItem(LS_INTEG_DISMISSED_AT) || null)
  const agentDismissed = ref(localStorage.getItem(LS_AGENT_DISMISSED) === 'true')

  /**
   * Whether the integration reminder should display.
   * @param {boolean} hasProjects - true if the user has at least one project
   */
  const showIntegrationReminder = computed(() => {
    return (hasProjects) => {
      if (!hasProjects) return false
      if (integDismissCount.value >= 2) return false
      if (integDismissCount.value === 0) return true
      // Dismissed once — check if 2 days have passed
      if (integDismissedAt.value) {
        const elapsed = Date.now() - new Date(integDismissedAt.value).getTime()
        return elapsed >= TWO_DAYS_MS
      }
      return false
    }
  })

  /**
   * Whether the agent/context reminder should display.
   * @param {boolean} hasCompletedProject - true if user has a completed project
   */
  const showAgentReminder = computed(() => {
    return (hasCompletedProject) => {
      if (!hasCompletedProject) return false
      return !agentDismissed.value
    }
  })

  function dismissIntegrationReminder() {
    integDismissCount.value += 1
    integDismissedAt.value = new Date().toISOString()
    localStorage.setItem(LS_INTEG_COUNT, String(integDismissCount.value))
    localStorage.setItem(LS_INTEG_DISMISSED_AT, integDismissedAt.value)
  }

  function dismissAgentReminder() {
    agentDismissed.value = true
    localStorage.setItem(LS_AGENT_DISMISSED, 'true')
  }

  return {
    showIntegrationReminder,
    showAgentReminder,
    dismissIntegrationReminder,
    dismissAgentReminder,
  }
}
