/**
 * useHubPresence.spec.js — FE-6054f
 * Verifies presence detection: Hub pane focused + visible + /hub route.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { reactive, nextTick } from 'vue'

// Mock vue-router — use reactive so computed watchers pick up path changes
const mockRoute = reactive({ path: '/hub' })
vi.mock('vue-router', () => ({
  useRoute: () => mockRoute,
}))

describe('useHubPresence', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.resetModules()
    // Default: visible, focused, /hub
    Object.defineProperty(document, 'visibilityState', {
      writable: true,
      configurable: true,
      value: 'visible',
    })
    Object.defineProperty(document, 'hasFocus', {
      writable: true,
      configurable: true,
      value: () => true,
    })
    mockRoute.path = '/hub'
  })

  it('isHubPresent is true when visible, focused, and on /hub', async () => {
    const { useHubPresence } = await import('./useHubPresence')
    const { isHubPresent } = useHubPresence()
    expect(isHubPresent.value).toBe(true)
  })

  it('isHubPresent is false when route is NOT /hub', async () => {
    mockRoute.path = '/projects'
    const { useHubPresence } = await import('./useHubPresence')
    const { isHubPresent } = useHubPresence()
    expect(isHubPresent.value).toBe(false)
  })

  it('isHubPresent is false when document is hidden', async () => {
    Object.defineProperty(document, 'visibilityState', { value: 'hidden', configurable: true })
    const { useHubPresence } = await import('./useHubPresence')
    const { isHubPresent } = useHubPresence()
    expect(isHubPresent.value).toBe(false)
  })

  it('isHubPresent is false when document does not have focus', async () => {
    Object.defineProperty(document, 'hasFocus', {
      value: () => false,
      configurable: true,
      writable: true,
    })
    const { useHubPresence } = await import('./useHubPresence')
    const { isHubPresent } = useHubPresence()
    expect(isHubPresent.value).toBe(false)
  })

  it('isHubPresent updates when route changes away from /hub', async () => {
    const { useHubPresence } = await import('./useHubPresence')
    const { isHubPresent } = useHubPresence()
    expect(isHubPresent.value).toBe(true)
    mockRoute.path = '/dashboard'
    await nextTick()
    expect(isHubPresent.value).toBe(false)
  })
})
