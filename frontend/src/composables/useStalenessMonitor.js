/**
 * Staleness Monitoring Composable
 * Handover 0234: Agent Status Enhancements - Phase 4
 *
 * Monitors job staleness and emits warnings when jobs become stale.
 * Uses a state tracking flag (_wasStale) to prevent duplicate warnings.
 */

import { ref, onMounted, onUnmounted } from 'vue'
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
   * Check all jobs for staleness and emit warnings for newly stale jobs
   * Uses _wasStale flag to track previous staleness state and prevent duplicate warnings
   */
  const checkStaleness = () => {
    jobs.value.forEach((job) => {
      const wasStale = job._wasStale || false
      const isStale = isJobStale(job.last_progress_at, job.status)

      // Emit warning if job became stale (transition from fresh to stale)
      if (isStale && !wasStale) {
        if (emitStaleWarning) {
          // Use callback if provided (backward compatibility)
          emitStaleWarning(job)
        } else {
          // Use notification store
          notificationStore.addNotification({
            type: 'agent_health',
            title: 'Agent Inactive',
            message: `${job.agent_name || job.agent_display_name} has been inactive for over 10 minutes`,
            metadata: {
              job_id: job.job_id,
              agent_display_name: job.agent_display_name
            }
          })
        }
      }

      // Track staleness state (mutate job object for state tracking)
      job._wasStale = isStale
    })
  }

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
