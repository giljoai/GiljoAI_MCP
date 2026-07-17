/**
 * notificationRouting.js — FE-9191
 *
 * Pure route-resolution helpers extracted from NotificationDropdown.vue so the
 * host component and specs import the SAME code (reviewDispatch.js precedent).
 *
 * Edition scope: Both.
 */

/**
 * IMP-5037a: client-side type → named route mapping. The server does NOT
 * provide cta_route in the payload (5037b concern); all navigation is
 * resolved here by notification type.
 */
export const TYPE_ROUTE_MAP = {
  // api_key.expiring_soon → Tools connect tab (ApiKeyManager lives there)
  'api_key.expiring_soon': () => ({ name: 'Tools', query: { tab: 'connect' } }),
}

/**
 * Handover 0831 / 0842d: these notification types keep the user on the
 * current page — clicking them must not navigate anywhere.
 */
const STAY_ON_PAGE_TYPES = new Set(['context_tuning', 'vision_analysis'])

/**
 * FE-9191: closeout-family notifications land on the project's Implementation
 * (jobs) tab — the closeout pill, Review project button, and decision surfaces
 * live there, not on the Launch tab. The bare project route otherwise falls to
 * ProjectTabs' generic default tab ('launch'), which is deliberate for every
 * other family, so the retarget is scoped per notification type here.
 */
export const CLOSEOUT_NOTIFICATION_TYPES = new Set([
  'project.pre_launch_workproduct', // BE-9085: closed-out-without-launch alarm
  'closeout.approval_required', // BE-9153: HITL closeout gate approval
])

/**
 * The project id a notification points at. Handover 0259 rows carry it in
 * metadata.project_id; structured-payload rows (BE-9085, TSK-9090) carry it
 * in payload.project_id. Read either so both deep-link to the project.
 */
export const projectIdOf = (n) => n?.metadata?.project_id ?? n?.payload?.project_id

/**
 * Project deep-link for a notification, closeout-family-aware.
 * Returns null when the notification carries no project context.
 */
export function projectRouteFor(notification) {
  const projectId = projectIdOf(notification)
  if (!projectId) return null
  const route = { name: 'ProjectLaunch', params: { projectId } }
  if (CLOSEOUT_NOTIFICATION_TYPES.has(notification?.type)) {
    route.query = { tab: 'jobs' }
  }
  return route
}

/**
 * Full click resolution: stay-on-page carve-outs first, then the explicit
 * type → route map, then the project-context fallback. Returns null when the
 * click should not navigate.
 */
export function resolveNotificationRoute(notification) {
  if (STAY_ON_PAGE_TYPES.has(notification?.type)) return null
  const routeFactory = TYPE_ROUTE_MAP[notification?.type]
  if (routeFactory) return routeFactory(notification)
  return projectRouteFor(notification)
}
