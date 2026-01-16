/**
 * Periodic Notification Reminder Composable
 *
 * Checks for unread notifications every 15 minutes and shows a toast reminder.
 * Respects user settings to silence reminders.
 *
 * @see Handover: notifications-implementation
 */

import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useNotificationStore } from '@/stores/notifications'
import { useSettingsStore } from '@/stores/settings'
import { useToast } from '@/composables/useToast'

// Reminder interval: 15 minutes in milliseconds
const REMINDER_INTERVAL = 15 * 60 * 1000

/**
 * Use notification reminder composable
 *
 * @returns {Object} Composable API
 */
export function useNotificationReminder() {
  const notificationStore = useNotificationStore()
  const settingsStore = useSettingsStore()
  const { showToast } = useToast()

  const intervalId = ref(null)
  const lastReminderAt = ref(null)
  const isActive = ref(false)

  /**
   * Check if reminders are enabled in settings
   */
  function isReminderEnabled() {
    try {
      const settings = settingsStore.settings
      // Default to true if setting doesn't exist yet
      return settings?.notifications?.periodicReminders !== false
    } catch (error) {
      console.warn('[NotificationReminder] Failed to check settings:', error)
      return true // Default to enabled
    }
  }

  /**
   * Show reminder toast if there are unread notifications
   */
  function checkAndRemind() {
    // Skip if reminders are disabled
    if (!isReminderEnabled()) {
      console.log('[NotificationReminder] Reminders disabled in settings')
      return
    }

    const unreadCount = notificationStore.unreadCount || 0

    if (unreadCount > 0) {
      const message =
        unreadCount === 1
          ? 'You have 1 unread notification'
          : `You have ${unreadCount} unread notifications`

      showToast({
        title: 'Unread Notifications',
        message,
        color: 'info',
        icon: 'mdi-bell-ring',
        timeout: 8000,
      })

      lastReminderAt.value = new Date().toISOString()
      console.log('[NotificationReminder] Reminder shown:', message)
    }
  }

  /**
   * Start the reminder interval
   */
  function start() {
    if (intervalId.value) {
      console.log('[NotificationReminder] Already running')
      return
    }

    // Initial check after a short delay (give time for notifications to load)
    setTimeout(() => {
      checkAndRemind()
    }, 5000)

    // Set up periodic check
    intervalId.value = setInterval(checkAndRemind, REMINDER_INTERVAL)
    isActive.value = true

    console.log('[NotificationReminder] Started with interval:', REMINDER_INTERVAL, 'ms')
  }

  /**
   * Stop the reminder interval
   */
  function stop() {
    if (intervalId.value) {
      clearInterval(intervalId.value)
      intervalId.value = null
    }
    isActive.value = false
    console.log('[NotificationReminder] Stopped')
  }

  /**
   * Manually trigger a reminder check
   */
  function triggerReminder() {
    checkAndRemind()
  }

  // Lifecycle hooks for auto-start/stop
  onMounted(() => {
    start()
  })

  onUnmounted(() => {
    stop()
  })

  return {
    // State
    isActive,
    lastReminderAt,

    // Methods
    start,
    stop,
    triggerReminder,
    isReminderEnabled,
  }
}

export default useNotificationReminder
