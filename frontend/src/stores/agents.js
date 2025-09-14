import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'

export const useAgentStore = defineStore('agents', () => {
  // State
  const agents = ref([])
  const currentAgent = ref(null)
  const loading = ref(false)
  const error = ref(null)
  const healthData = ref({})

  // Getters
  const activeAgents = computed(() => 
    agents.value.filter(a => a.status === 'active')
  )
  
  const agentsByProject = computed(() => (projectId) =>
    agents.value.filter(a => a.project_id === projectId)
  )
  
  const agentByName = computed(() => (name) =>
    agents.value.find(a => a.name === name)
  )

  const agentHealth = computed(() => (agentId) =>
    healthData.value[agentId] || null
  )

  // Actions
  async function fetchAgents(projectId = null) {
    loading.value = true
    error.value = null
    try {
      const response = await api.agents.list(projectId)
      agents.value = response.data
    } catch (err) {
      error.value = err.message
      console.error('Failed to fetch agents:', err)
    } finally {
      loading.value = false
    }
  }

  async function fetchAgent(id) {
    loading.value = true
    error.value = null
    try {
      const response = await api.agents.get(id)
      currentAgent.value = response.data
      
      // Update in list if exists
      const index = agents.value.findIndex(a => a.id === id)
      if (index !== -1) {
        agents.value[index] = response.data
      }
    } catch (err) {
      error.value = err.message
      console.error('Failed to fetch agent:', err)
    } finally {
      loading.value = false
    }
  }

  async function createAgent(agentData) {
    loading.value = true
    error.value = null
    try {
      const response = await api.agents.create(agentData)
      agents.value.push(response.data)
      return response.data
    } catch (err) {
      error.value = err.message
      console.error('Failed to create agent:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchAgentHealth(id) {
    try {
      const response = await api.agents.health(id)
      healthData.value[id] = response.data
      return response.data
    } catch (err) {
      console.error('Failed to fetch agent health:', err)
      return null
    }
  }

  async function assignJob(agentName, jobData) {
    loading.value = true
    error.value = null
    try {
      const response = await api.agents.assign(agentName, jobData)
      await fetchAgents() // Refresh agents list
      return response.data
    } catch (err) {
      error.value = err.message
      console.error('Failed to assign job:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function decommissionAgent(id, reason = 'completed') {
    loading.value = true
    error.value = null
    try {
      const response = await api.agents.decommission(id, reason)
      agents.value = agents.value.filter(a => a.id !== id)
      if (currentAgent.value?.id === id) {
        currentAgent.value = null
      }
      return response.data
    } catch (err) {
      error.value = err.message
      console.error('Failed to decommission agent:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  function updateAgentStatus(agentId, status) {
    const agent = agents.value.find(a => a.id === agentId)
    if (agent) {
      agent.status = status
      agent.updated_at = new Date().toISOString()
    }
  }

  function clearError() {
    error.value = null
  }

  // Handle real-time updates from WebSocket
  function handleRealtimeUpdate(data) {
    const { agent_name, project_id, status, health, active_jobs, context_used } = data
    
    // Find agent by name and project
    const agent = agents.value.find(a => 
      a.name === agent_name && a.project_id === project_id
    )
    
    if (agent) {
      // Update agent status
      if (status) {
        agent.status = status
      }
      
      // Update health data if provided
      if (health !== undefined) {
        healthData.value[agent.id] = {
          ...healthData.value[agent.id],
          health,
          context_used,
          active_jobs,
          last_updated: new Date().toISOString()
        }
      }
      
      // Update timestamp
      agent.updated_at = new Date().toISOString()
      
      // If this is the current agent, update it too
      if (currentAgent.value?.id === agent.id) {
        currentAgent.value = { ...agent }
      }
    } else if (agent_name && project_id) {
      // New agent appeared - fetch the updated list
      fetchAgents(project_id)
    }
  }

  return {
    // State
    agents,
    currentAgent,
    loading,
    error,
    healthData,
    
    // Getters
    activeAgents,
    agentsByProject,
    agentByName,
    agentHealth,
    
    // Actions
    fetchAgents,
    fetchAgent,
    createAgent,
    fetchAgentHealth,
    assignJob,
    decommissionAgent,
    updateAgentStatus,
    clearError,
    handleRealtimeUpdate
  }
})