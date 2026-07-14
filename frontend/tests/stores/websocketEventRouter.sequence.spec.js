/**
 * websocketEventRouter.sequence.spec.js — FE-6165f
 *
 * The `sequence:updated` event (BE-6165c) must route to the sequenceRunStore so
 * durable election + the cockpit stay live.
 */
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { EVENT_MAP, routeWebsocketEvent, defaultShouldRoute } from '@/stores/websocketEventRouter'
import { SEQUENCE_EVENT_ROUTES } from '@/stores/eventRoutes/sequenceEventRoutes'
import { useUserStore } from '@/stores/user'

describe('websocketEventRouter — sequence:updated (FE-6165f)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    const userStore = useUserStore()
    userStore.currentUser = { tenant_key: 'test-tenant' }
  })

  it('declares sequence:updated -> sequenceRun.handleSequenceUpdated', () => {
    expect(SEQUENCE_EVENT_ROUTES['sequence:updated']).toEqual({
      store: 'sequenceRun',
      action: 'handleSequenceUpdated',
    })
    expect(EVENT_MAP['sequence:updated']).toBeDefined()
  })

  it('routes a sequence:updated event to the store action with the {run_id} payload', async () => {
    const sequenceRunStore = { handleSequenceUpdated: vi.fn() }
    const storeRegistry = { sequenceRun: () => sequenceRunStore }

    const routed = await routeWebsocketEvent(
      { type: 'sequence:updated', data: { run_id: 'run-42' } },
      { eventMap: EVENT_MAP, storeRegistry, shouldRoute: defaultShouldRoute },
    )

    expect(routed).toBe(true)
    expect(sequenceRunStore.handleSequenceUpdated).toHaveBeenCalledTimes(1)
    // normalizeWebsocketPayload hoists data.* to the top level (and keeps `data`),
    // so the handler reads payload.run_id.
    expect(sequenceRunStore.handleSequenceUpdated).toHaveBeenCalledWith(
      expect.objectContaining({ run_id: 'run-42' }),
    )
  })
})
