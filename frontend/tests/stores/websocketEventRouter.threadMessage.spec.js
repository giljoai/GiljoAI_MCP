/**
 * websocketEventRouter — FE-9184 thread_message → Messages Waiting refresh.
 *
 * A hub thread_message WS event may raise an agent's messages_waiting_count on
 * the OPEN project's jobs table. The commHubEventRoutes handler must trigger
 * agentJobsStore.refreshMessagesWaitingCounts(currentProjectId), scoped:
 *
 * - payload.project_id matches the open project        → refresh
 * - payload.project_id is a different project          → skip
 * - payload.project_id null, thread known project-bound → resolve via commHub
 * - payload.project_id null, thread known standalone    → skip (no badge impact)
 * - payload.project_id null, thread unknown             → refresh (conservative;
 *   the MCP post path broadcasts project_id=null even for project-bound threads)
 * - no open project                                     → skip
 *
 * Edition Scope: CE
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/services/api', () => ({
  default: {
    agentJobs: {
      list: vi.fn(),
    },
  },
}))

import api from '@/services/api'
import { EVENT_MAP, routeWebsocketEvent } from '@/stores/websocketEventRouter'
import { useProjectTabsStore } from '@/stores/projectTabs'
import { useCommHubStore } from '@/stores/commHubStore'

async function fireThreadMessage(data) {
  await routeWebsocketEvent(
    { type: 'thread_message', data },
    { eventMap: EVENT_MAP },
  )
}

describe('websocketEventRouter — FE-9184 thread_message waiting-count refresh', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    setActivePinia(createPinia())
    api.agentJobs.list.mockReset()
    api.agentJobs.list.mockResolvedValue({ data: { jobs: [] } })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('refreshes when payload.project_id matches the open project', async () => {
    useProjectTabsStore().setCurrentProject({ id: 'project-1' })

    await fireThreadMessage({
      thread_id: 'thread-1',
      message_id: 'm-1',
      content: 'hello',
      project_id: 'project-1',
    })
    await vi.advanceTimersByTimeAsync(1000)

    expect(api.agentJobs.list).toHaveBeenCalledTimes(1)
    expect(api.agentJobs.list).toHaveBeenCalledWith('project-1')
  })

  it('skips when payload.project_id is a different project', async () => {
    useProjectTabsStore().setCurrentProject({ id: 'project-1' })

    await fireThreadMessage({
      thread_id: 'thread-1',
      message_id: 'm-1',
      content: 'hello',
      project_id: 'project-2',
    })
    await vi.advanceTimersByTimeAsync(5000)

    expect(api.agentJobs.list).not.toHaveBeenCalled()
  })

  it('resolves a null project_id via the commHub thread directory (project-bound)', async () => {
    useProjectTabsStore().setCurrentProject({ id: 'project-1' })
    useCommHubStore()._testSeedThread({ thread_id: 'thread-1', project_id: 'project-1' })

    await fireThreadMessage({
      thread_id: 'thread-1',
      message_id: 'm-1',
      content: 'MCP-path post',
      project_id: null,
    })
    await vi.advanceTimersByTimeAsync(1000)

    expect(api.agentJobs.list).toHaveBeenCalledTimes(1)
    expect(api.agentJobs.list).toHaveBeenCalledWith('project-1')
  })

  it('skips a null project_id resolved to a standalone (town square) thread', async () => {
    useProjectTabsStore().setCurrentProject({ id: 'project-1' })
    useCommHubStore()._testSeedThread({ thread_id: 'thread-ts', project_id: null })

    await fireThreadMessage({
      thread_id: 'thread-ts',
      message_id: 'm-1',
      content: 'town square chatter',
      project_id: null,
    })
    await vi.advanceTimersByTimeAsync(5000)

    expect(api.agentJobs.list).not.toHaveBeenCalled()
  })

  it('refreshes conservatively when the thread is unknown and project_id is null', async () => {
    useProjectTabsStore().setCurrentProject({ id: 'project-1' })

    await fireThreadMessage({
      thread_id: 'thread-unknown',
      message_id: 'm-1',
      content: 'MCP-path post on an unloaded thread',
      project_id: null,
    })
    await vi.advanceTimersByTimeAsync(1000)

    expect(api.agentJobs.list).toHaveBeenCalledTimes(1)
    expect(api.agentJobs.list).toHaveBeenCalledWith('project-1')
  })

  it('skips when no project is open', async () => {
    useProjectTabsStore().setCurrentProject(null)

    await fireThreadMessage({
      thread_id: 'thread-1',
      message_id: 'm-1',
      content: 'hello',
      project_id: 'project-1',
    })
    await vi.advanceTimersByTimeAsync(5000)

    expect(api.agentJobs.list).not.toHaveBeenCalled()
  })
})

describe('websocketEventRouter — FE-9184 thread_update read-drain refresh', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    setActivePinia(createPinia())
    api.agentJobs.list.mockReset()
    api.agentJobs.list.mockResolvedValue({ data: { jobs: [] } })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  async function fireThreadUpdate(data) {
    await routeWebsocketEvent(
      { type: 'thread_update', data },
      { eventMap: EVENT_MAP },
    )
  }

  it('refreshes on update_type="read" (agent drained its messages — badge decrement)', async () => {
    useProjectTabsStore().setCurrentProject({ id: 'project-1' })
    useCommHubStore()._testSeedThread({ thread_id: 'thread-1', project_id: 'project-1' })

    await fireThreadUpdate({
      thread_id: 'thread-1',
      chat_id: 'CHT-0001',
      status: 'open',
      update_type: 'read',
    })
    await vi.advanceTimersByTimeAsync(1000)

    expect(api.agentJobs.list).toHaveBeenCalledTimes(1)
    expect(api.agentJobs.list).toHaveBeenCalledWith('project-1')
  })

  it('refreshes conservatively on update_type="read" for an unloaded thread', async () => {
    useProjectTabsStore().setCurrentProject({ id: 'project-1' })

    await fireThreadUpdate({
      thread_id: 'thread-unknown',
      chat_id: 'CHT-0002',
      status: 'open',
      update_type: 'read',
    })
    await vi.advanceTimersByTimeAsync(1000)

    expect(api.agentJobs.list).toHaveBeenCalledTimes(1)
  })

  it('does not refresh on non-read thread_update types (baton/status)', async () => {
    useProjectTabsStore().setCurrentProject({ id: 'project-1' })
    useCommHubStore()._testSeedThread({ thread_id: 'thread-1', project_id: 'project-1' })

    await fireThreadUpdate({
      thread_id: 'thread-1',
      chat_id: 'CHT-0001',
      status: 'open',
      next_action_owner: 'someone',
      update_type: 'baton',
    })
    await vi.advanceTimersByTimeAsync(5000)

    expect(api.agentJobs.list).not.toHaveBeenCalled()
  })

  it('skips update_type="read" for a thread bound to another project', async () => {
    useProjectTabsStore().setCurrentProject({ id: 'project-1' })
    useCommHubStore()._testSeedThread({ thread_id: 'thread-2', project_id: 'project-2' })

    await fireThreadUpdate({
      thread_id: 'thread-2',
      chat_id: 'CHT-0003',
      status: 'open',
      update_type: 'read',
    })
    await vi.advanceTimersByTimeAsync(5000)

    expect(api.agentJobs.list).not.toHaveBeenCalled()
  })
})
