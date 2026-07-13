/**
 * useChainAutoNav.spec.js — FE-6218 (solo extension: FE-6228)
 *
 * Regression coverage at the failing layer (the store -> nav seam). Simulates the
 * WS events by driving the REAL store handlers, then asserts the active pane
 * auto-navigates to track a headless drive:
 *   - viewed project staging_complete       -> flip to the launch/implement surface
 *   - viewed project implementation_launched -> flip to the jobs pane
 *   - chain advance (currentPid moves)       -> router.replace to the new member + jobs
 * plus the load-bearing anti-hijack guard (a user's own action is NOT yanked, but a
 * headless drive resumes once the window lapses).
 *
 * FE-6228 splits the gate: the two SAME-PROJECT flips carry a SOLO headless run
 * (chainCtx null) too — gated only on the anti-hijack window — while the
 * CROSS-PROJECT advance watcher stays chain-only (inert in solo, never
 * cross-navigates). The "SOLO" describe below covers that new contract.
 *
 * Parallel-safe: own pinia per test, watchers owned by a per-test effectScope that
 * is stopped in afterEach, an injected deterministic clock, no module-level globals.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { ref, effectScope, nextTick } from 'vue'
import { setActivePinia, createPinia } from 'pinia'

import { useProjectStateStore } from '@/stores/projectStateStore'
import { useChainAutoNav, USER_ACTION_GUARD_MS } from './useChainAutoNav'

const stubRouter = () => ({ push: vi.fn(), replace: vi.fn() })

// Minimal chain bundle: useChainAutoNav reads only `currentPid` (+ presence as the
// chain gate). A null value exercises the solo path.
const makeChainCtx = (currentPid) => ({ currentPid, run: { id: 'run-1' } })

describe('useChainAutoNav — FE-6218 live-follow', () => {
  let scope
  let clock

  beforeEach(() => {
    setActivePinia(createPinia())
    scope = effectScope()
    clock = { t: 1_000_000 }
  })

  afterEach(() => scope.stop())

  function build({ chainCtx, projectId, activeTab, router, route }) {
    return scope.run(() =>
      useChainAutoNav({
        chainCtx,
        projectId,
        activeTab,
        router,
        route,
        now: () => clock.t,
      }),
    )
  }

  it('flips to the launch/implement surface when the viewed member reaches staging_complete', async () => {
    const activeTab = ref('jobs')
    build({
      chainCtx: ref(makeChainCtx('p1')),
      projectId: ref('p1'),
      activeTab,
      router: stubRouter(),
      route: { query: { run: 'run-1' } },
    })

    // Simulate the project:staging_complete WS event for the viewed member.
    useProjectStateStore().handleStagingComplete({ project_id: 'p1' })
    await nextTick()

    expect(activeTab.value).toBe('launch')
  })

  it('flips to the jobs pane when the viewed member implementation launches', async () => {
    const activeTab = ref('launch')
    build({
      chainCtx: ref(makeChainCtx('p1')),
      projectId: ref('p1'),
      activeTab,
      router: stubRouter(),
      route: { query: {} },
    })

    // Simulate the project:implementation_launched WS event for the viewed member.
    useProjectStateStore().handleImplementationLaunched({
      project_id: 'p1',
      implementation_launched_at: '2026-06-28T00:00:00Z',
    })
    await nextTick()

    expect(activeTab.value).toBe('jobs')
  })

  it('navigates to the new active member on chain advance, landing on the jobs pane', async () => {
    const activeTab = ref('launch')
    const chainCtx = ref(makeChainCtx('p1'))
    const router = stubRouter()
    build({
      chainCtx,
      projectId: ref('p1'),
      activeTab,
      router,
      route: { query: { run: 'run-1' } },
    })

    // sequence:updated advanced current_index -> chainCtx.currentPid moves to p2.
    chainCtx.value = makeChainCtx('p2')
    await nextTick()

    expect(router.replace).toHaveBeenCalledWith({
      name: 'ProjectLaunch',
      params: { projectId: 'p2' },
      query: { run: 'run-1', tab: 'jobs' },
    })
  })

  it('on advance to the already-viewed member, flips the tab without navigating', async () => {
    const activeTab = ref('launch')
    const chainCtx = ref(makeChainCtx('p1'))
    const router = stubRouter()
    build({
      chainCtx,
      projectId: ref('p2'), // viewing p2 already
      activeTab,
      router,
      route: { query: { run: 'run-1' } },
    })

    chainCtx.value = makeChainCtx('p2') // advance lands on the member we're viewing
    await nextTick()

    expect(activeTab.value).toBe('jobs')
    expect(router.replace).not.toHaveBeenCalled()
  })

  it('ANTI-HIJACK: suppresses the auto-flip within the guard window after a user action', async () => {
    const activeTab = ref('jobs')
    const chainCtx = ref(makeChainCtx('p1'))
    const router = stubRouter()
    const { markUserAction } = build({
      chainCtx,
      projectId: ref('p1'),
      activeTab,
      router,
      route: { query: { run: 'run-1' } },
    })

    markUserAction() // user just clicked something

    // The WS echo of the user's own drive arrives inside the window: NOT yanked.
    useProjectStateStore().handleStagingComplete({ project_id: 'p1' })
    await nextTick()
    expect(activeTab.value).toBe('jobs') // would have been 'launch' without the guard

    // ...and a concurrent advance is suppressed too.
    chainCtx.value = makeChainCtx('p2')
    await nextTick()
    expect(router.replace).not.toHaveBeenCalled()
  })

  it('resumes carrying the user along once the guard window lapses', async () => {
    const activeTab = ref('jobs')
    const { markUserAction } = build({
      chainCtx: ref(makeChainCtx('p1')),
      projectId: ref('p1'),
      activeTab,
      router: stubRouter(),
      route: { query: { run: 'run-1' } },
    })

    markUserAction()
    clock.t += USER_ACTION_GUARD_MS + 1 // window lapses; the headless drive is still running

    useProjectStateStore().handleStagingComplete({ project_id: 'p1' })
    await nextTick()
    expect(activeTab.value).toBe('launch') // carried along again
  })

  // FE-6228: SOLO (chainCtx null) now carries the two SAME-PROJECT pane flips — a
  // solo project driven headlessly should track staging -> launch -> jobs just like
  // a chain — while the cross-project advance watcher stays inert (a solo run has a
  // single project and must never cross-navigate).
  describe('SOLO headless-run follow (chainCtx null) — FE-6228', () => {
    it('flips to the launch surface on staging_complete (no chain, no ?run=)', async () => {
      const activeTab = ref('jobs')
      const router = stubRouter()
      build({
        chainCtx: ref(null),
        projectId: ref('solo-pid'),
        activeTab,
        router,
        route: { query: {} }, // no ?run= — a plain solo project view
      })

      useProjectStateStore().handleStagingComplete({ project_id: 'solo-pid' })
      await nextTick()

      expect(activeTab.value).toBe('launch') // carried, even in solo
      expect(router.replace).not.toHaveBeenCalled() // never cross-navigates in solo
    })

    it('flips to the jobs pane on implementation_launched (no chain, no ?run=)', async () => {
      const activeTab = ref('launch')
      const router = stubRouter()
      build({
        chainCtx: ref(null),
        projectId: ref('solo-pid'),
        activeTab,
        router,
        route: { query: {} },
      })

      useProjectStateStore().handleImplementationLaunched({
        project_id: 'solo-pid',
        implementation_launched_at: '2026-06-28T00:00:00Z',
      })
      await nextTick()

      expect(activeTab.value).toBe('jobs') // carried, even in solo
      expect(router.replace).not.toHaveBeenCalled()
    })

    it('ANTI-HIJACK in solo: the same-project flip is suppressed inside the guard window', async () => {
      const activeTab = ref('jobs')
      const { markUserAction } = build({
        chainCtx: ref(null),
        projectId: ref('solo-pid'),
        activeTab,
        router: stubRouter(),
        route: { query: {} },
      })

      markUserAction() // user just clicked stage/implement on their OWN solo project

      // The WS echo of the user's own action arrives inside the window: NOT yanked.
      useProjectStateStore().handleStagingComplete({ project_id: 'solo-pid' })
      await nextTick()
      expect(activeTab.value).toBe('jobs') // would have been 'launch' without the guard
    })

    it('resumes carrying the solo user once the guard window lapses', async () => {
      const activeTab = ref('jobs')
      const { markUserAction } = build({
        chainCtx: ref(null),
        projectId: ref('solo-pid'),
        activeTab,
        router: stubRouter(),
        route: { query: {} },
      })

      markUserAction()
      clock.t += USER_ACTION_GUARD_MS + 1 // window lapses; the headless solo drive is still running

      useProjectStateStore().handleStagingComplete({ project_id: 'solo-pid' })
      await nextTick()
      expect(activeTab.value).toBe('launch') // carried along again, even in solo
    })

    it('cross-project advance watcher stays INERT in solo (no router.replace ever)', async () => {
      const activeTab = ref('launch')
      const router = stubRouter()
      build({
        chainCtx: ref(null), // solo: no chain context, so currentPid never moves
        projectId: ref('solo-pid'),
        activeTab,
        router,
        // even with a stray ?run= in the URL, solo must not cross-navigate (chainCtx null)
        route: { query: { run: 'run-1' } },
      })

      const projectState = useProjectStateStore()
      projectState.handleStagingComplete({ project_id: 'solo-pid' })
      projectState.handleImplementationLaunched({ project_id: 'solo-pid', implementation_launched_at: 'x' })
      await nextTick()

      expect(router.replace).not.toHaveBeenCalled() // chain-only advance is inert in solo
      expect(router.push).not.toHaveBeenCalled()
    })
  })

  // TSK-6254 / BE-9111: the project:implementation_launched broadcast carries an
  // authoritative source tag ("mcp"|"ui"|absent). "mcp" always follows the headless
  // drive; "ui" and absent BOTH fall through to the per-window anti-hijack window —
  // the clicking window is protected by its own markUserAction(), every other
  // window/surface follows. (BE-9111 narrowed "ui" from the old "never flip anywhere",
  // which stranded the projects-table play button / second-window / view-switch cases.)
  describe('TSK-6254 / BE-9111: payload.source gates the implementation_launched flip', () => {
    it('source="mcp" -> follows the headless drive (flips to jobs)', async () => {
      const activeTab = ref('launch')
      build({
        chainCtx: ref(makeChainCtx('p1')),
        projectId: ref('p1'),
        activeTab,
        router: stubRouter(),
        route: { query: { run: 'run-1' } },
      })

      useProjectStateStore().handleImplementationLaunched({
        project_id: 'p1',
        implementation_launched_at: '2026-06-28T00:00:00Z',
        source: 'mcp',
      })
      await nextTick()

      expect(activeTab.value).toBe('jobs') // headless drive followed
    })

    it('source="ui" + suppression window OPEN (own click) -> does NOT flip', async () => {
      const activeTab = ref('launch')
      const { markUserAction } = build({
        chainCtx: ref(makeChainCtx('p1')),
        projectId: ref('p1'),
        activeTab,
        router: stubRouter(),
        route: { query: { run: 'run-1' } },
      })

      markUserAction() // the clicking window opens its own anti-hijack window

      // The WS echo of that same click lands inside the window: NOT yanked.
      useProjectStateStore().handleImplementationLaunched({
        project_id: 'p1',
        implementation_launched_at: '2026-06-28T00:00:00Z',
        source: 'ui',
      })
      await nextTick()

      expect(activeTab.value).toBe('launch') // own click — stays put
    })

    it('source="ui" + window EXPIRED (other window/surface) -> flips to jobs', async () => {
      const activeTab = ref('launch')
      build({
        chainCtx: ref(makeChainCtx('p1')),
        projectId: ref('p1'),
        activeTab,
        router: stubRouter(),
        route: { query: { run: 'run-1' } },
      })

      // BE-9111: a "ui" launch driven from ANOTHER surface (projects-table play
      // button, a second browser window, a view switch) never called markUserAction()
      // in THIS window, so no suppression window is open — it must follow the drive.
      useProjectStateStore().handleImplementationLaunched({
        project_id: 'p1',
        implementation_launched_at: '2026-06-28T00:00:00Z',
        source: 'ui',
      })
      await nextTick()

      expect(activeTab.value).toBe('jobs') // other surface — carried to jobs
    })

    it('source absent -> falls back to the anti-hijack window (suppressed within it)', async () => {
      const activeTab = ref('launch')
      const { markUserAction } = build({
        chainCtx: ref(makeChainCtx('p1')),
        projectId: ref('p1'),
        activeTab,
        router: stubRouter(),
        route: { query: { run: 'run-1' } },
      })

      markUserAction() // inside the window, untagged launch echo must be ignored

      useProjectStateStore().handleImplementationLaunched({
        project_id: 'p1',
        implementation_launched_at: '2026-06-28T00:00:00Z',
        // no source field — legacy backend
      })
      await nextTick()

      expect(activeTab.value).toBe('launch') // window fallback preserved
    })
  })

  it('RULE-3 guard: advance does NOT cross-navigate when route.query.run is absent', async () => {
    // The user is NOT in the ?run= cockpit (e.g. on /projects list or /roadmap).
    // Even if chainCtx is somehow non-null, the router.replace must not fire.
    const activeTab = ref('launch')
    const chainCtx = ref(makeChainCtx('p1'))
    const router = stubRouter()
    build({
      chainCtx,
      projectId: ref('p1'),
      activeTab,
      router,
      route: { query: {} }, // no ?run= param
    })

    chainCtx.value = makeChainCtx('p2') // chain advance
    await nextTick()

    expect(router.replace).not.toHaveBeenCalled() // guard blocked cross-project nav
    // In-pane tab flip is also skipped because pid !== projectId ('p2' !== 'p1')
  })

  it('ignores a sibling member being driven (only the VIEWED member flips the pane)', async () => {
    const activeTab = ref('jobs')
    build({
      chainCtx: ref(makeChainCtx('p1')),
      projectId: ref('p1'), // viewing p1
      activeTab,
      router: stubRouter(),
      route: { query: { run: 'run-1' } },
    })

    // A different member (p2) reaches staging_complete — must not flip p1's pane.
    useProjectStateStore().handleStagingComplete({ project_id: 'p2' })
    await nextTick()

    expect(activeTab.value).toBe('jobs') // unchanged
  })
})
