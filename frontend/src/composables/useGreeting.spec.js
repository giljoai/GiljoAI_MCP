import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { ref } from 'vue'
import { setActivePinia, createPinia } from 'pinia'
import { useGreeting } from './useGreeting'

vi.mock('@/stores/user', () => ({
  useUserStore: () => ({
    currentUser: null,
  }),
}))

describe('useGreeting', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  describe('firstName', () => {
    it('returns first word of full_name when available', () => {
      const { firstName } = useGreeting({ currentUser: ref({ full_name: 'Alice Wonderland', username: 'alice' }) })
      expect(firstName.value).toBe('Alice')
    })

    it('returns username when full_name is not set', () => {
      const { firstName } = useGreeting({ currentUser: ref({ full_name: null, username: 'alice' }) })
      expect(firstName.value).toBe('alice')
    })

    it('returns "Friend" when both full_name and username are absent', () => {
      const { firstName } = useGreeting({ currentUser: ref({}) })
      expect(firstName.value).toBe('Friend')
    })

    it('returns "Friend" when currentUser is null', () => {
      const { firstName } = useGreeting({ currentUser: ref(null) })
      expect(firstName.value).toBe('Friend')
    })

    it('handles single-word full name', () => {
      const { firstName } = useGreeting({ currentUser: ref({ full_name: 'Mononym' }) })
      expect(firstName.value).toBe('Mononym')
    })
  })

  describe('fullGreeting', () => {
    it('contains the first name somewhere in the greeting', () => {
      const { fullGreeting } = useGreeting({ currentUser: ref({ full_name: 'Bob Smith' }) })
      expect(fullGreeting.value).toContain('Bob')
    })

    it('returns a non-empty string', () => {
      const { fullGreeting } = useGreeting({ currentUser: ref({ username: 'charlie' }) })
      expect(fullGreeting.value.length).toBeGreaterThan(0)
    })

    it('ends with "!" or "?"', () => {
      const { fullGreeting } = useGreeting({ currentUser: ref({ full_name: 'Dana' }) })
      expect(fullGreeting.value).toMatch(/[!?]$/)
    })

    it('uses morning greetings in the morning (hour 7)', () => {
      vi.useFakeTimers()
      vi.setSystemTime(new Date('2026-01-01T07:00:00'))
      const results = new Set()
      for (let i = 0; i < 50; i++) {
        const { fullGreeting } = useGreeting({ currentUser: ref({ full_name: 'Eve' }) })
        results.add(fullGreeting.value)
      }
      const morningPhrases = ['morning', 'Morning', 'Rise', 'Top of', 'Wakey']
      const hasMorning = [...results].some(g => morningPhrases.some(p => g.includes(p)))
      expect(hasMorning).toBe(true)
    })

    it('uses evening greetings in the evening (hour 20)', () => {
      vi.useFakeTimers()
      vi.setSystemTime(new Date('2026-01-01T20:00:00'))
      const results = new Set()
      for (let i = 0; i < 50; i++) {
        const { fullGreeting } = useGreeting({ currentUser: ref({ full_name: 'Frank' }) })
        results.add(fullGreeting.value)
      }
      const eveningPhrases = ['evening', 'Evening', 'Salutations', 'Glad you stopped']
      const hasEvening = [...results].some(g => eveningPhrases.some(p => g.includes(p)))
      expect(hasEvening).toBe(true)
    })

    it('uses general (late night) greetings after hour 22', () => {
      vi.useFakeTimers()
      vi.setSystemTime(new Date('2026-01-01T23:00:00'))
      const results = new Set()
      for (let i = 0; i < 50; i++) {
        const { fullGreeting } = useGreeting({ currentUser: ref({ full_name: 'Grace' }) })
        results.add(fullGreeting.value)
      }
      const generalPhrases = ['Welcome back', 'Hey,', 'Howdy,', 'Ahoy', 'Greetings,', 'Great to see you', 'Good to have you back', 'Look who showed up', 'There you are']
      const hasGeneral = [...results].some(g => generalPhrases.some(p => g.includes(p)))
      expect(hasGeneral).toBe(true)
    })

    it('uses fun casual greetings occasionally', () => {
      vi.useFakeTimers()
      vi.setSystemTime(new Date('2026-01-01T10:00:00'))
      const results = new Set()
      for (let i = 0; i < 100; i++) {
        const { fullGreeting } = useGreeting({ currentUser: ref({ full_name: 'Hank' }) })
        results.add(fullGreeting.value)
      }
      const funPhrases = ["crackalackin'", "Let's do this", "Ready to rock", "Game on", "Let's crush it"]
      const hasFun = [...results].some(g => funPhrases.some(p => g.includes(p)))
      expect(hasFun).toBe(true)
    })

    it('replaces {name} placeholder fully (no leftover placeholder)', () => {
      for (let i = 0; i < 20; i++) {
        const { fullGreeting } = useGreeting({ currentUser: ref({ full_name: 'Iris' }) })
        expect(fullGreeting.value).not.toContain('{name}')
      }
    })

    it('works without a userStore argument (uses internal store)', () => {
      const { firstName, fullGreeting } = useGreeting()
      expect(typeof firstName.value).toBe('string')
      expect(typeof fullGreeting.value).toBe('string')
    })
  })
})
