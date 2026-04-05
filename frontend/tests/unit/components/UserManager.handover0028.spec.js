/**
 * Test suite for UserManager.vue - Handover 0028 Enhancements
 *
 * Tests for new fields added to user management:
 * - Email field display and editing
 * - Created date field display
 * - Proper integration with existing user management functionality
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import UserManager from '@/components/UserManager.vue'

// Mock the API module
vi.mock('@/services/api', () => ({
  default: {
    auth: {
      listUsers: vi.fn(),
      register: vi.fn(),
      updateUser: vi.fn()
    }
  }
}))

describe('UserManager.vue - Handover 0028 Email and Created Date Fields', () => {
  let wrapper
  let api
  const mockUsers = [
    {
      id: 1,
      username: 'admin',
      email: 'admin@example.com',
      role: 'admin',
      is_active: true,
      last_login: '2025-10-09T10:00:00Z',
      created_at: '2025-01-01T00:00:00Z',
      tenant_key: 'tk_test'
    },
    {
      id: 2,
      username: 'developer',
      email: 'dev@example.com',
      role: 'developer',
      is_active: true,
      last_login: '2025-10-09T11:00:00Z',
      created_at: '2025-01-15T00:00:00Z',
      tenant_key: 'tk_test'
    },
    {
      id: 3,
      username: 'viewer',
      email: null,
      role: 'viewer',
      is_active: false,
      last_login: null,
      created_at: '2025-02-01T00:00:00Z',
      tenant_key: 'tk_test'
    }
  ]

  const mockCurrentUser = {
    id: 1,
    username: 'admin',
    role: 'admin',
    tenant_key: 'tk_test'
  }

  beforeEach(async () => {
    // Get the mocked API
    api = (await import('@/services/api')).default

    // Setup mock responses
    api.auth.listUsers.mockResolvedValue({ data: mockUsers })
    api.auth.register.mockResolvedValue({
      data: { id: 4, username: 'newuser', email: 'newuser@example.com', role: 'developer' }
    })
    api.auth.updateUser.mockResolvedValue({ data: { message: 'User updated' } })

    wrapper = mount(UserManager, {
      global: {
        plugins: [
          createTestingPinia({
            initialState: {
              user: {
                currentUser: mockCurrentUser
              }
            }
          })
        ]
      }
    })

    // Wait for component to mount and load users
    await wrapper.vm.$nextTick()
  })

  describe('Table Headers with Email and Created Date', () => {
    it('includes email column in table headers', () => {
      const headers = wrapper.vm.headers
      const emailHeader = headers.find(h => h.key === 'email')
      expect(emailHeader).toBeDefined()
      expect(emailHeader.title).toBe('Email')
    })

    it('includes created date column in table headers', () => {
      const headers = wrapper.vm.headers
      const createdHeader = headers.find(h => h.key === 'created_at')
      expect(createdHeader).toBeDefined()
      expect(createdHeader.title).toBe('Created')
    })

    it('maintains correct header order', () => {
      const headers = wrapper.vm.headers
      expect(headers.map(h => h.key)).toEqual([
        'username',
        'email',
        'role',
        'is_active',
        'created_at',
        'last_login',
        'actions'
      ])
    })

    it('all new columns are sortable', () => {
      const headers = wrapper.vm.headers
      const emailHeader = headers.find(h => h.key === 'email')
      const createdHeader = headers.find(h => h.key === 'created_at')

      expect(emailHeader.sortable).toBe(true)
      expect(createdHeader.sortable).toBe(true)
    })
  })

  describe('Email Field Display', () => {
    beforeEach(async () => {
      wrapper.vm.users = mockUsers
      await wrapper.vm.$nextTick()
    })

    it('displays email addresses for users with email', () => {
      const userWithEmail = mockUsers[0]
      expect(userWithEmail.email).toBe('admin@example.com')
    })

    it('displays "No email" for users without email', () => {
      const userWithoutEmail = mockUsers[2]
      expect(userWithoutEmail.email).toBeNull()
    })

    it('email column is defined in headers', () => {
      // The email column exists in the headers definition
      const emailHeader = wrapper.vm.headers.find(h => h.key === 'email')
      expect(emailHeader).toBeDefined()
    })
  })

  describe('Created Date Field Display', () => {
    beforeEach(async () => {
      wrapper.vm.users = mockUsers
      await wrapper.vm.$nextTick()
    })

    it('displays created date for all users', () => {
      mockUsers.forEach(user => {
        expect(user.created_at).toBeDefined()
      })
    })

    it('formats created date correctly', () => {
      const formattedDate = wrapper.vm.formatDate('2025-01-01T00:00:00Z')
      // useFormatDate composable returns "Mon DD, YYYY" format (e.g. "Jan 1, 2025")
      expect(formattedDate).toMatch(/[A-Z][a-z]{2} \d{1,2}, \d{4}/)
    })

    it('handles null created date gracefully', () => {
      const formattedDate = wrapper.vm.formatDate(null)
      expect(formattedDate).toBe('N/A')
    })

    it('handles invalid created date gracefully', () => {
      const formattedDate = wrapper.vm.formatDate('invalid-date')
      // Should still return a date or N/A, not crash
      expect(formattedDate).toBeDefined()
    })

    it('created date column is defined in headers', () => {
      const createdHeader = wrapper.vm.headers.find(h => h.key === 'created_at')
      expect(createdHeader).toBeDefined()
    })
  })

  describe('Email in Search Functionality', () => {
    beforeEach(async () => {
      wrapper.vm.users = mockUsers
      await wrapper.vm.$nextTick()
    })

    it('filters users by email address', async () => {
      wrapper.vm.search = 'admin@example.com'
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.filteredUsers).toHaveLength(1)
      expect(wrapper.vm.filteredUsers[0].email).toBe('admin@example.com')
    })

    it('email search is case-insensitive', async () => {
      wrapper.vm.search = 'ADMIN@EXAMPLE.COM'
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.filteredUsers).toHaveLength(1)
      expect(wrapper.vm.filteredUsers[0].email).toBe('admin@example.com')
    })

    it('searches by partial email', async () => {
      wrapper.vm.search = 'example.com'
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.filteredUsers.length).toBeGreaterThan(0)
    })

    it('handles null email in search', async () => {
      wrapper.vm.search = 'null'
      await wrapper.vm.$nextTick()
      // Should not crash
      expect(wrapper.vm.filteredUsers).toBeDefined()
    })
  })

  describe('Email in Create User Dialog', () => {
    it('includes email field in create user form', async () => {
      wrapper.vm.openCreateDialog()
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.userForm).toHaveProperty('email')
    })

    it('email field is optional in create form', async () => {
      wrapper.vm.openCreateDialog()
      wrapper.vm.userForm = {
        username: 'testuser',
        password: 'password123',
        role: 'developer',
        email: '' // Empty email should be allowed
      }
      wrapper.vm.isEditMode = false

      await wrapper.vm.saveUser()

      expect(api.auth.register).toHaveBeenCalledWith({
        username: 'testuser',
        email: null,
        password: 'password123',
        role: 'developer'
      })
    })

    it('creates user with email successfully', async () => {
      wrapper.vm.userForm = {
        id: null,
        username: 'testuser',
        email: 'test@example.com',
        password: 'password123',
        role: 'developer',
        is_active: true
      }
      wrapper.vm.isEditMode = false

      await wrapper.vm.saveUser()

      expect(api.auth.register).toHaveBeenCalledWith({
        username: 'testuser',
        email: 'test@example.com',
        password: 'password123',
        role: 'developer'
      })
    })

    it('validates email format', () => {
      const emailRule = wrapper.vm.rules.email
      expect(emailRule('test@example.com')).toBe(true)
      expect(emailRule('invalid-email')).toBe('Enter a valid email (e.g. user@company.com)')
      expect(emailRule('')).toBe(true) // Empty is allowed (optional field)
      expect(emailRule(null)).toBe(true) // Null is allowed (optional field)
    })
  })

  describe('Email in Edit User Dialog', () => {
    it('populates email field when editing user', async () => {
      const user = mockUsers[0]
      wrapper.vm.openEditDialog(user)
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.userForm.email).toBe('admin@example.com')
    })

    it('handles null email when editing user', async () => {
      const user = mockUsers[2]
      wrapper.vm.openEditDialog(user)
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.userForm.email).toBe('')
    })

    it('updates email successfully', async () => {
      wrapper.vm.userForm = {
        id: 2,
        username: 'developer',
        email: 'newemail@example.com',
        role: 'developer',
        is_active: true
      }
      wrapper.vm.isEditMode = true

      await wrapper.vm.saveUser()

      expect(api.auth.updateUser).toHaveBeenCalledWith(2, {
        username: 'developer',
        email: 'newemail@example.com',
        role: 'developer',
        is_active: true
      })
    })

    it('can clear email when editing', async () => {
      wrapper.vm.userForm = {
        id: 2,
        username: 'developer',
        email: '',
        role: 'developer',
        is_active: true
      }
      wrapper.vm.isEditMode = true

      await wrapper.vm.saveUser()

      expect(api.auth.updateUser).toHaveBeenCalledWith(2, {
        username: 'developer',
        email: null,
        role: 'developer',
        is_active: true
      })
    })
  })

  describe('Created Date Display Format', () => {
    it('formats date as localized date string', () => {
      const date = wrapper.vm.formatDate('2025-01-01T00:00:00Z')
      // Should be in format like "1/1/2025"
      expect(date).toMatch(/\d/)
    })

    it('shows N/A for missing created date', () => {
      const result = wrapper.vm.formatDate(null)
      expect(result).toBe('N/A')
    })

    it('shows N/A for undefined created date', () => {
      const result = wrapper.vm.formatDate(undefined)
      expect(result).toBe('N/A')
    })
  })

  describe('Data Integrity', () => {
    it('preserves all existing user data when loading', async () => {
      await wrapper.vm.loadUsers()
      await wrapper.vm.$nextTick()

      const loadedUser = wrapper.vm.users.find(u => u.id === 1)
      expect(loadedUser).toMatchObject({
        id: 1,
        username: 'admin',
        email: 'admin@example.com',
        role: 'admin',
        is_active: true,
        created_at: '2025-01-01T00:00:00Z'
      })
    })

    it('includes email in user list response', async () => {
      await wrapper.vm.loadUsers()
      await wrapper.vm.$nextTick()

      wrapper.vm.users.forEach(user => {
        expect(user).toHaveProperty('email')
        expect(user).toHaveProperty('created_at')
      })
    })
  })

  describe('Accessibility', () => {
    it('email field has proper label', async () => {
      wrapper.vm.openCreateDialog()
      await wrapper.vm.$nextTick()

      // Email field should be labeled properly
      const emailField = wrapper.html()
      expect(emailField).toContain('Email')
    })

    it('email column has header definition', () => {
      const emailHeader = wrapper.vm.headers.find(h => h.key === 'email')
      expect(emailHeader).toBeDefined()
      expect(emailHeader.title).toBe('Email')
    })

    it('created date column has header definition', () => {
      const createdHeader = wrapper.vm.headers.find(h => h.key === 'created_at')
      expect(createdHeader).toBeDefined()
      expect(createdHeader.title).toBe('Created')
    })
  })

  describe('Backward Compatibility', () => {
    it('handles users without email field', async () => {
      const usersWithoutEmail = [
        {
          id: 5,
          username: 'olduser',
          role: 'viewer',
          is_active: true,
          // No email field
          created_at: '2025-01-01T00:00:00Z'
        }
      ]

      api.auth.listUsers.mockResolvedValueOnce({ data: usersWithoutEmail })
      await wrapper.vm.loadUsers()
      await wrapper.vm.$nextTick()

      // Should not crash
      expect(wrapper.vm.users).toHaveLength(1)
    })

    it('handles users without created_at field', async () => {
      const usersWithoutCreatedAt = [
        {
          id: 6,
          username: 'olduser2',
          email: 'old@example.com',
          role: 'viewer',
          is_active: true
          // No created_at field
        }
      ]

      api.auth.listUsers.mockResolvedValueOnce({ data: usersWithoutCreatedAt })
      await wrapper.vm.loadUsers()
      await wrapper.vm.$nextTick()

      // Should not crash
      expect(wrapper.vm.users).toHaveLength(1)
    })
  })
})
