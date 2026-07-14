/**
 * Vitest spec — NB-2 fix: dismiss control wired in NotificationDropdown (IMP-5037a)
 *
 * Covers:
 *  - Dismiss button exists for each notification item
 *  - Clicking dismiss calls notificationStore.markDismissed(id)
 *  - Clicking dismiss does NOT trigger the row click (navigate/markRead) handler
 *  - After dismiss, the item is removed from the rendered list (store removes it)
 *
 * Notes on test setup:
 *  - v-list-item stub (setup.js) renders <div class="v-list-item"><slot /></div>
 *    (named slots like v-slot:append are NOT rendered by the stub).
 *    The dismiss button must therefore sit in the default slot — verified by data-test attr.
 *  - We use createTestingPinia with spy actions and control state directly.
 *  - vue-router is mocked to avoid router injection errors.
 *  - date-fns/formatDistanceToNow is mocked to avoid locale issues.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import { ref } from 'vue'
import NotificationDropdown from '@/components/navigation/NotificationDropdown.vue'

// ── Router mock ──────────────────────────────────────────────────────────────
vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
}))

// ── date-fns mock ────────────────────────────────────────────────────────────
vi.mock('date-fns', () => ({
  formatDistanceToNow: vi.fn(() => '2 hours ago'),
}))

// ── WebSocket store mock ─────────────────────────────────────────────────────
vi.mock('@/stores/websocket', () => ({
  useWebSocketStore: () => ({
    on: vi.fn(() => vi.fn()), // returns unsubscribe fn
  }),
}))

// ── User store mock ──────────────────────────────────────────────────────────
vi.mock('@/stores/user', () => ({
  useUserStore: () => ({
    currentUser: { id: 'user-1' },
  }),
}))

// ── Fixtures ─────────────────────────────────────────────────────────────────
const NOTIF_A = {
  id: 'notif-a',
  type: 'api_key.expiring_soon',
  severity: 'warning',
  title: 'Key A expiring',
  body: 'Your key expires soon',
  read: false,
  read_at: null,
  dismissed_at: null,
  created_at: '2026-06-03T00:00:00Z',
  timestamp: '2026-06-03T00:00:00Z',
}

const NOTIF_B = {
  id: 'notif-b',
  type: 'api_key.expiring_soon',
  severity: 'warning',
  title: 'Key B expiring',
  body: 'Another key expires soon',
  read: false,
  read_at: null,
  dismissed_at: null,
  created_at: '2026-06-02T00:00:00Z',
  timestamp: '2026-06-02T00:00:00Z',
}

// ── Helper ───────────────────────────────────────────────────────────────────
/**
 * Mount with testing pinia.
 * stubActions: true (default) replaces ALL actions with vi.fn() no-ops, which
 * prevents onMounted's fetch() from overwriting our initialState.
 * Individual tests spy on / implement specific actions as needed.
 */
function mountDropdown(initialNotifications = [NOTIF_A, NOTIF_B]) {
  return mount(NotificationDropdown, {
    global: {
      plugins: [
        createTestingPinia({
          createSpy: vi.fn,
          initialState: {
            notifications: {
              notifications: initialNotifications,
            },
          },
          // stubActions defaults to true — actions are vi.fn() stubs; fetch() is a no-op
        }),
      ],
    },
  })
}

// ── Tests ─────────────────────────────────────────────────────────────────────
describe('NotificationDropdown — NB-2: dismiss control (IMP-5037a)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // ---------------------------------------------------------------------------
  // 1. Dismiss button exists for each notification
  // ---------------------------------------------------------------------------
  it('renders a dismiss button for each notification item', () => {
    const wrapper = mountDropdown([NOTIF_A, NOTIF_B])
    const dismissBtns = wrapper.findAll('[data-test^="dismiss-btn-"]')
    expect(dismissBtns).toHaveLength(2)
    expect(wrapper.find('[data-test="dismiss-btn-notif-a"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="dismiss-btn-notif-b"]').exists()).toBe(true)
  })

  // ---------------------------------------------------------------------------
  // 2. Dismiss button has accessible label
  // ---------------------------------------------------------------------------
  it('dismiss button has an aria-label for accessibility', () => {
    const wrapper = mountDropdown([NOTIF_A])
    const btn = wrapper.find('[data-test="dismiss-btn-notif-a"]')
    expect(btn.attributes('aria-label')).toBeTruthy()
  })

  // ---------------------------------------------------------------------------
  // 3. Clicking dismiss calls store.markDismissed with the notification id
  // ---------------------------------------------------------------------------
  it('clicking dismiss calls notificationStore.markDismissed with the notification id', async () => {
    const wrapper = mountDropdown([NOTIF_A])
    const { useNotificationStore } = await import('@/stores/notifications')
    const store = useNotificationStore()

    // Stub markDismissed to resolve immediately without mutating store state
    store.markDismissed = vi.fn(() => Promise.resolve())

    const btn = wrapper.find('[data-test="dismiss-btn-notif-a"]')
    await btn.trigger('click')

    expect(store.markDismissed).toHaveBeenCalledOnce()
    expect(store.markDismissed).toHaveBeenCalledWith('notif-a')
  })

  // ---------------------------------------------------------------------------
  // 4. Clicking dismiss does NOT also trigger the row click handler
  // ---------------------------------------------------------------------------
  it('clicking dismiss does not trigger the row (navigate/markRead) click handler', async () => {
    const wrapper = mountDropdown([NOTIF_A])
    const { useNotificationStore } = await import('@/stores/notifications')
    const store = useNotificationStore()

    store.markDismissed = vi.fn(() => Promise.resolve())
    // markRead would be called by the row click handler if propagation were not stopped
    store.markRead = vi.fn(() => Promise.resolve())

    const btn = wrapper.find('[data-test="dismiss-btn-notif-a"]')
    await btn.trigger('click')

    // markRead must NOT be called — row click handler was not triggered
    expect(store.markRead).not.toHaveBeenCalled()
    // markDismissed must have been called exactly once
    expect(store.markDismissed).toHaveBeenCalledOnce()
  })

  // ---------------------------------------------------------------------------
  // 5. After dismissal the item is removed from the rendered list
  // ---------------------------------------------------------------------------
  it('dismissed notification is removed from the rendered list', async () => {
    const wrapper = mountDropdown([NOTIF_A, NOTIF_B])
    const { useNotificationStore } = await import('@/stores/notifications')
    const store = useNotificationStore()

    // Simulate real store removal on markDismissed
    store.markDismissed = vi.fn(async (id) => {
      store.notifications = store.notifications.filter((n) => n.id !== id)
    })

    expect(wrapper.findAll('[data-test^="dismiss-btn-"]')).toHaveLength(2)

    const btn = wrapper.find('[data-test="dismiss-btn-notif-a"]')
    await btn.trigger('click')
    await wrapper.vm.$nextTick()

    // notif-a gone, notif-b still present
    expect(wrapper.find('[data-test="dismiss-btn-notif-a"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="dismiss-btn-notif-b"]').exists()).toBe(true)
  })
})
