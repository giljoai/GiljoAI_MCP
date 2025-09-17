import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import websocketService from '@/services/websocket'
import { useToast } from '@/composables/useToast'
import { useProjectStore } from './projects'
import { useAgentStore } from './agents'
import { useMessageStore } from './messages'
import { useTaskStore } from './tasks'
import { useProductStore } from './products'

export const useWebSocketStore = defineStore('websocket', () => {
  // Connection state
  const connectionState = ref('disconnected')
  const connectionError = ref(null)
  const reconnectAttempts = ref(0)
  const maxReconnectAttempts = ref(10)
  const clientId = ref(null)
  const messageQueueSize = ref(0)
  
  // Current subscriptions
  const subscriptions = ref(new Set())
  
  // Computed properties
  const isConnected = computed(() => connectionState.value === 'connected')
  const isConnecting = computed(() => connectionState.value === 'connecting')
  const isReconnecting = computed(() => connectionState.value === 'reconnecting')
  
  // Initialize WebSocket connection
  async function connect(options = {}) {
    try {
      // Set up connection state listener
      websocketService.onConnectionChange((event) => {
        handleConnectionChange(event)
      })
      
      // Set up message handlers
      setupMessageHandlers()
      
      // Connect to WebSocket server
      await websocketService.connect(options)
      
      return true
    } catch (error) {
      console.error('Failed to connect WebSocket:', error)
      connectionError.value = error.message
      return false
    }
  }
  
  // Disconnect WebSocket
  function disconnect() {
    websocketService.disconnect()
    subscriptions.value.clear()
  }
  
  // Handle connection state changes
  function handleConnectionChange(event) {
    const { showToast } = useToast()
    const prevState = connectionState.value
    connectionState.value = event.state
    
    switch (event.state) {
      case 'connected':
        connectionError.value = null
        reconnectAttempts.value = 0
        clientId.value = websocketService.clientId
        
        // Show reconnection success notification
        if (prevState === 'reconnecting') {
          showToast({
            title: 'Connection Restored',
            message: 'Successfully reconnected to server',
            color: 'success',
            icon: 'mdi-wifi',
            timeout: 3000
          })
        }
        
        // Re-subscribe to previous subscriptions
        resubscribeAll()
        break
        
      case 'disconnected':
        // Show disconnection notification
        if (prevState === 'connected') {
          showToast({
            title: 'Connection Lost',
            message: 'Attempting to reconnect...',
            color: 'warning',
            icon: 'mdi-wifi-off',
            timeout: 5000
          })
        }
        break
        
      case 'reconnecting':
        reconnectAttempts.value = event.attempt
        maxReconnectAttempts.value = event.maxAttempts
        
        // Show reconnection attempt notification
        showToast({
          title: 'Reconnecting',
          message: `Attempt ${event.attempt}/${event.maxAttempts}`,
          color: 'info',
          icon: 'mdi-wifi-sync',
          timeout: 2000
        })
        break
        
      case 'connecting':
        connectionError.value = null
        break
    }
    
    // Update message queue size
    const info = websocketService.getConnectionInfo()
    messageQueueSize.value = info.messageQueueSize
  }
  
  // Set up message handlers for different types
  function setupMessageHandlers() {
    // Agent updates
    websocketService.onMessage('agent_update', (data) => {
      const agentsStore = useAgentStore()
      if (agentsStore.handleRealtimeUpdate) {
        agentsStore.handleRealtimeUpdate(data.data)
      }
    })
    
    // Message updates
    websocketService.onMessage('message', (data) => {
      const messagesStore = useMessageStore()
      if (messagesStore.handleRealtimeUpdate) {
        messagesStore.handleRealtimeUpdate(data.data)
      }
    })
    
    // Project updates
    websocketService.onMessage('project_update', (data) => {
      const projectsStore = useProjectStore()
      if (projectsStore.handleRealtimeUpdate) {
        projectsStore.handleRealtimeUpdate(data.data)
      }
    })
    
    // Task updates
    websocketService.onMessage('entity_update', (data) => {
      if (data.entity_type === 'task') {
        const tasksStore = useTaskStore()
        const productStore = useProductStore()
        
        // Filter by current product if one is selected
        if (productStore.currentProductId) {
          if (data.data.product_id === productStore.currentProductId) {
            if (tasksStore.handleRealtimeUpdate) {
              tasksStore.handleRealtimeUpdate(data.data)
            }
          }
        } else {
          // No product filter, process all updates
          if (tasksStore.handleRealtimeUpdate) {
            tasksStore.handleRealtimeUpdate(data.data)
          }
        }
      }
    })
    
    // Progress updates
    websocketService.onMessage('progress', (data) => {
      handleProgressUpdate(data.data)
    })
    
    // Notifications
    websocketService.onMessage('notification', (data) => {
      handleNotification(data.data)
    })
  }
  
  // Subscribe to entity updates
  function subscribe(entityType, entityId) {
    const key = `${entityType}:${entityId}`
    
    if (subscriptions.value.has(key)) {
      return // Already subscribed
    }
    
    if (websocketService.subscribe(entityType, entityId)) {
      subscriptions.value.add(key)
    }
  }
  
  // Unsubscribe from entity updates
  function unsubscribe(entityType, entityId) {
    const key = `${entityType}:${entityId}`
    
    if (!subscriptions.value.has(key)) {
      return // Not subscribed
    }
    
    if (websocketService.unsubscribe(entityType, entityId)) {
      subscriptions.value.delete(key)
    }
  }
  
  // Re-subscribe to all previous subscriptions
  function resubscribeAll() {
    subscriptions.value.forEach(key => {
      const [entityType, entityId] = key.split(':')
      websocketService.subscribe(entityType, entityId)
    })
  }
  
  // Subscribe to project updates
  function subscribeToProject(projectId) {
    subscribe('project', projectId)
  }
  
  // Subscribe to agent updates
  function subscribeToAgent(projectId, agentName) {
    subscribe('agent', `${projectId}:${agentName}`)
  }
  
  // Handle progress updates
  function handleProgressUpdate(data) {
    // Could emit events or update a progress store
    console.log('Progress update:', data)
    
    // Emit custom event for components to listen to
    window.dispatchEvent(new CustomEvent('ws-progress', { detail: data }))
  }
  
  // Handle notifications
  function handleNotification(data) {
    console.log('Notification:', data)
    
    // Emit custom event for notification system
    window.dispatchEvent(new CustomEvent('ws-notification', { detail: data }))
  }
  
  // Send message to server
  function send(data) {
    return websocketService.send(data)
  }
  
  // Get connection info
  function getConnectionInfo() {
    return websocketService.getConnectionInfo()
  }
  
  return {
    // State
    connectionState,
    connectionError,
    reconnectAttempts,
    maxReconnectAttempts,
    clientId,
    messageQueueSize,
    subscriptions,
    
    // Computed
    isConnected,
    isConnecting,
    isReconnecting,
    
    // Actions
    connect,
    disconnect,
    subscribe,
    unsubscribe,
    subscribeToProject,
    subscribeToAgent,
    send,
    getConnectionInfo
  }
})