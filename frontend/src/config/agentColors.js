/**
 * Agent Color Configuration
 *
 * Defines the visual branding for the 6 preseeded agent templates.
 * Colors match Handover 0077 specification and correspond to agent templates
 * from Handover 0041 (Agent Template Management).
 *
 * @see handovers/0077_launch_jobs_dual_tab_interface.md
 * @see handovers/0041/ (Agent Template Management)
 */

// Canonical role color map. Keep canonical roles aligned with backend
// seeded templates: orchestrator, implementer, tester, analyzer, reviewer, documenter.
// We also support legacy aliases (implementor, researcher) via a synonym map below.
export const AGENT_COLORS = {
  orchestrator: {
    hex: '#D4A574',
    name: 'ORCHESTRATOR',
    badge: 'OR',
    description: 'Primary coordinator and mission planner',
  },
  analyzer: {
    hex: '#E74C3C',
    name: 'ANALYZER',
    badge: 'AN',
    description: 'Architecture and analysis tasks',
  },
  implementer: {
    hex: '#3498DB',
    name: 'IMPLEMENTER',
    badge: 'IM',
    description: 'Implementation and development tasks',
  },
  documenter: {
    hex: '#27AE60',
    name: 'DOCUMENTER',
    badge: 'DO',
    description: 'Creates and updates documentation',
  },
  reviewer: {
    hex: '#9B59B6',
    name: 'REVIEWER',
    badge: 'RV',
    description: 'Code review and quality assurance',
  },
  tester: {
    hex: '#FFC300',
    name: 'TESTER',
    badge: 'TE',
    description: 'Testing and validation tasks',
  },
}

// Legacy/alias mapping (UI used to use these names)
const AGENT_SYNONYMS = {
  implementor: 'implementer',
  researcher: 'analyzer',
  // Common misspellings or variants
  analyser: 'analyzer',
  'code-reviewer': 'reviewer',
  'front-end-implementer': 'implementer',
  'frontend-implementer': 'implementer',
  'back-end-implementer': 'implementer',
  'backend-implementer': 'implementer',
  documentor: 'documenter',
  // Claude Code agent template mappings
  'tdd-implementor': 'implementer',
  'backend-integration-tester': 'tester',
  'frontend-tester': 'tester',
  'database-expert': 'analyzer',
  'deep-researcher': 'analyzer',
  'system-architect': 'analyzer',
  'documentation-manager': 'documenter',
  'network-security-engineer': 'reviewer',
  'ux-designer': 'implementer',
  'version-manager': 'reviewer',
  'installation-flow-agent': 'implementer',
  'orchestrator-coordinator': 'orchestrator',
}

/**
 * Get agent color by agent display name
 * @param {string} displayName - Agent display name (orchestrator, analyzer, etc.)
 * @returns {Object} Color configuration object
 */
export function getAgentColor(displayName) {
  const normalizedType = displayName?.toLowerCase() || ''
  const canonical = AGENT_SYNONYMS[normalizedType] || normalizedType
  return AGENT_COLORS[canonical] || AGENT_COLORS.orchestrator
}

/**
 * Get agent badge ID with instance number
 * @param {string} displayName - Agent display name
 * @param {number} instanceNumber - Instance number (1, 2, 3, etc.)
 * @returns {string} Badge ID (e.g., "Im", "I2", "I3")
 */
export function getAgentBadgeId(displayName, instanceNumber = 1) {
  const color = getAgentColor(displayName)

  if (instanceNumber === 1) {
    return color.badge
  }

  // For multiple instances: I2, I3, etc.
  const firstLetter = color.badge.charAt(0)
  return `${firstLetter}${instanceNumber}`
}

/**
 * Get darkened color for headers (10% darker)
 * @param {string} hex - Hex color code
 * @returns {string} Darkened hex color
 */
export function darkenColor(hex, percent = 10) {
  const num = parseInt(hex.replace('#', ''), 16)
  const amt = Math.round(2.55 * percent)
  const R = (num >> 16) - amt
  const G = ((num >> 8) & 0x00ff) - amt
  const B = (num & 0x0000ff) - amt

  return (
    '#' +
    (
      0x1000000 +
      (R < 255 ? (R < 1 ? 0 : R) : 255) * 0x10000 +
      (G < 255 ? (G < 1 ? 0 : G) : 255) * 0x100 +
      (B < 255 ? (B < 1 ? 0 : B) : 255)
    )
      .toString(16)
      .slice(1)
      .toUpperCase()
  )
}

/**
 * Get lightened color for borders (20% lighter)
 * @param {string} hex - Hex color code
 * @returns {string} Lightened hex color
 */
export function lightenColor(hex, percent = 20) {
  const num = parseInt(hex.replace('#', ''), 16)
  const amt = Math.round(2.55 * percent)
  const R = (num >> 16) + amt
  const G = ((num >> 8) & 0x00ff) + amt
  const B = (num & 0x0000ff) + amt

  return (
    '#' +
    (
      0x1000000 +
      (R < 255 ? (R < 1 ? 0 : R) : 255) * 0x10000 +
      (G < 255 ? (G < 1 ? 0 : G) : 255) * 0x100 +
      (B < 255 ? (B < 1 ? 0 : B) : 255)
    )
      .toString(16)
      .slice(1)
      .toUpperCase()
  )
}

/**
 * Get all agent colors as array
 * @returns {Array} Array of agent color objects
 */
export function getAllAgentColors() {
  return Object.entries(AGENT_COLORS).map(([key, value]) => ({
    type: key,
    ...value,
  }))
}

/**
 * Agent status color mapping
 * (Status badges shown on agent cards)
 */
export const AGENT_STATUS_COLORS = {
  waiting: {
    color: '#90A4AE',
    label: 'Waiting',
  },
  working: {
    color: '#3498DB',
    label: 'Working',
  },
  complete: {
    color: '#FFC300',
    label: 'Complete',
  },
  failure: {
    color: '#C6298C',
    label: 'Failure',
  },
  blocked: {
    color: '#E67E22',
    label: 'Blocked',
  },
}

/**
 * Launch prompt tool icons
 * (Shown on Orchestrator card in Jobs Tab)
 */
export const LAUNCH_PROMPT_TOOLS = {
  claudeCode: {
    name: 'Claude Code',
    icon: 'mdi-code-braces-box',
    color: '#E67E22',
    command: 'claude-code mcp add',
  },
  codex: {
    name: 'Codex CLI',
    icon: 'mdi-application-brackets',
    color: '#9B59B6',
    command: 'codex mcp add',
  },
  gemini: {
    name: 'Gemini CLI',
    icon: 'mdi-star-four-points',
    color: '#3498DB',
    command: 'gemini mcp add',
  },
}
