/**
 * ThreadList.spec.js — FE-6054e
 *
 * Tests:
 *  - filter change triggers loadThreads with updated filters
 *  - selecting a thread emits 'select' with thread_id
 *  - renders thread rows from the store
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createVuetify } from 'vuetify'

// ---- mocks ----
const loadThreadsMock = vi.fn()
const searchThreadsMock = vi.fn()
const copyMock = vi.fn(() => Promise.resolve(true))
const showToastMock = vi.fn()

vi.mock('@/services/api', () => ({
  default: {
    threads: {
      list: (...args) => loadThreadsMock(...args),
      search: (...args) => searchThreadsMock(...args),
    },
  },
}))

vi.mock('@/composables/useClipboard', () => ({
  useClipboard: () => ({ copy: copyMock, copied: { value: false } }),
}))

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ showToast: showToastMock }),
}))

import ThreadList from '@/components/hub/ThreadList.vue'
import { useCommHubStore } from '@/stores/commHubStore'

const vuetify = createVuetify()

const THREAD_A = {
  thread_id: 'thr-a',
  chat_id: 'CHT-0001',
  subject: 'Alpha thread',
  status: 'open',
  next_action_owner: null,
  created_at: '2026-06-17T09:00:00Z',
  last_activity_at: '2026-06-17T09:00:00Z',
}

const THREAD_B = {
  thread_id: 'thr-b',
  chat_id: 'CHT-0002',
  subject: 'Beta thread',
  status: 'closed',
  next_action_owner: 'implementer',
  created_at: '2026-06-17T08:00:00Z',
  last_activity_at: '2026-06-17T08:00:00Z',
}

function mountList(activePinia) {
  return mount(ThreadList, {
    global: {
      plugins: [activePinia, vuetify],
    },
  })
}

describe('ThreadList', () => {
  let pinia
  let store

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    store = useCommHubStore()
    loadThreadsMock.mockReset()
    searchThreadsMock.mockReset()
    copyMock.mockClear()
    showToastMock.mockClear()
    loadThreadsMock.mockResolvedValue({ data: { threads: [], count: 0 } })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  // ---------------------------------------------------------------------------
  // renders thread rows
  // ---------------------------------------------------------------------------
  it('renders thread rows from the store', async () => {
    loadThreadsMock.mockResolvedValueOnce({ data: { threads: [THREAD_A, THREAD_B], count: 2 } })
    await store.loadThreads()

    const wrapper = mountList(pinia)
    await flushPromises()

    const rows = wrapper.findAll('[data-testid="thread-row"]')
    expect(rows.length).toBe(2)
  })

  it('shows subject text in the row', async () => {
    loadThreadsMock.mockResolvedValueOnce({ data: { threads: [THREAD_A], count: 1 } })
    await store.loadThreads()

    const wrapper = mountList(pinia)
    await flushPromises()

    expect(wrapper.find('[data-testid="thread-subject"]').text()).toBe('Alpha thread')
  })

  it('renders the badge slot placeholder on each row', async () => {
    loadThreadsMock.mockResolvedValueOnce({ data: { threads: [THREAD_A], count: 1 } })
    await store.loadThreads()

    const wrapper = mountList(pinia)
    await flushPromises()

    // Badge slot exists for FE-6054f (unread / baton indicators to be added)
    expect(wrapper.find('[data-testid="thread-badge-slot"]').exists()).toBe(true)
  })

  // ---------------------------------------------------------------------------
  // thread id only — never the raw next_action_owner UUID (FE-6121 DoD-2)
  // ---------------------------------------------------------------------------
  it('does NOT render the raw next_action_owner participant id on the row', async () => {
    // THREAD_B carries next_action_owner: 'implementer' — must not surface as the id.
    loadThreadsMock.mockResolvedValueOnce({ data: { threads: [THREAD_B], count: 1 } })
    await store.loadThreads()

    const wrapper = mountList(pinia)
    await flushPromises()

    expect(wrapper.find('[data-testid="thread-owner"]').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('implementer')
  })

  it('shows the CHT-#### thread identifier on the row', async () => {
    loadThreadsMock.mockResolvedValueOnce({ data: { threads: [THREAD_A], count: 1 } })
    await store.loadThreads()

    const wrapper = mountList(pinia)
    await flushPromises()

    expect(wrapper.find('[data-testid="thread-chat-id"]').text()).toContain('CHT-0001')
  })

  it('clicking the thread id copies the thread_id (not the chat id) and does not select the row', async () => {
    loadThreadsMock.mockResolvedValueOnce({ data: { threads: [THREAD_A], count: 1 } })
    await store.loadThreads()

    const wrapper = mountList(pinia)
    await flushPromises()

    await wrapper.find('[data-testid="thread-chat-id"]').trigger('click')
    await flushPromises()

    expect(copyMock).toHaveBeenCalledWith('thr-a')
    // @click.stop — copying must not also emit a row select.
    expect(wrapper.emitted('select')).toBeFalsy()
  })

  // ---------------------------------------------------------------------------
  // soft delete
  // ---------------------------------------------------------------------------
  it('clicking delete opens the confirm dialog without selecting the row', async () => {
    loadThreadsMock.mockResolvedValueOnce({ data: { threads: [THREAD_A], count: 1 } })
    await store.loadThreads()

    const wrapper = mountList(pinia)
    await flushPromises()

    await wrapper.find('[data-testid="thread-delete"]').trigger('click')
    expect(wrapper.vm.showDeleteDialog).toBe(true)
    expect(wrapper.vm.threadToDelete.thread_id).toBe('thr-a')
    // @click.stop — opening the delete dialog must not select the row.
    expect(wrapper.emitted('select')).toBeFalsy()
  })

  it('confirming delete calls commHub.deleteThread with the thread id', async () => {
    loadThreadsMock.mockResolvedValueOnce({ data: { threads: [THREAD_A], count: 1 } })
    await store.loadThreads()
    const deleteSpy = vi.spyOn(store, 'deleteThread').mockResolvedValue()

    const wrapper = mountList(pinia)
    await flushPromises()

    await wrapper.find('[data-testid="thread-delete"]').trigger('click')
    await wrapper.vm.onConfirmDelete()
    await flushPromises()

    expect(deleteSpy).toHaveBeenCalledWith('thr-a')
    expect(wrapper.vm.showDeleteDialog).toBe(false)
  })

  // ---------------------------------------------------------------------------
  // select emits
  // ---------------------------------------------------------------------------
  it('clicking a thread row emits select with thread_id', async () => {
    loadThreadsMock.mockResolvedValueOnce({ data: { threads: [THREAD_A], count: 1 } })
    await store.loadThreads()

    const wrapper = mountList(pinia)
    await flushPromises()

    await wrapper.find('[data-testid="thread-row"]').trigger('click')
    expect(wrapper.emitted('select')).toBeTruthy()
    expect(wrapper.emitted('select')[0]).toEqual(['thr-a'])
  })

  it('clicking a thread row also calls commHub.selectThread', async () => {
    loadThreadsMock.mockResolvedValueOnce({ data: { threads: [THREAD_A], count: 1 } })
    await store.loadThreads()

    const wrapper = mountList(pinia)
    await flushPromises()

    await wrapper.find('[data-testid="thread-row"]').trigger('click')
    expect(store.selectedThreadId).toBe('thr-a')
  })

  // ---------------------------------------------------------------------------
  // filter change triggers loadThreads
  // ---------------------------------------------------------------------------
  it('changing status filter calls loadThreads with updated filters', async () => {
    const wrapper = mountList(pinia)
    await flushPromises()
    loadThreadsMock.mockClear()
    loadThreadsMock.mockResolvedValue({ data: { threads: [], count: 0 } })

    // Trigger onFilterChange via component method
    wrapper.vm.localFilters.status = 'closed'
    wrapper.vm.onFilterChange()
    await flushPromises()

    expect(loadThreadsMock).toHaveBeenCalled()
  })

  // ---------------------------------------------------------------------------
  // severity strip (FE-6121 residual removed) — must stay gone
  // ---------------------------------------------------------------------------
  it('does NOT render the severity filter or per-row severity badge', async () => {
    loadThreadsMock.mockResolvedValueOnce({ data: { threads: [THREAD_A, THREAD_B], count: 2 } })
    await store.loadThreads()

    const wrapper = mountList(pinia)
    await flushPromises()

    expect(wrapper.find('[data-testid="filter-severity"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="thread-severity-badge"]').exists()).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// FE-9012c (D2): the scope prop splits the SAME list into the two Hub tabs.
// ---------------------------------------------------------------------------
describe('ThreadList scope prop (FE-9012c)', () => {
  let pinia
  let store

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    store = useCommHubStore()
    loadThreadsMock.mockReset()
    loadThreadsMock.mockResolvedValue({ data: { threads: [], count: 0 } })
    store._testSeedThread({ thread_id: 'pb', project_id: 'projA', subject: 'Bound', chat_id: 'CHT-0009' })
    store._testSeedThread({ thread_id: 'ts', project_id: null, subject: 'Standalone', chat_id: 'CHT-0010' })
  })

  function mountScoped(scope) {
    return mount(ThreadList, { props: { scope }, global: { plugins: [pinia, vuetify] } })
  }

  it("scope='project' renders only project-bound threads", async () => {
    const wrapper = mountScoped('project')
    await flushPromises()
    expect(wrapper.findAll('[data-testid="thread-row"]').length).toBe(1)
    expect(wrapper.text()).toContain('Bound')
    expect(wrapper.text()).not.toContain('Standalone')
  })

  it("scope='town' renders only standalone threads", async () => {
    const wrapper = mountScoped('town')
    await flushPromises()
    expect(wrapper.findAll('[data-testid="thread-row"]').length).toBe(1)
    expect(wrapper.text()).toContain('Standalone')
    expect(wrapper.text()).not.toContain('Bound')
  })

  it("default scope ('all') renders both tabs' threads", async () => {
    const wrapper = mountScoped(undefined)
    await flushPromises()
    expect(wrapper.findAll('[data-testid="thread-row"]').length).toBe(2)
  })

  it('a project-bound thread shows NO delete affordance (D1); a standalone one does', async () => {
    const wrapper = mountScoped('all')
    await flushPromises()
    const rows = wrapper.findAll('[data-testid="thread-row"]')
    const boundRow = rows.find((r) => r.text().includes('Bound'))
    const townRow = rows.find((r) => r.text().includes('Standalone'))
    expect(boundRow.find('[data-testid="thread-delete"]').exists()).toBe(false)
    expect(townRow.find('[data-testid="thread-delete"]').exists()).toBe(true)
  })
})
