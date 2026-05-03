// Tests for the skills-version drift surface in SystemStatusBanner.vue.
//
// Behaviour under test (Phase 1 + Phase 2 of the Skills version tracking project,
// HO1028 follow-up: server-side never_installed source-of-truth):
//   - On mount, when admin and localStorage has a known installed skills
//     version, the banner calls GET /api/notifications/check-skills-version
//     with the installed version as a query param.
//   - When the API response reports drift_detected: true AND
//     never_installed: false, the skills-drift v-alert is shown.
//   - When the server reports never_installed: true (no record of the user
//     ever running giljo_setup), the drift banner is suppressed even if
//     drift_detected is true. The server flag is the authoritative gate.
//   - A WS `system:update_available` event arriving while the most recent
//     server response had never_installed: true must NOT cause the banner
//     to appear (the re-fetch must reuse the server gate).
//   - Dismissing the drift banner persists a per-version key in localStorage
//     (giljo_skills_dismissed_for_<version>); the banner does NOT reappear
//     for the same drift on a fresh mount.
//   - The drift banner reappears when the bundled version advances
//     (different dismiss key).

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

import { useUserStore } from '@/stores/user'

// Override the api mock from setup.js so we can control apiClient + the
// /api/notifications/check-skills-version response per test. vi.hoisted lets
// us define the mock object at the top of the file in a way that survives
// vi.mock hoisting (vi.mock is moved above all imports).
const { apiClientMock, apiObjMock } = vi.hoisted(() => {
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
  return { apiClientMock: apiClient, apiObjMock: apiObj }
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

// Reset api + storage in each test before component mount.
async function importBanner() {
  // Dynamic import so vi.mock has applied.
  const mod = await import('@/components/system/SystemStatusBanner.vue')
  return mod.default
}

describe('SystemStatusBanner — skills version drift', () => {
  let SystemStatusBanner
  let pinia

  beforeEach(async () => {
    pinia = createPinia()
    setActivePinia(pinia)
    apiClientMock.get.mockReset()
    apiClientMock.post.mockReset()
    sessionStorage.clear?.()

    // Default: /api/system/status (the existing call) returns no migration / update.
    apiClientMock.get.mockImplementation((url) => {
      if (url === '/api/system/status') {
        return Promise.resolve({
          data: { pending_migrations: false, update_available: false, commits_behind: 0 },
        })
      }
      // Default for skills-version drift: not-drifted, installed known.
      if (url === '/api/notifications/check-skills-version') {
        return Promise.resolve({
          data: {
            installed: '1.1.11',
            current: '1.1.11',
            drift_detected: false,
            never_installed: false,
            message: null,
          },
        })
      }
      return Promise.resolve({ data: {} })
    })

    const userStore = useUserStore()
    userStore.currentUser = { id: 1, username: 'admin', role: 'admin' }

    SystemStatusBanner = await importBanner()
  })

  it('calls /api/notifications/check-skills-version with installed version when localStorage has it', async () => {
    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      writable: true,
      value: makeLocalStorage({ giljo_skills_version: '1.1.10' }),
    })

    apiClientMock.get.mockImplementation((url, config) => {
      if (url === '/api/system/status') {
        return Promise.resolve({
          data: { pending_migrations: false, update_available: false, commits_behind: 0 },
        })
      }
      if (url === '/api/notifications/check-skills-version') {
        // Echo the param so the assertion on params can see it.
        const installed = config?.params?.installed_skills_version
        return Promise.resolve({
          data: {
            installed,
            current: '1.1.11',
            drift_detected: true,
            never_installed: false,
            message: 'A newer skills bundle is available',
          },
        })
      }
      return Promise.resolve({ data: {} })
    })

    const wrapper = mount(SystemStatusBanner, { global: { plugins: [pinia] } })
    await flushPromises() // flush onMounted promise chain
    await wrapper.vm.$nextTick()

    const driftCalls = apiClientMock.get.mock.calls.filter(
      ([url]) => url === '/api/notifications/check-skills-version',
    )
    expect(driftCalls).toHaveLength(1)
    expect(driftCalls[0][1]?.params?.installed_skills_version).toBe('1.1.10')
  })

  it('suppresses the drift banner when server reports never_installed: true (HO1028)', async () => {
    // localStorage is irrelevant here — even if it has a stale skills_version
    // entry, the server is the source of truth. never_installed: true means
    // the user has never run giljo_setup against this server, so we must NOT
    // nag them with a drift banner.
    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      writable: true,
      value: makeLocalStorage({ giljo_skills_version: '1.1.10' }),
    })

    apiClientMock.get.mockImplementation((url) => {
      if (url === '/api/system/status') {
        return Promise.resolve({
          data: { pending_migrations: false, update_available: false, commits_behind: 0 },
        })
      }
      if (url === '/api/notifications/check-skills-version') {
        return Promise.resolve({
          data: {
            installed: null,
            current: '1.1.11',
            drift_detected: true,
            never_installed: true,
            message: 'No installed skills version reported.',
          },
        })
      }
      return Promise.resolve({ data: {} })
    })

    const wrapper = mount(SystemStatusBanner, { global: { plugins: [pinia] } })
    await flushPromises()
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).not.toMatch(/CLI skills|skills bundle/i)
  })

  it('shows the drift banner when server reports never_installed: false AND drift_detected: true', async () => {
    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      writable: true,
      value: makeLocalStorage({ giljo_skills_version: '1.1.10' }),
    })

    apiClientMock.get.mockImplementation((url) => {
      if (url === '/api/system/status') {
        return Promise.resolve({
          data: { pending_migrations: false, update_available: false, commits_behind: 0 },
        })
      }
      if (url === '/api/notifications/check-skills-version') {
        return Promise.resolve({
          data: {
            installed: '1.1.10',
            current: '1.1.11',
            drift_detected: true,
            never_installed: false,
            message: 'A newer skills bundle is available',
          },
        })
      }
      return Promise.resolve({ data: {} })
    })

    const wrapper = mount(SystemStatusBanner, { global: { plugins: [pinia] } })
    await flushPromises()
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toMatch(/CLI skills/i)
  })

  it('keeps banner hidden after WS system:update_available when never_installed remains true', async () => {
    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      writable: true,
      value: makeLocalStorage({}),
    })

    apiClientMock.get.mockImplementation((url) => {
      if (url === '/api/system/status') {
        return Promise.resolve({
          data: { pending_migrations: false, update_available: false, commits_behind: 0 },
        })
      }
      if (url === '/api/notifications/check-skills-version') {
        return Promise.resolve({
          data: {
            installed: null,
            current: '1.1.11',
            drift_detected: true,
            never_installed: true,
            message: 'No installed skills version reported.',
          },
        })
      }
      return Promise.resolve({ data: {} })
    })

    const wrapper = mount(SystemStatusBanner, { global: { plugins: [pinia] } })
    await flushPromises()
    await wrapper.vm.$nextTick()

    // Simulate the WS event the systemEventRoutes router dispatches.
    window.dispatchEvent(
      new CustomEvent('ws-system-update-available', {
        detail: { commits_behind: 3 },
      }),
    )
    await flushPromises()
    await wrapper.vm.$nextTick()

    // Re-fetch should have happened, but server still reports never_installed
    // so the drift banner stays hidden.
    expect(wrapper.text()).not.toMatch(/CLI skills|skills bundle/i)
  })

  it('persists dismissal under giljo_skills_dismissed_for_<version> when user closes the drift banner', async () => {
    const ls = makeLocalStorage({ giljo_skills_version: '1.1.10' })
    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      writable: true,
      value: ls,
    })

    apiClientMock.get.mockImplementation((url) => {
      if (url === '/api/system/status') {
        return Promise.resolve({
          data: { pending_migrations: false, update_available: false, commits_behind: 0 },
        })
      }
      if (url === '/api/notifications/check-skills-version') {
        return Promise.resolve({
          data: {
            installed: '1.1.10',
            current: '1.1.11',
            drift_detected: true,
            never_installed: false,
            message: 'A newer skills bundle is available',
          },
        })
      }
      return Promise.resolve({ data: {} })
    })

    const wrapper = mount(SystemStatusBanner, { global: { plugins: [pinia] } })
    await flushPromises()
    await wrapper.vm.$nextTick()

    // Trigger dismissSkills() via exposed action — emit close on the alert.
    // Component must expose dismissSkills via defineExpose for direct invocation
    // OR react to the click:close event. We invoke via the exposed method.
    const vm = wrapper.vm
    expect(typeof vm.dismissSkills).toBe('function')
    vm.dismissSkills()
    await wrapper.vm.$nextTick()

    expect(ls.setItem).toHaveBeenCalledWith('giljo_skills_dismissed_for_1.1.11', 'true')
  })

  it('does not show the drift banner when the current version is already dismissed', async () => {
    const ls = makeLocalStorage({ giljo_skills_version: '1.1.10' })
    // Property key with dots — set on the backing store directly.
    ls._backing['giljo_skills_dismissed_for_1.1.11'] = 'true'
    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      writable: true,
      value: ls,
    })

    apiClientMock.get.mockImplementation((url) => {
      if (url === '/api/system/status') {
        return Promise.resolve({
          data: { pending_migrations: false, update_available: false, commits_behind: 0 },
        })
      }
      if (url === '/api/notifications/check-skills-version') {
        return Promise.resolve({
          data: {
            installed: '1.1.10',
            current: '1.1.11',
            drift_detected: true,
            never_installed: false,
            message: 'A newer skills bundle is available',
          },
        })
      }
      return Promise.resolve({ data: {} })
    })

    const wrapper = mount(SystemStatusBanner, { global: { plugins: [pinia] } })
    await flushPromises()
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).not.toMatch(/CLI skills|skills bundle/i)
  })
})
