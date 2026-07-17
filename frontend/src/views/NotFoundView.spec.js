/**
 * NotFoundView.spec.js — TSK-9216
 *
 * The catch-all 404 route (/:pathMatch(.*)*) rendered an unfinished placeholder.
 * This locks the finished page: it renders the 404 identity + message and offers
 * a route-home action (plus a go-back action).
 *
 * Edition scope: Both (shared frontend/src view).
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'

const h = vi.hoisted(() => ({
  push: vi.fn(),
  back: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: h.push, back: h.back }),
}))

import NotFoundView from './NotFoundView.vue'

const passthrough = { template: '<div><slot /></div>' }

function mountView() {
  return mount(NotFoundView, {
    global: {
      stubs: {
        'v-container': passthrough,
        'v-row': passthrough,
        'v-col': passthrough,
        'v-card': passthrough,
        'v-icon': { template: '<i><slot /></i>' },
        'v-btn': {
          inheritAttrs: false,
          template: '<button v-bind="$attrs" @click="$emit(\'click\')"><slot /></button>',
        },
      },
    },
  })
}

describe('NotFoundView (TSK-9216)', () => {
  beforeEach(() => {
    h.push.mockClear()
    h.back.mockClear()
  })

  it('renders the finished 404 page (not the placeholder stub)', () => {
    const wrapper = mountView()
    const text = wrapper.text()
    expect(text).toContain('404')
    expect(text).toContain('Page not found')
    // The old stub copy must be gone.
    expect(text).not.toContain('Awaiting implementation')
    expect(wrapper.find('[data-testid="notfound-home"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="notfound-back"]').exists()).toBe(true)
  })

  it('the Home action routes to /', async () => {
    const wrapper = mountView()
    await wrapper.find('[data-testid="notfound-home"]').trigger('click')
    expect(h.push).toHaveBeenCalledWith('/')
  })

  it('the Back action navigates (history back, or Home when there is no history)', async () => {
    const wrapper = mountView()
    await wrapper.find('[data-testid="notfound-back"]').trigger('click')
    const navigated = h.back.mock.calls.length > 0 || h.push.mock.calls.some((c) => c[0] === '/')
    expect(navigated).toBe(true)
  })
})
