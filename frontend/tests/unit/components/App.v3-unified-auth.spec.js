/**
 * Unit tests for App.vue - v3.0 Unified Authentication
 * Tests that localhost detection is REMOVED and authentication is unified for ALL IPs
 *
 * CRITICAL: These tests verify Phase 1 of Handover 0004
 * - Localhost should NOT bypass authentication
 * - Network IP should NOT bypass authentication
 * - ALL users should follow identical authentication flow
 *
 * Expected to FAIL initially with current localhost bypass logic
 * Expected to PASS after removing localhost bypass from App.vue
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { setActivePinia, createPinia } from 'pinia'
import { useUserStore } from '@/stores/user'
import App from '@/App.vue'

// Mock stores
vi.mock('@/stores/websocket', () => ({
  useWebSocketStore: () => ({
    isConnected: false,
    connect: vi.fn(),
    disconnect: vi.fn(),
  }),
}))

vi.mock('@/stores/agents', () => ({
  useAgentStore: () => ({
    activeAgents: [],
    fetchAgents: vi.fn(),
  }),
}))

vi.mock('@/stores/messages', () => ({
  useMessageStore: () => ({
    pendingMessages: [],
    fetchMessages: vi.fn(),
  }),
}))

vi.mock('@/composables/useKeyboardShortcuts', () => ({
  useKeyboardShortcuts: () => ({
    isHelpModalOpen: false,
    hideHelp: vi.fn(),
    shortcuts: [],
  }),
}))

describe('App.vue - v3.0 Unified Authentication (Phase 1 Tests)', () => {
  let wrapper
  let userStore
  let router
  let vuetify
  let apiMock
  let originalHostname

  beforeEach(() => {
    // Save original hostname
    originalHostname = window.location.hostname

    // Create fresh pinia instance
    setActivePinia(createPinia())
    userStore = useUserStore()

    // Create router
    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', name: 'Dashboard', component: { template: '<div>Dashboard</div>' } },
        { path: '/login', name: 'Login', component: { template: '<div>Login</div>' } },
        { path: '/setup', name: 'Setup', component: { template: '<div>Setup</div>' } },
      ],
    })

    // Create vuetify instance
    vuetify = createVuetify({
      components,
      directives,
    })

    // Mock API with dynamic import to allow per-test customization
    apiMock = {
      auth: {
        me: vi.fn(),
        logout: vi.fn(),
      },
    }
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
    vi.clearAllMocks()
  })

  /**
   * Helper function to mock window.location.hostname
   * Using delete and redefine for test environment compatibility
   */
  const mockHostname = (hostname) => {
    delete window.location
    window.location = { hostname, pathname: '/' }
  }

  /**
   * Helper function to mount App component with mocked API
   */
  const mountApp = async (apiResponse) => {
    // Mock the API module
    vi.doMock('@/services/api', () => ({
      default: apiMock,
    }))

    if (apiResponse) {
      apiMock.auth.me.mockImplementation(apiResponse)
    }

    wrapper = mount(App, {
      global: {
        plugins: [router, vuetify],
      },
    })

    await flushPromises()
    return wrapper
  }

  describe('CRITICAL: Localhost Authentication Unified Behavior', () => {
    /**
     * TEST 1: Localhost should require authentication (no bypass)
     * Expected to FAIL with current code (localhost bypasses auth)
     * Expected to PASS after removing localhost bypass
     */
    it('should redirect to login when accessing from localhost without authentication', async () => {
      // Arrange: Mock localhost hostname
      mockHostname('localhost')

      // Arrange: Mock API to return 401 (unauthenticated)
      const mockRouter = vi.spyOn(router, 'push')
      apiMock.auth.me.mockRejectedValue({ response: { status: 401 } })

      // Act: Mount App component
      await mountApp()

      // Assert: Should redirect to login (v3.0 unified behavior)
      // CRITICAL: This FAILS with current code because localhost bypasses auth
      expect(mockRouter).toHaveBeenCalledWith(
        expect.objectContaining({
          path: '/login',
        })
      )
    })

    /**
     * TEST 2: Localhost with 127.0.0.1 should require authentication
     * Expected to FAIL with current code
     * Expected to PASS after removing localhost bypass
     */
    it('should redirect to login when accessing from 127.0.0.1 without authentication', async () => {
      // Arrange: Mock 127.0.0.1 hostname
      mockHostname('127.0.0.1')

      // Arrange: Mock API to return 401 (unauthenticated)
      const mockRouter = vi.spyOn(router, 'push')
      apiMock.auth.me.mockRejectedValue({ response: { status: 401 } })

      // Act: Mount App component
      await mountApp()

      // Assert: Should redirect to login
      expect(mockRouter).toHaveBeenCalledWith(
        expect.objectContaining({
          path: '/login',
        })
      )
    })

    /**
     * TEST 3: Localhost with IPv6 ::1 should require authentication
     * Expected to FAIL with current code
     * Expected to PASS after removing localhost bypass
     */
    it('should redirect to login when accessing from ::1 without authentication', async () => {
      // Arrange: Mock ::1 hostname
      mockHostname('::1')

      // Arrange: Mock API to return 401 (unauthenticated)
      const mockRouter = vi.spyOn(router, 'push')
      apiMock.auth.me.mockRejectedValue({ response: { status: 401 } })

      // Act: Mount App component
      await mountApp()

      // Assert: Should redirect to login
      expect(mockRouter).toHaveBeenCalledWith(
        expect.objectContaining({
          path: '/login',
        })
      )
    })
  })

  describe('Network IP Authentication Unified Behavior (Should Already Pass)', () => {
    /**
     * TEST 4: Network IP should require authentication (existing behavior)
     * Expected to PASS with current code (already redirects)
     * Expected to PASS after changes (behavior unchanged)
     */
    it('should redirect to login when accessing from network IP without authentication', async () => {
      // Arrange: Mock network IP hostname
      mockHostname('10.1.0.164')

      // Arrange: Mock API to return 401 (unauthenticated)
      const mockRouter = vi.spyOn(router, 'push')
      apiMock.auth.me.mockRejectedValue({ response: { status: 401 } })

      // Act: Mount App component
      await mountApp()

      // Assert: Should redirect to login
      expect(mockRouter).toHaveBeenCalledWith(
        expect.objectContaining({
          path: '/login',
        })
      )
    })

    /**
     * TEST 5: Domain name should require authentication
     * Expected to PASS with current and updated code
     */
    it('should redirect to login when accessing from domain without authentication', async () => {
      // Arrange: Mock domain hostname
      mockHostname('giljo.example.com')

      // Arrange: Mock API to return 401 (unauthenticated)
      const mockRouter = vi.spyOn(router, 'push')
      apiMock.auth.me.mockRejectedValue({ response: { status: 401 } })

      // Act: Mount App component
      await mountApp()

      // Assert: Should redirect to login
      expect(mockRouter).toHaveBeenCalledWith(
        expect.objectContaining({
          path: '/login',
        })
      )
    })
  })

  describe('Authenticated Access Works from ANY IP (Unified)', () => {
    /**
     * TEST 6: Authenticated localhost access should work
     * Expected to PASS with current and updated code
     */
    it('should allow access from localhost with valid authentication', async () => {
      // Arrange: Mock localhost hostname
      mockHostname('localhost')

      // Arrange: Mock API to return valid user (authenticated)
      const mockUser = { id: 1, username: 'testuser', role: 'user' }
      apiMock.auth.me.mockResolvedValue({ data: mockUser })

      // Act: Mount App component
      await mountApp()

      // Assert: Should load normally without redirect
      expect(userStore.currentUser).toEqual(mockUser)
      expect(router.currentRoute.value.path).not.toBe('/login')
    })

    /**
     * TEST 7: Authenticated network IP access should work
     * Expected to PASS with current and updated code
     */
    it('should allow access from network IP with valid authentication', async () => {
      // Arrange: Mock network IP hostname
      mockHostname('10.1.0.164')

      // Arrange: Mock API to return valid user (authenticated)
      const mockUser = { id: 1, username: 'testuser', role: 'user' }
      apiMock.auth.me.mockResolvedValue({ data: mockUser })

      // Act: Mount App component
      await mountApp()

      // Assert: Should load normally without redirect
      expect(userStore.currentUser).toEqual(mockUser)
      expect(router.currentRoute.value.path).not.toBe('/login')
    })
  })

  describe('Console Logging Verification (No Localhost Messages)', () => {
    /**
     * TEST 8: Should not log "Not on localhost" messages
     * Expected to FAIL with current code (logs "Not on localhost")
     * Expected to PASS after removing localhost bypass
     */
    it('should not log localhost-specific authentication messages', async () => {
      // Arrange: Mock console.log to capture messages
      const consoleLogSpy = vi.spyOn(console, 'log')
      mockHostname('10.1.0.164')

      // Arrange: Mock API to return 401 (unauthenticated)
      apiMock.auth.me.mockRejectedValue({ response: { status: 401 } })

      // Act: Mount App component
      await mountApp()

      // Assert: Should NOT log "Not on localhost" message
      const localhostMessages = consoleLogSpy.mock.calls.filter(call =>
        call.some(arg => typeof arg === 'string' && arg.includes('Not on localhost'))
      )
      expect(localhostMessages).toHaveLength(0)

      consoleLogSpy.mockRestore()
    })

    /**
     * TEST 9: Should log unified authentication messages
     * Expected to PASS after implementing unified authentication
     */
    it('should log unified authentication messages for all IPs', async () => {
      // Arrange: Mock console.log to capture messages
      const consoleLogSpy = vi.spyOn(console, 'log')

      // Test localhost
      mockHostname('localhost')
      apiMock.auth.me.mockRejectedValue({ response: { status: 401 } })
      await mountApp()

      // Assert: Should log generic "Not authenticated" message
      const authMessages = consoleLogSpy.mock.calls.filter(call =>
        call.some(arg => typeof arg === 'string' && arg.includes('Not authenticated'))
      )
      expect(authMessages.length).toBeGreaterThan(0)

      consoleLogSpy.mockRestore()
    })
  })

  describe('Edge Cases and Error Handling', () => {
    /**
     * TEST 10: Network errors should redirect to login (no localhost bypass)
     */
    it('should redirect to login on network error from localhost', async () => {
      // Arrange: Mock localhost hostname
      mockHostname('localhost')

      // Arrange: Mock API to throw network error
      const mockRouter = vi.spyOn(router, 'push')
      apiMock.auth.me.mockRejectedValue(new Error('Network error'))

      // Act: Mount App component
      await mountApp()

      // Assert: Should redirect to login (no localhost bypass on errors)
      expect(mockRouter).toHaveBeenCalledWith(
        expect.objectContaining({
          path: '/login',
        })
      )
    })

    /**
     * TEST 11: Already on login page should not redirect again
     */
    it('should not redirect when already on login page from localhost', async () => {
      // Arrange: Mock localhost hostname and navigate to login
      mockHostname('localhost')
      await router.push('/login')

      // Arrange: Mock API to return 401
      const mockRouter = vi.spyOn(router, 'push')
      apiMock.auth.me.mockRejectedValue({ response: { status: 401 } })

      // Act: Mount App component
      await mountApp()

      // Assert: Should not redirect again (already on login)
      expect(mockRouter).not.toHaveBeenCalledWith(
        expect.objectContaining({
          path: '/login',
        })
      )
    })
  })

  describe('Code Quality Checks', () => {
    /**
     * TEST 12: App.vue should not contain window.location.hostname checks for auth
     * This is a static code analysis test
     */
    it('should not use window.location.hostname for authentication decisions', async () => {
      // Read App.vue source code
      const fs = await import('fs')
      const path = await import('path')
      const appVuePath = path.resolve(__dirname, '../../../src/App.vue')
      const appVueContent = fs.readFileSync(appVuePath, 'utf-8')

      // Check for localhost detection patterns
      const localhostPatterns = [
        /window\.location\.hostname.*localhost/i,
        /\['localhost',\s*'127\.0\.0\.1',\s*'::1'\]/,
        /const\s+isLocalhost\s*=/i,
      ]

      // Assert: Should not contain localhost detection for authentication
      // Note: Might contain for other purposes (dynamic URLs), so check context
      const authRelatedCode = appVueContent.match(/loadCurrentUser[\s\S]*?catch[\s\S]*?\}/g)
      if (authRelatedCode) {
        localhostPatterns.forEach(pattern => {
          authRelatedCode.forEach(block => {
            expect(block).not.toMatch(pattern)
          })
        })
      }
    })
  })
})
