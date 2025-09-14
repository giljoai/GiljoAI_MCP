// API Configuration for GiljoAI MCP Dashboard
export const API_CONFIG = {
  REST_API: {
    baseURL: process.env.NODE_ENV === 'production' 
      ? 'http://localhost:6002' 
      : 'http://localhost:6002',
    timeout: 30000,
    headers: {
      'Content-Type': 'application/json'
    }
  },
  WEBSOCKET: {
    url: import.meta.env.VITE_WS_URL || (process.env.NODE_ENV === 'production'
      ? 'ws://localhost:8000'
      : 'ws://localhost:8000'),
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 30000,
    reconnectionAttempts: 10,
    debug: import.meta.env.VITE_WS_DEBUG === 'true' || false
  },
  ENDPOINTS: {
    // Project Management
    projects: '/api/projects',
    project: '/api/projects/:id',
    
    // Agent Management
    agents: '/api/agents',
    agent: '/api/agents/:id',
    agentHealth: '/api/agents/:id/health',
    
    // Messages
    messages: '/api/messages',
    message: '/api/messages/:id',
    acknowledge: '/api/messages/:id/acknowledge',
    
    // Tasks
    tasks: '/api/tasks',
    task: '/api/tasks/:id',
    
    // Vision Documents
    vision: '/api/vision',
    visionChunk: '/api/vision/chunk/:part',
    
    // Configuration
    settings: '/api/settings',
    context: '/api/context'
  }
}

export default API_CONFIG