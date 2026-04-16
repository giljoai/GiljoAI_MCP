import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ForgotPasswordEmail from '@/saas/components/ForgotPasswordEmail.vue'

// Mock axios
vi.mock('axios', () => ({
  default: {
    post: vi.fn(),
  },
}))

// Mock configService
vi.mock('@/services/configService', () => ({
  default: {
    config: null,
  },
}))

import axios from 'axios'

describe('ForgotPasswordEmail', () => {
  let wrapper

  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  function createWrapper(props = {}) {
    return mount(ForgotPasswordEmail, {
      props: {
        show: true,
        ...props,
      },
    })
  }

  it('renders the dialog when show is true', () => {
    wrapper = createWrapper()
    expect(wrapper.find('.dlg-header').exists()).toBe(true)
    expect(wrapper.find('.dlg-title').text()).toContain('Forgot Password')
  })

  it('has a close button with dlg-close class', () => {
    wrapper = createWrapper()
    expect(wrapper.find('.dlg-close').exists()).toBe(true)
  })

  it('has an email input field', () => {
    wrapper = createWrapper()
    const input = wrapper.find('[data-testid="forgot-email-input"]')
    expect(input.exists()).toBe(true)
  })

  it('has a submit button', () => {
    wrapper = createWrapper()
    const btn = wrapper.find('[data-testid="forgot-submit-btn"]')
    expect(btn.exists()).toBe(true)
  })

  it('emits update:show when close button is clicked', async () => {
    wrapper = createWrapper()
    await wrapper.find('.dlg-close').trigger('click')
    expect(wrapper.emitted('update:show')).toBeTruthy()
    expect(wrapper.emitted('update:show')[0]).toEqual([false])
  })

  it('calls POST /api/saas/password-reset/request on submit', async () => {
    axios.post.mockResolvedValueOnce({ data: { message: 'ok' } })
    wrapper = createWrapper()

    // Set email value via the component's internal state
    wrapper.vm.email = 'user@example.com'
    await wrapper.vm.$nextTick()

    await wrapper.vm.handleSubmit()
    await flushPromises()

    expect(axios.post).toHaveBeenCalledWith(
      '/api/saas/password-reset/request',
      { email: 'user@example.com' },
    )
  })

  it('shows confirmation message on success', async () => {
    axios.post.mockResolvedValueOnce({ data: { message: 'ok' } })
    wrapper = createWrapper()
    wrapper.vm.email = 'user@example.com'
    await wrapper.vm.$nextTick()

    await wrapper.vm.handleSubmit()
    await flushPromises()

    expect(wrapper.text()).toContain("you'll receive a reset link")
  })

  it('emits success event on successful submission', async () => {
    axios.post.mockResolvedValueOnce({ data: { message: 'ok' } })
    wrapper = createWrapper()
    wrapper.vm.email = 'user@example.com'
    await wrapper.vm.$nextTick()

    await wrapper.vm.handleSubmit()
    await flushPromises()

    expect(wrapper.emitted('success')).toBeTruthy()
  })

  it('shows error message on API failure', async () => {
    axios.post.mockRejectedValueOnce({
      response: { data: { detail: 'Server error' } },
    })
    wrapper = createWrapper()
    wrapper.vm.email = 'user@example.com'
    await wrapper.vm.$nextTick()

    await wrapper.vm.handleSubmit()
    await flushPromises()

    expect(wrapper.vm.error).toBeTruthy()
  })

  it('uses smooth-border class on the card', () => {
    wrapper = createWrapper()
    expect(wrapper.find('.smooth-border').exists()).toBe(true)
  })
})
