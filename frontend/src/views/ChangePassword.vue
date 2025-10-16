<template>
  <v-container fluid class="fill-height change-password-container">
    <v-row align="center" justify="center">
      <v-col cols="12" sm="8" md="5" lg="4">
        <v-card elevation="8" class="change-password-card">
          <!-- Logo/Header -->
          <v-card-title class="text-center pa-6">
            <div class="d-flex flex-column align-center w-100">
              <v-img
                :src="theme.global.current.value.dark ? '/Giljo_YW.svg' : '/Giljo_BY.svg'"
                alt="GiljoAI MCP"
                height="50"
                width="auto"
                max-width="200"
                class="mb-3"
              />
              <h1 class="text-h5 font-weight-bold">Change Default Password</h1>
              <p class="text-body-2 text-medium-emphasis mt-2">First-Time Security Setup</p>
            </div>
          </v-card-title>

          <v-divider />

          <v-card-text class="pa-6">
            <!-- Security Notice -->
            <AppAlert
              type="warning"
              variant="tonal"
              class="mb-4"
              icon="mdi-shield-alert"
            >
              <AppAlert-title>Security Notice</AppAlert-title>
              <div class="text-body-2">
                For security reasons, you must change the default password before proceeding.
                Your new password must meet minimum security requirements.
              </div>
            </AppAlert>

            <!-- Error Alert -->
            <AppAlert
              v-if="errorMessage"
              type="error"
              variant="tonal"
              class="mb-4"
              closable
              @click:close="errorMessage = ''"
            >
              {{ errorMessage }}
            </AppAlert>

            <!-- Change Password Form -->
            <v-form ref="passwordForm" @submit.prevent="handleSubmit">
              <!-- Username (read-only) -->
              <v-text-field
                v-model="username"
                label="Username"
                prepend-inner-icon="mdi-account"
                variant="outlined"
                readonly
                :disabled="loading"
                aria-label="Username (read-only)"
                class="mb-3"
              />

              <!-- Current Password -->
              <v-text-field
                v-model="currentPassword"
                label="Current Password"
                prepend-inner-icon="mdi-lock"
                :append-inner-icon="showCurrentPassword ? 'mdi-eye' : 'mdi-eye-off'"
                :type="showCurrentPassword ? 'text' : 'password'"
                variant="outlined"
                :rules="[rules.required]"
                :disabled="loading"
                autocomplete="current-password"
                aria-label="Current password"
                aria-required="true"
                hint="Default password: admin"
                persistent-hint
                class="mb-3"
                @click:append-inner="showCurrentPassword = !showCurrentPassword"
                @input="errorMessage = ''"
              />

              <!-- New Password -->
              <v-text-field
                v-model="newPassword"
                label="New Password"
                prepend-inner-icon="mdi-lock-reset"
                :append-inner-icon="showNewPassword ? 'mdi-eye' : 'mdi-eye-off'"
                :type="showNewPassword ? 'text' : 'password'"
                variant="outlined"
                :rules="passwordRules"
                :disabled="loading"
                autocomplete="new-password"
                aria-label="New password"
                aria-required="true"
                aria-describedby="password-strength password-requirements"
                class="mb-2"
                @click:append-inner="showNewPassword = !showNewPassword"
                @input="updatePasswordStrength"
              />

              <!-- Password Strength Meter -->
              <div class="mb-2">
                <v-progress-linear
                  v-model="passwordStrength"
                  :color="passwordStrengthColor"
                  height="6"
                  rounded
                />
              </div>
              <div
                id="password-strength"
                class="text-caption mb-1"
                :style="{ color: passwordStrengthColorValue }"
                aria-live="polite"
              >
                Password strength: {{ passwordStrengthLabel }}
              </div>

              <!-- Password Requirements -->
              <div id="password-requirements" class="text-caption text-medium-emphasis mb-4">
                <v-icon size="x-small" class="mr-1">mdi-information</v-icon>
                Requirements: 8+ characters, uppercase, lowercase, number, special character
              </div>

              <!-- Confirm Password -->
              <v-text-field
                v-model="confirmPassword"
                label="Confirm New Password"
                prepend-inner-icon="mdi-lock-check"
                :append-inner-icon="showConfirmPassword ? 'mdi-eye' : 'mdi-eye-off'"
                :type="showConfirmPassword ? 'text' : 'password'"
                variant="outlined"
                :rules="[rules.required, rules.passwordMatch]"
                :disabled="loading"
                autocomplete="new-password"
                aria-label="Confirm new password"
                aria-required="true"
                class="mb-4"
                @click:append-inner="showConfirmPassword = !showConfirmPassword"
                @input="errorMessage = ''"
                @keyup.enter="handleSubmit"
              />

              <!-- Submit Button -->
              <v-btn
                type="submit"
                color="primary"
                size="large"
                block
                :loading="loading"
                :disabled="!isFormValid || loading"
                class="mt-4"
              >
                <v-icon start v-if="!loading">mdi-shield-check</v-icon>
                {{ loading ? 'Changing Password...' : 'Change Password & Continue' }}
              </v-btn>
            </v-form>
          </v-card-text>

          <v-divider />

          <!-- Footer Info -->
          <v-card-text class="text-center pa-4">
            <p class="text-caption text-medium-emphasis">
              <v-icon size="small" class="mr-1">mdi-information</v-icon>
              This is a one-time security setup required on first access
            </p>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, computed } from 'vue'
import AppAlert from '@/components/ui/AppAlert.vue'
import { useRouter } from 'vue-router'
import { useTheme } from 'vuetify'
import api from '@/services/api'

// Composables
const router = useRouter()
const theme = useTheme()

// State
const username = ref('admin')
const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const loading = ref(false)
const errorMessage = ref('')
const passwordForm = ref(null)

// Password visibility toggles
const showCurrentPassword = ref(false)
const showNewPassword = ref(false)
const showConfirmPassword = ref(false)

// Password strength
const passwordStrength = ref(0)

// Password strength computed properties
const passwordStrengthColor = computed(() => {
  if (passwordStrength.value < 25) return 'error'
  if (passwordStrength.value < 50) return 'warning'
  if (passwordStrength.value < 75) return 'info'
  return 'success'
})

const passwordStrengthColorValue = computed(() => {
  const colors = {
    error: 'rgb(244, 67, 54)',
    warning: 'rgb(255, 152, 0)',
    info: 'rgb(33, 150, 243)',
    success: 'rgb(76, 175, 80)',
  }
  return colors[passwordStrengthColor.value]
})

const passwordStrengthLabel = computed(() => {
  if (passwordStrength.value === 0) return 'Not set'
  if (passwordStrength.value < 25) return 'Weak'
  if (passwordStrength.value < 50) return 'Fair'
  if (passwordStrength.value < 75) return 'Good'
  return 'Strong'
})

// Validation rules
const rules = {
  required: (v) => !!v || 'This field is required',
  minLength: (v) => (v && v.length >= 8) || 'Password must be at least 8 characters',
  hasUppercase: (v) => /[A-Z]/.test(v) || 'Password must contain at least 1 uppercase letter',
  hasLowercase: (v) => /[a-z]/.test(v) || 'Password must contain at least 1 lowercase letter',
  hasDigit: (v) => /\d/.test(v) || 'Password must contain at least 1 number',
  hasSpecialChar: (v) =>
    /[!@#$%^&*()_+\-=[\]{}|;:,.<>?]/.test(v) ||
    'Password must contain at least 1 special character',
  passwordMatch: (v) => v === newPassword.value || 'Passwords must match',
}

// Combined password rules for new password field
const passwordRules = computed(() => [
  rules.required,
  rules.minLength,
  rules.hasUppercase,
  rules.hasLowercase,
  rules.hasDigit,
  rules.hasSpecialChar,
])

// Form validation state
const isFormValid = computed(() => {
  if (!currentPassword.value || !newPassword.value || !confirmPassword.value) {
    return false
  }

  // Check all password rules pass
  const passwordValid = passwordRules.value.every(rule => rule(newPassword.value) === true)

  // Check passwords match
  const passwordsMatch = rules.passwordMatch(confirmPassword.value) === true

  return passwordValid && passwordsMatch
})

// Update password strength meter
function updatePasswordStrength() {
  if (!newPassword.value) {
    passwordStrength.value = 0
    return
  }

  let strength = 0

  // Length scoring
  if (newPassword.value.length >= 8) strength += 20
  if (newPassword.value.length >= 16) strength += 10
  if (newPassword.value.length >= 20) strength += 5

  // Character type scoring
  if (/[A-Z]/.test(newPassword.value)) strength += 20
  if (/[a-z]/.test(newPassword.value)) strength += 20
  if (/\d/.test(newPassword.value)) strength += 15
  if (/[!@#$%^&*()_+\-=[\]{}|;:,.<>?]/.test(newPassword.value)) strength += 15

  // Complexity bonus
  const hasMultipleUppercase = (newPassword.value.match(/[A-Z]/g) || []).length >= 2
  const hasMultipleDigits = (newPassword.value.match(/\d/g) || []).length >= 2
  const hasMultipleSpecial = (newPassword.value.match(/[!@#$%^&*()_+\-=[\]{}|;:,.<>?]/g) || []).length >= 2

  if (hasMultipleUppercase) strength += 5
  if (hasMultipleDigits) strength += 5
  if (hasMultipleSpecial) strength += 5

  passwordStrength.value = Math.min(strength, 100)
}

// Handle form submission
async function handleSubmit() {
  // Validate form
  const { valid } = await passwordForm.value.validate()
  if (!valid) {
    return
  }

  loading.value = true
  errorMessage.value = ''

  try {
    // POST to /api/auth/change-password
    const response = await api.auth.changePassword({
      current_password: currentPassword.value,
      new_password: newPassword.value,
      confirm_password: confirmPassword.value,
    })

    // SECURITY: Mark setup as completed to prevent setup screen on network errors
    localStorage.setItem('setup_completed', 'true')

    // Store JWT token if provided (backend returns "token" not "access_token")
    if (response.data?.token) {
      localStorage.setItem('auth_token', response.data.token)
    }

    // Store user data if provided
    if (response.data?.user) {
      localStorage.setItem('user', JSON.stringify(response.data.user))
    }

    console.log('[ChangePassword] Password changed successfully - setup marked complete')

    // Small delay to show success
    await new Promise((resolve) => setTimeout(resolve, 300))

    // Redirect to setup wizard (or dashboard if setup complete)
    router.push('/setup')
  } catch (err) {
    // Handle specific error types
    if (err.response?.status === 400) {
      // Validation error
      const detail = err.response?.data?.detail || 'Invalid password format'
      errorMessage.value = detail
    } else if (err.response?.status === 401) {
      errorMessage.value = 'Current password is incorrect'
    } else if (err.response?.status === 403) {
      errorMessage.value = 'Password change not allowed at this time'
    } else if (err.response?.data?.detail) {
      errorMessage.value = err.response.data.detail
    } else if (err.code === 'ERR_NETWORK' || !err.response) {
      errorMessage.value = 'Network error - please check your connection and try again'
    } else if (err.message) {
      errorMessage.value = `Password change failed: ${err.message}`
    } else {
      errorMessage.value = 'Password change failed. Please try again.'
    }

    // Clear password fields on error
    currentPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
    passwordStrength.value = 0
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.change-password-container {
  background: linear-gradient(135deg, rgb(30, 49, 71) 0%, rgb(18, 29, 42) 100%);
  min-height: 100vh;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 9999;
  overflow-y: auto;
}

.change-password-card {
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}

/* Dark theme adjustments */
:deep(.v-theme--dark) .change-password-container {
  background: linear-gradient(135deg, rgb(18, 29, 42) 0%, rgb(10, 15, 22) 100%);
}

/* Light theme adjustments */
:deep(.v-theme--light) .change-password-container {
  background: linear-gradient(135deg, rgb(240, 244, 248) 0%, rgb(220, 230, 240) 100%);
}

/* Accessibility: Focus indicators */
.v-text-field:focus-within {
  outline: 2px solid rgba(var(--v-theme-primary), 0.5);
  outline-offset: 2px;
  border-radius: 4px;
}

/* Screen reader only text */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}
</style>
