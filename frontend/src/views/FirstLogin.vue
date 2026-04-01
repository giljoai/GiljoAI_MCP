<template>
  <v-container fluid class="fill-height first-login-container">
    <v-row align="center" justify="center">
      <v-col cols="12" sm="10" md="8" lg="6">
        <v-card elevation="8" class="first-login-card smooth-border">
          <!-- Header -->
          <v-card-title class="text-center pa-6">
            <div class="d-flex flex-column align-center w-100">
              <v-img
                src="/Giljo_YW.svg"
                alt="GiljoAI MCP"
                height="50"
                width="auto"
                max-width="200"
                class="mb-3"
              />
              <h1 class="text-h5 font-weight-bold">Complete Account Setup</h1>
              <p class="text-body-2 text-muted-a11y mt-2">
                Set your new password and recovery PIN
              </p>
            </div>
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

            <!-- Info Alert -->
            <AppAlert type="info" variant="tonal" class="mb-4">
              <strong>Security Setup Required:</strong> Please create a new password and 4-digit
              recovery PIN. Your recovery PIN can be used to reset your password if you forget it.
            </AppAlert>

            <!-- Form -->
            <v-form ref="firstLoginForm" @submit.prevent="handleSubmit">
              <!-- Current Password -->
              <v-text-field
                v-model="currentPassword"
                label="Current Password"
                prepend-inner-icon="mdi-lock-outline"
                :type="showCurrentPassword ? 'text' : 'password'"
                variant="outlined"
                :rules="[(v) => !!v || 'Current password is required']"
                :disabled="loading"
                autocomplete="current-password"
                class="mb-4"
                aria-label="Enter your current password"
                aria-required="true"
                hint="Enter the temporary password you used to log in"
                persistent-hint
                @input="error = ''"
              >
                <template #append-inner>
                  <v-icon
                    tabindex="-1"
                    @click="showCurrentPassword = !showCurrentPassword"
                  >
                    {{ showCurrentPassword ? 'mdi-eye' : 'mdi-eye-off' }}
                  </v-icon>
                </template>
              </v-text-field>

              <!-- New Password -->
              <v-text-field
                v-model="newPassword"
                label="New Password"
                prepend-inner-icon="mdi-lock"
                :type="showNewPassword ? 'text' : 'password'"
                variant="outlined"
                :rules="passwordRules"
                :disabled="loading"
                autocomplete="new-password"
                class="mb-4"
                aria-label="Enter your new password"
                aria-required="true"
                @input="error = ''"
              >
                <template #append-inner>
                  <v-icon
                    tabindex="-1"
                    @click="showNewPassword = !showNewPassword"
                  >
                    {{ showNewPassword ? 'mdi-eye' : 'mdi-eye-off' }}
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

              <!-- Password Strength Indicator -->
              <v-progress-linear
                :model-value="passwordStrength"
                :color="passwordStrengthColor"
                height="8"
                rounded
                class="mb-2"
                aria-label="Password strength indicator"
              />
              <p class="text-caption mb-4" :class="passwordStrengthColor + '--text'">
                Password Strength: {{ passwordStrengthText }}
              </p>

              <!-- Requirements List -->
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

              <v-divider class="my-4" />

              <!-- Recovery PIN Section -->
              <h3 class="text-subtitle-1 font-weight-bold mb-2">
                <v-icon class="mr-2">mdi-shield-key</v-icon>
                Recovery PIN Setup
              </h3>
              <p class="text-caption text-muted-a11y mb-4">
                Create a 4-digit PIN for password recovery. This PIN can be used if you forget your
                password.
              </p>

              <!-- Recovery PIN -->
              <v-text-field
                v-model="recoveryPin"
                label="Recovery PIN (4 digits)"
                prepend-inner-icon="mdi-numeric"
                variant="outlined"
                type="text"
                inputmode="numeric"
                maxlength="4"
                :rules="pinRules"
                :disabled="loading"
                autocomplete="off"
                class="mb-4"
                aria-label="Enter your 4-digit recovery PIN"
                aria-required="true"
                hint="Enter 4 digits (example: 1234)"
                persistent-hint
                @keypress="onlyNumbers"
              />

              <!-- Confirm PIN -->
              <v-text-field
                v-model="confirmPin"
                label="Confirm Recovery PIN"
                prepend-inner-icon="mdi-numeric-positive-1"
                variant="outlined"
                type="text"
                inputmode="numeric"
                maxlength="4"
                :rules="confirmPinRules"
                :disabled="loading"
                autocomplete="off"
                class="mb-4"
                aria-label="Confirm your 4-digit recovery PIN"
                aria-required="true"
                @keypress="onlyNumbers"
              />

              <!-- Security Warning -->
              <AppAlert type="warning" variant="tonal" density="compact" class="mb-4">
                <strong>Important:</strong> Keep your recovery PIN secure. Do not use obvious PINs
                like 0000 or 1234.
              </AppAlert>

              <!-- Submit Button -->
              <v-btn
                type="submit"
                color="primary"
                size="large"
                block
                :loading="loading"
                :disabled="!isFormValid || loading"
                class="mt-4"
                aria-label="Complete setup and continue to dashboard"
              >
                <v-icon v-if="!loading" start>mdi-check-circle</v-icon>
                {{ loading ? 'Setting up...' : 'Complete Setup' }}
              </v-btn>
            </v-form>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import AppAlert from '@/components/ui/AppAlert.vue'
import api from '@/services/api'

// Composables
const router = useRouter()

// State
const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const recoveryPin = ref('')
const confirmPin = ref('')
const showCurrentPassword = ref(false)
const showNewPassword = ref(false)
const showConfirmPassword = ref(false)
const loading = ref(false)
const error = ref('')
const firstLoginForm = ref(null)

// Validation rules
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

const pinRules = [
  (v) => !!v || 'Recovery PIN is required',
  (v) => /^\d{4}$/.test(v) || 'PIN must be exactly 4 digits',
]

const confirmPinRules = [
  (v) => !!v || 'PIN confirmation is required',
  (v) => /^\d{4}$/.test(v) || 'PIN must be exactly 4 digits',
  (v) => v === recoveryPin.value || 'PINs do not match',
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

const passwordStrength = computed(() => {
  const metRequirements = passwordRequirements.value.filter((req) => req.met).length
  return (metRequirements / passwordRequirements.value.length) * 100
})

const passwordStrengthColor = computed(() => {
  if (passwordStrength.value < 40) return 'error'
  if (passwordStrength.value < 70) return 'warning'
  return 'success'
})

const passwordStrengthText = computed(() => {
  if (passwordStrength.value < 40) return 'Weak'
  if (passwordStrength.value < 70) return 'Good'
  return 'Strong'
})

const isFormValid = computed(() => {
  return (
    currentPassword.value &&
    newPassword.value &&
    confirmPassword.value &&
    newPassword.value === confirmPassword.value &&
    passwordRequirements.value.every((req) => req.met) &&
    recoveryPin.value &&
    confirmPin.value &&
    recoveryPin.value === confirmPin.value &&
    /^\d{4}$/.test(recoveryPin.value) &&
    /^\d{4}$/.test(confirmPin.value)
  )
})

// Methods
function onlyNumbers(event) {
  const charCode = event.which ? event.which : event.keyCode
  if (charCode < 48 || charCode > 57) {
    event.preventDefault()
  }
}

async function handleSubmit() {
  // Validate form
  const { valid } = await firstLoginForm.value.validate()
  if (!valid) {
    return
  }

  loading.value = true
  error.value = ''

  try {
    await api.auth.completeFirstLogin({
      current_password: currentPassword.value,
      new_password: newPassword.value,
      confirm_password: confirmPassword.value,
      recovery_pin: recoveryPin.value,
      confirm_pin: confirmPin.value,
    })

    // Redirect to dashboard
    router.push('/')
  } catch (err) {
    console.error('[FirstLogin] Failed to complete setup:', err)

    if (err.response?.data?.detail) {
      error.value = err.response.data.detail
    } else if (err.message) {
      error.value = `Setup failed: ${err.message}`
    } else {
      error.value = 'Failed to complete setup. Please try again.'
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.first-login-container {
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

.first-login-card {
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}

.requirement-list {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  padding: 12px;
}

/* Dark theme adjustments */
:deep(.v-theme--dark) .first-login-container {
  background: linear-gradient(135deg, rgb(18, 29, 42) 0%, rgb(10, 15, 22) 100%);
}

/* Accessibility: Focus indicators */
.v-text-field:focus-within {
  outline: 2px solid rgba(var(--v-theme-primary), 0.5);
  outline-offset: 2px;
  border-radius: 4px;
}

.v-btn:focus-visible {
  outline: 2px solid rgba(var(--v-theme-primary), 0.8);
  outline-offset: 2px;
}
</style>
