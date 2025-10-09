import { describe, it, expect } from 'vitest'
import {
  generateClaudeCodeConfig,
  generateCodexConfig,
  generateGenericConfig
} from '@/utils/configTemplates'

describe('Config Template Generation', () => {
  const mockApiKey = 'gk_test_key_123'
  const mockServerUrl = 'http://localhost:7272'
  const mockPythonPath = '/path/to/venv/bin/python'

  it('generates valid Claude Code config JSON', () => {
    const config = generateClaudeCodeConfig(mockApiKey, mockServerUrl, mockPythonPath)

    expect(config).toMatch(/"mcpServers"/)
    expect(config).toMatch(/giljo-mcp/)
    expect(config).toContain(mockApiKey)
    expect(config).toContain(mockServerUrl)
    expect(config).toContain(mockPythonPath)
  })

  it('generates valid Codex config TOML', () => {
    const config = generateCodexConfig(mockApiKey)

    expect(config).toMatch(/\[tools\.claude_code\]/)
    expect(config).toContain(mockApiKey)
  })

  it('generates generic config with curl example', () => {
    const config = generateGenericConfig(mockApiKey)

    expect(config).toMatch(/curl/)
    expect(config).toContain(mockApiKey)
  })

  it('handles config generation with missing parameters', () => {
    const baseConfig1 = generateClaudeCodeConfig(mockApiKey)
    const baseConfig2 = generateCodexConfig(mockApiKey)

    expect(baseConfig1).toBeTruthy()
    expect(baseConfig2).toBeTruthy()
  })
})