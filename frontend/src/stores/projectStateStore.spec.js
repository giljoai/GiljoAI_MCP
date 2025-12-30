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

  it('marks staging complete only for broadcast message:sent events', () => {
    store.setProject({ id: 'project-1', mission: '' })

    store.handleMessageSent({ project_id: 'project-1', message_type: 'direct' })
    expect(store.getProjectState('project-1').stagingComplete).toBe(false)

    store.handleMessageSent({ project_id: 'project-1', message_type: 'broadcast' })
    expect(store.getProjectState('project-1').stagingComplete).toBe(true)
  })

  it('marks staging complete on message:received events', () => {
    store.setProject({ id: 'project-1', mission: '' })
    const before = store.getProjectState('project-1')
    expect(before.stagingComplete).toBe(false)

    store.handleMessageReceived({ project_id: 'project-1', message_id: 'm1' })

    const after = store.getProjectState('project-1')
    expect(after).not.toBe(before)
    expect(after.stagingComplete).toBe(true)
  })
})
