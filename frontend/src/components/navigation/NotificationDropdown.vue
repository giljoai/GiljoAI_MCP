<template>
  <v-menu
    v-model="menuOpen"
    :close-on-content-click="false"
    location="bottom end"
    offset="8"
    max-width="350"
  >
    <template v-slot:activator="{ props: menuProps }">
      <v-badge
        :content="unreadCount"
        :model-value="unreadCount > 0"
        color="error"
        overlap
        offset-x="4"
        offset-y="4"
      >
        <v-btn
          v-bind="menuProps"
          icon="mdi-bell"
          variant="text"
          aria-label="View notifications"
          :class="['mr-2', { 'notification-bell--unread': unreadCount > 0 }]"
        ></v-btn>
      </v-badge>
    </template>

    <v-card class="notification-dropdown" elevation="8">
      <!-- Header -->
      <v-card-title class="d-flex align-center justify-space-between py-3 px-4 notification-header">
        <span class="text-subtitle-1 font-weight-bold">Notifications</span>
        <v-btn
          v-if="unreadCount > 0"
          variant="text"
          size="small"
          color="primary"
          @click="handleMarkAllRead"
          aria-label="Mark all notifications as read"
        >
          Mark all read
        </v-btn>
      </v-card-title>

      <v-divider />

      <!-- Notification List -->
      <v-list
        v-if="notifications.length > 0"
        class="notification-list pa-0"
        lines="two"
      >
        <template v-for="(notification, index) in notifications" :key="notification.id">
          <v-list-item
            :class="{ 'notification-unread': !notification.read }"
            class="notification-item"
            @click="handleNotificationClick(notification)"
          >
            <!-- Icon -->
            <template v-slot:prepend>
              <v-icon
                :icon="getNotificationIcon(notification.type)"
                :color="getNotificationColor(notification.type)"
                size="24"
              />
            </template>

            <!-- Content -->
            <v-list-item-title class="text-body-2 font-weight-medium mb-1">
              {{ notification.title }}
            </v-list-item-title>
            <v-list-item-subtitle
              :class="['text-caption', { 'message-truncated': !notification._expanded, 'text-wrap': notification._expanded }]"
              @click.stop="toggleExpand(notification)"
            >
              {{ notification.message }}
            </v-list-item-subtitle>

            <!-- Timestamp and Unread Indicator -->
            <template v-slot:append>
              <div class="d-flex flex-column align-end">
                <span class="text-caption text-medium-emphasis">
                  {{ formatTimestamp(notification.timestamp) }}
                </span>
                <v-icon
                  v-if="!notification.read"
                  icon="mdi-circle"
                  color="primary"
                  size="8"
                  class="mt-1"
                />
              </div>
            </template>
          </v-list-item>

          <v-divider v-if="index < notifications.length - 1" />
        </template>
      </v-list>

      <!-- Empty State -->
      <div v-else class="notification-empty pa-8 text-center">
        <v-icon icon="mdi-bell-outline" size="48" color="grey-lighten-1" class="mb-3" />
        <div class="text-body-2 text-medium-emphasis">No notifications</div>
      </div>
    </v-card>
  </v-menu>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { formatDistanceToNow } from 'date-fns'
import { useNotificationStore } from '@/stores/notifications'
import { useWebSocketStore } from '@/stores/websocket'

const notificationStore = useNotificationStore()
const wsStore = useWebSocketStore()

const menuOpen = ref(false)
let unsubscribeNotification = null

// Computed properties
const notifications = computed(() => notificationStore.sortedNotifications || [])
const unreadCount = computed(() => notificationStore.unreadCount || 0)

// Get icon based on notification type
const getNotificationIcon = (type) => {
  const iconMap = {
    agent_health: 'mdi-clock-alert',
    agent_status: 'mdi-robot',
    project_update: 'mdi-folder-edit',
    system_alert: 'mdi-alert-circle',
    message_received: 'mdi-message-alert',
    connection_lost: 'mdi-wifi-off',
    connection_restored: 'mdi-wifi-check',
    success: 'mdi-check-circle',
    error: 'mdi-alert-circle',
    info: 'mdi-information',
    warning: 'mdi-alert',
  }
  return iconMap[type] || 'mdi-bell'
}

// Get color based on notification type
const getNotificationColor = (type) => {
  const colorMap = {
    agent_health: 'warning',
    agent_status: 'info',
    project_update: 'primary',
    system_alert: 'error',
    message_received: 'success',
    connection_lost: 'error',
    connection_restored: 'success',
    success: 'success',
    error: 'error',
    info: 'info',
    warning: 'warning',
  }
  return colorMap[type] || 'default'
}

// Format timestamp to relative time
const formatTimestamp = (timestamp) => {
  if (!timestamp) return ''
  try {
    return formatDistanceToNow(new Date(timestamp), { addSuffix: true })
  } catch (error) {
    console.error('[NotificationDropdown] Error formatting timestamp:', error)
    return ''
  }
}

// Toggle message expand/collapse
const toggleExpand = (notification) => {
  notification._expanded = !notification._expanded
}

// Handle notification click (mark as read)
const handleNotificationClick = async (notification) => {
  if (!notification.read) {
    try {
      await notificationStore.markAsRead(notification.id)
    } catch (error) {
      console.error('[NotificationDropdown] Error marking notification as read:', error)
    }
  }

  // Optionally handle navigation or action based on notification type
  if (notification.action_url) {
    // Router navigation could be added here if needed
    console.log('[NotificationDropdown] Notification action:', notification.action_url)
  }
}

// Mark all notifications as read
const handleMarkAllRead = async () => {
  try {
    await notificationStore.markAllAsRead()
  } catch (error) {
    console.error('[NotificationDropdown] Error marking all as read:', error)
  }
}

// WebSocket event handlers
const handleNewNotification = (payload) => {
  console.log('[NotificationDropdown] New notification received:', payload)
  notificationStore.addNotification(payload)
}

// Lifecycle hooks
// Note: agent:health_alert events are now handled by websocketEventRouter.js (Handover 0424)
onMounted(async () => {
  console.log('[NotificationDropdown] Component mounted')

  // Subscribe to WebSocket events
  // Note: agent:health_alert is handled by websocketEventRouter.js (Handover 0424)
  try {
    unsubscribeNotification = wsStore.on('notification:new', handleNewNotification)
    console.log('[NotificationDropdown] Subscribed to notification events')
  } catch (error) {
    console.warn('[NotificationDropdown] Failed to subscribe to events:', error)
  }

  // Note: No need to fetch initial notifications since the store
  // starts empty and will be populated via WebSocket events
  console.log('[NotificationDropdown] Initial notifications:', notifications.value.length)
})

onUnmounted(() => {
  console.log('[NotificationDropdown] Component unmounting')

  // Cleanup WebSocket subscriptions
  try {
    if (typeof unsubscribeNotification === 'function') {
      unsubscribeNotification()
    }
    console.log('[NotificationDropdown] Unsubscribed from notification events')
  } catch (error) {
    console.warn('[NotificationDropdown] Error during cleanup:', error)
  }
})
</script>

<style scoped>
/* Pulsing glow animation for unread notifications */
@keyframes notification-pulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(var(--v-theme-error), 0.6);
  }
  50% {
    box-shadow: 0 0 0 12px rgba(var(--v-theme-error), 0);
  }
}

.notification-bell--unread {
  animation: notification-pulse 2s ease-in-out infinite;
  border-radius: 50%;
}

.notification-dropdown {
  width: 420px;
  max-height: 500px;
  display: flex;
  flex-direction: column;
}

/* Message truncation - click to expand */
.message-truncated {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  cursor: pointer;
}

.message-truncated:hover {
  text-decoration: underline;
  text-decoration-style: dotted;
}

.notification-header {
  background-color: rgba(var(--v-theme-surface-variant), 0.3);
  flex-shrink: 0;
}

.notification-list {
  max-height: 400px;
  overflow-y: auto;
  flex: 1 1 auto;
}

.notification-item {
  cursor: pointer;
  transition: background-color 0.2s ease;
  padding: 12px 16px;
}

.notification-item:hover {
  background-color: rgba(var(--v-theme-primary), 0.08);
}

.notification-unread {
  background-color: rgba(var(--v-theme-primary), 0.05);
  border-left: 3px solid rgb(var(--v-theme-primary));
}

.notification-empty {
  flex-shrink: 0;
  min-height: 200px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

/* Scrollbar styling */
.notification-list::-webkit-scrollbar {
  width: 6px;
}

.notification-list::-webkit-scrollbar-track {
  background: transparent;
}

.notification-list::-webkit-scrollbar-thumb {
  background-color: rgba(var(--v-theme-on-surface), 0.2);
  border-radius: 3px;
}

.notification-list::-webkit-scrollbar-thumb:hover {
  background-color: rgba(var(--v-theme-on-surface), 0.3);
}
</style>
