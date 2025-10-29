import axios from 'axios'
import { API_CONFIG } from '@/config/api'

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_CONFIG.REST_API.baseURL,
  timeout: API_CONFIG.REST_API.timeout,
  headers: API_CONFIG.REST_API.headers,
  withCredentials: true, // CRITICAL: Send cookies with requests for JWT auth
})

// Export function to update baseURL after runtime config is fetched
export function updateApiBaseURL(newBaseURL) {
  apiClient.defaults.baseURL = newBaseURL
  console.log('[API] Updated axios baseURL to:', newBaseURL)
}

// Request interceptor for tenant key
// NOTE: Authentication token is sent automatically via httpOnly cookie (access_token)
// No need to manually add Authorization header - the browser handles this
apiClient.interceptors.request.use(
  (config) => {
    // Ensure tenant key is always present
    if (!config.headers['X-Tenant-Key']) {
      config.headers['X-Tenant-Key'] =
        import.meta.env.VITE_DEFAULT_TENANT_KEY || 'tk_cyyOVf1HsbOCA8eFLEHoYUwiIIYhXjnd'
    }

    return config
  },
  (error) => Promise.reject(error),
)

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401) {
      // Handle unauthorized: clear cached state
      localStorage.removeItem('auth_token')
      localStorage.removeItem('user')

      if (!window.location.pathname.includes('/login') && !window.location.pathname.includes('/welcome') && !originalRequest?._retry) {
        originalRequest._retry = true

        // CRITICAL FIX (Handover 0034): Check fresh install status BEFORE redirecting
        // This prevents redirecting to /login when we should show /welcome (create admin page)
        try {
          const setupResponse = await fetch(`${apiClient.defaults.baseURL}/api/setup/status`, {
            method: 'GET',
            cache: 'no-cache'
          })

          if (setupResponse.ok) {
            const setupData = await setupResponse.json()

            if (setupData.is_fresh_install) {
              // Fresh install (0 users) - redirect to create admin account
              console.log('[API] 401 on fresh install, redirecting to create admin account')
              window.location.href = '/welcome'
              return Promise.reject(error)
            }
          }
        } catch (setupError) {
          console.warn('[API] Failed to check fresh install status:', setupError)
          // On error, default to login redirect (secure fallback)
        }

        // Normal operation (users exist) - redirect to login
        const currentPath = window.location.pathname + window.location.search
        window.location.href = `/login?redirect=${encodeURIComponent(currentPath)}`
      }
    }

    // Handle 403 Forbidden
    if (error.response?.status === 403) {
      console.error('[API] Access forbidden:', error.response.data)
    }

    // Handle network errors
    if (!error.response) {
      console.error('[API] Network error - server may be unreachable')
    }

    return Promise.reject(error)
  },
)

// API Service Methods
export const api = {
  // Products
  products: {
    list: (params) => apiClient.get('/api/v1/products/', { params }),
    get: (id) => apiClient.get(`/api/v1/products/${id}/`),
    create: (data) => {
      // Handle file upload with FormData
      if (data instanceof FormData) {
        return apiClient.post('/api/v1/products/', data, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
      }
      // Regular JSON creation without file
      const formData = new FormData()
      formData.append('name', data.name)
      if (data.description) formData.append('description', data.description)
      // Handover 0042: Add config_data as JSON string
      if (data.configData) formData.append('config_data', JSON.stringify(data.configData))
      return apiClient.post('/api/v1/products/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
    },
    update: (id, data) => {
      // Handover 0042: Convert to FormData for config_data support
      const formData = new FormData()
      if (data.name) formData.append('name', data.name)
      if (data.description) formData.append('description', data.description)
      if (data.configData) formData.append('config_data', JSON.stringify(data.configData))
      return apiClient.put(`/api/v1/products/${id}/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
    },
    delete: (id) => apiClient.delete(`/api/v1/products/${id}/`),
    getCascadeImpact: (id) => apiClient.get(`/api/v1/products/${id}/cascade-impact`),
    uploadVision: (id, file) => {
      const formData = new FormData()
      formData.append('vision_file', file)
      return apiClient.post(`/api/v1/products/${id}/upload-vision/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
    },
    getVisionChunks: (id) => apiClient.get(`/api/v1/products/${id}/vision-chunks/`),
    // Real-time token estimate for active product (Handover 0049)
    getActiveProductTokenEstimate: () => apiClient.get('/api/v1/products/active/token-estimate'),
    // Product activation endpoints (Handover 0049)
    activate: (id) => apiClient.post(`/api/v1/products/${id}/activate`),
    deactivate: (id) => apiClient.post(`/api/v1/products/${id}/deactivate`),
  },

  // Projects
  projects: {
    list: (params) => apiClient.get('/api/v1/projects/', { params }),
    get: (id) => apiClient.get(`/api/v1/projects/${id}/`),
    create: (data) => apiClient.post('/api/v1/projects/', data),
    update: (id, data) => apiClient.put(`/api/v1/projects/${id}/`, data),
    delete: (id) => apiClient.delete(`/api/v1/projects/${id}/`),
    close: (id, summary) => apiClient.delete(`/api/v1/projects/${id}/`, { params: { summary } }),
    status: (id) => apiClient.get(`/api/v1/projects/${id}/status/`),
    fetchDeleted: () => apiClient.get('/api/v1/projects/deleted'),
    // Status change endpoints - use PATCH for generic status updates
    changeStatus: (id, newStatus) => apiClient.patch(`/api/v1/projects/${id}/`, { status: newStatus }),
    // Specific action endpoints
    activate: (id) => apiClient.post(`/api/v1/projects/${id}/activate`),
    deactivate: (id) => apiClient.post(`/api/v1/projects/${id}/deactivate`),
    complete: (id) => apiClient.post(`/api/v1/projects/${id}/complete`),
    cancel: (id) => apiClient.post(`/api/v1/projects/${id}/cancel`),
    restore: (id) => apiClient.post(`/api/v1/projects/${id}/restore`),
    restoreCompleted: (id) => apiClient.post(`/api/v1/projects/${id}/restore-completed`),
  },

  // Agents
  agents: {
    list: (projectId) => apiClient.get('/api/v1/agents/', { params: { project_id: projectId } }),
    get: (id) => apiClient.get(`/api/v1/agents/${id}/`),
    create: (data) => apiClient.post('/api/v1/agents/', data),
    health: (id) => apiClient.get(`/api/v1/agents/${id}/health/`),
    assign: (agentName, jobData) => apiClient.post(`/api/v1/agents/${agentName}/assign/`, jobData),
    decommission: (id, reason) => apiClient.post(`/api/v1/agents/${id}/decommission/`, { reason }),
    tree: (projectId) => apiClient.get('/api/v1/agents/tree', { params: { project_id: projectId } }),
    metrics: (projectId, hours = 24) =>
      apiClient.get('/api/v1/agents/metrics', { params: { project_id: projectId, hours } }),
  },

  // Messages
  messages: {
    list: (params) => apiClient.get('/api/v1/messages/', { params }),
    get: (id) => apiClient.get(`/api/v1/messages/${id}/`),
    send: (data) => apiClient.post('/api/v1/messages/', data),
    acknowledge: (id, agentName) =>
      apiClient.post(`/api/v1/messages/${id}/acknowledge/`, { agent_name: agentName }),
    complete: (id, result) => apiClient.post(`/api/v1/messages/${id}/complete/`, { result }),
    broadcast: (projectId, content) =>
      apiClient.post('/api/v1/messages/broadcast/', { project_id: projectId, content }),
  },

  // Tasks
  tasks: {
    list: (params) => apiClient.get('/api/v1/tasks/', { params }),
    get: (id) => apiClient.get(`/api/v1/tasks/${id}/`),
    create: (data) => apiClient.post('/api/v1/tasks/', data),
    update: (id, data) => apiClient.put(`/api/v1/tasks/${id}/`, data),
    delete: (id) => apiClient.delete(`/api/v1/tasks/${id}/`),
    changeStatus: (id, status) => apiClient.patch(`/api/v1/tasks/${id}/status/`, { status }),
    summary: (productId) =>
      apiClient.get('/api/v1/tasks/summary/', { params: { product_id: productId } }),
    convert: (id, data) => apiClient.post(`/api/v1/tasks/${id}/convert/`, data),
  },

  // Users (for tenant user listing and assignment)
  users: {
    list: () => apiClient.get('/api/auth/users'),
    // Field priority configuration (Handover 0048)
    getFieldPriorityConfig: () => apiClient.get('/api/users/me/field-priority'),
    updateFieldPriorityConfig: (config) => apiClient.put('/api/users/me/field-priority', config),
    resetFieldPriorityConfig: () => apiClient.post('/api/users/me/field-priority/reset'),
  },

  // Vision Documents (Multi-Document Support - Handover 0043)
  visionDocuments: {
    // List all vision documents for a product
    listByProduct: (productId) => apiClient.get(`/api/vision-documents/product/${productId}?active_only=false`),
    // Get a specific vision document
    get: (documentId) => apiClient.get(`/api/vision-documents/${documentId}`),
    // Upload a new vision document (accepts FormData)
    upload: (formData) => {
      return apiClient.post('/api/vision-documents/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
    },
    // Delete a vision document
    delete: (documentId) => apiClient.delete(`/api/vision-documents/${documentId}`),
    // Get chunks for a specific document
    getChunks: (documentId) => apiClient.get(`/api/vision-documents/${documentId}/chunks`),
  },

  // Legacy Vision API (Single Document - Deprecated)
  vision: {
    get: () => apiClient.get('/api/v1/context/vision/'),
    getChunk: (part, maxTokens = 20000) =>
      apiClient.get('/api/v1/context/vision/', {
        params: { part, max_tokens: maxTokens },
      }),
    getIndex: () => apiClient.get('/api/v1/context/vision/index/'),
  },

  // Context & Discovery
  context: {
    getIndex: (productId) =>
      apiClient.get('/api/v1/context/index/', { params: { product_id: productId } }),
    getSection: (documentName, sectionName) =>
      apiClient.get('/api/v1/context/section/', {
        params: { document_name: documentName, section_name: sectionName },
      }),
  },

  // Settings & Configuration
  settings: {
    get: () => apiClient.get('/api/v1/config/'),
    update: (data) => apiClient.put('/api/v1/config/', data),
    getProduct: () => apiClient.get('/api/v1/config/product/'),
    // Database config and health
    getDatabase: () => apiClient.get('/api/v1/config/database'),
    testDatabase: () => apiClient.get('/api/v1/config/health/database'),
    getCookieDomains: () => apiClient.get('/api/v1/user/settings/cookie-domains'),
    addCookieDomain: (domain) => apiClient.post('/api/v1/user/settings/cookie-domains', { domain }),
    removeCookieDomain: (domain) => apiClient.delete('/api/v1/user/settings/cookie-domains', { data: { domain } }),
  },

  // Session Info
  session: {
    info: () => apiClient.get('/api/v1/stats/session/'),
    stats: () => apiClient.get('/api/v1/stats/'),
  },

  // Setup Status
  setup: {
    status: () => apiClient.get('/api/setup/status'),
  },

  // Templates
  templates: {
    list: (params) => apiClient.get('/api/v1/templates/', { params }),
    get: (id) => apiClient.get(`/api/v1/templates/${id}/`),
    create: (data) => apiClient.post('/api/v1/templates/', data),
    update: (id, data) => apiClient.put(`/api/v1/templates/${id}/`, data),
    delete: (id) => apiClient.delete(`/api/v1/templates/${id}/`),
    history: (id, limit = 10) =>
      apiClient.get(`/api/v1/templates/${id}/history/`, { params: { limit } }),
    restore: (templateId, archiveId) =>
      apiClient.post(`/api/v1/templates/${templateId}/restore/${archiveId}/`),
    preview: (id, data) => apiClient.post(`/api/v1/templates/${id}/preview/`, data),
    reset: (id) => apiClient.post(`/api/v1/templates/${id}/reset/`),
    diff: (id) => apiClient.get(`/api/v1/templates/${id}/diff/`),
    exportClaudeCode: (data) => apiClient.post('/api/export/claude-code', data),
  },

  // Authentication (JWT via httpOnly cookies)
  auth: {
    login: (username, password) => apiClient.post('/api/auth/login', { username, password }),
    logout: () => apiClient.post('/api/auth/logout'),
    me: () => apiClient.get('/api/auth/me'),
    register: (data) => apiClient.post('/api/auth/register', data),
    // REMOVED (Handover 0034): changePassword - legacy admin/admin flow
    // Replaced by createFirstAdmin for fresh installs
    createFirstAdmin: (data) => apiClient.post('/api/auth/create-first-admin', data),
    listUsers: () => apiClient.get('/api/auth/users'),
    updateUser: (userId, data) => apiClient.put(`/api/auth/users/${userId}`, data),
    deleteUser: (userId) => apiClient.delete(`/api/auth/users/${userId}`),
    // Password reset endpoints (Handover 0023)
    checkFirstLogin: (username) => apiClient.post('/api/auth/check-first-login', { username }),
    completeFirstLogin: (data) => apiClient.post('/api/auth/complete-first-login', data),
    verifyPinAndResetPassword: (data) => apiClient.post('/api/auth/verify-pin-and-reset-password', data),
    setRecoveryPin: (data) => apiClient.post('/api/auth/set-recovery-pin', data),
    resetUserPassword: (userId) => apiClient.post(`/api/users/${userId}/reset-password`),
  },

  // API Key Management
  apiKeys: {
    list: () => apiClient.get('/api/auth/api-keys'),
    create: (name) => apiClient.post('/api/auth/api-keys', { name }),
    delete: (keyId) => apiClient.delete(`/api/auth/api-keys/${keyId}`),
  },

  // AI Tools Integration
  aiTools: {
    getSupportedTools: () => apiClient.get('/api/ai-tools/supported'),
    generateConfig: (toolName) => apiClient.get(`/api/ai-tools/config-generator/${toolName}`),
    downloadSetupGuide: (toolName) => apiClient.get(`/api/ai-tools/config-generator/${toolName}/markdown`),
  },

  // Serena MCP Integration
  serena: {
    getStatus: () => apiClient.get('/api/serena/status'),
    toggle: (enabled) => apiClient.post('/api/serena/toggle', { enabled }),
  },

  // Orchestrator (Multi-Agent Workflow Coordination)
  orchestrator: {
    launch: (data) => apiClient.post('/api/v1/orchestration/launch', data),
    getWorkflowStatus: (projectId) => apiClient.get(`/api/v1/orchestration/workflow-status/${projectId}`),
    getMetrics: (projectId) => apiClient.get(`/api/v1/orchestration/metrics/${projectId}`),
    createMissions: (data) => apiClient.post('/api/v1/orchestration/create-missions', data),
    spawnTeam: (data) => apiClient.post('/api/v1/orchestration/spawn-team', data),
  },
}

export default api
