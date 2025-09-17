import axios from 'axios'
import { API_CONFIG } from '@/config/api'

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_CONFIG.REST_API.baseURL,
  timeout: API_CONFIG.REST_API.timeout,
  headers: API_CONFIG.REST_API.headers,
})

// Request interceptor for auth token
apiClient.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized access
      localStorage.removeItem('auth_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

// API Service Methods
export const api = {
  // Projects
  projects: {
    list: (params) => apiClient.get('/api/v1/projects', { params }),
    get: (id) => apiClient.get(`/api/v1/projects/${id}`),
    create: (data) => apiClient.post('/api/v1/projects', data),
    update: (id, data) => apiClient.put(`/api/v1/projects/${id}`, data),
    delete: (id) => apiClient.delete(`/api/v1/projects/${id}`),
    close: (id, summary) => apiClient.delete(`/api/v1/projects/${id}`, { params: { summary } }),
    status: (id) => apiClient.get(`/api/v1/projects/${id}/status`),
  },

  // Agents
  agents: {
    list: (projectId) => apiClient.get('/api/v1/agents', { params: { project_id: projectId } }),
    get: (id) => apiClient.get(`/api/agents/${id}`),
    create: (data) => apiClient.post('/api/v1/agents', data),
    health: (id) => apiClient.get(`/api/agents/${id}/health`),
    assign: (agentName, jobData) => apiClient.post(`/api/agents/${agentName}/assign`, jobData),
    decommission: (id, reason) => apiClient.post(`/api/agents/${id}/decommission`, { reason }),
  },

  // Messages
  messages: {
    list: (params) => apiClient.get('/api/v1/messages', { params }),
    get: (id) => apiClient.get(`/api/messages/${id}`),
    send: (data) => apiClient.post('/api/v1/messages', data),
    acknowledge: (id, agentName) =>
      apiClient.post(`/api/messages/${id}/acknowledge`, { agent_name: agentName }),
    complete: (id, result) => apiClient.post(`/api/messages/${id}/complete`, { result }),
    broadcast: (projectId, content) =>
      apiClient.post('/api/messages/broadcast', { project_id: projectId, content }),
  },

  // Tasks
  tasks: {
    list: (params) => apiClient.get('/api/v1/tasks', { params }),
    get: (id) => apiClient.get(`/api/tasks/${id}`),
    create: (data) => apiClient.post('/api/v1/tasks', data),
    update: (id, data) => apiClient.put(`/api/tasks/${id}`, data),
    delete: (id) => apiClient.delete(`/api/tasks/${id}`),
    changeStatus: (id, status) => apiClient.patch(`/api/tasks/${id}/status`, { status }),
    summary: (productId) =>
      apiClient.get('/api/tasks/summary', { params: { product_id: productId } }),
  },

  // Vision Documents
  vision: {
    get: () => apiClient.get('/api/v1/context/vision'),
    getChunk: (part, maxTokens = 20000) =>
      apiClient.get('/api/v1/context/vision', {
        params: { part, max_tokens: maxTokens },
      }),
    getIndex: () => apiClient.get('/api/v1/context/vision/index'),
  },

  // Context & Discovery
  context: {
    getIndex: (productId) =>
      apiClient.get('/api/v1/context/index', { params: { product_id: productId } }),
    getSection: (documentName, sectionName) =>
      apiClient.get('/api/v1/context/section', {
        params: { document_name: documentName, section_name: sectionName },
      }),
  },

  // Settings & Configuration
  settings: {
    get: () => apiClient.get('/api/v1/config'),
    update: (data) => apiClient.put('/api/v1/config', data),
    getProduct: () => apiClient.get('/api/v1/config/product'),
  },

  // Session Info
  session: {
    info: () => apiClient.get('/api/v1/stats/session'),
    stats: () => apiClient.get('/api/v1/stats'),
  },
}

export default api
