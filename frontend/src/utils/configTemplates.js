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
  const defaultServerUrl =
    serverUrl || `${window.location.protocol}//${window.location.hostname}:7272`

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
  const defaultServerUrl =
    serverUrl || `${window.location.protocol}//${window.location.hostname}:7272`

  // Native MCP integration via command-line
  const command = `# Codex CLI MCP Integration (Bearer token)
export GILJO_API_KEY="${apiKey}"
codex mcp add --url ${defaultServerUrl}/mcp --bearer-token-env-var GILJO_API_KEY giljo-mcp

# Verify installation:
# codex mcp list`

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
  const defaultServerUrl =
    serverUrl || `${window.location.protocol}//${window.location.hostname}:7272`

  // Native MCP integration via command-line
  const command = `# Gemini CLI MCP Integration (HTTP + header)
gemini mcp add -t http -H "X-API-Key: ${apiKey}" giljo-mcp ${defaultServerUrl}/mcp

# Verify installation:
# gemini mcp list`

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
  const defaultServerUrl =
    serverUrl || `${window.location.protocol}//${window.location.hostname}:7272`
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
