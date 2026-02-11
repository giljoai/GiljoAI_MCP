<template>
  <v-container class="pa-0 ma-0" fluid>
    <v-row no-gutters class="fill-height">
      <v-col cols="12" class="d-flex flex-column align-center justify-center">
        <v-card class="admin-card mx-auto" max-width="500" elevation="8">
          <v-card-title class="text-h4 text-center pa-6 admin-title">
            Create Administrator Account
          </v-card-title>

          <v-card-subtitle class="text-center pb-4 text-body-1">
            Set up your first administrator to access GiljoAI MCP
          </v-card-subtitle>

          <v-card-text class="pa-6">
            <v-form ref="adminForm" v-model="formValid" @submit.prevent="createAdmin">
              <!-- Workspace Name (Handover 0424h) -->
              <v-text-field
                v-model="workspaceName"
                label="Workspace Name"
                :rules="workspaceNameRules"
                variant="outlined"
                density="comfortable"
                class="mb-4"
                hint="Name for your organization (e.g., 'Acme Corp', 'My Team')"
                persistent-hint
                prepend-inner-icon="mdi-domain"
                required
              />

              <!-- Username -->
              <v-text-field
                v-model="username"
                label="Username"
                :rules="usernameRules"
                variant="outlined"
                density="comfortable"
                class="mb-4"
                hint="Unique username for login"
                persistent-hint
                prepend-inner-icon="mdi-account"
              />

              <!-- Email -->
              <v-text-field
                v-model="email"
                label="Email (optional)"
                type="email"
                :rules="emailRules"
                variant="outlined"
                density="comfortable"
                class="mb-4"
                prepend-inner-icon="mdi-email"
              />

              <!-- Full Name -->
              <v-text-field
                v-model="fullName"
                label="Full Name (optional)"
                variant="outlined"
                density="comfortable"
                class="mb-4"
                prepend-inner-icon="mdi-account-box"
              />

              <!-- Password -->
              <v-text-field
                v-model="password"
                label="Password"
                :type="showPassword ? 'text' : 'password'"
                :rules="passwordRules"
                variant="outlined"
                density="comfortable"
                class="mb-4"
                prepend-inner-icon="mdi-lock"
                :append-inner-icon="showPassword ? 'mdi-eye' : 'mdi-eye-off'"
                @click:append-inner="showPassword = !showPassword"
              />

              <!-- Confirm Password -->
              <v-text-field
                v-model="confirmPassword"
                label="Confirm Password"
                :type="showConfirmPassword ? 'text' : 'password'"
                :rules="confirmPasswordRules"
                variant="outlined"
                density="comfortable"
                class="mb-4"
                prepend-inner-icon="mdi-lock-check"
                :append-inner-icon="showConfirmPassword ? 'mdi-eye' : 'mdi-eye-off'"
                @click:append-inner="showConfirmPassword = !showConfirmPassword"
              />

              <!-- Compact Password Compliance Indicator -->
              <div v-if="passwordMeetsAll" class="d-flex align-center mb-4">
                <v-icon color="success" size="16" class="mr-1">mdi-check-circle</v-icon>
                <span class="text-caption">Meets password requirements</span>
                <v-tooltip location="top" max-width="300">
                  <template #activator="{ props }">
                    <v-icon v-bind="props" size="16" class="ml-1">mdi-information-outline</v-icon>
                  </template>
                  <span class="text-caption"
                    >At least 12 characters, one uppercase, one lowercase, one digit, and one
                    special character.</span
                  >
                </v-tooltip>
              </div>

              <v-divider class="my-4" />

              <!-- Recovery PIN Section -->
              <h3 class="text-subtitle-1 font-weight-bold mb-2">
                <v-icon class="mr-2">mdi-shield-key</v-icon>
                Recovery PIN Setup
              </h3>
              <p class="text-caption text-medium-emphasis mb-4">
                Create a 4-digit PIN for password recovery. This PIN can be used if you forget your
                password.
              </p>

              <!-- Recovery PIN -->
              <v-text-field
                v-model="recoveryPin"
                label="Recovery PIN (4 digits)"
                type="text"
                inputmode="numeric"
                pattern="[0-9]{4}"
                maxlength="4"
                :rules="pinRules"
                variant="outlined"
                density="comfortable"
                class="mb-3"
                hint="Enter 4 digits (example: 1234)"
                persistent-hint
                aria-label="Enter your 4-digit recovery PIN"
                aria-required="true"
                @input="handlePinInput"
                @keypress="onlyNumbers"
              />

              <!-- Confirm PIN -->
              <v-text-field
                v-model="confirmPin"
                label="Confirm Recovery PIN"
                type="text"
                inputmode="numeric"
                pattern="[0-9]{4}"
                maxlength="4"
                :rules="confirmPinRules"
                variant="outlined"
                density="comfortable"
                class="mb-3"
                aria-label="Confirm your 4-digit recovery PIN"
                aria-required="true"
                @input="handleConfirmPinInput"
                @keypress="onlyNumbers"
              />

              <!-- Error Message -->
              <v-alert v-if="errorMessage" type="error" variant="tonal" class="mb-4">
                {{ errorMessage }}
              </v-alert>

              <!-- Submit Button -->
              <v-btn
                type="submit"
                color="primary"
                size="large"
                block
                :loading="loading"
                :disabled="!formValid"
                class="mt-4"
              >
                Create Administrator Account
              </v-btn>
            </v-form>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/services/api'

const router = useRouter()

// Form data
const workspaceName = ref('')
const username = ref('')
const email = ref('')
const fullName = ref('')
const password = ref('')
const confirmPassword = ref('')
const recoveryPin = ref('')
const confirmPin = ref('')
const showPassword = ref(false)
const showConfirmPassword = ref(false)
const formValid = ref(false)
const loading = ref(false)
const errorMessage = ref('')

// Validation rules
const workspaceNameRules = [
  (v) => !!v || 'Workspace name is required',
  (v) => v.length >= 1 || 'Workspace name is required',
  (v) => v.length <= 255 || 'Workspace name must be less than 255 characters',
]

const usernameRules = [
  (v) => !!v || 'Username is required',
  (v) => v.length >= 3 || 'Username must be at least 3 characters',
  (v) => v.length <= 64 || 'Username must be less than 64 characters',
  (v) =>
    /^[a-zA-Z0-9_-]+$/.test(v) ||
    'Username can only contain letters, numbers, underscores, and hyphens',
]

const emailRules = [(v) => !v || /.+@.+\..+/.test(v) || 'Email must be valid']

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
  (v) => v === password.value || 'Passwords do not match',
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
  { text: 'At least 12 characters', met: password.value.length >= 12 },
  { text: 'One uppercase letter', met: /[A-Z]/.test(password.value) },
  { text: 'One lowercase letter', met: /[a-z]/.test(password.value) },
  { text: 'One digit', met: /\d/.test(password.value) },
  { text: 'One special character', met: /[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(password.value) },
  {
    text: 'Passwords match',
    met: password.value === confirmPassword.value && confirmPassword.value !== '',
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

// All requirements satisfied?
const passwordMeetsAll = computed(() => passwordRequirements.value.every((r) => r.met))

// Methods for PIN input handling
function handlePinInput(value) {
  // Handle both string and event objects
  const val = typeof value === 'string' ? value : value?.target?.value || ''
  recoveryPin.value = val.replace(/\D/g, '').slice(0, 4)
}

function handleConfirmPinInput(value) {
  // Handle both string and event objects
  const val = typeof value === 'string' ? value : value?.target?.value || ''
  confirmPin.value = val.replace(/\D/g, '').slice(0, 4)
}

function onlyNumbers(event) {
  const charCode = event.which ? event.which : event.keyCode
  if (charCode < 48 || charCode > 57) {
    event.preventDefault()
  }
}

// Clear error on input
watch([workspaceName, username, email, password, confirmPassword, recoveryPin, confirmPin], () => {
  errorMessage.value = ''
})

// Create admin function
const createAdmin = async () => {
  if (!formValid.value) return

  loading.value = true
  errorMessage.value = ''

  try {
    // Call new API endpoint with workspace_name (Handover 0424h)
    await api.auth.createFirstAdmin({
      workspace_name: workspaceName.value,
      username: username.value,
      email: email.value || null,
      full_name: fullName.value || null,
      password: password.value,
      confirm_password: confirmPassword.value,
      recovery_pin: recoveryPin.value,
      confirm_pin: confirmPin.value,
    })

    // Success - redirect to dashboard (JWT cookie set by API)
    router.push('/') // Dashboard is at root path
  } catch (error) {
    console.error('[CREATE_ADMIN] Failed:', error)

    // Extract error message
    if (error.response?.data?.detail) {
      errorMessage.value = error.response.data.detail
    } else if (error.message) {
      errorMessage.value = error.message
    } else {
      errorMessage.value = 'Failed to create administrator account. Please try again.'
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.fill-height {
  min-height: 100vh;
}

.admin-card {
  margin-top: 5vh;
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.admin-title {
  background: linear-gradient(45deg, #ffd93d, #6bcf7f);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  font-weight: 700;
}

.requirement-list {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 16px;
}
</style>
