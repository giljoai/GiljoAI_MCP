/**
 * Launch-action visibility rule for job action controls.
 * Used by usePlayButton.js to decide whether the launch button is shown.
 */

/**
 * Check if launch action should be shown
 *
 * Always visible for prompt re-copying, except in Claude Code CLI mode
 * where only orchestrator gets the launch button.
 *
 * @param {Object} job - Job object with status and agent_display_name
 * @param {Boolean} claudeCodeCliMode - Whether Claude Code CLI mode is enabled
 * @returns {Boolean} True if launch action should be shown
 */
export function shouldShowLaunchAction(job, claudeCodeCliMode) {
  // In Claude Code CLI mode, only orchestrator gets launch button
  if (claudeCodeCliMode && job.agent_display_name !== 'orchestrator') {
    return false
  }

  // Always show launch button for prompt re-copying
  return true
}
