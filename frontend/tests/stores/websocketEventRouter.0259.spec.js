/**
 * Tests for Handover 0259: Health alert project context in WebSocket event router.
 *
 * Verifies that:
 * 1. agent:health_alert notification message includes [ProjectName] prefix
 * 2. agent:health_alert notification falls back to old format without project_name
 * 3. agent:health_alert notification metadata includes project_id, project_name, execution_id
 * 4. agent:silent notification message includes [ProjectName] prefix
 * 5. agent:silent notification falls back without project_name
 * 6. agent:silent notification metadata includes project_id, project_name, execution_id
 *
 * Edition Scope: CE
 */

import { describe, expect, it, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import {
  EVENT_MAP,
  routeWebsocketEvent,
} from '@/stores/websocketEventRouter'
import { useNotificationStore } from '@/stores/notifications'
import { useUserStore } from '@/stores/user'

// Mock crypto.randomUUID for notification IDs
vi.stubGlobal('crypto', {
  randomUUID: vi.fn(() => `mock-uuid-${Math.random().toString(36).substring(7)}`),
})

describe('websocketEventRouter - agent:health_alert project context (Handover 0259)', () => {
  let notificationStore

  beforeEach(() => {
    setActivePinia(createPinia())
    notificationStore = useNotificationStore()

    const userStore = useUserStore()
    if (!userStore.currentUser) {
      userStore.currentUser = {}
    }
    userStore.currentUser.tenant_key = 'test-tenant'
  })

  describe('agent:health_alert with project context', () => {
    it('notification message includes project name prefix for critical alerts', async () => {
      await routeWebsocketEvent(
        {
          type: 'agent:health_alert',
          data: {
            health_state: 'critical',
            agent_display_name: 'implementer',
            issue_description: 'No progress for 20 minutes',
            job_id: 'job-100',
            project_name: 'MyProject',
            project_id: 'proj-abc',
            execution_id: 'exec-100',
            tenant_key: 'test-tenant',
          },
        },
        { eventMap: EVENT_MAP },
      )

      expect(notificationStore.notifications).toHaveLength(1)
      const notification = notificationStore.notifications[0]
      expect(notification.message).toBe('[MyProject] implementer - No progress for 20 minutes')
    })

    it('notification message includes project name prefix for timeout alerts', async () => {
      await routeWebsocketEvent(
        {
          type: 'agent:health_alert',
          data: {
            health_state: 'timeout',
            agent_display_name: 'orchestrator',
            issue_description: 'Job never acknowledged',
            job_id: 'job-200',
            project_name: 'Backend Refactor',
            project_id: 'proj-def',
            execution_id: 'exec-200',
            tenant_key: 'test-tenant',
          },
        },
        { eventMap: EVENT_MAP },
      )

      expect(notificationStore.notifications).toHaveLength(1)
      const notification = notificationStore.notifications[0]
      expect(notification.message).toBe('[Backend Refactor] orchestrator - Job never acknowledged')
    })

    it('notification message falls back to format without brackets when project_name is missing', async () => {
      await routeWebsocketEvent(
        {
          type: 'agent:health_alert',
          data: {
            health_state: 'critical',
            agent_display_name: 'implementer',
            issue_description: 'Stalled execution',
            job_id: 'job-orphan',
            project_id: '',
            execution_id: 'exec-orphan',
            tenant_key: 'test-tenant',
          },
        },
        { eventMap: EVENT_MAP },
      )

      expect(notificationStore.notifications).toHaveLength(1)
      const notification = notificationStore.notifications[0]
      expect(notification.message).toBe('implementer - Stalled execution')
      expect(notification.message).not.toContain('[')
    })

    it('notification message falls back when project_name is empty string', async () => {
      await routeWebsocketEvent(
        {
          type: 'agent:health_alert',
          data: {
            health_state: 'critical',
            agent_display_name: 'reviewer',
            issue_description: 'No heartbeat',
            job_id: 'job-300',
            project_name: '',
            project_id: '',
            execution_id: 'exec-300',
            tenant_key: 'test-tenant',
          },
        },
        { eventMap: EVENT_MAP },
      )

      expect(notificationStore.notifications).toHaveLength(1)
      const notification = notificationStore.notifications[0]
      expect(notification.message).toBe('reviewer - No heartbeat')
    })

    it('notification metadata includes project_id, project_name, and execution_id', async () => {
      await routeWebsocketEvent(
        {
          type: 'agent:health_alert',
          data: {
            health_state: 'critical',
            agent_display_name: 'implementer',
            issue_description: 'Stalled',
            job_id: 'job-400',
            project_name: 'Feature Sprint',
            project_id: 'proj-xyz',
            execution_id: 'exec-400',
            tenant_key: 'test-tenant',
          },
        },
        { eventMap: EVENT_MAP },
      )

      expect(notificationStore.notifications).toHaveLength(1)
      const { metadata } = notificationStore.notifications[0]
      expect(metadata.project_id).toBe('proj-xyz')
      expect(metadata.project_name).toBe('Feature Sprint')
      expect(metadata.execution_id).toBe('exec-400')
      expect(metadata.job_id).toBe('job-400')
      expect(metadata.agent_display_name).toBe('implementer')
      expect(metadata.health_state).toBe('critical')
    })

    it('does not create notification for warning-level health alerts', async () => {
      await routeWebsocketEvent(
        {
          type: 'agent:health_alert',
          data: {
            health_state: 'warning',
            agent_display_name: 'implementer',
            issue_description: 'Slow progress',
            job_id: 'job-500',
            project_name: 'Test Project',
            project_id: 'proj-warn',
            execution_id: 'exec-500',
            tenant_key: 'test-tenant',
          },
        },
        { eventMap: EVENT_MAP },
      )

      expect(notificationStore.notifications).toHaveLength(0)
    })

    it('notification type is agent_health and title is Agent Health Alert', async () => {
      await routeWebsocketEvent(
        {
          type: 'agent:health_alert',
          data: {
            health_state: 'critical',
            agent_display_name: 'tester',
            issue_description: 'Timeout',
            job_id: 'job-600',
            project_name: 'QA Sprint',
            project_id: 'proj-qa',
            execution_id: 'exec-600',
            tenant_key: 'test-tenant',
          },
        },
        { eventMap: EVENT_MAP },
      )

      const notification = notificationStore.notifications[0]
      expect(notification.type).toBe('agent_health')
      expect(notification.title).toBe('Agent Health Alert')
    })
  })

  describe('agent:silent with project context', () => {
    it('notification message includes project name prefix', async () => {
      await routeWebsocketEvent(
        {
          type: 'agent:silent',
          data: {
            agent_display_name: 'implementer',
            reason: 'Agent stopped responding',
            job_id: 'job-s100',
            project_name: 'Silent Project',
            project_id: 'proj-s1',
            execution_id: 'exec-s100',
            tenant_key: 'test-tenant',
          },
        },
        { eventMap: EVENT_MAP },
      )

      expect(notificationStore.notifications).toHaveLength(1)
      const notification = notificationStore.notifications[0]
      expect(notification.message).toBe('[Silent Project] implementer - Agent stopped responding')
    })

    it('notification message falls back without project_name', async () => {
      await routeWebsocketEvent(
        {
          type: 'agent:silent',
          data: {
            agent_display_name: 'orchestrator',
            reason: 'Disconnected',
            job_id: 'job-s200',
            execution_id: 'exec-s200',
            tenant_key: 'test-tenant',
          },
        },
        { eventMap: EVENT_MAP },
      )

      expect(notificationStore.notifications).toHaveLength(1)
      const notification = notificationStore.notifications[0]
      expect(notification.message).toBe('orchestrator - Disconnected')
      expect(notification.message).not.toContain('[')
    })

    it('notification uses default reason when reason is missing', async () => {
      await routeWebsocketEvent(
        {
          type: 'agent:silent',
          data: {
            agent_display_name: 'reviewer',
            job_id: 'job-s300',
            project_name: 'Review Sprint',
            project_id: 'proj-s3',
            execution_id: 'exec-s300',
            tenant_key: 'test-tenant',
          },
        },
        { eventMap: EVENT_MAP },
      )

      expect(notificationStore.notifications).toHaveLength(1)
      const notification = notificationStore.notifications[0]
      expect(notification.message).toBe('[Review Sprint] reviewer - Agent stopped communicating')
    })

    it('notification metadata includes project_id, project_name, and execution_id', async () => {
      await routeWebsocketEvent(
        {
          type: 'agent:silent',
          data: {
            agent_display_name: 'implementer',
            reason: 'Timeout detected',
            job_id: 'job-s400',
            project_name: 'API Rewrite',
            project_id: 'proj-s4',
            execution_id: 'exec-s400',
            tenant_key: 'test-tenant',
          },
        },
        { eventMap: EVENT_MAP },
      )

      expect(notificationStore.notifications).toHaveLength(1)
      const { metadata } = notificationStore.notifications[0]
      expect(metadata.project_id).toBe('proj-s4')
      expect(metadata.project_name).toBe('API Rewrite')
      expect(metadata.execution_id).toBe('exec-s400')
      expect(metadata.job_id).toBe('job-s400')
      expect(metadata.agent_display_name).toBe('implementer')
      expect(metadata.reason).toBe('Timeout detected')
    })

    it('notification type is agent_health and title is Agent Silent', async () => {
      await routeWebsocketEvent(
        {
          type: 'agent:silent',
          data: {
            agent_display_name: 'tester',
            reason: 'Gone quiet',
            job_id: 'job-s500',
            project_name: 'Test Sprint',
            project_id: 'proj-s5',
            execution_id: 'exec-s500',
            tenant_key: 'test-tenant',
          },
        },
        { eventMap: EVENT_MAP },
      )

      const notification = notificationStore.notifications[0]
      expect(notification.type).toBe('agent_health')
      expect(notification.title).toBe('Agent Silent')
    })
  })
})
