/**
 * Unit tests for App.vue - Navigation menu role-based visibility
 * Tests that menu items are shown/hidden based on user role
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
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

// Mock API service
vi.mock('@/services/api', () => ({
  default: {
    auth: {
      me: vi.fn(),
      logout: vi.fn(),
    },
  },
}))

describe('App.vue - Navigation Menu Visibility', () => {
  let wrapper
  let userStore
  let router
  let vuetify

  beforeEach(() => {
    // Create fresh pinia instance
    setActivePinia(createPinia())
    userStore = useUserStore()

    // Create router
    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', name: 'Dashboard', component: { template: '<div>Dashboard</div>' } },
        { path: '/users', name: 'Users', component: { template: '<div>Users</div>' } },
        { path: '/settings', name: 'Settings', component: { template: '<div>Settings</div>' } },
      ],
    })

    // Create vuetify instance
    vuetify = createVuetify({
      components,
      directives,
    })
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
  })

  describe('Admin User - Full Menu Access', () => {
    beforeEach(async () => {
      userStore.currentUser = { username: 'admin', role: 'admin' }

      wrapper = mount(App, {
        global: {
          plugins: [router, vuetify],
        },
      })
    })

    it('should display Users menu item for admin', () => {
      const navItems = wrapper.findAll('[role="listitem"]')
      const navItemsText = navItems.map(item => item.text())

      expect(navItemsText).toContain('Users')
    })

    it('should display all standard menu items for admin', () => {
      const navItems = wrapper.findAll('[role="listitem"]')
      const navItemsText = navItems.map(item => item.text())

      expect(navItemsText).toContain('Dashboard')
      expect(navItemsText).toContain('Projects')
      expect(navItemsText).toContain('Agents')
      expect(navItemsText).toContain('Messages')
      expect(navItemsText).toContain('Tasks')
      expect(navItemsText).toContain('Settings')
    })
  })

  describe('Regular User - Limited Menu Access', () => {
    beforeEach(async () => {
      userStore.currentUser = { username: 'testuser', role: 'user' }

      wrapper = mount(App, {
        global: {
          plugins: [router, vuetify],
        },
      })
    })

    it('should NOT display Users menu item for regular user', () => {
      const navItems = wrapper.findAll('[role="listitem"]')
      const navItemsText = navItems.map(item => item.text())

      expect(navItemsText).not.toContain('Users')
    })

    it('should display all standard menu items except Users', () => {
      const navItems = wrapper.findAll('[role="listitem"]')
      const navItemsText = navItems.map(item => item.text())

      expect(navItemsText).toContain('Dashboard')
      expect(navItemsText).toContain('Projects')
      expect(navItemsText).toContain('Agents')
      expect(navItemsText).toContain('Messages')
      expect(navItemsText).toContain('Tasks')
      expect(navItemsText).toContain('Settings')
    })
  })

  describe('Unauthenticated User', () => {
    beforeEach(async () => {
      userStore.currentUser = null

      wrapper = mount(App, {
        global: {
          plugins: [router, vuetify],
        },
      })
    })

    it('should NOT display Users menu item when not authenticated', () => {
      const navItems = wrapper.findAll('[role="listitem"]')
      const navItemsText = navItems.map(item => item.text())

      expect(navItemsText).not.toContain('Users')
    })
  })

  describe('Menu Structure', () => {
    it('should have correct icon for Users menu item when visible', async () => {
      userStore.currentUser = { username: 'admin', role: 'admin' }

      wrapper = mount(App, {
        global: {
          plugins: [router, vuetify],
        },
      })

      // Find the Users menu item
      const usersItem = wrapper.findAll('[role="listitem"]').find(item =>
        item.text().includes('Users')
      )

      expect(usersItem).toBeDefined()
      // Vuetify uses mdi-account-multiple for users
      expect(usersItem.html()).toContain('mdi-account-multiple')
    })

    it('should have correct route for Users menu item', async () => {
      userStore.currentUser = { username: 'admin', role: 'admin' }

      wrapper = mount(App, {
        global: {
          plugins: [router, vuetify],
        },
      })

      const usersItem = wrapper.findAll('[role="listitem"]').find(item =>
        item.text().includes('Users')
      )

      expect(usersItem).toBeDefined()
      // Check that it has the correct route
      expect(usersItem.attributes('to')).toBe('/users')
    })
  })

  describe('Dynamic Role Changes', () => {
    it('should update menu when user role changes from user to admin', async () => {
      userStore.currentUser = { username: 'testuser', role: 'user' }

      wrapper = mount(App, {
        global: {
          plugins: [router, vuetify],
        },
      })

      // Initially no Users menu
      let navItems = wrapper.findAll('[role="listitem"]')
      let navItemsText = navItems.map(item => item.text())
      expect(navItemsText).not.toContain('Users')

      // Change to admin
      userStore.currentUser = { username: 'admin', role: 'admin' }
      await wrapper.vm.$nextTick()

      // Now Users menu should appear
      navItems = wrapper.findAll('[role="listitem"]')
      navItemsText = navItems.map(item => item.text())
      expect(navItemsText).toContain('Users')
    })

    it('should hide Users menu when user logs out', async () => {
      userStore.currentUser = { username: 'admin', role: 'admin' }

      wrapper = mount(App, {
        global: {
          plugins: [router, vuetify],
        },
      })

      // Initially has Users menu
      let navItems = wrapper.findAll('[role="listitem"]')
      let navItemsText = navItems.map(item => item.text())
      expect(navItemsText).toContain('Users')

      // Logout
      userStore.currentUser = null
      await wrapper.vm.$nextTick()

      // Users menu should be hidden
      navItems = wrapper.findAll('[role="listitem"]')
      navItemsText = navItems.map(item => item.text())
      expect(navItemsText).not.toContain('Users')
    })
  })
})
