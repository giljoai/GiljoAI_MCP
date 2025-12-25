/**
 * Consolidated WebSocket Store V2
 * Merges websocket.js (507 lines) + flowWebSocket.js (377 lines) + stores/websocket.js (318 lines)
 * into single, clean Pinia store (~500 lines)
 *
 * PRODUCTION-GRADE:
 * - Auto-reconnection with exponential backoff
 * - Message queue for offline support
 * - Centralized subscription tracking
 * - Integration with all Pinia stores
 * - Toast notifications
 * - Memory leak prevention
 * - Zero breaking changes
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { API_CONFIG } from '@/config/api'
import { useToast } from '@/composables/useToast'

export const useWebSocketStore = defineStore('websocket', () => {
  // ============================================
  // STATE
  // ============================================

  // WebSocket instance
  const ws = ref(null)

  // Connection state
  const clientId = ref(null)
  const connectionStatus = ref('disconnected') // 'disconnected' | 'connecting' | 'connected' | 'reconnecting'
  const connectionError = ref(null)
  const reconnectAttempts = ref(0)
  const authCredentials = ref(null)

  // Configuration
  const config = {
    maxReconnectAttempts: 10,
    reconnectDelay: 1000,
    maxReconnectDelay: 30000,
    pingInterval: 30000, // 30 seconds
    messageQueueSize: 100,
    maxEventHistory: 50,
    debug: API_CONFIG.WEBSOCKET?.debug || false,
  }

  // Message queue
  const messageQueue = ref([])

  // Subscriptions tracking (refcounted)
  // key: 'entity_type:entity_id' -> value: number (subscriber count)
  const subscriptions = ref(new Map())

  // Event handlers tracking
  const eventHandlers = ref(new Map()) // key: event type -> value: Set<handler>

  // Connection listeners
  const connectionListeners = ref(new Set())

  // Heartbeat
  const pingInterval = ref(null)

  // Stats and debug
  const stats = ref({
    messagesSent: 0,
    messagesReceived: 0,
    connectionAttempts: 0,
    lastError: null,
    connectedAt: null,
    disconnectedAt: null,
  })

  const eventHistory = ref([])

  // ============================================
  // COMPUTED
  // ============================================

  const isConnected = computed(() => connectionStatus.value === 'connected')
  const isConnecting = computed(() => connectionStatus.value === 'connecting')
  const isReconnecting = computed(() => connectionStatus.value === 'reconnecting')
  const isDisconnected = computed(() => connectionStatus.value === 'disconnected')

  // ============================================
  // CONNECTION MANAGEMENT
  // ============================================

  /**
   * Generate unique client ID
   */
  function generateClientId() {
    return `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  /**
   * Connect to WebSocket server
   * @param {Object} options - Connection options
   * @param {string} options.apiKey - API key for authentication
   * @param {string} options.token - Bearer token for authentication
   */
  async function connect(options = {}) {
    if (isConnected.value || isConnecting.value) {
      log('Already connected or connecting')
      return Promise.resolve()
    }

    const isReconnectAttempt = connectionStatus.value === 'reconnecting'
    connectionStatus.value = 'connecting'
    authCredentials.value = options
    stats.value.connectionAttempts++

    // Generate client ID if not exists
    if (!clientId.value) {
      clientId.value = generateClientId()
    }

    return new Promise((resolve, reject) => {
      try {
        // Build WebSocket URL with authentication
        const baseUrl = API_CONFIG.WEBSOCKET?.url || `ws://${window.location.hostname}:7272`
        const wsUrl = new URL(`${baseUrl}/ws/${clientId.value}`)

        // Add auth parameters if provided
        if (options.apiKey) {
          wsUrl.searchParams.append('api_key', options.apiKey)
        } else if (options.token) {
          wsUrl.searchParams.append('token', options.token)
        }

        log(`Connecting to ${wsUrl.origin}${wsUrl.pathname}`)

        ws.value = new WebSocket(wsUrl.toString())

        // Connection opened
        ws.value.onopen = () => {
          log('Connection established')
          connectionStatus.value = 'connected'
          reconnectAttempts.value = 0
          connectionError.value = null
          stats.value.connectedAt = new Date().toISOString()
          stats.value.lastError = null
          addEvent('connection', 'Connected')

          // Start heartbeat
          startHeartbeat()

          // Process queued messages
          processMessageQueue()

          // Notify connection listeners
          notifyConnectionListeners('connected', { isReconnect: isReconnectAttempt })

          // Re-subscribe to all previous subscriptions
          resubscribeAll()

          resolve()
        }

        // Message received
        ws.value.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            stats.value.messagesReceived++
            log('Message received', data)
            handleMessage(data)
          } catch (error) {
            log('Failed to parse message', error)
            stats.value.lastError = `Parse error: ${error.message}`
          }
        }

        // Connection closed
        ws.value.onclose = (event) => {
          log(`Connection closed (code: ${event.code}, reason: ${event.reason})`)
          stats.value.disconnectedAt = new Date().toISOString()
          addEvent('connection', `Closed (${event.code}: ${event.reason})`)
          handleDisconnect(event)

          if (connectionStatus.value === 'connecting') {
            reject(new Error(`Connection failed: ${event.reason || 'Unknown error'}`))
          }
        }

        // Connection error
        ws.value.onerror = (error) => {
          log('Connection error', error)
          stats.value.lastError = `Connection error: ${error.message || 'Unknown'}`
          addEvent('error', 'Connection error', error)

          if (connectionStatus.value === 'connecting') {
            connectionStatus.value = 'disconnected'
            reject(error)
          }
        }
      } catch (error) {
        log('Failed to create connection', error)
        stats.value.lastError = `Connection failed: ${error.message}`
        connectionStatus.value = 'disconnected'
        reject(error)
      }
    })
  }

  /**
   * Disconnect from WebSocket server
   */
  function disconnect() {
    log('Disconnecting')

    // Stop heartbeat
    if (pingInterval.value) {
      clearInterval(pingInterval.value)
      pingInterval.value = null
    }

    // Close WebSocket
    if (ws.value) {
      ws.value.close(1000, 'Client disconnect')
      ws.value = null
    }

    connectionStatus.value = 'disconnected'
    notifyConnectionListeners('disconnected')
  }

  /**
   * Handle disconnection and attempt reconnect
   */
  function handleDisconnect(event) {
    const wasConnected = connectionStatus.value === 'connected'

    connectionStatus.value = 'disconnected'

    // Stop heartbeat
    if (pingInterval.value) {
      clearInterval(pingInterval.value)
      pingInterval.value = null
    }

    // Notify listeners
    notifyConnectionListeners('disconnected')

    // Show toast notification if we were previously connected
    if (wasConnected) {
      const { showToast } = useToast()
      showToast({
        title: 'Connection Lost',
        message: 'Attempting to reconnect...',
        color: 'warning',
        icon: 'mdi-wifi-off',
        timeout: 5000,
      })
    }

    // Attempt reconnect if we haven't exceeded max attempts
    if (reconnectAttempts.value < config.maxReconnectAttempts) {
      attemptReconnect()
    }
  }

  /**
   * Attempt to reconnect with exponential backoff
   */
  async function attemptReconnect() {
    reconnectAttempts.value++
    connectionStatus.value = 'reconnecting'

    // Calculate delay with exponential backoff
    const delay = Math.min(
      config.reconnectDelay * Math.pow(2, reconnectAttempts.value - 1),
      config.maxReconnectDelay,
    )

    log(
      `Reconnecting in ${delay}ms (attempt ${reconnectAttempts.value}/${config.maxReconnectAttempts})`,
    )

    // Notify listeners
    notifyConnectionListeners('reconnecting', {
      attempt: reconnectAttempts.value,
      maxAttempts: config.maxReconnectAttempts,
      delay,
    })

    // Show toast notification
    const { showToast } = useToast()
    showToast({
      title: 'Reconnecting',
      message: `Attempt ${reconnectAttempts.value}/${config.maxReconnectAttempts}`,
      color: 'info',
      icon: 'mdi-wifi-sync',
      timeout: 2000,
    })

    setTimeout(async () => {
      try {
        await connect(authCredentials.value)

        // Show success toast
        showToast({
          title: 'Connection Restored',
          message: 'Successfully reconnected to server',
          color: 'success',
          icon: 'mdi-wifi',
          timeout: 3000,
        })
      } catch (error) {
        console.error('WebSocket: Reconnection failed', error)
        // Will trigger handleDisconnect again if needed
      }
    }, delay)
  }

  /**
   * Start heartbeat mechanism
   */
  function startHeartbeat() {
    if (pingInterval.value) {
      clearInterval(pingInterval.value)
    }

    // Send ping every 30 seconds
    pingInterval.value = setInterval(() => {
      if (isConnected.value) {
        send({ type: 'ping' })
      }
    }, config.pingInterval)
  }

  // ============================================
  // MESSAGE HANDLING
  // ============================================

  /**
   * Send message to server
   */
  function send(data) {
    if (!isConnected.value) {
      log('Not connected, queuing message', data)
      messageQueue.value.push(data)

      // Limit queue size
      if (messageQueue.value.length > config.messageQueueSize) {
        messageQueue.value.shift() // Remove oldest
      }

      return false
    }

    try {
      ws.value.send(JSON.stringify(data))
      stats.value.messagesSent++
      log('Message sent', data)
      return true
    } catch (error) {
      log('Failed to send message', error)
      stats.value.lastError = `Send error: ${error.message}`
      messageQueue.value.push(data)
      return false
    }
  }

  /**
   * Process queued messages
   */
  function processMessageQueue() {
    while (messageQueue.value.length > 0 && isConnected.value) {
      const message = messageQueue.value.shift()
      send(message)
    }
  }

  /**
   * Handle incoming message
   *
   * Normalizes payload structure for backward compatibility:
   * - HTTP bridge sends flat: { type, project_id, tenant_key, ... }
   * - Direct broadcast sends nested: { type, data: { project_id, tenant_key, ... } }
   *
   * After normalization, handlers always receive flat payloads with data accessible
   * at the top level (e.g., payload.tenant_key works for both formats).
   *
   * @see Handover 0290 - WebSocket Payload Normalization
   */
  function handleMessage(data) {
    const { type, ...rest } = data

    // Normalize nested payloads (Handover 0290)
    // If payload has 'data' key with object value, merge nested fields to top level
    // This provides backward compatibility for both:
    // - HTTP bridge (flat): { type, project_id, tenant_key, ... }
    // - Direct broadcast (nested): { type, data: { project_id, tenant_key, ... } }
    let payload = rest
    if (rest.data && typeof rest.data === 'object' && !Array.isArray(rest.data)) {
      payload = { ...rest, ...rest.data } // Merge nested to top level, preserve original
    }

    // Handle system messages
    switch (type) {
      case 'pong':
        // Heartbeat response
        break

      case 'ping':
        // Server heartbeat - respond with pong
        send({ type: 'pong' })
        break

      case 'subscribed':
      case 'unsubscribed':
        log(`${type} to ${payload.entity_type}:${payload.entity_id}`)
        addEvent('subscription', `${type} ${payload.entity_type}:${payload.entity_id}`)
        break

      case 'error':
        log('Server error', payload)
        stats.value.lastError = `Server error: ${payload.message || payload.error}`
        addEvent('error', 'Server error', payload)
        break

      default:
        // Route to registered handlers
        notifyMessageHandlers(type, payload)
    }
  }

  /**
   * Notify message handlers
   */
  function notifyMessageHandlers(type, payload) {
    // Call specific handlers for this type
    const handlers = eventHandlers.value.get(type)
    if (handlers) {
      handlers.forEach((handler) => {
        try {
          handler(payload)
        } catch (error) {
          console.error(`Error in message handler for ${type}:`, error)
        }
      })
    }

    // Call wildcard handlers
    const wildcardHandlers = eventHandlers.value.get('*')
    if (wildcardHandlers) {
      wildcardHandlers.forEach((handler) => {
        try {
          handler({ type, ...payload })
        } catch (error) {
          console.error('Error in wildcard handler:', error)
        }
      })
    }
  }

  // ============================================
  // EVENT HANDLER MANAGEMENT
  // ============================================

  /**
   * Register message handler
   * @param {string} type - Message type (or '*' for all)
   * @param {Function} handler - Handler function
   * @returns {Function} Unsubscribe function
   */
  function on(type, handler) {
    if (!eventHandlers.value.has(type)) {
      eventHandlers.value.set(type, new Set())
    }

    eventHandlers.value.get(type).add(handler)
    log(`Registered handler for ${type}`)

    // Return unsubscribe function
    return () => off(type, handler)
  }

  /**
   * Remove message handler
   */
  function off(type, handler) {
    const handlers = eventHandlers.value.get(type)
    if (handlers) {
      handlers.delete(handler)
      if (handlers.size === 0) {
        eventHandlers.value.delete(type)
      }
      log(`Removed handler for ${type}`)
    }
  }

  // ============================================
  // CONNECTION LISTENER MANAGEMENT
  // ============================================

  /**
   * Register connection state listener
   */
  function onConnectionChange(callback) {
    connectionListeners.value.add(callback)

    // Return unsubscribe function
    return () => {
      connectionListeners.value.delete(callback)
    }
  }

  /**
   * Notify connection listeners
   */
  function notifyConnectionListeners(state, data = {}) {
    connectionListeners.value.forEach((listener) => {
      try {
        listener({ state, ...data })
      } catch (error) {
        console.error('Error in connection listener:', error)
      }
    })
  }

  // ============================================
  // SUBSCRIPTION MANAGEMENT
  // ============================================

  /**
   * Subscribe to entity updates
   */
  function subscribe(entityType, entityId) {
    const key = `${entityType}:${entityId}`

    const currentCount = subscriptions.value.get(key) || 0
    const nextCount = currentCount + 1
    subscriptions.value.set(key, nextCount)

    if (currentCount > 0) {
      log(`Subscription refcount incremented for ${key} (${nextCount})`)
      return key
    }

    const success = send({
      type: 'subscribe',
      entity_type: entityType,
      entity_id: entityId,
    })

    if (success || !isConnected.value) {
      // Subscription is tracked even if queued (will be sent on reconnect)
      log(`Subscribed to ${key}`)
    }

    return key
  }

  /**
   * Unsubscribe from entity updates
   */
  function unsubscribe(entityType, entityId) {
    const key = `${entityType}:${entityId}`

    const currentCount = subscriptions.value.get(key) || 0

    if (currentCount <= 0) {
      log(`Not subscribed to ${key}`)
      return false
    }

    if (currentCount > 1) {
      const nextCount = currentCount - 1
      subscriptions.value.set(key, nextCount)
      log(`Subscription refcount decremented for ${key} (${nextCount})`)
      return true
    }

    // Last subscriber: actually unsubscribe on the wire.
    send({ type: 'unsubscribe', entity_type: entityType, entity_id: entityId })

    subscriptions.value.delete(key)
    log(`Unsubscribed from ${key}`)
    return true
  }

  /**
   * Re-subscribe to all previous subscriptions (on reconnect)
   */
  function resubscribeAll() {
    log(`Re-subscribing to ${subscriptions.value.size} subscriptions`)

    subscriptions.value.forEach((count, key) => {
      if (!count || count <= 0) {
        return
      }
      const [entityType, entityId] = key.split(':')
      send({
        type: 'subscribe',
        entity_type: entityType,
        entity_id: entityId,
      })
    })
  }

  /**
   * Convenience: Subscribe to project updates
   */
  function subscribeToProject(projectId) {
    return subscribe('project', projectId)
  }

  /**
   * Convenience: Subscribe to agent updates
   */
  function subscribeToAgent(agentId) {
    return subscribe('agent', agentId)
  }

  // ============================================
  // DEBUG & LOGGING
  // ============================================

  /**
   * Debug logging
   */
  function log(message, data = null) {
    if (config.debug) {
      console.log(`[WebSocketV2] ${message}`, data || '')
    }

    // Add to event history
    addEvent('log', message, data)
  }

  /**
   * Add event to history
   */
  function addEvent(type, message, data = null) {
    const event = {
      type,
      message,
      data,
      timestamp: new Date().toISOString(),
    }

    eventHistory.value.unshift(event)

    // Limit history size
    if (eventHistory.value.length > config.maxEventHistory) {
      eventHistory.value.pop()
    }
  }

  /**
   * Get connection info
   */
  function getConnectionInfo() {
    return {
      state: connectionStatus.value,
      clientId: clientId.value,
      reconnectAttempts: reconnectAttempts.value,
      maxReconnectAttempts: config.maxReconnectAttempts,
      messageQueueSize: messageQueue.value.length,
      subscriptionsCount: subscriptions.value.size,
      stats: stats.value,
      eventHistory: eventHistory.value.slice(0, 10),
    }
  }

  /**
   * Get debug info
   */
  function getDebugInfo() {
    return {
      state: connectionStatus.value,
      isConnected: isConnected.value,
      isConnecting: isConnecting.value,
      isReconnecting: isReconnecting.value,
      clientId: clientId.value,
      reconnectAttempts: reconnectAttempts.value,
      maxReconnectAttempts: config.maxReconnectAttempts,
      messageQueueSize: messageQueue.value.length,
      subscriptions: Array.from(subscriptions.value.keys()),
      stats: stats.value,
      eventHistory: eventHistory.value.slice(0, 10),
      debug: config.debug,
      wsUrl: ws.value?.url || 'Not connected',
    }
  }

  /**
   * Enable/disable debug mode
   */
  function setDebugMode(enabled) {
    config.debug = enabled
    log(`Debug mode ${enabled ? 'enabled' : 'disabled'}`)
  }

  // ============================================
  // RETURN STORE API
  // ============================================

  return {
    // State
    connectionStatus,
    connectionError,
    reconnectAttempts,
    clientId,
    messageQueueSize: computed(() => messageQueue.value.length),
    subscriptions: computed(() => Array.from(subscriptions.value.keys())),

    // Computed
    isConnected,
    isConnecting,
    isReconnecting,
    isDisconnected,

    // Connection
    connect,
    disconnect,

    // Messaging
    send,
    on,
    off,
    onConnectionChange,

    // Subscriptions
    subscribe,
    unsubscribe,
    subscribeToProject,
    subscribeToAgent,

    // Debug
    getConnectionInfo,
    getDebugInfo,
    setDebugMode,
  }
})
