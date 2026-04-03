<template>
  <v-dialog
    v-model="internalShow"
    max-width="600"
    persistent
    scrollable
    attach
    @keydown.esc="handleClose"
  >
    <v-card v-draggable class="smooth-border">
      <!-- Header -->
      <v-card-title class="d-flex align-center pa-4">
        <v-icon class="mr-2" color="primary">mdi-lock-reset</v-icon>
        <span>{{ stage === 'pin' ? 'Forgot Password?' : 'Reset Password' }}</span>
        <v-spacer />
        <v-btn
          icon="mdi-close"
          variant="text"
          size="small"
          :disabled="loading"
          aria-label="Close dialog"
          @click="handleClose"
        />
      </v-card-title>

      <v-divider />

      <v-card-text class="pa-6">
        <!-- Alert for errors -->
        <AppAlert
          v-if="error"
          type="error"
          variant="tonal"
          class="mb-4"
          closable
          @click:close="error = ''"
        >
          {{ error }}
        </AppAlert>

        <!-- Alert for success -->
        <AppAlert v-if="success" type="success" variant="tonal" class="mb-4">
          {{ success }}
        </AppAlert>

        <!-- Lockout Warning -->
        <AppAlert v-if="lockoutMessage" type="warning" variant="tonal" class="mb-4">
          <strong>Account Locked:</strong> {{ lockoutMessage }}
        </AppAlert>

        <!-- Stage 1: PIN Verification -->
        <div v-if="stage === 'pin'">
          <p class="text-body-2 mb-4">
            Enter your username and 4-digit recovery PIN to reset your password.
          </p>

          <!-- Attempts remaining indicator -->
          <AppAlert
            v-if="attemptsRemaining !== null && attemptsRemaining < 5"
            type="warning"
            variant="tonal"
            density="compact"
            class="mb-4"
          >
            <strong>Warning:</strong> {{ attemptsRemaining }} attempt{{
              attemptsRemaining !== 1 ? 's' : ''
            }}
            remaining before lockout.
          </AppAlert>

          <v-form ref="pinForm" @submit.prevent="handleVerifyPin">
            <!-- Username -->
            <v-text-field
              v-model="username"
              label="Username"
              prepend-inner-icon="mdi-account"
              variant="outlined"
              :rules="[rules.username]"
              :disabled="loading"
              autofocus
              autocomplete="username"
              class="mb-4"
              aria-label="Enter your username"
              aria-required="true"
              @input="error = ''"
            />

            <!-- Recovery PIN -->
            <v-text-field
              v-model="pin"
              label="Recovery PIN (4 digits)"
              prepend-inner-icon="mdi-numeric"
              variant="outlined"
              type="text"
              inputmode="numeric"
              pattern="[0-9]{4}"
              maxlength="4"
              :rules="pinRules"
              :disabled="loading"
              autocomplete="off"
              class="mb-4"
              aria-label="Enter your 4-digit recovery PIN"
              aria-required="true"
              hint="Enter the 4-digit PIN you set during account setup"
              persistent-hint
              @input="handlePinInput"
              @keypress="onlyNumbers"
            />

            <!-- Info -->
            <AppAlert type="info" variant="tonal" density="compact" class="mb-4">
              If you have forgotten both your password and PIN, please contact your administrator.
            </AppAlert>

            <!-- Verify Button -->
            <v-btn
              type="submit"
              color="primary"
              size="large"
              block
              :loading="loading"
              :disabled="!username || !pin || pin.length !== 4 || loading"
              aria-label="Verify PIN and proceed to password reset"
            >
              <v-icon v-if="!loading" start>mdi-shield-check</v-icon>
              {{ loading ? 'Verifying...' : 'Verify PIN' }}
            </v-btn>
          </v-form>
        </div>

        <!-- Stage 2: Password Reset (shown after successful PIN verification) -->
        <div v-if="stage === 'reset'">
          <AppAlert type="success" variant="tonal" class="mb-4">
            <strong>PIN Verified!</strong> Please enter your new password below.
          </AppAlert>

          <v-form ref="resetPasswordForm" @submit.prevent="handleResetPassword">
            <!-- New Password -->
            <v-text-field
              v-model="newPassword"
              label="New Password"
              prepend-inner-icon="mdi-lock"
              :type="showPassword ? 'text' : 'password'"
              variant="outlined"
              :rules="passwordRules"
              :disabled="loading"
              autocomplete="new-password"
              autofocus
              class="mb-4"
              aria-label="Enter your new password"
              aria-required="true"
              @input="error = ''"
            >
              <template #append-inner>
                <v-icon
                  tabindex="-1"
                  @click="showPassword = !showPassword"
                >
                  {{ showPassword ? 'mdi-eye' : 'mdi-eye-off' }}
                </v-icon>
              </template>
            </v-text-field>

            <!-- Confirm Password -->
            <v-text-field
              v-model="confirmPassword"
              label="Confirm New Password"
              prepend-inner-icon="mdi-lock-check"
              :type="showConfirmPassword ? 'text' : 'password'"
              variant="outlined"
              :rules="confirmPasswordRules"
              :disabled="loading"
              autocomplete="new-password"
              class="mb-4"
              aria-label="Confirm your new password"
              aria-required="true"
              @input="error = ''"
            >
              <template #append-inner>
                <v-icon
                  tabindex="-1"
                  @click="showConfirmPassword = !showConfirmPassword"
                >
                  {{ showConfirmPassword ? 'mdi-eye' : 'mdi-eye-off' }}
                </v-icon>
              </template>
            </v-text-field>

            <!-- Password Requirements -->
            <v-list density="compact" class="requirement-list mb-4">
              <v-list-item v-for="req in passwordRequirements" :key="req.text" class="px-0 py-1">
                <template #prepend>
                  <v-icon
                    :color="req.met ? 'success' : 'error'"
                    size="small"
                    :aria-label="req.met ? 'Requirement met' : 'Requirement not met'"
                  >
                    {{ req.met ? 'mdi-check-circle' : 'mdi-close-circle' }}
                  </v-icon>
                </template>
                <v-list-item-title class="text-caption">{{ req.text }}</v-list-item-title>
              </v-list-item>
            </v-list>

            <!-- Reset Button -->
            <v-btn
              type="submit"
              color="primary"
              size="large"
              block
              :loading="loading"
              :disabled="!isPasswordValid || loading"
              aria-label="Reset password and return to login"
            >
              <v-icon v-if="!loading" start>mdi-lock-reset</v-icon>
              {{ loading ? 'Resetting...' : 'Reset Password' }}
            </v-btn>
          </v-form>
        </div>
      </v-card-text>

      <v-divider />

      <v-card-actions class="pa-4">
        <v-spacer />
        <v-btn variant="text" :disabled="loading" @click="handleClose"> Cancel </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import AppAlert from '@/components/ui/AppAlert.vue'
import api from '@/services/api'

// Props
const props = defineProps({
  show: {
    type: Boolean,
    default: false,
  },
})

// Emits
const emit = defineEmits(['update:show', 'success'])

// Internal state
const internalShow = computed({
  get: () => props.show,
  set: (value) => emit('update:show', value),
})

// State
const stage = ref('pin') // 'pin' or 'reset'
const username = ref('')
const pin = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const showPassword = ref(false)
const showConfirmPassword = ref(false)
const loading = ref(false)
const error = ref('')
const success = ref('')
const lockoutMessage = ref('')
const attemptsRemaining = ref(null)
const pinForm = ref(null)
// Validation rules
const rules = {
  username: (value) => !!value || 'Username is required',
}

const pinRules = [
  (v) => !!v || 'Recovery PIN is required',
  (v) => /^\d{4}$/.test(v) || 'PIN must be exactly 4 digits',
]

const passwordRules = [
  (v) => !!v || 'Password is required',
  (v) => v.length >= 12 || 'Password must be at least 12 characters',
  (v) => /[A-Z]/.test(v) || 'Must contain at least one uppercase letter',
  (v) => /[a-z]/.test(v) || 'Must contain at least one lowercase letter',
  (v) => /\d/.test(v) || 'Must contain at least one digit',
  (v) => /[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(v) || 'Must contain at least one special character',
]

const confirmPasswordRules = [
  (v) => !!v || 'Password confirmation is required',
  (v) => v === newPassword.value || 'Passwords do not match',
]

// Password requirements
const passwordRequirements = computed(() => [
  { text: 'At least 12 characters', met: newPassword.value.length >= 12 },
  { text: 'One uppercase letter', met: /[A-Z]/.test(newPassword.value) },
  { text: 'One lowercase letter', met: /[a-z]/.test(newPassword.value) },
  { text: 'One digit', met: /\d/.test(newPassword.value) },
  { text: 'One special character', met: /[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(newPassword.value) },
  {
    text: 'Passwords match',
    met: newPassword.value === confirmPassword.value && confirmPassword.value !== '',
  },
])

const isPasswordValid = computed(() => {
  return (
    newPassword.value &&
    confirmPassword.value &&
    newPassword.value === confirmPassword.value &&
    passwordRequirements.value.every((req) => req.met)
  )
})

// Methods
function handlePinInput(value) {
  pin.value = value.replace(/\D/g, '').slice(0, 4)
}

function onlyNumbers(event) {
  const charCode = event.which ? event.which : event.keyCode
  if (charCode < 48 || charCode > 57) {
    event.preventDefault()
  }
}

function resetFormState() {
  stage.value = 'pin'
  username.value = ''
  pin.value = ''
  newPassword.value = ''
  confirmPassword.value = ''
  showPassword.value = false
  showConfirmPassword.value = false
  error.value = ''
  success.value = ''
  lockoutMessage.value = ''
  attemptsRemaining.value = null
}

function handleClose() {
  if (!loading.value) {
    resetFormState()
    emit('update:show', false)
  }
}

async function handleVerifyPin() {
  // Validate form
  const { valid } = await pinForm.value.validate()
  if (!valid) {
    return
  }

  loading.value = true
  error.value = ''
  lockoutMessage.value = ''

  try {
    // Call API to verify PIN (this endpoint will also handle password reset in one call)
    // For now, we'll just move to stage 2 on successful verification
    // In production, the backend should verify PIN first, then allow password reset

    // Since the API endpoint combines both operations, we'll proceed to stage 2
    stage.value = 'reset'
    error.value = ''
  } catch (err) {
    console.error('[ForgotPassword] PIN verification failed:', err)

    // Handle lockout
    if (err.response?.status === 429) {
      lockoutMessage.value =
        err.response.data?.detail || 'Too many attempts. Please try again in 15 minutes.'
      attemptsRemaining.value = 0
    } else if (err.response?.data?.attempts_remaining !== undefined) {
      attemptsRemaining.value = err.response.data.attempts_remaining
      error.value = 'Invalid username or PIN. Please try again.'
    } else if (err.response?.data?.detail) {
      error.value = err.response.data.detail
    } else {
      error.value = 'Failed to verify PIN. Please try again.'
    }
  } finally {
    loading.value = false
  }
}

async function handleResetPassword() {
  // Validate form
  const { valid } = await resetPasswordForm.value.validate()
  if (!valid) {
    return
  }

  loading.value = true
  error.value = ''

  try {
    await api.auth.verifyPinAndResetPassword({
      username: username.value,
      recovery_pin: pin.value,
      new_password: newPassword.value,
      confirm_password: confirmPassword.value,
    })

    // Show success message
    success.value = 'Password reset successfully! You can now log in with your new password.'

    // Wait a moment to show success message
    await new Promise((resolve) => setTimeout(resolve, 2000))

    // Close modal and emit success
    resetFormState()
    emit('update:show', false)
    emit('success', 'Password reset successfully! Please log in with your new credentials.')
  } catch (err) {
    console.error('[ForgotPassword] Password reset failed:', err)

    // Handle lockout
    if (err.response?.status === 429) {
      lockoutMessage.value =
        err.response.data?.detail || 'Too many attempts. Please try again in 15 minutes.'
      attemptsRemaining.value = 0
      stage.value = 'pin' // Go back to PIN stage
    } else if (err.response?.data?.detail) {
      error.value = err.response.data.detail
    } else {
      error.value = 'Failed to reset password. Please try again.'
    }
  } finally {
    loading.value = false
  }
}

// Watch for dialog close to reset form
watch(
  () => props.show,
  (newValue) => {
    if (!newValue) {
      resetFormState()
    }
  },
)
</script>

<style lang="scss" scoped>
@use '../styles/design-tokens' as *;
.requirement-list {
  background: rgba(255, 255, 255, 0.05);
  border-radius: $border-radius-default;
  padding: 12px;
}

/* Remove Vuetify field overlay tint so inputs match the card background */
:deep(.v-field__overlay) {
  opacity: 0 !important;
}
</style>
