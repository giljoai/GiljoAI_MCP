/**
 * useAgentData Composable
 *
 * Shared agent data management logic for card and table views.
 * Extracted from AgentCardGrid and AgentCard to prevent code duplication.
 *
 * Handover 0228: StatusBoardTable Component
 *
 * REUSED by:
 * - AgentCardGrid.vue (existing component)
 * - AgentTableView.vue (new component)
 *
 * Ensures zero logic duplication between views.
 */

import { computed } from 'vue'

export function useAgentData(agents) {
  /**
   * Priority sorting algorithm
   * Extracted from AgentCardGrid.vue to prevent duplication
   *
   * Sort order:
   * 1. Status priority (failed/blocked → waiting → working → complete)
   * 2. Agent type (orchestrator first)
   * 3. Alphabetical by name
   */
  const sortedAgents = computed(() => {
    return [...agents.value].sort((a, b) => {
      // Status priority mapping
      const priority = {
        failed: 1,
        blocked: 1,
        waiting: 2,
        working: 3,
        complete: 4,
        cancelled: 5,
        decommissioned: 6,
      }

      // Primary sort: status priority
      const diff = (priority[a.status] || 999) - (priority[b.status] || 999)
      if (diff !== 0) return diff

      // Secondary sort: orchestrator first
      if (a.agent_type === 'orchestrator') return -1
      if (b.agent_type === 'orchestrator') return 1

      // Tertiary sort: alphabetical by name
      return (a.agent_name || '').localeCompare(b.agent_name || '')
    })
  })

  /**
   * Message count calculation
   * Extracted from AgentCard.vue message badge logic
   *
   * @param {Object} job - Agent job object with messages array
   * @returns {Object} - { unread, acknowledged, total }
   */
  const getMessageCounts = (job) => {
    const messages = job.messages || []
    return {
      unread: messages.filter((m) => m.status === 'pending').length,
      acknowledged: messages.filter((m) => m.status === 'acknowledged').length,
      total: messages.length,
    }
  }

  /**
   * Status color mapping
   * Extracted from AgentCard.vue status chip logic
   *
   * @param {String} status - Agent status
   * @returns {String} - Vuetify color name
   */
  const getStatusColor = (status) => {
    const colors = {
      waiting: 'grey',
      working: 'blue',
      blocked: 'orange',
      complete: 'green',
      failed: 'red',
      cancelled: 'grey-darken-2',
      decommissioned: 'grey-lighten-1',
    }
    return colors[status] || 'grey'
  }

  /**
   * Agent type color mapping
   * Extracted from AgentCard.vue avatar logic
   *
   * @param {String} agentType - Agent type (orchestrator, analyzer, etc.)
   * @returns {String} - Vuetify color name
   */
  const getAgentTypeColor = (agentType) => {
    const colors = {
      orchestrator: 'orange',
      analyzer: 'red',
      implementer: 'blue',
      tester: 'yellow',
      reviewer: 'purple',
    }
    return colors[agentType] || 'grey'
  }

  /**
   * Agent type abbreviation
   * Extracted from AgentCard.vue avatar text
   *
   * @param {String} agentType - Agent type
   * @returns {String} - Two-letter abbreviation
   */
  const getAgentAbbreviation = (agentType) => {
    const abbr = {
      orchestrator: 'Or',
      analyzer: 'An',
      implementer: 'Im',
      tester: 'Te',
      reviewer: 'Re',
    }
    return abbr[agentType] || agentType.substring(0, 2).toUpperCase()
  }

  /**
   * Health status color mapping
   * Extracted from health indicator logic
   *
   * @param {String} healthStatus - Health status (healthy, warning, critical, etc.)
   * @returns {String} - Vuetify color name
   */
  const getHealthColor = (healthStatus) => {
    const colors = {
      healthy: 'success',
      warning: 'warning',
      critical: 'error',
      timeout: 'error',
      unknown: 'grey',
    }
    return colors[healthStatus] || 'grey'
  }

  /**
   * Health status icon mapping
   * Maps health status to Material Design icon
   *
   * @param {String} healthStatus - Health status
   * @returns {String} - MDI icon name
   */
  const getHealthIcon = (healthStatus) => {
    const icons = {
      healthy: 'mdi-check-circle',
      warning: 'mdi-alert',
      critical: 'mdi-alert-octagon',
      timeout: 'mdi-timer-alert',
      unknown: 'mdi-help-circle',
    }
    return icons[healthStatus] || 'mdi-help-circle'
  }

  // Return all methods and computed properties
  return {
    sortedAgents,
    getMessageCounts,
    getStatusColor,
    getAgentTypeColor,
    getAgentAbbreviation,
    getHealthColor,
    getHealthIcon,
  }
}
