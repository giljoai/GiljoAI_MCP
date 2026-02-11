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

  // Visualization Data
  const agentTimeline = ref([]) // Timeline events for visualization
  const agentTree = ref(null) // Hierarchical tree structure
  const agentMetrics = ref({
    totalAgents: 0,
    activeAgents: 0,
    completedAgents: 0,
    averageDuration: 0,
    tokenUsage: {},
    successRate: 0,
    parallelExecutions: [],
  })

  // Getters
  const activeAgents = computed(() => agents.value.filter((a) => a.status === 'active'))

  const agentsByProject = computed(
    () => (projectId) => agents.value.filter((a) => a.project_id === projectId),
  )

  const agentByName = computed(() => (name) => agents.value.find((a) => a.name === name))

  const agentHealth = computed(() => (agentId) => healthData.value[agentId] || null)

  // Actions
  // MIGRATION NOTE (Handover 0119): Migrated from api.agents.list() to api.agentJobs.list()
  // Field mappings: agent_id → job_id, created_at → spawned_at
  async function fetchAgents(projectId = null) {
    loading.value = true
    error.value = null
    try {
      const response = await api.agentJobs.list(projectId)
      // Ensure agents.value is always an array (Bug #3 fix)
      agents.value = Array.isArray(response.data) ? response.data : []
    } catch (err) {
      error.value = err.message
      console.error('Failed to fetch agents:', err)
    } finally {
      loading.value = false
    }
  }

  // MIGRATION NOTE (Handover 0119): Migrated from api.agents.get() to api.agentJobs.get()
  async function fetchAgent(id) {
    loading.value = true
    error.value = null
    try {
      const response = await api.agentJobs.get(id)
      currentAgent.value = response.data

      // Update in list if exists
      const index = agents.value.findIndex((a) => a.id === id)
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

  // MIGRATION NOTE (Handover 0119): Migrated from api.agents.create() to api.agentJobs.spawn()
  async function createAgent(agentData) {
    loading.value = true
    error.value = null
    try {
      const response = await api.agentJobs.spawn(agentData)
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

  // MIGRATION NOTE (Handover 0119): Migrated from api.agents.health() to api.agentJobs.status()
  async function fetchAgentHealth(id) {
    try {
      const response = await api.agentJobs.status(id)
      healthData.value[id] = response.data
      return response.data
    } catch (err) {
      console.error('Failed to fetch agent health:', err)
      return null
    }
  }

  // MIGRATION NOTE (Handover 0119): Migrated from api.agents.assign() to api.agentJobs.spawn()
  // The old assign method is replaced with spawn for creating new agent jobs
  async function assignJob(agentName, jobData) {
    loading.value = true
    error.value = null
    try {
      const response = await api.agentJobs.spawn({ agent_name: agentName, ...jobData })
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

  function updateAgentStatus(agentId, status) {
    const agent = agents.value.find((a) => a.id === agentId)
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
    const {
      agent_name,
      project_id,
      status,
      health,
      active_jobs,
      context_used,
      progress_percentage,
    } = data

    // Find agent by name and project
    const agent = agents.value.find((a) => a.name === agent_name && a.project_id === project_id)

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
          last_updated: new Date().toISOString(),
        }
      }

      // Clear health alert state when agent reports progress (Handover 0106)
      // Progress updates indicate the agent is healthy again
      if (progress_percentage !== undefined || status === 'working') {
        agent.health_state = 'healthy'
        agent.minutes_since_update = 0
        agent.health_issue_description = null
        agent.recommended_action = null
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

  // Add timeline event
  function addTimelineEvent(event) {
    const timelineEvent = {
      id: `evt_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date().toISOString(),
      ...event,
    }

    agentTimeline.value.unshift(timelineEvent)

    // Limit timeline to last 100 events
    if (agentTimeline.value.length > 100) {
      agentTimeline.value = agentTimeline.value.slice(0, 100)
    }

    return timelineEvent
  }

  // Handle agent spawn event
  function handleAgentSpawn(data) {
    addTimelineEvent({
      type: 'spawn',
      agent_name: data.agent_name,
      parent_agent: data.parent_agent || 'orchestrator',
      mission: data.mission,
      status: 'active',
      color: 'green',
    })

    // Update metrics
    agentMetrics.value.totalAgents++
    agentMetrics.value.activeAgents++

    handleRealtimeUpdate(data)
  }

  // Handle agent complete event
  function handleAgentComplete(data) {
    addTimelineEvent({
      type: 'complete',
      agent_name: data.agent_name,
      duration: data.duration,
      tokens_used: data.tokens_used,
      status: 'completed',
      color: 'gray',
    })

    // Update metrics
    agentMetrics.value.activeAgents--
    agentMetrics.value.completedAgents++

    handleRealtimeUpdate({ ...data, status: 'completed' })
  }

  // Handle health alert events (Handover 0106)
  function handleHealthAlert(data) {
    const { job_id, health_state, minutes_since_update, issue_description, recommended_action } =
      data

    // Find agent by job_id
    const agent = agents.value.find((a) => a.job_id === job_id)

    if (agent) {
      // Update health fields
      agent.health_state = health_state
      agent.minutes_since_update = minutes_since_update
      agent.health_issue_description = issue_description
      agent.recommended_action = recommended_action
      agent.updated_at = new Date().toISOString()

      // Also update health data cache
      healthData.value[agent.id] = {
        ...healthData.value[agent.id],
        health_state,
        minutes_since_update,
        issue_description,
        recommended_action,
        last_updated: new Date().toISOString(),
      }

      // If this is the current agent, update it too
      if (currentAgent.value?.id === agent.id) {
        currentAgent.value = { ...agent }
      }
    }
  }

  // Handle health recovery events (Handover 0106)
  function handleHealthRecovered(data) {
    const { job_id } = data

    // Find agent by job_id
    const agent = agents.value.find((a) => a.job_id === job_id)

    if (agent) {
      // Clear health fields
      agent.health_state = 'healthy'
      agent.minutes_since_update = 0
      agent.health_issue_description = null
      agent.recommended_action = null
      agent.updated_at = new Date().toISOString()

      // Clear health data cache
      if (healthData.value[agent.id]) {
        healthData.value[agent.id].health_state = 'healthy'
        healthData.value[agent.id].minutes_since_update = 0
      }

      // If this is the current agent, update it too
      if (currentAgent.value?.id === agent.id) {
        currentAgent.value = { ...agent }
      }
    }
  }

  // Handover 0233 Phase 5: Update specific agent field by job_id
  function updateAgentField(jobId, fieldName, value) {
    // Find agent by job_id
    const agent = agents.value.find((a) => a.job_id === jobId)

    if (agent) {
      // Update the specified field
      agent[fieldName] = value
      agent.updated_at = new Date().toISOString()

      // If this is the current agent, update it too
      if (currentAgent.value?.job_id === jobId) {
        currentAgent.value = { ...agent }
      }
    }
  }

  return {
    // State
    agents,
    currentAgent,
    loading,
    error,
    healthData,
    agentTimeline,
    agentTree,
    agentMetrics,

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
    updateAgentStatus,
    clearError,
    handleRealtimeUpdate,
    addTimelineEvent,
    handleAgentSpawn,
    handleAgentComplete,
    handleHealthAlert,
    handleHealthRecovered,
    updateAgentField, // Handover 0233 Phase 5
  }
})
