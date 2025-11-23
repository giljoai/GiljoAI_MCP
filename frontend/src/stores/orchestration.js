/**
 * Orchestration Store
 * Manages agent orchestration state and operations
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'

export const useOrchestrationStore = defineStore('orchestration', () => {
  // State
  const agents = ref([])
  const project = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // Getters
  const orchestrator = computed(() => {
    return agents.value.find((agent) => agent.is_orchestrator)
  })

  const regularAgents = computed(() => {
    return agents.value.filter((agent) => !agent.is_orchestrator)
  })

  const getUnreadCount = (agentId) => {
    const agent = agents.value.find((a) => a.id === agentId)
    if (!agent || !agent.messages) return 0
    return agent.messages.filter((msg) => !msg.read).length
  }

  // Actions
  const loadAgents = async (projectId) => {
    loading.value = true
    error.value = null

    try {
      const response = await api.get(`/api/projects/${projectId}/agents`)
      agents.value = response.data.agents || []
      project.value = response.data.project || null
    } catch (err) {
      console.error('[OrchestrationStore] Failed to load agents:', err)
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  const handleAgentStatusUpdate = (update) => {
    const { job_id, status, progress, current_task } = update
    const agentIndex = agents.value.findIndex((a) => a.job_id === job_id)

    if (agentIndex !== -1) {
      agents.value[agentIndex] = {
        ...agents.value[agentIndex],
        status,
        progress,
        current_task,
      }
    }
  }

  // MIGRATION NOTE (Handover 0119): Updated to use /api/v1/prompts instead of /api/prompts
  const handleCopyPrompt = async (agentId, toolType) => {
    try {
      const response = await api.get(`/api/v1/prompts/${agentId}`, {
        params: { tool_type: toolType },
      })
      return response.data.prompt || 'Prompt not available'
    } catch (err) {
      console.error('[OrchestrationStore] Failed to get prompt:', err)
      throw err
    }
  }

  const initiateCloseout = async (projectId) => {
    try {
      const response = await api.get(`/api/projects/${projectId}/closeout`)
      return response.data
    } catch (err) {
      console.error('[OrchestrationStore] Failed to initiate closeout:', err)
      throw err
    }
  }

  const completeProject = async (projectId) => {
    try {
      const response = await api.post(`/api/projects/${projectId}/complete`, {
        confirm_closeout: true,
      })
      return response.data
    } catch (err) {
      console.error('[OrchestrationStore] Failed to complete project:', err)
      throw err
    }
  }

  return {
    // State
    agents,
    project,
    loading,
    error,

    // Getters
    orchestrator,
    regularAgents,
    getUnreadCount,

    // Actions
    loadAgents,
    handleAgentStatusUpdate,
    handleCopyPrompt,
    initiateCloseout,
    completeProject,
  }
})
