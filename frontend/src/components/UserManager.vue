<template>
  <v-container fluid>
    <!-- Header with search and add button -->
    <v-row class="mb-4">
      <v-col cols="12" md="8">
        <v-text-field
          v-model="search"
          prepend-inner-icon="mdi-magnify"
          label="Search users"
          variant="outlined"
          density="comfortable"
          clearable
          hide-details
        />
      </v-col>
      <v-col cols="12" md="4" class="d-flex justify-end">
        <v-btn
          color="primary"
          @click="openCreateDialog"
          :disabled="loading"
          prepend-icon="mdi-account-plus"
        >
          Add User
        </v-btn>
      </v-col>
    </v-row>

    <!-- User table -->
    <v-data-table
      :headers="headers"
      :items="filteredUsers"
      :loading="loading"
      :search="search"
      class="elevation-1"
    >
      <!-- Username column with icon -->
      <template #item.username="{ item }">
        <div class="d-flex align-center">
          <v-icon size="small" class="mr-2">mdi-account</v-icon>
          <span class="font-weight-medium">{{ item.username }}</span>
        </div>
      </template>

      <!-- Email column -->
      <template #item.email="{ item }">
        <div class="d-flex align-center">
          <v-icon size="small" class="mr-2 text-medium-emphasis">mdi-email</v-icon>
          <span class="text-caption">{{ item.email || 'No email' }}</span>
        </div>
      </template>

      <!-- Role badge column -->
      <template #item.role="{ item }">
        <v-chip :color="getRoleColor(item.role)" size="small" label>
          <v-icon start size="small">{{ getRoleIcon(item.role) }}</v-icon>
          {{ getRoleTitle(item.role) }}
        </v-chip>
      </template>

      <!-- Status badge column -->
      <template #item.is_active="{ item }">
        <v-chip :color="item.is_active ? 'success' : 'default'" size="small" label>
          <v-icon start size="small">
            {{ item.is_active ? 'mdi-check-circle' : 'mdi-cancel' }}
          </v-icon>
          {{ item.is_active ? 'Active' : 'Inactive' }}
        </v-chip>
      </template>

      <!-- Created date column -->
      <template #item.created_at="{ item }">
        <div class="d-flex align-center">
          <v-icon size="small" class="mr-2 text-medium-emphasis">mdi-calendar-plus</v-icon>
          <span class="text-caption">{{ formatDate(item.created_at) }}</span>
        </div>
      </template>

      <!-- Last login column -->
      <template #item.last_login="{ item }">
        <span class="text-caption">{{ formatRelativeTime(item.last_login) }}</span>
      </template>

      <!-- Actions column -->
      <template #item.actions="{ item }">
        <v-menu>
          <template v-slot:activator="{ props }">
            <v-btn icon="mdi-dots-vertical" size="small" variant="text" v-bind="props" />
          </template>
          <v-list density="compact">
            <v-list-item @click="openEditDialog(item)">
              <template v-slot:prepend>
                <v-icon>mdi-pencil</v-icon>
              </template>
              <v-list-item-title>Edit User</v-list-item-title>
            </v-list-item>
            <v-list-item @click="openPasswordDialog(item)">
              <template v-slot:prepend>
                <v-icon>mdi-key-variant</v-icon>
              </template>
              <v-list-item-title>Change Password</v-list-item-title>
            </v-list-item>
            <v-list-item @click="openResetPasswordDialog(item)">
              <template v-slot:prepend>
                <v-icon>mdi-lock-reset</v-icon>
              </template>
              <v-list-item-title>Reset Password</v-list-item-title>
            </v-list-item>
            <v-divider />
            <v-list-item @click="toggleUserStatus(item)" :disabled="item.id === currentUser?.id">
              <template v-slot:prepend>
                <v-icon>{{ item.is_active ? 'mdi-account-off' : 'mdi-account-check' }}</v-icon>
              </template>
              <v-list-item-title>
                {{ item.is_active ? 'Deactivate' : 'Activate' }}
              </v-list-item-title>
            </v-list-item>
          </v-list>
        </v-menu>
      </template>
    </v-data-table>

    <!-- Create/Edit User Dialog -->
    <v-dialog v-model="showUserDialog" max-width="600">
      <v-card>
        <v-card-title>
          <v-icon class="mr-2">{{ isEditMode ? 'mdi-pencil' : 'mdi-account-plus' }}</v-icon>
          {{ isEditMode ? 'Edit User' : 'Create New User' }}
        </v-card-title>

        <v-card-text>
          <v-form ref="formRef" @submit.prevent="saveUser">
            <v-text-field
              v-model="userForm.username"
              label="Username"
              variant="outlined"
              :rules="[rules.required]"
              :disabled="isEditMode"
              required
              class="mb-3"
            />

            <v-text-field
              v-model="userForm.email"
              label="Email"
              variant="outlined"
              type="email"
              :rules="[rules.email]"
              class="mb-3"
            />

            <v-text-field
              v-if="!isEditMode"
              v-model="userForm.password"
              label="Password"
              variant="outlined"
              type="password"
              :rules="[rules.required, rules.minLength]"
              hint="Min 8 characters"
              persistent-hint
              required
              class="mb-3"
            />

            <v-select
              v-model="userForm.role"
              label="Role"
              variant="outlined"
              :items="roleOptions"
              item-value="value"
              item-title="title"
              :rules="[rules.required]"
              required
              class="mb-3"
            />

            <v-switch
              v-if="isEditMode"
              v-model="userForm.is_active"
              label="Active"
              color="success"
              :disabled="userForm.id === currentUser?.id"
            />
          </v-form>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="closeUserDialog" :disabled="saving"> Cancel </v-btn>
          <v-btn color="primary" @click="saveUser" :loading="saving">
            {{ isEditMode ? 'Update' : 'Create' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Change Password Dialog -->
    <v-dialog v-model="showPasswordDialog" max-width="500">
      <v-card>
        <v-card-title>
          <v-icon class="mr-2">mdi-key-variant</v-icon>
          Change Password
        </v-card-title>

        <v-card-text>
          <v-alert type="info" variant="tonal" density="compact" class="mb-4">
            Changing password for: <strong>{{ passwordUser?.username }}</strong>
          </v-alert>

          <v-text-field
            v-model="newPassword"
            label="New Password"
            variant="outlined"
            type="password"
            :rules="[rules.required, rules.minLength]"
            required
          />
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="closePasswordDialog" :disabled="changingPassword">
            Cancel
          </v-btn>
          <v-btn color="primary" @click="changePassword" :loading="changingPassword">
            Change Password
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Reset Password Confirmation Dialog -->
    <v-dialog v-model="showResetPasswordDialog" max-width="500">
      <v-card>
        <v-card-title class="bg-warning">
          <v-icon class="mr-2">mdi-lock-reset</v-icon>
          Reset User Password?
        </v-card-title>

        <v-card-text class="pt-6">
          <p class="text-body-1 mb-2">You are about to reset the password for:</p>
          <v-card variant="outlined" class="mb-4 pa-3">
            <div class="d-flex align-center">
              <v-icon class="mr-2">mdi-account</v-icon>
              <strong>{{ resetPasswordUser?.username }}</strong>
            </div>
            <div class="d-flex align-center mt-2">
              <v-icon class="mr-2" size="small">{{ getRoleIcon(resetPasswordUser?.role) }}</v-icon>
              <span class="text-caption">{{ getRoleTitle(resetPasswordUser?.role) }}</span>
            </div>
          </v-card>

          <v-alert type="warning" variant="tonal" density="compact" class="mb-2">
            <strong>Password will be reset to:</strong> <code>GiljoMCP</code>
          </v-alert>

          <v-alert type="info" variant="tonal" density="compact">
            The user will be required to change this password on their next login. Their recovery
            PIN will remain unchanged.
          </v-alert>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="closeResetPasswordDialog" :disabled="resettingPassword">
            Cancel
          </v-btn>
          <v-btn color="warning" @click="confirmResetPassword" :loading="resettingPassword">
            Reset Password
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Status Toggle Confirmation Dialog -->
    <v-dialog v-model="showStatusDialog" max-width="500">
      <v-card>
        <v-card-title :class="statusUser?.is_active ? 'bg-warning' : 'bg-success'">
          <v-icon class="mr-2">
            {{ statusUser?.is_active ? 'mdi-account-off' : 'mdi-account-check' }}
          </v-icon>
          {{ statusUser?.is_active ? 'Deactivate' : 'Activate' }} User?
        </v-card-title>

        <v-card-text class="pt-6">
          <p class="text-body-1 mb-2">
            You are about to {{ statusUser?.is_active ? 'deactivate' : 'activate' }}:
          </p>
          <v-card variant="outlined" class="mb-4 pa-3">
            <div class="d-flex align-center">
              <v-icon class="mr-2">mdi-account</v-icon>
              <strong>{{ statusUser?.username }}</strong>
            </div>
            <div class="d-flex align-center mt-2">
              <v-icon class="mr-2" size="small">{{ getRoleIcon(statusUser?.role) }}</v-icon>
              <span class="text-caption">{{ getRoleTitle(statusUser?.role) }}</span>
            </div>
          </v-card>

          <v-alert v-if="statusUser?.is_active" type="warning" variant="tonal" density="compact">
            This user will no longer be able to log in to the system.
          </v-alert>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="closeStatusDialog" :disabled="togglingStatus">
            Cancel
          </v-btn>
          <v-btn
            :color="statusUser?.is_active ? 'warning' : 'success'"
            @click="confirmToggleStatus"
            :loading="togglingStatus"
          >
            {{ statusUser?.is_active ? 'Deactivate' : 'Activate' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Snackbar for notifications -->
    <v-snackbar
      v-model="snackbar.show"
      :color="snackbar.color"
      :timeout="5000"
      location="top"
    >
      {{ snackbar.message }}
      <template v-slot:actions>
        <v-btn variant="text" @click="snackbar.show = false">Close</v-btn>
      </template>
    </v-snackbar>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { formatDistanceToNow } from 'date-fns'
import api from '@/services/api'
import { useUserStore } from '@/stores/user'

// Store
const userStore = useUserStore()
const currentUser = computed(() => userStore.currentUser)

// Snackbar state
const snackbar = ref({
  show: false,
  message: '',
  color: 'error',
})

// State
const users = ref([])
const loading = ref(false)
const search = ref('')

// Template refs
const formRef = ref(null)

// Dialog state
const showUserDialog = ref(false)
const showPasswordDialog = ref(false)
const showResetPasswordDialog = ref(false)
const showStatusDialog = ref(false)
const isEditMode = ref(false)
const saving = ref(false)
const changingPassword = ref(false)
const resettingPassword = ref(false)
const togglingStatus = ref(false)

// Form data
const userForm = ref({
  id: null,
  username: '',
  email: '',
  password: '',
  role: 'developer',
  is_active: true,
})

const passwordUser = ref(null)
const newPassword = ref('')
const resetPasswordUser = ref(null)
const statusUser = ref(null)

// Table configuration
const headers = [
  { title: 'Username', key: 'username', sortable: true },
  { title: 'Email', key: 'email', sortable: true },
  { title: 'Role', key: 'role', sortable: true },
  { title: 'Status', key: 'is_active', sortable: true },
  { title: 'Created', key: 'created_at', sortable: true },
  { title: 'Last Login', key: 'last_login', sortable: true },
  { title: 'Actions', key: 'actions', sortable: false, align: 'end' },
]

// Role configuration
const roleOptions = [
  {
    value: 'admin',
    title: 'Administrator',
    color: 'error',
    icon: 'mdi-shield-crown',
  },
  {
    value: 'developer',
    title: 'Developer',
    color: 'primary',
    icon: 'mdi-code-tags',
  },
  {
    value: 'viewer',
    title: 'Viewer',
    color: 'info',
    icon: 'mdi-eye',
  },
]

// Form validation rules
const rules = {
  required: (value) => !!value || 'This field is required',
  minLength: (value) => !value || value.length >= 8 || 'Password must be at least 8 characters',
  email: (value) =>
    !value || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value) || 'Must be a valid email address',
}

// Computed
const filteredUsers = computed(() => {
  if (!search.value) return users.value
  const searchLower = search.value.toLowerCase()
  return users.value.filter(
    (user) =>
      user.username.toLowerCase().includes(searchLower) ||
      (user.email && user.email.toLowerCase().includes(searchLower)),
  )
})

// Methods
function getRoleColor(role) {
  const roleConfig = roleOptions.find((r) => r.value === role)
  return roleConfig?.color || 'default'
}

function getRoleIcon(role) {
  const roleConfig = roleOptions.find((r) => r.value === role)
  return roleConfig?.icon || 'mdi-account'
}

function getRoleTitle(role) {
  const roleConfig = roleOptions.find((r) => r.value === role)
  return roleConfig?.title || role
}

function formatRelativeTime(timestamp) {
  if (!timestamp) return 'Never'
  try {
    return formatDistanceToNow(new Date(timestamp), { addSuffix: true })
  } catch (err) {
    return 'Unknown'
  }
}

function formatDate(dateString) {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  return date.toLocaleDateString()
}

async function loadUsers() {
  loading.value = true
  try {
    const response = await api.auth.listUsers()
    users.value = response.data
    console.log('[UserManager] Loaded', users.value.length, 'users')
  } catch (err) {
    console.error('[UserManager] Failed to load users:', err)
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  isEditMode.value = false
  userForm.value = {
    id: null,
    username: '',
    email: '',
    password: '',
    role: 'developer',
    is_active: true,
  }
  showUserDialog.value = true
}

function openEditDialog(user) {
  isEditMode.value = true
  userForm.value = {
    id: user.id,
    username: user.username,
    email: user.email || '',
    password: '',
    role: user.role,
    is_active: user.is_active,
  }
  showUserDialog.value = true
}

function closeUserDialog() {
  showUserDialog.value = false
  userForm.value = {
    id: null,
    username: '',
    email: '',
    password: '',
    role: 'developer',
    is_active: true,
  }
}

async function saveUser() {
  saving.value = true
  try {
    if (isEditMode.value) {
      // Update existing user
      await api.auth.updateUser(userForm.value.id, {
        email: userForm.value.email,
        role: userForm.value.role,
        is_active: userForm.value.is_active,
      })
      console.log('[UserManager] Updated user:', userForm.value.username)
    } else {
      // Create new user
      await api.auth.register({
        username: userForm.value.username,
        email: userForm.value.email,
        password: userForm.value.password,
        role: userForm.value.role,
      })
      console.log('[UserManager] Created user:', userForm.value.username)
    }

    // Reload users list
    await loadUsers()
    closeUserDialog()
  } catch (err) {
    console.error('[UserManager] Failed to save user:', err)
    // Extract error message from response
    const errorMessage = err.response?.data?.detail || err.message || 'Failed to save user'
    // Show user-friendly message
    if (errorMessage.toLowerCase().includes('already exists')) {
      snackbar.value = {
        show: true,
        message: 'Username or email already exists. Please use different values.',
        color: 'warning',
      }
    } else {
      snackbar.value = {
        show: true,
        message: errorMessage,
        color: 'error',
      }
    }
  } finally {
    saving.value = false
  }
}

function openPasswordDialog(user) {
  passwordUser.value = user
  newPassword.value = ''
  showPasswordDialog.value = true
}

function closePasswordDialog() {
  showPasswordDialog.value = false
  passwordUser.value = null
  newPassword.value = ''
}

async function changePassword() {
  if (!passwordUser.value || !newPassword.value) return

  changingPassword.value = true
  try {
    await api.auth.updateUser(passwordUser.value.id, {
      password: newPassword.value,
    })
    console.log('[UserManager] Changed password for:', passwordUser.value.username)
    closePasswordDialog()
  } catch (err) {
    console.error('[UserManager] Failed to change password:', err)
  } finally {
    changingPassword.value = false
  }
}

function openResetPasswordDialog(user) {
  resetPasswordUser.value = user
  showResetPasswordDialog.value = true
}

function closeResetPasswordDialog() {
  showResetPasswordDialog.value = false
  resetPasswordUser.value = null
}

async function confirmResetPassword() {
  if (!resetPasswordUser.value) return

  resettingPassword.value = true
  try {
    await api.auth.resetUserPassword(resetPasswordUser.value.id)
    console.log('[UserManager] Reset password for:', resetPasswordUser.value.username)

    // Reload users list
    await loadUsers()
    closeResetPasswordDialog()

    // Show success message (you can add a snackbar component if needed)
    console.log('[UserManager] Password reset successfully to GiljoMCP')
  } catch (err) {
    console.error('[UserManager] Failed to reset password:', err)
  } finally {
    resettingPassword.value = false
  }
}

function toggleUserStatus(user) {
  statusUser.value = user
  showStatusDialog.value = true
}

function closeStatusDialog() {
  showStatusDialog.value = false
  statusUser.value = null
}

async function confirmToggleStatus() {
  if (!statusUser.value) return

  togglingStatus.value = true
  try {
    await api.auth.updateUser(statusUser.value.id, {
      is_active: !statusUser.value.is_active,
    })
    console.log(
      '[UserManager]',
      statusUser.value.is_active ? 'Deactivated' : 'Activated',
      statusUser.value.username,
    )

    // Reload users list
    await loadUsers()
    closeStatusDialog()
  } catch (err) {
    console.error('[UserManager] Failed to toggle user status:', err)
  } finally {
    togglingStatus.value = false
  }
}

// Lifecycle
onMounted(() => {
  loadUsers()
})
</script>

<style scoped>
.v-data-table {
  border-radius: 8px;
}

/* Accessibility: Focus indicators */
.v-btn:focus-visible {
  outline: 2px solid rgba(var(--v-theme-primary), 0.5);
  outline-offset: 2px;
}
</style>
