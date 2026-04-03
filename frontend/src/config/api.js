// API Configuration for GiljoAI MCP Dashboard
// Dynamically configured from environment or config file
import configService from '@/services/configService'

// Initial fallback configuration (used before backend config is fetched)
// CRITICAL: Use window.API_BASE_URL first (set in index.html) for production mode
const API_PORT = import.meta.env.VITE_API_PORT || window.API_PORT || window.location.port || '7272'
const API_HOST = import.meta.env.VITE_API_HOST || window.API_HOST || window.location.hostname
const DEFAULT_PROTOCOL = window.location.protocol === 'https:' ? 'https' : 'http'
const DEFAULT_BASE_URL =
  window.API_BASE_URL || (import.meta.env.DEV ? '' : `${DEFAULT_PROTOCOL}://${API_HOST}:${API_PORT}`)

// Configuration object that will be updated after fetching from backend
let runtimeConfig = null

/**
 * Initialize API configuration from backend
 * This should be called before the app mounts to ensure correct API host
 */
export async function initializeApiConfig() {
  try {
    // Fetch config from backend
    const backendConfig = await configService.fetchConfig()

    // Update runtime config with backend values
    runtimeConfig = {
      api: backendConfig.api,
      websocket: backendConfig.websocket,
      mode: backendConfig.mode,
      security: backendConfig.security,
    }

    // Choose baseURL strategy
    // - Dev: use same-origin + Vite proxy to avoid CORS
    // - Prod: use explicit host:port from backend
    const devMode = import.meta.env.DEV === true
    const apiProtocol = runtimeConfig.api?.protocol || DEFAULT_PROTOCOL
    const newBaseURL = devMode ? '' : `${apiProtocol}://${runtimeConfig.api.host}:${runtimeConfig.api.port}`

    // Update API and WebSocket config
    API_CONFIG.REST_API.baseURL = newBaseURL
    API_CONFIG.WEBSOCKET.url = runtimeConfig.websocket.url

    // Update default tenant key header from backend config
    if (runtimeConfig.security?.default_tenant_key) {
      API_CONFIG.REST_API.headers['X-Tenant-Key'] = runtimeConfig.security.default_tenant_key
    }
    // Extract port from websocket URL or use API port
    API_CONFIG.WEBSOCKET.port = runtimeConfig.api?.port || parseInt(API_PORT, 10)

    // Update axios instance baseURL (created before config was fetched)
    // Import dynamically to avoid circular dependency
    const { updateApiBaseURL } = await import('@/services/api')
    updateApiBaseURL(newBaseURL)

    return true
  } catch (error) {
    console.error('[API Config] Failed to initialize from backend, using fallback:', error)
    return false
  }
}

/**
 * Get current runtime configuration
 * @returns {Object} Current configuration
 */
export function getRuntimeConfig() {
  return runtimeConfig
}

/**
 * Get the current API base URL (runtime-aware)
 * Always use this instead of API_CONFIG.REST_API.baseURL for fetch() calls
 * @returns {string} Current API base URL
 */
export function getApiBaseURL() {
  return window.API_BASE_URL || API_CONFIG.REST_API.baseURL
}

/**
 * Get the default tenant key (runtime-aware)
 * Resolves from: runtime config (backend) > env var > empty string
 * @returns {string} Default tenant key
 */
export function getDefaultTenantKey() {
  return runtimeConfig?.security?.default_tenant_key || import.meta.env.VITE_DEFAULT_TENANT_KEY || ''
}

export const API_CONFIG = {
  REST_API: {
    baseURL: import.meta.env.VITE_API_URL || DEFAULT_BASE_URL,
    timeout: 30000,
    headers: {
      'Content-Type': 'application/json',
      'X-Tenant-Key': import.meta.env.VITE_DEFAULT_TENANT_KEY || '',
    },
  },
  WEBSOCKET: {
    url: import.meta.env.VITE_WS_URL ||
      (window.location.protocol === 'https:' ? `wss://${API_HOST}:${API_PORT}` : `ws://${API_HOST}:${API_PORT}`),
    port: parseInt(API_PORT, 10),
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 30000,
    reconnectionAttempts: 10,
    debug: import.meta.env.VITE_WS_DEBUG === 'true' || false,
  },
}

export default API_CONFIG
