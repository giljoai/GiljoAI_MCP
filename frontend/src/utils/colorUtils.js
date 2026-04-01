/**
 * Shared color utility functions for the 0870 design system.
 * Extracted from duplicated hexToRgba helpers across multiple components.
 *
 * @module colorUtils
 */

import { getAgentColor } from '@/config/agentColors'

/**
 * Convert a hex color string to an rgba() CSS value.
 * @param {string} hex - Hex color string (e.g. '#D4B08A')
 * @param {number} alpha - Alpha value between 0 and 1
 * @returns {string} CSS rgba() string
 */
export function hexToRgba(hex, alpha) {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

/**
 * Get tinted square badge style object for an agent by name.
 * Uses rgba(color, 0.15) background + bright color text + 8px border-radius.
 * Consolidates duplicate implementations from LaunchTab, JobsTab,
 * AgentTableView, AgentJobModal, etc.
 *
 * @param {string} agentName - Agent display name (e.g. 'orchestrator', 'Backend-Implementer')
 * @returns {{ backgroundColor: string, color: string, borderRadius: string }}
 */
export function getAgentBadgeStyle(agentName) {
  const colorObj = getAgentColor(agentName)
  const hex = colorObj?.hex || '#8895a8'
  return {
    backgroundColor: hexToRgba(hex, 0.15),
    color: hex,
    borderRadius: '8px',
  }
}
