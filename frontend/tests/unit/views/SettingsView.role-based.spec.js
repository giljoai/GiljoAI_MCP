/**
 * Unit tests for SettingsView.vue - Role-based tab visibility
 * Tests that Network Settings tab is hidden for non-admin users
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { setActivePinia, createPinia } from 'pinia'
import { useUserStore } from '@/stores/user'
import SettingsView from '@/views/SettingsView.vue'

// Mock setupService
vi.mock('@/services/setupService', () => ({
  default: {
    checkStatus: vi.fn().mockResolvedValue({ database_initialized: true }),
    getSerenaStatus: vi.fn().mockResolvedValue({ enabled: false }),
    toggleSerena: vi.fn().mockResolvedValue({ success: true, enabled: true }),
  },
}))

// Mock API config
vi.mock('@/config/api', () => ({
  API_CONFIG: {
    REST_API: {
      baseURL: 'http://localhost:7272',
      timeout: 30000,
      headers: { 'Content-Type': 'application/json' },
    },
  },
}))

// Mock stores
vi.mock('@/stores/settings', () => ({
  useSettingsStore: () => ({
    loadSettings: vi.fn().mockResolvedValue({}),
    updateSettings: vi.fn().mockResolvedValue({}),
  }),
}))

describe('SettingsView.vue - Role-based Tab Visibility', () => {
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
        { path: '/settings', name: 'Settings', component: SettingsView },
      ],
    })

    // Create vuetify instance
    vuetify = createVuetify({
      components,
      directives,
    })

    // Mock fetch for network settings
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            installation: { mode: 'localhost' },
            services: { api: { host: '127.0.0.1', port: 7272 } },
            security: { cors: { allowed_origins: [] } },
          }),
      })
    )
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
    vi.clearAllMocks()
  })

  describe('Admin User - All Tabs Visible', () => {
    beforeEach(async () => {
      userStore.currentUser = { username: 'admin', role: 'admin' }

      wrapper = mount(SettingsView, {
        global: {
          plugins: [router, vuetify],
        },
      })

      await wrapper.vm.$nextTick()
    })

    it('should display Network Settings tab for admin users', () => {
      const tabs = wrapper.findAll('.v-tab')
      const tabTexts = tabs.map(tab => tab.text())

      expect(tabTexts).toContain('Network')
    })

    it('should display all standard tabs for admin', () => {
      const tabs = wrapper.findAll('.v-tab')
      const tabTexts = tabs.map(tab => tab.text())

      expect(tabTexts).toContain('General')
      expect(tabTexts).toContain('Appearance')
      expect(tabTexts).toContain('Notifications')
      expect(tabTexts).toContain('Agent Templates')
      expect(tabTexts).toContain('API and Integrations')
      expect(tabTexts).toContain('API Keys')
      expect(tabTexts).toContain('Database')
      expect(tabTexts).toContain('Network')
    })

    it('should allow admin to click and view Network tab', async () => {
      const networkTab = wrapper.findAll('.v-tab').find(tab =>
        tab.text().includes('Network')
      )

      expect(networkTab).toBeDefined()
      await networkTab.trigger('click')
      await wrapper.vm.$nextTick()

      // Check that network settings content is visible
      const networkContent = wrapper.find('[value="network"]')
      expect(networkContent.exists()).toBe(true)
    })
  })

  describe('Regular User - Limited Tab Access', () => {
    beforeEach(async () => {
      userStore.currentUser = { username: 'testuser', role: 'user' }

      wrapper = mount(SettingsView, {
        global: {
          plugins: [router, vuetify],
        },
      })

      await wrapper.vm.$nextTick()
    })

    it('should NOT display Network Settings tab for regular users', () => {
      const tabs = wrapper.findAll('.v-tab')
      const tabTexts = tabs.map(tab => tab.text())

      expect(tabTexts).not.toContain('Network')
    })

    it('should display all other tabs for regular users', () => {
      const tabs = wrapper.findAll('.v-tab')
      const tabTexts = tabs.map(tab => tab.text())

      expect(tabTexts).toContain('General')
      expect(tabTexts).toContain('Appearance')
      expect(tabTexts).toContain('Notifications')
      expect(tabTexts).toContain('Agent Templates')
      expect(tabTexts).toContain('API and Integrations')
      expect(tabTexts).toContain('API Keys')
      expect(tabTexts).toContain('Database')
    })

    it('should allow regular users to view API Keys tab', async () => {
      const apiKeysTab = wrapper.findAll('.v-tab').find(tab =>
        tab.text().includes('API Keys')
      )

      expect(apiKeysTab).toBeDefined()
      await apiKeysTab.trigger('click')
      await wrapper.vm.$nextTick()

      // API Keys content should be visible
      const apiKeysContent = wrapper.find('[value="apikeys"]')
      expect(apiKeysContent.exists()).toBe(true)
    })
  })

  describe('Unauthenticated User', () => {
    beforeEach(async () => {
      userStore.currentUser = null

      wrapper = mount(SettingsView, {
        global: {
          plugins: [router, vuetify],
        },
      })

      await wrapper.vm.$nextTick()
    })

    it('should NOT display Network Settings tab when not authenticated', () => {
      const tabs = wrapper.findAll('.v-tab')
      const tabTexts = tabs.map(tab => tab.text())

      expect(tabTexts).not.toContain('Network')
    })
  })

  describe('Tab Navigation with Role Restrictions', () => {
    it('should maintain proper tab indexing when Network tab is hidden', async () => {
      userStore.currentUser = { username: 'testuser', role: 'user' }

      wrapper = mount(SettingsView, {
        global: {
          plugins: [router, vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      const tabs = wrapper.findAll('.v-tab')

      // Click through each tab to ensure navigation works
      for (const tab of tabs) {
        await tab.trigger('click')
        await wrapper.vm.$nextTick()
        // Should not throw errors or break navigation
      }

      expect(tabs.length).toBeGreaterThan(0)
    })

    it('should properly display Network icon for admin users', async () => {
      userStore.currentUser = { username: 'admin', role: 'admin' }

      wrapper = mount(SettingsView, {
        global: {
          plugins: [router, vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      const networkTab = wrapper.findAll('.v-tab').find(tab =>
        tab.text().includes('Network')
      )

      expect(networkTab).toBeDefined()
      expect(networkTab.html()).toContain('mdi-network-outline')
    })
  })

  describe('Dynamic Role Changes', () => {
    it('should show Network tab when user role changes from user to admin', async () => {
      userStore.currentUser = { username: 'testuser', role: 'user' }

      wrapper = mount(SettingsView, {
        global: {
          plugins: [router, vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      // Initially no Network tab
      let tabs = wrapper.findAll('.v-tab')
      let tabTexts = tabs.map(tab => tab.text())
      expect(tabTexts).not.toContain('Network')

      // Change to admin
      userStore.currentUser = { username: 'admin', role: 'admin' }
      await wrapper.vm.$nextTick()

      // Now Network tab should appear
      tabs = wrapper.findAll('.v-tab')
      tabTexts = tabs.map(tab => tab.text())
      expect(tabTexts).toContain('Network')
    })

    it('should hide Network tab when admin logs out', async () => {
      userStore.currentUser = { username: 'admin', role: 'admin' }

      wrapper = mount(SettingsView, {
        global: {
          plugins: [router, vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      // Initially has Network tab
      let tabs = wrapper.findAll('.v-tab')
      let tabTexts = tabs.map(tab => tab.text())
      expect(tabTexts).toContain('Network')

      // Logout
      userStore.currentUser = null
      await wrapper.vm.$nextTick()

      // Network tab should be hidden
      tabs = wrapper.findAll('.v-tab')
      tabTexts = tabs.map(tab => tab.text())
      expect(tabTexts).not.toContain('Network')
    })
  })

  describe('Edge Cases', () => {
    it('should handle user with no role as non-admin', async () => {
      userStore.currentUser = { username: 'testuser' }

      wrapper = mount(SettingsView, {
        global: {
          plugins: [router, vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      const tabs = wrapper.findAll('.v-tab')
      const tabTexts = tabs.map(tab => tab.text())
      expect(tabTexts).not.toContain('Network')
    })

    it('should handle case-insensitive admin role', async () => {
      userStore.currentUser = { username: 'admin', role: 'Admin' }

      wrapper = mount(SettingsView, {
        global: {
          plugins: [router, vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      const tabs = wrapper.findAll('.v-tab')
      const tabTexts = tabs.map(tab => tab.text())
      expect(tabTexts).toContain('Network')
    })
  })
})
