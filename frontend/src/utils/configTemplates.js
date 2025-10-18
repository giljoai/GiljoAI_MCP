/**
 * Configuration Template Generation
 *
 * Generates tool-specific configuration snippets for API key setup.
 * Supports Claude Code, Codex CLI, and generic integrations.
 */

/**
 * Generate Claude Code MCP server configuration using HTTP transport
 * @param {string} apiKey - The API key to embed
 * @param {string} serverUrl - GiljoAI MCP server URL (default: current host:7272)
 * @returns {string} Command-line instruction for HTTP transport setup
 */
export function generateClaudeCodeConfig(apiKey, serverUrl = null) {
  // v3.0 Unified: Default to current host if no URL provided
  const defaultServerUrl = serverUrl || `${window.location.protocol}//${window.location.hostname}:7272`

  // Generate HTTP transport command for Claude Code
  // Uses zero-dependency HTTP transport - no Python or local packages required
  const command = `claude mcp add --transport http giljo-mcp ${defaultServerUrl}/mcp --header "X-API-Key: ${apiKey}"`

  return command
}

/**
 * Generate Codex CLI configuration using HTTP transport
 * @param {string} apiKey - The API key to embed
 * @param {string} serverUrl - GiljoAI MCP server URL (default: current host:7272)
 * @returns {string} Command-line instruction for HTTP transport setup (placeholder)
 */
export function generateCodexConfig(apiKey, serverUrl = null) {
  // v3.0 Unified: Default to current host if no URL provided
  const defaultServerUrl = serverUrl || `${window.location.protocol}//${window.location.hostname}:7272`

  // Placeholder command - exact syntax pending Codex CLI documentation
  // Expected format follows Claude Code pattern when available
  const command = `# Codex CLI MCP Integration (Coming Soon)
# Expected command format (pending official documentation):
codex mcp add --transport http giljo-mcp ${defaultServerUrl}/mcp --header "X-API-Key: ${apiKey}"

# Note: This is a placeholder. Once Codex CLI MCP support is available,
# the exact command syntax will be updated based on official documentation.`

  return command
}

/**
 * Generate Gemini CLI configuration using HTTP transport
 * @param {string} apiKey - The API key to embed
 * @param {string} serverUrl - GiljoAI MCP server URL (default: current host:7272)
 * @returns {string} Command-line instruction for HTTP transport setup (placeholder)
 */
export function generateGeminiConfig(apiKey, serverUrl = null) {
  // v3.0 Unified: Default to current host if no URL provided
  const defaultServerUrl = serverUrl || `${window.location.protocol}//${window.location.hostname}:7272`

  // Placeholder command - exact syntax pending Gemini CLI documentation
  // Expected format follows Claude Code pattern when available
  const command = `# Gemini CLI MCP Integration (Coming Soon)
# Expected command format (pending official documentation):
gemini mcp add --transport http giljo-mcp ${defaultServerUrl}/mcp --header "X-API-Key: ${apiKey}"

# Note: This is a placeholder. Once Gemini CLI MCP support is available,
# the exact command syntax will be updated based on official documentation.`

  return command
}

/**
 * Generate generic API integration example
 * @param {string} apiKey - The API key to embed
 * @param {string} serverUrl - GiljoAI MCP server URL (default: current host:7272)
 * @returns {string} Generic curl example for API testing
 */
export function generateGenericConfig(apiKey, serverUrl = null) {
  // v3.0 Unified: Default to current host if no URL provided
  const defaultServerUrl = serverUrl || `${window.location.protocol}//${window.location.hostname}:7272`
  return `# Generic API Integration

Use this API key in your HTTP requests:

curl -X GET "${defaultServerUrl}/api/v1/projects/" \\
  -H "X-API-Key: ${apiKey}" \\
  -H "Content-Type: application/json"

Or use it in your application code:

import requests

headers = {
    "X-API-Key": "${apiKey}",
    "Content-Type": "application/json"
}

response = requests.get("${defaultServerUrl}/api/v1/projects/", headers=headers)
print(response.json())
`
}
