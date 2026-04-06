<template>
  <v-menu
    v-model="menuOpen"
    :close-on-content-click="false"
    :location="compact ? 'right' : 'bottom end'"
    offset="8"
    max-width="350"
  >
    <template v-slot:activator="{ props: menuProps }">
      <!-- Compact: orb style for navbar -->
      <v-badge
        v-if="compact"
        :content="unreadCount"
        :model-value="unreadCount > 0"
        :color="badgeColor"
        overlap
        offset-x="2"
        offset-y="2"
      >
        <div
          v-bind="menuProps"
          class="nav-orb nav-orb--bell"
          :class="notificationBellClass"
          role="button"
          tabindex="0"
          aria-label="View notifications"
        >
          <v-icon size="18">mdi-bell</v-icon>
        </div>
      </v-badge>
      <!-- Default: button style for other contexts -->
      <v-badge
        v-else
        :content="unreadCount"
        :model-value="unreadCount > 0"
        :color="badgeColor"
        overlap
        offset-x="4"
        offset-y="4"
      >
        <v-btn
          v-bind="menuProps"
          icon="mdi-bell"
          variant="text"
          aria-label="View notifications"
          :class="['mr-2', notificationBellClass]"
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
          aria-label="Mark all notifications as read"
          @click="handleMarkAllRead"
        >
          Mark all read
        </v-btn>
      </v-card-title>

      <v-divider />

      <!-- Notification List -->
      <v-list
        v-if="notifications.length > 0"
        class="notification-list scrollbar-thin pa-0"
        lines="two"
      >
        <template v-for="(notification, index) in notifications" :key="notification.id">
          <v-list-item
            :class="[
              'notification-item',
              { 'notification-unread': !notification.read },
              { 'notification-navigable': !!notification.metadata?.project_id },
            ]"
            :aria-label="getNotificationAriaLabel(notification)"
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
            <v-list-item-title class="text-body-1 font-weight-medium mb-1">
              {{ notification.title }}
            </v-list-item-title>
            <v-list-item-subtitle
              :class="['text-body-2', { 'message-truncated': !notification._expanded, 'text-wrap': notification._expanded }]"
              @click.stop="toggleExpand(notification)"
            >
              {{ notification.message }}
            </v-list-item-subtitle>

            <!-- Handover 0259: Project context link -->
            <div
              v-if="notification.metadata?.project_name"
              class="mt-1"
            >
              <v-chip
                size="x-small"
                variant="tonal"
                color="primary"
                prepend-icon="mdi-folder-outline"
                class="notification-project-chip"
                :aria-label="`View project ${notification.metadata.project_name}`"
                @click.stop="navigateToProject(notification)"
              >
                {{ notification.metadata.project_name }}
              </v-chip>
            </div>

            <!-- Timestamp and Unread Indicator -->
            <template v-slot:append>
              <div class="d-flex flex-column align-end">
                <span class="text-caption text-muted-a11y">
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
        <div class="text-body-2 text-muted-a11y">No notifications</div>
      </div>
    </v-card>
  </v-menu>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { formatDistanceToNow } from 'date-fns'
import { useNotificationStore } from '@/stores/notifications'
import { useWebSocketStore } from '@/stores/websocket'

defineProps({
  compact: {
    type: Boolean,
    default: false,
  },
})

const router = useRouter()
const notificationStore = useNotificationStore()
const wsStore = useWebSocketStore()

const menuOpen = ref(false)
let unsubscribeNotification = null

// Computed properties
const notifications = computed(() => notificationStore.sortedNotifications || [])
const unreadCount = computed(() => notificationStore.unreadCount || 0)
const badgeColor = computed(() => notificationStore.badgeColor || 'error')

// Dynamic bell class based on notification priority
const notificationBellClass = computed(() => {
  if (unreadCount.value === 0) return ''
  const color = badgeColor.value
  if (color === 'warning') return 'notification-bell--warning'
  if (color === 'error') return 'notification-bell--error'
  return 'notification-bell--unread'
})

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
    context_tuning: 'mdi-tune',
    vision_analysis: 'mdi-file-document-check',
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
    context_tuning: 'info',
    vision_analysis: 'success',
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

// Handover 0259: Build descriptive ARIA label for notification items
const getNotificationAriaLabel = (notification) => {
  const projectName = notification.metadata?.project_name
  const base = `${notification.title}: ${notification.message}`
  if (projectName) {
    return `${base}. Click to view project ${projectName}`
  }
  return base
}

// Toggle message expand/collapse
const toggleExpand = (notification) => {
  notification._expanded = !notification._expanded
}

// Handover 0259: Navigate to the project associated with a notification
const navigateToProject = async (notification) => {
  const projectId = notification.metadata?.project_id
  if (!projectId) return

  if (!notification.read) {
    try {
      await notificationStore.markAsRead(notification.id)
    } catch (error) {
      console.error('[NotificationDropdown] Error marking notification as read:', error)
    }
  }

  menuOpen.value = false
  router.push({ name: 'ProjectLaunch', params: { projectId } })
}

// Handle notification click (mark as read and navigate if project context exists)
const handleNotificationClick = async (notification) => {
  if (!notification.read) {
    try {
      await notificationStore.markAsRead(notification.id)
    } catch (error) {
      console.error('[NotificationDropdown] Error marking notification as read:', error)
    }
  }

  // Handover 0831: context_tuning notifications stay on current page (no project navigation)
  // Handover 0842d: vision_analysis notifications stay on current page
  if (notification.type === 'context_tuning' || notification.type === 'vision_analysis') {
    return
  }

  // Handover 0259: Navigate to project if notification has project context
  if (notification.metadata?.project_id) {
    menuOpen.value = false
    router.push({
      name: 'ProjectLaunch',
      params: { projectId: notification.metadata.project_id },
    })
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
  notificationStore.addNotification(payload)
}

// Lifecycle hooks
// Note: agent:health_alert events are now handled by websocketEventRouter.js (Handover 0424)
onMounted(async () => {
  // Subscribe to WebSocket events
  // Note: agent:health_alert is handled by websocketEventRouter.js (Handover 0424)
  try {
    unsubscribeNotification = wsStore.on('notification:new', handleNewNotification)
  } catch (error) {
    console.warn('[NotificationDropdown] Failed to subscribe to events:', error)
  }
})

onUnmounted(() => {
  // Cleanup WebSocket subscriptions
  try {
    if (typeof unsubscribeNotification === 'function') {
      unsubscribeNotification()
    }
  } catch (error) {
    console.warn('[NotificationDropdown] Error during cleanup:', error)
  }
})
</script>

<style lang="scss" scoped>
@use '../../styles/design-tokens' as *;

/* Pulsing glow animation for error notifications (connection lost, system alerts) */
@keyframes notification-pulse-error {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(var(--v-theme-error), 0.6);
  }
  50% {
    box-shadow: 0 0 0 12px rgba(var(--v-theme-error), 0);
  }
}

/* Pulsing glow animation for warning notifications (agent health) */
@keyframes notification-pulse-warning {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(var(--v-theme-warning), 0.6);
  }
  50% {
    box-shadow: 0 0 0 12px rgba(var(--v-theme-warning), 0);
  }
}

.notification-bell--error {
  animation: notification-pulse-error 2s ease-in-out infinite;
  border-radius: 50%;
}

.notification-bell--warning {
  animation: notification-pulse-warning 2s ease-in-out infinite;
  border-radius: 50%;
}

/* Fallback for other notification types */
.notification-bell--unread {
  animation: notification-pulse-error 2s ease-in-out infinite;
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
  transition: background-color $transition-normal ease;
  padding: 12px 16px;
}

.notification-item:hover {
  background-color: rgba(var(--v-theme-primary), 0.08);
}

.notification-unread {
  background-color: rgba(var(--v-theme-primary), 0.05);
  border-left: 3px solid rgb(var(--v-theme-primary));
}

/* Handover 0259: Visual affordance for navigable notifications */
.notification-navigable {
  cursor: pointer;
}

.notification-navigable:hover {
  background-color: rgba(var(--v-theme-primary), 0.12);
}

.notification-project-chip {
  cursor: pointer;
}

.notification-empty {
  flex-shrink: 0;
  min-height: 200px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

// Orb style matching NavigationDrawer orbs
.nav-orb {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.25s ease;

  &:hover { transform: scale(1.08); }
  &:active { transform: scale(0.95); }
}

@media (max-width: 1024px) {
  .nav-orb {
    width: 44px;
    height: 44px;
  }
}

.nav-orb--bell {
  background: rgba(255, 255, 255, 0.12);
  color: rgba(255, 255, 255, 0.9);

  &:hover { background: rgba(255, 255, 255, 0.18); }
}

</style>
