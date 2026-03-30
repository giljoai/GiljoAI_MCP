import { describe, it, expect } from 'vitest'
import {
  normalizeToolId,
  detectPlatform,
  buildServerUrl,
  generateClaudeConfig,
  generateCodexConfig,
  generateGeminiConfig,
  generateOpenclawConfig,
  generateConfigForTool,
  generateCodexEnvVar,
  getCertTrustCommand,
  makeKeyName,
} from '@/composables/useMcpConfig'

describe('useMcpConfig', () => {
  // ─── normalizeToolId ───────────────────────────────────────────────

  describe('normalizeToolId', () => {
    it('maps claude_code to claude', () => {
      expect(normalizeToolId('claude_code')).toBe('claude')
    })

    it('maps codex_cli to codex', () => {
      expect(normalizeToolId('codex_cli')).toBe('codex')
    })

    it('maps gemini_cli to gemini', () => {
      expect(normalizeToolId('gemini_cli')).toBe('gemini')
    })

    it('passes through unknown IDs unchanged', () => {
      expect(normalizeToolId('openclaw')).toBe('openclaw')
      expect(normalizeToolId('some_other_tool')).toBe('some_other_tool')
    })

    it('passes through legacy IDs unchanged', () => {
      expect(normalizeToolId('claude')).toBe('claude')
      expect(normalizeToolId('codex')).toBe('codex')
      expect(normalizeToolId('gemini')).toBe('gemini')
    })
  })

  // ─── detectPlatform ────────────────────────────────────────────────

  describe('detectPlatform', () => {
    it('returns windows when navigator.platform contains Win', () => {
      Object.defineProperty(global, 'navigator', {
        value: { platform: 'Win32' },
        writable: true,
        configurable: true,
      })
      expect(detectPlatform()).toBe('windows')
    })

    it('returns unix for non-Windows platforms', () => {
      Object.defineProperty(global, 'navigator', {
        value: { platform: 'Linux x86_64' },
        writable: true,
        configurable: true,
      })
      expect(detectPlatform()).toBe('unix')
    })

    it('returns unix for MacIntel platform', () => {
      Object.defineProperty(global, 'navigator', {
        value: { platform: 'MacIntel' },
        writable: true,
        configurable: true,
      })
      expect(detectPlatform()).toBe('unix')
    })
  })

  // ─── buildServerUrl ────────────────────────────────────────────────

  describe('buildServerUrl', () => {
    it('builds URL with protocol from window.location', () => {
      // jsdom defaults to http:
      expect(buildServerUrl('myhost.local', '8372')).toBe(
        'http://myhost.local:8372',
      )
    })

    it('defaults to hostname and port 7272', () => {
      const result = buildServerUrl()
      expect(result).toContain(':7272')
    })
  })

  // ─── generateClaudeConfig ──────────────────────────────────────────

  describe('generateClaudeConfig', () => {
    it('returns the correct claude mcp add command', () => {
      const result = generateClaudeConfig('https://localhost:8372', 'giljo_abc123')
      expect(result).toBe(
        'claude mcp add --transport http giljo_mcp https://localhost:8372/mcp --header "Authorization: Bearer giljo_abc123"',
      )
    })
  })

  // ─── generateCodexConfig ───────────────────────────────────────────

  describe('generateCodexConfig', () => {
    it('returns the correct codex mcp add command', () => {
      const result = generateCodexConfig('https://localhost:8372')
      expect(result).toBe(
        'codex mcp add giljo_mcp --url https://localhost:8372/mcp --bearer-token-env-var GILJO_API_KEY',
      )
    })
  })

  // ─── generateGeminiConfig ──────────────────────────────────────────

  describe('generateGeminiConfig', () => {
    it('returns the correct gemini mcp add command', () => {
      const result = generateGeminiConfig('https://localhost:8372', 'giljo_xyz789')
      expect(result).toBe(
        'gemini mcp add -t http -H "Authorization: Bearer giljo_xyz789" giljo_mcp https://localhost:8372/mcp',
      )
    })
  })

  // ─── generateOpenclawConfig ────────────────────────────────────────

  describe('generateOpenclawConfig', () => {
    it('returns valid JSON with transport, url, and headers', () => {
      const result = generateOpenclawConfig('https://localhost:8372', 'giljo_key456')
      const parsed = JSON.parse(result)
      const server = parsed['giljo_mcp']
      expect(server).toBeDefined()
      expect(server).toHaveProperty('transport')
      expect(server).toHaveProperty('url', 'https://localhost:8372/mcp')
      expect(server).toHaveProperty('headers')
      expect(server.headers).toHaveProperty('Authorization', 'Bearer giljo_key456')
    })
  })

  // ─── generateConfigForTool ─────────────────────────────────────────

  describe('generateConfigForTool', () => {
    const serverUrl = 'https://localhost:8372'
    const apiKey = 'giljo_test'

    it('dispatches to claude generator for wizard ID claude_code', () => {
      expect(generateConfigForTool('claude_code', serverUrl, apiKey)).toContain('claude mcp add')
    })

    it('dispatches to claude generator for legacy ID claude', () => {
      expect(generateConfigForTool('claude', serverUrl, apiKey)).toContain('claude mcp add')
    })

    it('dispatches to codex generator for wizard ID codex_cli', () => {
      expect(generateConfigForTool('codex_cli', serverUrl, apiKey)).toContain('codex mcp add')
    })

    it('dispatches to codex generator for legacy ID codex', () => {
      expect(generateConfigForTool('codex', serverUrl, apiKey)).toContain('codex mcp add')
    })

    it('dispatches to gemini generator for wizard ID gemini_cli', () => {
      expect(generateConfigForTool('gemini_cli', serverUrl, apiKey)).toContain('gemini mcp add')
    })

    it('dispatches to gemini generator for legacy ID gemini', () => {
      expect(generateConfigForTool('gemini', serverUrl, apiKey)).toContain('gemini mcp add')
    })

    it('dispatches to openclaw generator for openclaw', () => {
      const result = generateConfigForTool('openclaw', serverUrl, apiKey)
      const parsed = JSON.parse(result)
      expect(parsed['giljo_mcp']).toHaveProperty('url', `${serverUrl}/mcp`)
    })
  })

  // ─── generateCodexEnvVar ───────────────────────────────────────────

  describe('generateCodexEnvVar', () => {
    it('returns Windows setx and $env commands for windows platform', () => {
      const result = generateCodexEnvVar('giljo_mykey', 'windows')
      expect(result).toContain('setx')
      expect(result).toContain('$env')
    })

    it('returns export command for unix platform', () => {
      const result = generateCodexEnvVar('giljo_mykey', 'unix')
      expect(result).toContain('export')
    })
  })

  // ─── getCertTrustCommand ───────────────────────────────────────────

  describe('getCertTrustCommand', () => {
    it('returns Windows cert trust command for windows platform', () => {
      const result = getCertTrustCommand('windows')
      expect(result.length).toBeGreaterThan(0)
    })

    it('returns Unix cert trust command for unix platform', () => {
      const result = getCertTrustCommand('unix')
      expect(result.length).toBeGreaterThan(0)
    })

    it('returns different commands for windows vs unix', () => {
      expect(getCertTrustCommand('windows')).not.toBe(getCertTrustCommand('unix'))
    })
  })

  // ─── makeKeyName ──────────────────────────────────────────────────

  describe('makeKeyName', () => {
    it('returns human-readable key name for claude_code', () => {
      expect(makeKeyName('claude_code')).toMatch(/prompt key/i)
    })

    it('returns human-readable key name for codex_cli', () => {
      expect(makeKeyName('codex_cli')).toMatch(/prompt key/i)
    })

    it('returns human-readable key name for gemini_cli', () => {
      expect(makeKeyName('gemini_cli')).toMatch(/prompt key/i)
    })

    it('includes a tool-specific portion in the name', () => {
      expect(makeKeyName('claude_code')).not.toBe(makeKeyName('codex_cli'))
    })
  })
})
