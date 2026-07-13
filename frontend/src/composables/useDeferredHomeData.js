/**
 * useDeferredHomeData (FE-6059) — defer Home/Welcome's Tools-domain reads off the
 * cold first paint.
 *
 * The agent-templates list ("Your Team" section) and git/serena integration
 * status (onboarding-reminder copy) are only needed once their section actually
 * renders. This composable fetches each lazily the first time its gate turns
 * true, instead of firing /api/v1/templates/, templates/stats/active-count,
 * /api/git/settings and /api/serena/status unconditionally on mount. Extracted
 * from WelcomeView so the orchestration lives in one cohesive place.
 *
 * @param {Object} deps
 * @param {import('vue').Ref<boolean>} deps.onboardingComplete - gates the team-templates load.
 * @param {import('vue').Ref<boolean>} deps.showIntegReminder - gates the integration-status load.
 * @param {import('vue').Ref<Array>} deps.templates - destination ref for the templates list.
 * @param {import('vue').Ref<number>} deps.totalSlots - destination ref for the active-count max_slots.
 * @returns {{ gitEnabled: import('vue').Ref<boolean>, serenaEnabled: import('vue').Ref<boolean> }}
 */
import { watch } from 'vue'
import api from '@/services/api'
import { useIntegrationStatus } from '@/composables/useIntegrationStatus'

export function useDeferredHomeData({ onboardingComplete, showIntegReminder, templates, totalSlots }) {
  const { gitEnabled, serenaEnabled, refresh: refreshIntegrationStatus } = useIntegrationStatus({
    immediate: false,
  })

  let teamTemplatesLoaded = false
  async function loadTeamTemplates() {
    if (teamTemplatesLoaded) return
    teamTemplatesLoaded = true
    await Promise.allSettled([
      api.templates
        .list()
        .then((response) => {
          templates.value = response.data || []
        })
        .catch(() => {}),
      api.templates
        .activeCount()
        .then((response) => {
          if (response.data?.max_slots) {
            totalSlots.value = response.data.max_slots
          }
        })
        .catch(() => {}),
    ])
  }

  let integrationStatusLoaded = false
  function loadIntegrationStatusOnce() {
    if (integrationStatusLoaded) return
    integrationStatusLoaded = true
    refreshIntegrationStatus()
  }

  watch(onboardingComplete, (ready) => { if (ready) loadTeamTemplates() }, { immediate: true })
  watch(showIntegReminder, (show) => { if (show) loadIntegrationStatusOnce() }, { immediate: true })

  return { gitEnabled, serenaEnabled }
}
