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
const AGENT_COLORS = {
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
