/**
 * Configuration Template Generation
 *
 * Generates tool-specific configuration snippets for API key setup.
 * Supports Claude Code, Codex CLI, and generic integrations.
 */

/**
 * Generate Claude Code MCP server configuration
 * @param {string} apiKey - The API key to embed
 * @param {string} serverUrl - GiljoAI MCP server URL (default: current host:7272)
 * @param {string} pythonPath - Path to Python executable
 * @returns {string} JSON configuration snippet for .claude.json
 */
export function generateClaudeCodeConfig(apiKey, serverUrl = null) {
  // v3.0 Unified: Default to current host if no URL provided
  const defaultServerUrl = serverUrl || `${window.location.protocol}//${window.location.hostname}:7272`

  // Return the entry to add under "mcpServers"
  const entry = {
    'giljo-mcp': {
      command: 'uvx',
      args: ['giljo-mcp'],
      env: {
        GILJO_API_KEY: apiKey,
        GILJO_SERVER_URL: defaultServerUrl,
      },
    },
  }

  // Pretty-print just the giljo-mcp entry block for clarity
  return JSON.stringify(entry['giljo-mcp'], null, 2)
}

/**
 * Generate Codex CLI configuration
 * @param {string} apiKey - The API key to embed
 * @param {string} serverUrl - GiljoAI MCP server URL (default: current host:7272)
 * @returns {string} TOML configuration snippet for config.toml
 */
export function generateCodexConfig(apiKey, serverUrl = null) {
  // v3.0 Unified: Default to current host if no URL provided
  const defaultServerUrl = serverUrl || `${window.location.protocol}//${window.location.hostname}:7272`

  return `[tools.claude_code]
api_key = "${apiKey}"
server_url = "${defaultServerUrl}"

# Codex CLI integration (coming soon)
# This configuration will be used when Codex CLI support is added
`
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
