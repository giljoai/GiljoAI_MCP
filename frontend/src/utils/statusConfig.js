/**
 * Status configuration for agent job status display
 * Provides consistent status labels, colors, and styles across JobsTab and other components
 *
 * Handover 0243c: Dynamic Status Display with real-time WebSocket updates
 */

// JobsTab-specific status configuration (Handover 0243c)
export const statusConfig = {
  waiting: {
    label: 'Waiting.',
    color: '#ffd700', // Yellow
    italic: true,
    chipColor: 'warning',
  },
  working: {
    label: 'Working...',
    color: '#ffd700', // Yellow
    italic: true,
    chipColor: 'warning',
  },
  complete: {
    label: 'Complete',
    color: '#67bd6d', // Green
    italic: false,
    chipColor: 'success',
  },
  failed: {
    label: 'Failed',
    color: '#e53935', // Red
    italic: false,
    chipColor: 'error',
  },
  cancelled: {
    label: 'Cancelled',
    color: '#ff9800', // Orange
    italic: false,
    chipColor: 'warning',
  },
  // Handover 0506: Status after orchestrator hands over to successor
  handed_over: {
    label: 'Handed Over',
    color: '#9e9e9e', // Grey
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
  return statusConfig[status]?.color || '#666'
}

/**
 * Check if status should be displayed in italic
 * @param {string} status - Agent status value
 * @returns {boolean} True if italic
 */
export const isStatusItalic = (status) => {
  return statusConfig[status]?.italic || false
}

/**
 * Get Vuetify chip color for status
 * @param {string} status - Agent status value
 * @returns {string} Vuetify color name
 */
export const getStatusChipColor = (status) => {
  return statusConfig[status]?.chipColor || 'default'
}

// Legacy status config for other components
export const STATUS_CONFIG = {
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
    icon: 'mdi-alert-octagon',
    color: 'orange',
    label: 'Blocked',
    description: 'Agent is blocked waiting for input',
  },
  complete: {
    icon: 'mdi-check-circle',
    color: 'yellow-darken-2',
    label: 'Complete',
    description: 'Agent has completed successfully',
  },
  failed: {
    icon: 'mdi-alert-circle',
    color: 'purple',
    label: 'Failure',
    description: 'Agent has failed',
  },
  cancelled: {
    icon: 'mdi-cancel',
    color: 'warning',
    label: 'Cancelled',
    description: 'Agent was cancelled by user',
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

export const HEALTH_CONFIG = {
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

export const STALENESS_THRESHOLD = 10 // minutes

export function getStatusConfig(status) {
  return STATUS_CONFIG[status] || STATUS_CONFIG.waiting
}

export function getHealthConfig(healthStatus) {
  return HEALTH_CONFIG[healthStatus] || HEALTH_CONFIG.unknown
}

export function isJobStale(lastProgressAt, status) {
  if (!lastProgressAt) return false

  const terminalStates = ['complete', 'failed', 'cancelled', 'decommissioned', 'handed_over']
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
