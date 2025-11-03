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
  it('should generate valid Codex CLI command with --url and name last', () => {
    const command = generateCodexConfig('test-key-123', 'http://localhost:7272')

    expect(command).toContain('Codex CLI MCP Integration')
    expect(command).toContain('codex mcp add')
    expect(command).toContain('--url http://localhost:7272/mcp')
    // Ensure header present and name at the end
    expect(command).toMatch(/--header \"X-API-Key: test-key-123\".*giljo-mcp/) 
  })

  it('should include API key in header', () => {
    const command = generateCodexConfig('codex-key-456', 'https://example.com:7272')
    expect(command).toContain('X-API-Key: codex-key-456')
  })
})

describe('generateGeminiConfig - HTTP Transport', () => {
  it('should generate valid Gemini CLI command with --url and name last', () => {
    const command = generateGeminiConfig('test-key-123', 'http://localhost:7272')

    expect(command).toContain('Gemini CLI MCP Integration')
    expect(command).toContain('gemini mcp add')
    expect(command).toContain('--url http://localhost:7272/mcp')
    expect(command).toMatch(/--header \"X-API-Key: test-key-123\".*giljo-mcp/)
  })

  it('should include API key in header', () => {
    const command = generateGeminiConfig('gemini-key-789', 'https://example.com:7272')
    expect(command).toContain('X-API-Key: gemini-key-789')
  })
})
