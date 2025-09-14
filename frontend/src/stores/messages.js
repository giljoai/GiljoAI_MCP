import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'

export const useMessageStore = defineStore('messages', () => {
  // State
  const messages = ref([])
  const currentMessage = ref(null)
  const loading = ref(false)
  const error = ref(null)
  const unreadCount = ref(0)

  // Getters
  const pendingMessages = computed(() => 
    messages.value.filter(m => m.status === 'pending')
  )
  
  const messagesByProject = computed(() => (projectId) =>
    messages.value.filter(m => m.project_id === projectId)
  )
  
  const messagesByAgent = computed(() => (agentName) =>
    messages.value.filter(m => 
      m.to_agents?.includes(agentName) || m.from === agentName
    )
  )
  
  const highPriorityMessages = computed(() =>
    messages.value.filter(m => m.priority === 'high' || m.priority === 'urgent')
  )

  const acknowledgedMessages = computed(() =>
    messages.value.filter(m => m.acknowledged_by?.length > 0)
  )

  // Actions
  async function fetchMessages(params = {}) {
    loading.value = true
    error.value = null
    try {
      const response = await api.messages.list(params)
      messages.value = response.data
      updateUnreadCount()
    } catch (err) {
      error.value = err.message
      console.error('Failed to fetch messages:', err)
    } finally {
      loading.value = false
    }
  }

  async function fetchMessage(id) {
    loading.value = true
    error.value = null
    try {
      const response = await api.messages.get(id)
      currentMessage.value = response.data
      
      // Update in list if exists
      const index = messages.value.findIndex(m => m.id === id)
      if (index !== -1) {
        messages.value[index] = response.data
      }
    } catch (err) {
      error.value = err.message
      console.error('Failed to fetch message:', err)
    } finally {
      loading.value = false
    }
  }

  async function sendMessage(messageData) {
    loading.value = true
    error.value = null
    try {
      const response = await api.messages.send(messageData)
      messages.value.unshift(response.data) // Add to beginning
      return response.data
    } catch (err) {
      error.value = err.message
      console.error('Failed to send message:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function acknowledgeMessage(id, agentName) {
    try {
      const response = await api.messages.acknowledge(id, agentName)
      
      // Update message in list
      const message = messages.value.find(m => m.id === id)
      if (message) {
        if (!message.acknowledged_by) {
          message.acknowledged_by = []
        }
        if (!message.acknowledged_by.includes(agentName)) {
          message.acknowledged_by.push(agentName)
        }
        message.status = 'acknowledged'
      }
      
      updateUnreadCount()
      return response.data
    } catch (err) {
      console.error('Failed to acknowledge message:', err)
      throw err
    }
  }

  async function completeMessage(id, result) {
    try {
      const response = await api.messages.complete(id, result)
      
      // Update message in list
      const message = messages.value.find(m => m.id === id)
      if (message) {
        message.status = 'completed'
        message.result = result
        message.completed_at = new Date().toISOString()
      }
      
      return response.data
    } catch (err) {
      console.error('Failed to complete message:', err)
      throw err
    }
  }

  async function broadcastMessage(projectId, content) {
    loading.value = true
    error.value = null
    try {
      const response = await api.messages.broadcast(projectId, content)
      messages.value.unshift(response.data)
      return response.data
    } catch (err) {
      error.value = err.message
      console.error('Failed to broadcast message:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  function addMessage(message) {
    // Add new message from WebSocket
    const exists = messages.value.find(m => m.id === message.id)
    if (!exists) {
      messages.value.unshift(message)
      updateUnreadCount()
    }
  }

  function updateMessage(updatedMessage) {
    // Update message from WebSocket
    const index = messages.value.findIndex(m => m.id === updatedMessage.id)
    if (index !== -1) {
      messages.value[index] = { ...messages.value[index], ...updatedMessage }
      updateUnreadCount()
    }
  }

  function updateUnreadCount() {
    unreadCount.value = messages.value.filter(m => 
      m.status === 'pending' && !m.acknowledged_by?.length
    ).length
  }

  function clearError() {
    error.value = null
  }

  return {
    // State
    messages,
    currentMessage,
    loading,
    error,
    unreadCount,
    
    // Getters
    pendingMessages,
    messagesByProject,
    messagesByAgent,
    highPriorityMessages,
    acknowledgedMessages,
    
    // Actions
    fetchMessages,
    fetchMessage,
    sendMessage,
    acknowledgeMessage,
    completeMessage,
    broadcastMessage,
    addMessage,
    updateMessage,
    clearError
  }
})