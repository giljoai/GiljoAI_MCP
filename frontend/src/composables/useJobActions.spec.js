import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useJobActions } from './useJobActions'
import { api } from '@/services/api'

const mockShowToast = vi.fn()
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ showToast: mockShowToast }),
}))

describe('useJobActions', () => {
  let getJob

  beforeEach(() => {
    setActivePinia(createPinia())
    getJob = vi.fn(() => null)
    vi.clearAllMocks()
  })

  it('initializes with all modals closed', () => {
    const {
      showAgentDetailsModal,
      showAgentJobModal,
      showMessageAuditModal,
      showHandoverModal,
    } = useJobActions(getJob)

    expect(showAgentDetailsModal.value).toBe(false)
    expect(showAgentJobModal.value).toBe(false)
    expect(showMessageAuditModal.value).toBe(false)
    expect(showHandoverModal.value).toBe(false)
  })

  it('handleMessages opens message audit modal on sent tab', () => {
    const { handleMessages, showMessageAuditModal, messageAuditInitialTab, selectedJobId } =
      useJobActions(getJob)

    handleMessages({ job_id: 'job-1' })

    expect(selectedJobId.value).toBe('job-1')
    expect(messageAuditInitialTab.value).toBe('sent')
    expect(showMessageAuditModal.value).toBe(true)
  })

  it('handleMessages falls back to agent_id when job_id missing', () => {
    const { handleMessages, selectedJobId } = useJobActions(getJob)

    handleMessages({ agent_id: 'agent-2' })

    expect(selectedJobId.value).toBe('agent-2')
  })

  it('handleStepsClick opens job modal on plan tab', () => {
    const { handleStepsClick, showAgentJobModal, jobModalInitialTab, selectedJobId } =
      useJobActions(getJob)

    handleStepsClick({ job_id: 'job-1', steps: { completed: 2, total: 5 } })

    expect(selectedJobId.value).toBe('job-1')
    expect(jobModalInitialTab.value).toBe('plan')
    expect(showAgentJobModal.value).toBe(true)
  })

  it('handleStepsClick does nothing when steps data invalid', () => {
    const { handleStepsClick, showAgentJobModal } = useJobActions(getJob)

    handleStepsClick({ job_id: 'job-1', steps: null })
    expect(showAgentJobModal.value).toBe(false)

    handleStepsClick({ job_id: 'job-1', steps: { completed: 'x', total: 5 } })
    expect(showAgentJobModal.value).toBe(false)
  })

  it('handleAgentRole opens agent details modal', () => {
    const { handleAgentRole, showAgentDetailsModal, selectedJobId } = useJobActions(getJob)

    handleAgentRole({ job_id: 'job-3' })

    expect(selectedJobId.value).toBe('job-3')
    expect(showAgentDetailsModal.value).toBe(true)
  })

  it('handleAgentJob opens job modal on mission tab', () => {
    const { handleAgentJob, showAgentJobModal, jobModalInitialTab, selectedJobId } =
      useJobActions(getJob)

    handleAgentJob({ job_id: 'job-4' })

    expect(selectedJobId.value).toBe('job-4')
    expect(jobModalInitialTab.value).toBe('mission')
    expect(showAgentJobModal.value).toBe(true)
  })

  it('handleHandOver calls simpleHandover and opens modal on success', async () => {
    api.agentJobs.simpleHandover.mockResolvedValue({
      data: {
        success: true,
        retirement_prompt: 'retire this',
        continuation_prompt: 'continue here',
      },
    })

    const { handleHandOver, showHandoverModal, handoverData } = useJobActions(getJob)
    await handleHandOver({ job_id: 'job-5' })

    expect(api.agentJobs.simpleHandover).toHaveBeenCalledWith('job-5')
    expect(showHandoverModal.value).toBe(true)
    expect(handoverData.value.retirement_prompt).toBe('retire this')
    expect(handoverData.value.continuation_prompt).toBe('continue here')
  })

  it('handleHandOver shows error toast on API failure', async () => {
    api.agentJobs.simpleHandover.mockRejectedValue(new Error('Network error'))

    const { handleHandOver, showHandoverModal } = useJobActions(getJob)
    await handleHandOver({ job_id: 'job-6' })

    expect(showHandoverModal.value).toBe(false)
    expect(mockShowToast).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'error' })
    )
  })

  it('selectedAgent delegates to getJob with selectedJobId', () => {
    const mockJob = { job_id: 'job-7', agent_display_name: 'implementer' }
    getJob = vi.fn((id) => (id === 'job-7' ? mockJob : null))

    const { selectedAgent, handleAgentRole } = useJobActions(getJob)
    handleAgentRole({ job_id: 'job-7' })

    expect(selectedAgent.value).toEqual(mockJob)
  })
})
