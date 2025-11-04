import { describe, it, expect } from 'vitest'
import {
  generateClaudeCodeConfig,
  generateCodexConfig,
  generateGeminiConfig,
  generateGenericConfig
} from '@/utils/configTemplates'

describe('generateClaudeCodeConfig - HTTP Transport', () => {
  it('should generate valid HTTP transport command', () => {
    const command = generateClaudeCodeConfig('test-key-123', 'http://localhost:7272')

    // Verify command structure
    expect(command).toContain('claude mcp add')
    expect(command).toContain('--transport http')
    expect(command).toContain('giljo-mcp')
    expect(command).toContain('http://localhost:7272/mcp')
    expect(command).toContain('--header "X-API-Key: test-key-123"')
  })

  it('should include API key in header', () => {
    const command = generateClaudeCodeConfig('gk_SecretKey123', 'https://example.com:7272')

    expect(command).toContain('X-API-Key: gk_SecretKey123')
  })

  it('should use correct MCP endpoint path', () => {
    const command = generateClaudeCodeConfig('test-key', 'http://server:7272')

    // Verify endpoint is /mcp not /api/mcp
    expect(command).toContain('http://server:7272/mcp')
    expect(command).not.toContain('/api/mcp')
  })

  it('should be zero-dependency - no Python or uvx', () => {
    const command = generateClaudeCodeConfig('test-key-123', 'http://localhost:7272')

    // CRITICAL: No Python, no uvx, no local packages
    expect(command).not.toContain('python')
    expect(command).not.toContain('uvx')
    expect(command).not.toContain('GILJO_MCP_HOME')
  })

  it('should work cross-platform - no hardcoded paths', () => {
    const command = generateClaudeCodeConfig('test-key-123', 'http://localhost:7272')

    // CRITICAL: No hardcoded Windows paths
    expect(command).not.toContain('F:/')
    expect(command).not.toContain('C:/')
    expect(command).not.toContain('\\\\')
  })
})

describe('generateCodexConfig - HTTP Transport', () => {
  it('should generate valid Codex CLI command with bearer env var and --url', () => {
    const command = generateCodexConfig('test-key-123', 'http://localhost:7272')

    expect(command).toContain('Codex CLI MCP Integration')
    expect(command).toContain('export GILJO_API_KEY="test-key-123"')
    expect(command).toContain('codex mcp add')
    expect(command).toContain('--url http://localhost:7272/mcp')
    expect(command).toContain('--bearer-token-env-var GILJO_API_KEY')
  })
})

describe('generateGeminiConfig - HTTP Transport', () => {
  it('should generate valid Gemini CLI command with -t http, header, name then URL', () => {
    const command = generateGeminiConfig('test-key-123', 'http://localhost:7272')

    expect(command).toContain('Gemini CLI MCP Integration')
    expect(command).toContain('gemini mcp add')
    expect(command).toContain('-t http')
    expect(command).toContain('-H "X-API-Key: test-key-123"')
    expect(command).toMatch(/gemini mcp add.*giljo-mcp http:\/\/localhost:7272\/mcp/)
  })
})
