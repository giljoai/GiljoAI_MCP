import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { ref } from 'vue'

// Mock configService
vi.mock('@/services/configService', () => ({
  default: {
    fetchConfig: vi.fn(() => Promise.resolve()),
    getGiljoMode: vi.fn(() => 'demo'),
    config: { giljo_mode: 'demo' },
  },
}))

// Mock useSaasMode composable
vi.mock('@/saas/composables/useSaasMode', () => ({
  useSaasMode: () => ({
    giljoMode: ref('demo'),
    isSaas: ref(false),
    isDemo: ref(true),
    isCe: ref(false),
    isSaasOrDemo: ref(true),
    editionLabel: ref('Demo Edition'),
    init: vi.fn(() => Promise.resolve()),
  }),
}))

// Mock vue-router
vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
  useRoute: () => ({
    query: {},
  }),
}))

// Mock axios
vi.mock('axios', () => {
  const post = vi.fn()
  return {
    default: {
      post,
      create: vi.fn(() => ({
        post,
        interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
      })),
    },
  }
})

import RegisterView from '@/saas/views/RegisterView.vue'
import axios from 'axios'

describe('RegisterView.vue', () => {
  let wrapper

  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
  })

  function mountComponent() {
    return mount(RegisterView, {
      global: {
        stubs: {
          'router-link': { template: '<a><slot /></a>' },
          AppAlert: {
            props: ['type', 'variant', 'closable'],
            template: '<div class="app-alert"><slot /></div>',
          },
        },
      },
    })
  }

  /** Helper to fill form and submit */
  async function fillAndSubmit(w, { email = 'test@example.com', name = 'Test User' } = {}) {
    // Access the component's internal state directly since stubs don't propagate v-model
    w.vm.email = email
    w.vm.name = name
    await w.vm.$nextTick()
    await w.vm.handleRegister()
    await flushPromises()
  }

  it('renders the registration form with required fields', () => {
    wrapper = mountComponent()
    const html = wrapper.html()

    expect(html).toContain('v-text-field')
    expect(wrapper.find('[data-testid="register-button"]').exists()).toBe(true)
    expect(html).toContain('Demo Edition')
  })

  it('renders a honeypot field that is visually hidden', () => {
    wrapper = mountComponent()
    const honeypot = wrapper.find('[data-testid="honeypot-field"]')
    expect(honeypot.exists()).toBe(true)
  })

  it('shows "Already have an account? Sign In" link', () => {
    wrapper = mountComponent()
    const html = wrapper.html()
    expect(html).toContain('Already have an account?')
    expect(html).toContain('Sign In')
  })

  it('shows success message after successful registration', async () => {
    axios.post.mockResolvedValueOnce({
      status: 201,
      data: { message: 'Registration successful', org_id: 'test-org-123' },
    })

    wrapper = mountComponent()
    await fillAndSubmit(wrapper)

    expect(wrapper.html()).toContain('Check your email')
    expect(axios.post).toHaveBeenCalledWith(
      expect.stringContaining('/api/saas/register'),
      expect.objectContaining({ email: 'test@example.com' }),
    )
  })

  it('shows error message on 409 duplicate email', async () => {
    axios.post.mockRejectedValueOnce({
      response: { status: 409, data: { detail: 'Email already registered' } },
    })

    wrapper = mountComponent()
    await fillAndSubmit(wrapper, { email: 'taken@example.com' })

    expect(wrapper.html()).toContain('already registered')
  })

  it('shows error message on 429 rate limit', async () => {
    axios.post.mockRejectedValueOnce({
      response: { status: 429, data: { detail: 'Too many requests' } },
    })

    wrapper = mountComponent()
    await fillAndSubmit(wrapper)

    expect(wrapper.html()).toContain('Too many')
  })

  it('disables submit button when email is empty', () => {
    wrapper = mountComponent()
    const btn = wrapper.find('[data-testid="register-button"]')
    expect(btn.attributes('disabled')).toBeDefined()
  })

  it('has the GiljoAI logo', () => {
    wrapper = mountComponent()
    expect(wrapper.html()).toContain('Giljo_YW.svg')
  })

  it('shows validation error on 422 response', async () => {
    axios.post.mockRejectedValueOnce({
      response: { status: 422, data: { detail: 'Invalid input' } },
    })

    wrapper = mountComponent()
    await fillAndSubmit(wrapper, { email: 'bad@example.com' })

    expect(wrapper.html()).toContain('Invalid')
  })

  it('shows network error when server is unreachable', async () => {
    axios.post.mockRejectedValueOnce({
      code: 'ERR_NETWORK',
      response: undefined,
    })

    wrapper = mountComponent()
    await fillAndSubmit(wrapper)

    expect(wrapper.html()).toContain('Network error')
  })

  it('sends honeypot value when filled by a bot', async () => {
    axios.post.mockResolvedValueOnce({ status: 201, data: { message: 'ok' } })

    wrapper = mountComponent()
    wrapper.vm.website = 'bot-value'
    await fillAndSubmit(wrapper)

    expect(axios.post).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ website: 'bot-value' }),
    )
  })
})
