import { useAgentJobsStore } from '../agentJobsStore'
import { useNotificationStore } from '../notifications'
import { useApprovalsStore } from '../useApprovalsStore'

/**
 * Agent and orchestrator event route definitions.
 *
 * Each entry maps an event type to either:
 * - { store, action } for simple store dispatch
 * - { handler } for multi-store or complex logic
 */
export const AGENT_EVENT_ROUTES = {
  'agent:update': {
    handler: async (payload, { storeRegistry } = {}) => {
      const agentJobsStore = storeRegistry?.agentJobs?.() ?? useAgentJobsStore()

      agentJobsStore.handleUpdated?.(payload)
      agentJobsStore.handleRealtimeUpdate?.(payload)
    },
  },
  'agent:status_changed': {
    handler: async (payload, { storeRegistry } = {}) => {
      const agentJobsStore = storeRegistry?.agentJobs?.() ?? useAgentJobsStore()
      agentJobsStore.handleStatusChanged?.(payload)

      // FE-5017 Phase C: surface user_approval transitions to the inbox store.
      // Backend rides the existing 'agent:status_changed' channel — no new
      // event type — adding `user_approval_id` (on awaiting_user) and
      // `decided_option_id` (on resume) to the payload.
      if (payload?.user_approval_id || payload?.decided_option_id) {
        try {
          const approvalsStore = useApprovalsStore()
          await approvalsStore.handleStatusEvent(payload)
        } catch (err) {
          // Don't break the agent UI if the approvals store hiccups.
          // eslint-disable-next-line no-console
          console.debug('[agentEventRoutes] approvals handleStatusEvent failed:', err?.message)
        }
      }
    },
  },
  'agent:spawn': {
    handler: async (payload, { storeRegistry } = {}) => {
      const agentJobsStore = storeRegistry?.agentJobs?.() ?? useAgentJobsStore()

      const normalized = payload?.agent && typeof payload.agent === 'object'
        ? { ...payload.agent, project_id: payload.project_id, tenant_key: payload.tenant_key }
        : payload

      agentJobsStore.handleCreated?.(normalized)
      agentJobsStore.handleAgentSpawn?.(normalized)
    },
  },
  'agent:created': {
    handler: async (payload, { storeRegistry } = {}) => {
      const agentJobsStore = storeRegistry?.agentJobs?.() ?? useAgentJobsStore()

      const normalized = payload?.agent && typeof payload.agent === 'object'
        ? { ...payload.agent, project_id: payload.project_id, tenant_key: payload.tenant_key }
        : payload

      agentJobsStore.handleCreated?.(normalized)
      agentJobsStore.handleAgentSpawn?.(normalized)
    },
  },
  'agent:complete': {
    handler: async (payload, { storeRegistry } = {}) => {
      const agentJobsStore = storeRegistry?.agentJobs?.() ?? useAgentJobsStore()

      agentJobsStore.handleUpdated?.({ ...payload, status: 'complete' })
      agentJobsStore.handleAgentComplete?.(payload)
    },
  },
  'agent:mission_updated': { store: 'agentJobs', action: 'handleUpdated' },
  'agent:health_recovered': { store: 'agentJobs', action: 'handleHealthRecovered' },
  'agent:health_alert': {
    handler: async (payload) => {
      const agentJobsStore = useAgentJobsStore()
      agentJobsStore.handleHealthAlert?.(payload)

      const {
        health_state,
        agent_display_name,
        issue_description,
        job_id,
        project_name,
        project_id,
        execution_id,
      } = payload

      if (health_state === 'critical' || health_state === 'timeout') {
        // Handover 0259: Include project context in health alert notifications
        const prefix = project_name ? `[${project_name}] ` : ''
        const notificationStore = useNotificationStore()
        notificationStore.addNotification({
          type: 'agent_health',
          title: 'Agent Health Alert',
          message: `${prefix}${agent_display_name} - ${issue_description}`,
          metadata: {
            job_id,
            agent_display_name,
            health_state,
            project_id,
            project_name,
            execution_id,
          },
        })
      }
    },
  },
  // Handover 0491: Replaced agent:auto_failed with agent:silent
  'agent:silent': {
    handler: async (payload, { storeRegistry } = {}) => {
      const { agent_display_name, reason, job_id, project_name, project_id, execution_id } = payload

      // Update agent status in store so dashboard reflects silent state in real-time
      const agentJobsStore = storeRegistry?.agentJobs?.() ?? useAgentJobsStore()
      agentJobsStore.handleStatusChanged({
        job_id,
        status: 'silent',
        project_id,
        agent_display_name,
        execution_id,
      })

      // Handover 0259: Include project context in silent agent notifications
      const prefix = project_name ? `[${project_name}] ` : ''
      const notificationStore = useNotificationStore()
      notificationStore.addNotification({
        type: 'agent_health',
        title: 'Agent Silent',
        message: `${prefix}${agent_display_name} - ${reason || 'Agent stopped communicating'}`,
        metadata: {
          job_id,
          agent_display_name,
          reason,
          project_id,
          project_name,
          execution_id,
        },
      })
    },
  },

  // Handover 0431: Orchestrator prompt generated
  'orchestrator:prompt_generated': {
    handler: async (payload, { storeRegistry } = {}) => {
      const agentJobsStore = storeRegistry?.agentJobs?.() ?? useAgentJobsStore()

      // Handover 0700i: Removed instance_number
      agentJobsStore.handleUpdated?.({
        job_id: payload.orchestrator_id,
        agent_id: payload.agent_id,
        execution_id: payload.execution_id,
        project_id: payload.project_id,
        agent_display_name: 'orchestrator',
        status: 'waiting',
        staged: true,
      })
    },
  },
}
