// Application constants

// Sort priority for agent status display (active-first order).
// Lower number = higher priority (shown first in lists/grids).
// Both agentJobsStore and useAgentData share this definition.
export const AGENT_STATUS_PRIORITY = {
  working: 0,
  blocked: 1,
  silent: 2,
  waiting: 3,
  complete: 4,
  completed: 4, // alias used by some backend responses
  decommissioned: 5,
}

// Default color for project types without a custom color
export const DEFAULT_PROJECT_TYPE_COLOR = '#607D8B'

// Reserved taxonomy abbreviation for tasks (BE-6049c). TSK is auto-assigned to
// every task and is NEVER selectable/filterable as a *project* type. A project
// whose type resolves to TSK originated as a converted task (read-time origin
// signal — no dedicated column).
export const RESERVED_TASK_TYPE_ABBR = 'TSK'

// Purple accent for the reserved TSK tag. Single JS mirror of the
// `$color-accent-special` / `--color-accent-special` design token (#8b5cf6).
// Do not hardcode this hex inline in components — import this constant.
export const TSK_TYPE_COLOR = '#8b5cf6'

// Color swatches for the project type color picker
export const PROJECT_TYPE_COLOR_SWATCHES = [
  '#4CAF50', '#2196F3', '#FF9800', '#9C27B0',
  '#00BCD4', '#795548', '#607D8B', '#F44336',
  '#E91E63', '#3F51B5', '#009688', '#FF5722',
]

// Default color for the project type color picker
export const DEFAULT_SWATCH_COLOR = '#E91E63'


export const TASK_STATUS = {
  PENDING: 'pending',
  IN_PROGRESS: 'in_progress',
  COMPLETED: 'completed',
  FAILED: 'failed',
  CANCELLED: 'cancelled',
}
