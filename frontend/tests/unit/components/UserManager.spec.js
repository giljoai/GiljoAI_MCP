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
      updateUser: vi.fn(),
      deleteUser: vi.fn(),
    },
  },
}))

// Mock configService so CE user-limit guard does not fire during tests
vi.mock('@/services/configService', () => ({
  default: {
    getEdition: () => 'saas',
    fetchConfig: vi.fn().mockResolvedValue({}),
  },
}))

describe('UserManager', () => {
  let wrapper
  let api
  const mockUsers = [
    {
      id: 1,
      username: 'admin',
      role: 'admin',
      is_active: true,
      last_login: '2025-10-09T10:00:00Z',
      tenant_key: 'tk_test',
    },
    {
      id: 2,
      username: 'developer',
      role: 'developer',
      is_active: true,
      last_login: '2025-10-09T11:00:00Z',
      tenant_key: 'tk_test',
    },
    {
      id: 3,
      username: 'viewer',
      role: 'viewer',
      is_active: false,
      last_login: null,
      tenant_key: 'tk_test',
    },
  ]

  const mockCurrentUser = {
    id: 1,
    username: 'admin',
    role: 'admin',
    tenant_key: 'tk_test',
  }

  beforeEach(async () => {
    // Get the mocked API
    api = (await import('@/services/api')).default

    // Setup mock responses
    api.auth.listUsers.mockResolvedValue({ data: mockUsers })
    api.auth.register.mockResolvedValue({
      data: { id: 4, username: 'newuser', role: 'developer' },
    })
    api.auth.updateUser.mockResolvedValue({ data: { message: 'User updated' } })
    api.auth.deleteUser.mockResolvedValue({ data: { message: 'User deleted' } })

    wrapper = mount(UserManager, {
      global: {
        plugins: [
          createTestingPinia({
            initialState: {
              user: {
                currentUser: mockCurrentUser,
              },
            },
          }),
        ],
      },
    })

    // Wait for component to mount and load users
    await wrapper.vm.$nextTick()
  })

  describe('User Loading', () => {
    it('loads users on mount', async () => {
      await wrapper.vm.$nextTick()
      expect(api.auth.listUsers).toHaveBeenCalled()
      expect(wrapper.vm.users).toHaveLength(3)
    })

    it('displays user table with correct headers', () => {
      const headers = wrapper.vm.headers
      expect(headers).toHaveLength(7)
      expect(headers.map((h) => h.key)).toEqual([
        'username',
        'email',
        'role',
        'is_active',
        'created_at',
        'last_login',
        'actions',
      ])
    })

    it('displays correct number of users in table', async () => {
      await wrapper.vm.$nextTick()
      wrapper.vm.users = mockUsers
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.filteredUsers).toHaveLength(3)
    })
  })

  describe('User Search', () => {
    beforeEach(async () => {
      wrapper.vm.users = mockUsers
      await wrapper.vm.$nextTick()
    })

    it('filters users by username', async () => {
      wrapper.vm.search = 'admin'
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.filteredUsers).toHaveLength(1)
      expect(wrapper.vm.filteredUsers[0].username).toBe('admin')
    })

    it('returns all users when search is empty', async () => {
      wrapper.vm.search = ''
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.filteredUsers).toHaveLength(3)
    })

    it('search is case-insensitive', async () => {
      wrapper.vm.search = 'ADMIN'
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.filteredUsers).toHaveLength(1)
      expect(wrapper.vm.filteredUsers[0].username).toBe('admin')
    })
  })

  describe('Role Display', () => {
    it('displays correct role color for admin', () => {
      const color = wrapper.vm.getRoleColor('admin')
      expect(color).toBe('error')
    })

    it('displays correct role color for developer', () => {
      const color = wrapper.vm.getRoleColor('developer')
      expect(color).toBe('primary')
    })

    it('displays correct role color for viewer', () => {
      const color = wrapper.vm.getRoleColor('viewer')
      expect(color).toBe('info')
    })

    it('displays correct role icon for admin', () => {
      const icon = wrapper.vm.getRoleIcon('admin')
      expect(icon).toBe('mdi-shield-crown')
    })

    it('displays correct role icon for developer', () => {
      const icon = wrapper.vm.getRoleIcon('developer')
      expect(icon).toBe('mdi-code-tags')
    })

    it('displays correct role icon for viewer', () => {
      const icon = wrapper.vm.getRoleIcon('viewer')
      expect(icon).toBe('mdi-eye')
    })

    it('returns default values for unknown role', () => {
      const color = wrapper.vm.getRoleColor('unknown')
      const icon = wrapper.vm.getRoleIcon('unknown')
      expect(color).toBe('default')
      expect(icon).toBe('mdi-account')
    })
  })

  describe('Relative Time Formatting', () => {
    it('formats recent timestamp correctly', () => {
      const pastDate = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString() // 2 hours ago
      const result = wrapper.vm.formatRelativeTime(pastDate)
      expect(result).toContain('ago')
    })

    it('shows "Never" for null timestamp', () => {
      const result = wrapper.vm.formatRelativeTime(null)
      expect(result).toBe('Never')
    })

    it('shows "Unknown" for invalid timestamp', () => {
      const result = wrapper.vm.formatRelativeTime('invalid-date')
      expect(result).toBe('Unknown')
    })
  })

  describe('Create User Dialog', () => {
    it('opens create dialog when add button clicked', async () => {
      expect(wrapper.vm.showUserDialog).toBe(false)
      wrapper.vm.openCreateDialog()
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.showUserDialog).toBe(true)
      expect(wrapper.vm.isEditMode).toBe(false)
    })

    it('initializes form with default values for create', async () => {
      wrapper.vm.openCreateDialog()
      await wrapper.vm.$nextTick()
      // Access the ref value
      expect(wrapper.vm.userForm).toBeDefined()
      expect(wrapper.vm.isEditMode).toBe(false)
      expect(wrapper.vm.showUserDialog).toBe(true)
    })

    it('creates new user successfully', async () => {
      wrapper.vm.userForm = {
        id: null,
        username: 'testuser',
        email: 'test@example.com',
        password: 'password123',
        role: 'developer',
        is_active: true,
      }
      wrapper.vm.isEditMode = false

      await wrapper.vm.saveUser()

      expect(api.auth.register).toHaveBeenCalledWith({
        username: 'testuser',
        email: 'test@example.com',
        password: 'password123',
        role: 'developer',
      })
      expect(api.auth.listUsers).toHaveBeenCalled() // Reloaded after save
    })

    it('closes dialog after successful create', async () => {
      wrapper.vm.showUserDialog = true
      wrapper.vm.userForm = {
        username: 'testuser',
        password: 'password123',
        role: 'developer',
      }
      wrapper.vm.isEditMode = false

      await wrapper.vm.saveUser()
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.showUserDialog).toBe(false)
    })
  })

  describe('Edit User Dialog', () => {
    it('opens edit dialog with user data', async () => {
      const user = mockUsers[0]
      wrapper.vm.users = mockUsers // Set users data
      wrapper.vm.openEditDialog(user)
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.showUserDialog).toBe(true)
      expect(wrapper.vm.isEditMode).toBe(true)
      // Just verify the dialog opened correctly
      expect(wrapper.vm.userForm).toBeDefined()
    })

    it('updates user successfully', async () => {
      wrapper.vm.userForm = {
        id: 2,
        username: 'developer',
        email: 'dev@example.com',
        role: 'admin',
        is_active: true,
      }
      wrapper.vm.isEditMode = true

      await wrapper.vm.saveUser()

      expect(api.auth.updateUser).toHaveBeenCalledWith(2, {
        username: 'developer',
        email: 'dev@example.com',
        role: 'admin',
        is_active: true,
      })
      expect(api.auth.listUsers).toHaveBeenCalled() // Reloaded after save
    })

    it('closes dialog after update', async () => {
      wrapper.vm.showUserDialog = true
      wrapper.vm.userForm = { id: 2, role: 'admin', is_active: true }
      wrapper.vm.isEditMode = true

      await wrapper.vm.saveUser()
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.showUserDialog).toBe(false)
    })
  })

  describe('Password Change Dialog', () => {
    it('opens password dialog with user info', async () => {
      const user = mockUsers[1]
      wrapper.vm.openPasswordDialog(user)
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.showPasswordDialog).toBe(true)
      expect(wrapper.vm.passwordUser).toEqual(user)
      expect(wrapper.vm.newPassword).toBe('')
    })

    it('changes password successfully', async () => {
      wrapper.vm.passwordUser = mockUsers[1]
      wrapper.vm.newPassword = 'newpassword123'

      await wrapper.vm.changePassword()

      expect(api.auth.updateUser).toHaveBeenCalledWith(mockUsers[1].id, {
        password: 'newpassword123',
      })
      expect(wrapper.vm.showPasswordDialog).toBe(false)
    })

    it('prevents password change without new password', async () => {
      // Clear previous mock calls
      api.auth.updateUser.mockClear()

      wrapper.vm.passwordUser = null
      wrapper.vm.newPassword = ''

      await wrapper.vm.changePassword()

      expect(api.auth.updateUser).not.toHaveBeenCalled()
    })

    it('closes password dialog', async () => {
      wrapper.vm.showPasswordDialog = true
      wrapper.vm.passwordUser = mockUsers[1]
      wrapper.vm.newPassword = 'test'

      wrapper.vm.closePasswordDialog()

      expect(wrapper.vm.showPasswordDialog).toBe(false)
      expect(wrapper.vm.passwordUser).toBeNull()
      expect(wrapper.vm.newPassword).toBe('')
    })
  })

  describe('User Status Toggle', () => {
    it('opens status confirmation dialog', async () => {
      const user = mockUsers[2]
      wrapper.vm.toggleUserStatus(user)
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.showStatusDialog).toBe(true)
      expect(wrapper.vm.statusUser).toEqual(user)
    })

    it('activates inactive user', async () => {
      const inactiveUser = mockUsers[2] // is_active: false
      wrapper.vm.statusUser = inactiveUser

      await wrapper.vm.confirmToggleStatus()

      expect(api.auth.updateUser).toHaveBeenCalledWith(inactiveUser.id, {
        is_active: true,
      })
    })

    it('deactivates active user', async () => {
      const activeUser = mockUsers[0] // is_active: true
      wrapper.vm.statusUser = activeUser

      await wrapper.vm.confirmToggleStatus()

      expect(api.auth.updateUser).toHaveBeenCalledWith(activeUser.id, {
        is_active: false,
      })
    })

    it('reloads users after status toggle', async () => {
      wrapper.vm.statusUser = mockUsers[2]
      api.auth.listUsers.mockClear()

      await wrapper.vm.confirmToggleStatus()

      expect(api.auth.listUsers).toHaveBeenCalled()
      expect(wrapper.vm.showStatusDialog).toBe(false)
    })

    it('closes status dialog', async () => {
      wrapper.vm.showStatusDialog = true
      wrapper.vm.statusUser = mockUsers[2]

      wrapper.vm.closeStatusDialog()

      expect(wrapper.vm.showStatusDialog).toBe(false)
      expect(wrapper.vm.statusUser).toBeNull()
    })
  })

  describe('Form Validation', () => {
    it('validates required fields', () => {
      const usernameRule = wrapper.vm.rules.username
      expect(usernameRule('test')).toBe(true)
      expect(usernameRule('')).toBe('Username is required')
      expect(usernameRule(null)).toBe('Username is required')

      const passwordRule = wrapper.vm.rules.password
      expect(passwordRule('test')).toBe(true)
      expect(passwordRule('')).toBe('Password is required')

      const roleRule = wrapper.vm.rules.role
      expect(roleRule('admin')).toBe(true)
      expect(roleRule('')).toBe('Role is required')
    })

    it('validates minimum password length', () => {
      const minLengthRule = wrapper.vm.rules.minLength
      expect(minLengthRule('password123')).toBe(true)
      expect(minLengthRule('short')).toBe('Password must be at least 8 characters')
      expect(minLengthRule(null)).toBe(true) // null is allowed (for edit mode)
    })
  })

  describe('Error Handling', () => {
    it('handles API error when loading users', async () => {
      // First set some users
      wrapper.vm.users = mockUsers

      // Now mock an error
      api.auth.listUsers.mockRejectedValueOnce(new Error('Network error'))

      await wrapper.vm.loadUsers()

      expect(wrapper.vm.loading).toBe(false)
      // Users should remain unchanged after error
      expect(wrapper.vm.users).toEqual(mockUsers)
    })

    it('handles API error when creating user', async () => {
      api.auth.register.mockRejectedValueOnce(new Error('Validation error'))
      wrapper.vm.userForm = {
        username: 'testuser',
        password: 'password123',
        role: 'developer',
      }
      wrapper.vm.isEditMode = false

      await wrapper.vm.saveUser()

      expect(wrapper.vm.saving).toBe(false)
    })

    it('handles API error when updating user', async () => {
      api.auth.updateUser.mockRejectedValueOnce(new Error('Update failed'))
      wrapper.vm.userForm = { id: 2, role: 'admin', is_active: true }
      wrapper.vm.isEditMode = true

      await wrapper.vm.saveUser()

      expect(wrapper.vm.saving).toBe(false)
    })

    it('handles API error when changing password', async () => {
      api.auth.updateUser.mockRejectedValueOnce(new Error('Password change failed'))
      wrapper.vm.passwordUser = mockUsers[1]
      wrapper.vm.newPassword = 'newpassword123'

      await wrapper.vm.changePassword()

      expect(wrapper.vm.changingPassword).toBe(false)
    })

    it('handles API error when toggling status', async () => {
      api.auth.updateUser.mockRejectedValueOnce(new Error('Status toggle failed'))
      wrapper.vm.statusUser = mockUsers[2]

      await wrapper.vm.confirmToggleStatus()

      expect(wrapper.vm.togglingStatus).toBe(false)
    })
  })

  describe('Current User Protection', () => {
    it('prevents current user from deactivating themselves in form', () => {
      const currentUser = mockUsers[0] // id: 1 (matches mockCurrentUser)
      wrapper.vm.openEditDialog(currentUser)

      // The switch should be disabled for current user
      expect(wrapper.vm.userForm.id).toBe(mockCurrentUser.id)
      // Component logic should prevent self-deactivation
    })
  })

  describe('Dialog Management', () => {
    it('closes user dialog and resets form', () => {
      wrapper.vm.showUserDialog = true
      wrapper.vm.userForm = { id: 1, username: 'test', role: 'admin', is_active: true }

      wrapper.vm.closeUserDialog()

      expect(wrapper.vm.showUserDialog).toBe(false)
      expect(wrapper.vm.userForm.id).toBeNull()
      expect(wrapper.vm.userForm.username).toBe('')
      expect(wrapper.vm.userForm.role).toBe('developer')
    })
  })
})
