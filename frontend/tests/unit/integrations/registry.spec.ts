import { describe, it, expect } from 'vitest'
import {
  INTEGRATIONS,
  getIntegrationById,
  getIntegrationsByKind,
  type Integration,
  type IntegrationKind
} from '@/integrations/registry'

describe('Integration Registry', () => {
  describe('INTEGRATIONS array', () => {
    it('exports INTEGRATIONS array', () => {
      expect(INTEGRATIONS).toBeDefined()
      expect(Array.isArray(INTEGRATIONS)).toBe(true)
    })

    it('contains at least 5 integrations', () => {
      expect(INTEGRATIONS.length).toBeGreaterThanOrEqual(5)
    })

    it('has no duplicate IDs', () => {
      const ids = INTEGRATIONS.map(i => i.id)
      const uniqueIds = new Set(ids)
      expect(ids.length).toBe(uniqueIds.size)
    })
  })

  describe('Integration structure', () => {
    it('each integration has required fields', () => {
      INTEGRATIONS.forEach(integration => {
        expect(integration.id).toBeDefined()
        expect(typeof integration.id).toBe('string')
        expect(integration.id.length).toBeGreaterThan(0)

        expect(integration.name).toBeDefined()
        expect(typeof integration.name).toBe('string')
        expect(integration.name.length).toBeGreaterThan(0)

        expect(integration.kind).toBeDefined()
        expect(typeof integration.kind).toBe('string')

        expect(integration.userConfigComponent).toBeDefined()
        expect(typeof integration.userConfigComponent).toBe('string')
        expect(integration.userConfigComponent.length).toBeGreaterThan(0)
      })
    })

    it('each kind is a valid enum value', () => {
      const validKinds: IntegrationKind[] = ['tooling', 'ai_tool', 'export', 'scm']
      INTEGRATIONS.forEach(integration => {
        expect(validKinds).toContain(integration.kind)
      })
    })

    it('optional fields have correct types when present', () => {
      INTEGRATIONS.forEach(integration => {
        if (integration.description !== undefined) {
          expect(typeof integration.description).toBe('string')
        }
        if (integration.icon !== undefined) {
          expect(typeof integration.icon).toBe('string')
        }
        if (integration.adminInfoComponent !== undefined) {
          expect(typeof integration.adminInfoComponent).toBe('string')
        }
      })
    })
  })

  describe('Required integrations', () => {
    it('includes MCP integration', () => {
      const mcp = INTEGRATIONS.find(i => i.id === 'mcp')
      expect(mcp).toBeDefined()
      expect(mcp?.name).toBe('GiljoAI MCP Integration')
      expect(mcp?.kind).toBe('tooling')
      expect(mcp?.userConfigComponent).toBe('AiToolConfigWizard')
    })

    it('includes Slash Commands integration', () => {
      const slashCommands = INTEGRATIONS.find(i => i.id === 'slash_commands')
      expect(slashCommands).toBeDefined()
      expect(slashCommands?.name).toBe('Slash Commands')
      expect(slashCommands?.kind).toBe('tooling')
      expect(slashCommands?.userConfigComponent).toBe('SlashCommandSetup')
    })

    it('includes Claude Code export integration', () => {
      const claudeCode = INTEGRATIONS.find(i => i.id === 'claude_code')
      expect(claudeCode).toBeDefined()
      expect(claudeCode?.name).toBe('Claude Code Export')
      expect(claudeCode?.kind).toBe('export')
      expect(claudeCode?.userConfigComponent).toBe('ClaudeCodeExport')
    })

    it('includes Serena integration', () => {
      const serena = INTEGRATIONS.find(i => i.id === 'serena')
      expect(serena).toBeDefined()
      expect(serena?.name).toBe('Serena MCP')
      expect(serena?.kind).toBe('ai_tool')
      expect(serena?.userConfigComponent).toBe('SerenaIntegrationCard')
    })

    it('includes GitHub/Git integration', () => {
      const github = INTEGRATIONS.find(i => i.id === 'github')
      expect(github).toBeDefined()
      expect(github?.name).toBe('Git + 360 Memory')
      expect(github?.kind).toBe('scm')
      expect(github?.userConfigComponent).toBe('GitIntegrationCard')
    })
  })

  describe('getIntegrationById', () => {
    it('returns integration when found', () => {
      const mcp = getIntegrationById('mcp')
      expect(mcp).toBeDefined()
      expect(mcp?.id).toBe('mcp')
    })

    it('returns undefined for non-existent ID', () => {
      const result = getIntegrationById('non_existent')
      expect(result).toBeUndefined()
    })

    it('returns undefined for empty string', () => {
      const result = getIntegrationById('')
      expect(result).toBeUndefined()
    })

    it('is case-sensitive', () => {
      const result = getIntegrationById('MCP')
      expect(result).toBeUndefined()
    })
  })

  describe('getIntegrationsByKind', () => {
    it('returns all tooling integrations', () => {
      const tooling = getIntegrationsByKind('tooling')
      expect(tooling.length).toBeGreaterThanOrEqual(2)
      tooling.forEach(integration => {
        expect(integration.kind).toBe('tooling')
      })
    })

    it('returns all ai_tool integrations', () => {
      const aiTools = getIntegrationsByKind('ai_tool')
      expect(aiTools.length).toBeGreaterThanOrEqual(1)
      aiTools.forEach(integration => {
        expect(integration.kind).toBe('ai_tool')
      })
    })

    it('returns all export integrations', () => {
      const exports = getIntegrationsByKind('export')
      expect(exports.length).toBeGreaterThanOrEqual(1)
      exports.forEach(integration => {
        expect(integration.kind).toBe('export')
      })
    })

    it('returns all scm integrations', () => {
      const scm = getIntegrationsByKind('scm')
      expect(scm.length).toBeGreaterThanOrEqual(1)
      scm.forEach(integration => {
        expect(integration.kind).toBe('scm')
      })
    })

    it('returns empty array for non-existent kind', () => {
      const result = getIntegrationsByKind('unknown' as IntegrationKind)
      expect(result).toEqual([])
    })

    it('returns a new array (not a reference to INTEGRATIONS)', () => {
      const tooling = getIntegrationsByKind('tooling')
      expect(tooling).not.toBe(INTEGRATIONS)
    })
  })

  describe('Integration metadata', () => {
    it('MCP integration has description', () => {
      const mcp = getIntegrationById('mcp')
      expect(mcp?.description).toBeDefined()
      expect(mcp?.description?.length).toBeGreaterThan(0)
    })

    it('Serena integration has description', () => {
      const serena = getIntegrationById('serena')
      expect(serena?.description).toBeDefined()
      expect(serena?.description?.length).toBeGreaterThan(0)
    })

    it('GitHub integration has description', () => {
      const github = getIntegrationById('github')
      expect(github?.description).toBeDefined()
      expect(github?.description?.length).toBeGreaterThan(0)
    })

    it('MCP integration has icon', () => {
      const mcp = getIntegrationById('mcp')
      expect(mcp?.icon).toBeDefined()
    })
  })

  describe('Type safety', () => {
    it('Integration type is correctly defined', () => {
      const integration: Integration = INTEGRATIONS[0]
      expect(integration).toBeDefined()
    })

    it('IntegrationKind type restricts valid values', () => {
      const kind: IntegrationKind = 'tooling'
      expect(['tooling', 'ai_tool', 'export', 'scm']).toContain(kind)
    })
  })
})
