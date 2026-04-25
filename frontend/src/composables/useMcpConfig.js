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
 * Build the server URL that AI coding tools will connect to.
 *
 * Preferred usage (INF-5012): pass `backendConfig` from GET /api/v1/config/frontend
 * so we honor reverse-proxy deployments (Cloudflare Tunnel, nginx) where the
 * public URL has no explicit port.
 *
 * Heuristic:
 *  1. If `backendConfig` is provided and `window.location.hostname === backendConfig.host`,
 *     the browser is already on the correct public host — return `window.location.origin`.
 *     This produces the right scheme + host + (omitted) port for proxied deployments.
 *  2. If `backendConfig` is provided but browser is on a different host (out-of-band
 *     config rendering), compose `protocol://host[:port]`, omitting the port when it is
 *     the implicit default for the protocol (443 for https, 80 for http).
 *  3. Fallback (no backendConfig): legacy behavior — window.location.hostname +
 *     (window.location.port || '7272'). Kept for backward compat with callers that
 *     do not yet pass config.
 *
 * @param {string|object} [hostnameOrConfig]
 *        Legacy: hostname string. New: backendConfig object `{host, port, protocol, ssl_enabled}`.
 * @param {string} [port]  - Legacy port override (ignored when first arg is an object).
 * @returns {string} e.g. "https://demo.giljo.ai" or "http://localhost:7272"
 */
export function buildServerUrl(hostnameOrConfig, port) {
  // Path 1+2: backendConfig object passed in.
  if (hostnameOrConfig && typeof hostnameOrConfig === 'object') {
    const cfg = hostnameOrConfig
    const protocol = cfg.protocol || (window.location.protocol === 'https:' ? 'https' : 'http')
    const host = cfg.host || window.location.hostname
    const cfgPort = cfg.port

    // Browser is already on the target host — trust window.location.origin.
    // This automatically omits the port for proxy-fronted deployments where the
    // backend's internal port differs from the public-facing port.
    if (host && window.location.hostname === host) {
      return window.location.origin
    }

    // Out-of-band composition: omit implicit default ports.
    const isImplicitHttps = protocol === 'https' && Number(cfgPort) === 443
    const isImplicitHttp = protocol === 'http' && Number(cfgPort) === 80
    if (!cfgPort || isImplicitHttps || isImplicitHttp) {
      return `${protocol}://${host}`
    }
    return `${protocol}://${host}:${cfgPort}`
  }

  // Path 3: legacy string-based signature.
  const h = hostnameOrConfig || window.location.hostname
  const p = port || window.location.port || '7272'
  const protocol = window.location.protocol === 'https:' ? 'https' : 'http'
  return `${protocol}://${h}:${p}`
}

/**
 * True if the browser page is served over HTTPS.
 * Note: HTTPS from the browser's perspective may be terminated by Cloudflare or
 * nginx — it does NOT imply the backend itself speaks TLS.
 * @returns {boolean}
 */
export function isBrowserHttps() {
  return window.location.protocol === 'https:'
}

/**
 * True when the backend serves its own TLS (mkcert / self-signed on LAN).
 * This is what triggers the cert-trust UI step — Node.js tools need to trust
 * the backend's CA.
 * Cloudflare/nginx-proxied deployments report ssl_enabled=false even though the
 * public URL is https, because their TLS is terminated by the proxy, not the backend.
 * @param {object} [backendConfig] - `{ssl_enabled: bool, ...}` from GET /api/v1/config/frontend
 * @returns {boolean}
 */
export function isBackendHttps(backendConfig) {
  return backendConfig?.ssl_enabled === true
}

/**
 * @deprecated Use `isBrowserHttps()` or `isBackendHttps(backendConfig)` instead.
 * Retained as an alias for callers that haven't migrated yet.
 * @returns {boolean}
 */
export function isHttps() {
  return isBrowserHttps()
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
  return `echo 'export GILJO_API_KEY="${key}"' >> ~/.bashrc && export GILJO_API_KEY="${key}"`
}

// ─── Certificate trust commands ───────────────────────────────────

export const CERT_TRUST_WINDOWS = '$env:NODE_OPTIONS = "--use-system-ca"; [System.Environment]::SetEnvironmentVariable(\'NODE_OPTIONS\', \'--use-system-ca\', \'User\')'
export const CERT_TRUST_UNIX = 'mkdir -p ~/.giljo && cp ~/Downloads/rootCA.pem ~/.giljo/rootCA.pem && export NODE_EXTRA_CA_CERTS="$HOME/.giljo/rootCA.pem"'

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
