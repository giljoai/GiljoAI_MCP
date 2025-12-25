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
  const pendingMessages = computed(() => messages.value.filter((m) => m.status === 'pending'))

  const messagesByProject = computed(
    () => (projectId) => messages.value.filter((m) => m.project_id === projectId),
  )

  const messagesByAgent = computed(
    () => (agentName) =>
      messages.value.filter((m) => m.to_agents?.includes(agentName) || m.from === agentName),
  )

  const highPriorityMessages = computed(() =>
    messages.value.filter((m) => m.priority === 'high' || m.priority === 'urgent'),
  )

  const acknowledgedMessages = computed(() =>
    messages.value.filter((m) => m.acknowledged_by?.length > 0),
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
      const index = messages.value.findIndex((m) => m.id === id)
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

  async function completeMessage(id, result) {
    try {
      const response = await api.messages.complete(id, result)

      // Update message in list
      const message = messages.value.find((m) => m.id === id)
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
    const exists = messages.value.find((m) => m.id === message.id)
    if (!exists) {
      messages.value.unshift(message)
      updateUnreadCount()
    }
  }

  function updateMessage(updatedMessage) {
    // Update message from WebSocket
    const index = messages.value.findIndex((m) => m.id === updatedMessage.id)
    if (index !== -1) {
      messages.value[index] = { ...messages.value[index], ...updatedMessage }
      updateUnreadCount()
    }
  }

  function updateUnreadCount() {
    unreadCount.value = messages.value.filter(
      (m) => m.status === 'pending' && !m.acknowledged_by?.length,
    ).length
  }

  function clearError() {
    error.value = null
  }

  // Handle real-time updates from WebSocket
  function handleRealtimeUpdate(data) {
    const {
      message_id,
      project_id,
      update_type,
      from_agent,
      to_agents,
      content,
      priority,
      status,
    } = data

    // Find message by ID
    const messageIndex = messages.value.findIndex((m) => m.id === message_id)

    if (update_type === 'new' && messageIndex === -1) {
      // New message - add to list
      const newMessage = {
        id: message_id,
        project_id,
        from: from_agent,
        to_agents,
        content,
        priority: priority || 'normal',
        status: status || 'pending',
        acknowledged_by: [],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }

      messages.value.unshift(newMessage) // Add to beginning
      updateUnreadCount()

      // Emit event for new message notification
      window.dispatchEvent(new CustomEvent('new-message', { detail: newMessage }))
    } else if (messageIndex !== -1) {
      // Update existing message
      const message = messages.value[messageIndex]

      if (update_type === 'acknowledged') {
        // Add to acknowledged_by if not already there
        if (!message.acknowledged_by) {
          message.acknowledged_by = []
        }
        if (from_agent && !message.acknowledged_by.includes(from_agent)) {
          message.acknowledged_by.push(from_agent)
        }
        message.status = 'acknowledged'
      } else if (update_type === 'completed') {
        message.status = 'completed'
        message.completed_at = new Date().toISOString()
      }

      // Update other fields if provided
      if (content) {
        message.content = content
      }
      if (priority) {
        message.priority = priority
      }
      if (status) {
        message.status = status
      }

      message.updated_at = new Date().toISOString()

      // Update current message if it's the same
      if (currentMessage.value?.id === message_id) {
        currentMessage.value = { ...message }
      }

      updateUnreadCount()
    } else if (message_id && update_type === 'new') {
      // Unknown message - fetch updated list
      fetchMessages({ project_id })
    }
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
    completeMessage,
    broadcastMessage,
    addMessage,
    updateMessage,
    clearError,
    handleRealtimeUpdate,
  }
})
