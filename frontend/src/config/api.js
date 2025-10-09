// API Configuration for GiljoAI MCP Dashboard
// Dynamically configured from environment or config file
import configService from '@/services/configService'

// Initial fallback configuration (used before backend config is fetched)
const API_PORT = import.meta.env.VITE_API_PORT || window.API_PORT || '7272'
const API_HOST = import.meta.env.VITE_API_HOST || window.API_HOST || window.location.hostname

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

    // Update API_CONFIG with correct values
    API_CONFIG.REST_API.baseURL = `http://${runtimeConfig.api.host}:${runtimeConfig.api.port}`
    API_CONFIG.WEBSOCKET.url = runtimeConfig.websocket.url

    console.log('[API Config] Initialized from backend:', runtimeConfig)
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

export const API_CONFIG = {
  REST_API: {
    baseURL: import.meta.env.VITE_API_URL || `http://${API_HOST}:${API_PORT}`,
    timeout: 30000,
    headers: {
      'Content-Type': 'application/json',
      'X-Tenant-Key':
        import.meta.env.VITE_DEFAULT_TENANT_KEY || 'tk_cyyOVf1HsbOCA8eFLEHoYUwiIIYhXjnd',
    },
  },
  WEBSOCKET: {
    url: import.meta.env.VITE_WS_URL || `ws://${API_HOST}:${API_PORT}`,
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

    // Agent Management
    agents: '/api/v1/agents/',
    agent: '/api/v1/agents/:id',
    agentHealth: '/api/v1/agents/:id/health',

    // Messages
    messages: '/api/v1/messages/',
    message: '/api/v1/messages/:id',
    acknowledge: '/api/v1/messages/:id/acknowledge',

    // Tasks
    tasks: '/api/v1/tasks/',
    task: '/api/v1/tasks/:id',

    // Vision Documents
    vision: '/api/v1/context/vision',
    visionChunk: '/api/v1/context/vision/:part',

    // Configuration
    settings: '/api/v1/config/',
    context: '/api/v1/context/',

    // Templates (NEW)
    templates: '/api/v1/templates/',
    template: '/api/v1/templates/:id',
    templateHistory: '/api/v1/templates/:id/history',
    templateRestore: '/api/v1/templates/:id/restore/:archiveId',

    // Statistics
    stats: '/api/v1/stats/',
    health: '/health',
  },
}

export default API_CONFIG
