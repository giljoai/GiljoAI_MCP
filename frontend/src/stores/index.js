import { createPinia } from 'pinia'

export const pinia = createPinia()

// Store modules will be imported here after implementation
export { useProjectStore } from './projects'
export { useAgentJobsStore, useAgentJobsStore as useAgentStore } from './agentJobsStore'
export { useMessageStore } from './messages'
export { useTaskStore } from './tasks'
export { useSettingsStore } from './settings'
export { useWebSocketStore } from './websocket'

export default pinia
