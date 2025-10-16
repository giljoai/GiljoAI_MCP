<template>
  <v-container fluid class="fill-height welcome-container">
    <v-row align="center" justify="center">
      <v-col cols="12" sm="8" md="5" lg="4">
        <v-card elevation="8" class="welcome-card">
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
              <h1 class="text-h5 font-weight-bold">Welcome to<br/>GiljoAI Agent Orchestration MCP Server</h1>
              <p class="text-body-2 text-medium-emphasis mt-2">Set Your Administrator Password</p>
            </div>
          </v-card-title>

          <v-divider />

          <v-card-text class="pa-6">
            <!-- Alert for errors -->
            <v-alert
              v-if="error"
              type="error"
              variant="tonal"
              class="mb-4"
              closable
              @click:close="error = ''"
            >
              {{ error }}
            </v-alert>

            <!-- Alert for success messages -->
            <v-alert
              v-if="successMessage"
              type="success"
              variant="tonal"
              class="mb-4"
            >
              <div class="d-flex align-center">
                <v-icon start class="mr-2">mdi-check-circle</v-icon>
                {{ successMessage }}
              </div>
            </v-alert>

            <!-- Info message about password requirements -->
            <v-alert
              type="info"
              variant="tonal"
              class="mb-4"
              density="compact"
            >
              <div class="text-body-2">
Create a secure password (minimum 8 characters)
              </div>
            </v-alert>

            <!-- Password Setup Form -->
            <v-form @submit.prevent="handlePasswordSetup" ref="passwordForm">
              <v-text-field
                v-model="newPassword"
                label="New Password"
                prepend-inner-icon="mdi-lock"
                :append-inner-icon="showPassword ? 'mdi-eye' : 'mdi-eye-off'"
                :type="showPassword ? 'text' : 'password'"
                variant="outlined"
                :rules="[rules.required, rules.minLength]"
                :disabled="loading"
                autofocus
                autocomplete="new-password"
                aria-label="New password"
                aria-required="true"
                @click:append-inner="showPassword = !showPassword"
                @input="error = ''"
              />

              <v-text-field
                v-model="confirmPassword"
                label="Confirm Password"
                prepend-inner-icon="mdi-lock-check"
                :append-inner-icon="showConfirmPassword ? 'mdi-eye' : 'mdi-eye-off'"
                :type="showConfirmPassword ? 'text' : 'password'"
                variant="outlined"
                :rules="[rules.required, rules.passwordMatch]"
                :disabled="loading"
                autocomplete="new-password"
                aria-label="Confirm password"
                aria-required="true"
                class="mt-4"
                @click:append-inner="showConfirmPassword = !showConfirmPassword"
                @keyup.enter="handlePasswordSetup"
                @input="error = ''"
              />

              <!-- Password strength indicator -->
              <div v-if="newPassword.length > 0" class="mt-2 mb-4">
                <div class="d-flex align-center">
                  <v-progress-linear
                    :model-value="passwordStrength"
                    :color="passwordStrengthColor"
                    height="6"
                    class="flex-grow-1"
                    rounded
                  />
                  <span class="text-caption ml-2" :style="{ color: passwordStrengthColor }">
                    {{ passwordStrengthLabel }}
                  </span>
                </div>
              </div>

              <v-btn
                type="submit"
                color="primary"
                size="large"
                block
                :loading="loading"
                :disabled="!canSubmit || loading"
                class="mt-4"
              >
                <v-icon start v-if="!loading">mdi-check-circle</v-icon>
                {{ loading ? 'Setting Password...' : 'Set Password & Continue' }}
              </v-btn>
            </v-form>
          </v-card-text>

          <v-divider />

          <!-- Footer Info -->
          <v-card-text class="text-center pa-4">
            <p class="text-caption text-medium-emphasis">
              <v-icon size="small" class="mr-1">mdi-shield-lock</v-icon>
              Your password will be encrypted and stored securely
            </p>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useTheme } from 'vuetify'
import api from '@/services/api'

// Composables
const router = useRouter()
const theme = useTheme()

// State
const newPassword = ref('')
const confirmPassword = ref('')
const showPassword = ref(false)
const showConfirmPassword = ref(false)
const loading = ref(false)
const error = ref('')
const successMessage = ref('')
const passwordForm = ref(null)

// Validation rules
const rules = {
  required: (value) => !!value || 'This field is required',
  minLength: (value) => value.length >= 8 || 'Password must be at least 8 characters',
  passwordMatch: (value) => value === newPassword.value || 'Passwords do not match',
}

// Password strength calculation
const passwordStrength = computed(() => {
  const password = newPassword.value
  if (password.length === 0) return 0

  let strength = 0

  // Length check
  if (password.length >= 8) strength += 25
  if (password.length >= 12) strength += 25

  // Complexity checks
  if (/[a-z]/.test(password)) strength += 12.5
  if (/[A-Z]/.test(password)) strength += 12.5
  if (/[0-9]/.test(password)) strength += 12.5
  if (/[^a-zA-Z0-9]/.test(password)) strength += 12.5

  return Math.min(strength, 100)
})

const passwordStrengthColor = computed(() => {
  if (passwordStrength.value < 40) return 'error'
  if (passwordStrength.value < 70) return 'warning'
  return 'success'
})

const passwordStrengthLabel = computed(() => {
  if (passwordStrength.value < 40) return 'Weak'
  if (passwordStrength.value < 70) return 'Good'
  return 'Strong'
})

// Form validation
const canSubmit = computed(() => {
  return (
    newPassword.value.length >= 8 &&
    confirmPassword.value.length >= 8 &&
    newPassword.value === confirmPassword.value
  )
})

// Methods
async function handlePasswordSetup() {
  // Validate form
  const { valid } = await passwordForm.value.validate()
  if (!valid) {
    return
  }

  loading.value = true
  error.value = ''

  try {
    // POST to /api/auth/change-password with default credentials
    await api.auth.changePassword({
      current_password: 'admin',
      new_password: newPassword.value,
      confirm_password: confirmPassword.value,
    })

    // Show success message
    successMessage.value = 'Password set successfully! Redirecting to login...'

    // Wait 2 seconds to show success message
    await new Promise((resolve) => setTimeout(resolve, 2000))

    // Redirect to login page - user will validate new credentials
    router.push('/login')
  } catch (err) {
    // Handle specific error types with user-friendly messages
    if (err.response?.status === 401) {
      error.value = 'Authentication failed. Please contact support if this issue persists.'
    } else if (err.response?.status === 400) {
      const detail = err.response?.data?.detail || ''
      if (detail.toLowerCase().includes('password')) {
        error.value = detail
      } else {
        error.value = 'Invalid password format. Please ensure your password meets requirements.'
      }
    } else if (err.response?.data?.detail) {
      error.value = err.response.data.detail
    } else if (err.code === 'ERR_NETWORK' || !err.response) {
      error.value = 'Network error - please check your connection and try again'
    } else if (err.message) {
      error.value = `Password setup failed: ${err.message}`
    } else {
      error.value = 'Password setup failed. Please try again.'
    }

    // Clear passwords on error
    newPassword.value = ''
    confirmPassword.value = ''
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.welcome-container {
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

.welcome-card {
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}

/* Dark theme adjustments */
:deep(.v-theme--dark) .welcome-container {
  background: linear-gradient(135deg, rgb(18, 29, 42) 0%, rgb(10, 15, 22) 100%);
}

/* Light theme adjustments */
:deep(.v-theme--light) .welcome-container {
  background: linear-gradient(135deg, rgb(240, 244, 248) 0%, rgb(220, 230, 240) 100%);
}

/* Accessibility: Focus indicators */
.v-text-field:focus-within {
  outline: 2px solid rgba(var(--v-theme-primary), 0.5);
  outline-offset: 2px;
  border-radius: 4px;
}

/* Password strength progress bar styling */
:deep(.v-progress-linear) {
  border-radius: 3px;
}
</style>
