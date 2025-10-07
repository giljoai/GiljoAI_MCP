/**
 * Mock setup utilities for setup wizard tests
 * Provides consistent mocks for fetch, window APIs, and router
 */

import { vi } from 'vitest'

/**
 * Mock fetch API with configurable responses
 */
export function mockFetchAPI() {
  const mockFetch = vi.fn()
  global.fetch = mockFetch
  return mockFetch
}

/**
 * Mock installation info response
 */
export function mockInstallationInfo(platform = 'windows', path = 'F:\\GiljoAI_MCP') {
  return {
    ok: true,
    json: async () => ({
      installation_path: path,
      platform: platform,
    }),
  }
}

/**
 * Mock setup status response
 */
export function mockSetupStatus(completed = false) {
  return {
    ok: true,
    json: async () => ({
      completed,
      database_configured: true,
      tools_attached: [],
      network_mode: 'localhost',
    }),
  }
}

/**
 * Mock complete setup response
 */
export function mockCompleteSetup(mode = 'localhost', apiKey = null) {
  return {
    ok: true,
    json: async () => ({
      success: true,
      message: `Setup completed in ${mode} mode`,
      api_key: apiKey,
      requires_restart: mode === 'lan',
    }),
  }
}

/**
 * Mock window APIs required by Vuetify and tests
 */
export function mockWindowAPIs() {
  // Mock visualViewport
  Object.defineProperty(window, 'visualViewport', {
    writable: true,
    configurable: true,
    value: {
      width: 1024,
      height: 768,
      scale: 1,
      offsetLeft: 0,
      offsetTop: 0,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    },
  })

  // Mock window.location.href
  delete window.location
  window.location = {
    href: 'http://localhost:7274/',
    protocol: 'http:',
    host: 'localhost:7274',
    hostname: 'localhost',
    port: '7274',
    pathname: '/',
    search: '',
    hash: '',
    origin: 'http://localhost:7274',
  }

  // Mock navigator.clipboard
  Object.assign(navigator, {
    clipboard: {
      writeText: vi.fn().mockResolvedValue(undefined),
      readText: vi.fn().mockResolvedValue(''),
    },
  })

  // Mock user agent
  Object.defineProperty(window.navigator, 'userAgent', {
    value: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    configurable: true,
  })
}

/**
 * Mock router with setup-aware guard
 */
export async function createMockRouter(setupCompleted = false) {
  const { createRouter, createMemoryHistory } = await import('vue-router')

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: '/',
        name: 'Dashboard',
        component: { template: '<div>Dashboard</div>' },
      },
      {
        path: '/setup',
        name: 'Setup',
        component: { template: '<div>Setup</div>' },
        meta: { requiresSetup: false },
      },
    ],
  })

  // Add navigation guard
  router.beforeEach(async (to, from, next) => {
    if (to.meta.requiresSetup === false) {
      next()
      return
    }

    if (!setupCompleted && to.path !== '/setup') {
      next('/setup')
    } else {
      next()
    }
  })

  return router
}

/**
 * Create a complete mock environment for setup wizard tests
 */
export function setupTestEnvironment() {
  mockWindowAPIs()
  const mockFetch = mockFetchAPI()

  // Default mock responses
  mockFetch.mockImplementation((url) => {
    if (url.includes('/api/setup/installation-info')) {
      return Promise.resolve(mockInstallationInfo())
    }
    if (url.includes('/api/setup/status')) {
      return Promise.resolve(mockSetupStatus(false))
    }
    if (url.includes('/api/setup/complete')) {
      return Promise.resolve(mockCompleteSetup())
    }

    // Default fallback
    return Promise.resolve({
      ok: true,
      json: async () => ({}),
    })
  })

  return { mockFetch }
}

/**
 * Clean up test environment
 */
export function cleanupTestEnvironment() {
  vi.clearAllMocks()
  vi.resetModules()
}
