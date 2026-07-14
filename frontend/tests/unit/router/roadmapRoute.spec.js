/**
 * FE-6022b: the /roadmap route is registered statically (ADR-005 — before
 * createRouter), lazy-loaded, and shows in the nav. Asserted at the route-table
 * layer so a future edit that drops or mistargets it fails here.
 *
 * Edition Scope: CE
 */
import { describe, it, expect } from 'vitest'
import { createRouter, createMemoryHistory } from 'vue-router'
import { routes } from '@/router'

describe('/roadmap route (FE-6022b)', () => {
  it('declares a lazy-loaded Roadmap route with the map-marker-path icon', () => {
    const roadmap = routes.find((r) => r.path === '/roadmap')
    expect(roadmap).toBeDefined()
    expect(roadmap.name).toBe('Roadmap')
    // Lazy-loaded: the component is a function (dynamic import), not an object.
    expect(typeof roadmap.component).toBe('function')
    expect(roadmap.meta.icon).toBe('mdi-map-marker-path')
    expect(roadmap.meta.requiresAuth).toBe(true)
  })

  it('navigating to /roadmap resolves to the Roadmap route (not NotFound)', async () => {
    const router = createRouter({ history: createMemoryHistory(), routes })
    await router.push('/roadmap')
    expect(router.currentRoute.value.name).toBe('Roadmap')
    expect(router.currentRoute.value.matched.some((r) => r.name === 'NotFound')).toBe(false)
  })
})
