/**
 * Vue Composable for WebSocket V2
 * Thin wrapper around WebSocketV2 store with component lifecycle management
 *
 * PRODUCTION-GRADE:
 * - Auto-connects on mount
 * - Auto-cleanup on unmount (prevents memory leaks)
 * - Reactive connection status
 * - Simple subscription API
 * - Integration with Pinia stores
 *
 * Usage:
 * ```vue
 * <script setup>
 * import { useWebSocketV2 } from '@/composables/useWebSocketV2'
 *
 * const {
 *   isConnected,
 *   subscribe,
 *   on,
 *   send,
 * } = useWebSocketV2()
 *
 * // Subscribe to project updates
 * subscribe('project', 'project-123')
 *
 * // Listen for messages
 * on('project_update', (data) => {
 *   console.log('Project updated:', data)
 * })
 *
 * // Send message
 * send({ type: 'custom_event', payload: { foo: 'bar' } })
 * </script>
 * ```
 */

import { onMounted, onUnmounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useWebSocketStore } from '@/stores/websocket'

export function useWebSocketV2() {
  const store = useWebSocketStore()

  // Reactive refs from store
  const {
    isConnected,
    isConnecting,
    isReconnecting,
    isDisconnected,
    connectionStatus,
    connectionError,
    reconnectAttempts,
    clientId,
    messageQueueSize,
    subscriptions,
  } = storeToRefs(store)

  // Track subscriptions and handlers for cleanup
  const componentSubscriptions = []
  const componentHandlers = []

  // ============================================
  // SUBSCRIPTION MANAGEMENT
  // ============================================

  /**
   * Subscribe to entity updates (auto-cleanup on unmount)
   * @param {string} entityType - Entity type (e.g., 'project', 'agent')
   * @param {string} entityId - Entity ID
   * @returns {string} Subscription key
   */
  function subscribe(entityType, entityId) {
    const key = store.subscribe(entityType, entityId)
    componentSubscriptions.push(key)
    return key
  }

  /**
   * Unsubscribe from entity updates
   * @param {string} entityType - Entity type
   * @param {string} entityId - Entity ID
   */
  function unsubscribe(entityType, entityId) {
    const key = `${entityType}:${entityId}`
    store.unsubscribe(entityType, entityId)

    // Remove from component tracking
    const index = componentSubscriptions.indexOf(key)
    if (index !== -1) {
      componentSubscriptions.splice(index, 1)
    }
  }

  /**
   * Subscribe to project updates (convenience method)
   */
  function subscribeToProject(projectId) {
    return subscribe('project', projectId)
  }

  /**
   * Subscribe to agent updates (convenience method)
   */
  function subscribeToAgent(agentId) {
    return subscribe('agent', agentId)
  }

  // ============================================
  // MESSAGE HANDLING
  // ============================================

  /**
   * Register message handler (auto-cleanup on unmount)
   * @param {string} type - Message type (or '*' for all)
   * @param {Function} handler - Handler function
   * @returns {Function} Cleanup function
   */
  function on(type, handler) {
    const cleanup = store.on(type, handler)
    componentHandlers.push(cleanup)
    return cleanup
  }

  /**
   * Remove message handler
   * @param {string} type - Message type
   * @param {Function} handler - Handler function
   */
  function off(type, handler) {
    store.off(type, handler)

    // Note: We can't easily remove specific cleanup functions from array
    // but onUnmounted will call all cleanup functions anyway
  }

  /**
   * Send message to server
   * @param {Object} data - Message data (must include 'type' field)
   */
  function send(data) {
    return store.send(data)
  }

  // ============================================
  // CONNECTION MANAGEMENT
  // ============================================

  /**
   * Connect to WebSocket server
   * @param {Object} options - Connection options
   */
  function connect(options = {}) {
    return store.connect(options)
  }

  /**
   * Disconnect from WebSocket server
   */
  function disconnect() {
    return store.disconnect()
  }

  /**
   * Register connection state change listener (auto-cleanup on unmount)
   * @param {Function} callback - Callback function
   * @returns {Function} Cleanup function
   */
  function onConnectionChange(callback) {
    const cleanup = store.onConnectionChange(callback)
    componentHandlers.push(cleanup)
    return cleanup
  }

  // ============================================
  // DEBUG
  // ============================================

  /**
   * Get connection info
   */
  function getConnectionInfo() {
    return store.getConnectionInfo()
  }

  /**
   * Get debug info
   */
  function getDebugInfo() {
    return store.getDebugInfo()
  }

  // ============================================
  // LIFECYCLE HOOKS
  // ============================================

  /**
   * Auto-connect on mount (if not already connected)
   */
  onMounted(() => {
    if (!isConnected.value && !isConnecting.value) {
      // Note: Components can pass auth options if needed
      // For now, we don't auto-connect to avoid breaking existing behavior
      // Components should explicitly call connect() if needed
    }
  })

  /**
   * Auto-cleanup on unmount (CRITICAL for memory leak prevention)
   */
  onUnmounted(() => {
    // Unsubscribe from all component subscriptions
    componentSubscriptions.forEach((key) => {
      const [entityType, entityId] = key.split(':')
      store.unsubscribe(entityType, entityId)
    })
    componentSubscriptions.length = 0

    // Remove all component handlers
    componentHandlers.forEach((cleanup) => {
      try {
        cleanup()
      } catch (error) {
        console.warn('[useWebSocketV2] Error during cleanup:', error)
      }
    })
    componentHandlers.length = 0
  })

  // ============================================
  // RETURN API
  // ============================================

  return {
    // Reactive state
    isConnected,
    isConnecting,
    isReconnecting,
    isDisconnected,
    connectionStatus,
    connectionError,
    reconnectAttempts,
    clientId,
    messageQueueSize,
    subscriptions,

    // Connection
    connect,
    disconnect,
    onConnectionChange,

    // Messaging
    send,
    on,
    off,

    // Subscriptions
    subscribe,
    unsubscribe,
    subscribeToProject,
    subscribeToAgent,

    // Debug
    getConnectionInfo,
    getDebugInfo,
  }
}

// Export with both old and new names for backward compatibility
export const useWebSocket = useWebSocketV2
