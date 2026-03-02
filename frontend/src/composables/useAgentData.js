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
import { getAgentColor } from '@/config/agentColors'
import { AGENT_STATUS_PRIORITY } from '@/utils/constants'

export function useAgentData(agents) {
  /**
   * Priority sorting algorithm
   * Extracted from AgentCardGrid.vue to prevent duplication
   *
   * Sort order: working > blocked > silent > waiting > complete > decommissioned
   * Uses shared AGENT_STATUS_PRIORITY from constants.
   *
   * Secondary: orchestrator first
   * Tertiary: alphabetical by name
   */
  const sortedAgents = computed(() => {
    return [...agents.value].sort((a, b) => {
      // Primary sort: status priority (shared constant)
      const diff = (AGENT_STATUS_PRIORITY[a.status] ?? 999) - (AGENT_STATUS_PRIORITY[b.status] ?? 999)
      if (diff !== 0) return diff

      // Secondary sort: orchestrator first
      if (a.agent_display_name === 'orchestrator') return -1
      if (b.agent_display_name === 'orchestrator') return 1

      // Tertiary sort: alphabetical by name
      return (a.agent_name || '').localeCompare(b.agent_name || '')
    })
  })

  /**
   * Message count calculation
   * Uses server-provided counter fields (Handover 0387g)
   *
   * @param {Object} job - Agent job object with message counter fields
   * @returns {Object} - { sent, waiting, read }
   */
  const getMessageCounts = (job) => {
    return {
      sent: job?.messages_sent_count ?? 0,
      waiting: job?.messages_waiting_count ?? 0,
      read: job?.messages_read_count ?? 0,
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
      silent: 'amber-darken-2',
      decommissioned: 'grey-lighten-1',
    }
    return colors[status] || 'grey'
  }

  /**
   * Agent display name color mapping
   * Delegates to centralized getAgentColor function for consistent color resolution
   *
   * @param {String} agentName - Agent name/template key (e.g., 'tdd-implementor', 'analyzer')
   * @returns {Object} Color configuration object with hex, name, badge, description
   */
  const getAgentDisplayNameColor = (agentName) => {
    return getAgentColor(agentName)
  }

  /**
   * Agent display name abbreviation
   * Extracted from AgentCard.vue avatar text
   *
   * Split by dash, space, or underscore and use first letter of each part
   * e.g., "Backend-Implementer" → "BI", "Backend-Tester" → "BT"
   *
   * @param {String} displayName - Agent display name
   * @returns {String} - Two-letter abbreviation
   */
  const getAgentAbbreviation = (displayName) => {
    if (!displayName) return '??'

    // Split by dash, space, or underscore
    const parts = displayName.split(/[-_\s]+/).filter(Boolean)

    if (parts.length >= 2) {
      // Use first letter of first two parts: "Backend-Implementer" → "BI"
      return (parts[0][0] + parts[1][0]).toUpperCase()
    }

    // Single word fallback: use first two letters
    return displayName.substring(0, 2).toUpperCase()
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
    getAgentDisplayNameColor,
    getAgentAbbreviation,
    getHealthColor,
    getHealthIcon,
  }
}
