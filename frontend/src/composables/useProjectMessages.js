import api from '@/services/api'
import { useProjectMessagesStore } from '@/stores/projectMessagesStore'

function extractMessagesFromResponse(data) {
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.messages)) return data.messages
  if (Array.isArray(data?.rows)) return data.rows
  return []
}

export function useProjectMessages() {
  const store = useProjectMessagesStore()

  async function loadMessages(projectId) {
    if (!projectId) {
      return []
    }

    const response = await api.messages.list({ project_id: projectId })
    const messages = extractMessagesFromResponse(response?.data)
    store.setMessages(projectId, messages)
    return messages
  }

  return {
    store,
    loadMessages,
  }
}
