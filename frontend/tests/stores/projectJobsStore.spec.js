import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
// import { useProjectJobsStore } from '@/stores/projectJobs' // module deleted/moved

describe.skip('projectJobs store - module deleted/moved', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useProjectJobsStore()
  })

  it('tracks mission updates and dirty state', () => {
    store.setProjectContext({ projectId: 'p1', description: 'Test project' })
    store.setMission('New mission')
    expect(store.orchestratorMission).toBe('New mission')
    expect(store.missionDirty).toBe(true)
  })

  it('updates staging status and resets launch state on restage', () => {
    store.updateStagingStatus('ready')
    expect(store.isLaunchReady).toBe(true)

    store.updateStagingStatus('staging', '2025-11-25T10:00:00Z')
    expect(store.isLaunchReady).toBe(false)
    expect(store.stagingStartedAt).toBe('2025-11-25T10:00:00Z')
    expect(store.launchComplete).toBe(false)
    expect(store.launchError).toBeNull()
  })

  it('marks launch completion and errors', () => {
    store.markLaunchComplete()
    expect(store.launchComplete).toBe(true)
    expect(store.canLaunch).toBe(false)

    store.setLaunchError('failed to start')
    expect(store.launchError).toBe('failed to start')
    expect(store.hasStagingError).toBe(false)
  })

  it('resets state cleanly', () => {
    store.setProjectContext({ projectId: 'p1', description: 'desc' })
    store.setMission('mission')
    store.updateStagingStatus('ready')
    store.markLaunchComplete()

    store.$reset()
    expect(store.currentProjectId).toBeNull()
    expect(store.orchestratorMission).toBe('')
    expect(store.stagingStatus).toBeNull()
    expect(store.launchComplete).toBe(false)
  })
})
