/**
 * AUTH-EMAIL Phase 4 frontend contract: the forgot-password PIN flow
 * identifier field must indicate that either an email OR a username can
 * be entered. Backend dual-lookup is being extended to /verify-pin and
 * /verify-pin-and-reset-password in parallel.
 *
 * Guard-rails:
 *   - Label reads "Email or username".
 *   - aria-label reads "Enter your email or username".
 *   - autocomplete stays "username".
 *   - The literal "Invalid username or PIN." fallback is INTENTIONALLY kept
 *     (mirrors backend no-enumeration security wording) — not asserted here.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/services/api', () => ({
  default: { post: vi.fn(() => Promise.resolve({ data: {} })) },
}))

import ForgotPasswordPin from '@/components/ForgotPasswordPin.vue'

describe('ForgotPasswordPin.vue -- identifier field accepts email or username (AUTH-EMAIL Phase 4)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
  })

  function mountDialog() {
    return mount(ForgotPasswordPin, {
      props: { show: true },
      global: {
        stubs: {
          AppAlert: { template: '<div class="app-alert"><slot /></div>' },
        },
      },
      attachTo: document.body,
    })
  }

  it('uses "Email or username" as the identifier field label', async () => {
    mountDialog()
    await flushPromises()

    // v-dialog teleports; read from document
    const html = document.body.innerHTML
    expect(html).toContain('Email or username')
    expect(html).not.toMatch(/label="Username"/)
  })

  it('uses "Enter your email or username" as the aria-label', async () => {
    mountDialog()
    await flushPromises()

    const html = document.body.innerHTML
    expect(html).toContain('aria-label="Enter your email or username"')
    expect(html).not.toContain('aria-label="Enter your username"')
  })
})
