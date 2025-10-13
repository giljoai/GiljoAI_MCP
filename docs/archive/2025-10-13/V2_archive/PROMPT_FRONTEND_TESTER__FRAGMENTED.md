# Frontend Tester: Login UI & API Key Management

**Mission:** Create login page, update axios for JWT, and build API key management UI

**Duration:** 2-3 days

**Dependencies:** Backend Integration Tester must complete auth endpoints first

---

## Your Mission

You are the Frontend Tester responsible for implementing the complete authentication user interface: login page, API key management, user management (admin), and routing guards.

### What You're Building

- Login page with username/password form
- Axios interceptor for cookie-based authentication
- API key management UI (generate, view, revoke)
- User management UI (admin only)
- Route guards for authentication

### Why This Matters

This UI will:
- Enable users to log in to the dashboard
- Allow users to manage their personal API keys
- Allow admins to create and manage user accounts
- Provide seamless authentication experience

---

## Prerequisites

Before you begin, ensure the Backend Integration Tester has completed:
- ✅ POST /api/auth/login endpoint (returns JWT cookie)
- ✅ GET /api/auth/me endpoint (current user info)
- ✅ API key endpoints (GET/POST/DELETE /api/auth/api-keys)
- ✅ Authentication middleware (JWT validation)

---

## Part 1: Login Page

Location: `frontend/src/views/LoginView.vue` (NEW FILE)

```vue
<template>
  <v-container class="fill-height" fluid>
    <v-row align="center" justify="center">
      <v-col cols="12" sm="8" md="4">
        <v-card elevation="12" class="pa-4">
          <v-card-title class="text-h4 mb-4 text-center">
            Login to GiljoAI MCP
          </v-card-title>

          <v-card-text>
            <v-alert
              v-if="errorMessage"
              type="error"
              variant="tonal"
              class="mb-4"
              closable
              @click:close="errorMessage = ''"
            >
              {{ errorMessage }}
            </v-alert>

            <v-form @submit.prevent="handleLogin">
              <v-text-field
                v-model="username"
                label="Username"
                prepend-inner-icon="mdi-account"
                variant="outlined"
                required
                autofocus
                :disabled="loading"
              />

              <v-text-field
                v-model="password"
                label="Password"
                prepend-inner-icon="mdi-lock"
                type="password"
                variant="outlined"
                required
                :disabled="loading"
              />

              <v-btn
                type="submit"
                color="primary"
                size="large"
                block
                :loading="loading"
                class="mt-4"
              >
                Login
              </v-btn>
            </v-form>
          </v-card-text>

          <v-divider class="my-4" />

          <v-card-text class="text-center text-caption">
            GiljoAI MCP - Multi-Agent Orchestration Platform
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/services/api'

const router = useRouter()
const username = ref('')
const password = ref('')
const loading = ref(false)
const errorMessage = ref('')

const handleLogin = async () => {
  if (!username.value || !password.value) {
    errorMessage.value = 'Please enter username and password'
    return
  }

  loading.value = true
  errorMessage.value = ''

  try {
    const response = await api.post('/auth/login', {
      username: username.value,
      password: password.value
    })

    // JWT token stored in httpOnly cookie automatically
    // Redirect to dashboard
    const redirectTo = router.currentRoute.value.query.redirect || '/dashboard'
    router.push(redirectTo)

  } catch (error) {
    console.error('Login failed:', error)
    errorMessage.value = error.response?.data?.detail || 'Login failed. Please check your credentials.'
  } finally {
    loading.value = false
  }
}
</script>
```

---

## Part 2: Update Axios Interceptor

Location: `frontend/src/services/api.js` (UPDATE EXISTING)

```javascript
import axios from 'axios'
import router from '@/router'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:7272/api',
  withCredentials: true  // CRITICAL: Send cookies with requests
})

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Cookies sent automatically (withCredentials: true)
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor (handle 401 unauthorized)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Check if we're on localhost (skip redirect)
      const isLocalhost = window.location.hostname === 'localhost' ||
                          window.location.hostname === '127.0.0.1'

      if (!isLocalhost) {
        // Redirect to login with return URL
        const currentPath = window.location.pathname
        router.push({
          path: '/login',
          query: { redirect: currentPath }
        })
      }
    }
    return Promise.reject(error)
  }
)

export default api
```

---

## Part 3: API Key Management Component

Location: `frontend/src/components/ApiKeyManager.vue` (NEW FILE)

```vue
<template>
  <v-card>
    <v-card-title>Personal API Keys</v-card-title>

    <v-card-text>
      <v-alert type="info" variant="tonal" class="mb-4">
        Use personal API keys to authenticate MCP tools, CLI scripts, and CI/CD pipelines.
        Each key is tied to your account.
      </v-alert>

      <!-- List of API keys -->
      <v-list v-if="apiKeys.length > 0">
        <v-list-item
          v-for="key in apiKeys"
          :key="key.id"
        >
          <v-list-item-title>{{ key.name || 'Unnamed Key' }}</v-list-item-title>
          <v-list-item-subtitle>
            <div>Prefix: <code>{{ key.key_prefix }}...</code></div>
            <div>Created: {{ formatDate(key.created_at) }}</div>
            <div v-if="key.last_used">Last used: {{ formatDate(key.last_used) }}</div>
          </v-list-item-subtitle>

          <template v-slot:append>
            <v-btn
              icon="mdi-delete"
              variant="text"
              color="error"
              @click="confirmRevoke(key)"
            />
          </template>
        </v-list-item>
      </v-list>

      <v-alert v-else type="info" variant="outlined" class="mb-4">
        No API keys yet. Generate your first key to use with MCP tools.
      </v-alert>

      <!-- Generate new key button -->
      <v-btn
        color="primary"
        prepend-icon="mdi-key-plus"
        @click="showGenerateDialog = true"
      >
        Generate New API Key
      </v-btn>
    </v-card-text>

    <!-- Generate Key Dialog -->
    <v-dialog v-model="showGenerateDialog" max-width="600" persistent>
      <v-card>
        <v-card-title>Generate New API Key</v-card-title>

        <v-card-text>
          <v-text-field
            v-model="newKeyName"
            label="Key Name (optional)"
            hint="e.g., 'Laptop', 'CI/CD Pipeline', 'Work Desktop'"
            persistent-hint
            variant="outlined"
          />
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn @click="showGenerateDialog = false">Cancel</v-btn>
          <v-btn
            color="primary"
            :loading="generating"
            @click="generateKey"
          >
            Generate
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Display Generated Key Dialog -->
    <v-dialog v-model="showKeyDialog" max-width="700" persistent>
      <v-card>
        <v-card-title class="text-h5">Your New API Key</v-card-title>

        <v-card-text>
          <v-alert type="warning" variant="tonal" class="mb-4">
            <strong>Important:</strong> Save this key securely. It won't be shown again!
          </v-alert>

          <v-text-field
            :model-value="generatedKey"
            label="API Key"
            readonly
            variant="outlined"
            class="monospace-font"
            :append-inner-icon="copied ? 'mdi-check' : 'mdi-content-copy'"
            @click:append-inner="copyKey"
          />

          <v-alert type="info" variant="outlined" class="mt-4">
            <div class="text-subtitle-2 mb-2">Use this key in your MCP configuration:</div>
            <pre class="code-block">{{ mcpConfigExample }}</pre>
          </v-alert>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn
            color="primary"
            @click="closeKeyDialog"
          >
            I've Saved It
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Confirm Revoke Dialog -->
    <v-dialog v-model="showRevokeDialog" max-width="500">
      <v-card>
        <v-card-title>Revoke API Key?</v-card-title>

        <v-card-text>
          Are you sure you want to revoke this key?
          <br><br>
          <strong>{{ keyToRevoke?.name || 'Unnamed Key' }}</strong>
          <br>
          <code>{{ keyToRevoke?.key_prefix }}...</code>
          <br><br>
          This action cannot be undone. Any tools using this key will stop working.
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn @click="showRevokeDialog = false">Cancel</v-btn>
          <v-btn
            color="error"
            :loading="revoking"
            @click="revokeKey"
          >
            Revoke
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import api from '@/services/api'

const apiKeys = ref([])
const showGenerateDialog = ref(false)
const showKeyDialog = ref(false)
const showRevokeDialog = ref(false)
const newKeyName = ref('')
const generatedKey = ref('')
const copied = ref(false)
const generating = ref(false)
const revoking = ref(false)
const keyToRevoke = ref(null)

const mcpConfigExample = computed(() => {
  return `{
  "mcpServers": {
    "giljo-mcp": {
      "env": {
        "GILJO_SERVER_URL": "http://your-server:7272",
        "GILJO_API_KEY": "${generatedKey.value}"
      }
    }
  }
}`
})

const formatDate = (dateString) => {
  return new Date(dateString).toLocaleString()
}

const loadApiKeys = async () => {
  try {
    const response = await api.get('/auth/api-keys')
    apiKeys.value = response.data
  } catch (error) {
    console.error('Failed to load API keys:', error)
  }
}

const generateKey = async () => {
  generating.value = true
  try {
    const response = await api.post('/auth/api-keys', {
      name: newKeyName.value || null
    })

    generatedKey.value = response.data.key
    showGenerateDialog.value = false
    showKeyDialog.value = true
    newKeyName.value = ''

    // Reload keys
    await loadApiKeys()

  } catch (error) {
    console.error('Failed to generate API key:', error)
    alert('Failed to generate API key: ' + error.message)
  } finally {
    generating.value = false
  }
}

const copyKey = async () => {
  try {
    await navigator.clipboard.writeText(generatedKey.value)
    copied.value = true
    setTimeout(() => { copied.value = false }, 3000)
  } catch (error) {
    console.error('Failed to copy:', error)
  }
}

const closeKeyDialog = () => {
  showKeyDialog.value = false
  generatedKey.value = ''
  copied.value = false
}

const confirmRevoke = (key) => {
  keyToRevoke.value = key
  showRevokeDialog.value = true
}

const revokeKey = async () => {
  revoking.value = true
  try {
    await api.delete(`/auth/api-keys/${keyToRevoke.value.id}`)
    showRevokeDialog.value = false
    keyToRevoke.value = null

    // Reload keys
    await loadApiKeys()

  } catch (error) {
    console.error('Failed to revoke key:', error)
    alert('Failed to revoke key: ' + error.message)
  } finally {
    revoking.value = false
  }
}

onMounted(() => {
  loadApiKeys()
})
</script>

<style scoped>
.monospace-font {
  font-family: 'Courier New', Courier, monospace;
}
.code-block {
  background-color: #f5f5f5;
  padding: 12px;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 12px;
}
</style>
```

---

## Part 4: User Management (Admin Only)

Location: `frontend/src/views/UserManagementView.vue` (NEW FILE)

```vue
<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title class="d-flex align-center">
            User Management
            <v-spacer />
            <v-btn
              color="primary"
              prepend-icon="mdi-account-plus"
              @click="showAddDialog = true"
            >
              Add New User
            </v-btn>
          </v-card-title>

          <v-card-text>
            <v-data-table
              :headers="headers"
              :items="users"
              :loading="loading"
            >
              <template v-slot:item.role="{ item }">
                <v-chip :color="getRoleColor(item.role)" size="small">
                  {{ item.role }}
                </v-chip>
              </template>

              <template v-slot:item.is_active="{ item }">
                <v-chip :color="item.is_active ? 'success' : 'error'" size="small">
                  {{ item.is_active ? 'Active' : 'Inactive' }}
                </v-chip>
              </template>

              <template v-slot:item.created_at="{ item }">
                {{ formatDate(item.created_at) }}
              </template>

              <template v-slot:item.actions="{ item }">
                <v-btn
                  icon="mdi-pencil"
                  variant="text"
                  size="small"
                  @click="editUser(item)"
                />
                <v-btn
                  icon="mdi-delete"
                  variant="text"
                  size="small"
                  color="error"
                  @click="confirmDelete(item)"
                />
              </template>
            </v-data-table>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Add User Dialog -->
    <v-dialog v-model="showAddDialog" max-width="600">
      <v-card>
        <v-card-title>Add New User</v-card-title>

        <v-card-text>
          <v-form @submit.prevent="createUser">
            <v-text-field
              v-model="newUser.username"
              label="Username"
              required
              variant="outlined"
            />

            <v-text-field
              v-model="newUser.email"
              label="Email"
              type="email"
              variant="outlined"
            />

            <v-text-field
              v-model="newUser.password"
              label="Password"
              type="password"
              required
              variant="outlined"
              hint="Minimum 12 characters, uppercase, lowercase, number, special character"
            />

            <v-select
              v-model="newUser.role"
              label="Role"
              :items="['admin', 'developer', 'viewer']"
              required
              variant="outlined"
            />
          </v-form>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn @click="showAddDialog = false">Cancel</v-btn>
          <v-btn
            color="primary"
            :loading="creating"
            @click="createUser"
          >
            Create User
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/services/api'

const users = ref([])
const loading = ref(false)
const showAddDialog = ref(false)
const creating = ref(false)

const newUser = ref({
  username: '',
  email: '',
  password: '',
  role: 'developer'
})

const headers = [
  { title: 'Username', key: 'username' },
  { title: 'Email', key: 'email' },
  { title: 'Role', key: 'role' },
  { title: 'Status', key: 'is_active' },
  { title: 'Created', key: 'created_at' },
  { title: 'Actions', key: 'actions', sortable: false }
]

const formatDate = (dateString) => {
  return new Date(dateString).toLocaleString()
}

const getRoleColor = (role) => {
  const colors = {
    admin: 'error',
    developer: 'primary',
    viewer: 'info'
  }
  return colors[role] || 'default'
}

const loadUsers = async () => {
  loading.value = true
  try {
    const response = await api.get('/auth/users')  // Assumes endpoint exists
    users.value = response.data
  } catch (error) {
    console.error('Failed to load users:', error)
  } finally {
    loading.value = false
  }
}

const createUser = async () => {
  creating.value = true
  try {
    await api.post('/auth/register', newUser.value)
    showAddDialog.value = false
    newUser.value = {
      username: '',
      email: '',
      password: '',
      role: 'developer'
    }
    await loadUsers()
  } catch (error) {
    console.error('Failed to create user:', error)
    alert('Failed to create user: ' + (error.response?.data?.detail || error.message))
  } finally {
    creating.value = false
  }
}

onMounted(() => {
  loadUsers()
})
</script>
```

---

## Part 5: Route Guards

Location: `frontend/src/router/index.js` (UPDATE EXISTING)

```javascript
import { createRouter, createWebHistory } from 'vue-router'
import api from '@/services/api'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/LoginView.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/dashboard',
      name: 'Dashboard',
      component: () => import('@/views/DashboardView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/settings',
      name: 'Settings',
      component: () => import('@/views/SettingsView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/users',
      name: 'Users',
      component: () => import('@/views/UserManagementView.vue'),
      meta: { requiresAuth: true, requiresAdmin: true }
    },
    // ... other routes
  ]
})

// Check if running on localhost
function isLocalhost() {
  return window.location.hostname === 'localhost' ||
         window.location.hostname === '127.0.0.1'
}

// Check if user is authenticated
async function isAuthenticated() {
  try {
    const response = await api.get('/auth/me')
    return response.data
  } catch (error) {
    return null
  }
}

// Global navigation guard
router.beforeEach(async (to, from, next) => {
  // Skip auth for localhost
  if (isLocalhost()) {
    next()
    return
  }

  // Skip auth check if route doesn't require it
  if (!to.meta.requiresAuth) {
    next()
    return
  }

  // Check authentication
  const user = await isAuthenticated()

  if (!user) {
    // Not authenticated, redirect to login
    next({
      path: '/login',
      query: { redirect: to.fullPath }
    })
    return
  }

  // Check admin permission if required
  if (to.meta.requiresAdmin && user.role !== 'admin') {
    // Not authorized
    next({ path: '/dashboard' })
    return
  }

  // Authenticated and authorized
  next()
})

export default router
```

---

## Part 6: Update Settings View

Location: `frontend/src/views/SettingsView.vue` (UPDATE EXISTING)

Add API Keys tab:

```vue
<template>
  <v-container>
    <v-tabs v-model="tab">
      <v-tab value="general">General</v-tab>
      <v-tab value="api-keys">API Keys</v-tab>
      <v-tab value="database">Database</v-tab>
    </v-tabs>

    <v-window v-model="tab" class="mt-4">
      <v-window-item value="general">
        <!-- Existing general settings -->
      </v-window-item>

      <v-window-item value="api-keys">
        <ApiKeyManager />
      </v-window-item>

      <v-window-item value="database">
        <!-- Existing database settings -->
      </v-window-item>
    </v-window>
  </v-container>
</template>

<script setup>
import { ref } from 'vue'
import ApiKeyManager from '@/components/ApiKeyManager.vue'

const tab = ref('general')
</script>
```

---

## Acceptance Criteria

Before marking complete, verify:

- [ ] Login page works (correct credentials → dashboard)
- [ ] Invalid credentials show error message
- [ ] JWT stored in httpOnly cookie (not accessible via JS)
- [ ] 401 errors redirect to login page
- [ ] Localhost mode bypasses login (auto-redirect to dashboard)
- [ ] API key management UI works (generate, view, revoke)
- [ ] Generated key shown ONCE with copy button
- [ ] User management UI works (admin only)
- [ ] Admin can create users with username/email/password
- [ ] Route guards enforce authentication
- [ ] Admin-only routes protected
- [ ] All components responsive (mobile-friendly)
- [ ] Accessibility (WCAG 2.1 AA)

---

## Files to Create/Modify

**New Files:**
- `frontend/src/views/LoginView.vue` (login page)
- `frontend/src/components/ApiKeyManager.vue` (API key management)
- `frontend/src/views/UserManagementView.vue` (user management, admin only)

**Modified Files:**
- `frontend/src/services/api.js` (update interceptor for cookies + 401 handling)
- `frontend/src/router/index.js` (add route guards)
- `frontend/src/views/SettingsView.vue` (add API Keys tab)

---

## Handoff Information

When complete, hand off to **Documentation Manager** with:

**UI Complete:**
- Login page at /login
- API key management in Settings → API Keys
- User management in /users (admin only)
- Route guards protecting authenticated routes

**Testing Ready:**
- E2E auth flow testable (register → login → dashboard)
- API key generation testable (generate → copy → use in MCP)
- User management testable (create → edit → delete)

**Documentation Needed:**
- User guide for login and API key generation
- Admin guide for user management
- Troubleshooting section (forgot password, lost API key)

---

Good luck building the authentication UI! 🎨
