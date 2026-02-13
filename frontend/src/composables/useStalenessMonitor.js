/**
 * Staleness Monitoring Composable
 * Handover 0234: Agent Status Enhancements - Phase 4
 * Handover 0491: Updated to work with `silent` status model
 *
 * Monitors job staleness and emits warnings when jobs become stale.
 * The backend now handles the actual status transition to "silent" via
 * the agent health monitor. This composable provides client-side
 * awareness by:
 *   1. Detecting stale agents locally (using isJobStale from statusConfig)
 *   2. Reacting to "silent" status received via WebSocket events
 *   3. Emitting notifications when agents go silent
 *
 * Uses a state tracking flag (_wasStale) to prevent duplicate warnings.
 */

import { ref, onMounted, onUnmounted, watch } from 'vue'
import { isJobStale } from '@/utils/statusConfig'
import { useNotificationStore } from '@/stores/notifications'

/**
 * Monitor job staleness and emit warnings
 *
 * @param {Ref<Array>} jobs - Reactive array of job objects
 * @param {Function} [emitStaleWarning] - Optional callback to emit stale warning (for backward compatibility)
 * @returns {Object} - { checkStaleness } for manual triggering
 */
export function useStalenessMonitor(jobs, emitStaleWarning = null) {
  const stalenessCheckInterval = ref(null)
  const notificationStore = useNotificationStore()

  /**
   * Check all jobs for staleness and emit warnings for newly stale jobs.
   * Also detects agents that transitioned to "silent" status via backend.
   * Uses _wasStale flag to track previous staleness state and prevent duplicate warnings.
   */
  const checkStaleness = () => {
    jobs.value.forEach((job) => {
      const wasStale = job._wasStale || false
      const wasSilent = job._wasSilent || false

      // Check if backend has marked the agent as silent
      const isSilent = job.status === 'silent'

      // Notify on transition to silent status (backend-driven)
      if (isSilent && !wasSilent) {
        if (emitStaleWarning) {
          emitStaleWarning(job)
        } else {
          notificationStore.addNotification({
            type: 'agent_health',
            title: 'Agent Silent',
            message: `${job.agent_name || job.agent_display_name} has stopped communicating`,
            metadata: {
              job_id: job.job_id,
              agent_display_name: job.agent_display_name,
            },
          })
        }
      }

      // Client-side staleness detection (pre-backend transition)
      const isStale = isJobStale(job.last_progress_at, job.status)

      if (isStale && !wasStale && !isSilent) {
        if (emitStaleWarning) {
          emitStaleWarning(job)
        } else {
          notificationStore.addNotification({
            type: 'agent_health',
            title: 'Agent Inactive',
            message: `${job.agent_name || job.agent_display_name} has been inactive for over 10 minutes`,
            metadata: {
              job_id: job.job_id,
              agent_display_name: job.agent_display_name,
            },
          })
        }
      }

      // Track state to prevent duplicate notifications
      job._wasStale = isStale
      job._wasSilent = isSilent
    })
  }

  // Watch for status changes to detect backend-driven silent transitions
  watch(
    () => jobs.value.map((j) => j.status),
    () => {
      checkStaleness()
    },
    { deep: true },
  )

  onMounted(() => {
    // Check every 30 seconds
    stalenessCheckInterval.value = setInterval(checkStaleness, 30000)
  })

  onUnmounted(() => {
    if (stalenessCheckInterval.value) {
      clearInterval(stalenessCheckInterval.value)
      stalenessCheckInterval.value = null
    }
  })

  return {
    checkStaleness,
  }
}
