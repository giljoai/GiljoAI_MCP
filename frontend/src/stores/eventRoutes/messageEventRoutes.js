import { useAgentJobsStore } from '../agentJobsStore'
import { useProjectMessagesStore } from '../projectMessagesStore'
import { useProjectStateStore } from '../projectStateStore'
import { useProjectTabsStore } from '../projectTabs'

function dispatchWindowEvent(name, detail) {
  window.dispatchEvent(new CustomEvent(name, { detail }))
}

/**
 * Message event route definitions.
 */
export const MESSAGE_EVENT_ROUTES = {
  message: { store: 'messages', action: 'handleRealtimeUpdate' }, // legacy
  'message:new': { store: 'messages', action: 'handleRealtimeUpdate' },
  'message:sent': {
    handler: async (payload, { storeRegistry } = {}) => {
      const agentJobsStore = storeRegistry?.agentJobs?.() ?? useAgentJobsStore()
      const projectMessagesStore = storeRegistry?.projectMessages?.() ?? useProjectMessagesStore()
      const projectStateStore = storeRegistry?.projectState?.() ?? useProjectStateStore()
      const projectTabsStore = storeRegistry?.projectTabs?.() ?? useProjectTabsStore()

      agentJobsStore.handleMessageSent?.(payload)
      projectMessagesStore.handleSent?.(payload)
      projectStateStore.handleMessageSent?.(payload)
      projectTabsStore.handleMessageSent?.(payload)

      dispatchWindowEvent('agent:message_sent', payload)
    },
  },
  'message:received': {
    handler: async (payload, { storeRegistry } = {}) => {
      const agentJobsStore = storeRegistry?.agentJobs?.() ?? useAgentJobsStore()
      const projectMessagesStore = storeRegistry?.projectMessages?.() ?? useProjectMessagesStore()
      const projectStateStore = storeRegistry?.projectState?.() ?? useProjectStateStore()
      const projectTabsStore = storeRegistry?.projectTabs?.() ?? useProjectTabsStore()

      agentJobsStore.handleMessageReceived?.(payload)
      projectMessagesStore.handleReceived?.(payload)
      projectStateStore.handleMessageReceived?.(payload)
      projectTabsStore.handleMessageReceived?.(payload)

      dispatchWindowEvent('agent:message_received', payload)
    },
  },
  'message:acknowledged': {
    handler: async (payload, { storeRegistry } = {}) => {
      // Handover 0407: Debug logging to diagnose message counter sync issues
      // eslint-disable-next-line no-console
      console.debug('[websocketEventRouter] message:acknowledged received', {
        agent_id: payload?.agent_id,
        job_id: payload?.job_id,
        from_job_id: payload?.from_job_id,
        message_ids_count: payload?.message_ids?.length || 0,
      })

      const agentJobsStore = storeRegistry?.agentJobs?.() ?? useAgentJobsStore()
      const projectMessagesStore = storeRegistry?.projectMessages?.() ?? useProjectMessagesStore()

      agentJobsStore.handleMessageAcknowledged?.(payload)
      projectMessagesStore.handleAcknowledged?.(payload)

      dispatchWindowEvent('agent:message_acknowledged', payload)
    },
  },
}
