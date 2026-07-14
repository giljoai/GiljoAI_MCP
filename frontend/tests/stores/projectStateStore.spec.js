import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { useProjectStateStore } from '@/stores/projectStateStore'

describe('projectStateStore (map-based)', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useProjectStateStore()
    store.$reset?.()
  })

  it('updates mission immutably on project:mission_updated', () => {
    store.setProject({ id: 'project-1', mission: '' })

    const before = store.getProjectState('project-1')
    expect(before).toBeTruthy()
    expect(before.mission).toBe('')

    store.handleMissionUpdated({ project_id: 'project-1', mission: 'New mission' })

    const after = store.getProjectState('project-1')
    expect(after).not.toBe(before)
    expect(before.mission).toBe('')
    expect(after.mission).toBe('New mission')
  })

})
