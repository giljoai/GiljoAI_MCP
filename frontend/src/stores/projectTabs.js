/**
 * Project Tabs Store
 *
 * State management for the dual-tab interface (Launch Tab / Jobs Tab)
 * managing project staging, agent jobs, and real-time messaging.
 *
 * @see handovers/0077_launch_jobs_dual_tab_interface.md
 */

import { defineStore } from 'pinia'
import { useWebSocketStore } from './websocket'
import api from '@/services/api'

export const useProjectTabsStore = defineStore('projectTabs', {
  state: () => ({
    // Tab navigation
    activeTab: 'launch', // 'launch' | 'jobs'

    // Project reference
    currentProject: null,

    // Agents
    agents: [],

    // Orchestrator mission
    orchestratorMission: '',

    // Messages
    messages: [],

    // Staging state
    isStaging: false,
    isLaunched: false,
    stagingComplete: false, // Handover 0287: Tracks when staging workflow is complete

    // Loading states
    loading: false,
    error: null,
  }),

  getters: {
    // Tab state
    isLaunchTab: (state) => state.activeTab === 'launch',
    isJobsTab: (state) => state.activeTab === 'jobs',

    // Agent queries
    sortedAgents: (state) => {
      const priority = {
        failed: 1,
        blocked: 2,
        waiting: 3,
        working: 4,
        complete: 5,
      }
      return [...state.agents].sort((a, b) => {
        const aPriority = priority[a.status] || 999
        const bPriority = priority[b.status] || 999
        return aPriority - bPriority
      })
    },

    orchestrator: (state) => {
      return state.agents.find((a) => a.agent_type === 'orchestrator')
    },

    agentsByStatus: (state) => (status) => {
      return state.agents.filter((a) => a.status === status)
    },

    agentCount: (state) => state.agents.length,

    // Multi-instance agents
    agentInstances: (state) => {
      const instances = {}
      state.agents.forEach((agent) => {
        const type = agent.agent_type
        if (!instances[type]) {
          instances[type] = []
        }
        instances[type].push(agent)
      })
      return instances
    },

    // Message queries
    unreadMessages: (state) => {
      return state.messages.filter((m) => m.status === 'pending')
    },

    // DEPRECATED (Handover 0289): Tab badge removed - messages now tracked per-agent in JobsTab
    // Kept for backwards compatibility with any code that may reference this getter
    unreadCount: (state) => {
      return state.messages.filter((m) => m.status === 'pending').length
    },

    messagesByAgent: (state) => (agentId) => {
      return state.messages.filter((m) => m.to_agent === agentId || m.from_agent === agentId)
    },

    // Completion state
    allAgentsComplete(state) {
      if (state.agents.length === 0) return false
      return state.agents.every((a) => a.status === 'complete')
    },

    // Ready state (Handover 0287: Use stagingComplete instead of manual checks)
    readyToLaunch(state) {
      return state.stagingComplete && state.orchestratorMission && state.agents.length > 0 && !state.isStaging
    },
  },

  actions: {
    // ==================== Tab Navigation ====================

    /**
     * Switch active tab
     * @param {string} tabName - 'launch' | 'jobs'
     */
    switchTab(tabName) {
      this.activeTab = tabName
    },

    // ==================== Project Management ====================

    /**
     * Set current project
     * @param {Object} project - Project object
     */
    setProject(project) {
      // Defensive validation
      if (!project) {
        console.warn('[ProjectTabs] setProject called with null/undefined project')
        this.clearProject()
        return
      }

      // Set project data
      this.currentProject = project
      this.orchestratorMission = project.mission || ''
      this.agents = Array.isArray(project.agents) ? project.agents : []

      // Production-grade isLaunched detection
      // A project is considered "launched" if it has agent jobs (excluding just orchestrator in waiting state)
      // This handles page reload scenarios where the project was previously launched
      const hasNonOrchestratorAgents = this.agents.some(
        (agent) => agent.agent_type !== 'orchestrator',
      )
      const hasActiveOrchestrator = this.agents.some(
        (agent) => agent.agent_type === 'orchestrator' && agent.status !== 'waiting',
      )

      // Set isLaunched flag based on agent state
      // - If there are non-orchestrator agents, project was launched
      // - If orchestrator is beyond waiting state, project was launched
      this.isLaunched = hasNonOrchestratorAgents || hasActiveOrchestrator

      // Log state for debugging (production-safe)
      if (this.isLaunched) {
        console.info(
          `[ProjectTabs] Project "${project.name || project.id}" loaded with ${this.agents.length} agents - Jobs tab enabled`,
        )
      }
    },

    /**
     * Clear current project
     */
    clearProject() {
      this.currentProject = null
      this.orchestratorMission = ''
      this.agents = []
      this.messages = []
      this.isStaging = false
      this.isLaunched = false
      this.stagingComplete = false // Handover 0287: Reset staging complete flag
      this.activeTab = 'launch'
      this.error = null
    },

    // ==================== Staging Workflow ====================

    /**
     * Stage project - Generate orchestrator prompt
     *
     * Handover 0086: Fixed bug where code expected mission/agents from endpoint.
     * These fields don't exist in the response - the endpoint only returns the prompt.
     * Mission and agents populate later via WebSocket events when the orchestrator
     * calls MCP tools externally (update_project_mission, create_agent_job_external).
     */
    async stageProject() {
      if (!this.currentProject) {
        this.error = 'No project selected'
        return
      }

      this.isStaging = true
      this.error = null

      try {
        const response = await api.prompts.staging(this.currentProject.id, { tool: 'claude-code' })

        if (!response.data?.prompt) {
          throw new Error('Invalid response from staging endpoint - no prompt returned')
        }

        // Copy orchestrator prompt to clipboard (handled by component)
        // Mission and agents will populate via WebSocket events when
        // orchestrator calls MCP tools externally
        this.isStaging = false

        return { success: true, prompt: response.data.prompt }
      } catch (error) {
        console.error('Failed to stage project:', error)
        this.error = error.message || 'Failed to stage project'
        this.isStaging = false
        throw error
      }
    },

    /**
     * Launch jobs - Create agent jobs and switch to Jobs tab
     */
    async launchJobs() {
      if (!this.readyToLaunch) {
        this.error = 'Project not ready to launch'
        return
      }

      this.loading = true
      this.error = null

      try {
        const response = await api.orchestrator.launchProject({
          project_id: this.currentProject.id,
        })

        this.isLaunched = true
        this.activeTab = 'jobs'
        this.loading = false

        // Subscribe to WebSocket updates
        const wsStore = useWebSocketStore()
        wsStore.subscribeToProject(this.currentProject.id)
      } catch (error) {
        console.error('Failed to launch jobs:', error)
        this.error = error.message || 'Failed to launch jobs'
        this.loading = false
        throw error
      }
    },

    /**
     * Cancel staging - Delete agents and mission
     */
    async cancelStaging() {
      if (!this.currentProject) return

      this.loading = true
      this.error = null

      try {
        await api.orchestrator.cancelStaging(this.currentProject.id)
        this.resetStaging()
      } catch (error) {
        console.error('Failed to cancel staging:', error)
        this.error = error.message || 'Failed to cancel staging'
        this.loading = false
        throw error
      }
    },

    /**
     * Reset staging state (local only)
     */
    resetStaging() {
      this.orchestratorMission = ''
      this.agents = []
      this.isStaging = false
      this.stagingComplete = false // Handover 0287: Reset staging complete flag
      this.loading = false
    },

    /**
     * Set staging complete flag (Handover 0287)
     * Called by ProjectTabs watcher when mission + orchestrator + specialists detected
     * @param {boolean} complete - Staging complete status
     */
    setStagingComplete(complete) {
      this.stagingComplete = complete
    },

    // ==================== Mission Management ====================

    /**
     * Set orchestrator mission
     * @param {string} mission - Mission text
     */
    setMission(mission) {
      this.orchestratorMission = mission
    },

    /**
     * Update orchestrator mission
     * @param {string} missionText - New mission text
     */
    async updateMission(missionText) {
      if (!this.currentProject) return

      try {
        await api.orchestrator.updateMission(this.currentProject.id, missionText)
        this.orchestratorMission = missionText
      } catch (error) {
        console.error('Failed to update mission:', error)
        this.error = error.message || 'Failed to update mission'
        throw error
      }
    },

    // ==================== Agent Management ====================

    /**
     * Add agent to list
     * @param {Object} agent - Agent object
     */
    addAgent(agent) {
      const exists = this.agents.find((a) => a.job_id === agent.job_id)
      if (!exists) {
        this.agents.push(agent)
      }
    },

    /**
     * Update agent
     * @param {string} agentId - Agent job_id
     * @param {Object} updates - Update fields
     */
    updateAgent(agentId, updates) {
      const index = this.agents.findIndex((a) => a.job_id === agentId)
      if (index !== -1) {
        this.agents[index] = { ...this.agents[index], ...updates }
      }
    },

    /**
     * Remove agent from list
     * @param {string} agentId - Agent job_id
     */
    removeAgent(agentId) {
      this.agents = this.agents.filter((a) => a.job_id !== agentId)
    },

    /**
     * Clear all agents
     */
    clearAgents() {
      this.agents = []
    },

    // ==================== Status Management ====================

    /**
     * Acknowledge agent (pending → active)
     * @param {string} agentId - Agent job_id
     */
    async acknowledgeAgent(agentId) {
      try {
        await api.agent_jobs.acknowledgeJob(agentId)
        this.updateAgent(agentId, {
          status: 'active',
          acknowledged: true,
          started_at: new Date().toISOString(),
        })
      } catch (error) {
        console.error('Failed to acknowledge agent:', error)
        throw error
      }
    },

    /**
     * Complete agent (active → complete)
     * @param {string} agentId - Agent job_id
     */
    async completeAgent(agentId) {
      try {
        await api.agent_jobs.completeJob(agentId)
        this.updateAgent(agentId, {
          status: 'complete',
          completed_at: new Date().toISOString(),
        })
      } catch (error) {
        console.error('Failed to complete agent:', error)
        throw error
      }
    },

    /**
     * Fail agent (active → failed)
     * @param {string} agentId - Agent job_id
     * @param {string} error - Error message
     */
    async failAgent(agentId, error) {
      try {
        await api.agent_jobs.failJob(agentId, error)
        this.updateAgent(agentId, {
          status: 'failed',
          completed_at: new Date().toISOString(),
          block_reason: error,
        })
      } catch (err) {
        console.error('Failed to fail agent:', err)
        throw err
      }
    },

    // ==================== Message Management ====================

    /**
     * Load existing messages for a project from the database
     * @param {string} projectId - Project ID to load messages for
     */
    async loadMessages(projectId) {
      try {
        const response = await api.messages.list({ project_id: projectId })
        if (response.data && Array.isArray(response.data)) {
          this.messages = response.data
          console.log(
            `[ProjectTabs] Loaded ${response.data.length} existing messages for project ${projectId}`,
          )
        }
      } catch (error) {
        console.error('[ProjectTabs] Failed to load messages:', error)
      }
    },

    /**
     * Add message to list
     * @param {Object} message - Message object
     */
    addMessage(message) {
      const exists = this.messages.find((m) => m.id === message.id)
      if (!exists) {
        this.messages.push(message)
      }
    },

    /**
     * Send message to agent(s) - Handover 0299: Unified UI Messaging Endpoint
     * Uses the unified /api/v1/messages/send endpoint for both broadcast and direct messages.
     *
     * @param {string} content - Message content
     * @param {string} recipient - 'orchestrator' | 'broadcast' | agent_id
     */
    async sendMessage(content, recipient) {
      if (!this.currentProject) return

      try {
        // Determine to_agents and message_type based on recipient
        let toAgents
        let messageType

        if (recipient === 'broadcast') {
          toAgents = ['all']
          messageType = 'broadcast'
        } else {
          // Find orchestrator job for this project
          const orchestratorJob = this.agents.find((a) => a.agent_type === 'orchestrator')

          if (!orchestratorJob) {
            throw new Error('Orchestrator not found')
          }
          toAgents = [orchestratorJob.job_id]
          messageType = 'direct'
        }

        // Use unified endpoint (Handover 0299)
        const response = await api.messages.sendUnified(
          this.currentProject.id,
          toAgents,
          content,
          messageType,
        )

        // Add to local messages
        this.addMessage({
          id: response.data.message_id,
          from: 'user',
          to_agent: recipient === 'broadcast' ? null : 'orchestrator',
          content,
          type: messageType,
          timestamp: new Date().toISOString(),
          status: 'sent',
        })
      } catch (error) {
        console.error('Failed to send message:', error)
        throw error
      }
    },

    // ==================== Closeout ====================

    /**
     * Closeout project - Mark project as complete
     */
    async closeoutProject() {
      if (!this.currentProject) return

      try {
        await api.projects.completeProject(this.currentProject.id)

        // Update local project
        if (this.currentProject) {
          this.currentProject.status = 'completed'
        }

        // Show summary (future: navigate to summary view)
        console.log('Project closeout complete')
      } catch (error) {
        console.error('Failed to closeout project:', error)
        this.error = error.message || 'Failed to closeout project'
        throw error
      }
    },

    // ==================== WebSocket Handlers ====================

    /**
     * Handle agent update from WebSocket
     * @param {Object} data - Agent update data
     */
    handleAgentUpdate(data) {
      const { job_id, status, progress, current_task, block_reason } = data

      this.updateAgent(job_id, {
        status,
        progress,
        current_task,
        block_reason,
      })
    },

    /**
     * Handle message update from WebSocket
     * @param {Object} data - Message update data
     */
    handleMessageUpdate(data) {
      this.addMessage(data)
    },

    /**
     * Handle project update from WebSocket
     * @param {Object} data - Project update data
     */
    handleProjectUpdate(data) {
      if (this.currentProject && data.project_id === this.currentProject.id) {
        this.currentProject = { ...this.currentProject, ...data }
      }
    },
  },
})
