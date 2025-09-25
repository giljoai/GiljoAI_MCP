/**
 * Native WebSocket Service for GiljoAI MCP
 * Implements real-time communication with auto-reconnect and message queuing
 */

import { API_CONFIG } from '@/config/api'

class WebSocketService {
  constructor() {
    this.ws = null
    this.clientId = null
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 10
    this.reconnectDelay = 1000
    this.maxReconnectDelay = 30000
    this.pingInterval = null
    this.connectionListeners = new Set()
    this.messageHandlers = new Map()
    this.messageQueue = []
    this.isConnecting = false
    this.isConnected = false
    this.shouldReconnect = true
    this.authCredentials = null
    
    // Debug mode
    this.debug = API_CONFIG.WEBSOCKET.debug || false
    this.eventHistory = []
    this.maxEventHistory = 50
    this.stats = {
      messagesSent: 0,
      messagesReceived: 0,
      connectionAttempts: 0,
      lastError: null,
      connectedAt: null,
      disconnectedAt: null
    }
  }

  /**
   * Generate unique client ID
   */
  generateClientId() {
    return `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  /**
   * Connect to WebSocket server
   * @param {Object} options - Connection options
   * @param {string} options.apiKey - API key for authentication
   * @param {string} options.token - Bearer token for authentication
   */
  async connect(options = {}) {
    if (this.isConnected || this.isConnecting) {
      this.log('Already connected or connecting')
      return Promise.resolve()
    }

    this.isConnecting = true
    this.shouldReconnect = true
    this.authCredentials = options
    this.stats.connectionAttempts++
    
    // Generate client ID if not exists
    if (!this.clientId) {
      this.clientId = this.generateClientId()
    }

    return new Promise((resolve, reject) => {
      try {
        // Build WebSocket URL with authentication
        const baseUrl = API_CONFIG.WEBSOCKET.url || 'ws://localhost:8000'
        const wsUrl = new URL(`${baseUrl}/ws/${this.clientId}`)
        
        // Add auth parameters if provided
        if (options.apiKey) {
          wsUrl.searchParams.append('api_key', options.apiKey)
        } else if (options.token) {
          wsUrl.searchParams.append('token', options.token)
        }

        this.log(`Connecting to ${wsUrl.origin}${wsUrl.pathname}`)
        
        this.ws = new WebSocket(wsUrl.toString())
        
        // Connection opened
        this.ws.onopen = () => {
          this.log('Connection established')
          this.isConnected = true
          this.isConnecting = false
          this.reconnectAttempts = 0
          this.stats.connectedAt = new Date().toISOString()
          this.stats.lastError = null
          this.addEvent('connection', 'Connected')
          
          // Start heartbeat
          this.startHeartbeat()
          
          // Process queued messages
          this.processMessageQueue()
          
          // Notify listeners
          this.notifyConnectionListeners('connected')
          
          resolve()
        }
        
        // Message received
        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            this.stats.messagesReceived++
            this.log('Message received', data)
            this.handleMessage(data)
          } catch (error) {
            this.log('Failed to parse message', error)
            this.stats.lastError = `Parse error: ${error.message}`
          }
        }
        
        // Connection closed
        this.ws.onclose = (event) => {
          this.log(`Connection closed (code: ${event.code}, reason: ${event.reason})`)
          this.stats.disconnectedAt = new Date().toISOString()
          this.addEvent('connection', `Closed (${event.code}: ${event.reason})`)
          this.handleDisconnect(event)
          
          if (this.isConnecting) {
            reject(new Error(`Connection failed: ${event.reason || 'Unknown error'}`))
          }
        }
        
        // Connection error
        this.ws.onerror = (error) => {
          this.log('Connection error', error)
          this.stats.lastError = `Connection error: ${error.message || 'Unknown'}`
          this.addEvent('error', 'Connection error', error)
          
          if (this.isConnecting) {
            this.isConnecting = false
            reject(error)
          }
        }
        
      } catch (error) {
        this.log('Failed to create connection', error)
        this.stats.lastError = `Connection failed: ${error.message}`
        this.isConnecting = false
        reject(error)
      }
    })
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect() {
    this.log('Disconnecting')
    this.shouldReconnect = false
    
    if (this.pingInterval) {
      clearInterval(this.pingInterval)
      this.pingInterval = null
    }
    
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect')
      this.ws = null
    }
    
    this.isConnected = false
    this.isConnecting = false
    this.notifyConnectionListeners('disconnected')
  }

  /**
   * Handle disconnection and attempt reconnect
   */
  handleDisconnect(event) {
    this.isConnected = false
    this.isConnecting = false
    
    if (this.pingInterval) {
      clearInterval(this.pingInterval)
      this.pingInterval = null
    }
    
    // Notify listeners
    this.notifyConnectionListeners('disconnected')
    
    // Attempt reconnect if not intentional disconnect
    if (this.shouldReconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
      this.attemptReconnect()
    }
  }

  /**
   * Attempt to reconnect with exponential backoff
   */
  async attemptReconnect() {
    this.reconnectAttempts++
    
    // Calculate delay with exponential backoff
    const delay = Math.min(
      this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1),
      this.maxReconnectDelay
    )
    
    this.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`)
    
    // Notify listeners of reconnecting state
    this.notifyConnectionListeners('reconnecting', {
      attempt: this.reconnectAttempts,
      maxAttempts: this.maxReconnectAttempts,
      delay
    })
    
    setTimeout(async () => {
      try {
        await this.connect(this.authCredentials)
      } catch (error) {
        console.error('WebSocket: Reconnection failed', error)
      }
    }, delay)
  }

  /**
   * Start heartbeat mechanism
   */
  startHeartbeat() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval)
    }
    
    // Send ping every 30 seconds
    this.pingInterval = setInterval(() => {
      if (this.isConnected) {
        this.send({ type: 'ping' })
      }
    }, 30000)
  }

  /**
   * Send message to server
   */
  send(data) {
    if (!this.isConnected) {
      this.log('Not connected, queuing message', data)
      this.messageQueue.push(data)
      return false
    }
    
    try {
      this.ws.send(JSON.stringify(data))
      this.stats.messagesSent++
      this.log('Message sent', data)
      return true
    } catch (error) {
      this.log('Failed to send message', error)
      this.stats.lastError = `Send error: ${error.message}`
      this.messageQueue.push(data)
      return false
    }
  }

  /**
   * Process queued messages
   */
  processMessageQueue() {
    while (this.messageQueue.length > 0 && this.isConnected) {
      const message = this.messageQueue.shift()
      this.send(message)
    }
  }

  /**
   * Handle incoming message
   */
  handleMessage(data) {
    const { type, ...payload } = data
    
    // Handle system messages
    switch (type) {
      case 'pong':
        // Heartbeat response
        break
        
      case 'ping':
        // Server heartbeat - respond with pong
        this.send({ type: 'pong' })
        break
        
      case 'subscribed':
      case 'unsubscribed':
        this.log(`${type} to ${payload.entity_type}:${payload.entity_id}`)
        this.addEvent('subscription', `${type} ${payload.entity_type}:${payload.entity_id}`)
        break
        
      case 'error':
        this.log('Server error', payload)
        this.stats.lastError = `Server error: ${payload.message || payload.error}`
        this.addEvent('error', 'Server error', payload)
        break
        
      default:
        // Handle application messages
        this.notifyMessageHandlers(type, payload)
    }
  }

  /**
   * Subscribe to entity updates
   */
  subscribe(entityType, entityId) {
    return this.send({
      type: 'subscribe',
      entity_type: entityType,
      entity_id: entityId
    })
  }

  /**
   * Unsubscribe from entity updates
   */
  unsubscribe(entityType, entityId) {
    return this.send({
      type: 'unsubscribe',
      entity_type: entityType,
      entity_id: entityId
    })
  }

  /**
   * Register connection state listener
   */
  onConnectionChange(callback) {
    this.connectionListeners.add(callback)
    
    // Return unsubscribe function
    return () => {
      this.connectionListeners.delete(callback)
    }
  }

  /**
   * Register message handler
   */
  onMessage(type, handler) {
    if (!this.messageHandlers.has(type)) {
      this.messageHandlers.set(type, new Set())
    }
    
    this.messageHandlers.get(type).add(handler)
    
    // Return unsubscribe function
    return () => {
      const handlers = this.messageHandlers.get(type)
      if (handlers) {
        handlers.delete(handler)
        if (handlers.size === 0) {
          this.messageHandlers.delete(type)
        }
      }
    }
  }

  /**
   * Notify connection listeners
   */
  notifyConnectionListeners(state, data = {}) {
    this.connectionListeners.forEach(listener => {
      try {
        listener({ state, ...data })
      } catch (error) {
        console.error('WebSocket: Error in connection listener', error)
      }
    })
  }

  /**
   * Notify message handlers
   */
  notifyMessageHandlers(type, data) {
    const handlers = this.messageHandlers.get(type)
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(data)
        } catch (error) {
          console.error(`WebSocket: Error in message handler for ${type}`, error)
        }
      })
    }
    
    // Also notify wildcard handlers
    const wildcardHandlers = this.messageHandlers.get('*')
    if (wildcardHandlers) {
      wildcardHandlers.forEach(handler => {
        try {
          handler({ type, ...data })
        } catch (error) {
          console.error('WebSocket: Error in wildcard handler', error)
        }
      })
    }
  }

  /**
   * Get connection state
   */
  getState() {
    if (this.isConnected) return 'connected'
    if (this.isConnecting) return 'connecting'
    if (this.reconnectAttempts > 0) return 'reconnecting'
    return 'disconnected'
  }

  /**
   * Get connection info
   */
  getConnectionInfo() {
    return {
      state: this.getState(),
      clientId: this.clientId,
      reconnectAttempts: this.reconnectAttempts,
      maxReconnectAttempts: this.maxReconnectAttempts,
      messageQueueSize: this.messageQueue.length,
      stats: this.stats,
      eventHistory: this.eventHistory,
      subscriptions: this.getSubscriptions()
    }
  }

  /**
   * Debug logging
   */
  log(message, data = null) {
    if (this.debug) {
      console.log(`[WebSocket] ${message}`, data || '')
    }
    
    // Add to event history
    this.addEvent('log', message, data)
  }

  /**
   * Add event to history
   */
  addEvent(type, message, data = null) {
    const event = {
      type,
      message,
      data,
      timestamp: new Date().toISOString()
    }
    
    this.eventHistory.unshift(event)
    
    // Limit history size
    if (this.eventHistory.length > this.maxEventHistory) {
      this.eventHistory.pop()
    }
  }

  /**
   * Get current subscriptions (to be implemented by store)
   */
  getSubscriptions() {
    // This will be populated by the store
    return []
  }

    return queueSize
  }

  /**
   * Get debug info
   */
  getDebugInfo() {
    return {
      state: this.getState(),
      isConnected: this.isConnected,
      isConnecting: this.isConnecting,
      shouldReconnect: this.shouldReconnect,
      clientId: this.clientId,
      reconnectAttempts: this.reconnectAttempts,
      maxReconnectAttempts: this.maxReconnectAttempts,
      messageQueueSize: this.messageQueue.length,
      stats: this.stats,
      eventHistory: this.eventHistory.slice(0, 10),
      debug: this.debug,
      wsUrl: this.ws?.url || 'Not connected'
    }
  }

  /**
   * Enable/disable debug mode
   */
  setDebugMode(enabled) {
    this.debug = enabled
    this.log(`Debug mode ${enabled ? 'enabled' : 'disabled'}`)
  }
}

// Create singleton instance
const websocketService = new WebSocketService()

export default websocketService
export { WebSocketService }