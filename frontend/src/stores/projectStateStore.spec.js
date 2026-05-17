/**
 * CE-0029 Item 3 — projectStateStore: setImplementationLaunched mutation +
 * handleImplementationLaunched WS handler.
 *
 * Mirrors the setStagingComplete/handleStagingComplete pattern. Tests are
 * deliberately store-mutation-driven (no prop injection), per the
 * test-discipline rule in feedback_frontend_prop_vs_store_source_of_truth.
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useProjectStateStore } from './projectStateStore'

describe('projectStateStore — staging_complete (pre-existing baseline)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('setStagingComplete sets stagingComplete=true and isStaging=false', () => {
    const store = useProjectStateStore()
    store.setStagingComplete('proj-1', true)
    const state = store.getProjectState('proj-1')
    expect(state.stagingComplete).toBe(true)
    expect(state.isStaging).toBe(false)
  })

  it('handleStagingComplete patches the store from a WS payload', () => {
    const store = useProjectStateStore()
    store.handleStagingComplete({ project_id: 'proj-1', staging_status: 'staging_complete' })
    expect(store.getProjectState('proj-1').stagingComplete).toBe(true)
  })
})

describe('projectStateStore — CE-0029 Item 3 implementation_launched', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('defaults implementationLaunched=false and implementationLaunchedAt=null', () => {
    const store = useProjectStateStore()
    store.setProject({ id: 'proj-1', name: 'p', staging_status: 'staging' })
    const state = store.getProjectState('proj-1')
    expect(state.implementationLaunched).toBe(false)
    expect(state.implementationLaunchedAt).toBeNull()
  })

  it('normalizeProjectState hydrates implementationLaunched from API field', () => {
    const store = useProjectStateStore()
    store.setProject({
      id: 'proj-1',
      name: 'p',
      staging_status: 'staging_complete',
      implementation_launched_at: '2026-05-17T12:00:00Z',
    })
    const state = store.getProjectState('proj-1')
    expect(state.implementationLaunched).toBe(true)
    expect(state.implementationLaunchedAt).toBe('2026-05-17T12:00:00Z')
  })

  it('setImplementationLaunched(projectId, timestamp) patches both fields', () => {
    const store = useProjectStateStore()
    store.setImplementationLaunched('proj-1', '2026-05-17T13:00:00Z')
    const state = store.getProjectState('proj-1')
    expect(state.implementationLaunched).toBe(true)
    expect(state.implementationLaunchedAt).toBe('2026-05-17T13:00:00Z')
  })

  it('setImplementationLaunched(projectId, null) clears both fields', () => {
    const store = useProjectStateStore()
    store.setImplementationLaunched('proj-1', '2026-05-17T13:00:00Z')
    store.setImplementationLaunched('proj-1', null)
    const state = store.getProjectState('proj-1')
    expect(state.implementationLaunched).toBe(false)
    expect(state.implementationLaunchedAt).toBeNull()
  })

  it('handleImplementationLaunched patches the store from a WS payload', () => {
    const store = useProjectStateStore()
    store.handleImplementationLaunched({
      project_id: 'proj-1',
      implementation_launched_at: '2026-05-17T14:00:00Z',
    })
    const state = store.getProjectState('proj-1')
    expect(state.implementationLaunched).toBe(true)
    expect(state.implementationLaunchedAt).toBe('2026-05-17T14:00:00Z')
  })

  it('handleImplementationLaunched ignores payloads without project_id', () => {
    const store = useProjectStateStore()
    store.handleImplementationLaunched({})
    expect(store.allProjects).toHaveLength(0)
  })

  it('handleImplementationLaunched preserves stagingComplete on the same project', () => {
    // Verifies the patch is additive — staging signal that arrived earlier
    // is not clobbered by the impl-launched signal.
    const store = useProjectStateStore()
    store.handleStagingComplete({ project_id: 'proj-1' })
    store.handleImplementationLaunched({
      project_id: 'proj-1',
      implementation_launched_at: '2026-05-17T14:00:00Z',
    })
    const state = store.getProjectState('proj-1')
    expect(state.stagingComplete).toBe(true)
    expect(state.implementationLaunched).toBe(true)
    expect(state.implementationLaunchedAt).toBe('2026-05-17T14:00:00Z')
  })
})
