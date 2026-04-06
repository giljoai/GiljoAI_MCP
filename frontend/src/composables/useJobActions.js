import { ref, computed } from 'vue'
import { api } from '@/services/api'
import { useToast } from '@/composables/useToast'

/**
 * useJobActions — modal state and action handlers extracted from JobsTab.
 *
 * @param {Function} getJob - function(jobId) => agent job object from store
 * @returns modal state, selected agent computed, and action handlers
 */
export function useJobActions(getJob) {
  const { showToast } = useToast()

  const showAgentDetailsModal = ref(false)
  const showAgentJobModal = ref(false)
  const showMessageAuditModal = ref(false)
  const showHandoverModal = ref(false)
  const handoverData = ref({ retirement_prompt: '', continuation_prompt: '' })
  const jobModalInitialTab = ref('mission')
  const messageAuditInitialTab = ref('sent')
  const selectedJobId = ref(null)

  const selectedAgent = computed(() => getJob(selectedJobId.value))

  function handleMessages(agent) {
    selectedJobId.value = agent.job_id || agent.agent_id
    messageAuditInitialTab.value = 'sent'
    showMessageAuditModal.value = true
  }

  function handleStepsClick(agent) {
    if (
      !agent.steps ||
      typeof agent.steps.completed !== 'number' ||
      typeof agent.steps.total !== 'number'
    ) {
      return
    }

    selectedJobId.value = agent.job_id || agent.agent_id
    jobModalInitialTab.value = 'plan'
    showAgentJobModal.value = true
  }

  function handleAgentRole(agent) {
    selectedJobId.value = agent.job_id || agent.agent_id
    showAgentDetailsModal.value = true
  }

  function handleAgentJob(agent) {
    selectedJobId.value = agent.job_id || agent.agent_id
    jobModalInitialTab.value = 'mission'
    showAgentJobModal.value = true
  }

  async function handleHandOver(agent) {
    try {
      const jobId = agent.job_id || agent.agent_id
      const response = await api.agentJobs.simpleHandover(jobId)

      if (response.data.success) {
        handoverData.value = {
          retirement_prompt: response.data.retirement_prompt,
          continuation_prompt: response.data.continuation_prompt,
        }
        showHandoverModal.value = true
      } else {
        throw new Error(response.data.error || 'Session refresh failed')
      }
    } catch (error) {
      console.error('[useJobActions] Hand over failed:', error)
      const msg = error.response?.data?.detail || error.message || 'Hand over failed'
      showToast({ message: msg, type: 'error', timeout: 5000 })
    }
  }

  async function handleStopProject(projectId, clipboardCopy) {
    try {
      const response = await api.prompts.termination(projectId)

      if (response.data.prompt) {
        const copyOk = await clipboardCopy(response.data.prompt)
        if (!copyOk) throw new Error('Clipboard copy failed')

        showToast({
          message: `Termination prompt copied! Paste into orchestrator terminal. (${response.data.agent_count} agents)`,
          type: 'warning',
          timeout: 8000,
        })
      } else {
        throw new Error('No prompt returned')
      }
    } catch (error) {
      console.error('[useJobActions] Stop project failed:', error)
      const msg = error.response?.data?.detail || error.message || 'Failed to generate termination prompt'
      showToast({ message: msg, type: 'error', timeout: 5000 })
    }
  }

  return {
    showAgentDetailsModal,
    showAgentJobModal,
    showMessageAuditModal,
    showHandoverModal,
    handoverData,
    jobModalInitialTab,
    messageAuditInitialTab,
    selectedJobId,
    selectedAgent,
    handleMessages,
    handleStepsClick,
    handleAgentRole,
    handleAgentJob,
    handleHandOver,
    handleStopProject,
  }
}
