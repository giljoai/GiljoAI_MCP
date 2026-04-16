import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PasswordResetPage from '@/saas/views/PasswordResetPage.vue'

// Mock axios
vi.mock('axios', () => ({
  default: {
    post: vi.fn(),
  },
}))

// Mock vue-router
const mockRoute = { query: { token: 'test-token-123' } }
const mockRouter = { push: vi.fn() }
vi.mock('vue-router', () => ({
  useRoute: () => mockRoute,
  useRouter: () => mockRouter,
}))

import axios from 'axios'

describe('PasswordResetPage', () => {
  let wrapper

  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    mockRoute.query.token = 'test-token-123'
  })

  function createWrapper() {
    return mount(PasswordResetPage)
  }

  it('renders the reset password form', () => {
    wrapper = createWrapper()
    expect(wrapper.text()).toContain('Reset Password')
  })

  it('reads token from route query', () => {
    wrapper = createWrapper()
    expect(wrapper.vm.token).toBe('test-token-123')
  })

  it('has new password and confirm password fields', () => {
    wrapper = createWrapper()
    const newPw = wrapper.find('[data-testid="new-password-input"]')
    const confirmPw = wrapper.find('[data-testid="confirm-password-input"]')
    expect(newPw.exists()).toBe(true)
    expect(confirmPw.exists()).toBe(true)
  })

  it('validates minimum 8 characters for password', () => {
    wrapper = createWrapper()
    wrapper.vm.newPassword = 'short'
    wrapper.vm.confirmPassword = 'short'
    expect(wrapper.vm.canSubmit).toBe(false)
  })

  it('validates passwords must match', () => {
    wrapper = createWrapper()
    wrapper.vm.newPassword = 'LongPassword1'
    wrapper.vm.confirmPassword = 'DifferentPass2'
    expect(wrapper.vm.passwordsMatch).toBe(false)
  })

  it('submits to POST /api/saas/password-reset/confirm', async () => {
    axios.post.mockResolvedValueOnce({ data: { message: 'ok' } })
    wrapper = createWrapper()
    wrapper.vm.newPassword = 'ValidPass123'
    wrapper.vm.confirmPassword = 'ValidPass123'
    await wrapper.vm.$nextTick()

    await wrapper.vm.handleSubmit()
    await flushPromises()

    expect(axios.post).toHaveBeenCalledWith(
      '/api/saas/password-reset/confirm',
      { token: 'test-token-123', new_password: 'ValidPass123' },
    )
  })

  it('shows success state after successful reset', async () => {
    axios.post.mockResolvedValueOnce({ data: { message: 'ok' } })
    wrapper = createWrapper()
    wrapper.vm.newPassword = 'ValidPass123'
    wrapper.vm.confirmPassword = 'ValidPass123'
    await wrapper.vm.$nextTick()

    await wrapper.vm.handleSubmit()
    await flushPromises()

    expect(wrapper.vm.resetSuccess).toBe(true)
    expect(wrapper.text()).toContain('Back to Login')
  })

  it('shows error for expired or invalid token', async () => {
    axios.post.mockRejectedValueOnce({
      response: { status: 400, data: { detail: 'Token expired' } },
    })
    wrapper = createWrapper()
    wrapper.vm.newPassword = 'ValidPass123'
    wrapper.vm.confirmPassword = 'ValidPass123'
    await wrapper.vm.$nextTick()

    await wrapper.vm.handleSubmit()
    await flushPromises()

    expect(wrapper.vm.error).toBeTruthy()
    expect(wrapper.text()).toContain('Request new reset link')
  })

  it('shows missing token error when token is absent', () => {
    mockRoute.query.token = undefined
    wrapper = createWrapper()
    expect(wrapper.vm.tokenMissing).toBe(true)
  })

  it('uses smooth-border class on the card', () => {
    mockRoute.query.token = 'test-token-123'
    wrapper = createWrapper()
    expect(wrapper.find('.smooth-border').exists()).toBe(true)
  })
})
