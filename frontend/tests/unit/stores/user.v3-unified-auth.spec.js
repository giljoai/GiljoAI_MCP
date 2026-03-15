/**
 * Unit tests for user store - v3.0 Unified Authentication
 * Tests that localhost detection is REMOVED from checkAuth() method
 *
 * CRITICAL: These tests verify Phase 1 of Handover 0004
 * - checkAuth() should NOT bypass authentication for localhost
 * - checkAuth() should return false for ALL IPs without valid JWT
 * - Unified authentication behavior regardless of access method
 *
 * Expected to FAIL initially with current localhost bypass logic
 * Expected to PASS after removing localhost bypass from user store
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useUserStore } from '@/stores/user'
import api from '@/services/api'

// Mock the API service
vi.mock('@/services/api', () => ({
  default: {
    auth: {
      me: vi.fn(),
      login: vi.fn(),
      logout: vi.fn(),
    },
  },
}))

describe('User Store - v3.0 Unified Authentication (Phase 1 Tests)', () => {
  let originalHostname

  beforeEach(() => {
    // Save original hostname
    originalHostname = window.location.hostname

    // Create a fresh pinia instance for each test
    setActivePinia(createPinia())

    // Clear all mocks before each test
    vi.clearAllMocks()
  })

  afterEach(() => {
    // Tests clean up automatically in vitest
  })

  /**
   * Helper function to mock window.location.hostname
   * Using delete and redefine for test environment compatibility
   */
  const mockHostname = (hostname) => {
    delete window.location
    window.location = { hostname, pathname: '/' }
  }

  describe('CRITICAL: checkAuth() Unified Behavior - No Localhost Bypass', () => {
    /**
     * TEST 1: checkAuth() from localhost should return false without valid JWT
     * Expected to FAIL with current code (returns true for localhost)
     * Expected to PASS after removing localhost bypass
     */
    it('should return false when checking auth from localhost without valid JWT', async () => {
      // Arrange: Mock localhost hostname
      mockHostname('localhost')

      // Arrange: Mock API to return 401 (unauthenticated)
      api.auth.me.mockRejectedValue({ response: { status: 401 } })

      const store = useUserStore()

      // Act: Check authentication
      const result = await store.checkAuth()

      // Assert: Should return false (v3.0 unified behavior)
      // CRITICAL: This FAILS with current code because localhost returns true
      expect(result).toBe(false)
      expect(store.currentUser).toBeNull()
    })

    /**
     * TEST 2: checkAuth() from 127.0.0.1 should return false without valid JWT
     * Expected to FAIL with current code
     * Expected to PASS after removing localhost bypass
     */
    it('should return false when checking auth from 127.0.0.1 without valid JWT', async () => {
      // Arrange: Mock 127.0.0.1 hostname
      mockHostname('127.0.0.1')

      // Arrange: Mock API to return 401 (unauthenticated)
      api.auth.me.mockRejectedValue({ response: { status: 401 } })

      const store = useUserStore()

      // Act: Check authentication
      const result = await store.checkAuth()

      // Assert: Should return false
      expect(result).toBe(false)
      expect(store.currentUser).toBeNull()
    })

    /**
     * TEST 3: checkAuth() from IPv6 ::1 should return false without valid JWT
     * Expected to FAIL with current code
     * Expected to PASS after removing localhost bypass
     */
    it('should return false when checking auth from ::1 without valid JWT', async () => {
      // Arrange: Mock ::1 hostname
      mockHostname('::1')

      // Arrange: Mock API to return 401 (unauthenticated)
      api.auth.me.mockRejectedValue({ response: { status: 401 } })

      const store = useUserStore()

      // Act: Check authentication
      const result = await store.checkAuth()

      // Assert: Should return false
      expect(result).toBe(false)
      expect(store.currentUser).toBeNull()
    })

    /**
     * TEST 4: checkAuth() from network IP should return false without valid JWT
     * Expected to PASS with current code (already returns false)
     * Expected to PASS after changes (behavior unchanged)
     */
    it('should return false when checking auth from network IP without valid JWT', async () => {
      // Arrange: Mock network IP hostname
      mockHostname('10.1.0.164')

      // Arrange: Mock API to return 401 (unauthenticated)
      api.auth.me.mockRejectedValue({ response: { status: 401 } })

      const store = useUserStore()

      // Act: Check authentication
      const result = await store.checkAuth()

      // Assert: Should return false
      expect(result).toBe(false)
      expect(store.currentUser).toBeNull()
    })

    /**
     * TEST 5: checkAuth() from domain should return false without valid JWT
     * Expected to PASS with current and updated code
     */
    it('should return false when checking auth from domain without valid JWT', async () => {
      // Arrange: Mock domain hostname
      mockHostname('giljo.example.com')

      // Arrange: Mock API to return 401 (unauthenticated)
      api.auth.me.mockRejectedValue({ response: { status: 401 } })

      const store = useUserStore()

      // Act: Check authentication
      const result = await store.checkAuth()

      // Assert: Should return false
      expect(result).toBe(false)
      expect(store.currentUser).toBeNull()
    })
  })

  describe('checkAuth() with Valid JWT Works from ANY IP (Unified)', () => {
    /**
     * TEST 6: checkAuth() should return true with valid JWT from localhost
     * Expected to PASS with current and updated code
     */
    it('should return true when checking auth from localhost with valid JWT', async () => {
      // Arrange: Mock localhost hostname
      mockHostname('localhost')

      // Arrange: Mock API to return valid user
      const mockUser = { id: 1, username: 'testuser', role: 'user' }
      api.auth.me.mockResolvedValue({ data: mockUser })

      const store = useUserStore()

      // Act: Check authentication
      const result = await store.checkAuth()

      // Assert: Should return true with valid JWT
      expect(result).toBe(true)
      expect(store.currentUser).toEqual(mockUser)
    })

    /**
     * TEST 7: checkAuth() should return true with valid JWT from network IP
     * Expected to PASS with current and updated code
     */
    it('should return true when checking auth from network IP with valid JWT', async () => {
      // Arrange: Mock network IP hostname
      mockHostname('10.1.0.164')

      // Arrange: Mock API to return valid user
      const mockUser = { id: 1, username: 'testuser', role: 'user' }
      api.auth.me.mockResolvedValue({ data: mockUser })

      const store = useUserStore()

      // Act: Check authentication
      const result = await store.checkAuth()

      // Assert: Should return true with valid JWT
      expect(result).toBe(true)
      expect(store.currentUser).toEqual(mockUser)
    })

    /**
     * TEST 8: checkAuth() should return true with valid JWT from any hostname
     * Expected to PASS with current and updated code
     */
    it('should return true when checking auth from any hostname with valid JWT', async () => {
      // Test multiple hostnames
      const hostnames = ['localhost', '127.0.0.1', '::1', '10.1.0.164', 'giljo.example.com']

      for (const hostname of hostnames) {
        // Arrange: Mock hostname
        mockHostname(hostname)

        // Arrange: Mock API to return valid user
        const mockUser = { id: 1, username: 'testuser', role: 'user' }
        api.auth.me.mockResolvedValue({ data: mockUser })

        // Reset store for each test
        setActivePinia(createPinia())
        const store = useUserStore()

        // Act: Check authentication
        const result = await store.checkAuth()

        // Assert: Should return true regardless of hostname
        expect(result).toBe(true)
        expect(store.currentUser).toEqual(mockUser)
      }
    })
  })

  describe('Error Handling and Edge Cases', () => {
    /**
     * TEST 9: checkAuth() should handle network errors uniformly
     */
    it('should return false on network error regardless of hostname', async () => {
      // Test both localhost and network IP
      const hostnames = ['localhost', '10.1.0.164']

      for (const hostname of hostnames) {
        // Arrange: Mock hostname
        mockHostname(hostname)

        // Arrange: Mock API to throw network error
        api.auth.me.mockRejectedValue(new Error('Network error'))

        // Reset store for each test
        setActivePinia(createPinia())
        const store = useUserStore()

        // Act: Check authentication
        const result = await store.checkAuth()

        // Assert: Should return false (no localhost bypass on errors)
        expect(result).toBe(false)
        expect(store.currentUser).toBeNull()
      }
    })

    /**
     * TEST 10: checkAuth() should set loading state correctly
     */
    // Test for isLoading removed: the user store does not expose an isLoading property.
    // Authentication loading state is managed internally without a public reactive ref.
  })

  describe('Code Quality Checks', () => {
    /**
     * TEST 11: user store should not contain window.location.hostname checks
     * This is a static code analysis test
     */
    it('should not use window.location.hostname in checkAuth() for authentication bypass', async () => {
      // Read user store source code
      const fs = await import('fs')
      const path = await import('path')
      const userStorePath = path.resolve(__dirname, '../../../src/stores/user.js')
      const userStoreContent = fs.readFileSync(userStorePath, 'utf-8')

      // Extract checkAuth method
      const checkAuthMatch = userStoreContent.match(/async function checkAuth\(\)[\s\S]*?\n  \}/g)

      if (checkAuthMatch) {
        const checkAuthCode = checkAuthMatch[0]

        // Check for localhost detection patterns
        const localhostPatterns = [
          /window\.location\.hostname/i,
          /\['localhost',\s*'127\.0\.0\.1',\s*'::1'\]/,
          /const\s+isLocalhost\s*=/i,
        ]

        // Assert: checkAuth should not contain localhost detection
        localhostPatterns.forEach(pattern => {
          expect(checkAuthCode).not.toMatch(pattern)
        })
      }
    })

    /**
     * TEST 12: checkAuth should always return boolean based on API response only
     */
    it('should return boolean based solely on API response, not hostname', async () => {
      // Arrange: Mock localhost hostname
      mockHostname('localhost')

      const store = useUserStore()

      // Test 1: API success -> true
      api.auth.me.mockResolvedValue({ data: { id: 1, username: 'test' } })
      expect(await store.checkAuth()).toBe(true)

      // Reset
      store.currentUser = null

      // Test 2: API failure -> false (no localhost bypass)
      api.auth.me.mockRejectedValue({ response: { status: 401 } })
      expect(await store.checkAuth()).toBe(false)
    })
  })

  describe('Integration with Other Store Methods', () => {
    /**
     * TEST 13: fetchCurrentUser should work uniformly regardless of hostname
     */
    it('should fetch current user successfully from any hostname', async () => {
      const hostnames = ['localhost', '127.0.0.1', '10.1.0.164']

      for (const hostname of hostnames) {
        // Arrange: Mock hostname
        mockHostname(hostname)

        // Arrange: Mock API to return valid user
        const mockUser = { id: 1, username: 'testuser', role: 'user' }
        api.auth.me.mockResolvedValue({ data: mockUser })

        // Reset store for each test
        setActivePinia(createPinia())
        const store = useUserStore()

        // Act: Fetch current user
        const result = await store.fetchCurrentUser()

        // Assert: Should succeed from any hostname
        expect(result).toBe(true)
        expect(store.currentUser).toEqual(mockUser)
      }
    })

    /**
     * TEST 14: login should work uniformly regardless of hostname
     */
    it('should login successfully from any hostname', async () => {
      const hostnames = ['localhost', '10.1.0.164']

      for (const hostname of hostnames) {
        // Arrange: Mock hostname
        mockHostname(hostname)

        // Arrange: Mock successful login and user fetch
        const mockUser = { id: 1, username: 'testuser', role: 'user' }
        api.auth.login.mockResolvedValue({ data: { success: true } })
        api.auth.me.mockResolvedValue({ data: mockUser })

        // Reset store for each test
        setActivePinia(createPinia())
        const store = useUserStore()

        // Act: Login
        const result = await store.login('testuser', 'password')

        // Assert: Should succeed from any hostname
        expect(result).toBe(true)
        expect(store.currentUser).toEqual(mockUser)
      }
    })
  })
})
