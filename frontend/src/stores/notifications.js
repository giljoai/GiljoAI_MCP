/**
 * Notifications store (IMP-5037a Phase 2 — DB-backed bell)
 *
 * Replaces the prior in-memory-only store with a REST-backed implementation.
 * Server is source of truth: fetch() → GET /api/notifications on mount.
 * Real-time updates via notification:new WS event (merged by id).
 *
 * Preserved from prior store:
 *  - addNotification() — retained as the WS event handler shim (used by
 *    NotificationDropdown via wsStore.on('notification:new', ...) and by
 *    clearForProject / clearAll callers).
 *  - markAsRead() / markAllAsRead() — local-only fallback kept for
 *    in-memory callers (agent_health events that predate DB persistence).
 *  - removeNotification() / clearForProject() / clearAll() — preserved.
 *  - type→icon/color mapping lives in NotificationDropdown (component layer).
 *  - badgeColor uses severity field from server response when available,
 *    falling back to type-based heuristics for legacy in-memory notifications.
 *
 * New exports: fetch(), markRead(id), markDismissed(id), handleWsNewNotification(data)
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/services/api'

/** Normalize a raw notification from the server into local store shape. */
function normalizeServerNotif(raw) {
  return {
    // Server fields — preserved verbatim for PATCH response merging
    id: raw.id,
    type: raw.type,
    severity: raw.severity ?? null,
    title: raw.title,
    // Support both body (server) and message (legacy in-memory)
    body: raw.body ?? null,
    message: raw.body ?? raw.message ?? null,
    payload: raw.payload ?? null,
    read_at: raw.read_at ?? null,
    dismissed_at: raw.dismissed_at ?? null,
    // IMP-5037b Phase 1 fields — banner surface routing
    resolved_at: raw.resolved_at ?? null,
    surface: raw.surface ?? null,
    role_filter: raw.role_filter ?? null,
    cta_label: raw.cta_label ?? null,
    cta_route: raw.cta_route ?? null,
    dismissible: raw.dismissible ?? null,
    created_at: raw.created_at ?? null,
    // Computed convenience flag
    read: raw.read_at !== null && raw.read_at !== undefined,
    // Legacy compat: timestamp used by sortedNotifications fallback
    timestamp: raw.created_at ?? raw.timestamp ?? new Date().toISOString(),
    // Preserve metadata if present (legacy in-memory notifications)
    ...(raw.metadata != null ? { metadata: raw.metadata } : {}),
  }
}

export const useNotificationStore = defineStore('notifications', () => {
  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------
  const notifications = ref([])

  // ---------------------------------------------------------------------------
  // Getters
  // ---------------------------------------------------------------------------
  const unreadCount = computed(() => notifications.value.filter((n) => !n.read).length)

  /**
   * Badge color based on highest-priority unread notification.
   * Priority (highest → lowest):
   *  - severity: 'critical' | type: connection_lost | system_alert → error (red)
   *  - severity: 'error'                                           → error (red)
   *  - severity: 'warning' | type: agent_health | api_key.expiring_soon → warning
   *  - severity: 'info' | type: context_tuning                    → info
   *  - others                                                      → primary
   * When no unread → 'error' (default badge; same as prior store behavior).
   */
  const badgeColor = computed(() => {
    const unread = notifications.value.filter((n) => !n.read)
    if (unread.length === 0) return 'error'

    const hasCritical = unread.some(
      (n) =>
        n.severity === 'critical' ||
        n.type === 'connection_lost' ||
        n.type === 'system_alert',
    )
    if (hasCritical) return 'error'

    const hasError = unread.some((n) => n.severity === 'error')
    if (hasError) return 'error'

    const hasWarning = unread.some(
      (n) =>
        n.severity === 'warning' ||
        n.type === 'agent_health' ||
        n.type === 'api_key.expiring_soon',
    )
    if (hasWarning) return 'warning'

    const hasContextTuning = unread.some(
      (n) => n.type === 'context_tuning' || n.severity === 'info',
    )
    if (hasContextTuning) return 'info'

    return 'primary'
  })

  const sortedNotifications = computed(() => {
    const sorted = [...notifications.value]
    sorted.sort((a, b) => {
      const timeA = new Date(a.timestamp ?? a.created_at ?? 0).getTime()
      const timeB = new Date(b.timestamp ?? b.created_at ?? 0).getTime()
      return timeB - timeA // Newest first
    })
    return sorted
  })

  /**
   * IMP-5037b: Banner-surface notifications.
   *
   * Returns rows where:
   *  - surface is 'banner' or 'both' (bell-only rows are excluded)
   *  - dismissed_at is null (user has not dismissed this row)
   *  - resolved_at is null (backend has not resolved this row)
   *
   * Role-filter enforcement is server-side; components add a defense-in-depth
   * guard via userHasRole(n.role_filter) before rendering.
   */
  const bannerNotifications = computed(() =>
    notifications.value.filter(
      (n) =>
        (n.surface === 'banner' || n.surface === 'both') &&
        n.dismissed_at == null &&
        n.resolved_at == null,
    ),
  )

  /**
   * IMP-6042: Single highest-precedence active banner type.
   *
   * Precedence order (highest → lowest):
   *   saas.account_deletion_scheduled > saas.subscription_lapsed >
   *   saas.trial_expired > saas.trial_warning
   *
   * Derived from bannerNotifications so dismissed/resolved rows are already
   * excluded. The notification bell (NotificationDropdown) reads
   * bannerNotifications (or sortedNotifications) directly — this getter is a
   * DISPLAY concern only and does NOT suppress rows at the source.
   *
   * Returns the winning type string, or null when no banner rows are active.
   */
  const BANNER_PRECEDENCE = [
    'saas.account_deletion_scheduled',
    'saas.subscription_lapsed',
    'saas.trial_expired',
    'saas.trial_warning',
  ]

  const activeBannerType = computed(() => {
    const active = bannerNotifications.value
    if (active.length === 0) return null
    for (const type of BANNER_PRECEDENCE) {
      if (active.some((n) => n.type === type)) return type
    }
    return null
  })

  // ---------------------------------------------------------------------------
  // Actions — REST-backed
  // ---------------------------------------------------------------------------

  /**
   * Fetch current user's notifications from the server.
   * Replaces local list on each call (server is authoritative).
   * Called on component mount and on explicit refresh.
   */
  async function fetch() {
    try {
      const response = await api.notifications.list()
      notifications.value = (response.data ?? []).map(normalizeServerNotif)
    } catch (error) {
      // Fail silently — keep existing notifications to avoid blank bell on transient errors.
      console.error('[NotificationStore] Failed to fetch notifications:', error)
    }
  }

  /**
   * Mark a notification as read via PATCH /api/notifications/{id}/read.
   * Updates local state from server response.
   */
  async function markRead(id) {
    try {
      const response = await api.notifications.markRead(id)
      const updated = normalizeServerNotif(response.data)
      const idx = notifications.value.findIndex((n) => n.id === id)
      if (idx !== -1) {
        notifications.value[idx] = updated
      }
    } catch (error) {
      console.error('[NotificationStore] Failed to mark notification as read:', error)
    }
  }

  /**
   * Mark a notification as dismissed via PATCH /api/notifications/{id}/dismiss.
   * Removes from local list on success (dismissed items are excluded by default).
   */
  async function markDismissed(id) {
    try {
      await api.notifications.markDismissed(id)
      notifications.value = notifications.value.filter((n) => n.id !== id)
    } catch (error) {
      console.error('[NotificationStore] Failed to dismiss notification:', error)
    }
  }

  // ---------------------------------------------------------------------------
  // Actions — WS event handler
  // ---------------------------------------------------------------------------

  /**
   * Handle a notification:new WS event payload.
   * Merges by id — no-op if the notification is already present.
   * Callers should filter by user_id (null=broadcast OR == current user) before calling.
   */
  function handleWsNewNotification(data) {
    if (!data?.id) return
    const exists = notifications.value.some((n) => n.id === data.id)
    if (exists) return
    notifications.value.push(normalizeServerNotif(data))
  }

  // ---------------------------------------------------------------------------
  // Legacy in-memory actions (preserved for backward compat)
  // ---------------------------------------------------------------------------

  /**
   * Add a notification directly (in-memory, no REST call).
   * Retained for callers that emit local events (e.g. agent_health WS events
   * that are not yet persisted in the DB). Deduplicates by id.
   */
  function addNotification(notification) {
    const newNotification = {
      id: notification.id || (crypto.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`),
      type: notification.type,
      title: notification.title,
      message: notification.message ?? notification.body ?? null,
      timestamp: notification.timestamp || notification.created_at || new Date().toISOString(),
      read: notification.read !== undefined ? notification.read : false,
      // Spread optional fields only when present — preserves exact shape for legacy callers
      ...(notification.body !== undefined ? { body: notification.body } : {}),
      ...(notification.created_at !== undefined ? { created_at: notification.created_at } : {}),
      ...(notification.severity !== undefined ? { severity: notification.severity } : {}),
      ...(notification.read_at !== undefined ? { read_at: notification.read_at } : {}),
      ...(notification.dismissed_at !== undefined ? { dismissed_at: notification.dismissed_at } : {}),
      ...(notification.payload !== undefined ? { payload: notification.payload } : {}),
      ...(notification.metadata != null ? { metadata: notification.metadata } : {}),
    }

    // Dedup by id
    const exists = notifications.value.some((n) => n.id === newNotification.id)
    if (!exists) {
      notifications.value.push(newNotification)
    }
  }

  /** Mark a notification as read locally (no REST call). Preserved for agent_health callers. */
  function markAsRead(id) {
    const notification = notifications.value.find((n) => n.id === id)
    if (notification) {
      notification.read = true
      notification.read_at = notification.read_at ?? new Date().toISOString()
    }
  }

  /** Mark all notifications as read locally (no REST call). */
  function markAllAsRead() {
    notifications.value.forEach((n) => {
      n.read = true
      n.read_at = n.read_at ?? new Date().toISOString()
    })
  }

  function removeNotification(id) {
    notifications.value = notifications.value.filter((n) => n.id !== id)
  }

  function clearForProject(projectId) {
    if (!projectId) return
    notifications.value = notifications.value.filter(
      (n) => n.metadata?.project_id !== projectId,
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
    sortedNotifications,
    bannerNotifications,
    activeBannerType,
    badgeColor,

    // REST-backed actions
    fetch,
    markRead,
    markDismissed,
    handleWsNewNotification,

    // Legacy in-memory actions (preserved for backward compat)
    addNotification,
    markAsRead,
    markAllAsRead,
    removeNotification,
    clearForProject,
    clearAll,
  }
})
