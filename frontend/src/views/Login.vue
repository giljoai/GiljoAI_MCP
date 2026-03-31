<template>
  <v-container fluid class="fill-height login-container">
    <v-row align="center" justify="center">
      <v-col cols="12" sm="8" md="5" lg="4">
        <v-card elevation="8" class="login-card smooth-border">
          <!-- Logo/Header -->
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
              <h1 class="text-h5 font-weight-bold">GiljoAI MCP Login</h1>
              <span class="edition-badge mt-2 text-caption">
                Community Edition
              </span>
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

            <!-- Alert for success messages -->
            <AppAlert
              v-if="successMessage"
              type="success"
              variant="tonal"
              class="mb-4"
              closable
              @click:close="successMessage = ''"
            >
              {{ successMessage }}
            </AppAlert>

            <!-- Login Form -->
            <v-form ref="loginForm" @submit.prevent="handleLogin">
              <v-text-field
                v-model="username"
                label="Username"
                prepend-inner-icon="mdi-account"
                variant="outlined"
                :rules="[rules.required]"
                :disabled="loading"
                autofocus
                autocomplete="username"
                data-testid="email-input"
                @keyup.enter="handleLogin"
                @input="error = ''"
              />

              <v-text-field
                v-model="password"
                label="Password"
                prepend-inner-icon="mdi-lock"
                :type="showPassword ? 'text' : 'password'"
                variant="outlined"
                :rules="[rules.required]"
                :disabled="loading"
                autocomplete="current-password"
                class="mt-4"
                data-testid="password-input"
                @keyup.enter="handleLogin"
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

              <v-checkbox
                v-model="rememberMe"
                label="Remember me"
                color="primary"
                density="compact"
                :disabled="loading"
                class="mt-2"
              />

              <v-btn
                type="submit"
                color="primary"
                size="large"
                block
                :loading="loading"
                :disabled="!username || !password || loading"
                class="mt-4"
                data-testid="login-button"
              >
                <v-icon v-if="!loading" start>mdi-login</v-icon>
                {{ loading ? 'Logging in...' : 'Sign In' }}
              </v-btn>

              <!-- Forgot Password Link -->
              <div class="text-center mt-4">
                <v-btn
                  variant="text"
                  color="primary"
                  :disabled="loading"
                  aria-label="Open forgot password dialog"
                  @click="handleForgotPasswordClick"
                >
                  <v-icon start>mdi-lock-question</v-icon>
                  Forgot Password?
                </v-btn>
              </div>
            </v-form>
          </v-card-text>

          <!-- Forgot Password Modal -->
          <ForgotPasswordPin
            v-model:show="showForgotPassword"
            @success="handlePasswordResetSuccess"
          />

          <v-divider />

          <!-- Footer Info -->
          <v-card-text class="text-center pa-4">
            <a
              href="https://www.giljo.ai"
              target="_blank"
              rel="noopener noreferrer"
              class="text-caption text-muted-a11y text-decoration-none"
            >
              www.giljo.ai
            </a>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import AppAlert from '@/components/ui/AppAlert.vue'
import ForgotPasswordPin from '@/components/ForgotPasswordPin.vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import api from '@/services/api'

// Composables
const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

// State
const username = ref('')
const password = ref('')
const rememberMe = ref(false)
const showPassword = ref(false)
const showForgotPassword = ref(false)
const loading = ref(false)
const error = ref('')
const successMessage = ref('')
const loginForm = ref(null)

// Validation rules
const rules = {
  required: (value) => !!value || 'This field is required',
}

// Methods
async function handleLogin() {
  // Validate form
  const { valid } = await loginForm.value.validate()
  if (!valid) {
    return
  }

  loading.value = true
  error.value = ''

  try {
    // Use user store login method - this will authenticate AND populate currentUser
    const loginSuccess = await userStore.login(username.value, password.value)

    if (!loginSuccess) {
      error.value = 'Login failed. Please check your credentials.'
      return
    }

    // Check if first login is required (password change or PIN setup)
    try {
      const firstLoginResponse = await api.auth.checkFirstLogin(username.value)
      const firstLoginData = firstLoginResponse.data

      if (firstLoginData.must_change_password || firstLoginData.must_set_pin) {
        // Redirect to first login page for password change and/or PIN setup
        router.push('/first-login')
        return
      }
    } catch (firstLoginErr) {
      console.warn('[Login] First login check failed:', firstLoginErr)
      // Continue with normal login flow if check fails
    }

    // Legacy check for backward compatibility
    if (userStore.currentUser?.password_change_required) {
      // Redirect to first login page for password setup
      router.push('/first-login')
      return
    }

    // SECURITY: Mark setup as completed (user successfully logged in after setup)
    localStorage.setItem('setup_completed', 'true')

    // Store remember me preference
    if (rememberMe.value) {
      localStorage.setItem('remember_me', 'true')
      localStorage.setItem('remembered_username', username.value)
    } else {
      localStorage.removeItem('remember_me')
      localStorage.removeItem('remembered_username')
    }

    // Show success message briefly
    successMessage.value = 'Login successful! Redirecting...'

    // Small delay to show success message
    await new Promise((resolve) => setTimeout(resolve, 500))

    // Redirect to the original destination or dashboard
    const redirect = route.query.redirect || '/'
    router.push(redirect)
  } catch (err) {
    // Handle specific error types with user-friendly messages
    if (err.response?.status === 401) {
      // Check if there's a specific detail about inactive account or password change required
      const detail = err.response?.data?.detail || ''
      if (detail.toLowerCase().includes('inactive')) {
        error.value = 'Account is inactive. Please contact your administrator.'
      } else if (
        detail.toLowerCase().includes('must_change_password') ||
        detail.toLowerCase().includes('change password')
      ) {
        // Redirect to welcome page for password setup
        router.push('/welcome')
        return
      } else {
        error.value = 'Invalid username or password'
      }
    } else if (err.response?.status === 403) {
      const detail = err.response?.data?.detail || ''
      if (
        detail.toLowerCase().includes('must_change_password') ||
        detail.toLowerCase().includes('change password')
      ) {
        // Redirect to welcome page for password setup
        router.push('/welcome')
        return
      }
      error.value = 'Access forbidden. Please contact your administrator.'
    } else if (err.response?.status === 429) {
      error.value = 'Too many login attempts. Please try again later.'
    } else if (err.response?.data?.detail) {
      error.value = err.response.data.detail
    } else if (err.code === 'ERR_NETWORK' || !err.response) {
      error.value = 'Network error - please check your connection and try again'
    } else if (err.message) {
      error.value = `Login failed: ${err.message}`
    } else {
      error.value = 'Login failed. Please try again.'
    }

    // Clear password field on error
    password.value = ''
  } finally {
    loading.value = false
  }
}

// Handle forgot password click
function handleForgotPasswordClick() {
  showForgotPassword.value = true
}

// Handle password reset success
function handlePasswordResetSuccess(message) {
  successMessage.value = message
  showForgotPassword.value = false
}

// Check if already authenticated on mount
onMounted(async () => {
  // Check for password change success message
  if (route.query.passwordChanged === 'true') {
    successMessage.value = 'Password changed successfully! Please log in with your new credentials.'
  }

  // Restore remembered username if available
  const rememberedUsername = localStorage.getItem('remembered_username')
  const rememberMeFlag = localStorage.getItem('remember_me')

  if (rememberedUsername && rememberMeFlag === 'true') {
    username.value = rememberedUsername
    rememberMe.value = true
  }

  // REMOVED: Auto-login check
  // Always require manual login - no automatic authentication
})
</script>

<style scoped>
.login-container {
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

.login-card {
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}

/* Dark theme adjustments */
:deep(.v-theme--dark) .login-container {
  background: linear-gradient(135deg, rgb(18, 29, 42) 0%, rgb(10, 15, 22) 100%);
}

/* Tinted edition badge */
.edition-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 8px;
  background: rgba(136, 149, 168, 0.15);
  color: #8895a8;
  font-weight: 500;
}

/* Accessibility: Focus indicators */
.v-text-field:focus-within {
  outline: 2px solid rgba(var(--v-theme-primary), 0.5);
  outline-offset: 2px;
  border-radius: 4px;
}
</style>
