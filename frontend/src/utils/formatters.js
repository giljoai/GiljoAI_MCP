// Utility formatters for the dashboard

export const formatStatus = (status) => {
  const statusMap = {
    active: 'Active',
    inactive: 'Inactive',
    pending: 'Pending',
    completed: 'Completed',
    failed: 'Failed',
    silent: 'Silent',
    in_progress: 'In Progress',
    error: 'Error',
    success: 'Success',
    warning: 'Warning',
  }
  return statusMap[status] || status
}
