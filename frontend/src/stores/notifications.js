import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useNotificationStore = defineStore('notifications', () => {
  // State
  const notifications = ref([])

  // Getters
  const unreadCount = computed(() => notifications.value.filter((n) => !n.read).length)

  const agentHealthNotifications = computed(() =>
    notifications.value.filter((n) => n.type === 'agent_health'),
  )

  // Badge color based on highest priority unread notification (Handover: notification color system)
  // Priority: connection_lost (red/error) > agent_health (yellow/warning) > context_tuning (info, no escalation) > others (default)
  const badgeColor = computed(() => {
    const unread = notifications.value.filter((n) => !n.read)
    if (unread.length === 0) return 'error' // default when no unread

    // Check for critical notifications first (red)
    const hasCritical = unread.some((n) => n.type === 'connection_lost' || n.type === 'system_alert')
    if (hasCritical) return 'error'

    // Check for warning notifications (yellow)
    const hasWarning = unread.some((n) => n.type === 'agent_health')
    if (hasWarning) return 'warning'

    // Handover 0831: context_tuning stays info, does not escalate
    const hasContextTuning = unread.some((n) => n.type === 'context_tuning')
    if (hasContextTuning) return 'info'

    // Default color for other notification types
    return 'primary'
  })

  const sortedNotifications = computed(() => {
    const sorted = [...notifications.value]
    sorted.sort((a, b) => {
      const timeA = new Date(a.timestamp).getTime()
      const timeB = new Date(b.timestamp).getTime()
      return timeB - timeA // Newest first
    })
    return sorted
  })

  // Actions
  function addNotification(notification) {
    const newNotification = {
      id: notification.id || crypto.randomUUID(),
      type: notification.type,
      title: notification.title,
      message: notification.message,
      timestamp: notification.timestamp || new Date().toISOString(),
      read: notification.read !== undefined ? notification.read : false,
      ...(notification.metadata && { metadata: notification.metadata }),
    }

    notifications.value.push(newNotification)
  }

  function markAsRead(id) {
    const notification = notifications.value.find((n) => n.id === id)
    if (notification) {
      notification.read = true
    }
  }

  function markAllAsRead() {
    notifications.value.forEach((n) => {
      n.read = true
    })
  }

  function removeNotification(id) {
    notifications.value = notifications.value.filter((n) => n.id !== id)
  }

  function clearForProject(projectId) {
    if (!projectId) return
    notifications.value = notifications.value.filter(
      (n) => n.metadata?.project_id !== projectId
    )
  }

  function clearAll() {
    notifications.value = []
  }

  return {
    // State
    notifications,

    // Getters
    unreadCount,
    agentHealthNotifications,
    sortedNotifications,
    badgeColor,

    // Actions
    addNotification,
    markAsRead,
    markAllAsRead,
    removeNotification,
    clearForProject,
    clearAll,
  }
})
