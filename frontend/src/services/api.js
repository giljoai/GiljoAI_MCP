import axios from 'axios'
import { API_CONFIG } from '@/config/api'
import { parseErrorResponse, getErrorMessage } from '@/utils/errorMessages'

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

// Store current tenant key (set by user store after login)
let currentTenantKey = null

export function setTenantKey(tenantKey) {
  currentTenantKey = tenantKey
  console.log('[API] Tenant key updated to:', tenantKey)
}

// Request interceptor for tenant key
// NOTE: Authentication token is sent automatically via httpOnly cookie (access_token)
// No need to manually add Authorization header - the browser handles this
apiClient.interceptors.request.use(
  (config) => {
    // Use current tenant key if set (from user store after login)
    // Otherwise fallback to default for pre-auth requests
    if (!config.headers['X-Tenant-Key']) {
      config.headers['X-Tenant-Key'] =
        currentTenantKey ||
        import.meta.env.VITE_DEFAULT_TENANT_KEY ||
        'tk_cyyOVf1HsbOCA8eFLEHoYUwiIIYhXjnd'
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

    // Parse error response (handles both structured and legacy errors)
    const parsedError = parseErrorResponse(error)

    // Log structured errors for debugging
    if (parsedError.isStructured) {
      console.error('[API] Structured error:', {
        errorCode: parsedError.errorCode,
        message: parsedError.message,
        context: parsedError.context,
        timestamp: parsedError.timestamp,
        status: parsedError.status,
      })

      // Log validation errors with field details
      if (parsedError.errors) {
        console.error('[API] Validation errors:', parsedError.errors)
      }
    } else if (error.response) {
      // Log legacy errors for debugging
      console.error('[API] Legacy error:', {
        status: error.response.status,
        message: error.response.data?.message || error.message,
        data: error.response.data,
      })
    } else {
      // Log network errors
      console.error('[API] Network error:', error.message)
    }

    if (error.response?.status === 401) {
      // Handle unauthorized: clear cached state
      localStorage.removeItem('auth_token')
      localStorage.removeItem('user')

      if (
        !window.location.pathname.includes('/login') &&
        !window.location.pathname.includes('/welcome') &&
        !originalRequest?._retry
      ) {
        originalRequest._retry = true

        // CRITICAL FIX (Handover 0034): Check fresh install status BEFORE redirecting
        // This prevents redirecting to /login when we should show /welcome (create admin page)
        try {
          const setupResponse = await fetch(`${apiClient.defaults.baseURL}/api/setup/status`, {
            method: 'GET',
            cache: 'no-cache',
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
      console.error('[API] Access forbidden:', {
        message: parsedError.message,
        context: parsedError.context,
      })
    }

    // Handle network errors
    if (!error.response) {
      console.error('[API] Network error - server may be unreachable:', error.message)
    }

    return Promise.reject(error)
  },
)

// API Service Methods
export const api = {
  // Products
  products: {
    list: (params) => apiClient.get('/api/v1/products/', { params }),
    get: (id) => apiClient.get(`/api/v1/products/${id}`),
    getActive: () => apiClient.get('/api/v1/products/refresh-active'),
    create: (data) => {
      // Handover 0507: Send JSON to match backend ProductCreate schema
      // Backend expects: { name, description, project_path, config_data, target_platforms }
      const payload = {
        name: data.name,
        description: data.description || null,
        project_path: data.projectPath || null,
        config_data: data.configData || null, // FIX: Add config_data (Handover 0507)
        target_platforms: data.target_platforms || ['all'], // Handover 0425 Phase 2
      }
      return apiClient.post('/api/v1/products/', payload)
    },
    update: (id, data) => {
      // Handover 0507: Send JSON to match backend ProductUpdate schema
      // Backend expects: { name?, description?, project_path?, config_data?, target_platforms?, is_active? }
      const payload = {}
      if (data.name !== undefined) payload.name = data.name
      if (data.description !== undefined) payload.description = data.description
      if (data.projectPath !== undefined) payload.project_path = data.projectPath
      if (data.configData !== undefined) payload.config_data = data.configData // FIX: Add config_data (Handover 0507)
      if (data.target_platforms !== undefined) payload.target_platforms = data.target_platforms // Handover 0425 Phase 2
      if (data.isActive !== undefined) payload.is_active = data.isActive
      return apiClient.put(`/api/v1/products/${id}`, payload)
    },
    delete: (id) => apiClient.delete(`/api/v1/products/${id}`),
    getCascadeImpact: (id) => apiClient.get(`/api/v1/products/${id}/cascade-impact`),

    // Vision document endpoints (Handover 0507: Consolidated to /vision)
    uploadVision: (id, file) => {
      const formData = new FormData()
      formData.append('file', file) // Backend expects 'file' parameter
      return apiClient.post(`/api/v1/products/${id}/vision`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
    },
    listVision: (id) => apiClient.get(`/api/v1/products/${id}/vision`),
    deleteVision: (id, docId) => apiClient.delete(`/api/v1/products/${id}/vision/${docId}`),
    getVisionChunks: (id) => apiClient.get(`/api/v1/products/${id}/vision-chunks`),
    // Consolidated vision regeneration endpoint (Handover 0377)
    regenerateConsolidated: (id, force = true) =>
      apiClient.post(`/api/v1/products/${id}/vision/regenerate-consolidated`, null, {
        params: { force },
      }),
    // Product activation endpoints (Handover 0049)
    activate: (id) => apiClient.post(`/api/v1/products/${id}/activate`),
    deactivate: (id) => apiClient.post(`/api/v1/products/${id}/deactivate`),
    // Soft delete recovery endpoints
    getDeletedProducts: () => apiClient.get('/api/v1/products/deleted'),
    restoreProduct: (id) => apiClient.post(`/api/v1/products/${id}/restore`),
    // Git integration endpoints (Handover 013B)
    getGitIntegration: (id) => apiClient.get(`/api/v1/products/${id}/git-integration`),
    updateGitIntegration: (id, settings) =>
      apiClient.post(`/api/v1/products/${id}/git-integration`, settings),
    // 360 Memory endpoints (Handover 0490)
    getMemoryEntries: (productId, params) =>
      apiClient.get(`/api/v1/products/${productId}/memory-entries`, { params }),
  },

  // Projects
  projects: {
    list: (params) => apiClient.get('/api/v1/projects/', { params }),
    get: (id) => apiClient.get(`/api/v1/projects/${id}`),
    getOrchestrator: (id) => apiClient.get(`/api/v1/projects/${id}/orchestrator`),
    getActive: () => apiClient.get('/api/v1/projects/active'),
    create: (data) => apiClient.post('/api/v1/projects/', data),
    update: (id, data) => apiClient.patch(`/api/v1/projects/${id}`, data),
    delete: (id) => apiClient.delete(`/api/v1/projects/${id}`),
    close: (id, summary) => apiClient.delete(`/api/v1/projects/${id}`, { params: { summary } }),
    fetchDeleted: () => apiClient.get('/api/v1/projects/deleted'),
    // Status change endpoints - use PATCH for generic status updates
    changeStatus: (id, newStatus) =>
      apiClient.patch(`/api/v1/projects/${id}`, { status: newStatus }),
    // Specific action endpoints (Handover 0507: Added force and reason parameters)
    activate: (id, force = false) => apiClient.post(`/api/v1/projects/${id}/activate`, { force }),
    deactivate: (id, reason = null) =>
      apiClient.post(`/api/v1/projects/${id}/deactivate`, { reason }),
    complete: (id) => apiClient.post(`/api/v1/projects/${id}/complete`),
    cancel: (id) => apiClient.post(`/api/v1/projects/${id}/cancel`),
    restore: (id) => apiClient.post(`/api/v1/projects/${id}/restore`),
    purgeDeleted: (id) => apiClient.delete(`/api/v1/projects/${id}/purge`),
    purgeAllDeleted: () => apiClient.delete('/api/v1/projects/deleted'),
    // Completed projects are resumed via the continue-working endpoint
    restoreCompleted: (id) => apiClient.post(`/api/v1/projects/${id}/continue-working`),
    // Handover 0507: Project launch and summary with config parameter support
    summary: (id) => apiClient.get(`/api/v1/projects/${id}/summary`),
    launch: (id, config = null) => apiClient.post(`/api/v1/projects/${id}/launch`, config),
    // Handover 0108: Staging cancellation
    cancelStaging: (id) => apiClient.post(`/api/v1/projects/${id}/cancel-staging`),
    // Closeout endpoints (Handover 0371, 0412)
    getCloseoutData: (id) => apiClient.get(`/api/v1/projects/${id}/closeout`),
    completeWithData: (id, data) => apiClient.post(`/api/v1/projects/${id}/complete`, data),
    archive: (id) => apiClient.post(`/api/v1/projects/${id}/archive`),  // Handover 0412: Simple archive
    // Implementation phase gate (Handover 0709)
    launchImplementation: (id) => apiClient.patch(`/api/agent-jobs/projects/${id}/launch-implementation`),
  },


  // Messages
  messages: {
    list: (params) => apiClient.get('/api/v1/messages/', { params }),
    get: (id) => apiClient.get(`/api/v1/messages/${id}/`),
    // Legacy send method - use sendUnified for UI messaging (Handover 0299)
    send: (data) => apiClient.post('/api/v1/messages/', data),
    complete: (id, result) => apiClient.post(`/api/v1/messages/${id}/complete/`, { result }),
    broadcast: (projectId, content, priority = 'normal') =>
      apiClient.post('/api/v1/messages/broadcast', {
        project_id: projectId,
        content: content,
        priority: priority,
      }),
    /**
     * Unified send endpoint for UI messaging (Handover 0299)
     * Handles both broadcast (toAgents=['all']) and direct messages.
     * Uses MessageService for consistent message handling.
     *
     * @param {string} projectId - Project ID
     * @param {string[]} toAgents - Recipients. Use ['all'] for broadcast.
     * @param {string} content - Message content
     * @param {string} messageType - 'direct' or 'broadcast'
     * @param {string} priority - 'low', 'normal', or 'high'
     */
    sendUnified: (projectId, toAgents, content, messageType = 'direct', priority = 'normal') =>
      apiClient.post('/api/v1/messages/send', {
        project_id: projectId,
        to_agents: toAgents,
        content: content,
        message_type: messageType,
        priority: priority,
      }),
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
    convertToProject: (id) => apiClient.post(`/api/v1/tasks/${id}/convert`, {}),
  },

  // Users (for tenant user listing and assignment)
  // Handover 0506: Fixed paths to use /api/v1/users
  users: {
    list: () => apiClient.get('/api/v1/users/'),
    get: (userId) => apiClient.get(`/api/v1/users/${userId}`),
    update: (userId, updates) => apiClient.patch(`/api/v1/users/${userId}`, updates),
    delete: (userId) => apiClient.delete(`/api/v1/users/${userId}`),
    getMe: () => apiClient.get('/api/v1/users/me'),
    changePassword: (oldPassword, newPassword) =>
      apiClient.put('/api/v1/users/me/password', { oldPassword, newPassword }),
    // Field priority configuration (Handover 0048)
    getFieldPriorityConfig: () => apiClient.get('/api/v1/users/me/field-priority'),
    updateFieldPriorityConfig: (config) => apiClient.put('/api/v1/users/me/field-priority', config),
    resetFieldPriorityConfig: () => apiClient.post('/api/v1/users/me/field-priority/reset'),
  },

  // Vision Documents (Multi-Document Support - Handover 0043)
  visionDocuments: {
    // List all vision documents for a product
    listByProduct: (productId) =>
      apiClient.get(`/api/vision-documents/product/${productId}?active_only=false`),
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


  // Context & Discovery
  context: {
    getIndex: (productId) =>
      apiClient.get('/api/v1/context/index/', { params: { product_id: productId } }),
  },

  // Settings & Configuration
  // Handover 0506: Added new settings endpoints (general, network, database, product-info, cookie-domain)
  settings: {
    // Legacy config endpoints (kept for backward compatibility)
    get: () => apiClient.get('/api/v1/config/'),
    update: (data) => apiClient.put('/api/v1/config/', data),
    // New settings endpoints (Handover 0506)
    getGeneral: () => apiClient.get('/api/v1/settings/general'),
    updateGeneral: (settings) => apiClient.put('/api/v1/settings/general', { settings }),

    getNetwork: () => apiClient.get('/api/v1/settings/network'),
    updateNetwork: (settings) => apiClient.put('/api/v1/settings/network', { settings }),

    getDatabase: () => apiClient.get('/api/v1/settings/database'),

    getProductInfo: () => apiClient.get('/api/v1/settings/product-info'),
    getCookieDomain: () => apiClient.get('/api/v1/settings/cookie-domain'),

    // User settings - cookie domain management
    getCookieDomains: () => apiClient.get('/api/v1/user/settings/cookie-domains'),
    addCookieDomain: (domain) => apiClient.post('/api/v1/user/settings/cookie-domains', { domain }),
    removeCookieDomain: (domain) =>
      apiClient.delete('/api/v1/user/settings/cookie-domains', { data: { domain } }),
  },

  // Setup Status
  setup: {
    status: () => apiClient.get('/api/setup/status'),
  },

  // Templates
  templates: {
    list: (params) => apiClient.get('/api/v1/templates/', { params }),
    get: (id) => apiClient.get(`/api/v1/templates/${id}`),
    create: (data) => apiClient.post('/api/v1/templates/', data),
    update: (id, data) => apiClient.put(`/api/v1/templates/${id}`, data),
    delete: (id) => apiClient.delete(`/api/v1/templates/${id}`),
    history: (id, limit = 10) =>
      apiClient.get(`/api/v1/templates/${id}/history/`, { params: { limit } }),
    // Handover 0396: Added optional reason parameter for restore operation
    restore: (templateId, archiveId, reason = null) => {
      const payload = reason ? { reason } : {}
      return apiClient.post(`/api/v1/templates/${templateId}/restore/${archiveId}/`, payload)
    },
    preview: (id, data = {}) => apiClient.post(`/api/v1/templates/${id}/preview/`, data),
    reset: (id) => apiClient.post(`/api/v1/templates/${id}/reset/`),
    diff: (id) => apiClient.get(`/api/v1/templates/${id}/diff/`),
    activeCount: () => apiClient.get('/api/v1/templates/stats/active-count'),
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
    listUsers: () => apiClient.get('/api/v1/users/'),  // 0371: Fixed - was /api/auth/users (missing PUT/DELETE)
    updateUser: (userId, data) => apiClient.put(`/api/v1/users/${userId}`, data),
    deleteUser: (userId) => apiClient.delete(`/api/v1/users/${userId}`),
    // Password reset endpoints (Handover 0023)
    checkFirstLogin: (username) => apiClient.post('/api/auth/check-first-login', { username }),
    completeFirstLogin: (data) => apiClient.post('/api/auth/complete-first-login', data),
    verifyPinAndResetPassword: (data) =>
      apiClient.post('/api/auth/verify-pin-and-reset-password', data),
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
    downloadSetupGuide: (toolName) =>
      apiClient.get(`/api/ai-tools/config-generator/${toolName}/markdown`),
  },

  // Serena MCP Integration
  serena: {
    getStatus: () => apiClient.get('/api/serena/status'),
    toggle: (enabled) => apiClient.post('/api/serena/toggle', { use_in_prompts: enabled }),
    getConfig: () => apiClient.get('/api/serena/config'),
    updateConfig: (data) => apiClient.post('/api/serena/config', data),
  },

  // Git Integration (system-level)
  git: {
    getSettings: () => apiClient.get('/api/git/settings'),
    toggle: (enabled) => apiClient.post('/api/git/toggle', { enabled }),
    updateSettings: (settings) => apiClient.post('/api/git/settings', settings),
  },

  // Agent Jobs API (Handover 0119 Phase 1 - Migration from /api/v1/agents)
  // Reference: handovers/0119_api_harmonization_backward_compatibility_cleanup.md
  // Field mappings: agent_id → job_id, created_at → spawned_at, status → job status
  agentJobs: {
    // Core job management (maps from old agents API)
    list: (projectId) => apiClient.get('/api/agent-jobs/', { params: { project_id: projectId } }),
    get: (jobId) => apiClient.get(`/api/agent-jobs/${jobId}`),
    spawn: (data) => apiClient.post('/api/agent-jobs/spawn', data),
    status: (jobId) => apiClient.get(`/api/agent-jobs/${jobId}/status`),
    // Additional job-specific endpoints (new functionality)
    acknowledge: (jobId) => apiClient.post(`/api/agent-jobs/${jobId}/acknowledge`),
    reportProgress: (jobId, data) => apiClient.post(`/api/agent-jobs/${jobId}/progress`, data),
    complete: (jobId, data) => apiClient.post(`/api/agent-jobs/${jobId}/complete`, data),

    // Mission update endpoint (Handover 0244b)
    updateMission: (jobId, data) => apiClient.patch(`/api/agent-jobs/${jobId}/mission`, data),

    // Handover 0461d: Simple handover - reset context and get continuation prompt
    // NOTE: Legacy succession endpoints (triggerSuccession, checkSuccessionStatus, initiateHandover)
    // removed in Handover 0700d. Use simpleHandover instead.
    simpleHandover: (jobId) => apiClient.post(`/api/agent-jobs/${jobId}/simple-handover`),
    // Get all executions for a job (succession history)
    getExecutions: (jobId) => apiClient.get(`/api/agent-jobs/${jobId}/executions`),

    // Message and communication endpoints (Handover 0066 - Kanban Dashboard)
    messages: (jobId) => apiClient.get(`/api/agent-jobs/${jobId}/messages`),
    getMessageThread: (jobId) => apiClient.get(`/api/agent-jobs/${jobId}/messages`),
    sendMessage: (jobId, data) =>
      apiClient.post(`/api/agent-jobs/${jobId}/messages`, {
        message: {
          content: data.content,
          to_agent: data.to,
          type: data.type || "direct",
          from_agent: "developer",
        },
      }),
    broadcast: (data) =>
      apiClient.post(`/api/v1/messages/broadcast`, {
        project_id: data.project_id,
        content: data.content,
        priority: data.priority || 'normal',
        from_agent: data.from_agent || 'user',
      }),

  },

  // Organizations (Handover 0424 - gap fix)
  organizations: {
    list: () => apiClient.get('/api/organizations'),
    get: (orgId) => apiClient.get(`/api/organizations/${orgId}`),
    create: (data) => apiClient.post('/api/organizations', data),
    update: (orgId, data) => apiClient.put(`/api/organizations/${orgId}`, data),
    delete: (orgId) => apiClient.delete(`/api/organizations/${orgId}`),
    // Member operations
    listMembers: (orgId) => apiClient.get(`/api/organizations/${orgId}/members`),
    inviteMember: (orgId, data) => apiClient.post(`/api/organizations/${orgId}/members`, data),
    changeMemberRole: (orgId, userId, data) => apiClient.put(`/api/organizations/${orgId}/members/${userId}`, data),
    removeMember: (orgId, userId) => apiClient.delete(`/api/organizations/${orgId}/members/${userId}`),
    transferOwnership: (orgId, data) => apiClient.post(`/api/organizations/${orgId}/transfer`, data),
  },

  // Orchestrator (Multi-Agent Workflow Coordination)
  orchestrator: {
    launchProject: (data) => apiClient.post('/api/agent-jobs/launch-project', data),
  },

  // Prompts (Handover 0119 Phase 1 - Standardized to /api/v1/prompts)
  // Reference: handovers/0119_api_harmonization_backward_compatibility_cleanup.md
  prompts: {
    staging: (projectId, params) =>
      apiClient.get(`/api/v1/prompts/staging/${projectId}`, { params }),
    agentPrompt: (agentJobId) => apiClient.get(`/api/v1/prompts/agent/${agentJobId}`),
    // Handover 0344: CLI mode implementation prompt for orchestrator play button
    implementation: (projectId) => apiClient.get(`/api/v1/prompts/implementation/${projectId}`),
    // Handover 0396: Orchestrator prompt for copy-to-clipboard (Claude Code or Codex/Gemini)
    orchestrator: (tool, projectId) =>
      apiClient.get(`/api/v1/prompts/orchestrator/${tool}`, {
        params: { project_id: projectId },
      }),
  },

  // Downloads
  downloads: {
    // Generic temp download with token
    downloadViaToken: (token, filename) =>
      apiClient.get(`/api/download/temp/${token}/${filename}`, { responseType: 'blob' }),
    // Generate slash commands installation instructions with timed download URL
    generateSlashCommandsInstructions: () =>
      apiClient.post('/api/download/generate-token', null, { params: { content_type: 'slash_commands' } }),
  },

  system: {
    getOrchestratorPrompt: () => apiClient.get('/api/v1/system/orchestrator-prompt'),
    updateOrchestratorPrompt: (content) =>
      apiClient.put('/api/v1/system/orchestrator-prompt', { content }),
    resetOrchestratorPrompt: () => apiClient.post('/api/v1/system/orchestrator-prompt/reset'),
  },

  // Statistics
  stats: {
    getSystem: () => apiClient.get('/api/v1/stats/system'),
    getCallCounts: () => apiClient.get('/api/v1/stats/call-counts'),
  },
}

// Export error handling utilities for use in components (Handover 0480f)
export { parseErrorResponse, getErrorMessage }

export default api
