import { ref, computed, watch } from 'vue'
import api from '@/services/api'
import { useNotificationStore } from '@/stores/notifications'
import { useToast } from '@/composables/useToast'

/**
 * Manages the project closeout gate: detects when all agent jobs reach terminal
 * state, polls for 360 memory writes, and exposes the modal + guidance flags.
 *
 * @param {object} options
 * @param {import('vue').Ref}       options.project     - Reactive project object ref
 * @param {import('vue').ComputedRef} options.projectId  - Computed project ID string
 * @param {import('vue').ComputedRef} options.sortedJobs - Computed array of agent jobs
 * @param {Function} [options.onComplete]               - Called after closeout or continue
 * @returns Reactive state, computeds, and action methods
 */
export function useProjectCloseout({ project, projectId, sortedJobs, onComplete }) {
  const notificationStore = useNotificationStore()
  const { showToast } = useToast()

  const showCloseoutModal = ref(false)
  const memoryWritten = ref(false)
  const showContinueGuidance = ref(false)

  let memoryCheckTimeout = null

  const projectDoneStatus = computed(() => {
    const status = project.value?.status
    if (['completed', 'terminated', 'cancelled'].includes(status)) return status
    return null
  })

  const allJobsTerminal = computed(() => {
    if (['completed', 'terminated', 'cancelled'].includes(project.value?.status)) return false
    const jobs = sortedJobs.value || []
    if (!jobs.length) return false
    const isTerminal = (status) => status === 'complete' || status === 'completed' || status === 'decommissioned'
    const allTerminal = jobs.every((job) => isTerminal(job.status))
    if (!allTerminal) return false
    const orchestrator = jobs.find((job) => job.agent_display_name === 'orchestrator')
    return Boolean(orchestrator && isTerminal(orchestrator.status))
  })

  const showCloseoutButton = computed(() => {
    if (!allJobsTerminal.value) return false
    if (!project.value?.product_id) return true
    return memoryWritten.value
  })

  const showMemoryPending = computed(() => {
    if (!allJobsTerminal.value) return false
    if (!project.value?.product_id) return false
    return !memoryWritten.value
  })

  function openCloseoutModal() {
    showCloseoutModal.value = true
  }

  async function handleCloseoutComplete() {
    showCloseoutModal.value = false
    notificationStore.clearForProject(projectId.value)
    showToast({ message: 'Project closed out successfully', type: 'success' })
    onComplete?.()
  }

  async function handleContinueWorking() {
    showCloseoutModal.value = false
    showContinueGuidance.value = true
    showToast({ message: 'Project resumed - agents ready for work', type: 'success' })
    onComplete?.()
  }

  watch(
    () => sortedJobs.value,
    (jobs) => {
      if (showContinueGuidance.value && jobs?.length) {
        const orchestrator = jobs.find((j) => j.agent_display_name === 'orchestrator')
        if (orchestrator && orchestrator.status === 'working') {
          showContinueGuidance.value = false
        }
      }
    },
  )

  watch(
    allJobsTerminal,
    async (terminal) => {
      clearTimeout(memoryCheckTimeout)
      if (!terminal || memoryWritten.value) return
      const productId = project.value?.product_id
      if (!productId) return
      try {
        const res = await api.products.getMemoryEntries(productId, {
          project_id: projectId.value,
          limit: 1,
        })
        if (res.data?.entries?.length > 0) {
          memoryWritten.value = true
          return
        }
      } catch {
        memoryWritten.value = true
        return
      }
      memoryCheckTimeout = setTimeout(async () => {
        if (memoryWritten.value) return
        try {
          await api.products.getMemoryEntries(productId, {
            project_id: projectId.value,
            limit: 1,
          })
          memoryWritten.value = true
        } catch {
          memoryWritten.value = true
        }
      }, 60_000)
    },
    { immediate: true },
  )

  function reset(newProjectId, oldProjectId) {
    if (oldProjectId && oldProjectId !== newProjectId) {
      clearTimeout(memoryCheckTimeout)
      memoryWritten.value = false
    }
  }

  function cleanup() {
    clearTimeout(memoryCheckTimeout)
  }

  return {
    showCloseoutModal,
    memoryWritten,
    showContinueGuidance,
    projectDoneStatus,
    allJobsTerminal,
    showCloseoutButton,
    showMemoryPending,
    openCloseoutModal,
    handleCloseoutComplete,
    handleContinueWorking,
    reset,
    cleanup,
  }
}
