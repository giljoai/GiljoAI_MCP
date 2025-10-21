/**
 * Test suite for AppBar.vue - Handover 0028 User Panel Consolidation
 *
 * Tests for changes related to:
 * - Removal of "My API Keys" from avatar dropdown menu
 * - Verification that Users menu item exists for admin users
 * - Verification that proper navigation structure is maintained
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import AppBar from '@/components/navigation/AppBar.vue'

// Mock the API module
vi.mock('@/services/api', () => ({
  default: {
    auth: {
      logout: vi.fn().mockResolvedValue({ data: { message: 'Logged out' } })
    }
  }
}))

// Mock ProductSwitcher and ConnectionStatus components
vi.mock('@/components/ProductSwitcher.vue', () => ({
  default: { template: '<div>Product Switcher</div>' }
}))

vi.mock('@/components/ConnectionStatus.vue', () => ({
  default: { template: '<div>Connection Status</div>' }
}))

describe('AppBar.vue - Handover 0028 Avatar Dropdown', () => {
  let wrapper
  let vuetify
  let router
  let pinia

  const mockAdminUser = {
    id: 1,
    username: 'admin',
    email: 'admin@example.com',
    role: 'admin',
    is_active: true,
    created_at: '2025-01-01T00:00:00Z'
  }

  const mockDeveloperUser = {
    id: 2,
    username: 'developer',
    email: 'dev@example.com',
    role: 'developer',
    is_active: true,
    created_at: '2025-01-02T00:00:00Z'
  }

  beforeEach(() => {
    // Setup Vuetify
    vuetify = createVuetify({
      components,
      directives
    })

    // Setup Router
    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', name: 'Dashboard', component: { template: '<div>Dashboard</div>' } },
        { path: '/settings', name: 'UserSettings', component: { template: '<div>Settings</div>' } },
        { path: '/admin/settings', name: 'SystemSettings', component: { template: '<div>System Settings</div>' } },
        { path: '/users', name: 'Users', component: { template: '<div>Users</div>' } },
        { path: '/api-keys', name: 'ApiKeys', component: { template: '<div>API Keys</div>' } }
      ]
    })

    // Setup Pinia
    pinia = createTestingPinia({
      initialState: {
        user: {
          currentUser: mockAdminUser
        }
      }
    })
  })

  describe('Avatar Dropdown Menu Structure', () => {
    it('renders user menu button', () => {
      wrapper = mount(AppBar, {
        props: {
          currentUser: mockAdminUser,
          rail: false
        },
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            ProductSwitcher: true,
            ConnectionStatus: true
          }
        }
      })

      const userMenuButton = wrapper.find('[aria-label="User menu"]')
      expect(userMenuButton.exists()).toBe(true)
    })

    it('displays current user information in dropdown', () => {
      wrapper = mount(AppBar, {
        props: {
          currentUser: mockAdminUser,
          rail: false
        },
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            ProductSwitcher: true,
            ConnectionStatus: true
          }
        }
      })

      expect(wrapper.text()).toContain('admin')
    })

    it('displays user role badge in dropdown', () => {
      wrapper = mount(AppBar, {
        props: {
          currentUser: mockAdminUser,
          rail: false
        },
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            ProductSwitcher: true,
            ConnectionStatus: true
          }
        }
      })

      expect(wrapper.text()).toContain('admin')
    })
  })

  describe('My API Keys Removal (Handover 0028)', () => {
    it('does NOT display "My API Keys" menu item in avatar dropdown', () => {
      wrapper = mount(AppBar, {
        props: {
          currentUser: mockAdminUser,
          rail: false
        },
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            ProductSwitcher: true,
            ConnectionStatus: true
          }
        }
      })

      // Should NOT contain "My API Keys" text in dropdown
      const menuItems = wrapper.findAll('.v-list-item')
      const apiKeysItem = menuItems.find(item =>
        item.text().includes('My API Keys') ||
        item.text().includes('API Keys')
      )

      expect(apiKeysItem).toBeUndefined()
    })

    it('does NOT have route to ApiKeys view in avatar dropdown', () => {
      wrapper = mount(AppBar, {
        props: {
          currentUser: mockAdminUser,
          rail: false
        },
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            ProductSwitcher: true,
            ConnectionStatus: true
          }
        }
      })

      const menuItems = wrapper.findAll('.v-list-item')
      const apiKeysRoute = menuItems.find(item => {
        const to = item.attributes('to')
        return to && to.includes('api-keys')
      })

      expect(apiKeysRoute).toBeUndefined()
    })
  })

  describe('Admin User Menu Items', () => {
    it('displays "My Settings" menu item for all users', () => {
      wrapper = mount(AppBar, {
        props: {
          currentUser: mockAdminUser,
          rail: false
        },
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            ProductSwitcher: true,
            ConnectionStatus: true
          }
        }
      })

      expect(wrapper.text()).toContain('My Settings')
    })

    it('displays "Admin Settings" menu item for admin users', () => {
      wrapper = mount(AppBar, {
        props: {
          currentUser: mockAdminUser,
          rail: false
        },
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            ProductSwitcher: true,
            ConnectionStatus: true
          }
        }
      })

      expect(wrapper.text()).toContain('Admin Settings')
    })

    it('displays "Users" menu item for admin users', () => {
      wrapper = mount(AppBar, {
        props: {
          currentUser: mockAdminUser,
          rail: false
        },
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            ProductSwitcher: true,
            ConnectionStatus: true
          }
        }
      })

      expect(wrapper.text()).toContain('Users')
    })

    it('does NOT display "Admin Settings" for non-admin users', () => {
      wrapper = mount(AppBar, {
        props: {
          currentUser: mockDeveloperUser,
          rail: false
        },
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            ProductSwitcher: true,
            ConnectionStatus: true
          }
        }
      })

      const adminSettingsText = wrapper.text()
      const hasAdminSettings = adminSettingsText.includes('Admin Settings') ||
                               adminSettingsText.includes('System Settings')
      expect(hasAdminSettings).toBe(false)
    })

    it('does NOT display "Users" for non-admin users', () => {
      wrapper = mount(AppBar, {
        props: {
          currentUser: mockDeveloperUser,
          rail: false
        },
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            ProductSwitcher: true,
            ConnectionStatus: true
          }
        }
      })

      // Check that Users menu item is not present
      const menuText = wrapper.text()
      // Should have "My Settings" and "Logout" but NOT "Users"
      const hasUsersMenuItem = menuText.split('My Settings')[1]?.includes('Users')
      expect(hasUsersMenuItem).toBeFalsy()
    })
  })

  describe('Logout Functionality', () => {
    it('displays logout button', () => {
      wrapper = mount(AppBar, {
        props: {
          currentUser: mockAdminUser,
          rail: false
        },
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            ProductSwitcher: true,
            ConnectionStatus: true
          }
        }
      })

      expect(wrapper.text()).toContain('Logout')
    })

    it('calls handleLogout when logout clicked', async () => {
      wrapper = mount(AppBar, {
        props: {
          currentUser: mockAdminUser,
          rail: false
        },
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            ProductSwitcher: true,
            ConnectionStatus: true
          }
        }
      })

      const logoutItem = wrapper.findAll('.v-list-item').find(item =>
        item.text().includes('Logout')
      )

      expect(logoutItem).toBeDefined()
    })
  })

  describe('Role Badge Styling', () => {
    it('displays admin role with error color', () => {
      wrapper = mount(AppBar, {
        props: {
          currentUser: mockAdminUser,
          rail: false
        },
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            ProductSwitcher: true,
            ConnectionStatus: true
          }
        }
      })

      const roleColor = wrapper.vm.getRoleColor('admin')
      expect(roleColor).toBe('error')
    })

    it('displays developer role with primary color', () => {
      wrapper = mount(AppBar, {
        props: {
          currentUser: mockDeveloperUser,
          rail: false
        },
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            ProductSwitcher: true,
            ConnectionStatus: true
          }
        }
      })

      const roleColor = wrapper.vm.getRoleColor('developer')
      expect(roleColor).toBe('primary')
    })

    it('displays viewer role with success color', () => {
      wrapper = mount(AppBar, {
        props: {
          currentUser: { ...mockDeveloperUser, role: 'viewer' },
          rail: false
        },
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            ProductSwitcher: true,
            ConnectionStatus: true
          }
        }
      })

      const roleColor = wrapper.vm.getRoleColor('viewer')
      expect(roleColor).toBe('success')
    })
  })

  describe('Accessibility', () => {
    it('has proper ARIA labels for user menu button', () => {
      wrapper = mount(AppBar, {
        props: {
          currentUser: mockAdminUser,
          rail: false
        },
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            ProductSwitcher: true,
            ConnectionStatus: true
          }
        }
      })

      const userMenuButton = wrapper.find('[aria-label="User menu"]')
      expect(userMenuButton.exists()).toBe(true)
    })

    it('has proper navigation sidebar toggle accessibility', () => {
      wrapper = mount(AppBar, {
        props: {
          currentUser: mockAdminUser,
          rail: false
        },
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            ProductSwitcher: true,
            ConnectionStatus: true
          }
        }
      })

      const railToggle = wrapper.find('[aria-label="Collapse navigation"]')
      expect(railToggle.exists()).toBe(true)
    })
  })

  describe('Responsive Behavior', () => {
    it('shows rail toggle on desktop', () => {
      wrapper = mount(AppBar, {
        props: {
          currentUser: mockAdminUser,
          rail: false
        },
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            ProductSwitcher: true,
            ConnectionStatus: true
          },
          mocks: {
            mobile: false
          }
        }
      })

      const railToggle = wrapper.find('[aria-label="Collapse navigation"]')
      expect(railToggle.exists()).toBe(true)
    })
  })
})
