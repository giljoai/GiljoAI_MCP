import { computed, ref } from 'vue'

// Matches the special-character requirement below (kept in sync manually —
// it's a plain char class, not worth a shared regex constant across the two
// use sites).
const SPECIAL_CHAR_PATTERN = /[!@#$%^&*()_+\-=[\]{}|;:,.<>?]/

/**
 * Password complexity rules shared by ForgotPasswordPin.vue, FirstLogin.vue
 * (dup-11), and CreateAdminAccount.vue (FE-9151).
 */
export const PASSWORD_RULES = [
  (v) => !!v || 'Password is required',
  (v) => v.length >= 8 || 'Password must be at least 8 characters',
  (v) => /[A-Z]/.test(v) || 'Must contain at least one uppercase letter',
  (v) => /[a-z]/.test(v) || 'Must contain at least one lowercase letter',
  (v) => /\d/.test(v) || 'Must contain at least one digit',
  (v) => SPECIAL_CHAR_PATTERN.test(v) || 'Must contain at least one special character',
]

/** 4-digit recovery PIN validation, shared by the same two views. */
export const PIN_RULES = [
  (v) => !!v || 'Recovery PIN is required',
  (v) => /^\d{4}$/.test(v) || 'PIN must be exactly 4 digits',
]

/** Restrict a keypress event to digits 0-9 (PIN inputs). */
export function onlyNumbers(event) {
  const charCode = event.which ? event.which : event.keyCode
  if (charCode < 48 || charCode > 57) {
    event.preventDefault()
  }
}

/**
 * usePasswordForm — shared new/confirm password state, validation, and the
 * live requirements checklist for ForgotPasswordPin.vue and FirstLogin.vue
 * (dup-11).
 */
export function usePasswordForm() {
  const newPassword = ref('')
  const confirmPassword = ref('')
  const showNewPassword = ref(false)
  const showConfirmPassword = ref(false)

  const confirmPasswordRules = [
    (v) => !!v || 'Password confirmation is required',
    (v) => v === newPassword.value || 'Passwords do not match',
  ]

  const passwordRequirements = computed(() => [
    { text: 'At least 8 characters', met: newPassword.value.length >= 8 },
    { text: 'One uppercase letter', met: /[A-Z]/.test(newPassword.value) },
    { text: 'One lowercase letter', met: /[a-z]/.test(newPassword.value) },
    { text: 'One digit', met: /\d/.test(newPassword.value) },
    {
      text: 'One special character',
      met: SPECIAL_CHAR_PATTERN.test(newPassword.value),
    },
    {
      text: 'Passwords match',
      met: newPassword.value === confirmPassword.value && confirmPassword.value !== '',
    },
  ])

  return {
    newPassword,
    confirmPassword,
    showNewPassword,
    showConfirmPassword,
    passwordRules: PASSWORD_RULES,
    confirmPasswordRules,
    passwordRequirements,
  }
}
