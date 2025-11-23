/**
 * WebSocket Store Integrations
 * Sets up message routing between WebSocket and other Pinia stores
 *
 * This replaces the setupMessageHandlers() logic from the old stores/websocket.js
 * Call setupWebSocketIntegrations() once in App.vue or main router
 */

import { useWebSocketStore } from './websocket'
import { useProjectStore } from './projects'
import { useAgentStore } from './agents'
import { useMessageStore } from './messages'
import { useTaskStore } from './tasks'
import { useProductStore } from './products'
import { useToast } from '@/composables/useToast'

let isInitialized = false

/**
 * Set up WebSocket integrations with other stores
 * Call this once when app starts (e.g., in App.vue or router)
 */
export function setupWebSocketIntegrations() {
  if (isInitialized) {
    console.warn('[WebSocket Integrations] Already initialized')
    return
  }

  const wsStore = useWebSocketStore()
  const { showToast } = useToast()

  console.log('[WebSocket Integrations] Setting up integrations...')

  // ============================================
  // AGENT UPDATES
  // ============================================

  wsStore.on('agent_update', (data) => {
    const agentsStore = useAgentStore()
    if (agentsStore.handleRealtimeUpdate) {
      agentsStore.handleRealtimeUpdate(data.data || data)
    }
  })

  // Agent health alerts (Handover 0106)
  wsStore.on('agent:health_alert', (data) => {
    const agentsStore = useAgentStore()
    const payload = data.data || data

    if (agentsStore.handleHealthAlert) {
      agentsStore.handleHealthAlert(payload)
    }

    // Show notification for critical/timeout states
    const { health_state, agent_type, issue_description } = payload
    if (health_state === 'critical' || health_state === 'timeout') {
      showToast({
        title: 'Agent Health Alert',
        message: `${agent_type} - ${issue_description}`,
        color: health_state === 'timeout' ? 'error' : 'warning',
        icon: health_state === 'timeout' ? 'mdi-clock-remove' : 'mdi-alert-circle',
        timeout: 8000, // Longer timeout for critical alerts
      })
    }
  })

  // Agent health recovery (Handover 0106)
  wsStore.on('agent:health_recovered', (data) => {
    const agentsStore = useAgentStore()
    if (agentsStore.handleHealthRecovered) {
      agentsStore.handleHealthRecovered(data.data || data)
    }
  })

  // Agent auto-failed (Handover 0106)
  wsStore.on('agent:auto_failed', (data) => {
    const payload = data.data || data
    const { agent_type, reason } = payload

    showToast({
      title: 'Agent Auto-Failed',
      message: `${agent_type} - ${reason}`,
      color: 'error',
      icon: 'mdi-robot-dead',
      timeout: 10000, // Long timeout for failures
    })
  })

  // ============================================
  // MESSAGE UPDATES
  // ============================================

  wsStore.on('message', (data) => {
    const messagesStore = useMessageStore()
    if (messagesStore.handleRealtimeUpdate) {
      messagesStore.handleRealtimeUpdate(data.data || data)
    }
  })

  // ============================================
  // PROJECT UPDATES
  // ============================================

  wsStore.on('project_update', (data) => {
    const projectsStore = useProjectStore()
    if (projectsStore.handleRealtimeUpdate) {
      projectsStore.handleRealtimeUpdate(data.data || data)
    }
  })

  // ============================================
  // TASK UPDATES
  // ============================================

  wsStore.on('entity_update', (data) => {
    const payload = data.data || data

    if (payload.entity_type === 'task') {
      const tasksStore = useTaskStore()
      const productStore = useProductStore()

      // Filter by current product if one is selected
      if (productStore.currentProductId) {
        if (payload.product_id === productStore.currentProductId) {
          if (tasksStore.handleRealtimeUpdate) {
            tasksStore.handleRealtimeUpdate(payload)
          }
        }
      } else {
        // No product filter, process all updates
        if (tasksStore.handleRealtimeUpdate) {
          tasksStore.handleRealtimeUpdate(payload)
        }
      }
    }
  })

  // ============================================
  // PROGRESS UPDATES
  // ============================================

  wsStore.on('progress', (data) => {
    console.log('[WebSocket] Progress update:', data)

    // Emit custom event for components to listen to
    window.dispatchEvent(
      new CustomEvent('ws-progress', {
        detail: data.data || data,
      }),
    )
  })

  // ============================================
  // NOTIFICATIONS
  // ============================================

  wsStore.on('notification', (data) => {
    console.log('[WebSocket] Notification:', data)

    // Emit custom event for notification system
    window.dispatchEvent(
      new CustomEvent('ws-notification', {
        detail: data.data || data,
      }),
    )
  })

  // ============================================
  // AGENT COMMUNICATION EVENTS (from flowWebSocket.js)
  // ============================================

  // Agent status updates
  wsStore.on('agent_communication:status_update', (data) => {
    // This can be handled by components using the agentFlow store
    // For now, just emit a custom event
    window.dispatchEvent(
      new CustomEvent('agent:status_update', {
        detail: data,
      }),
    )
  })

  // Agent spawned
  wsStore.on('agent_communication:agent_spawned', (data) => {
    window.dispatchEvent(
      new CustomEvent('agent:spawned', {
        detail: data,
      }),
    )
  })

  // Agent completed
  wsStore.on('agent_communication:agent_complete', (data) => {
    window.dispatchEvent(
      new CustomEvent('agent:complete', {
        detail: data,
      }),
    )
  })

  // Agent error
  wsStore.on('agent_communication:error', (data) => {
    window.dispatchEvent(
      new CustomEvent('agent:error', {
        detail: data,
      }),
    )
  })

  // Message sent
  wsStore.on('agent_communication:message_sent', (data) => {
    window.dispatchEvent(
      new CustomEvent('agent:message_sent', {
        detail: data,
      }),
    )
  })

  // Message acknowledged
  wsStore.on('agent_communication:message_acknowledged', (data) => {
    window.dispatchEvent(
      new CustomEvent('agent:message_acknowledged', {
        detail: data,
      }),
    )
  })

  // Message completed
  wsStore.on('agent_communication:message_completed', (data) => {
    window.dispatchEvent(
      new CustomEvent('agent:message_completed', {
        detail: data,
      }),
    )
  })

  // Artifact created
  wsStore.on('agent_communication:artifact_created', (data) => {
    window.dispatchEvent(
      new CustomEvent('agent:artifact_created', {
        detail: data,
      }),
    )
  })

  // Directory structure
  wsStore.on('agent_communication:directory_structure', (data) => {
    window.dispatchEvent(
      new CustomEvent('agent:directory_structure', {
        detail: data,
      }),
    )
  })

  // Code artifact
  wsStore.on('agent_communication:code_artifact', (data) => {
    window.dispatchEvent(
      new CustomEvent('agent:code_artifact', {
        detail: data,
      }),
    )
  })

  // Mission events
  wsStore.on('mission:started', (data) => {
    window.dispatchEvent(
      new CustomEvent('mission:started', {
        detail: data,
      }),
    )
  })

  wsStore.on('mission:progress', (data) => {
    window.dispatchEvent(
      new CustomEvent('mission:progress', {
        detail: data,
      }),
    )
  })

  wsStore.on('mission:completed', (data) => {
    window.dispatchEvent(
      new CustomEvent('mission:completed', {
        detail: data,
      }),
    )
  })

  wsStore.on('mission:failed', (data) => {
    window.dispatchEvent(
      new CustomEvent('mission:failed', {
        detail: data,
      }),
    )
  })

  // ============================================
  // MISSION TRACKING EVENTS (Handover 0233 Phase 5)
  // ============================================

  // Listen for job:mission_read events
  wsStore.on('job:mission_read', (data) => {
    console.log('[MISSION_TRACKING] Job mission read event:', data)

    const payload = data.data || data

    // Update agents store
    const agentsStore = useAgentStore()
    if (agentsStore && agentsStore.updateAgentField) {
      agentsStore.updateAgentField(payload.job_id, 'mission_read_at', payload.mission_read_at)
    }

    // Emit custom event for components
    window.dispatchEvent(
      new CustomEvent('agent:mission_read', {
        detail: { jobId: payload.job_id, timestamp: payload.mission_read_at },
      }),
    )
  })

  // Listen for job:mission_acknowledged events
  wsStore.on('job:mission_acknowledged', (data) => {
    console.log('[MISSION_TRACKING] Job mission acknowledged event:', data)

    const payload = data.data || data

    // Update agents store
    const agentsStore = useAgentStore()
    if (agentsStore && agentsStore.updateAgentField) {
      agentsStore.updateAgentField(
        payload.job_id,
        'mission_acknowledged_at',
        payload.mission_acknowledged_at,
      )
    }

    // Emit custom event for components
    window.dispatchEvent(
      new CustomEvent('agent:mission_acknowledged', {
        detail: { jobId: payload.job_id, timestamp: payload.mission_acknowledged_at },
      }),
    )
  })

  isInitialized = true
  console.log('[WebSocket Integrations] Setup complete')
}

/**
 * Check if integrations are initialized
 */
export function isWebSocketIntegrationsInitialized() {
  return isInitialized
}
