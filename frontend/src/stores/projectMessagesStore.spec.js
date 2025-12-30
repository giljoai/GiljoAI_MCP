import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { useProjectMessagesStore } from '@/stores/projectMessagesStore'

describe('projectMessagesStore (map-based)', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useProjectMessagesStore()
    store.$reset?.()
  })

  it('stores messages per project immutably and dedupes by message_id', () => {
    store.setMessages('project-1', [])
    const beforeList = store.getMessages('project-1')
    expect(beforeList).toEqual([])

    store.handleSent({
      project_id: 'project-1',
      message_id: 'm1',
      from_agent: 'orchestrator',
      message_type: 'broadcast',
      timestamp: '2025-12-25T00:00:00Z',
    })

    const afterFirst = store.getMessages('project-1')
    expect(afterFirst).not.toBe(beforeList)
    expect(afterFirst).toHaveLength(1)

    store.handleSent({
      project_id: 'project-1',
      message_id: 'm1',
      from_agent: 'orchestrator',
      message_type: 'broadcast',
      timestamp: '2025-12-25T00:00:00Z',
    })

    const afterDup = store.getMessages('project-1')
    expect(afterDup).toHaveLength(1)
  })

  it('updates acknowledged status for known messages', () => {
    store.handleSent({ project_id: 'project-1', message_id: 'm1', status: 'sent' })
    expect(store.getMessages('project-1')[0]).toEqual(expect.objectContaining({ id: 'm1' }))

    store.handleAcknowledged({
      project_id: 'project-1',
      message_ids: ['m1'],
    })

    expect(store.getMessages('project-1')[0]).toEqual(
      expect.objectContaining({ id: 'm1', status: 'acknowledged' }),
    )
  })
})
