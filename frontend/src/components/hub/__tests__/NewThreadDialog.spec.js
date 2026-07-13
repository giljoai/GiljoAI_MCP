/**
 * NewThreadDialog.spec.js — FE-6121
 *
 * Tests (DoD-6 — severity dropdown removed):
 *  - the severity selector is no longer rendered
 *  - creating a thread does NOT send a severity field
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createVuetify } from 'vuetify'

// ---- mocks ----
const createThreadMock = vi.fn()
const showToastMock = vi.fn()

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ showToast: showToastMock }),
}))

vi.mock('@/services/api', () => ({
  default: {
    threads: {
      list: vi.fn(() => Promise.resolve({ data: { threads: [] } })),
      create: (...args) => createThreadMock(...args),
    },
  },
}))

import NewThreadDialog from '@/components/hub/NewThreadDialog.vue'

const vuetify = createVuetify()

function mountDialog() {
  return mount(NewThreadDialog, {
    props: { modelValue: true },
    global: { plugins: [createPinia(), vuetify] },
    attachTo: document.body,
  })
}

describe('NewThreadDialog', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    createThreadMock.mockReset()
    createThreadMock.mockResolvedValue({ data: { thread_id: 'thr-new', chat_id: 'CHT-0009' } })
    showToastMock.mockClear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('does not render the severity selector', () => {
    const wrapper = mountDialog()
    expect(wrapper.find('[data-testid="new-thread-severity"]').exists()).toBe(false)
  })

  it('creating a thread does not include a severity field in the body', async () => {
    const wrapper = mountDialog()
    wrapper.vm.form.subject = 'Coordination thread'
    await wrapper.vm.$nextTick()

    await wrapper.find('[data-testid="new-thread-submit"]').trigger('click')
    await flushPromises()

    expect(createThreadMock).toHaveBeenCalledTimes(1)
    const [body] = createThreadMock.mock.calls[0]
    expect(body.subject).toBe('Coordination thread')
    expect(body.severity).toBeUndefined()
    expect('severity' in body).toBe(false)
  })
})
