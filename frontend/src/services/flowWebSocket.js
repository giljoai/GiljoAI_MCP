/**
 * Flow WebSocket Service for Agent Flow Visualization
 * Handles real-time updates for agent status, messages, and artifacts
 */

import websocketService from './websocket'
import { useAgentFlowStore } from '@/stores/agentFlow'

class FlowWebSocketService {
  constructor() {
    this.store = null
    this.isInitialized = false
    this.subscriptions = new Map()
    this.eventHandlers = new Map()
  }

  /**
   * Initialize the flow WebSocket service
   */
  initialize() {
    if (this.isInitialized) {
      return
    }

    this.store = useAgentFlowStore()

    // Subscribe to agent communication events
    this.subscribeToAgentEvents()

    // Subscribe to artifact events
    this.subscribeToArtifactEvents()

    // Subscribe to mission events
    this.subscribeToMissionEvents()

    this.isInitialized = true
  }

  /**
   * Subscribe to agent-related WebSocket events
   */
  subscribeToAgentEvents() {
    // Agent status update
    websocketService.onMessage('agent_communication:status_update', (data) => {
      if (this.store) {
        this.store.handleAgentUpdate({
          agent_name: data.agent_name,
          agentId: data.agent_id,
          status: data.status,
          health: data.health,
          context_used: data.context_used,
          active_jobs: data.active_jobs,
        })
      }

      this.triggerEventHandler('agent:status', data)
    })

    // Agent spawn event
    websocketService.onMessage('agent_communication:agent_spawned', (data) => {
      if (this.store) {
        // Reinitialize flow to include new agent
        this.store.initializeFromAgents()
      }

      this.triggerEventHandler('agent:spawned', data)
    })

    // Agent completion event
    websocketService.onMessage('agent_communication:agent_complete', (data) => {
      if (this.store) {
        this.store.handleAgentUpdate({
          agent_name: data.agent_name,
          agentId: data.agent_id,
          status: 'completed',
          duration: data.duration,
          tokens_used: data.tokens_used,
        })
      }

      this.triggerEventHandler('agent:complete', data)
    })

    // Agent error event
    websocketService.onMessage('agent_communication:error', (data) => {
      if (this.store) {
        this.store.handleAgentUpdate({
          agent_name: data.agent_name,
          agentId: data.agent_id,
          status: 'error',
        })
      }

      this.triggerEventHandler('agent:error', data)
    })
  }

  /**
   * Subscribe to message flow WebSocket events
   */
  subscribeToMessageFlowEvents() {
    // Message sent event
    websocketService.onMessage('agent_communication:message_sent', (data) => {
      if (this.store) {
        this.store.handleMessageFlow({
          message_id: data.message_id,
          from_agent: data.from_agent,
          to_agents: data.to_agents,
          content: data.content,
          status: 'sent',
          created_at: data.created_at,
        })
      }

      this.triggerEventHandler('message:sent', data)
    })

    // Message acknowledged event
    websocketService.onMessage('agent_communication:message_acknowledged', (data) => {
      if (this.store) {
        const node = this.store.nodes.find((n) => n.data.agentName === data.agent_name)
        if (node && node.data.messages) {
          const msg = node.data.messages.find((m) => m.id === data.message_id)
          if (msg) {
            msg.status = 'acknowledged'
          }
        }
      }

      this.triggerEventHandler('message:acknowledged', data)
    })

    // Message completed event
    websocketService.onMessage('agent_communication:message_completed', (data) => {
      if (this.store) {
        const node = this.store.nodes.find((n) => n.data.agentName === data.agent_name)
        if (node && node.data.messages) {
          const msg = node.data.messages.find((m) => m.id === data.message_id)
          if (msg) {
            msg.status = 'completed'
            msg.result = data.result
          }
        }
      }

      this.triggerEventHandler('message:completed', data)
    })
  }

  /**
   * Subscribe to artifact WebSocket events
   */
  subscribeToArtifactEvents() {
    // Artifact created event
    websocketService.onMessage('agent_communication:artifact_created', (data) => {
      if (this.store) {
        this.store.addArtifact({
          type: 'file',
          name: data.filename || data.name,
          path: data.filepath || data.path,
          size: data.filesize || data.size,
          mimeType: data.content_type || data.mime_type,
          agentName: data.agent_name,
          agentId: data.agent_id,
          description: data.description,
          tags: data.tags || [],
        })
      }

      this.triggerEventHandler('artifact:created', data)
    })

    // Directory structure event
    websocketService.onMessage('agent_communication:directory_structure', (data) => {
      if (this.store) {
        this.store.addArtifact({
          type: 'directory',
          name: data.directory_name || 'Project Structure',
          path: data.root_path,
          structure: data.structure,
          agentName: data.agent_name,
          agentId: data.agent_id,
          description: 'Directory structure',
          tags: ['structure'],
        })
      }

      this.triggerEventHandler('artifact:directory', data)
    })

    // Code artifact event
    websocketService.onMessage('agent_communication:code_artifact', (data) => {
      if (this.store) {
        this.store.addArtifact({
          type: 'code',
          name: data.filename,
          path: data.filepath,
          language: data.language,
          code: data.code,
          agentName: data.agent_name,
          agentId: data.agent_id,
          description: data.description || `${data.language} code`,
          tags: [data.language, 'code'],
        })
      }

      this.triggerEventHandler('artifact:code', data)
    })
  }

  /**
   * Subscribe to mission WebSocket events
   */
  subscribeToMissionEvents() {
    // Mission started event
    websocketService.onMessage('mission:started', (data) => {
      if (this.store) {
        this.store.setMissionData({
          id: data.mission_id,
          title: data.title,
          description: data.description,
          status: 'active',
          agents: data.agents || [],
          goals: data.goals || [],
        })
      }

      this.triggerEventHandler('mission:started', data)
    })

    // Mission progress event
    websocketService.onMessage('mission:progress', (data) => {
      if (this.store && this.store.missionData) {
        this.store.missionData.progress = data.progress
        this.store.missionData.currentStep = data.current_step
        this.store.missionData.completedSteps = data.completed_steps
      }

      this.triggerEventHandler('mission:progress', data)
    })

    // Mission completed event
    websocketService.onMessage('mission:completed', (data) => {
      if (this.store && this.store.missionData) {
        this.store.missionData.status = 'completed'
        this.store.missionData.completedAt = new Date().toISOString()
        this.store.missionData.result = data.result
      }

      this.triggerEventHandler('mission:completed', data)
    })

    // Mission failed event
    websocketService.onMessage('mission:failed', (data) => {
      if (this.store && this.store.missionData) {
        this.store.missionData.status = 'failed'
        this.store.missionData.failedAt = new Date().toISOString()
        this.store.missionData.error = data.error
      }

      this.triggerEventHandler('mission:failed', data)
    })
  }

  /**
   * Register custom event handler
   */
  on(event, handler) {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, new Set())
    }

    this.eventHandlers.get(event).add(handler)

    // Return unsubscribe function
    return () => {
      const handlers = this.eventHandlers.get(event)
      if (handlers) {
        handlers.delete(handler)
      }
    }
  }

  /**
   * Trigger event handlers
   */
  triggerEventHandler(event, data) {
    const handlers = this.eventHandlers.get(event)
    if (handlers) {
      handlers.forEach((handler) => {
        try {
          handler(data)
        } catch (error) {
          console.error(`Error in flow WebSocket event handler for ${event}:`, error)
        }
      })
    }
  }

  /**
   * Subscribe to agent updates
   */
  subscribeToAgent(agentId) {
    const subscriptionKey = `agent:${agentId}`
    if (!this.subscriptions.has(subscriptionKey)) {
      websocketService.subscribe('agent', agentId)
      this.subscriptions.set(subscriptionKey, true)
    }
  }

  /**
   * Unsubscribe from agent updates
   */
  unsubscribeFromAgent(agentId) {
    const subscriptionKey = `agent:${agentId}`
    if (this.subscriptions.has(subscriptionKey)) {
      websocketService.unsubscribe('agent', agentId)
      this.subscriptions.delete(subscriptionKey)
    }
  }

  /**
   * Subscribe to project updates
   */
  subscribeToProject(projectId) {
    const subscriptionKey = `project:${projectId}`
    if (!this.subscriptions.has(subscriptionKey)) {
      websocketService.subscribe('project', projectId)
      this.subscriptions.set(subscriptionKey, true)
    }
  }

  /**
   * Unsubscribe from project updates
   */
  unsubscribeFromProject(projectId) {
    const subscriptionKey = `project:${projectId}`
    if (this.subscriptions.has(subscriptionKey)) {
      websocketService.unsubscribe('project', projectId)
      this.subscriptions.delete(subscriptionKey)
    }
  }

  /**
   * Get all active subscriptions
   */
  getSubscriptions() {
    return Array.from(this.subscriptions.keys())
  }

  /**
   * Clear all subscriptions
   */
  clearSubscriptions() {
    this.subscriptions.forEach((_, key) => {
      const [type, id] = key.split(':')
      websocketService.unsubscribe(type, id)
    })
    this.subscriptions.clear()
  }

  /**
   * Reset the service
   */
  reset() {
    this.clearSubscriptions()
    this.eventHandlers.clear()
    this.isInitialized = false
  }
}

// Create singleton instance
const flowWebSocketService = new FlowWebSocketService()

export default flowWebSocketService
export { FlowWebSocketService }
