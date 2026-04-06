import { ref } from 'vue'
import { api } from '@/services/api'
import { useToast } from '@/composables/useToast'
import { shouldShowLaunchAction } from '@/utils/actionConfig'

/**
 * usePlayButton — play button display logic and launch handlers extracted from JobsTab.
 *
 * @param {Object|Ref} project - project object (or reactive ref)
 * @param {Function} getProjectState - function(projectId) => project state with stagingComplete
 * @param {Function} clipboardCopy - async function(text) => boolean (from useClipboard)
 * @returns play button state, visibility helpers, and action handlers
 */
export function usePlayButton(project, getProjectState, clipboardCopy) {
  const { showToast } = useToast()

  const reactivatedAgents = ref(new Set())

  function _getProject() {
    return project?.value ?? project
  }

  function shouldShowCopyButton(agent) {
    const proj = _getProject()
    const projectId = proj?.project_id || proj?.id
    const state = getProjectState(projectId)
    if (!state?.stagingComplete) return false

    const executionMode = proj?.execution_mode
    const claudeCodeCliMode = ['claude_code_cli', 'codex_cli', 'gemini_cli'].includes(executionMode)

    return shouldShowLaunchAction(agent, claudeCodeCliMode)
  }

  function isPlayButtonFaded(agent) {
    const jobId = agent.job_id || agent.agent_id
    if (reactivatedAgents.value.has(jobId)) return false
    return agent.status !== 'waiting'
  }

  function reactivatePlay(agent) {
    const jobId = agent.job_id || agent.agent_id
    reactivatedAgents.value.add(jobId)
  }

  async function handlePlay(agent) {
    const jobId = agent.job_id || agent.agent_id
    reactivatedAgents.value.delete(jobId)

    const proj = _getProject()

    try {
      if (agent.agent_display_name === 'orchestrator') {
        if (['claude_code_cli', 'codex_cli', 'gemini_cli'].includes(proj?.execution_mode)) {
          try {
            const projectId = proj.project_id || proj.id
            try {
              await api.projects.launchImplementation(projectId)
            } catch (gateError) {
              console.warn('[usePlayButton] launch-implementation call failed (non-blocking):', gateError)
            }

            const response = await api.prompts.implementation(projectId)
            const prompt = response.data.prompt
            await _copyPrompt(prompt)
            showToast({
              message: `Implementation prompt copied! ${response.data.agent_count + 1} jobs ready (1 orchestrator, ${response.data.agent_count} agents)`,
              type: 'success',
              timeout: 5000,
            })
          } catch (error) {
            const errorMsg = error.response?.data?.detail || 'Failed to generate implementation prompt'
            showToast({ message: errorMsg, type: 'error', timeout: 6000 })
          }
          return
        }

        // Multi-terminal orchestrator
        try {
          const projectId = proj.project_id || proj.id
          try {
            await api.projects.launchImplementation(projectId)
          } catch (gateError) {
            console.warn('[usePlayButton] launch-implementation call failed (non-blocking):', gateError)
          }

          const response = await api.prompts.implementation(projectId)
          const prompt = response.data.prompt
          await _copyPrompt(prompt)
          showToast({
            message: `Orchestrator prompt copied! ${response.data.agent_count} agents ready for launch.`,
            type: 'success',
            timeout: 5000,
          })
        } catch (error) {
          const errorMsg = error.response?.data?.detail || 'Failed to generate orchestrator prompt'
          showToast({ message: errorMsg, type: 'error', timeout: 6000 })
        }
        return
      }

      // Specialist agent
      const response = await api.prompts.agentPrompt(agent.agent_id || agent.job_id)
      const promptText = response.data?.prompt || ''

      if (!promptText) {
        throw new Error('No prompt text returned')
      }

      await _copyPrompt(promptText)
      showToast({ message: 'Launch prompt copied to clipboard', type: 'success', timeout: 3000 })
    } catch (error) {
      console.error('[usePlayButton] Failed to prepare launch prompt:', error)
      const msg = error.response?.data?.detail || error.message || 'Failed to prepare launch prompt'
      showToast({ message: msg, type: 'error', timeout: 5000 })
    }
  }

  async function _copyPrompt(text) {
    const success = await clipboardCopy(text)
    if (!success) {
      throw new Error('Clipboard copy failed')
    }
  }

  return {
    reactivatedAgents,
    shouldShowCopyButton,
    isPlayButtonFaded,
    reactivatePlay,
    handlePlay,
  }
}
