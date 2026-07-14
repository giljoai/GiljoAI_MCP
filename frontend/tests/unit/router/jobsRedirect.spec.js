/**
 * Regression: the bare /jobs URL must resolve, not 404.
 *
 * The sidebar "Jobs" link routes to /launch?via=jobs (or /projects/:id?via=jobs
 * when a project is active) — there is no registered /jobs route. A stray
 * bookmark or stale tab on /jobs previously fell through to the NotFound
 * catch-all. A legacy-redirect alias now points /jobs → /launch?via=jobs, the
 * same destination the nav uses (LaunchRedirectView resolves the active project).
 *
 * This asserts the redirect at the route-table layer (the layer the alias lives
 * in), so a future route-table edit that drops or mistargets the alias fails here.
 */

import { describe, it, expect } from 'vitest'
import { createRouter, createMemoryHistory } from 'vue-router'
import { routes } from '@/router'

describe('/jobs legacy-redirect alias', () => {
  it('declares a /jobs route that redirects to /launch?via=jobs', () => {
    const jobs = routes.find((r) => r.path === '/jobs')
    expect(jobs).toBeDefined()
    expect(jobs.redirect).toBe('/launch?via=jobs')
  })

  it('navigating to /jobs lands on the Launch route with via=jobs (not NotFound)', async () => {
    // Build an isolated router from the real route table — no auth guard, no API.
    // String redirects are followed during navigation, not in resolve(), so push.
    const router = createRouter({ history: createMemoryHistory(), routes })
    await router.push('/jobs')
    const current = router.currentRoute.value
    expect(current.name).toBe('Launch')
    expect(current.path).toBe('/launch')
    expect(current.query.via).toBe('jobs')
    expect(current.matched.some((r) => r.name === 'NotFound')).toBe(false)
  })

  it('still routes an unknown URL to NotFound (catch-all intact)', async () => {
    const router = createRouter({ history: createMemoryHistory(), routes })
    await router.push('/this-route-does-not-exist')
    expect(router.currentRoute.value.name).toBe('NotFound')
  })
})
