// API Configuration for GiljoAI MCP Dashboard
export const API_CONFIG = {
  REST_API: {
    baseURL:
      process.env.NODE_ENV === 'production' ? 'http://localhost:6002' : 'http://localhost:6002',
    timeout: 30000,
    headers: {
      'Content-Type': 'application/json',
    },
  },
  WEBSOCKET: {
    url:
      import.meta.env.VITE_WS_URL ||
      (process.env.NODE_ENV === 'production' ? 'ws://localhost:6002' : 'ws://localhost:6002'),
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
