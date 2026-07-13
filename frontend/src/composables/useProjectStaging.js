/**
 * useProjectStaging.js — FE-6006 unit 3a
 *
 * Extracted from ProjectTabs.vue: handles project staging (prompt generation),
 * unstaging, and launching. Also exposes loadingStageProject state.
 * Edition scope: CE
 */
import { ref, isRef } from 'vue'
import api from '@/services/api'
import { useToast } from '@/composables/useToast'
import { useClipboard } from '@/composables/useClipboard'
import { useProjectStateStore } from '@/stores/projectStateStore'
import { useProjectTabsStore } from '@/stores/projectTabs'

/**
 * @param {Object} options
 * @param {import('vue').Ref<string|null>} options.projectId
 * @param {import('vue').Ref<string>} options.executionMode
 * @param {import('vue').Ref<boolean>} options.isProjectStaged
 * @param {import('vue').Ref<boolean>} options.readyToLaunch
 * @param {import('vue').Ref<boolean>} [options.canRestage]  true when staging_complete && !implementationLaunched
 */
export function useProjectStaging({ projectId, executionMode, isProjectStaged, readyToLaunch, canRestage = null }) {
  const { showToast } = useToast()
  const { copy: clipboardCopy } = useClipboard()
  const projectStateStore = useProjectStateStore()
  const tabsStore = useProjectTabsStore()

  const loadingStageProject = ref(false)

  // Callbacks registered via onLaunchSuccess for the container to handle
  // tab-switch + route update (avoids coupling to router here)
  const launchSuccessCallbacks = []
  function onLaunchSuccess(cb) {
    launchSuccessCallbacks.push(cb)
  }

  function showError(message) {
    showToast({ message: message || 'Unexpected error', type: 'error' })
  }

  // BE-9035c: execution-mode collapse — the UI only ever writes 'multi_terminal'
  // or 'subagent' now; harness detection for a subagent project happens
  // server-side. The legacy per-CLI keys stay so a pre-collapse project that
  // hasn't been re-staged yet (tolerated-on-read execution_mode) still gets
  // its old tool hint / paste label instead of falling through to the default.
  const _platformToTool = {
    multi_terminal: 'claude-code',
    subagent: 'claude-code',
    claude_code_cli: 'claude-code',
    codex_cli: 'codex',
    gemini_cli: 'gemini',
    antigravity_cli: 'antigravity',
  }

  const _pasteLabels = {
    multi_terminal: 'Orchestrator brief copied. Paste into any terminal to stage the project.',
    subagent: 'Orchestrator brief copied. Paste into your subagent orchestrator session to stage the project.',
    claude_code_cli: 'Orchestrator brief copied. Paste into Claude Code CLI to stage the project.',
    codex_cli: 'Orchestrator brief copied. Paste into Codex CLI to stage the project.',
    gemini_cli: 'Orchestrator brief copied. Paste into Gemini CLI to stage the project.',
    antigravity_cli: 'Orchestrator brief copied. Paste into Antigravity CLI to stage the project.',
  }

  async function handleStageProject() {
    loadingStageProject.value = true

    try {
      const pid = projectId.value
      if (!pid) {
        throw new Error('Project missing ID')
      }

      // NULL-state redesign: send the user's actual chosen mode, NOT a
      // 'multi_terminal' default. When unchosen (null/undefined) axios omits the
      // execution_mode param and the backend 409s (handled below). The `tool`
      // fallback stays — the backend legitimately requires a tool and
      // 'claude-code' is a valid default for that separate axis.
      const currentMode = executionMode.value
      const response = await api.prompts.staging(pid, {
        tool: _platformToTool[currentMode] || 'claude-code',
        execution_mode: currentMode,
      })

      if (!response.data?.prompt) {
        throw new Error('Invalid response from staging endpoint')
      }

      const { prompt } = response.data

      projectStateStore.setIsStaged(pid, true)

      const copied = await clipboardCopy(prompt)

      if (copied) {
        showToast({ message: _pasteLabels[currentMode] || _pasteLabels.multi_terminal, type: 'success' })
      } else {
        showToast({ message: 'Copy failed. Check your browser\'s clipboard permissions and try again.', type: 'warning', timeout: 6000 })
      }
    } catch (error) {
      console.error('Stage project failed:', error)

      const errorMsg = error.response?.data?.detail || error.message || 'Failed to stage project'

      if (errorMsg.toLowerCase().includes('orchestrator already exists')) {
        showToast({ message: 'An orchestrator is already active for this project. The existing orchestrator will be reused.', type: 'info' })
      } else if (error.response?.status === 409 && errorMsg.toLowerCase().includes('execution mode')) {
        // NULL-state gate backstop: the Stage button is already disabled until a
        // mode is picked, but surface the backend 409 cleanly if it slips through.
        showToast({ message: 'Please select an execution mode before staging.', type: 'warning', timeout: 5000 })
      } else {
        showError(errorMsg)
      }
    } finally {
      loadingStageProject.value = false
    }
  }

  async function handleUnstageProject() {
    try {
      await projectStateStore.unstageProject(projectId.value)
      showToast({
        message: 'Project unstaged. You can change execution mode and stage again.',
        type: 'success',
      })
    } catch (error) {
      console.error('Unstage failed:', error)
      const msg = error.response?.data?.detail || error.message || 'Failed to unstage project'
      showError(msg)
    }
  }

  // BE-6047: recovery from staging_complete (no implementation launched)
  async function handleRestageProject() {
    try {
      await projectStateStore.restageProject(projectId.value)
      showToast({
        message: 'Project recovery complete. Execution mode unlocked — you can re-stage with a new mode.',
        type: 'success',
      })
    } catch (error) {
      console.error('Restage failed:', error)
      const msg = error.response?.data?.detail || error.message || 'Failed to recover project staging'
      showError(msg)
    }
  }

  // Resolve canRestage: support both ref and plain boolean (defaults to false if not provided)
  function _canRestage() {
    if (canRestage === null || canRestage === undefined) return false
    return isRef(canRestage) ? canRestage.value : Boolean(canRestage)
  }

  async function handleStageOrRestage() {
    if (isProjectStaged.value) {
      await handleUnstageProject()
    } else if (_canRestage()) {
      await handleRestageProject()
    } else {
      await handleStageProject()
    }
  }

  async function handleLaunchJobs(project) {
    try {
      if (!readyToLaunch.value) {
        showError('Project not ready to launch')
        return
      }

      await api.orchestrator.launchProject({ project_id: projectId.value })
      tabsStore.isLaunched = true
      tabsStore.currentProject = project
      projectStateStore.setLaunched(projectId.value, true)

      // Notify container to switch tab + update route
      for (const cb of launchSuccessCallbacks) {
        cb()
      }
    } catch (error) {
      console.error('Launch jobs failed:', error)
      const msg = error.response?.data?.detail || error.message || 'Failed to launch jobs'
      showError(msg)
    }
  }

  return {
    loadingStageProject,
    handleStageProject,
    handleUnstageProject,
    handleRestageProject,
    handleStageOrRestage,
    handleLaunchJobs,
    onLaunchSuccess,
  }
}
