import { computed } from 'vue'
import { useUserStore } from '@/stores/user'

/**
 * Derives the user's first name and selects a randomized, time-sensitive
 * greeting message. Zero side effects — no store writes.
 *
 * @param {object} [options]
 * @param {import('vue').Ref} [options.currentUser] - Override the currentUser ref (useful for testing)
 * @returns {{ firstName: ComputedRef<string>, fullGreeting: ComputedRef<string> }}
 */
export function useGreeting(options = {}) {
  const userStore = options.currentUser === undefined ? useUserStore() : null

  const currentUser = options.currentUser !== undefined
    ? options.currentUser
    : computed(() => userStore.currentUser)

  const firstName = computed(() => {
    const name = currentUser.value?.full_name || currentUser.value?.username || 'Friend'
    return String(name).split(' ')[0]
  })

  const fullGreeting = computed(() => {
    const name = firstName.value
    const hour = new Date().getHours()

    const withComma = {
      morning: [
        'Good morning, {name}!',
        'Morning, {name}!',
        'Rise and shine, {name}!',
        'Top of the morning, {name}!',
        'Wakey wakey, {name}!',
      ],
      afternoon: [
        'Good afternoon, {name}!',
        'Hello there, {name}!',
        'Hey there, {name}!',
        'Howdy, {name}!',
        'Greetings, {name}!',
      ],
      evening: [
        'Good evening, {name}!',
        'Evening, {name}!',
        'Hey there, {name}!',
        'Salutations, {name}!',
      ],
      general: [
        'Welcome back, {name}!',
        'Hey, {name}!',
        'Howdy, {name}!',
        'Ahoy, {name}!',
        'Yo, {name}!',
        'Greetings, {name}!',
      ],
    }

    const withoutComma = {
      morning: [
        'Ready to conquer the day {name}?',
        'Time to shine {name}!',
        'Another beautiful morning awaits {name}!',
      ],
      afternoon: [
        'Great to see you {name}!',
        'Nice to have you back {name}!',
        'Good to see you {name}!',
      ],
      evening: [
        'Great to see you {name}!',
        'Nice to see you {name}!',
        'Glad you stopped by {name}!',
      ],
      general: [
        'Great to see you {name}!',
        'Good to have you back {name}!',
        'Look who showed up... {name}!',
        'There you are {name}!',
      ],
    }

    const funCasual = [
      "Let's get crackalackin' {name}!",
      "Let's do this {name}!",
      "Ready to rock {name}?",
      "Let's roll {name}!",
      "Game on {name}!",
      "Let's crush it {name}!",
      "Time to make magic {name}!",
      "Adventure awaits {name}!",
      "Buckle up {name}!",
      "Let's build something awesome {name}!",
      "Ready to rumble {name}?",
      "Let's make it happen {name}!",
      "Fire it up {name}!",
      "Here we go {name}!",
      "Showtime {name}!",
    ]

    function choose(arr) {
      return arr[Math.floor(Math.random() * arr.length)]
    }

    const timeKey = hour < 12 ? 'morning' : hour < 17 ? 'afternoon' : hour < 22 ? 'evening' : 'general'

    const pool = [
      ...withComma[timeKey],
      ...withComma[timeKey],
      ...withoutComma[timeKey],
      ...funCasual,
    ]

    const msg = choose(pool)
    return msg.replace('{name}', name)
  })

  return { firstName, fullGreeting }
}
