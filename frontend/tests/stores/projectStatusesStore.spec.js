import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { useProjectStatusesStore } from '@/stores/projectStatusesStore'

// Mock api.projectStatuses.list — must be hoisted before importing the store.
vi.mock('@/services/api', () => {
  return {
    default: {
      projectStatuses: {
        list: vi.fn(),
      },
    },
  }
})

import api from '@/services/api'

const CANONICAL = [
  {
    value: 'inactive',
    label: 'Inactive',
    color_token: 'color-text-muted',
    is_lifecycle_finished: false,
    is_immutable: false,
    is_user_mutable_via_mcp: true,
  },
  {
    value: 'active',
    label: 'Active',
    color_token: 'color-agent-implementer',
    is_lifecycle_finished: false,
    is_immutable: false,
    is_user_mutable_via_mcp: true,
  },
  {
    value: 'completed',
    label: 'Completed',
    color_token: 'color-status-complete',
    is_lifecycle_finished: true,
    is_immutable: true,
    is_user_mutable_via_mcp: true,
  },
  {
    value: 'cancelled',
    label: 'Cancelled',
    color_token: 'color-status-blocked',
    is_lifecycle_finished: true,
    is_immutable: true,
    is_user_mutable_via_mcp: true,
  },
  {
    value: 'terminated',
    label: 'Terminated',
    color_token: 'color-agent-analyzer',
    is_lifecycle_finished: true,
    is_immutable: false,
    is_user_mutable_via_mcp: false,
  },
  {
    value: 'deleted',
    label: 'Deleted',
    color_token: 'color-agent-analyzer',
    is_lifecycle_finished: true,
    is_immutable: false,
    is_user_mutable_via_mcp: false,
  },
]

describe('projectStatusesStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    api.projectStatuses.list.mockReset()
    api.projectStatuses.list.mockResolvedValue({ data: CANONICAL })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('starts empty with loaded=false and loading=false', () => {
    const store = useProjectStatusesStore()
    expect(store.statuses).toEqual([])
    expect(store.loaded).toBe(false)
    expect(store.loading).toBe(false)
    expect(store.validValues).toEqual([])
  })

  it('fetches statuses on first ensureLoaded() call', async () => {
    const store = useProjectStatusesStore()
    await store.ensureLoaded()
    expect(api.projectStatuses.list).toHaveBeenCalledTimes(1)
    expect(store.loaded).toBe(true)
    expect(store.statuses).toHaveLength(6)
    expect(store.validValues).toEqual([
      'inactive',
      'active',
      'completed',
      'cancelled',
      'terminated',
      'deleted',
    ])
  })

  it('does not refetch on subsequent ensureLoaded() calls', async () => {
    const store = useProjectStatusesStore()
    await store.ensureLoaded()
    await store.ensureLoaded()
    await store.ensureLoaded()
    expect(api.projectStatuses.list).toHaveBeenCalledTimes(1)
  })

  it('coalesces concurrent in-flight fetches into one request', async () => {
    let resolveFn
    api.projectStatuses.list.mockImplementationOnce(
      () =>
        new Promise((res) => {
          resolveFn = res
        }),
    )
    const store = useProjectStatusesStore()
    const a = store.ensureLoaded()
    const b = store.ensureLoaded()
    const c = store.ensureLoaded()
    resolveFn({ data: CANONICAL })
    await Promise.all([a, b, c])
    expect(api.projectStatuses.list).toHaveBeenCalledTimes(1)
  })

  it('exposes getMeta(value) for each canonical status', async () => {
    const store = useProjectStatusesStore()
    await store.ensureLoaded()
    expect(store.getMeta('completed').label).toBe('Completed')
    expect(store.getMeta('completed').color_token).toBe('color-status-complete')
    expect(store.getMeta('active').color_token).toBe('color-agent-implementer')
  })

  it('returns undefined for unknown status values via getMeta', async () => {
    const store = useProjectStatusesStore()
    await store.ensureLoaded()
    expect(store.getMeta('staging')).toBeUndefined()
    expect(store.getMeta('closed')).toBeUndefined()
    expect(store.getMeta('archived')).toBeUndefined()
  })

  it('exposes a Set-backed isValid(value) check', async () => {
    const store = useProjectStatusesStore()
    await store.ensureLoaded()
    expect(store.isValid('active')).toBe(true)
    expect(store.isValid('deleted')).toBe(true)
    expect(store.isValid('archived')).toBe(false)
    expect(store.isValid('closed')).toBe(false)
    expect(store.isValid(undefined)).toBe(false)
  })

  it('reset() clears state so the next ensureLoaded() refetches', async () => {
    const store = useProjectStatusesStore()
    await store.ensureLoaded()
    expect(api.projectStatuses.list).toHaveBeenCalledTimes(1)
    store.reset()
    expect(store.loaded).toBe(false)
    expect(store.statuses).toEqual([])
    await store.ensureLoaded()
    expect(api.projectStatuses.list).toHaveBeenCalledTimes(2)
  })

  it('on fetch failure: leaves loaded=false and rethrows so callers can degrade gracefully', async () => {
    const err = new Error('Network down')
    api.projectStatuses.list.mockRejectedValueOnce(err)
    const store = useProjectStatusesStore()
    await expect(store.ensureLoaded()).rejects.toThrow('Network down')
    expect(store.loaded).toBe(false)
    expect(store.loading).toBe(false)
    // After failure, the next ensureLoaded() should retry.
    api.projectStatuses.list.mockResolvedValueOnce({ data: CANONICAL })
    await store.ensureLoaded()
    expect(store.loaded).toBe(true)
    expect(store.validValues).toHaveLength(6)
  })

  it('preserves declaration order of statuses from the API', async () => {
    const store = useProjectStatusesStore()
    await store.ensureLoaded()
    expect(store.statuses.map((s) => s.value)).toEqual([
      'inactive',
      'active',
      'completed',
      'cancelled',
      'terminated',
      'deleted',
    ])
  })
})
