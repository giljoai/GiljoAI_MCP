import axios from 'axios'
import { API_CONFIG } from '@/config/api'

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_CONFIG.REST_API.baseURL,
  timeout: API_CONFIG.REST_API.timeout,
  headers: API_CONFIG.REST_API.headers,
  withCredentials: true, // CRITICAL: Send cookies with requests for JWT auth
})

// Request interceptor for auth token and tenant key
apiClient.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

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
      // Handle unauthorized access
      // Clear any cached user state
      localStorage.removeItem('auth_token')
      localStorage.removeItem('user')

      // Only redirect to login if not already on the login page
      if (!window.location.pathname.includes('/login') && !originalRequest._retry) {
        // Mark request as retried to prevent infinite loops
        originalRequest._retry = true

        // CRITICAL FIX: Check setup status BEFORE redirecting to login
        // This prevents the bug where fresh installs redirect to /login instead of /setup
        try {
          // Use a separate axios instance to avoid circular dependency
          const setupResponse = await axios.get('/api/setup/status')
          const setupStatus = setupResponse.data

          // If database is NOT initialized, don't redirect to login
          // Let the router handle the redirect to /setup
          if (!setupStatus.database_initialized) {
            console.log('[API] Database not initialized - skipping login redirect')
            return Promise.reject(error)
          }
        } catch (e) {
          // If setup status check fails, assume fresh install (don't redirect)
          console.log('[API] Setup status check failed - assuming fresh install')
          return Promise.reject(error)
        }

        // Setup is complete - proceed with login redirect (existing behavior)
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
      return apiClient.post('/api/v1/products/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
    },
    update: (id, data) => apiClient.put(`/api/v1/products/${id}/`, data),
    delete: (id) => apiClient.delete(`/api/v1/products/${id}/`),
    uploadVision: (id, file) => {
      const formData = new FormData()
      formData.append('vision_file', file)
      return apiClient.post(`/api/v1/products/${id}/upload-vision/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
    },
    getVisionChunks: (id) => apiClient.get(`/api/v1/products/${id}/vision-chunks/`),
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
  },

  // Agents
  agents: {
    list: (projectId) => apiClient.get('/api/v1/agents/', { params: { project_id: projectId } }),
    get: (id) => apiClient.get(`/api/v1/agents/${id}/`),
    create: (data) => apiClient.post('/api/v1/agents/', data),
    health: (id) => apiClient.get(`/api/v1/agents/${id}/health/`),
    assign: (agentName, jobData) => apiClient.post(`/api/v1/agents/${agentName}/assign/`, jobData),
    decommission: (id, reason) => apiClient.post(`/api/v1/agents/${id}/decommission/`, { reason }),
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
  },

  // Vision Documents
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
  },

  // Authentication (JWT via httpOnly cookies)
  auth: {
    login: (username, password) => apiClient.post('/api/auth/login', { username, password }),
    logout: () => apiClient.post('/api/auth/logout'),
    me: () => apiClient.get('/api/auth/me'),
    register: (data) => apiClient.post('/api/auth/register', data),
    changePassword: (data) => apiClient.post('/api/auth/change-password', data),
    listUsers: () => apiClient.get('/api/auth/users'),
    updateUser: (userId, data) => apiClient.put(`/api/auth/users/${userId}`, data),
    deleteUser: (userId) => apiClient.delete(`/api/auth/users/${userId}`),
  },

  // API Key Management
  apiKeys: {
    list: () => apiClient.get('/api/auth/api-keys'),
    create: (name) => apiClient.post('/api/auth/api-keys', { name }),
    delete: (keyId) => apiClient.delete(`/api/auth/api-keys/${keyId}`),
  },
}

export default api
