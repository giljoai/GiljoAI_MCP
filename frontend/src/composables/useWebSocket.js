/**
 * WebSocket Composable for Agent Orchestration
 * Provides reactive WebSocket connection for real-time agent updates
 */

import { ref, onMounted, onUnmounted } from 'vue'
import { webSocketService } from '@/services/websocket'

export function useWebSocket() {
  const isConnected = ref(false)
  const lastMessage = ref(null)
  const error = ref(null)

  // Message handlers registry
  const handlers = new Map()

  /**
   * Register a message handler for specific event type
   * @param {string} eventType - Event type to listen for
   * @param {Function} callback - Handler function
   */
  const on = (eventType, callback) => {
    if (!handlers.has(eventType)) {
      handlers.set(eventType, new Set())
    }
    handlers.get(eventType).add(callback)

    // Register with WebSocket service
    webSocketService.on(eventType, callback)
  }

  /**
   * Unregister a message handler
   * @param {string} eventType - Event type
   * @param {Function} callback - Handler function
   */
  const off = (eventType, callback) => {
    if (handlers.has(eventType)) {
      handlers.get(eventType).delete(callback)
      webSocketService.off(eventType, callback)
    }
  }

  /**
   * Send message through WebSocket
   * @param {string} type - Message type
   * @param {Object} data - Message payload
   */
  const send = (type, data) => {
    try {
      webSocketService.send({ type, ...data })
    } catch (err) {
      console.error('[WebSocket] Send failed:', err)
      error.value = err.message
    }
  }

  /**
   * Connect to WebSocket server
   */
  const connect = async () => {
    try {
      if (!webSocketService.isConnected) {
        await webSocketService.connect()
      }
      isConnected.value = true
      error.value = null
    } catch (err) {
      console.error('[WebSocket] Connection failed:', err)
      error.value = err.message
      isConnected.value = false
    }
  }

  /**
   * Disconnect from WebSocket server
   */
  const disconnect = () => {
    // Clean up all registered handlers
    handlers.forEach((callbacks, eventType) => {
      callbacks.forEach(callback => {
        webSocketService.off(eventType, callback)
      })
    })
    handlers.clear()
  }

  // Auto-connect on mount if WebSocket service is available
  onMounted(() => {
    if (webSocketService && webSocketService.isConnected) {
      isConnected.value = true
    }
  })

  // Clean up on unmount
  onUnmounted(() => {
    disconnect()
  })

  return {
    isConnected,
    lastMessage,
    error,
    on,
    off,
    send,
    connect,
    disconnect
  }
}
