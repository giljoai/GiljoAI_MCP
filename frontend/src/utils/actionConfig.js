/**
 * Action configuration for status board action icons
 * Defines icons, colors, tooltips, and availability rules for all job actions
 */

export const ACTION_CONFIG = {
  launch: {
    icon: 'mdi-rocket-launch',
    color: 'primary',
    label: 'Launch Agent',
    tooltip: 'Copy prompt to clipboard and launch agent',
    confirmation: false,
    requiresStatus: ['waiting'],
    excludeTerminalStates: true,
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

  cancel: {
    icon: 'mdi-cancel',
    color: 'error',
    label: 'Cancel Job',
    tooltip: 'Cancel this agent job',
    confirmation: true,
    confirmationTitle: 'Cancel Agent Job?',
    confirmationMessage:
      'Are you sure you want to cancel this agent? This action cannot be undone.',
    requiresStatus: ['working', 'waiting', 'blocked'],
    excludeTerminalStates: true,
  },

  handOver: {
    icon: 'mdi-hand-left',
    color: 'warning',
    label: 'Hand Over',
    tooltip: 'Trigger orchestrator succession and hand over context',
    confirmation: true,
    confirmationTitle: 'Trigger Orchestrator Handover?',
    confirmationMessage:
      'This will create a new orchestrator instance and transfer context. Continue?',
    requiresStatus: ['working'],
    requiresAgentType: 'orchestrator',
    requiresContextThreshold: 0.9, // 90% context usage
    excludeTerminalStates: true,
  },
}

/**
 * Get available actions for a job
 * @param {Object} job - Job object with status, agent_type, context_used, context_budget
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

  // Cancel action
  if (shouldShowCancelAction(job)) {
    actions.push('cancel')
  }

  // Hand over action (orchestrator only, at 90% context)
  if (shouldShowHandOverAction(job)) {
    actions.push('handOver')
  }

  return actions
}

/**
 * Check if launch action should be shown
 * @param {Object} job - Job object
 * @param {Boolean} claudeCodeCliMode - Whether Claude Code CLI mode is enabled
 * @returns {Boolean}
 */
function shouldShowLaunchAction(job, claudeCodeCliMode) {
  // In Claude Code CLI mode, only orchestrator gets launch button
  if (claudeCodeCliMode && job.agent_type !== 'orchestrator') {
    return false
  }

  // In General CLI mode, all agents get launch buttons
  return job.status === 'waiting'
}

/**
 * Check if cancel action should be shown
 * @param {Object} job - Job object
 * @returns {Boolean}
 */
function shouldShowCancelAction(job) {
  const cancelableStates = ['working', 'waiting', 'blocked']
  return cancelableStates.includes(job.status)
}

/**
 * Check if hand over action should be shown
 * @param {Object} job - Job object
 * @returns {Boolean}
 */
function shouldShowHandOverAction(job) {
  if (job.agent_type !== 'orchestrator') return false
  if (job.status !== 'working') return false

  // Check context usage (from job data)
  const contextUsage = (job.context_used || 0) / (job.context_budget || 1)
  return contextUsage >= 0.9
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
    const terminalStates = ['complete', 'failed', 'cancelled', 'decommissioned']
    if (terminalStates.includes(job.status)) {
      return `Job is ${job.status}`
    }
  }

  // Launch action specific checks
  if (actionName === 'launch') {
    if (job.status !== 'waiting') {
      return 'Agent must be in waiting status to launch'
    }
    if (claudeCodeCliMode && job.agent_type !== 'orchestrator') {
      return 'Only orchestrator can be launched in Claude Code CLI mode'
    }
    return ''
  }

  // Cancel action specific checks
  if (actionName === 'cancel') {
    if (!['working', 'waiting', 'blocked'].includes(job.status)) {
      return 'Job is not in a cancelable state'
    }
    return ''
  }

  // Hand over action specific checks
  if (actionName === 'handOver') {
    if (job.agent_type !== 'orchestrator') {
      return 'Only orchestrator can trigger handover'
    }
    if (job.status !== 'working') {
      return 'Orchestrator must be working to trigger handover'
    }
    const contextUsage = (job.context_used || 0) / (job.context_budget || 1)
    if (contextUsage < 0.9) {
      const percentage = Math.round(contextUsage * 100)
      return `Context usage ${percentage} percent (requires 90 percent)`
    }
    return ''
  }

  return ''
}
