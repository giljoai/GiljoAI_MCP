<template>
  <v-container class="pa-0 ma-0" fluid>
    <v-row no-gutters class="fill-height">
      <!-- Main Content -->
      <v-col cols="12" class="d-flex flex-column">
        <v-card class="welcome-card mx-auto" max-width="500" elevation="8">
          <v-card-title class="text-h4 text-center pa-6 welcome-title">
            Welcome to GiljoAI MCP
          </v-card-title>

          <v-card-subtitle class="text-center pb-4 text-body-1">
            Complete your secure setup by changing the default password
          </v-card-subtitle>

          <v-card-text class="pa-6">
            <v-form ref="passwordForm" v-model="formValid" @submit.prevent="changePassword">
              <!-- Current Password -->
              <v-text-field
                v-model="currentPassword"
                label="Current Password"
                type="password"
                :rules="currentPasswordRules"
                outlined
                dense
                class="mb-4"
                hint="Default password: admin"
                persistent-hint
              />

              <!-- New Password -->
              <v-text-field
                v-model="newPassword"
                label="New Password"
                :type="showNewPassword ? 'text' : 'password'"
                :rules="passwordRules"
                outlined
                dense
                class="mb-4"
                :append-inner-icon="showNewPassword ? 'mdi-eye' : 'mdi-eye-off'"
                @click:append-inner="showNewPassword = !showNewPassword"
              />

              <!-- Confirm Password -->
              <v-text-field
                v-model="confirmPassword"
                label="Confirm New Password"
                :type="showConfirmPassword ? 'text' : 'password'"
                :rules="confirmPasswordRules"
                outlined
                dense
                class="mb-4"
                :append-inner-icon="showConfirmPassword ? 'mdi-eye' : 'mdi-eye-off'"
                @click:append-inner="showConfirmPassword = !showConfirmPassword"
              />

              <!-- Password Strength Indicator -->
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
              <v-list dense class="requirement-list">
                <v-list-item
                  v-for="req in passwordRequirements"
                  :key="req.text"
                  class="px-0 py-1"
                >
                  <template #prepend>
                    <v-icon
                      :color="req.met ? 'success' : 'error'"
                      size="small"
                    >
                      {{ req.met ? 'mdi-check-circle' : 'mdi-close-circle' }}
                    </v-icon>
                  </template>
                  <v-list-item-title class="text-caption">
                    {{ req.text }}
                  </v-list-item-title>
                </v-list-item>
              </v-list>

              <!-- Error Message -->
              <v-alert
                v-if="errorMessage"
                type="error"
                variant="outlined"
                class="mb-4"
              >
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
                Change Password & Continue
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
const currentPassword = ref('admin')
const newPassword = ref('')
const confirmPassword = ref('')
const showNewPassword = ref(false)
const showConfirmPassword = ref(false)
const formValid = ref(false)
const loading = ref(false)
const errorMessage = ref('')

// Password validation rules
const currentPasswordRules = [
  v => !!v || 'Current password is required'
]

const passwordRules = [
  v => !!v || 'Password is required',
  v => v.length >= 12 || 'Password must be at least 12 characters',
  v => /[A-Z]/.test(v) || 'Password must contain at least one uppercase letter',
  v => /[a-z]/.test(v) || 'Password must contain at least one lowercase letter',
  v => /\d/.test(v) || 'Password must contain at least one digit',
  v => /[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(v) || 'Password must contain at least one special character'
]

const confirmPasswordRules = [
  v => !!v || 'Password confirmation is required',
  v => v === newPassword.value || 'Passwords do not match'
]

// Password requirements tracking
const passwordRequirements = computed(() => [
  { text: 'At least 12 characters', met: newPassword.value.length >= 12 },
  { text: 'One uppercase letter', met: /[A-Z]/.test(newPassword.value) },
  { text: 'One lowercase letter', met: /[a-z]/.test(newPassword.value) },
  { text: 'One digit', met: /\d/.test(newPassword.value) },
  { text: 'One special character', met: /[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(newPassword.value) },
  { text: 'Passwords match', met: newPassword.value === confirmPassword.value && confirmPassword.value !== '' }
])

// Password strength calculation
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

// Clear error message when form changes
watch([currentPassword, newPassword, confirmPassword], () => {
  errorMessage.value = ''
})

// Change password function
const changePassword = async () => {
  if (!formValid.value) return

  loading.value = true
  errorMessage.value = ''

  try {
    await api.changePassword(currentPassword.value, newPassword.value)

    // Password changed successfully, redirect to dashboard
    router.push('/dashboard')
  } catch (error) {
    console.error('Password change failed:', error)
    errorMessage.value = error.response?.data?.detail || 'Failed to change password. Please try again.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.welcome-card {
  margin-top: 10vh;
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.welcome-title {
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

.fill-height {
  min-height: 100vh;
}
</style>