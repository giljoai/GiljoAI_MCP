import { describe, it, expect } from 'vitest'
import {
  generateClaudeCodeConfig,
  generateCodexConfig,
  generateGenericConfig
} from '@/utils/configTemplates'

describe('generateClaudeCodeConfig', () => {
  it('should generate valid JSON config', () => {
    const config = generateClaudeCodeConfig('test-key-123', 'http://localhost:7272')
    const parsed = JSON.parse(config)

    expect(parsed.mcpServers).toBeDefined()
    expect(parsed.mcpServers['giljo-mcp']).toBeDefined()
    expect(parsed.mcpServers['giljo-mcp'].command).toBe('python')
    expect(parsed.mcpServers['giljo-mcp'].env.GILJO_API_KEY).toBe('test-key-123')
    expect(parsed.mcpServers['giljo-mcp'].env.GILJO_SERVER_URL).toBe('http://localhost:7272')
  })

  it('should NOT include GILJO_MCP_HOME environment variable', () => {
    const config = generateClaudeCodeConfig('test-key-123', 'http://localhost:7272')
    const parsed = JSON.parse(config)

    // CRITICAL TEST: This will FAIL until we remove the hardcoded path
    expect(parsed.mcpServers['giljo-mcp'].env.GILJO_MCP_HOME).toBeUndefined()
  })

  it('should work cross-platform - no hardcoded Windows paths', () => {
    const config = generateClaudeCodeConfig('test-key-123', 'http://localhost:7272')

    // CRITICAL TEST: Will FAIL if hardcoded F:/GiljoAI_MCP exists
    expect(config).not.toContain('F:/')
  })

  it('should use simple python command', () => {
    const config = generateClaudeCodeConfig('test-key-123', 'http://localhost:7272')
    const parsed = JSON.parse(config)

    expect(parsed.mcpServers['giljo-mcp'].command).toBe('python')
  })
})
