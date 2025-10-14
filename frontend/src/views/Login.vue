<template>
  <v-container fluid class="fill-height login-container">
    <v-row align="center" justify="center">
      <v-col cols="12" sm="8" md="5" lg="4">
        <v-card elevation="8" class="login-card">
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
              <h1 class="text-h5 font-weight-bold">GiljoAI MCP Login</h1>
              <p class="text-body-2 text-medium-emphasis mt-2">Agent Orchestration System</p>
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
            <v-form @submit.prevent="handleLogin" ref="loginForm">
              <v-text-field
                v-model="username"
                label="Username"
                prepend-inner-icon="mdi-account"
                variant="outlined"
                :rules="[rules.required]"
                :disabled="loading"
                autofocus
                autocomplete="username"
                @keyup.enter="handleLogin"
                @input="error = ''"
              />

              <v-text-field
                v-model="password"
                label="Password"
                prepend-inner-icon="mdi-lock"
                :append-inner-icon="showPassword ? 'mdi-eye' : 'mdi-eye-off'"
                :type="showPassword ? 'text' : 'password'"
                variant="outlined"
                :rules="[rules.required]"
                :disabled="loading"
                autocomplete="current-password"
                class="mt-4"
                @click:append-inner="showPassword = !showPassword"
                @keyup.enter="handleLogin"
                @input="error = ''"
              />

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
              >
                <v-icon start v-if="!loading">mdi-login</v-icon>
                {{ loading ? 'Logging in...' : 'Sign In' }}
              </v-btn>
            </v-form>
          </v-card-text>

          <v-divider />

          <!-- Footer Info -->
          <v-card-text class="text-center pa-4">
            <p class="text-caption text-medium-emphasis">
              <v-icon size="small" class="mr-1">mdi-information</v-icon>
              Localhost mode (127.0.0.1) bypasses authentication
            </p>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import AppAlert from '@/components/ui/AppAlert.vue'
import { useRouter, useRoute } from 'vue-router'
import { useTheme } from 'vuetify'
import api from '@/services/api'

// Composables
const router = useRouter()
const route = useRoute()
const theme = useTheme()

// State
const username = ref('')
const password = ref('')
const rememberMe = ref(false)
const showPassword = ref(false)
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
    // POST to /api/auth/login with credentials
    // The backend sets an httpOnly cookie named 'access_token' automatically
    // We don't need to store it in localStorage - the browser handles it
    const response = await api.auth.login(username.value, password.value)

    // Check if password change is required (v3.0 unified auth)
    if (response.data?.password_change_required) {
      // Redirect to password change page
      router.push('/change-password')
      return
    }

    // Store user data if provided (for display purposes, not auth)
    if (response.data) {
      const userData = {
        username: response.data.username,
        role: response.data.role,
        tenant_key: response.data.tenant_key
      }
      localStorage.setItem('user', JSON.stringify(userData))
    }

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
      } else if (detail.toLowerCase().includes('must_change_password') || detail.toLowerCase().includes('change password')) {
        // Redirect to password change page
        router.push('/change-password')
        return
      } else {
        error.value = 'Invalid username or password'
      }
    } else if (err.response?.status === 403) {
      const detail = err.response?.data?.detail || ''
      if (detail.toLowerCase().includes('must_change_password') || detail.toLowerCase().includes('change password')) {
        // Redirect to password change page
        router.push('/change-password')
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

// Check if already authenticated on mount
onMounted(async () => {
  // Restore remembered username if available
  const rememberedUsername = localStorage.getItem('remembered_username')
  const rememberMeFlag = localStorage.getItem('remember_me')
  
  if (rememberedUsername && rememberMeFlag === 'true') {
    username.value = rememberedUsername
    rememberMe.value = true
  }

  try {
    // Try to access a protected endpoint to check if already logged in
    await api.auth.me()

    // If successful, user is already authenticated, redirect to dashboard
    const redirect = route.query.redirect || '/'
    router.push(redirect)
  } catch (err) {
    // Not authenticated, stay on login page
    console.log('User not authenticated, showing login page')
  }
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

/* Light theme adjustments */
:deep(.v-theme--light) .login-container {
  background: linear-gradient(135deg, rgb(240, 244, 248) 0%, rgb(220, 230, 240) 100%);
}

/* Accessibility: Focus indicators */
.v-text-field:focus-within {
  outline: 2px solid rgba(var(--v-theme-primary), 0.5);
  outline-offset: 2px;
  border-radius: 4px;
}
</style>
