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
   * Format a date string as "Mar 30, 2026 14:05" (24h military time).
   */
  function formatDateWithTime(dateString) {
    if (!dateString) return 'N/A'
    try {
      const d = new Date(dateString)
      const date = d.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      })
      const hh = String(d.getHours()).padStart(2, '0')
      const mm = String(d.getMinutes()).padStart(2, '0')
      return `${date} ${hh}:${mm}`
    } catch {
      return String(dateString)
    }
  }

  /**
   * Format a date string as compact "30/03/26 14:05" (24h military time).
   */
  function formatDateCompactWithTime(dateString) {
    if (!dateString) return '—'
    try {
      const d = new Date(dateString)
      const dd = String(d.getDate()).padStart(2, '0')
      const mo = String(d.getMonth() + 1).padStart(2, '0')
      const yy = String(d.getFullYear()).slice(-2)
      const hh = String(d.getHours()).padStart(2, '0')
      const mm = String(d.getMinutes()).padStart(2, '0')
      return `${dd}/${mo}/${yy} ${hh}:${mm}`
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

  return { formatDate, formatDateTime, formatDateWithTime, formatDateCompactWithTime, formatDateCompact }
}
