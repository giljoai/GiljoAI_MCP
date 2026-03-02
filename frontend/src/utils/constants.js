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

export const TASK_STATUS = {
  PENDING: 'pending',
  IN_PROGRESS: 'in_progress',
  COMPLETED: 'completed',
  FAILED: 'failed',
  CANCELLED: 'cancelled',
}
