/**
 * notificationRouting.spec.js — FE-9191
 *
 * Closeout-family notifications must deep-link to the project's Implementation
 * (jobs) tab, where the closeout pill and decision surfaces live. Every other
 * notification family keeps its current target (regression map below).
 *
 * Edition scope: Both.
 */
import { describe, it, expect } from 'vitest'
import {
  resolveNotificationRoute,
  projectRouteFor,
  CLOSEOUT_NOTIFICATION_TYPES,
} from './notificationRouting'

describe('notificationRouting — FE-9191 closeout family lands on the jobs tab', () => {
  it('project.pre_launch_workproduct (payload project context) routes to ?tab=jobs', () => {
    const route = resolveNotificationRoute({
      type: 'project.pre_launch_workproduct',
      payload: { project_id: 'p-1', project_name: 'Demo' },
    })
    expect(route).toEqual({
      name: 'ProjectLaunch',
      params: { projectId: 'p-1' },
      query: { tab: 'jobs' },
    })
  })

  it('closeout.approval_required (payload project context) routes to ?tab=jobs', () => {
    const route = resolveNotificationRoute({
      type: 'closeout.approval_required',
      payload: { project_id: 'p-9', approval_id: 'a-1' },
    })
    expect(route).toEqual({
      name: 'ProjectLaunch',
      params: { projectId: 'p-9' },
      query: { tab: 'jobs' },
    })
  })

  it('closeout family with metadata-style project context also routes to ?tab=jobs', () => {
    const route = resolveNotificationRoute({
      type: 'project.pre_launch_workproduct',
      metadata: { project_id: 'p-3' },
    })
    expect(route.query).toEqual({ tab: 'jobs' })
  })

  it('the project-name chip navigation (projectRouteFor) is family-aware too', () => {
    const closeout = projectRouteFor({
      type: 'closeout.approval_required',
      payload: { project_id: 'p-4' },
    })
    expect(closeout.query).toEqual({ tab: 'jobs' })

    const generic = projectRouteFor({
      type: 'project_update',
      metadata: { project_id: 'p-5' },
    })
    expect(generic.query).toBeUndefined()
  })

  it('the closeout family set contains exactly the two closeout notification types', () => {
    expect([...CLOSEOUT_NOTIFICATION_TYPES].sort()).toEqual([
      'closeout.approval_required',
      'project.pre_launch_workproduct',
    ])
  })
})

describe('notificationRouting — regression map: other families keep their targets', () => {
  it('api_key.expiring_soon keeps its Tools connect target', () => {
    const route = resolveNotificationRoute({ type: 'api_key.expiring_soon' })
    expect(route).toEqual({ name: 'Tools', query: { tab: 'connect' } })
  })

  it('a generic project notification keeps ProjectLaunch WITHOUT a tab override', () => {
    const route = resolveNotificationRoute({
      type: 'project_update',
      metadata: { project_id: 'p-2' },
    })
    expect(route).toEqual({ name: 'ProjectLaunch', params: { projectId: 'p-2' } })
    expect(route.query).toBeUndefined()
  })

  it('context_tuning and vision_analysis stay on the current page (no route)', () => {
    expect(resolveNotificationRoute({ type: 'context_tuning', metadata: { project_id: 'p-6' } })).toBeNull()
    expect(resolveNotificationRoute({ type: 'vision_analysis', payload: { project_id: 'p-7' } })).toBeNull()
  })

  it('a notification without project context resolves to no route', () => {
    expect(resolveNotificationRoute({ type: 'system_alert' })).toBeNull()
    expect(projectRouteFor({ type: 'project.pre_launch_workproduct' })).toBeNull()
  })
})
