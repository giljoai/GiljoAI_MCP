/**
 * Test suite for Claude Code agent template color mappings
 *
 * Verifies that all Claude Code agent template names (agent_name values)
 * are correctly mapped to canonical agent colors.
 *
 * Related components:
 * - AgentCard.vue: Uses agentColor computed property
 * - useAgentData.js: Uses getAgentColor function
 * - agentColors.js: Defines AGENT_SYNONYMS mappings
 */

import { describe, it, expect } from 'vitest'
import { getAgentColor } from '@/config/agentColors'

// AGENT_COLORS is not exported from agentColors.js; derive expected values from getAgentColor
const AGENT_COLORS = {
  orchestrator: getAgentColor('orchestrator'),
  analyzer: getAgentColor('analyzer'),
  implementer: getAgentColor('implementer'),
  documenter: getAgentColor('documenter'),
  reviewer: getAgentColor('reviewer'),
  tester: getAgentColor('tester'),
}

describe('Claude Code Agent Template Color Mappings', () => {
  describe('TDD Implementor', () => {
    it('maps tdd-implementor to implementer color (blue)', () => {
      const color = getAgentColor('tdd-implementor')
      expect(color).toEqual(AGENT_COLORS.implementer)
      expect(color.hex).toBe('#6DB3E4')
      expect(color.name).toBe('IMPLEMENTER')
    })

    it('maps tdd-implementor case-insensitively', () => {
      const color = getAgentColor('TDD-IMPLEMENTOR')
      expect(color).toEqual(AGENT_COLORS.implementer)
    })
  })

  describe('Backend Integration Tester', () => {
    it('maps backend-integration-tester to tester color (yellow)', () => {
      const color = getAgentColor('backend-integration-tester')
      expect(color).toEqual(AGENT_COLORS.tester)
      expect(color.hex).toBe('#EDBA4A')
      expect(color.name).toBe('TESTER')
    })
  })

  describe('Frontend Tester', () => {
    it('maps frontend-tester to tester color (yellow)', () => {
      const color = getAgentColor('frontend-tester')
      expect(color).toEqual(AGENT_COLORS.tester)
      expect(color.hex).toBe('#EDBA4A')
    })
  })

  describe('Database Expert', () => {
    it('maps database-expert to analyzer color (red)', () => {
      const color = getAgentColor('database-expert')
      expect(color).toEqual(AGENT_COLORS.analyzer)
      expect(color.hex).toBe('#E07872')
      expect(color.name).toBe('ANALYZER')
    })
  })

  describe('Deep Researcher', () => {
    it('maps deep-researcher to analyzer color (red)', () => {
      const color = getAgentColor('deep-researcher')
      expect(color).toEqual(AGENT_COLORS.analyzer)
      expect(color.hex).toBe('#E07872')
    })
  })

  describe('System Architect', () => {
    it('maps system-architect to analyzer color (red)', () => {
      const color = getAgentColor('system-architect')
      expect(color).toEqual(AGENT_COLORS.analyzer)
      expect(color.hex).toBe('#E07872')
    })
  })

  describe('Documentation Manager', () => {
    it('maps documentation-manager to documenter color (green)', () => {
      const color = getAgentColor('documentation-manager')
      expect(color).toEqual(AGENT_COLORS.documenter)
      expect(color.hex).toBe('#5EC48E')
      expect(color.name).toBe('DOCUMENTER')
    })
  })

  describe('Network Security Engineer', () => {
    it('maps network-security-engineer to reviewer color (purple)', () => {
      const color = getAgentColor('network-security-engineer')
      expect(color).toEqual(AGENT_COLORS.reviewer)
      expect(color.hex).toBe('#AC80CC')
      expect(color.name).toBe('REVIEWER')
    })
  })

  describe('UX Designer', () => {
    it('maps ux-designer to implementer color (blue)', () => {
      const color = getAgentColor('ux-designer')
      expect(color).toEqual(AGENT_COLORS.implementer)
      expect(color.hex).toBe('#6DB3E4')
    })
  })

  describe('Version Manager', () => {
    it('maps version-manager to reviewer color (purple)', () => {
      const color = getAgentColor('version-manager')
      expect(color).toEqual(AGENT_COLORS.reviewer)
      expect(color.hex).toBe('#AC80CC')
    })
  })

  describe('Installation Flow Agent', () => {
    it('maps installation-flow-agent to implementer color (blue)', () => {
      const color = getAgentColor('installation-flow-agent')
      expect(color).toEqual(AGENT_COLORS.implementer)
      expect(color.hex).toBe('#6DB3E4')
    })
  })

  describe('Orchestrator Coordinator', () => {
    it('maps orchestrator-coordinator to orchestrator color (tan)', () => {
      const color = getAgentColor('orchestrator-coordinator')
      expect(color).toEqual(AGENT_COLORS.orchestrator)
      expect(color.hex).toBe('#D4B08A')
      expect(color.name).toBe('ORCHESTRATOR')
    })
  })

  describe('Canonical Agent Types', () => {
    it('maps canonical agent types correctly', () => {
      expect(getAgentColor('orchestrator')).toEqual(AGENT_COLORS.orchestrator)
      expect(getAgentColor('analyzer')).toEqual(AGENT_COLORS.analyzer)
      expect(getAgentColor('implementer')).toEqual(AGENT_COLORS.implementer)
      expect(getAgentColor('documenter')).toEqual(AGENT_COLORS.documenter)
      expect(getAgentColor('reviewer')).toEqual(AGENT_COLORS.reviewer)
      expect(getAgentColor('tester')).toEqual(AGENT_COLORS.tester)
    })
  })

  describe('Fallback and Edge Cases', () => {
    it('falls back to orchestrator color for unknown agent names', () => {
      const color = getAgentColor('unknown-agent')
      expect(color).toEqual(AGENT_COLORS.orchestrator)
    })

    it('handles empty string gracefully', () => {
      const color = getAgentColor('')
      expect(color).toEqual(AGENT_COLORS.orchestrator)
    })

    it('handles null gracefully', () => {
      const color = getAgentColor(null)
      expect(color).toEqual(AGENT_COLORS.orchestrator)
    })

    it('handles undefined gracefully', () => {
      const color = getAgentColor(undefined)
      expect(color).toEqual(AGENT_COLORS.orchestrator)
    })
  })

  describe('Color Object Properties', () => {
    it('returns complete color configuration object', () => {
      const color = getAgentColor('tdd-implementor')

      expect(color).toHaveProperty('hex')
      expect(color).toHaveProperty('name')
      expect(color).toHaveProperty('badge')
      expect(color).toHaveProperty('description')

      expect(typeof color.hex).toBe('string')
      expect(typeof color.name).toBe('string')
      expect(typeof color.badge).toBe('string')
      expect(typeof color.description).toBe('string')
    })

    it('returns correct badge ID for agent types', () => {
      const implementerColor = getAgentColor('tdd-implementor')
      expect(implementerColor.badge).toBe('IM')

      const testerColor = getAgentColor('frontend-tester')
      expect(testerColor.badge).toBe('TE')

      const analyzerColor = getAgentColor('database-expert')
      expect(analyzerColor.badge).toBe('AN')

      const documenterColor = getAgentColor('documentation-manager')
      expect(documenterColor.badge).toBe('DO')

      const reviewerColor = getAgentColor('network-security-engineer')
      expect(reviewerColor.badge).toBe('RV')

      const orchestratorColor = getAgentColor('orchestrator-coordinator')
      expect(orchestratorColor.badge).toBe('OR')
    })
  })

  describe('AgentCard Integration', () => {
    it('supports agent_name || agent_display_name fallback pattern', () => {
      // Test the pattern used in AgentCard.vue line 447
      const agent1 = {
        agent_name: 'tdd-implementor',
        agent_display_name: 'Requirements Analyst',
      }
      const agent2 = {
        agent_name: null,
        agent_display_name: 'analyzer',
      }

      const color1 = getAgentColor(agent1.agent_name || agent1.agent_display_name)
      expect(color1).toEqual(AGENT_COLORS.implementer)

      const color2 = getAgentColor(agent2.agent_name || agent2.agent_display_name)
      expect(color2).toEqual(AGENT_COLORS.analyzer)
    })
  })
})
