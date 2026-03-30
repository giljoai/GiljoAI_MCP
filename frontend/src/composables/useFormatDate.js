/**
 * Date formatting composable.
 *
 * Provides consistent date formatting across the application.
 * Replaces 11 ad-hoc formatDate implementations.
 */
export function useFormatDate() {
  /**
   * Format a date string as "Mar 30, 2026".
   */
  function formatDate(dateString) {
    if (!dateString) return 'N/A'
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      })
    } catch {
      return String(dateString)
    }
  }

  /**
   * Format a date string as "Mar 30, 2026, 02:45 PM".
   */
  function formatDateTime(dateString) {
    if (!dateString) return 'N/A'
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    } catch {
      return String(dateString)
    }
  }

  /**
   * Format a date string as compact "30/03/26".
   */
  function formatDateCompact(dateString) {
    if (!dateString) return '—'
    try {
      const d = new Date(dateString)
      const dd = String(d.getDate()).padStart(2, '0')
      const mm = String(d.getMonth() + 1).padStart(2, '0')
      const yy = String(d.getFullYear()).slice(-2)
      return `${dd}/${mm}/${yy}`
    } catch {
      return String(dateString)
    }
  }

  return { formatDate, formatDateTime, formatDateCompact }
}
