import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { ref } from 'vue'

// Mock configService -- use vi.fn with implementation that defers to a mutable holder
const _mode = { value: 'ce' }
vi.mock('@/services/configService', () => ({
  default: {
    fetchConfig: vi.fn(() => Promise.resolve()),
    getGiljoMode: vi.fn(() => _mode.value),
    getEdition: vi.fn(() => 'community'),
    config: null,
  },
}))

// Mock setupService
vi.mock('@/services/setupService', () => ({
  default: {
    checkEnhancedStatus: vi.fn(() => Promise.resolve({ is_fresh_install: false, total_users_count: 1 })),
  },
}))

// Mock vue-router
vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
  useRoute: () => ({
    path: '/home',
    query: {},
  }),
}))

// Mock stores
vi.mock('@/stores/projects', () => ({
  useProjectStore: () => ({
    projects: [],
    activeProject: null,
  }),
}))

vi.mock('@/stores/products', () => ({
  useProductStore: () => ({
    activeProduct: null,
  }),
}))

vi.mock('@/stores/user', () => ({
  useUserStore: () => ({
    currentUser: { username: 'admin', role: 'admin', email: 'admin@test.com' },
    currentOrg: null,
    orgRole: null,
  }),
}))

vi.mock('@/stores/websocket', () => ({
  useWebSocketStore: () => ({
    connectionStatus: 'connected',
    reconnectAttempts: 0,
    maxReconnectAttempts: 5,
    disconnect: vi.fn(),
  }),
}))

// Mock axios
vi.mock('axios', () => {
  const post = vi.fn(() => Promise.resolve({ data: { message: 'ok' } }))
  return { default: { post } }
})

import NavigationDrawer from '@/components/navigation/NavigationDrawer.vue'
import configService from '@/services/configService'

describe('NavigationDrawer.vue -- SaaS modifications', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    _mode.value = 'ce'
    // Restore mock implementations after clearAllMocks resets them
    configService.fetchConfig.mockImplementation(() => Promise.resolve())
    configService.getGiljoMode.mockImplementation(() => _mode.value)
    configService.getEdition.mockReturnValue('community')
  })

  function mountDrawer() {
    return mount(NavigationDrawer, {
      props: {
        modelValue: true,
        rail: false,
        temporary: false,
        currentUser: { username: 'admin', role: 'admin', email: 'admin@test.com' },
      },
      global: {
        stubs: {
          'v-navigation-drawer': {
            template: '<div class="v-navigation-drawer"><slot /><slot name="append" /></div>',
          },
          'router-link': { template: '<a><slot /></a>' },
          NotificationDropdown: { template: '<div class="notification-stub" />' },
          ConnectionDebugDialog: { template: '<div class="conn-debug-stub" />' },
          UserProfileDialog: { template: '<div class="profile-dialog-stub" />' },
          RoleBadge: { template: '<span class="role-badge-stub" />' },
        },
      },
    })
  }

  describe('Admin Settings visibility', () => {
    it('shows Admin Settings in CE mode for admin users', async () => {
      _mode.value = 'ce'
      const wrapper = mountDrawer()
      await flushPromises()

      expect(wrapper.html()).toContain('Admin Settings')
    })

    it('hides Admin Settings in demo mode', async () => {
      _mode.value = 'demo'
      const wrapper = mountDrawer()
      await flushPromises()

      expect(wrapper.html()).not.toContain('Admin Settings')
    })

    it('hides Admin Settings in saas mode', async () => {
      _mode.value = 'saas'
      const wrapper = mountDrawer()
      await flushPromises()

      expect(wrapper.html()).not.toContain('Admin Settings')
    })
  })

  describe('Reset Password menu item', () => {
    it('does NOT show Reset Password in CE mode', async () => {
      _mode.value = 'ce'
      const wrapper = mountDrawer()
      await flushPromises()

      // Debug: check giljoMode after mount
      expect(wrapper.vm.giljoMode).toBe('ce')
      // The Reset Password v-list-item has v-if="giljoMode !== 'ce'"
      // In CE mode this should not be rendered
      const listItems = wrapper.findAll('.v-list-item')
      const resetItem = listItems.filter(li => li.text().includes('Reset Password'))
      expect(resetItem.length).toBe(0)
    })

    it('shows Reset Password in demo mode', async () => {
      _mode.value = 'demo'
      const wrapper = mountDrawer()
      await flushPromises()

      expect(wrapper.html()).toContain('Reset Password')
    })

    it('shows Reset Password in saas mode', async () => {
      _mode.value = 'saas'
      const wrapper = mountDrawer()
      await flushPromises()

      expect(wrapper.html()).toContain('Reset Password')
    })
  })

  describe('Edition footer', () => {
    it('shows "Community Edition" in CE mode when expanded', async () => {
      _mode.value = 'ce'
      const wrapper = mountDrawer()
      await flushPromises()

      const html = wrapper.html()
      expect(html).toContain('Community Edition')
    })

    it('shows "Demo Edition" in demo mode', async () => {
      _mode.value = 'demo'
      const wrapper = mountDrawer()
      await flushPromises()

      const html = wrapper.html()
      expect(html).toContain('Demo Edition')
    })

    it('shows "SaaS Edition" in saas mode', async () => {
      _mode.value = 'saas'
      const wrapper = mountDrawer()
      await flushPromises()

      const html = wrapper.html()
      expect(html).toContain('SaaS Edition')
    })
  })
})
