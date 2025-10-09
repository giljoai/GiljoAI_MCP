/**
 * Configuration Template Generation
 *
 * Generates tool-specific configuration snippets for API key setup.
 * Supports Claude Code, Codex CLI, and generic integrations.
 */

/**
 * Generate Claude Code MCP server configuration
 * @param {string} apiKey - The API key to embed
 * @param {string} serverUrl - GiljoAI MCP server URL (default: http://localhost:7272)
 * @param {string} pythonPath - Path to Python executable
 * @returns {string} JSON configuration snippet for .claude.json
 */
export function generateClaudeCodeConfig(apiKey, serverUrl = 'http://localhost:7272', pythonPath) {
  // Use default Python path if not provided
  const defaultPythonPath = pythonPath || 'python'

  const config = {
    mcpServers: {
      'giljo-mcp': {
        command: defaultPythonPath,
        args: ['-m', 'giljo_mcp'],
        env: {
          GILJO_MCP_HOME: 'F:/GiljoAI_MCP',
          GILJO_SERVER_URL: serverUrl,
          GILJO_API_KEY: apiKey,
        },
      },
    },
  }

  return JSON.stringify(config, null, 2)
}

/**
 * Generate Codex CLI configuration
 * @param {string} apiKey - The API key to embed
 * @returns {string} TOML configuration snippet for config.toml
 */
export function generateCodexConfig(apiKey) {
  return `[tools.claude_code]
api_key = "${apiKey}"
server_url = "http://localhost:7272"

# Codex CLI integration (coming soon)
# This configuration will be used when Codex CLI support is added
`
}

/**
 * Generate generic API integration example
 * @param {string} apiKey - The API key to embed
 * @param {string} serverUrl - GiljoAI MCP server URL (default: http://localhost:7272)
 * @returns {string} Generic curl example for API testing
 */
export function generateGenericConfig(apiKey, serverUrl = 'http://localhost:7272') {
  return `# Generic API Integration

Use this API key in your HTTP requests:

curl -X GET "${serverUrl}/api/v1/projects/" \\
  -H "X-API-Key: ${apiKey}" \\
  -H "Content-Type: application/json"

Or use it in your application code:

import requests

headers = {
    "X-API-Key": "${apiKey}",
    "Content-Type": "application/json"
}

response = requests.get("${serverUrl}/api/v1/projects/", headers=headers)
print(response.json())
`
}
