/**
 * Shared MCP configuration generation composable (Handover 0855d)
 *
 * Extracted from AiToolConfigWizard.vue so both the standalone modal
 * and the setup wizard (SetupStep2Connect.vue) share one source of truth.
 *
 * Tool ID conventions:
 *   - Setup wizard uses: claude_code, codex_cli, gemini_cli
 *   - Legacy modal uses: claude, codex, gemini, openclaw
 *   Both are supported via normalizeToolId().
 */

/**
 * Normalize tool IDs between wizard (claude_code) and legacy (claude) formats.
 * @param {string} toolId
 * @returns {string} canonical legacy ID (claude, codex, gemini, openclaw)
 */
export function normalizeToolId(toolId) {
  const map = {
    claude_code: 'claude',
    codex_cli: 'codex',
    gemini_cli: 'gemini',
  }
  return map[toolId] || toolId
}

/**
 * Detect platform from user agent.
 * @returns {'windows'|'unix'}
 */
export function detectPlatform() {
  if (typeof navigator !== 'undefined' && /win/i.test(navigator.platform)) {
    return 'windows'
  }
  return 'unix'
}

/**
 * Build server URL from current page location.
 * @param {string} [hostname] - Override hostname (defaults to window.location.hostname)
 * @param {string} [port]     - Override port (defaults to '7272')
 * @returns {string} e.g. "https://192.168.1.5:7272"
 */
export function buildServerUrl(hostname, port) {
  const h = hostname || window.location.hostname
  const p = port || window.location.port || '7272'
  const protocol = window.location.protocol === 'https:' ? 'https' : 'http'
  return `${protocol}://${h}:${p}`
}

/**
 * @returns {boolean} true if current page is served over HTTPS
 */
export function isHttps() {
  return window.location.protocol === 'https:'
}

// ─── Config generation per tool ───────────────────────────────────

/**
 * Generate Claude Code MCP add command.
 */
export function generateClaudeConfig(serverUrl, apiKey) {
  return `claude mcp add --scope user --transport http giljo_mcp ${serverUrl}/mcp --header "Authorization: Bearer ${apiKey}"`
}

/**
 * Generate Codex CLI MCP add command.
 * Codex reads bearer token from env var at runtime.
 */
export function generateCodexConfig(serverUrl) {
  return `codex mcp add giljo_mcp --url ${serverUrl}/mcp --bearer-token-env-var GILJO_API_KEY`
}

/**
 * Generate Gemini CLI MCP add command.
 */
export function generateGeminiConfig(serverUrl, apiKey) {
  return `gemini mcp add -t http -H "Authorization: Bearer ${apiKey}" giljo_mcp ${serverUrl}/mcp`
}

/**
 * Generate OpenClaw JSON config snippet.
 * Only used by the standalone modal, NOT the setup wizard.
 */
export function generateOpenclawConfig(serverUrl, apiKey) {
  return JSON.stringify({
    'giljo_mcp': {
      transport: 'streamable-http',
      url: `${serverUrl}/mcp`,
      headers: { Authorization: `Bearer ${apiKey}` },
    },
  }, null, 2)
}

/**
 * Dispatch to the right generator.
 * Accepts both wizard IDs (claude_code) and legacy IDs (claude).
 * @param {string} toolId
 * @param {string} serverUrl
 * @param {string} apiKey
 * @returns {string}
 */
export function generateConfigForTool(toolId, serverUrl, apiKey) {
  const id = normalizeToolId(toolId)
  switch (id) {
    case 'claude':
      return generateClaudeConfig(serverUrl, apiKey)
    case 'codex':
      return generateCodexConfig(serverUrl)
    case 'gemini':
      return generateGeminiConfig(serverUrl, apiKey)
    case 'openclaw':
      return generateOpenclawConfig(serverUrl, apiKey)
    default:
      return `Use these values with your tool:\n- Base URL: ${serverUrl}\n- Header: Authorization: Bearer ${apiKey}`
  }
}

// ─── Environment variable helpers ─────────────────────────────────

/**
 * Generate Codex env var command for a given platform.
 * @param {string} apiKey
 * @param {'windows'|'unix'} platform
 * @returns {string}
 */
export function generateCodexEnvVar(apiKey, platform) {
  const key = apiKey || 'YOUR_API_KEY'
  if (platform === 'windows') {
    return `setx GILJO_API_KEY "${key}"\n$env:GILJO_API_KEY="${key}"`
  }
  return `export GILJO_API_KEY="${key}"`
}

// ─── Certificate trust commands ───────────────────────────────────

export const CERT_TRUST_WINDOWS = '$env:NODE_EXTRA_CA_CERTS = "$env:USERPROFILE\\Downloads\\rootCA.pem"; [System.Environment]::SetEnvironmentVariable(\'NODE_EXTRA_CA_CERTS\', "$env:USERPROFILE\\Downloads\\rootCA.pem", \'User\')'
export const CERT_TRUST_UNIX = 'export NODE_EXTRA_CA_CERTS="$HOME/Downloads/rootCA.pem"'

/**
 * @param {'windows'|'unix'} platform
 * @returns {string}
 */
export function getCertTrustCommand(platform) {
  return platform === 'windows' ? CERT_TRUST_WINDOWS : CERT_TRUST_UNIX
}

// ─── Tool metadata ────────────────────────────────────────────────

/**
 * Human-readable name for API key generation.
 * @param {string} toolId - Either wizard or legacy ID
 * @returns {string}
 */
export function makeKeyName(toolId) {
  const id = normalizeToolId(toolId)
  const map = {
    claude: 'Claude Code',
    codex: 'Codex CLI',
    gemini: 'Gemini',
    openclaw: 'OpenClaw',
  }
  return `${map[id] || 'AI Agent'} prompt key`
}
