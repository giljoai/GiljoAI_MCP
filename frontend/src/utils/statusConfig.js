/**
 * Status and health configuration for agent jobs
 */

export const STATUS_CONFIG = {
  waiting: {
    icon: 'mdi-clock-outline',
    color: 'grey',
    label: 'Waiting',
    description: 'Agent is waiting to start'
  },
  working: {
    icon: 'mdi-cog',
    color: 'primary',
    label: 'Working',
    description: 'Agent is actively working'
  },
  blocked: {
    icon: 'mdi-alert-octagon',
    color: 'orange',
    label: 'Blocked',
    description: 'Agent is blocked waiting for input'
  },
  complete: {
    icon: 'mdi-check-circle',
    color: 'yellow-darken-2',
    label: 'Complete',
    description: 'Agent has completed successfully'
  },
  failed: {
    icon: 'mdi-alert-circle',
    color: 'purple',
    label: 'Failure',
    description: 'Agent has failed'
  },
  cancelled: {
    icon: 'mdi-cancel',
    color: 'warning',
    label: 'Cancelled',
    description: 'Agent was cancelled by user'
  },
  decommissioned: {
    icon: 'mdi-archive',
    color: 'grey-darken-1',
    label: 'Decommissioned',
    description: 'Agent has been decommissioned'
  }
};

export const HEALTH_CONFIG = {
  healthy: {
    icon: null,
    color: 'success',
    label: 'Healthy',
    showIndicator: false
  },
  warning: {
    icon: 'mdi-alert',
    color: 'warning',
    label: 'Warning',
    showIndicator: true,
    dotColor: 'yellow darken-2',
    pulse: false
  },
  critical: {
    icon: 'mdi-alert-octagon',
    color: 'error',
    label: 'Critical',
    showIndicator: true,
    dotColor: 'red',
    pulse: true
  },
  timeout: {
    icon: 'mdi-timer-alert',
    color: 'grey',
    label: 'Timeout',
    showIndicator: true,
    dotColor: 'grey'
  },
  unknown: {
    icon: 'mdi-help-circle',
    color: 'grey lighten-1',
    label: 'Unknown',
    showIndicator: false
  }
};

export const STALENESS_THRESHOLD = 10; // minutes

export function getStatusConfig(status) {
  return STATUS_CONFIG[status] || STATUS_CONFIG.waiting;
}

export function getHealthConfig(healthStatus) {
  return HEALTH_CONFIG[healthStatus] || HEALTH_CONFIG.unknown;
}

export function isJobStale(lastProgressAt, status) {
  if (!lastProgressAt) return false;

  const terminalStates = ['complete', 'failed', 'cancelled', 'decommissioned'];
  if (terminalStates.includes(status)) return false;

  const now = new Date();
  const lastProgress = new Date(lastProgressAt);
  const minutesSince = (now - lastProgress) / (1000 * 60);

  return minutesSince > STALENESS_THRESHOLD;
}

export function formatLastActivity(lastProgressAt) {
  if (!lastProgressAt) return 'Never';

  const now = new Date();
  const lastProgress = new Date(lastProgressAt);
  const minutesSince = Math.floor((now - lastProgress) / (1000 * 60));

  if (minutesSince < 1) return 'Just now';
  if (minutesSince === 1) return '1 minute ago';
  if (minutesSince < 60) return `${minutesSince} minutes ago`;

  const hoursSince = Math.floor(minutesSince / 60);
  if (hoursSince === 1) return '1 hour ago';
  if (hoursSince < 24) return `${hoursSince} hours ago`;

  const daysSince = Math.floor(hoursSince / 24);
  if (daysSince === 1) return '1 day ago';
  return `${daysSince} days ago`;
}
