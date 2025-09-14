// Application constants

export const AGENT_STATUS = {
  ACTIVE: 'active',
  INACTIVE: 'inactive',
  WORKING: 'working',
  IDLE: 'idle',
  ERROR: 'error',
  DECOMMISSIONED: 'decommissioned'
}

export const MESSAGE_TYPES = {
  DIRECT: 'direct',
  BROADCAST: 'broadcast',
  HANDOFF: 'handoff',
  STATUS: 'status',
  ERROR: 'error',
  COMPLETION: 'completion'
}

export const MESSAGE_PRIORITY = {
  LOW: 'low',
  NORMAL: 'normal',
  HIGH: 'high',
  URGENT: 'urgent'
}

export const TASK_STATUS = {
  PENDING: 'pending',
  IN_PROGRESS: 'in_progress',
  COMPLETED: 'completed',
  FAILED: 'failed',
  CANCELLED: 'cancelled'
}

export const PROJECT_STATUS = {
  ACTIVE: 'active',
  INACTIVE: 'inactive',
  COMPLETED: 'completed',
  ARCHIVED: 'archived'
}

export const JOB_TYPES = {
  ANALYSIS: 'analysis',
  IMPLEMENTATION: 'implementation',
  TESTING: 'testing',
  REVIEW: 'review',
  DEPLOYMENT: 'deployment',
  DOCUMENTATION: 'documentation'
}

export const REFRESH_INTERVALS = {
  AGENT_HEALTH: 5000,      // 5 seconds
  MESSAGES: 2000,          // 2 seconds
  PROJECTS: 10000,         // 10 seconds
  TASKS: 3000,            // 3 seconds
  CONTEXT: 30000          // 30 seconds
}

export const CHART_COLORS = {
  primary: '#315074',
  secondary: '#ffc300',
  success: '#67bd6d',
  error: '#c6298c',
  info: '#8f97b7',
  warning: '#ffc300'
}

export const MASCOT_STATES = {
  IDLE: 'giljo_mascot_loader',
  ACTIVE: 'giljo_mascot_active',
  THINKING: 'giljo_mascot_thinker',
  WORKING: 'giljo_mascot_working',
  ERROR: 'error',
  BLINK: 'blink'
}