/**
 * agentDisplay.js — shared row-level display helpers
 *
 * Lifted from JobsTab (FE-6042a) so both JobsTab and AgentRow can share
 * the `isOrchestrator` predicate without duplication.
 *
 * Edition scope: CE
 */

/**
 * Returns true when the agent is the orchestrator role.
 * @param {Object|null} agent
 * @returns {boolean}
 */
export function isOrchestrator(agent) {
  return agent?.agent_name === 'orchestrator' || agent?.agent_display_name === 'orchestrator'
}
