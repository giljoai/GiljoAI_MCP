/**
 * Action configuration for status board action icons
 * Defines icons, colors, tooltips, and availability rules for all job actions
 */

export const ACTION_CONFIG = {
  launch: {
    icon: 'mdi-rocket-launch',
    color: 'primary',
    label: 'Launch Agent',
    tooltip: 'Copy prompt to clipboard',
    confirmation: false,
    requiresStatus: [], // Always available for prompt re-copying
    excludeTerminalStates: false,
  },

  copyPrompt: {
    icon: 'mdi-content-copy',
    color: 'grey darken-1',
    label: 'Copy Prompt',
    tooltip: 'Copy agent prompt to clipboard',
    confirmation: false,
    requiresStatus: [], // Available for all
    excludeTerminalStates: false,
  },

  viewMessages: {
    icon: 'mdi-message-text',
    color: 'blue',
    label: 'View Messages',
    tooltip: 'Open message history',
    confirmation: false,
    requiresStatus: [], // Available for all
    excludeTerminalStates: false,
    badge: true, // Show unread count badge
  },

  handOver: {
    icon: 'mdi-refresh',
    color: 'warning',
    label: 'Refresh Session',
    tooltip: 'Refresh Session (reset context)',
    // Handover 0461d: Direct API call - no confirmation dialog
    // Copies continuation prompt to clipboard automatically
    confirmation: false,
    requiresStatus: ['working'],
    requiresAgentType: 'orchestrator',
    // Handover 0461d: Session refresh available while working
    excludeTerminalStates: true,
  },
}

/**
 * Get available actions for a job
 * @param {Object} job - Job object with status, agent_display_name, context_used, context_budget
 * @param {Boolean} claudeCodeCliMode - Whether Claude Code CLI mode is enabled
 * @returns {Array<string>} List of available action names
 */
export function getAvailableActions(job, claudeCodeCliMode = false) {
  const actions = []

  // Launch action
  if (shouldShowLaunchAction(job, claudeCodeCliMode)) {
    actions.push('launch')
  }

  // Copy prompt (always available except decommissioned)
  if (job.status !== 'decommissioned') {
    actions.push('copyPrompt')
  }

  // View messages (always available)
  actions.push('viewMessages')

  // Hand over action (orchestrator only)
  if (shouldShowHandOverAction(job)) {
    actions.push('handOver')
  }

  return actions
}

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

/**
 * Check if hand over action should be shown
 * Handover 0506: Always available for orchestrators in working status
 * @param {Object} job - Job object
 * @returns {Boolean}
 */
function shouldShowHandOverAction(job) {
  if (job.agent_display_name !== 'orchestrator') return false
  if (job.status !== 'working') return false
  // Handover 0506: Removed context threshold - user decides when to hand over
  return true
}

/**
 * Get action configuration
 * @param {String} actionName - Name of the action (e.g., 'launch', 'cancel')
 * @returns {Object|null} Action configuration or null if not found
 */
export function getActionConfig(actionName) {
  return ACTION_CONFIG[actionName] || null
}

/**
 * Check if action requires confirmation
 * @param {String} actionName - Name of the action
 * @returns {Boolean}
 */
export function actionRequiresConfirmation(actionName) {
  const config = getActionConfig(actionName)
  return config?.confirmation || false
}

/**
 * Get reason why action is disabled (for tooltips)
 * @param {String} actionName - Name of the action
 * @param {Object} job - Job object
 * @param {Boolean} claudeCodeCliMode - Whether Claude Code CLI mode is enabled
 * @returns {String} Reason or empty string if action is available
 */
export function getDisabledReason(actionName, job, claudeCodeCliMode = false) {
  const config = getActionConfig(actionName)
  if (!config) return 'Action not found'

  // Check terminal states
  if (config.excludeTerminalStates) {
    const terminalStates = ['complete', 'failed', 'cancelled', 'decommissioned', 'handed_over']
    if (terminalStates.includes(job.status)) {
      return `Job is ${job.status}`
    }
  }

  // Launch action specific checks
  if (actionName === 'launch') {
    if (claudeCodeCliMode && job.agent_display_name !== 'orchestrator') {
      return 'Only orchestrator can be launched in Claude Code CLI mode'
    }
    return ''
  }

  // Hand over action specific checks
  // Handover 0506: Removed context threshold - user decides when to hand over
  if (actionName === 'handOver') {
    if (job.agent_display_name !== 'orchestrator') {
      return 'Only orchestrator can initiate handover'
    }
    if (job.status !== 'working') {
      return 'Orchestrator must be working to initiate handover'
    }
    return ''
  }

  return ''
}
