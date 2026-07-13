/**
 * useWelcomeGreeting.js — FE-6006 unit 3a
 *
 * Extracted from WelcomeView.vue: time-of-day personalised greeting generator.
 * Pure computed — no side-effects, no API calls.
 * Edition scope: CE
 */
import { computed } from 'vue'

/**
 * @param {Object} options
 * @param {import('vue').Ref<string>} options.firstName - reactive first name of current user
 * @returns {{ fullGreeting: import('vue').ComputedRef<string> }}
 */
export function useWelcomeGreeting({ firstName }) {
  const fullGreeting = computed(() => {
    const name = firstName.value
    const hour = new Date().getHours()

    // WITH COMMA - Direct address greetings (vocative case)
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

    // WITHOUT COMMA - Name flows naturally into phrase
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

    // FUN CASUAL - Energetic oddball greetings
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

    // Determine time-based category
    const timeKey = hour < 12 ? 'morning' : hour < 17 ? 'afternoon' : hour < 22 ? 'evening' : 'general'

    // Build pool: 40% with comma, 30% without comma, 30% fun casual
    const pool = [
      ...withComma[timeKey],
      ...withComma[timeKey], // Double weight for time-appropriate
      ...withoutComma[timeKey],
      ...funCasual,
    ]

    const msg = choose(pool)
    return msg.replace('{name}', name)
  })

  return { fullGreeting }
}
