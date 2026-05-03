// Tests for the skills-version drift surface in SystemStatusBanner.vue.
//
// Behaviour under test (post-simplification per project skills-drift-cleanup):
//   - The banner consumes the simplified server contract:
//       { current, announced, drift_detected, message }
//     There is no `installed` or `never_installed`; the server alone decides
//     whether drift exists for the authenticated user.
//   - On mount, when admin, the banner calls
//     GET /api/notifications/check-skills-version (no installed param).
//   - When the API response reports drift_detected: true, the skills-drift
//     v-alert is shown to admins. Non-admins never see it.
//   - Dismissing the drift banner persists a per-version key in localStorage
//     (giljo_skills_dismissed_for_<current>); the banner does NOT reappear
//     for the same drift on a fresh mount.
//   - The drift banner reappears when `current` advances to a new version
//     (different dismiss key).
//   - Edition-aware copy: in CE mode the banner mentions `git pull`; in
//     demo/saas mode the message must NOT mention git pull.

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

import { useUserStore } from '@/stores/user'

// Override the api mock from setup.js so we can control apiClient + the
// /api/notifications/check-skills-version response per test. vi.hoisted lets
// us define the mock object at the top of the file in a way that survives
// vi.mock hoisting (vi.mock is moved above all imports).
const { apiClientMock, apiObjMock, setupServiceMock } = vi.hoisted(() => {
  const apiClient = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  }
  // Minimal api object that satisfies user store's default import path.
  const apiObj = {
    auth: {
      me: vi.fn(() => Promise.resolve({ data: { id: 1, username: 'admin', role: 'admin' } })),
      logout: vi.fn(() => Promise.resolve({ data: { success: true } })),
    },
  }
  const setupService = {
    checkEnhancedStatus: vi.fn(() => Promise.resolve({ mode: 'ce' })),
  }
  return { apiClientMock: apiClient, apiObjMock: apiObj, setupServiceMock: setupService }
})

vi.mock('@/services/api', () => {
  return {
    api: apiObjMock,
    default: apiObjMock,
    apiClient: apiClientMock,
    setTenantKey: vi.fn(),
    updateApiBaseURL: vi.fn(),
    parseErrorResponse: vi.fn(() => ({ message: '', isStructured: false })),
    getErrorMessage: vi.fn(() => ''),
  }
})

vi.mock('@/services/setupService', () => {
  return {
    default: setupServiceMock,
    setupService: setupServiceMock,
  }
})

// Real localStorage shim that records reads/writes (the global mock from
// setup.js returns undefined for getItem unless we replace it for this file).
function makeLocalStorage(initial = {}) {
  const store = { ...initial }
  return {
    getItem: vi.fn((k) => (k in store ? store[k] : null)),
    setItem: vi.fn((k, v) => {
      store[k] = String(v)
    }),
    removeItem: vi.fn((k) => {
      delete store[k]
    }),
    clear: vi.fn(() => {
      for (const k of Object.keys(store)) delete store[k]
    }),
    _backing: store,
  }
}

async function importBanner() {
  // Dynamic import so vi.mock has applied.
  const mod = await import('@/components/system/SystemStatusBanner.vue')
  return mod.default
}

function makeApiMock({ drift_detected = false, current = '1.1.11', announced = '1.1.11', message = null } = {}) {
  return (url) => {
    if (url === '/api/system/status') {
      return Promise.resolve({
        data: { pending_migrations: false, update_available: false, commits_behind: 0 },
      })
    }
    if (url === '/api/notifications/check-skills-version') {
      return Promise.resolve({
        data: { current, announced, drift_detected, message },
      })
    }
    return Promise.resolve({ data: {} })
  }
}

describe('SystemStatusBanner — skills version drift', () => {
  let SystemStatusBanner
  let pinia

  beforeEach(async () => {
    pinia = createPinia()
    setActivePinia(pinia)
    apiClientMock.get.mockReset()
    apiClientMock.post.mockReset()
    setupServiceMock.checkEnhancedStatus.mockReset()
    setupServiceMock.checkEnhancedStatus.mockResolvedValue({ mode: 'ce' })
    sessionStorage.clear?.()

    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      writable: true,
      value: makeLocalStorage({}),
    })

    apiClientMock.get.mockImplementation(makeApiMock({ drift_detected: false }))

    const userStore = useUserStore()
    userStore.currentUser = { id: 1, username: 'admin', role: 'admin' }

    SystemStatusBanner = await importBanner()
  })

  it('shows the drift banner for admin when drift_detected is true and not dismissed', async () => {
    apiClientMock.get.mockImplementation(
      makeApiMock({ drift_detected: true, current: '1.1.11', announced: '1.1.12' }),
    )

    const wrapper = mount(SystemStatusBanner, { global: { plugins: [pinia] } })
    await flushPromises()
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toMatch(/Skills updated/i)
  })

  it('hides the drift banner when drift_detected is false', async () => {
    apiClientMock.get.mockImplementation(
      makeApiMock({ drift_detected: false, current: '1.1.11', announced: '1.1.11' }),
    )

    const wrapper = mount(SystemStatusBanner, { global: { plugins: [pinia] } })
    await flushPromises()
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).not.toMatch(/Skills updated/i)
  })

  it('hides the drift banner for non-admin users even when drift_detected is true', async () => {
    const userStore = useUserStore()
    userStore.currentUser = { id: 2, username: 'user', role: 'user' }

    apiClientMock.get.mockImplementation(
      makeApiMock({ drift_detected: true, current: '1.1.11', announced: '1.1.12' }),
    )

    const wrapper = mount(SystemStatusBanner, { global: { plugins: [pinia] } })
    await flushPromises()
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).not.toMatch(/Skills updated/i)
  })

  it('persists dismissal under giljo_skills_dismissed_for_<current> when admin closes the banner', async () => {
    apiClientMock.get.mockImplementation(
      makeApiMock({ drift_detected: true, current: '1.1.11', announced: '1.1.12' }),
    )

    const wrapper = mount(SystemStatusBanner, { global: { plugins: [pinia] } })
    await flushPromises()
    await wrapper.vm.$nextTick()

    const vm = wrapper.vm
    expect(typeof vm.dismissSkills).toBe('function')
    vm.dismissSkills()
    await wrapper.vm.$nextTick()

    expect(window.localStorage.setItem).toHaveBeenCalledWith(
      'giljo_skills_dismissed_for_1.1.11',
      '1',
    )
    expect(wrapper.text()).not.toMatch(/Skills updated/i)
  })

  it('does not show the banner when current version is already dismissed', async () => {
    const ls = makeLocalStorage({})
    ls._backing['giljo_skills_dismissed_for_1.1.11'] = '1'
    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      writable: true,
      value: ls,
    })

    apiClientMock.get.mockImplementation(
      makeApiMock({ drift_detected: true, current: '1.1.11', announced: '1.1.12' }),
    )

    const wrapper = mount(SystemStatusBanner, { global: { plugins: [pinia] } })
    await flushPromises()
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).not.toMatch(/Skills updated/i)
  })

  it('CE edition copy mentions git pull', async () => {
    setupServiceMock.checkEnhancedStatus.mockResolvedValue({ mode: 'ce' })
    apiClientMock.get.mockImplementation(
      makeApiMock({ drift_detected: true, current: '1.1.11', announced: '1.1.12' }),
    )

    const wrapper = mount(SystemStatusBanner, { global: { plugins: [pinia] } })
    await flushPromises()
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toMatch(/git pull/i)
  })

  it('demo/saas edition copy does not mention git pull', async () => {
    setupServiceMock.checkEnhancedStatus.mockResolvedValue({ mode: 'demo' })
    apiClientMock.get.mockImplementation(
      makeApiMock({ drift_detected: true, current: '1.1.11', announced: '1.1.12' }),
    )

    const wrapper = mount(SystemStatusBanner, { global: { plugins: [pinia] } })
    await flushPromises()
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toMatch(/Skills updated/i)
    expect(wrapper.text()).not.toMatch(/git pull/i)
  })

  it('SaaS edition copy does not mention git pull', async () => {
    setupServiceMock.checkEnhancedStatus.mockResolvedValue({ mode: 'saas' })
    apiClientMock.get.mockImplementation(
      makeApiMock({ drift_detected: true, current: '1.1.11', announced: '1.1.12' }),
    )

    const wrapper = mount(SystemStatusBanner, { global: { plugins: [pinia] } })
    await flushPromises()
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).not.toMatch(/git pull/i)
  })
})
