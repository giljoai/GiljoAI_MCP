/**
 * Test: getAgentColor() behavior pin (FE-9129)
 *
 * Pins synonym resolution, separator normalization, segment matching, and
 * the orchestrator fallback BEFORE agentColors.js gains new exports —
 * proves the codegen work below does not change any of this.
 */
import { describe, it, expect } from 'vitest'
import { getAgentColor } from '@/config/agentColors.js'

describe('getAgentColor', () => {
  it('resolves the implementor legacy alias to implementer', () => {
    expect(getAgentColor('implementor').hex).toBe('#6DB3E4')
  })

  it('resolves researcher to analyzer (JS-side synonym, not documenter)', () => {
    expect(getAgentColor('researcher').hex).toBe('#E07872')
  })

  it('normalizes separators and segment-matches a specialized template name', () => {
    expect(getAgentColor('Implementer Backend').hex).toBe('#6DB3E4')
  })

  it('falls back to orchestrator for unknown input', () => {
    expect(getAgentColor('totally-unknown-agent')).toEqual(getAgentColor('orchestrator'))
  })

  it('returns an object with exactly hex, name, badge, description', () => {
    const color = getAgentColor('tester')
    expect(Object.keys(color).sort()).toEqual(['badge', 'description', 'hex', 'name'])
  })
})
