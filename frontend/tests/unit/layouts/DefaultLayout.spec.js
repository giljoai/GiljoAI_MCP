/**
 * Test suite for DefaultLayout component
 * TDD approach: Tests written BEFORE implementation
 *
 * DefaultLayout is the full application layout for app routes (dashboard, settings, etc.)
 * - Includes AppBar and NavigationDrawer
 * - Loads user data on mount
 * - Reloads user after navigation from login
 * - Passes currentUser to child components
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import api from '@/services/api'

// Mock the API module
vi.mock('@/services/api', () => ({
  default: {
    auth: {
      me: vi.fn()
    }
  }
}))

describe('DefaultLayout.vue', () => {
  let vuetify
  let wrapper
  let router
  let pinia

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)

    vuetify = createVuetify({
      components,
      directives,
    })

    // Create router with test routes
    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        {
          path: '/',
          name: 'dashboard',
          component: { template: '<div>Dashboard</div>' },
          meta: { layout: 'default', requiresAuth: true }
        },
        {
          path: '/login',
          name: 'login',
          component: { template: '<div>Login</div>' },
          meta: { layout: 'auth', requiresAuth: false }
        }
      ]
    })
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
    vi.clearAllMocks()
  })

  describe('Component Rendering', () => {
    it('should render without errors', async () => {
      api.auth.me.mockResolvedValue({
        data: { username: 'admin', role: 'admin' }
      })

      wrapper = mount(DefaultLayout, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      await flushPromises()
      expect(wrapper.exists()).toBe(true)
    })

    it('should render v-app wrapper', async () => {
      api.auth.me.mockResolvedValue({
        data: { username: 'admin', role: 'admin' }
      })

      wrapper = mount(DefaultLayout, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      await flushPromises()
      const vApp = wrapper.findComponent({ name: 'VApp' })
      expect(vApp.exists()).toBe(true)
    })

    it('should render AppBar component', async () => {
      api.auth.me.mockResolvedValue({
        data: { username: 'admin', role: 'admin' }
      })

      wrapper = mount(DefaultLayout, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            AppBar: true,
            NavigationDrawer: true
          }
        }
      })

      await flushPromises()
      const appBar = wrapper.findComponent({ name: 'AppBar' })
      expect(appBar.exists()).toBe(true)
    })

    it('should render NavigationDrawer component', async () => {
      api.auth.me.mockResolvedValue({
        data: { username: 'admin', role: 'admin' }
      })

      wrapper = mount(DefaultLayout, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            AppBar: true,
            NavigationDrawer: true
          }
        }
      })

      await flushPromises()
      const navDrawer = wrapper.findComponent({ name: 'NavigationDrawer' })
      expect(navDrawer.exists()).toBe(true)
    })

    it('should render router-view', async () => {
      api.auth.me.mockResolvedValue({
        data: { username: 'admin', role: 'admin' }
      })

      wrapper = mount(DefaultLayout, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            RouterView: true,
            AppBar: true,
            NavigationDrawer: true
          }
        }
      })

      await flushPromises()
      const routerView = wrapper.findComponent({ name: 'RouterView' })
      expect(routerView.exists()).toBe(true)
    })
  })

  describe('User Data Loading', () => {
    it('should load user data on mount', async () => {
      const mockUser = { username: 'admin', role: 'admin' }
      api.auth.me.mockResolvedValue({ data: mockUser })

      wrapper = mount(DefaultLayout, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            AppBar: true,
            NavigationDrawer: true
          }
        }
      })

      await flushPromises()
      expect(api.auth.me).toHaveBeenCalled()
      expect(wrapper.vm.currentUser).toEqual(mockUser)
    })

    it('should set currentUser ref after successful API call', async () => {
      const mockUser = { username: 'testuser', role: 'developer' }
      api.auth.me.mockResolvedValue({ data: mockUser })

      wrapper = mount(DefaultLayout, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            AppBar: true,
            NavigationDrawer: true
          }
        }
      })

      await flushPromises()
      expect(wrapper.vm.currentUser).toEqual(mockUser)
    })

    it('should update userStore with current user', async () => {
      const mockUser = { username: 'admin', role: 'admin' }
      api.auth.me.mockResolvedValue({ data: mockUser })

      wrapper = mount(DefaultLayout, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            AppBar: true,
            NavigationDrawer: true
          }
        }
      })

      await flushPromises()

      // Access userStore from pinia
      const { useUserStore } = await import('@/stores/user')
      const userStore = useUserStore()
      expect(userStore.currentUser).toEqual(mockUser)
    })

    it('should handle API errors gracefully', async () => {
      api.auth.me.mockRejectedValue(new Error('Unauthorized'))

      wrapper = mount(DefaultLayout, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            AppBar: true,
            NavigationDrawer: true
          }
        }
      })

      await flushPromises()
      expect(wrapper.vm.currentUser).toBeNull()
    })

    it('should redirect to login on auth failure', async () => {
      const pushSpy = vi.spyOn(router, 'push')
      api.auth.me.mockRejectedValue(new Error('Unauthorized'))

      wrapper = mount(DefaultLayout, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            AppBar: true,
            NavigationDrawer: true
          }
        }
      })

      await flushPromises()
      expect(pushSpy).toHaveBeenCalledWith('/login')
    })
  })

  describe('Props Passing', () => {
    it('should pass currentUser to AppBar component', async () => {
      const mockUser = { username: 'admin', role: 'admin' }
      api.auth.me.mockResolvedValue({ data: mockUser })

      wrapper = mount(DefaultLayout, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            AppBar: true,
            NavigationDrawer: true
          }
        }
      })

      await flushPromises()
      const appBar = wrapper.findComponent({ name: 'AppBar' })
      expect(appBar.props('currentUser')).toEqual(mockUser)
    })

    it('should pass currentUser to NavigationDrawer component', async () => {
      const mockUser = { username: 'admin', role: 'admin' }
      api.auth.me.mockResolvedValue({ data: mockUser })

      wrapper = mount(DefaultLayout, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            AppBar: true,
            NavigationDrawer: true
          }
        }
      })

      await flushPromises()
      const navDrawer = wrapper.findComponent({ name: 'NavigationDrawer' })
      expect(navDrawer.props('currentUser')).toEqual(mockUser)
    })
  })

  describe('Route Meta Handling', () => {
    it('should hide AppBar when route meta hideAppBar is true', async () => {
      api.auth.me.mockResolvedValue({
        data: { username: 'admin', role: 'admin' }
      })

      // Update router with route that has hideAppBar meta
      router.addRoute({
        path: '/fullscreen',
        name: 'fullscreen',
        component: { template: '<div>Fullscreen</div>' },
        meta: { layout: 'default', hideAppBar: true }
      })

      await router.push('/fullscreen')

      wrapper = mount(DefaultLayout, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            AppBar: true,
            NavigationDrawer: true
          }
        }
      })

      await flushPromises()
      const appBar = wrapper.findComponent({ name: 'AppBar' })
      expect(appBar.exists()).toBe(false)
    })

    it('should hide NavigationDrawer when route meta hideDrawer is true', async () => {
      api.auth.me.mockResolvedValue({
        data: { username: 'admin', role: 'admin' }
      })

      // Update router with route that has hideDrawer meta
      router.addRoute({
        path: '/minimal',
        name: 'minimal',
        component: { template: '<div>Minimal</div>' },
        meta: { layout: 'default', hideDrawer: true }
      })

      await router.push('/minimal')

      wrapper = mount(DefaultLayout, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            AppBar: true,
            NavigationDrawer: true
          }
        }
      })

      await flushPromises()
      const navDrawer = wrapper.findComponent({ name: 'NavigationDrawer' })
      expect(navDrawer.exists()).toBe(false)
    })
  })

  describe('Navigation from Login', () => {
    it('should reload user after navigation from login page', async () => {
      const mockUser = { username: 'admin', role: 'admin' }
      api.auth.me.mockResolvedValue({ data: mockUser })

      wrapper = mount(DefaultLayout, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            AppBar: true,
            NavigationDrawer: true
          }
        }
      })

      await flushPromises()

      // Clear the initial mount call
      api.auth.me.mockClear()

      // Simulate navigation from login to dashboard
      await router.push('/login')
      await router.push('/')
      await flushPromises()

      // Should have reloaded user data
      expect(api.auth.me).toHaveBeenCalled()
    })
  })

  describe('Drawer State Management', () => {
    it('should initialize drawer as open', async () => {
      api.auth.me.mockResolvedValue({
        data: { username: 'admin', role: 'admin' }
      })

      wrapper = mount(DefaultLayout, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            AppBar: true,
            NavigationDrawer: true
          }
        }
      })

      await flushPromises()
      expect(wrapper.vm.drawer).toBe(true)
    })

    it('should toggle drawer when AppBar emits toggle-drawer event', async () => {
      api.auth.me.mockResolvedValue({
        data: { username: 'admin', role: 'admin' }
      })

      wrapper = mount(DefaultLayout, {
        global: {
          plugins: [vuetify, router, pinia],
          stubs: {
            AppBar: true,
            NavigationDrawer: true
          }
        }
      })

      await flushPromises()

      const initialDrawerState = wrapper.vm.drawer
      const appBar = wrapper.findComponent({ name: 'AppBar' })
      await appBar.vm.$emit('toggle-drawer')
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.drawer).toBe(!initialDrawerState)
    })
  })
})
