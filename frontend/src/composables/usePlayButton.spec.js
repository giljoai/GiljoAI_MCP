import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { usePlayButton } from './usePlayButton'
import { api } from '@/services/api'

const mockShowToast = vi.fn()
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ showToast: mockShowToast }),
}))

describe('usePlayButton', () => {
  let project
  let getProjectState
  let clipboardCopy

  beforeEach(() => {
    setActivePinia(createPinia())
    project = { project_id: 'proj-1', execution_mode: 'multi_terminal' }
    getProjectState = vi.fn(() => ({ stagingComplete: true }))
    clipboardCopy = vi.fn(() => Promise.resolve(true))
    vi.clearAllMocks()
  })

  it('shouldShowCopyButton returns false when staging not complete', () => {
    getProjectState = vi.fn(() => ({ stagingComplete: false }))
    const { shouldShowCopyButton } = usePlayButton(project, getProjectState, clipboardCopy)

    const agent = { agent_display_name: 'implementer', status: 'waiting' }
    expect(shouldShowCopyButton(agent)).toBe(false)
  })

  it('isPlayButtonFaded returns false for waiting agent', () => {
    const { isPlayButtonFaded } = usePlayButton(project, getProjectState, clipboardCopy)
    const agent = { job_id: 'job-1', status: 'waiting' }
    expect(isPlayButtonFaded(agent)).toBe(false)
  })

  it('isPlayButtonFaded returns true for non-waiting agent', () => {
    const { isPlayButtonFaded } = usePlayButton(project, getProjectState, clipboardCopy)
    const agent = { job_id: 'job-1', status: 'working' }
    expect(isPlayButtonFaded(agent)).toBe(true)
  })

  it('reactivatePlay makes isPlayButtonFaded return false', () => {
    const { reactivatePlay, isPlayButtonFaded } = usePlayButton(project, getProjectState, clipboardCopy)
    const agent = { job_id: 'job-2', status: 'working' }

    expect(isPlayButtonFaded(agent)).toBe(true)
    reactivatePlay(agent)
    expect(isPlayButtonFaded(agent)).toBe(false)
  })

  it('handlePlay calls clipboard copy for specialist agent', async () => {
    api.prompts.agentPrompt.mockResolvedValue({ data: { prompt: 'specialist prompt text' } })

    const { handlePlay } = usePlayButton(project, getProjectState, clipboardCopy)
    const agent = { agent_id: 'agent-1', agent_display_name: 'implementer', status: 'waiting' }

    await handlePlay(agent)

    expect(api.prompts.agentPrompt).toHaveBeenCalledWith('agent-1')
    expect(clipboardCopy).toHaveBeenCalledWith('specialist prompt text')
    expect(mockShowToast).toHaveBeenCalledWith(expect.objectContaining({ type: 'success' }))
  })

  it('handlePlay re-fades button after re-copy', async () => {
    api.prompts.agentPrompt.mockResolvedValue({ data: { prompt: 'prompt' } })

    const { handlePlay, reactivatePlay, isPlayButtonFaded } = usePlayButton(
      project, getProjectState, clipboardCopy
    )
    const agent = { job_id: 'job-3', agent_id: 'agent-3', agent_display_name: 'implementer', status: 'working' }

    reactivatePlay(agent)
    expect(isPlayButtonFaded(agent)).toBe(false)

    await handlePlay(agent)
    expect(isPlayButtonFaded(agent)).toBe(true)
  })

  it('handlePlay for CLI orchestrator calls implementation and copies prompt', async () => {
    project = { project_id: 'proj-2', execution_mode: 'claude_code_cli' }
    api.projects.launchImplementation.mockResolvedValue({ data: { success: true } })
    api.prompts.implementation.mockResolvedValue({
      data: { prompt: 'impl prompt', agent_count: 2 },
    })

    const { handlePlay } = usePlayButton(project, getProjectState, clipboardCopy)
    const agent = { job_id: 'job-orch', agent_display_name: 'orchestrator', status: 'waiting' }

    await handlePlay(agent)

    expect(api.prompts.implementation).toHaveBeenCalledWith('proj-2')
    expect(clipboardCopy).toHaveBeenCalledWith('impl prompt')
    expect(mockShowToast).toHaveBeenCalledWith(expect.objectContaining({ type: 'success' }))
  })

  it('handlePlay shows error toast when specialist prompt empty', async () => {
    api.prompts.agentPrompt.mockResolvedValue({ data: { prompt: '' } })

    const { handlePlay } = usePlayButton(project, getProjectState, clipboardCopy)
    const agent = { agent_id: 'agent-5', agent_display_name: 'implementer', status: 'waiting' }

    await handlePlay(agent)

    expect(mockShowToast).toHaveBeenCalledWith(expect.objectContaining({ type: 'error' }))
  })
})
