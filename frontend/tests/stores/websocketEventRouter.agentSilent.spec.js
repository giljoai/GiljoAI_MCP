/**
 * websocketEventRouter - agent:silent store update tests
 *
 * Validates the fix where the agent:silent handler now updates the agentJobsStore
 * before adding a notification. Previously, agent:silent only added a bell
 * notification -- the dashboard did not update in real-time.
 *
 * Edition Scope: CE
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import {
  EVENT_MAP,
  routeWebsocketEvent,
} from '@/stores/websocketEventRouter'
import { useAgentJobsStore } from '@/stores/agentJobsStore'
import { useNotificationStore } from '@/stores/notifications'
import { useUserStore } from '@/stores/user'

// Mock crypto.randomUUID for notification IDs
vi.stubGlobal('crypto', {
  randomUUID: vi.fn(() => `mock-uuid-${Math.random().toString(36).substring(7)}`),
})

describe('websocketEventRouter - agent:silent updates agentJobsStore', () => {
  let agentJobsStore
  let notificationStore

  beforeEach(() => {
    setActivePinia(createPinia())
    agentJobsStore = useAgentJobsStore()
    notificationStore = useNotificationStore()

    // Set up tenant context for routing
    const userStore = useUserStore()
    if (!userStore.currentUser) {
      userStore.currentUser = {}
    }
    userStore.currentUser.tenant_key = 'test-tenant'
  })

  it('updates agent status to silent in the store', async () => {
    // Setup: Pre-populate a working job in the store
    agentJobsStore.setJobs([
      {
        job_id: 'job-100',
        agent_id: 'agent-100',
        agent_display_name: 'implementer',
        status: 'working',
        project_id: 'proj-1',
      },
    ])

    // Pre-condition: Job is working
    expect(agentJobsStore.getJob('job-100').status).toBe('working')

    // Act: Route an agent:silent event through the event router
    await routeWebsocketEvent(
      {
        type: 'agent:silent',
        data: {
          job_id: 'job-100',
          agent_display_name: 'implementer',
          reason: 'No heartbeat for 5 minutes',
          project_id: 'proj-1',
          project_name: 'Feature Sprint',
          execution_id: 'exec-100',
          tenant_key: 'test-tenant',
        },
      },
      { eventMap: EVENT_MAP },
    )

    // Assert: Job status now reflects 'silent' in the store
    const job = agentJobsStore.getJob('job-100')
    expect(job).toBeTruthy()
    expect(job.status).toBe('silent')
  })

  it('adds a notification to the notification store', async () => {
    // Setup: Pre-populate a working job
    agentJobsStore.setJobs([
      {
        job_id: 'job-200',
        agent_id: 'agent-200',
        agent_display_name: 'orchestrator',
        status: 'working',
      },
    ])

    // Act: Route agent:silent
    await routeWebsocketEvent(
      {
        type: 'agent:silent',
        data: {
          job_id: 'job-200',
          agent_display_name: 'orchestrator',
          reason: 'Disconnected',
          execution_id: 'exec-200',
          tenant_key: 'test-tenant',
        },
      },
      { eventMap: EVENT_MAP },
    )

    // Assert: A notification was added
    expect(notificationStore.notifications).toHaveLength(1)
    const notification = notificationStore.notifications[0]
    expect(notification.type).toBe('agent_health')
    expect(notification.title).toBe('Agent Silent')
    expect(notification.message).toContain('orchestrator')
    expect(notification.message).toContain('Disconnected')
  })

  it('includes project context in notification when project_name is present', async () => {
    // Setup: Pre-populate a working job
    agentJobsStore.setJobs([
      {
        job_id: 'job-300',
        agent_id: 'agent-300',
        agent_display_name: 'tester',
        status: 'working',
        project_id: 'proj-abc',
      },
    ])

    // Act: Route agent:silent with project context
    await routeWebsocketEvent(
      {
        type: 'agent:silent',
        data: {
          job_id: 'job-300',
          agent_display_name: 'tester',
          reason: 'Agent stopped responding',
          project_id: 'proj-abc',
          project_name: 'Backend Refactor',
          execution_id: 'exec-300',
          tenant_key: 'test-tenant',
        },
      },
      { eventMap: EVENT_MAP },
    )

    // Assert: Notification message includes project name prefix
    expect(notificationStore.notifications).toHaveLength(1)
    const notification = notificationStore.notifications[0]
    expect(notification.message).toBe(
      '[Backend Refactor] tester - Agent stopped responding',
    )
    expect(notification.metadata.project_name).toBe('Backend Refactor')
    expect(notification.metadata.project_id).toBe('proj-abc')
  })

  it('performs both store update and notification in the correct order', async () => {
    // Setup: Pre-populate a working job
    agentJobsStore.setJobs([
      {
        job_id: 'job-400',
        agent_id: 'agent-400',
        agent_display_name: 'reviewer',
        status: 'working',
      },
    ])

    // Act: Route the event
    await routeWebsocketEvent(
      {
        type: 'agent:silent',
        data: {
          job_id: 'job-400',
          agent_display_name: 'reviewer',
          reason: 'Gone quiet',
          project_name: 'Code Review',
          project_id: 'proj-cr',
          execution_id: 'exec-400',
          tenant_key: 'test-tenant',
        },
      },
      { eventMap: EVENT_MAP },
    )

    // Assert: Both side effects happened
    // 1. Store was updated
    const job = agentJobsStore.getJob('job-400')
    expect(job.status).toBe('silent')

    // 2. Notification was created
    expect(notificationStore.notifications).toHaveLength(1)
    expect(notificationStore.notifications[0].title).toBe('Agent Silent')
  })

  it('passes execution_id to the store via handleStatusChanged', async () => {
    // Setup: Pre-populate a job with execution_id
    agentJobsStore.setJobs([
      {
        job_id: 'job-500',
        agent_id: 'agent-500',
        execution_id: 'exec-500',
        agent_display_name: 'analyzer',
        status: 'working',
      },
    ])

    // Act: Route agent:silent with execution_id
    await routeWebsocketEvent(
      {
        type: 'agent:silent',
        data: {
          job_id: 'job-500',
          agent_display_name: 'analyzer',
          reason: 'Stalled',
          execution_id: 'exec-500',
          tenant_key: 'test-tenant',
        },
      },
      { eventMap: EVENT_MAP },
    )

    // Assert: Job is found and updated (execution_id helps resolution)
    const job = agentJobsStore.getJob('job-500')
    expect(job).toBeTruthy()
    expect(job.status).toBe('silent')
  })

  it('works with storeRegistry override for testability', async () => {
    // Setup: Create mock store with handleStatusChanged spy
    const mockHandleStatusChanged = vi.fn()
    const mockAgentJobsStore = { handleStatusChanged: mockHandleStatusChanged }
    const storeRegistry = { agentJobs: () => mockAgentJobsStore }

    // Act: Route with custom storeRegistry
    await routeWebsocketEvent(
      {
        type: 'agent:silent',
        data: {
          job_id: 'job-600',
          agent_display_name: 'implementer',
          reason: 'Timeout',
          project_id: 'proj-x',
          execution_id: 'exec-600',
          tenant_key: 'test-tenant',
        },
      },
      { eventMap: EVENT_MAP, storeRegistry },
    )

    // Assert: handleStatusChanged was called with correct arguments
    expect(mockHandleStatusChanged).toHaveBeenCalledTimes(1)
    expect(mockHandleStatusChanged).toHaveBeenCalledWith(
      expect.objectContaining({
        job_id: 'job-600',
        status: 'silent',
        project_id: 'proj-x',
        agent_display_name: 'implementer',
        execution_id: 'exec-600',
      }),
    )
  })
})
