// API Configuration for GiljoAI MCP Dashboard
// Dynamically configured from environment or config file
import configService from '@/services/configService'

// Initial fallback configuration (used before backend config is fetched)
// CRITICAL: Use window.API_BASE_URL first (set in index.html) for production mode
const API_PORT = import.meta.env.VITE_API_PORT || window.API_PORT || '7272'
const API_HOST = import.meta.env.VITE_API_HOST || window.API_HOST || window.location.hostname
const DEFAULT_BASE_URL =
  window.API_BASE_URL || (import.meta.env.DEV ? '' : `http://${API_HOST}:${API_PORT}`)

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
    const newBaseURL = devMode ? '' : `http://${runtimeConfig.api.host}:${runtimeConfig.api.port}`

    // Update API and WebSocket config
    API_CONFIG.REST_API.baseURL = newBaseURL
    API_CONFIG.WEBSOCKET.url = runtimeConfig.websocket.url
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

export const API_CONFIG = {
  REST_API: {
    baseURL: import.meta.env.VITE_API_URL || DEFAULT_BASE_URL,
    timeout: 30000,
    headers: {
      'Content-Type': 'application/json',
      'X-Tenant-Key':
        import.meta.env.VITE_DEFAULT_TENANT_KEY || 'tk_cyyOVf1HsbOCA8eFLEHoYUwiIIYhXjnd',
    },
  },
  WEBSOCKET: {
    url: import.meta.env.VITE_WS_URL || `ws://${API_HOST}:${API_PORT}`,
    port: parseInt(API_PORT, 10),
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 30000,
    reconnectionAttempts: 10,
    debug: import.meta.env.VITE_WS_DEBUG === 'true' || false,
  },
  ENDPOINTS: {
    // Project Management
    projects: '/api/v1/projects/',
    project: '/api/v1/projects/:id',

    // Agent Jobs Management (Handover 0119 - Migrated from /api/v1/agents)
    agentJobs: '/api/agent-jobs/',
    agentJob: '/api/agent-jobs/:jobId',
    agentJobStatus: '/api/agent-jobs/:jobId/status',

    // Messages
    messages: '/api/v1/messages/',
    message: '/api/v1/messages/:id',

    // Tasks
    tasks: '/api/v1/tasks/',
    task: '/api/v1/tasks/:id',

    // Vision Documents
    vision: '/api/v1/context/vision',
    visionChunk: '/api/v1/context/vision/:part',

    // Configuration
    settings: '/api/v1/config/',
    context: '/api/v1/context/',

    // Templates
    templates: '/api/v1/templates/',
    template: '/api/v1/templates/:id',
    templateHistory: '/api/v1/templates/:id/history',
    templateRestore: '/api/v1/templates/:id/restore/:archiveId',

    // Prompts (Handover 0119 - Standardized to /api/v1/prompts)
    prompts: '/api/v1/prompts/',
    promptAgent: '/api/v1/prompts/agent/:jobId',
    promptOrchestrator: '/api/v1/prompts/orchestrator/:projectId',

    // Statistics
    stats: '/api/v1/stats/',
    health: '/health',
  },
}

export default API_CONFIG
