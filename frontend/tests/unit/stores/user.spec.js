/**
 * Unit tests for user store - authentication and role management
 * Following TDD principles: write tests first, then implement
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
  setTenantKey: vi.fn(),
}))

describe('User Store', () => {
  beforeEach(() => {
    // Create a fresh pinia instance for each test
    setActivePinia(createPinia())
    // Clear all mocks before each test
    vi.clearAllMocks()
  })

  describe('State Management', () => {
    it('should initialize with null user and unauthenticated state', () => {
      const store = useUserStore()

      expect(store.currentUser).toBeNull()
      expect(store.isAuthenticated).toBe(false)
      expect(store.isLoading).toBe(false)
    })
  })

  describe('Getters - Role Checking', () => {
    it('should return false for isAdmin when user is null', () => {
      const store = useUserStore()

      expect(store.isAdmin).toBe(false)
    })

    it('should return true for isAdmin when user role is "admin"', () => {
      const store = useUserStore()
      store.currentUser = { username: 'admin', role: 'admin' }

      expect(store.isAdmin).toBe(true)
    })

    it('should return false for isAdmin when user role is "user"', () => {
      const store = useUserStore()
      store.currentUser = { username: 'testuser', role: 'user' }

      expect(store.isAdmin).toBe(false)
    })

    it('should return true for isAuthenticated when user exists', () => {
      const store = useUserStore()
      store.currentUser = { username: 'testuser', role: 'user' }

      expect(store.isAuthenticated).toBe(true)
    })

    it('should handle case-insensitive role checking', () => {
      const store = useUserStore()
      store.currentUser = { username: 'admin', role: 'Admin' }

      expect(store.isAdmin).toBe(true)
    })
  })

  describe('Actions - fetchCurrentUser', () => {
    it('should fetch current user and update state on success', async () => {
      const store = useUserStore()
      const mockUser = {
        id: 1,
        username: 'testuser',
        role: 'user',
        email: 'test@example.com'
      }

      api.auth.me.mockResolvedValue({ data: mockUser })

      await store.fetchCurrentUser()

      expect(store.currentUser).toEqual(mockUser)
      expect(store.isAuthenticated).toBe(true)
      expect(api.auth.me).toHaveBeenCalledTimes(1)
    })

    it('should set loading state during fetch', async () => {
      const store = useUserStore()

      api.auth.me.mockImplementation(() =>
        new Promise(resolve => setTimeout(() => resolve({ data: {} }), 100))
      )

      const fetchPromise = store.fetchCurrentUser()
      expect(store.isLoading).toBe(true)

      await fetchPromise
      expect(store.isLoading).toBe(false)
    })

    it('should handle fetch error and set user to null', async () => {
      const store = useUserStore()

      api.auth.me.mockRejectedValue(new Error('Unauthorized'))

      await store.fetchCurrentUser()

      expect(store.currentUser).toBeNull()
      expect(store.isAuthenticated).toBe(false)
      expect(store.isLoading).toBe(false)
    })
  })

  describe('Actions - login', () => {
    it('should login user and fetch user data on success', async () => {
      const store = useUserStore()
      const mockUser = { id: 1, username: 'admin', role: 'admin' }

      api.auth.login.mockResolvedValue({ data: { success: true } })
      api.auth.me.mockResolvedValue({ data: mockUser })

      const result = await store.login('admin', 'password123')

      expect(result).toBe(true)
      expect(store.currentUser).toEqual(mockUser)
      expect(api.auth.login).toHaveBeenCalledWith('admin', 'password123')
      expect(api.auth.me).toHaveBeenCalled()
    })

    it('should return false on login failure', async () => {
      const store = useUserStore()

      api.auth.login.mockRejectedValue(new Error('Invalid credentials'))

      const result = await store.login('admin', 'wrongpassword')

      expect(result).toBe(false)
      expect(store.currentUser).toBeNull()
    })
  })

  describe('Actions - logout', () => {
    it('should clear user state and call logout endpoint', async () => {
      const store = useUserStore()
      store.currentUser = { username: 'testuser', role: 'user' }

      api.auth.logout.mockResolvedValue({ data: { success: true } })

      await store.logout()

      expect(store.currentUser).toBeNull()
      expect(store.isAuthenticated).toBe(false)
      expect(api.auth.logout).toHaveBeenCalledTimes(1)
    })

    it('should clear user state even if logout endpoint fails', async () => {
      const store = useUserStore()
      store.currentUser = { username: 'testuser', role: 'user' }

      api.auth.logout.mockRejectedValue(new Error('Network error'))

      await store.logout()

      expect(store.currentUser).toBeNull()
      expect(store.isAuthenticated).toBe(false)
    })
  })

  describe('Role-based Access Control', () => {
    it('should correctly identify admin users', () => {
      const store = useUserStore()

      // Test admin user
      store.currentUser = { username: 'admin', role: 'admin' }
      expect(store.isAdmin).toBe(true)

      // Test regular user
      store.currentUser = { username: 'user', role: 'user' }
      expect(store.isAdmin).toBe(false)

      // Test no user
      store.currentUser = null
      expect(store.isAdmin).toBe(false)
    })

    it('should handle missing role gracefully', () => {
      const store = useUserStore()
      store.currentUser = { username: 'testuser' }

      expect(store.isAdmin).toBe(false)
      expect(store.isAuthenticated).toBe(true)
    })
  })

  describe('Organization Integration (Handover 0424h)', () => {
    it('should initialize with null org state', () => {
      const store = useUserStore()

      expect(store.orgId).toBeNull()
      expect(store.orgName).toBeNull()
      expect(store.orgRole).toBeNull()
    })

    it('should store org data from API response', async () => {
      const store = useUserStore()
      const mockUser = {
        id: 'user-1',
        username: 'testuser',
        email: 'test@example.com',
        tenant_key: 'tk-123',
        role: 'member',
        org_id: 'org-123',
        org_name: 'Test Organization',
        org_role: 'admin'
      }

      api.auth.me.mockResolvedValue({ data: mockUser })

      await store.fetchCurrentUser()

      expect(store.orgId).toBe('org-123')
      expect(store.orgName).toBe('Test Organization')
      expect(store.orgRole).toBe('admin')
    })

    it('should provide currentOrg computed property', async () => {
      const store = useUserStore()
      const mockUser = {
        id: 'user-1',
        username: 'testuser',
        org_id: 'org-123',
        org_name: 'Test Org',
        org_role: 'member'
      }

      api.auth.me.mockResolvedValue({ data: mockUser })
      await store.fetchCurrentUser()

      const currentOrg = store.currentOrg
      expect(currentOrg).toEqual({
        id: 'org-123',
        name: 'Test Org',
        role: 'member'
      })
    })

    it('should return null for currentOrg when no org data', () => {
      const store = useUserStore()

      expect(store.currentOrg).toBeNull()
    })

    it('should provide isOrgAdmin computed property', async () => {
      const store = useUserStore()

      // Test with admin role
      let mockUser = {
        id: 'user-1',
        org_role: 'admin'
      }
      api.auth.me.mockResolvedValue({ data: mockUser })
      await store.fetchCurrentUser()
      expect(store.isOrgAdmin).toBe(true)

      // Test with owner role
      mockUser = { id: 'user-1', org_role: 'owner' }
      api.auth.me.mockResolvedValue({ data: mockUser })
      await store.fetchCurrentUser()
      expect(store.isOrgAdmin).toBe(true)

      // Test with member role
      mockUser = { id: 'user-1', org_role: 'member' }
      api.auth.me.mockResolvedValue({ data: mockUser })
      await store.fetchCurrentUser()
      expect(store.isOrgAdmin).toBe(false)

      // Test with viewer role
      mockUser = { id: 'user-1', org_role: 'viewer' }
      api.auth.me.mockResolvedValue({ data: mockUser })
      await store.fetchCurrentUser()
      expect(store.isOrgAdmin).toBe(false)
    })

    it('should provide isOrgOwner computed property', async () => {
      const store = useUserStore()

      // Test with owner role
      let mockUser = { id: 'user-1', org_role: 'owner' }
      api.auth.me.mockResolvedValue({ data: mockUser })
      await store.fetchCurrentUser()
      expect(store.isOrgOwner).toBe(true)

      // Test with admin role
      mockUser = { id: 'user-1', org_role: 'admin' }
      api.auth.me.mockResolvedValue({ data: mockUser })
      await store.fetchCurrentUser()
      expect(store.isOrgOwner).toBe(false)

      // Test with member role
      mockUser = { id: 'user-1', org_role: 'member' }
      api.auth.me.mockResolvedValue({ data: mockUser })
      await store.fetchCurrentUser()
      expect(store.isOrgOwner).toBe(false)
    })

    it('should handle missing org data gracefully', async () => {
      const store = useUserStore()
      const mockUser = {
        id: 'user-1',
        username: 'testuser',
        role: 'member'
        // No org_id, org_name, org_role
      }

      api.auth.me.mockResolvedValue({ data: mockUser })
      await store.fetchCurrentUser()

      expect(store.orgId).toBeNull()
      expect(store.orgName).toBeNull()
      expect(store.orgRole).toBeNull()
      expect(store.currentOrg).toBeNull()
      expect(store.isOrgAdmin).toBe(false)
      expect(store.isOrgOwner).toBe(false)
    })

    it('should clear org fields on logout', async () => {
      const store = useUserStore()

      // First set org data
      store.orgId = 'org-123'
      store.orgName = 'Test Org'
      store.orgRole = 'admin'
      store.currentUser = { id: 'user-1', username: 'testuser' }

      api.auth.logout.mockResolvedValue({ data: { success: true } })

      await store.logout()

      expect(store.currentUser).toBeNull()
      expect(store.orgId).toBeNull()
      expect(store.orgName).toBeNull()
      expect(store.orgRole).toBeNull()
    })

    it('should clear org fields on login failure', async () => {
      const store = useUserStore()

      // Set initial org state
      store.orgId = 'org-123'
      store.orgName = 'Test Org'
      store.orgRole = 'admin'

      api.auth.login.mockRejectedValue(new Error('Invalid credentials'))

      const result = await store.login('user', 'wrong')

      expect(result).toBe(false)
      expect(store.currentUser).toBeNull()
      expect(store.orgId).toBeNull()
      expect(store.orgName).toBeNull()
      expect(store.orgRole).toBeNull()
    })

    it('should clear org fields on fetchCurrentUser failure', async () => {
      const store = useUserStore()

      // Set initial org state
      store.orgId = 'org-123'
      store.orgName = 'Test Org'
      store.orgRole = 'admin'

      api.auth.me.mockRejectedValue(new Error('Unauthorized'))

      const result = await store.fetchCurrentUser()

      expect(result).toBe(false)
      expect(store.currentUser).toBeNull()
      expect(store.orgId).toBeNull()
      expect(store.orgName).toBeNull()
      expect(store.orgRole).toBeNull()
    })

    it('should clear org fields on checkAuth failure', async () => {
      const store = useUserStore()

      // Set initial org state
      store.orgId = 'org-123'
      store.orgName = 'Test Org'
      store.orgRole = 'admin'

      api.auth.me.mockRejectedValue(new Error('Session expired'))

      const result = await store.checkAuth()

      expect(result).toBe(false)
      expect(store.currentUser).toBeNull()
      expect(store.orgId).toBeNull()
      expect(store.orgName).toBeNull()
      expect(store.orgRole).toBeNull()
    })

    it('should provide clearUser() method', () => {
      const store = useUserStore()

      // Set user and org data
      store.currentUser = { id: 'user-1', username: 'testuser' }
      store.isLoading = true
      store.orgId = 'org-123'
      store.orgName = 'Test Org'
      store.orgRole = 'admin'

      // Call clearUser
      store.clearUser()

      expect(store.currentUser).toBeNull()
      expect(store.isLoading).toBe(false)
      expect(store.orgId).toBeNull()
      expect(store.orgName).toBeNull()
      expect(store.orgRole).toBeNull()
    })

    it('should update org fields on checkAuth success', async () => {
      const store = useUserStore()
      const mockUser = {
        id: 'user-1',
        username: 'testuser',
        tenant_key: 'tk-123',
        role: 'member',
        org_id: 'org-456',
        org_name: 'New Organization',
        org_role: 'owner'
      }

      api.auth.me.mockResolvedValue({ data: mockUser })

      const result = await store.checkAuth()

      expect(result).toBe(true)
      expect(store.orgId).toBe('org-456')
      expect(store.orgName).toBe('New Organization')
      expect(store.orgRole).toBe('owner')
      expect(store.isOrgOwner).toBe(true)
    })
  })
})
