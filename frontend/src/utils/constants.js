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

// Color swatches for the project type color picker
export const PROJECT_TYPE_COLOR_SWATCHES = [
  '#4CAF50', '#2196F3', '#FF9800', '#9C27B0',
  '#00BCD4', '#795548', '#607D8B', '#F44336',
  '#E91E63', '#3F51B5', '#009688', '#FF5722',
]

// Default color for the project type color picker
export const DEFAULT_SWATCH_COLOR = '#E91E63'

// CLI tool display colors for template manager
export const CLI_TOOL_COLORS = {
  claude: '#1976D2',
  codex: '#4CAF50',
  gemini: '#9C27B0',
}

export const TASK_STATUS = {
  PENDING: 'pending',
  IN_PROGRESS: 'in_progress',
  COMPLETED: 'completed',
  FAILED: 'failed',
  CANCELLED: 'cancelled',
}
