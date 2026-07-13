/**
 * ThreadTimeline.spec.js — FE-6122
 *
 * User-vs-agent author rendering:
 *  - A genuine USER post (from_agent_id is the user's UUID) renders the
 *    brand-yellow user avatar treatment + the user's initials.
 *  - An AGENT post (from_agent_id is a role slug) renders the tinted role
 *    color badge — NOT the user treatment.
 * The signal is from_agent_id (UUID = user, slug = agent), robust to the
 * persisted display name being the real human name.
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createVuetify } from 'vuetify'

import ThreadTimeline from '@/components/hub/ThreadTimeline.vue'
import { useCommHubStore } from '@/stores/commHubStore'

const vuetify = createVuetify()
const THREAD_ID = 'thr-timeline'
const USER_UUID = '550e8400-e29b-41d4-a716-446655440000'

const USER_MSG = {
  thread_id: THREAD_ID,
  message_id: 'msg-user',
  from_agent_id: USER_UUID,
  from_display_name: 'Patrik Pettersson',
  content: 'operator speaking',
  message_type: 'broadcast',
  created_at: '2026-06-18T10:00:00Z',
}

const AGENT_MSG = {
  thread_id: THREAD_ID,
  message_id: 'msg-agent',
  from_agent_id: 'implementer',
  from_display_name: 'implementer',
  content: 'building it',
  message_type: 'broadcast',
  created_at: '2026-06-18T10:01:00Z',
}

function mountTimeline(pinia) {
  return mount(ThreadTimeline, { global: { plugins: [pinia, vuetify] } })
}

describe('ThreadTimeline author rendering (FE-6122)', () => {
  let pinia
  let store

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    store = useCommHubStore()
    store.selectedThreadId = THREAD_ID
    store.handleThreadMessage(USER_MSG)
    store.handleThreadMessage(AGENT_MSG)
  })

  it('renders both messages on the selected thread', () => {
    const wrapper = mountTimeline(pinia)
    expect(wrapper.findAll('.timeline-msg').length).toBe(2)
  })

  it('renders a USER post with the brand-yellow user avatar treatment + initials', () => {
    const wrapper = mountTimeline(pinia)
    const row = wrapper.find('[data-testid="timeline-message-msg-user"]')
    expect(row.classes()).toContain('timeline-msg--user')
    const avatar = row.find('.timeline-msg__avatar')
    expect(avatar.classes()).toContain('timeline-msg__avatar--user')
    // initials from the real display name, not an agent abbrev
    expect(avatar.text()).toBe('PP')
    // no inline agent color style applied to the user avatar
    expect(avatar.attributes('style') || '').not.toContain('background-color')
  })

  it('renders an AGENT post with a tinted role color badge, NOT the user treatment', () => {
    const wrapper = mountTimeline(pinia)
    const row = wrapper.find('[data-testid="timeline-message-msg-agent"]')
    expect(row.classes()).toContain('timeline-msg--agent')
    const avatar = row.find('.timeline-msg__avatar')
    expect(avatar.classes()).not.toContain('timeline-msg__avatar--user')
    // agent avatar carries an inline tinted color style from getAgentColor()
    expect(avatar.attributes('style') || '').toContain('background-color')
  })
})

// ---------------------------------------------------------------------------
// Participant-directory author resolution (badge identity fix):
// the Hub resolves each message's author from the thread's participant list
// (participant_type + display_name), NOT from the from_agent_id UUID shape.
// This fixes agents that post under their own agent_id UUID (per the worker
// protocol) being mislabeled as USER posts (brand-yellow avatar + raw UUID name).
// ---------------------------------------------------------------------------

const RESOLVE_THREAD = 'thr-resolve'
const AGENT_UUID = '277e2ee9-e15d-4339-9730-4ffee559cdcb'

function seedResolveMessage(store) {
  store.selectedThreadId = RESOLVE_THREAD
  store.handleThreadMessage({
    thread_id: RESOLVE_THREAD, message_id: 'msg-uuid-agent', from_agent_id: AGENT_UUID,
    from_display_name: AGENT_UUID, content: 'orchestrating', message_type: 'broadcast',
    created_at: '2026-06-18T10:00:00Z',
  })
}

describe('ThreadTimeline participant-directory author resolution', () => {
  let pinia
  let store

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    store = useCommHubStore()
    seedResolveMessage(store)
  })

  it('resolves a UUID-authored AGENT post to its role name + color (not a user post)', () => {
    // The participant directory says this UUID is an AGENT named "orchestrator".
    store.participantsByThreadId = new Map([
      [RESOLVE_THREAD, [{ participant_id: AGENT_UUID, participant_type: 'agent', display_name: 'orchestrator' }]],
    ])
    const wrapper = mountTimeline(pinia)
    const row = wrapper.find('[data-testid="timeline-message-msg-uuid-agent"]')
    // NOT rendered as a user post despite the UUID from_agent_id
    expect(row.classes()).toContain('timeline-msg--agent')
    expect(row.classes()).not.toContain('timeline-msg--user')
    const avatar = row.find('.timeline-msg__avatar')
    expect(avatar.classes()).not.toContain('timeline-msg__avatar--user')
    // friendly role name, not the raw UUID
    expect(row.find('.timeline-msg__sender').text()).toBe('orchestrator')
    // tinted agent color applied (from getAgentColor), not the brand-yellow user treatment
    expect(avatar.attributes('style') || '').toContain('background-color')
  })

  it('resolves a participant of type "user" to the user treatment', () => {
    store.participantsByThreadId = new Map([
      [RESOLVE_THREAD, [{ participant_id: AGENT_UUID, participant_type: 'user', display_name: 'Patrik' }]],
    ])
    const wrapper = mountTimeline(pinia)
    const row = wrapper.find('[data-testid="timeline-message-msg-uuid-agent"]')
    expect(row.classes()).toContain('timeline-msg--user')
    expect(row.find('.timeline-msg__sender').text()).toBe('Patrik')
  })

  it('falls back to prior behavior when the author is not in the participant list', () => {
    // No participants loaded — a UUID from_agent_id falls back to the user heuristic.
    const wrapper = mountTimeline(pinia)
    const row = wrapper.find('[data-testid="timeline-message-msg-uuid-agent"]')
    expect(row.classes()).toContain('timeline-msg--user')
  })
})

// ---------------------------------------------------------------------------
// FE-9012c (D3): the retired MessageAuditModal's 3-bucket audit becomes an
// in-thread filter, backed by the D4 recipient junctions.
//   Waiting = action-required post with recipients still pending
//   Read    = every recipient has acted (acked or completed; none pending)
//   Sent    = authored by the user (a UUID from_agent_id)
// MESSAGE-relative (what agents did with each post), never the viewer's inbox.
// ---------------------------------------------------------------------------

const FILTER_THREAD = 'thr-filter'

function seedFilterMessages(store) {
  store.handleThreadMessage({
    thread_id: FILTER_THREAD, message_id: 'waiting-1', content: 'act please', from_agent_id: 'orchestrator',
    requires_action: true, recipients: ['beta'], acked_by: [], completed_by: [], pending_for: ['beta'],
  })
  store.handleThreadMessage({
    thread_id: FILTER_THREAD, message_id: 'read-1', content: 'done', from_agent_id: 'orchestrator',
    requires_action: true, recipients: ['beta'], acked_by: ['beta'], completed_by: [], pending_for: [],
  })
  store.handleThreadMessage({
    thread_id: FILTER_THREAD, message_id: 'sent-1', content: 'from me', from_agent_id: USER_UUID,
    recipients: [], acked_by: [], completed_by: [], pending_for: [],
  })
}

describe('ThreadTimeline waiting/read/sent filter (FE-9012c)', () => {
  let pinia
  let store

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    store = useCommHubStore()
    store.selectedThreadId = FILTER_THREAD
    seedFilterMessages(store)
  })

  it('shows per-bucket counts on the filter pills', () => {
    const wrapper = mountTimeline(pinia)
    expect(wrapper.get('[data-testid="thread-filter-all"]').text()).toContain('All (3)')
    expect(wrapper.get('[data-testid="thread-filter-waiting"]').text()).toContain('Waiting (1)')
    expect(wrapper.get('[data-testid="thread-filter-read"]').text()).toContain('Read (1)')
    expect(wrapper.get('[data-testid="thread-filter-sent"]').text()).toContain('Sent (1)')
  })

  it('defaults to All — every message visible', () => {
    const wrapper = mountTimeline(pinia)
    expect(wrapper.findAll('[data-testid^="timeline-message-"]')).toHaveLength(3)
  })

  it('Waiting shows only action-required posts with pending recipients', async () => {
    const wrapper = mountTimeline(pinia)
    await wrapper.get('[data-testid="thread-filter-waiting"]').trigger('click')
    expect(wrapper.findAll('[data-testid^="timeline-message-"]')).toHaveLength(1)
    expect(wrapper.find('[data-testid="timeline-message-waiting-1"]').exists()).toBe(true)
  })

  it('Read shows only posts whose recipients have all acted', async () => {
    const wrapper = mountTimeline(pinia)
    await wrapper.get('[data-testid="thread-filter-read"]').trigger('click')
    expect(wrapper.findAll('[data-testid^="timeline-message-"]')).toHaveLength(1)
    expect(wrapper.find('[data-testid="timeline-message-read-1"]').exists()).toBe(true)
  })

  it('Sent shows only the user-authored post', async () => {
    const wrapper = mountTimeline(pinia)
    await wrapper.get('[data-testid="thread-filter-sent"]').trigger('click')
    expect(wrapper.findAll('[data-testid^="timeline-message-"]')).toHaveLength(1)
    expect(wrapper.find('[data-testid="timeline-message-sent-1"]').exists()).toBe(true)
  })

  it('an empty bucket shows the filter-empty notice', async () => {
    pinia = createPinia()
    setActivePinia(pinia)
    store = useCommHubStore()
    store.selectedThreadId = 'thr-empty'
    // Plain informational post: no pending recipients, not user-authored.
    store.handleThreadMessage({
      thread_id: 'thr-empty', message_id: 'plain', content: 'chatter', from_agent_id: 'implementer',
      recipients: ['beta'], acked_by: [], completed_by: [], pending_for: [],
    })
    const wrapper = mountTimeline(pinia)
    await wrapper.get('[data-testid="thread-filter-waiting"]').trigger('click')
    expect(wrapper.find('[data-testid="timeline-filter-empty"]').exists()).toBe(true)
  })
})

// ---------------------------------------------------------------------------
// Phase 5 / D1(a): an explicit `threadId` prop lets a read-only surface (the
// Project Review pane's "Project Comms" section) render a SPECIFIC thread
// without touching the store's global selectedThreadId; `readonly` hides the
// interactive filter pills. HubView.vue keeps passing no props (falls back to
// selectedThreadId + filter shown).
// ---------------------------------------------------------------------------

describe('ThreadTimeline explicit threadId + readonly (Phase 5 / D1(a))', () => {
  let pinia
  let store
  const EXPLICIT = 'thr-explicit'

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    store = useCommHubStore()
    // Point the store's selection at a DIFFERENT, empty thread to prove the
    // threadId prop wins over selectedThreadId.
    store.selectedThreadId = 'thr-other-empty'
    store.handleThreadMessage({
      thread_id: EXPLICIT, message_id: 'e1', content: 'hello', from_agent_id: 'implementer',
      created_at: '2026-06-18T10:00:00Z',
    })
    store.handleThreadMessage({
      thread_id: EXPLICIT, message_id: 'e2', content: 'world', from_agent_id: 'orchestrator',
      created_at: '2026-06-18T10:01:00Z',
    })
  })

  function mountExplicit(props) {
    return mount(ThreadTimeline, { props, global: { plugins: [pinia, vuetify] } })
  }

  it("renders the explicit thread's messages, ignoring selectedThreadId", () => {
    const wrapper = mountExplicit({ threadId: EXPLICIT, readonly: true })
    expect(wrapper.findAll('[data-testid^="timeline-message-"]')).toHaveLength(2)
    expect(wrapper.find('[data-testid="timeline-message-e1"]').exists()).toBe(true)
  })

  it('hides the interactive filter pills in readonly mode', () => {
    const wrapper = mountExplicit({ threadId: EXPLICIT, readonly: true })
    expect(wrapper.find('[data-testid="thread-filter"]').exists()).toBe(false)
  })

  it('still shows the filter pills when not readonly (backward-compat)', () => {
    const wrapper = mountExplicit({ threadId: EXPLICIT })
    expect(wrapper.find('[data-testid="thread-filter"]').exists()).toBe(true)
  })
})
