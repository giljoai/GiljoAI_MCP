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

              <!-- Password Strength -->
              <v-progress-linear
                :model-value="passwordStrength"
                :color="passwordStrengthColor"
                height="8"
                rounded
                class="mb-2"
              />
              <p class="text-caption mb-4" :class="passwordStrengthColor + '--text'">
                Password Strength: {{ passwordStrengthText }}
              </p>

              <!-- Requirements List -->
              <v-list density="compact" class="requirement-list">
                <v-list-item v-for="req in passwordRequirements" :key="req.text" class="px-0 py-1">
                  <template #prepend>
                    <v-icon :color="req.met ? 'success' : 'error'" size="small">
                      {{ req.met ? 'mdi-check-circle' : 'mdi-close-circle' }}
                    </v-icon>
                  </template>
                  <v-list-item-title class="text-caption">{{ req.text }}</v-list-item-title>
                </v-list-item>
              </v-list>

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
const username = ref('')
const email = ref('')
const fullName = ref('')
const password = ref('')
const confirmPassword = ref('')
const showPassword = ref(false)
const showConfirmPassword = ref(false)
const formValid = ref(false)
const loading = ref(false)
const errorMessage = ref('')

// Validation rules
const usernameRules = [
  v => !!v || 'Username is required',
  v => v.length >= 3 || 'Username must be at least 3 characters',
  v => v.length <= 64 || 'Username must be less than 64 characters',
  v => /^[a-zA-Z0-9_-]+$/.test(v) || 'Username can only contain letters, numbers, underscores, and hyphens'
]

const emailRules = [
  v => !v || /.+@.+\..+/.test(v) || 'Email must be valid'
]

const passwordRules = [
  v => !!v || 'Password is required',
  v => v.length >= 12 || 'Password must be at least 12 characters',
  v => /[A-Z]/.test(v) || 'Must contain at least one uppercase letter',
  v => /[a-z]/.test(v) || 'Must contain at least one lowercase letter',
  v => /\d/.test(v) || 'Must contain at least one digit',
  v => /[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(v) || 'Must contain at least one special character'
]

const confirmPasswordRules = [
  v => !!v || 'Password confirmation is required',
  v => v === password.value || 'Passwords do not match'
]

// Password requirements
const passwordRequirements = computed(() => [
  { text: 'At least 12 characters', met: password.value.length >= 12 },
  { text: 'One uppercase letter', met: /[A-Z]/.test(password.value) },
  { text: 'One lowercase letter', met: /[a-z]/.test(password.value) },
  { text: 'One digit', met: /\d/.test(password.value) },
  { text: 'One special character', met: /[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(password.value) },
  { text: 'Passwords match', met: password.value === confirmPassword.value && confirmPassword.value !== '' }
])

const passwordStrength = computed(() => {
  const metRequirements = passwordRequirements.value.filter(req => req.met).length
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

// Clear error on input
watch([username, email, password, confirmPassword], () => {
  errorMessage.value = ''
})

// Create admin function
const createAdmin = async () => {
  if (!formValid.value) return

  loading.value = true
  errorMessage.value = ''

  try {
    // Call new API endpoint
    await api.auth.createFirstAdmin({
      username: username.value,
      email: email.value || null,
      full_name: fullName.value || null,
      password: password.value,
      confirm_password: confirmPassword.value
    })

    // Success - redirect to dashboard (JWT cookie set by API)
    console.log('[CREATE_ADMIN] Admin account created successfully, redirecting to dashboard')
    router.push('/dashboard')
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
  background: linear-gradient(45deg, #FFD93D, #6BCF7F);
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
