import { defineStore } from 'pinia'
import { ref } from 'vue'
import { io } from 'socket.io-client'
import { API_CONFIG } from '@/config/api'

export const useWebSocketStore = defineStore('websocket', () => {
  // State
  const socket = ref(null)
  const connected = ref(false)
  const connectionError = ref(null)
  const reconnectAttempts = ref(0)
  
  // Event handlers registry
  const eventHandlers = new Map()

  // Initialize WebSocket connection
  function connect() {
    if (socket.value?.connected) {
      console.log('WebSocket already connected')
      return
    }

    socket.value = io(API_CONFIG.WEBSOCKET.url, {
      reconnection: API_CONFIG.WEBSOCKET.reconnection,
      reconnectionDelay: API_CONFIG.WEBSOCKET.reconnectionDelay,
      reconnectionDelayMax: API_CONFIG.WEBSOCKET.reconnectionDelayMax,
      reconnectionAttempts: API_CONFIG.WEBSOCKET.reconnectionAttempts,
      transports: ['websocket', 'polling']
    })

    // Connection events
    socket.value.on('connect', () => {
      console.log('WebSocket connected')
      connected.value = true
      connectionError.value = null
      reconnectAttempts.value = 0
    })

    socket.value.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason)
      connected.value = false
    })

    socket.value.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error)
      connectionError.value = error.message
      connected.value = false
    })

    socket.value.on('reconnect_attempt', (attemptNumber) => {
      reconnectAttempts.value = attemptNumber
    })

    // Application events
    socket.value.on('project:update', (data) => {
      triggerHandlers('project:update', data)
    })

    socket.value.on('agent:status', (data) => {
      triggerHandlers('agent:status', data)
    })

    socket.value.on('message:new', (data) => {
      triggerHandlers('message:new', data)
    })

    socket.value.on('task:update', (data) => {
      triggerHandlers('task:update', data)
    })

    socket.value.on('context:update', (data) => {
      triggerHandlers('context:update', data)
    })
  }

  // Disconnect WebSocket
  function disconnect() {
    if (socket.value) {
      socket.value.disconnect()
      socket.value = null
      connected.value = false
    }
  }

  // Emit event to server
  function emit(event, data) {
    if (!socket.value?.connected) {
      console.error('WebSocket not connected')
      return false
    }
    socket.value.emit(event, data)
    return true
  }

  // Subscribe to events
  function subscribe(event, handler) {
    if (!eventHandlers.has(event)) {
      eventHandlers.set(event, new Set())
    }
    eventHandlers.get(event).add(handler)
    
    // Return unsubscribe function
    return () => {
      const handlers = eventHandlers.get(event)
      if (handlers) {
        handlers.delete(handler)
        if (handlers.size === 0) {
          eventHandlers.delete(event)
        }
      }
    }
  }

  // Trigger handlers for an event
  function triggerHandlers(event, data) {
    const handlers = eventHandlers.get(event)
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(data)
        } catch (error) {
          console.error(`Error in WebSocket handler for ${event}:`, error)
        }
      })
    }
  }

  // Join a room (for project-specific updates)
  function joinRoom(room) {
    return emit('join', { room })
  }

  // Leave a room
  function leaveRoom(room) {
    return emit('leave', { room })
  }

  return {
    // State
    socket,
    connected,
    connectionError,
    reconnectAttempts,
    
    // Actions
    connect,
    disconnect,
    emit,
    subscribe,
    joinRoom,
    leaveRoom
  }
})