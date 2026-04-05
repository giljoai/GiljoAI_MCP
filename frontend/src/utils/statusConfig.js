/**
 * Status configuration for agent job status display
 * Provides consistent status labels, colors, and styles across JobsTab and other components
 *
 * Handover 0243c: Dynamic Status Display with real-time WebSocket updates
 */

// Status color tokens — keep in sync with design-tokens.scss ($color-status-*)
const STATUS_COLORS = {
  WAITING: '#ffd700',     // $color-status-waiting
  WORKING: '#ffffff',     // $color-status-working
  BLOCKED: '#ff9800',     // $color-status-blocked
  COMPLETE: '#67bd6d',    // $color-status-complete
  IDLE: '#7a9bb5',        // $color-status-idle
  SLEEPING: '#9b89b3',    // $color-status-sleeping
  HANDED_OVER: '#9e9e9e', // $color-status-handed-over
  DECOMMISSIONED: '#757575', // $color-status-decommissioned
  FALLBACK: '#666666',    // Fallback muted
}

// JobsTab-specific status configuration (Handover 0243c)
const statusConfig = {
  waiting: {
    label: 'Waiting.',
    color: STATUS_COLORS.WAITING,
    italic: true,
    chipColor: 'warning',
  },
  working: {
    label: 'Working',
    color: STATUS_COLORS.WORKING,
    italic: true,
    chipColor: 'default',
  },
  blocked: {
    label: 'Needs Input',
    color: STATUS_COLORS.BLOCKED,
    italic: false,
    chipColor: 'warning',
  },
  complete: {
    label: 'Complete',
    color: STATUS_COLORS.COMPLETE,
    italic: false,
    chipColor: 'success',
  },
  // Handover 0880: Agent resting states
  idle: {
    label: 'Monitoring',
    color: STATUS_COLORS.IDLE,
    italic: true,
    chipColor: 'default',
  },
  sleeping: {
    label: 'Sleeping',
    color: STATUS_COLORS.SLEEPING,
    italic: true,
    chipColor: 'default',
  },
  silent: {
    label: 'Silent',
    color: STATUS_COLORS.BLOCKED,
    italic: false,
    chipColor: 'warning',
  },
  // Handover 0506: Status after orchestrator hands over to successor
  handed_over: {
    label: 'Handed Over',
    color: STATUS_COLORS.HANDED_OVER,
    italic: false,
    chipColor: 'default',
  },
  // Agent ID Swap: Status for old orchestrator after succession (ID swapped to decomm-xxx)
  decommissioned: {
    label: 'Decommissioned',
    color: STATUS_COLORS.DECOMMISSIONED,
    italic: false,
    chipColor: 'default',
  },
}

/**
 * Get human-readable label for status
 * @param {string} status - Agent status value
 * @returns {string} Display label
 */
export const getStatusLabel = (status) => {
  return statusConfig[status]?.label || 'Unknown'
}

/**
 * Get color for status display
 * @param {string} status - Agent status value
 * @returns {string} Hex color code
 */
export const getStatusColor = (status) => {
  return statusConfig[status]?.color || STATUS_COLORS.FALLBACK
}

/**
 * Check if status should be displayed in italic
 * @param {string} status - Agent status value
 * @returns {boolean} True if italic
 */
export const isStatusItalic = (status) => {
  return statusConfig[status]?.italic || false
}

// Legacy status config for other components
const STATUS_CONFIG = {
  waiting: {
    icon: 'mdi-clock-outline',
    color: 'grey',
    label: 'Waiting',
    description: 'Agent is waiting to start',
  },
  working: {
    icon: 'mdi-cog',
    color: 'primary',
    label: 'Working',
    description: 'Agent is actively working',
  },
  blocked: {
    icon: 'mdi-account-question',
    color: 'orange',
    label: 'Needs Input',
    description: 'Agent needs user input to continue',
  },
  complete: {
    icon: 'mdi-check-circle',
    color: 'yellow-darken-2',
    label: 'Complete',
    description: 'Agent has completed successfully',
  },
  // Handover 0880: Agent resting states
  idle: {
    icon: 'mdi-eye-outline',
    color: 'blue-grey',
    label: 'Monitoring',
    description: 'Agent is idle, monitoring for activity',
  },
  sleeping: {
    icon: 'mdi-sleep',
    color: 'deep-purple-lighten-2',
    label: 'Sleeping',
    description: 'Agent is sleeping, will auto-check in',
  },
  silent: {
    icon: 'mdi-clock-alert',
    color: 'amber-darken-2',
    label: 'Silent',
    description: 'Agent stopped communicating',
  },
  decommissioned: {
    icon: 'mdi-archive',
    color: 'grey-darken-1',
    label: 'Decommissioned',
    description: 'Agent has been decommissioned',
  },
  // Handover 0506: Status after orchestrator hands over to successor
  handed_over: {
    icon: 'mdi-hand-wave',
    color: 'grey',
    label: 'Handed Over',
    description: 'Orchestrator handed over to successor',
  },
}

const HEALTH_CONFIG = {
  healthy: {
    icon: null,
    color: 'success',
    label: 'Healthy',
    showIndicator: false,
  },
  warning: {
    icon: 'mdi-alert',
    color: 'warning',
    label: 'Warning',
    showIndicator: true,
    dotColor: 'yellow darken-2',
    pulse: false,
  },
  critical: {
    icon: 'mdi-alert-octagon',
    color: 'error',
    label: 'Critical',
    showIndicator: true,
    dotColor: 'red',
    pulse: true,
  },
  timeout: {
    icon: 'mdi-timer-alert',
    color: 'grey',
    label: 'Timeout',
    showIndicator: true,
    dotColor: 'grey',
  },
  unknown: {
    icon: 'mdi-help-circle',
    color: 'grey lighten-1',
    label: 'Unknown',
    showIndicator: false,
  },
}

const STALENESS_THRESHOLD = 10 // minutes

export function getStatusConfig(status) {
  return STATUS_CONFIG[status] || STATUS_CONFIG.waiting
}

export function getHealthConfig(healthStatus) {
  return HEALTH_CONFIG[healthStatus] || HEALTH_CONFIG.unknown
}

export function isJobStale(lastProgressAt, status) {
  if (!lastProgressAt) return false

  const terminalStates = ['complete', 'silent', 'decommissioned', 'handed_over', 'idle', 'sleeping']
  if (terminalStates.includes(status)) return false

  const now = new Date()
  const lastProgress = new Date(lastProgressAt)
  const minutesSince = (now - lastProgress) / (1000 * 60)

  return minutesSince > STALENESS_THRESHOLD
}

export function formatLastActivity(lastProgressAt) {
  if (!lastProgressAt) return 'Never'

  const now = new Date()
  const lastProgress = new Date(lastProgressAt)
  const minutesSince = Math.floor((now - lastProgress) / (1000 * 60))

  if (minutesSince < 1) return 'Just now'
  if (minutesSince === 1) return '1 minute ago'
  if (minutesSince < 60) return `${minutesSince} minutes ago`

  const hoursSince = Math.floor(minutesSince / 60)
  if (hoursSince === 1) return '1 hour ago'
  if (hoursSince < 24) return `${hoursSince} hours ago`

  const daysSince = Math.floor(hoursSince / 24)
  if (daysSince === 1) return '1 day ago'
  return `${daysSince} days ago`
}
