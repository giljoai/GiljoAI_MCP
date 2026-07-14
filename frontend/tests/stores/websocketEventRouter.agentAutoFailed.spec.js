/**
 * websocketEventRouter - agent:auto_failed store update + notification tests
 *
 * FE-9151 (P3): the health monitor emits agent:auto_failed live (abandon past
 * ceiling -> 'decommissioned'; timeout + auto_fail_on_timeout -> 'silent') but
 * the frontend had no route for it, so routeWebsocketEvent silently dropped it
 * and the user saw nothing. This wires it up: add a bell notification.
 *
 * FE-9151-FIX (option B): the handler is BELL-ONLY by design. It must NOT write
 * any status into agentJobsStore. 'failed' is not a recognized display status
 * (statusConfig.js has no entry — it would render as gray "Unknown"), and
 * writing it would mask the backend's real status ('decommissioned' or
 * 'silent'), which arrives via the existing agent:status_changed path and has a
 * proper display config. So these tests assert the handler leaves the store
 * status untouched and never calls handleStatusChanged.
 *
 * Backend payload (api/websocket.py:broadcast_agent_auto_failed) carries only
 * { tenant_key, job_id, agent_display_name, reason, auto_failed } -- no
 * project_id / project_name / execution_id -- so the handler must degrade
 * gracefully when project context is absent.
 *
 * Edition Scope: CE
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { EVENT_MAP, routeWebsocketEvent } from '@/stores/websocketEventRouter'
import { useAgentJobsStore } from '@/stores/agentJobsStore'
import { useNotificationStore } from '@/stores/notifications'
import { useUserStore } from '@/stores/user'

// Mock crypto.randomUUID for notification IDs
vi.stubGlobal('crypto', {
  randomUUID: vi.fn(() => `mock-uuid-${Math.random().toString(36).substring(7)}`),
})

describe('websocketEventRouter - agent:auto_failed', () => {
  let agentJobsStore
  let notificationStore

  beforeEach(() => {
    setActivePinia(createPinia())
    agentJobsStore = useAgentJobsStore()
    notificationStore = useNotificationStore()

    const userStore = useUserStore()
    if (!userStore.currentUser) {
      userStore.currentUser = {}
    }
    userStore.currentUser.tenant_key = 'test-tenant'
  })

  it('does NOT write any status into the store (bell-only by design)', async () => {
    agentJobsStore.setJobs([
      {
        job_id: 'job-100',
        agent_id: 'agent-100',
        agent_display_name: 'implementer',
        status: 'working',
      },
    ])
    expect(agentJobsStore.getJob('job-100').status).toBe('working')

    await routeWebsocketEvent(
      {
        type: 'agent:auto_failed',
        data: {
          job_id: 'job-100',
          agent_display_name: 'implementer',
          reason: 'Abandoned 45m — auto-decommissioned',
          auto_failed: true,
          tenant_key: 'test-tenant',
        },
      },
      { eventMap: EVENT_MAP },
    )

    // The handler must NOT flip the store status to the unrecognized 'failed'
    // value — the card's real status comes from the backend via
    // agent:status_changed ('decommissioned'/'silent'). Status stays untouched.
    const job = agentJobsStore.getJob('job-100')
    expect(job).toBeTruthy()
    expect(job.status).toBe('working')
  })

  it('adds an Agent Auto-Failed notification with the reason', async () => {
    agentJobsStore.setJobs([
      {
        job_id: 'job-200',
        agent_id: 'agent-200',
        agent_display_name: 'orchestrator',
        status: 'working',
      },
    ])

    await routeWebsocketEvent(
      {
        type: 'agent:auto_failed',
        data: {
          job_id: 'job-200',
          agent_display_name: 'orchestrator',
          reason: 'Connection timeout',
          auto_failed: true,
          tenant_key: 'test-tenant',
        },
      },
      { eventMap: EVENT_MAP },
    )

    expect(notificationStore.notifications).toHaveLength(1)
    const notification = notificationStore.notifications[0]
    expect(notification.type).toBe('agent_health')
    expect(notification.title).toBe('Agent Auto-Failed')
    expect(notification.message).toContain('orchestrator')
    expect(notification.message).toContain('Connection timeout')
  })

  it('degrades gracefully with no project context (real backend payload shape)', async () => {
    agentJobsStore.setJobs([
      {
        job_id: 'job-300',
        agent_id: 'agent-300',
        agent_display_name: 'tester',
        status: 'working',
      },
    ])

    await routeWebsocketEvent(
      {
        type: 'agent:auto_failed',
        data: {
          job_id: 'job-300',
          agent_display_name: 'tester',
          reason: 'Agent stopped responding',
          auto_failed: true,
          tenant_key: 'test-tenant',
        },
      },
      { eventMap: EVENT_MAP },
    )

    expect(notificationStore.notifications).toHaveLength(1)
    // No project_name -> no bracketed prefix
    expect(notificationStore.notifications[0].message).toBe(
      'tester - Agent stopped responding',
    )
  })

  it('includes a project prefix when project_name is present', async () => {
    agentJobsStore.setJobs([
      {
        job_id: 'job-350',
        agent_id: 'agent-350',
        agent_display_name: 'analyzer',
        status: 'working',
      },
    ])

    await routeWebsocketEvent(
      {
        type: 'agent:auto_failed',
        data: {
          job_id: 'job-350',
          agent_display_name: 'analyzer',
          reason: 'Stalled',
          project_name: 'Backend Refactor',
          project_id: 'proj-abc',
          auto_failed: true,
          tenant_key: 'test-tenant',
        },
      },
      { eventMap: EVENT_MAP },
    )

    expect(notificationStore.notifications[0].message).toBe(
      '[Backend Refactor] analyzer - Stalled',
    )
  })

  it('never calls handleStatusChanged (no store status write)', async () => {
    const mockHandleStatusChanged = vi.fn()
    const mockAgentJobsStore = { handleStatusChanged: mockHandleStatusChanged }
    const storeRegistry = { agentJobs: () => mockAgentJobsStore }

    await routeWebsocketEvent(
      {
        type: 'agent:auto_failed',
        data: {
          job_id: 'job-600',
          agent_display_name: 'reviewer',
          reason: 'Timeout',
          auto_failed: true,
          tenant_key: 'test-tenant',
        },
      },
      { eventMap: EVENT_MAP, storeRegistry },
    )

    expect(mockHandleStatusChanged).not.toHaveBeenCalled()
  })
})
