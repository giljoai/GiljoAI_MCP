/**
 * FE-6061 regression — projectStateStore.setProject monotonic-flag clobber.
 *
 * Root cause: `setProject` normalizes the incoming entity with
 * `normalizeProjectState`, which derives boolean flags ONLY from the entity's
 * own fields (`staging_status`, `implementation_launched_at`, …). It then calls
 * `immutableObjectPatch(previous, normalized)` which applies normalized OVER
 * previous — meaning a normalized value of `false` overwrites a previously
 * WS-set `true`, even though the WS signal is the authoritative real-time source
 * and the entity data is simply the most recently fetched snapshot.
 *
 * This produces two observable breakages:
 *
 * 1. **stagingComplete clobber**: if `setStagingComplete(pid, true)` was
 *    called (e.g. because messages were loaded and exist, signalling that an
 *    orchestrator previously contacted), and `setProject` is then called with
 *    an entity whose `staging_status='staged'` (e.g. after Re-Stage + new
 *    Stage click), `normalizeProjectState` computes `stagingComplete=false`
 *    and `immutableObjectPatch` clobbers the previously-set `true` back to
 *    `false`.  `hasActiveOrchestrator` then reads `false` — correct for the
 *    staged state — but `canRestage` also reads `false`, so the Stage button
 *    correctly enables.  The REAL breakage is the mirror: stagingComplete is
 *    now incorrect for a project that IS orchestrated.
 *
 * 2. **implementationLaunched clobber (the list-wire clobber bug, #32)**: if the
 *    backend's list wire returns `implementation_launched_at=null` (hardcoded
 *    in crud.py line 333), seeding the store from a list-wire entity wipes
 *    `implementationLaunched=true` (set correctly by
 *    `handleImplementationLaunched`) back to `false`.  This converts a
 *    project that has already launched implementation (button should be
 *    permanently disabled) into one that appears re-stageable:
 *      - `canRestage = stagingComplete && !implementationLaunched = true`
 *      - `stageButtonText = 'Re-Stage'`  (wrong — user sees wrong action)
 *      - Click routes to `handleRestageProject()` (POST /restage), NOT
 *        `handleStageProject()` (GET /staging) — so no clipboard copy and
 *        no GET /staging fires, matching the live symptom.
 *
 * Fix: `setProject` must use forward-OR semantics for monotonic boolean flags
 * (`stagingComplete`, `implementationLaunched`, `implementationLaunchedAt`) —
 * once set true by a WS event, they must not revert to false via a stale
 * entity snapshot.  Explicit store actions (restageProject, unstageProject)
 * still clear them via `upsertProjectState`, which bypasses this guard.
 *
 * Edition Scope: Both (shared frontend).
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useProjectStateStore } from '@/stores/projectStateStore'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** A minimal full-GET entity as returned by the single-project detail endpoint */
function makeFullEntity(overrides = {}) {
  return {
    id: 'proj-fe6061',
    project_id: 'proj-fe6061',
    name: 'FE-6061 test project',
    status: 'active',
    staging_status: 'staging_complete',
    implementation_launched_at: '2026-06-14T10:00:00Z',
    execution_mode: 'multi_terminal',
    mission: 'some mission',
    ...overrides,
  }
}

/** A list-wire entity as returned by GET /projects (crud.py line 333 hardcodes impl_launched_at=null) */
function makeListWireEntity(overrides = {}) {
  return {
    id: 'proj-fe6061',
    name: 'FE-6061 test project',
    status: 'active',
    staging_status: 'staging_complete',
    implementation_launched_at: null,   // hardcoded null in crud.py — THE BUG SOURCE
    execution_mode: 'multi_terminal',
    ...overrides,
  }
}

// ---------------------------------------------------------------------------
// Test suites
// ---------------------------------------------------------------------------

describe('FE-6061 — projectStateStore.setProject monotonic-flag clobber (regression)', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useProjectStateStore()
  })

  // =========================================================================
  // Case 1: implementationLaunched clobber via list-wire null
  // =========================================================================
  describe('implementationLaunched clobber', () => {
    it('setProject with full entity seeds implementationLaunched=true correctly', () => {
      const fullEntity = makeFullEntity()
      store.setProject(fullEntity)
      const state = store.getProjectState('proj-fe6061')
      expect(state.implementationLaunched).toBe(true)
      expect(state.implementationLaunchedAt).toBe('2026-06-14T10:00:00Z')
    })

    it('REGRESSION: setProject with list-wire entity (impl_launched_at=null) must NOT clobber implementationLaunched set by WS event', () => {
      // Step 1: WS event arrives — implementation launched signal
      store.handleImplementationLaunched({
        project_id: 'proj-fe6061',
        implementation_launched_at: '2026-06-14T10:00:00Z',
      })
      expect(store.getProjectState('proj-fe6061').implementationLaunched).toBe(true)

      // Step 2: list-wire entity arrives via setProject (implementation_launched_at=null
      // because crud.py line 333 hardcodes it). This should NOT clobber the WS-set flag.
      const listEntity = makeListWireEntity()
      store.setProject(listEntity)

      const state = store.getProjectState('proj-fe6061')
      // FAILS before fix: immutableObjectPatch clobbers implementationLaunched to false
      expect(state.implementationLaunched).toBe(true)
      expect(state.implementationLaunchedAt).toBe('2026-06-14T10:00:00Z')
    })

    it('REGRESSION: setProject with list-wire null must not unlock a post-launch stage button', () => {
      // Scenario: project is staging_complete + implementation_launched.
      // The stage button should be permanently disabled.
      // If setProject clobbers implementationLaunched to false, canRestage fires
      // and button routes to handleRestageProject (wrong action — no GET /staging).
      store.setProject(makeFullEntity())   // correct seed: impl launched
      let state = store.getProjectState('proj-fe6061')
      expect(state.stagingComplete).toBe(true)
      expect(state.implementationLaunched).toBe(true)

      // Now simulate a list-wire re-seed (e.g. reconnect resync → refreshList
      // → projects.value updated → props.project changes → setProject re-called
      // from loadProjectData or refetchProject with the list row).
      store.setProject(makeListWireEntity())   // list wire: impl_launched_at=null

      state = store.getProjectState('proj-fe6061')
      // Before fix: implementationLaunched=false → canRestage=true → wrong verb
      // After fix:  implementationLaunched=true  → canRestage=false → button disabled
      expect(state.implementationLaunched).toBe(true)
    })
  })

  // =========================================================================
  // Case 2: stagingComplete clobber
  // =========================================================================
  describe('stagingComplete clobber', () => {
    it('REGRESSION: setProject with staging_status=staged entity must NOT clobber stagingComplete set by setStagingComplete', () => {
      // Step 1: setStagingComplete called (e.g. loadMessages found existing messages
      // signalling a prior orchestrator run).
      store.setStagingComplete('proj-fe6061', true)
      expect(store.getProjectState('proj-fe6061').stagingComplete).toBe(true)

      // Step 2: setProject called with a 'staged' entity (staging_status='staged').
      // normalizeProjectState computes stagingComplete=false because
      // 'staged' !== 'staging_complete'. immutableObjectPatch then clobbers it.
      store.setProject(makeListWireEntity({ staging_status: 'staged', implementation_launched_at: null }))

      const state = store.getProjectState('proj-fe6061')
      // Before fix: stagingComplete=false  ← clobber
      // After fix:  stagingComplete=true   ← preserved
      expect(state.stagingComplete).toBe(true)
    })

    it('stagingComplete preserved when setProject is called after handleStagingComplete', () => {
      store.handleStagingComplete({ project_id: 'proj-fe6061' })
      expect(store.getProjectState('proj-fe6061').stagingComplete).toBe(true)

      // setProject with a staging_complete entity preserves it (this already passes)
      store.setProject(makeFullEntity({ staging_status: 'staging_complete', implementation_launched_at: null }))
      expect(store.getProjectState('proj-fe6061').stagingComplete).toBe(true)

      // setProject with a 'staged' entity must also preserve it (this is the regression)
      store.setProject(makeListWireEntity({ staging_status: 'staged' }))
      expect(store.getProjectState('proj-fe6061').stagingComplete).toBe(true)
    })
  })

  // =========================================================================
  // Case 3: explicit clear (restage/unstage) must still work
  // =========================================================================
  describe('explicit clear via upsertProjectState still works', () => {
    it('restageProject clears implementationLaunched and stagingComplete despite forward-OR guard', async () => {
      // Seed with full lifecycle state
      store.setProject(makeFullEntity())
      expect(store.getProjectState('proj-fe6061').implementationLaunched).toBe(true)
      expect(store.getProjectState('proj-fe6061').stagingComplete).toBe(true)

      // Explicit patch via upsertProjectState (what restageProject calls internally)
      // This bypasses the setProject forward-OR guard — direct upsertProjectState
      // should still clear these fields (so Re-Stage works correctly).
      // We call the internal upsert path indirectly via setStagingComplete(false):
      store.setStagingComplete('proj-fe6061', false)
      store.setImplementationLaunched('proj-fe6061', null)

      const state = store.getProjectState('proj-fe6061')
      expect(state.stagingComplete).toBe(false)
      expect(state.implementationLaunched).toBe(false)
      expect(state.implementationLaunchedAt).toBeNull()
    })

    it('after explicit clear, setProject with null impl_launched_at entity keeps clear state', () => {
      // Simulate Re-Stage cycle:
      // 1. Full lifecycle state
      store.setProject(makeFullEntity())
      expect(store.getProjectState('proj-fe6061').implementationLaunched).toBe(true)

      // 2. Explicit clear (what restageProject does)
      store.setImplementationLaunched('proj-fe6061', null)
      store.setStagingComplete('proj-fe6061', false)

      // 3. setProject called with staged entity (after Re-Stage, backend returns staged)
      store.setProject(makeListWireEntity({ staging_status: 'staged', implementation_launched_at: null }))

      const state = store.getProjectState('proj-fe6061')
      // Should stay cleared — both previous and normalized are false, forward-OR gives false
      expect(state.implementationLaunched).toBe(false)
      expect(state.stagingComplete).toBe(false)
      // isStaged should be true (from staging_status='staged')
      expect(state.isStaged).toBe(true)
    })
  })

  // =========================================================================
  // Case 4: normal setProject flows still work
  // =========================================================================
  describe('normal setProject flows are unaffected', () => {
    it('setProject on a fresh project (no previous state) seeds all fields correctly', () => {
      store.setProject(makeFullEntity())
      const state = store.getProjectState('proj-fe6061')
      expect(state.stagingComplete).toBe(true)
      expect(state.implementationLaunched).toBe(true)
      expect(state.isStaged).toBe(false)
      expect(state.isStaging).toBe(false)
    })

    it('setProject with staging_status=staged correctly sets isStaged=true', () => {
      store.setProject(makeListWireEntity({ staging_status: 'staged', implementation_launched_at: null }))
      const state = store.getProjectState('proj-fe6061')
      expect(state.isStaged).toBe(true)
      expect(state.isStaging).toBe(false)
      expect(state.stagingComplete).toBe(false)
    })

    it('setProject with staging_status=null clears staging flags', () => {
      store.setProject(makeFullEntity({ staging_status: null, implementation_launched_at: null }))
      const state = store.getProjectState('proj-fe6061')
      expect(state.isStaged).toBe(false)
      expect(state.isStaging).toBe(false)
      expect(state.stagingComplete).toBe(false)
    })

    it('setProject with full entity carrying real impl_launched_at sets implementationLaunched=true', () => {
      store.setProject(makeFullEntity())
      const state = store.getProjectState('proj-fe6061')
      expect(state.implementationLaunched).toBe(true)
      expect(state.implementationLaunchedAt).toBe('2026-06-14T10:00:00Z')
    })
  })
})
