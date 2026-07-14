/**
 * CE-0029 Item 1 — ProjectTabs.vue reactive-project regression.
 *
 * After CE-0029, ProjectTabs maintains a `localProject` ref that hydrates
 * from props.project on mount AND refetches via api.projects.get when one
 * of the project:* WS events arrives. Children (JobsTab, useProjectCloseout)
 * read from this reactive ref instead of the static prop. The dual-source
 * store-OR-prop fallback that CE-0028b added is gone.
 *
 * Per feedback_frontend_prop_vs_store_source_of_truth, the WS event is
 * fired via the same path the production code uses (the wsStore.on()
 * handler that ProjectTabs registers). The test does NOT directly mutate
 * the prop or inject state through a side channel.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createVuetify } from 'vuetify'
import ProjectTabs from '@/components/projects/ProjectTabs.vue'

const mockRouter = { push: vi.fn(), replace: vi.fn() }
const mockRoute = { query: {}, hash: '' }

vi.mock('vue-router', () => ({
  useRoute: () => mockRoute,
  useRouter: () => mockRouter,
}))

const mockSortedJobs = { value: [] }
const mockLoadJobs = vi.fn().mockResolvedValue([])

vi.mock('@/composables/useAgentJobs', () => ({
  useAgentJobs: () => ({
    store: {},
    sortedJobs: mockSortedJobs,
    loadJobs: mockLoadJobs,
  }),
}))

vi.mock('@/composables/useIntegrationStatus', () => ({
  useIntegrationStatus: () => ({
    gitEnabled: { value: false },
    serenaEnabled: { value: false },
  }),
}))

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ showToast: vi.fn() }),
}))

vi.mock('@/composables/useClipboard', () => ({
  useClipboard: () => ({ copy: vi.fn().mockResolvedValue(true) }),
}))

// CE-0029: capture the handlers ProjectTabs registers with wsStore.on so we
// can invoke them directly — mirroring the routeWebsocketEvent dispatch path.
const wsHandlers = new Map()

vi.mock('@/stores/websocket', () => ({
  useWebSocketStore: () => ({
    subscribeToProject: vi.fn(),
    unsubscribe: vi.fn(),
    onConnectionChange: vi.fn().mockReturnValue(vi.fn()),
    on: vi.fn((type, handler) => {
      const set = wsHandlers.get(type) || new Set()
      set.add(handler)
      wsHandlers.set(type, set)
      return () => set.delete(handler)
    }),
  }),
}))

vi.mock('@/stores/notifications', () => ({
  useNotificationStore: () => ({ clearForProject: vi.fn() }),
}))

// CE-0029 critical: api.projects.get is what the WS handler calls to refetch.
// We start it returning the page-load shape, then update it to return the
// post-WS shape (staging_complete) for the event-driven refetch.
const apiProjectsGet = vi.fn()
const apiProjectsUpdate = vi.fn().mockResolvedValue({})

// FE-3007a: ProjectTabs is now store-backed — the WS refetch goes through the
// project store, which imports the NAMED `api` export. Provide both named +
// default so the real store (not mocked) resolves api.projects.get.
vi.mock('@/services/api', () => {
  const apiMock = {
    projects: {
      get: (...args) => apiProjectsGet(...args),
      update: (...args) => apiProjectsUpdate(...args),
    },
    prompts: {
      staging: vi.fn().mockResolvedValue({ data: { prompt: 'test' } }),
    },
    orchestrator: {
      launchProject: vi.fn().mockResolvedValue({}),
    },
    products: {
      getMemoryEntries: vi.fn().mockResolvedValue({ data: { entries: [] } }),
    },
  }
  return { api: apiMock, default: apiMock }
})

const PROJECT_ID = 'proj-ce-0029'

function makeProject(overrides = {}) {
  return {
    id: PROJECT_ID,
    project_id: PROJECT_ID,
    name: 'CE-0029 Reactive Test Project',
    status: 'active',
    execution_mode: 'multi_terminal',
    staging_status: 'staging',
    implementation_launched_at: null,
    ...overrides,
  }
}

function createWrapper(pinia, projectOverrides = {}) {
  const vuetify = createVuetify()
  return mount(ProjectTabs, {
    props: { project: makeProject(projectOverrides), orchestrator: null },
    global: {
      plugins: [vuetify, pinia],
      stubs: {
        LaunchTab: {
          template: '<div class="launch-tab-stub" :data-staging-status="project?.staging_status" />',
          props: ['project'],
        },
        JobsTab: {
          template: '<div class="jobs-tab-stub" :data-staging-status="project?.staging_status" :data-impl-launched-at="project?.implementation_launched_at || \'\'" />',
          props: ['project'],
        },
        CloseoutModal: { template: '<div class="closeout-modal-stub" />' },
        DecisionModal: { template: '<div class="decision-modal-stub" />' },
      },
    },
  })
}

describe('ProjectTabs CE-0029 reactive-project (WS-driven refetch)', () => {
  let pinia

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    wsHandlers.clear()
    apiProjectsGet.mockReset()
    // Default: get() returns the same shape as the initial prop (page load).
    apiProjectsGet.mockResolvedValue({
      data: makeProject({ staging_status: 'staging' }),
    })
    mockRoute.query = { tab: 'jobs' }
    mockSortedJobs.value = []
  })

  it('subscribes to project:staging_complete and project:implementation_launched on mount', async () => {
    createWrapper(pinia)
    await flushPromises()

    expect(wsHandlers.has('project:staging_complete')).toBe(true)
    expect(wsHandlers.has('project:implementation_launched')).toBe(true)
  })

  it('refetches the project on project:staging_complete and propagates new state to children', async () => {
    const wrapper = createWrapper(pinia)
    await flushPromises()

    // Children initially see the page-load shape.
    expect(wrapper.find('.jobs-tab-stub').attributes('data-staging-status')).toBe('staging')

    // Backend has flipped the column; the next api.projects.get returns
    // staging_complete. Fire the WS event the same way routeWebsocketEvent
    // would (call the registered handler directly).
    apiProjectsGet.mockResolvedValue({
      data: makeProject({ staging_status: 'staging_complete' }),
    })
    const handlers = Array.from(wsHandlers.get('project:staging_complete') || [])
    expect(handlers.length).toBeGreaterThan(0)
    for (const h of handlers) {
      await h({ project_id: PROJECT_ID, staging_status: 'staging_complete' })
    }
    await flushPromises()

    // Refetch happened.
    expect(apiProjectsGet).toHaveBeenCalledWith(PROJECT_ID)

    // FE-6228: staging_complete now trips the same-project auto-flip to the
    // launch pane (the solo auto-follow contract — consistent with chain). That
    // is intended; this test verifies the orthogonal concern of WS-refetch
    // propagation into the JobsTab child, so return to the jobs pane explicitly
    // before asserting on it.
    wrapper.vm.activeTab = 'jobs'
    await flushPromises()

    // Child re-renders with the new reactive value — no manual prop bump,
    // no dual-source fallback to a store.
    expect(wrapper.find('.jobs-tab-stub').attributes('data-staging-status')).toBe('staging_complete')
  })

  it('refetches the project on project:implementation_launched and propagates the timestamp', async () => {
    const wrapper = createWrapper(pinia, { staging_status: 'staging_complete' })
    await flushPromises()

    // FE-6228: mounting with staging_complete trips the same-project auto-flip
    // to the launch pane (the solo auto-follow contract). This test verifies
    // WS-refetch propagation of the timestamp into the JobsTab child, so return
    // to the jobs pane before asserting. (The subsequent implementation_launched
    // flip targets the jobs pane, so the pane stays put through the event.)
    wrapper.vm.activeTab = 'jobs'
    await flushPromises()

    expect(wrapper.find('.jobs-tab-stub').attributes('data-impl-launched-at')).toBe('')

    apiProjectsGet.mockResolvedValue({
      data: makeProject({
        staging_status: 'staging_complete',
        implementation_launched_at: '2026-05-17T15:00:00Z',
      }),
    })
    const handlers = Array.from(wsHandlers.get('project:implementation_launched') || [])
    for (const h of handlers) {
      await h({
        project_id: PROJECT_ID,
        implementation_launched_at: '2026-05-17T15:00:00Z',
      })
    }
    await flushPromises()

    expect(apiProjectsGet).toHaveBeenCalledWith(PROJECT_ID)
    expect(wrapper.find('.jobs-tab-stub').attributes('data-impl-launched-at')).toBe(
      '2026-05-17T15:00:00Z'
    )
  })

  it('ignores WS events for other projects', async () => {
    createWrapper(pinia)
    await flushPromises()

    apiProjectsGet.mockClear()
    const handlers = Array.from(wsHandlers.get('project:staging_complete') || [])
    for (const h of handlers) {
      await h({ project_id: 'some-other-project', staging_status: 'staging_complete' })
    }
    await flushPromises()

    expect(apiProjectsGet).not.toHaveBeenCalled()
  })
})
