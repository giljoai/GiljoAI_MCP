// Utility formatters for the dashboard

export const formatDate = (date) => {
  if (!date) return '-'
  const d = new Date(date)
  return d.toLocaleDateString() + ' ' + d.toLocaleTimeString()
}

export const formatShortDate = (date) => {
  if (!date) return '-'
  const d = new Date(date)
  return d.toLocaleDateString()
}

export const formatTime = (date) => {
  if (!date) return '-'
  const d = new Date(date)
  return d.toLocaleTimeString()
}

export const formatRelativeTime = (date) => {
  if (!date) return '-'
  const d = new Date(date)
  const now = new Date()
  const diff = now - d
  
  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)
  
  if (days > 0) return `${days}d ago`
  if (hours > 0) return `${hours}h ago`
  if (minutes > 0) return `${minutes}m ago`
  return `${seconds}s ago`
}

export const formatBytes = (bytes) => {
  if (!bytes) return '0 B'
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i]
}

export const formatPercent = (value, decimals = 1) => {
  if (!value) return '0%'
  return (value * 100).toFixed(decimals) + '%'
}

export const formatNumber = (num) => {
  if (!num) return '0'
  return num.toLocaleString()
}

export const truncateText = (text, maxLength = 50) => {
  if (!text) return ''
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

export const formatStatus = (status) => {
  const statusMap = {
    'active': 'Active',
    'inactive': 'Inactive',
    'pending': 'Pending',
    'completed': 'Completed',
    'failed': 'Failed',
    'in_progress': 'In Progress',
    'error': 'Error',
    'success': 'Success',
    'warning': 'Warning'
  }
  return statusMap[status] || status
}

export const formatAgentRole = (role) => {
  const roleMap = {
    'orchestrator': 'Orchestrator',
    'analyzer': 'Analyzer',
    'implementer': 'Implementer',
    'tester': 'Tester',
    'ui_analyzer': 'UI Analyzer',
    'ui_implementer': 'UI Implementer',
    'ui_tester': 'UI Tester'
  }
  return roleMap[role] || role
}