/**
 * HubComposer.spec.js — FE-6054e
 *
 * Tests:
 *  - broadcast mode sends without to_participant
 *  - direct mode sends with to_participant from dropdown
 *  - slider enabled (loop) sets loop_directive: true in the post body
 *  - slider Off leaves loop_directive undefined
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createVuetify } from 'vuetify'

// ---- mocks ----
const postMessageMock = vi.fn()
const showToastMock = vi.fn()
const participantsMock = vi.fn(() => Promise.resolve({ data: { participants: [] } }))

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ showToast: showToastMock }),
}))

vi.mock('@/services/api', () => ({
  default: {
    threads: {
      list: vi.fn(() => Promise.resolve({ data: { threads: [] } })),
      post: (...args) => postMessageMock(...args),
      participants: (...args) => participantsMock(...args),
    },
  },
}))

import HubComposer from '@/components/hub/HubComposer.vue'
import AutoCheckinControls from '@/components/projects/AutoCheckinControls.vue'
import { useCommHubStore } from '@/stores/commHubStore'

const vuetify = createVuetify()

function mountComposer(activePinia) {
  return mount(HubComposer, {
    global: {
      plugins: [activePinia, vuetify],
    },
  })
}

describe('HubComposer', () => {
  let pinia
  let store

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    store = useCommHubStore()
    postMessageMock.mockReset()
    showToastMock.mockClear()
    participantsMock.mockReset()
    participantsMock.mockResolvedValue({ data: { participants: [] } })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  // ---------------------------------------------------------------------------
  // broadcast mode
  // ---------------------------------------------------------------------------
  it('broadcast mode: sends without to_participant field', async () => {
    store.selectedThreadId = 'thr-001'
    postMessageMock.mockResolvedValue({ data: { message_id: 'msg-new' } })

    const wrapper = mountComposer(pinia)

    // Ensure broadcast mode
    wrapper.vm.isBroadcast = true
    // Set content directly on the reactive ref
    wrapper.vm.content = 'Hello agents'
    await wrapper.vm.$nextTick()

    await wrapper.find('[data-testid="send-btn"]').trigger('click')
    await flushPromises()

    expect(postMessageMock).toHaveBeenCalledTimes(1)
    const [_threadId, body] = postMessageMock.mock.calls[0]
    expect(_threadId).toBe('thr-001')
    expect(body.content).toBe('Hello agents')
    expect(body.to_participant).toBeUndefined()
  })

  // ---------------------------------------------------------------------------
  // direct mode
  // ---------------------------------------------------------------------------
  it('direct mode: includes to_participant when agent is selected', async () => {
    store.selectedThreadId = 'thr-001'
    // Seed participants
    store.participantsByThreadId.set('thr-001', [
      {
        participant_id: 'p-impl',
        display_name: 'implementer',
        participant_type: 'agent',
        role: 'implementer',
      },
    ])

    postMessageMock.mockResolvedValue({ data: { message_id: 'msg-direct' } })

    const wrapper = mountComposer(pinia)

    // Switch to direct mode and select participant
    wrapper.vm.isBroadcast = false
    wrapper.vm.selectedParticipant = 'p-impl'
    wrapper.vm.content = 'Direct message'
    await wrapper.vm.$nextTick()

    await wrapper.find('[data-testid="send-btn"]').trigger('click')
    await flushPromises()

    expect(postMessageMock).toHaveBeenCalledTimes(1)
    const [_threadId, body] = postMessageMock.mock.calls[0]
    expect(body.to_participant).toBe('p-impl')
    expect(body.content).toBe('Direct message')
  })

  // ---------------------------------------------------------------------------
  // loop directive
  // ---------------------------------------------------------------------------
  it('slider enabled: sets loop_directive true AND carries the chosen interval (FE-6140)', async () => {
    store.selectedThreadId = 'thr-001'
    postMessageMock.mockResolvedValue({ data: { message_id: 'msg-loop' } })

    const wrapper = mountComposer(pinia)

    // Enable loop via the exposed handler with a chosen cadence.
    wrapper.vm.onCheckinUpdate({ enabled: true, interval: 30 })
    wrapper.vm.content = 'Loop enabled message'
    await wrapper.vm.$nextTick()

    await wrapper.find('[data-testid="send-btn"]').trigger('click')
    await flushPromises()

    expect(postMessageMock).toHaveBeenCalledTimes(1)
    const [, body] = postMessageMock.mock.calls[0]
    expect(body.loop_directive).toBe(true)
    // FE-6140: the interval must round-trip in the body (it used to die here).
    expect(body.loop_interval_minutes).toBe(30)
  })

  it('slider Off: does NOT set loop_directive or interval in the body', async () => {
    store.selectedThreadId = 'thr-001'
    postMessageMock.mockResolvedValue({ data: { message_id: 'msg-noloop' } })

    const wrapper = mountComposer(pinia)

    wrapper.vm.onCheckinUpdate({ enabled: false })
    wrapper.vm.content = 'No loop'
    await wrapper.vm.$nextTick()

    await wrapper.find('[data-testid="send-btn"]').trigger('click')
    await flushPromises()

    expect(postMessageMock).toHaveBeenCalledTimes(1)
    const [, body] = postMessageMock.mock.calls[0]
    expect(body.loop_directive).toBeUndefined()
    expect(body.loop_interval_minutes).toBeUndefined()
  })

  it('renames the reused control to "Request Auto Check-in" (FE-6140)', () => {
    store.selectedThreadId = 'thr-001'
    const wrapper = mountComposer(pinia)
    // The control is the shared AutoCheckinControls, relabelled in the Hub context
    // via the `label` prop (the project staging usage keeps "Auto Check-in").
    const control = wrapper.findComponent(AutoCheckinControls)
    expect(control.exists()).toBe(true)
    expect(control.props('label')).toBe('Request Auto Check-in')
  })

  // ---------------------------------------------------------------------------
  // dropdown reactivity (FE-6121 DoD-3) — newly-joined agents appear w/o refresh
  // ---------------------------------------------------------------------------
  it('switching to Direct mode refetches participants', async () => {
    store.selectedThreadId = 'thr-001'
    const wrapper = mountComposer(pinia)
    participantsMock.mockClear()

    wrapper.vm.isBroadcast = false
    await wrapper.vm.$nextTick()
    await flushPromises()

    expect(participantsMock).toHaveBeenCalledWith('thr-001')
  })

  it('opening the agent menu refetches participants', async () => {
    store.selectedThreadId = 'thr-001'
    const wrapper = mountComposer(pinia)
    participantsMock.mockClear()

    wrapper.vm.onAgentMenu(true)
    await flushPromises()

    expect(participantsMock).toHaveBeenCalledWith('thr-001')
  })

  it('a freshly-joined agent appears in the dropdown items after a participants refetch', async () => {
    store.selectedThreadId = 'thr-001'
    // Initial participants: only an earlier-joined agent.
    store.participantsByThreadId.set('thr-001', [
      { participant_id: 'p-old', display_name: 'git_EM_12', participant_type: 'agent' },
    ])

    const wrapper = mountComposer(pinia)
    expect(wrapper.vm.participantItems.map((p) => p.participant_id)).toEqual(['p-old'])

    // Simulate the refetch (triggered by opening the dropdown) returning a NEW join.
    participantsMock.mockResolvedValueOnce({
      data: {
        participants: [
          { participant_id: 'p-old', display_name: 'git_EM_12', participant_type: 'agent' },
          { participant_id: 'p-new', display_name: 'CI2_lane', participant_type: 'agent' },
        ],
      },
    })
    wrapper.vm.onAgentMenu(true)
    await flushPromises()
    await wrapper.vm.$nextTick()

    expect(wrapper.vm.participantItems.map((p) => p.participant_id)).toEqual(['p-old', 'p-new'])
  })

  it('participantItems still filters out the human user participant', async () => {
    store.selectedThreadId = 'thr-001'
    store.participantsByThreadId.set('thr-001', [
      { participant_id: 'p-user', display_name: 'Patrik', participant_type: 'user' },
      { participant_id: 'p-agent', display_name: 'CI2_lane', participant_type: 'agent' },
    ])
    const wrapper = mountComposer(pinia)
    expect(wrapper.vm.participantItems.map((p) => p.participant_id)).toEqual(['p-agent'])
  })

  // ---------------------------------------------------------------------------
  // send disabled guards
  // ---------------------------------------------------------------------------
  it('send button is disabled when content is empty', async () => {
    store.selectedThreadId = 'thr-001'
    const wrapper = mountComposer(pinia)
    wrapper.vm.content = ''
    await wrapper.vm.$nextTick()
    const btn = wrapper.find('[data-testid="send-btn"]')
    expect(btn.attributes('disabled')).toBeDefined()
  })

  it('send button is disabled when no thread is selected', async () => {
    const wrapper = mountComposer(pinia)
    wrapper.vm.content = 'Some content'
    await wrapper.vm.$nextTick()
    const btn = wrapper.find('[data-testid="send-btn"]')
    expect(btn.attributes('disabled')).toBeDefined()
  })
})
