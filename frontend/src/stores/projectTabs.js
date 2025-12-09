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

/**
 * Transform flat steps fields to nested object (Handover 0334)
 *
 * API returns: { steps_total: 5, steps_completed: 3, current_step: "..." }
 * UI expects:  { steps: { total: 5, completed: 3, current: "..." } }
 *
 * @param {Object} job - Job data from API
 * @returns {Object} Job data with nested steps object
 */
function transformJobSteps(job) {
  if (!job) return job

  // If already has nested steps object, preserve it
  if (job.steps && typeof job.steps === 'object') {
    return job
  }

  return {
    ...job,
    steps: {
      total: job.steps_total || 0,
      completed: job.steps_completed || 0,
      current: job.current_step || null
    }
  }
}

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

    // Ready state: Launch Jobs enabled when staging is complete
    // Simplified: message:sent event = staging done = ready to launch
    // No need to check agents/mission - the broadcast message IS the completion signal
    readyToLaunch(state) {
      return state.stagingComplete && !state.isStaging
    },
  },

  actions: {
    // ==================== Utility Functions ====================

    /**
     * Transform flat steps fields to nested object (Handover 0334)
     * Exposed as action for external access (e.g., tests, WebSocket handlers)
     *
     * @param {Object} job - Job data from API
     * @returns {Object} Job data with nested steps object
     */
    transformJobSteps(job) {
      return transformJobSteps(job)
    },

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

      // CRITICAL: Reset staging state FIRST when switching to a different project
      // This ensures complete project isolation - state from Project A never leaks to Project B
      // Fix for: Button states persisting across projects (Handover 0335)
      const isNewProject = !this.currentProject || this.currentProject.id !== project.id
      if (isNewProject) {
        this.isStaging = false
        this.stagingComplete = false
        this.isLaunched = false
        this.messages = []
        console.info(`[ProjectTabs] Switching to project "${project.name || project.id}" - reset staging state`)
      }

      // Set project data
      this.currentProject = project
      this.orchestratorMission = project.mission || ''
      // Transform agent steps from flat fields to nested object (Handover 0334)
      this.agents = Array.isArray(project.agents)
        ? project.agents.map(transformJobSteps)
        : []

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

      // Set stagingComplete based on THIS project's actual state (not inherited from previous)
      // This ensures persistence across page reloads while maintaining project isolation
      if (hasNonOrchestratorAgents) {
        this.stagingComplete = true
        console.info('[ProjectTabs] Specialist agents found - staging marked complete')
      }
      // Note: stagingComplete stays false (from reset above) if project has no specialist agents

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
        // Transform steps from flat fields to nested object (Handover 0334)
        this.agents.push(transformJobSteps(agent))
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
        // Transform updates with steps fields (Handover 0334)
        const transformedUpdates = transformJobSteps(updates)
        // Merge steps object intelligently if both exist
        const currentAgent = this.agents[index]
        if (currentAgent.steps && transformedUpdates.steps) {
          transformedUpdates.steps = { ...currentAgent.steps, ...transformedUpdates.steps }
        }
        this.agents[index] = { ...currentAgent, ...transformedUpdates }
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

          // If messages exist, staging is complete (messages only sent after staging)
          if (response.data.length > 0) {
            this.stagingComplete = true
            console.log('[ProjectTabs] Messages found - staging marked complete')
          }
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

    // ==================== Real-time Message Counter Updates ====================
    // These handlers update agent message counters in real-time via WebSocket
    // Ensures counters update regardless of which tab (Launch/Jobs) is active

    /**
     * Handle message:sent WebSocket event
     * Updates the sender agent's "Messages Sent" counter
     * @param {Object} data - Message sent event data
     */
    handleMessageSent(data) {
      // Verify this event is for the current project
      if (!this.currentProject || data.project_id !== this.currentProject.id) {
        return
      }

      const fromAgent = data.from_agent

      // Find the sender agent and increment their sent count
      // For broadcasts from orchestrator, from_agent is 'orchestrator'
      const senderAgent = this.agents.find(
        (a) => a.agent_type === fromAgent || a.job_id === fromAgent,
      )

      if (senderAgent) {
        // Initialize messages array if needed
        if (!senderAgent.messages) {
          senderAgent.messages = []
        }

        // Add outbound message record for tracking
        senderAgent.messages.push({
          id: data.message_id,
          direction: 'outbound',
          status: 'sent',
          timestamp: data.timestamp || new Date().toISOString(),
        })

      }

      // Mark staging as complete when first message is sent (broadcast = staging done)
      if (!this.stagingComplete && data.message_type === 'broadcast') {
        this.stagingComplete = true
      }
    },

    /**
     * Handle message:received WebSocket event
     * Updates recipient agents' "Messages Waiting" counters
     * @param {Object} data - Message received event data
     */
    handleMessageReceived(data) {
      // Verify this event is for the current project
      if (!this.currentProject || data.project_id !== this.currentProject.id) {
        return
      }

      const recipientIds = data.to_agent_ids || []

      // Update each recipient agent's waiting count
      for (const recipientId of recipientIds) {
        const agent = this.agents.find(
          (a) => a.job_id === recipientId || a.agent_type === recipientId,
        )

        if (agent) {
          // Initialize messages array if needed
          if (!agent.messages) {
            agent.messages = []
          }

          // Add inbound message record for tracking
          agent.messages.push({
            id: data.message_id,
            from: data.from_agent,
            direction: 'inbound',
            status: 'waiting',
            timestamp: data.timestamp || new Date().toISOString(),
          })

        }
      }

      // Mark staging as complete when first message received
      if (!this.stagingComplete) {
        this.stagingComplete = true
      }
    },
  },
})
