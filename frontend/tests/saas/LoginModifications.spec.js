import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { ref, nextTick } from 'vue'

// Mock configService with controllable giljoMode
let mockGiljoMode = 'ce'
vi.mock('@/services/configService', () => ({
  default: {
    fetchConfig: vi.fn(() => Promise.resolve()),
    getGiljoMode: vi.fn(() => mockGiljoMode),
    config: null,
  },
}))

// Mock vue-router
const mockPush = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
  useRoute: () => ({
    query: {},
  }),
}))

// Mock getRuntimeConfig
vi.mock('@/config/api', () => ({
  getRuntimeConfig: vi.fn(() => null),
}))

// Mock user store
vi.mock('@/stores/user', () => ({
  useUserStore: () => ({
    currentUser: null,
    login: vi.fn(() => Promise.resolve(true)),
    fetchCurrentUser: vi.fn(),
  }),
}))

import Login from '@/views/Login.vue'
import configService from '@/services/configService'

describe('Login.vue -- SaaS modifications', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    mockGiljoMode = 'ce'
  })

  function mountLogin() {
    return mount(Login, {
      global: {
        stubs: {
          'router-link': {
            props: ['to'],
            template: '<a :href="to"><slot /></a>',
          },
          ForgotPasswordPin: { template: '<div class="forgot-pin-stub" />' },
          AppAlert: { template: '<div class="app-alert"><slot /></div>' },
        },
      },
    })
  }

  describe('Edition badge', () => {
    it('shows "Community Edition" in CE mode', async () => {
      mockGiljoMode = 'ce'
      const wrapper = mountLogin()
      await flushPromises()

      expect(wrapper.find('.edition-badge').text()).toContain('Community Edition')
    })

    it('shows "Demo Edition" in demo mode', async () => {
      mockGiljoMode = 'demo'
      const wrapper = mountLogin()
      await flushPromises()

      expect(wrapper.find('.edition-badge').text()).toContain('Demo Edition')
    })

    it('shows "SaaS Edition" in saas mode', async () => {
      mockGiljoMode = 'saas'
      const wrapper = mountLogin()
      await flushPromises()

      expect(wrapper.find('.edition-badge').text()).toContain('SaaS Edition')
    })
  })

  describe('Register link', () => {
    it('does NOT show register link in CE mode', async () => {
      mockGiljoMode = 'ce'
      const wrapper = mountLogin()
      await flushPromises()

      expect(wrapper.html()).not.toContain("Don't have an account?")
    })

    it('shows register link in demo mode', async () => {
      mockGiljoMode = 'demo'
      const wrapper = mountLogin()
      await flushPromises()

      const html = wrapper.html()
      expect(html).toContain("Don't have an account?")
      expect(html).toContain('Register')
    })

    it('shows register link in saas mode', async () => {
      mockGiljoMode = 'saas'
      const wrapper = mountLogin()
      await flushPromises()

      const html = wrapper.html()
      expect(html).toContain("Don't have an account?")
      expect(html).toContain('Register')
    })
  })

  describe('Forgot password conditional', () => {
    it('opens PIN-based dialog in CE mode', async () => {
      mockGiljoMode = 'ce'
      const wrapper = mountLogin()
      await flushPromises()

      // Click forgot password
      const forgotBtn = wrapper.find('[aria-label="Open forgot password dialog"]')
      expect(forgotBtn.exists()).toBe(true)
      await forgotBtn.trigger('click')

      // Should show the ForgotPasswordPin stub
      expect(wrapper.vm.showForgotPassword).toBe(true)
    })

    it('opens email-based dialog in demo mode', async () => {
      mockGiljoMode = 'demo'
      const wrapper = mountLogin()
      await flushPromises()

      const forgotBtn = wrapper.find('[aria-label="Open forgot password dialog"]')
      await forgotBtn.trigger('click')

      // In SaaS/demo mode, should open email-based forgot password
      expect(wrapper.vm.showForgotPasswordEmail).toBe(true)
    })
  })
})
