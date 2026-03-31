<template>
  <v-container fluid class="fill-height oauth-container">
    <v-row align="center" justify="center">
      <v-col cols="12" sm="8" md="5" lg="4">
        <v-card elevation="8" class="oauth-card smooth-border">
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
              <h1 class="text-h5 font-weight-bold">
                {{ isAuthenticated ? 'Authorize Application' : 'Sign In to Continue' }}
              </h1>
              <p class="text-body-2 oauth-text-muted mt-2">
                {{ isAuthenticated
                  ? 'An application is requesting access to your account'
                  : 'Authentication is required to authorize this application'
                }}
              </p>
            </div>
          </v-card-title>

          <v-divider />

          <!-- Error alert -->
          <v-card-text v-if="error" class="pb-0 pt-4 px-6">
            <AppAlert
              type="error"
              variant="tonal"
              closable
              @click:close="error = ''"
            >
              {{ error }}
            </AppAlert>
          </v-card-text>

          <!-- Missing OAuth parameters warning -->
          <v-card-text v-if="missingParams" class="pa-6">
            <AppAlert type="warning" variant="tonal">
              Invalid authorization request. Required OAuth parameters are missing.
            </AppAlert>
            <div class="text-center mt-4">
              <v-btn
                color="primary"
                variant="outlined"
                :to="{ name: 'Home' }"
                aria-label="Return to home page"
              >
                <v-icon start>mdi-home</v-icon>
                Go to Home
              </v-btn>
            </div>
          </v-card-text>

          <!-- Login Form (shown when not authenticated) -->
          <v-card-text v-else-if="!isAuthenticated" class="pa-6">
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
                aria-label="Username"
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
                aria-label="Password"
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

              <v-btn
                type="submit"
                color="primary"
                size="large"
                block
                :loading="loading"
                :disabled="!username || !password || loading"
                class="mt-4"
                aria-label="Sign in to authorize application"
              >
                <v-icon v-if="!loading" start>mdi-login</v-icon>
                {{ loading ? 'Signing in...' : 'Sign In' }}
              </v-btn>
            </v-form>
          </v-card-text>

          <!-- Consent Form (shown when authenticated) -->
          <v-card-text v-else class="pa-6">
            <!-- Client info -->
            <div class="d-flex align-center mb-4">
              <v-avatar color="primary" size="48" class="mr-4">
                <v-icon size="24" color="white">mdi-application</v-icon>
              </v-avatar>
              <div>
                <p class="text-subtitle-1 font-weight-medium">{{ clientDisplayName }}</p>
                <p class="text-caption oauth-text-muted">wants to access your account</p>
              </div>
            </div>

            <v-divider class="mb-4" />

            <!-- Requested permissions -->
            <p class="text-subtitle-2 font-weight-medium mb-2">Requested permissions</p>
            <v-list density="compact" class="mb-4 bg-transparent">
              <v-list-item
                v-for="permission in scopeDescriptions"
                :key="permission.scope"
                class="px-0"
              >
                <template #prepend>
                  <v-icon color="primary" size="20" class="mr-3">{{ permission.icon }}</v-icon>
                </template>
                <v-list-item-title class="text-body-2">
                  {{ permission.label }}
                </v-list-item-title>
                <v-list-item-subtitle class="text-caption">
                  {{ permission.description }}
                </v-list-item-subtitle>
              </v-list-item>
            </v-list>

            <v-divider class="mb-4" />

            <!-- User identity -->
            <div class="d-flex align-center mb-4">
              <v-icon size="18" color="oauth-text-muted" class="mr-2">mdi-account-circle</v-icon>
              <span class="text-body-2 oauth-text-muted">
                Signed in as <strong>{{ currentUser?.username }}</strong>
              </span>
            </div>

            <!-- Action buttons -->
            <div class="d-flex ga-3">
              <v-btn
                variant="outlined"
                size="large"
                class="flex-grow-1"
                :disabled="authorizing"
                aria-label="Deny authorization and return to the application"
                @click="handleDeny"
              >
                Deny
              </v-btn>
              <v-btn
                color="primary"
                size="large"
                class="flex-grow-1"
                :loading="authorizing"
                :disabled="authorizing"
                aria-label="Authorize this application to access your account"
                @click="handleAuthorize"
              >
                <v-icon v-if="!authorizing" start>mdi-check</v-icon>
                {{ authorizing ? 'Authorizing...' : 'Authorize' }}
              </v-btn>
            </div>
          </v-card-text>

          <v-divider />

          <!-- Footer -->
          <v-card-text class="text-center pa-4">
            <p class="text-caption oauth-text-muted">
              <v-icon size="small" class="mr-1">mdi-shield-lock</v-icon>
              You will be redirected back to the application after authorization
            </p>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import AppAlert from '@/components/ui/AppAlert.vue'
import { apiClient } from '@/services/api'

const route = useRoute()
const userStore = useUserStore()

// Login state
const username = ref('')
const password = ref('')
const showPassword = ref(false)
const loading = ref(false)
const loginForm = ref(null)

// Consent state
const authorizing = ref(false)
const error = ref('')

// Validation rules
const rules = {
  required: (value) => !!value || 'This field is required',
}

// OAuth parameters from URL query
const oauthParams = computed(() => ({
  client_id: route.query.client_id || '',
  redirect_uri: route.query.redirect_uri || '',
  response_type: route.query.response_type || '',
  code_challenge: route.query.code_challenge || '',
  code_challenge_method: route.query.code_challenge_method || '',
  scope: route.query.scope || '',
  state: route.query.state || '',
}))

// Check if required OAuth parameters are present
const missingParams = computed(() => {
  const params = oauthParams.value
  return !params.client_id || !params.redirect_uri || !params.response_type
})

// Auth state
const isAuthenticated = computed(() => userStore.isAuthenticated)
const currentUser = computed(() => userStore.currentUser)

// Map client_id to a human-readable display name
const clientDisplayName = computed(() => {
  const clientId = oauthParams.value.client_id
  const knownClients = {
    'giljo-mcp-default': 'GiljoAI MCP Client',
    'claude-desktop': 'Claude Desktop',
  }
  return knownClients[clientId] || clientId
})

// Map scope strings to descriptive permission entries
const scopeDescriptions = computed(() => {
  const scopeStr = oauthParams.value.scope || 'mcp'
  const scopes = scopeStr.split(' ').filter(Boolean)
  const descriptions = {
    mcp: {
      scope: 'mcp',
      label: 'MCP Tool Access',
      description: 'Execute tools and access resources via the MCP protocol',
      icon: 'mdi-connection',
    },
    read: {
      scope: 'read',
      label: 'Read Access',
      description: 'Read data from your account',
      icon: 'mdi-eye',
    },
    write: {
      scope: 'write',
      label: 'Write Access',
      description: 'Modify data in your account',
      icon: 'mdi-pencil',
    },
  }
  return scopes.map(
    (s) => descriptions[s] || { scope: s, label: s, description: `Access: ${s}`, icon: 'mdi-key' },
  )
})

// Handle login submission
async function handleLogin() {
  const { valid } = await loginForm.value.validate()
  if (!valid) return

  loading.value = true
  error.value = ''

  try {
    const loginSuccess = await userStore.login(username.value, password.value)
    if (!loginSuccess) {
      error.value = 'Invalid username or password.'
    }
  } catch (err) {
    if (err.response?.status === 401) {
      error.value = 'Invalid username or password.'
    } else if (err.response?.status === 429) {
      error.value = 'Too many login attempts. Please try again later.'
    } else if (err.code === 'ERR_NETWORK' || !err.response) {
      error.value = 'Network error. Please check your connection and try again.'
    } else {
      error.value = err.response?.data?.detail || 'Login failed. Please try again.'
    }
    password.value = ''
  } finally {
    loading.value = false
  }
}

// Handle authorize (consent granted)
async function handleAuthorize() {
  authorizing.value = true
  error.value = ''

  try {
    const response = await apiClient.post('/api/oauth/authorize', {
      client_id: oauthParams.value.client_id,
      redirect_uri: oauthParams.value.redirect_uri,
      response_type: oauthParams.value.response_type,
      code_challenge: oauthParams.value.code_challenge,
      code_challenge_method: oauthParams.value.code_challenge_method,
      scope: oauthParams.value.scope,
      state: oauthParams.value.state,
    })

    // Backend returns a redirect URL with the authorization code
    const redirectUrl = response.data?.redirect_uri || response.data?.redirect_url
    if (redirectUrl) {
      window.location.href = redirectUrl
    } else {
      error.value = 'Authorization succeeded but no redirect URL was returned.'
      authorizing.value = false
    }
  } catch (err) {
    authorizing.value = false
    if (err.response?.data?.detail) {
      error.value = err.response.data.detail
    } else if (err.code === 'ERR_NETWORK' || !err.response) {
      error.value = 'Network error. Please check your connection and try again.'
    } else {
      error.value = 'Authorization failed. Please try again.'
    }
  }
}

// Handle deny (consent refused)
function handleDeny() {
  const params = oauthParams.value
  const redirectUri = new URL(params.redirect_uri)
  redirectUri.searchParams.set('error', 'access_denied')
  redirectUri.searchParams.set('error_description', 'The user denied the authorization request')
  if (params.state) {
    redirectUri.searchParams.set('state', params.state)
  }
  window.location.href = redirectUri.toString()
}

// Check auth state on mount
onMounted(async () => {
  if (!userStore.currentUser) {
    try {
      await userStore.fetchCurrentUser()
    } catch {
      // Not authenticated -- will show login form
    }
  }
})
</script>

<style scoped>
.oauth-container {
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

.oauth-card {
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}

/* Dark theme adjustments */
:deep(.v-theme--dark) .oauth-container {
  background: linear-gradient(135deg, rgb(18, 29, 42) 0%, rgb(10, 15, 22) 100%);
}

/* Accessible text colors */
.oauth-text-muted {
  color: #8895a8 !important;
}

/* Accessibility: Focus indicators */
.v-text-field:focus-within {
  outline: 2px solid rgba(var(--v-theme-primary), 0.5);
  outline-offset: 2px;
  border-radius: 4px;
}
</style>
