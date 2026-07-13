/**
 * DashboardView.poll.spec.js — FE-6059.
 *
 * Edition Scope: Both.
 *
 * The live-counter poll was 30s and ran even while the tab was backgrounded.
 * FE-6059 raises the cadence to 60s and pauses polling while the page is hidden
 * (Page Visibility API), resuming + refetching immediately on re-show. This
 * spec drives the real view with fake timers and asserts all three behaviors.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock('@/services/setupService', () => ({
  default: {
    baseURL: '',
    checkStatus: vi.fn().mockResolvedValue({ requires_setup: false }),
  },
}))

const getDashboard = vi.fn()
const getCallCounts = vi.fn()
vi.mock('@/services/api', () => ({
  default: {
    stats: {
      getDashboard: (...a) => getDashboard(...a),
      getCallCounts: (...a) => getCallCounts(...a),
    },
  },
}))

import DashboardView from '@/views/DashboardView.vue'

let hidden = false

function setHidden(value) {
  hidden = value
  document.dispatchEvent(new Event('visibilitychange'))
}

let wrapper = null
const mountView = () => {
  wrapper = mount(DashboardView, {
    global: {
      stubs: {
        RecentProjectsList: true,
        RecentMemoriesList: true,
        ProjectReviewModal: true,
        AppAlert: true,
        RouterLink: true,
      },
    },
  })
  return wrapper
}

describe('DashboardView.vue — FE-6059 poll cadence + visibility pause', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    hidden = false
    Object.defineProperty(document, 'hidden', { configurable: true, get: () => hidden })
    getDashboard.mockResolvedValue({ data: { project_status_dist: {}, total_commits: 0 } })
    getCallCounts.mockResolvedValue({ data: { total_api_calls: 0, total_mcp_calls: 0 } })
    vi.useFakeTimers()
  })

  afterEach(() => {
    // Unmount so the component's visibilitychange listener is removed — a leaked
    // listener from a prior test would double-fire on the shared `document`.
    if (wrapper) {
      wrapper.unmount()
      wrapper = null
    }
    vi.useRealTimers()
    vi.clearAllMocks()
  })

  it('polls call counts on a 60s cadence (not 30s) and pauses while hidden', async () => {
    mountView()
    await flushPromises()

    // One initial fetch from onMounted's Promise.all.
    const base = getCallCounts.mock.calls.length
    expect(base).toBe(1)

    // At 30s nothing new fires — the interval is 60s now.
    vi.advanceTimersByTime(30_000)
    await flushPromises()
    expect(getCallCounts).toHaveBeenCalledTimes(base)

    // At 60s the poll fires once.
    vi.advanceTimersByTime(30_000)
    await flushPromises()
    expect(getCallCounts).toHaveBeenCalledTimes(base + 1)

    // Hide the tab -> polling stops; no further fetches while hidden.
    setHidden(true)
    const afterHide = getCallCounts.mock.calls.length
    vi.advanceTimersByTime(180_000)
    await flushPromises()
    expect(getCallCounts).toHaveBeenCalledTimes(afterHide)
  })

  it('refetches immediately and resumes polling when the tab becomes visible again', async () => {
    mountView()
    await flushPromises()
    const base = getCallCounts.mock.calls.length

    setHidden(true)
    vi.advanceTimersByTime(120_000)
    await flushPromises()
    const afterHide = getCallCounts.mock.calls.length
    expect(afterHide).toBe(base) // paused while hidden

    // Re-show -> immediate refetch.
    setHidden(false)
    await flushPromises()
    expect(getCallCounts).toHaveBeenCalledTimes(afterHide + 1)

    // ...and the 60s interval is running again.
    vi.advanceTimersByTime(60_000)
    await flushPromises()
    expect(getCallCounts).toHaveBeenCalledTimes(afterHide + 2)
  })
})
