/**
 * DashboardView.commits.spec.js — BE-6078 PART 3.
 *
 * Edition Scope: CE.
 *
 * The "Commits" mini-stat was bound to recentCommits.length — built only from
 * the capped 10-item recent_memories preview (.slice(0, 10)) — so it could never
 * exceed 10 and never reflected the cumulative commits in 360 memory. It now
 * binds to the backend's `total_commits` aggregate. This test drives the real
 * view: the stats payload carries total_commits=42 while the preview holds a
 * single memory with 3 commits, and asserts the mini-stat shows 42 (not 3/10).
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
    checkStatus: vi.fn().mockResolvedValue({
      setup_mode: false,
      setup_complete: true,
      database_configured: true,
      database_connected: true,
      requires_setup: false,
    }),
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

function dashboardPayload(overrides = {}) {
  return {
    project_status_dist: { active: 2 },
    taxonomy_dist: [],
    agent_role_dist: [],
    recent_projects: [],
    // One memory carrying 3 commits — the OLD binding (recentCommits.length)
    // would render 3 here; the new binding must render total_commits instead.
    recent_memories: [
      {
        product_name: 'Demo',
        project_name: 'p',
        git_commits: [{ sha: 'a' }, { sha: 'b' }, { sha: 'c' }],
      },
    ],
    task_status_dist: {},
    total_commits: 42,
    ...overrides,
  }
}

function commitsStatText(wrapper) {
  const stat = wrapper
    .findAll('.mini-stat')
    .find((el) => el.find('.mini-stat-label').text() === 'Commits')
  return stat.find('.mini-stat-value').text()
}

describe('DashboardView.vue — Commits mini-stat (BE-6078 PART 3)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    getDashboard.mockResolvedValue({ data: dashboardPayload() })
    getCallCounts.mockResolvedValue({ data: { total_api_calls: 0, total_mcp_calls: 0 } })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  const mountView = () =>
    mount(DashboardView, {
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

  it('binds the Commits stat to the cumulative total_commits, not the preview length', async () => {
    const wrapper = mountView()
    await flushPromises()
    expect(commitsStatText(wrapper)).toBe('42')
  })

  it('falls back to 0 when total_commits is absent from the payload', async () => {
    getDashboard.mockResolvedValue({ data: dashboardPayload({ total_commits: undefined }) })
    const wrapper = mountView()
    await flushPromises()
    expect(commitsStatText(wrapper)).toBe('0')
  })
})
