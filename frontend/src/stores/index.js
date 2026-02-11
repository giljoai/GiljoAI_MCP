import { createPinia } from 'pinia'

export const pinia = createPinia()

// Store modules will be imported here after implementation
export { useProjectStore } from './projects'
export { useAgentStore } from './agents'
export { useMessageStore } from './messages'
export { useTaskStore } from './tasks'
export { useSettingsStore } from './settings'
export { useWebSocketStore } from './websocket'
export { useAgentJobsStore } from './agentJobsStore'

export default pinia
