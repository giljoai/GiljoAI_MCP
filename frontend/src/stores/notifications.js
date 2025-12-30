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
    const index = notifications.value.findIndex((n) => n.id === id)
    if (index !== -1) {
      notifications.value.splice(index, 1)
    }
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

    // Actions
    addNotification,
    markAsRead,
    markAllAsRead,
    removeNotification,
    clearAll,
  }
})
