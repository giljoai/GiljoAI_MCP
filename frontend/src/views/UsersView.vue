<template>
  <v-container>
    <div class="d-flex justify-space-between align-center mb-6">
      <h1 class="text-h4">User Management</h1>
      <v-btn color="primary" @click="showCreateDialog = true" aria-label="Create new user">
        <v-icon start>mdi-account-plus</v-icon>
        Create User
      </v-btn>
    </div>

    <v-alert v-if="!userStore.isAdmin" type="error" variant="tonal" class="mb-4">
      <v-icon start>mdi-lock</v-icon>
      Access Denied: This page is only accessible to administrators.
    </v-alert>

    <v-card v-else>
      <v-card-title>
        <v-text-field
          v-model="search"
          prepend-inner-icon="mdi-magnify"
          label="Search users"
          single-line
          hide-details
          variant="outlined"
          density="compact"
          class="mb-4"
        />
      </v-card-title>

      <v-data-table
        :headers="headers"
        :items="users"
        :search="search"
        :loading="loading"
        item-value="id"
        class="elevation-1"
      >
        <template v-slot:item.role="{ item }">
          <v-chip :color="getRoleColor(item.role)" size="small">
            {{ item.role }}
          </v-chip>
        </template>

        <template v-slot:item.created_at="{ item }">
          {{ formatDate(item.created_at) }}
        </template>

        <template v-slot:item.actions="{ item }">
          <v-btn
            icon="mdi-pencil"
            size="small"
            variant="text"
            @click="editUser(item)"
            title="Edit user"
          />
          <v-btn
            icon="mdi-delete"
            size="small"
            variant="text"
            color="error"
            @click="confirmDelete(item)"
            title="Delete user"
            :disabled="item.username === userStore.currentUser?.username"
          />
        </template>
      </v-data-table>
    </v-card>

    <!-- Create/Edit User Dialog -->
    <v-dialog v-model="showCreateDialog" max-width="500px">
      <v-card>
        <v-card-title>
          <span class="text-h5">{{ editingUser ? 'Edit User' : 'Create New User' }}</span>
        </v-card-title>

        <v-card-text>
          <v-form ref="userForm">
            <v-text-field
              v-model="formData.username"
              label="Username"
              variant="outlined"
              :rules="[rules.required]"
              required
            />

            <v-text-field
              v-model="formData.email"
              label="Email"
              type="email"
              variant="outlined"
              :rules="[rules.required, rules.email]"
              required
              class="mt-4"
            />

            <v-text-field
              v-if="!editingUser"
              v-model="formData.password"
              label="Password"
              type="password"
              variant="outlined"
              :rules="[rules.required, rules.minLength]"
              required
              class="mt-4"
            />

            <v-select
              v-model="formData.role"
              :items="roleOptions"
              label="Role"
              variant="outlined"
              :rules="[rules.required]"
              required
              class="mt-4"
            />
          </v-form>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="closeDialog">Cancel</v-btn>
          <v-btn color="primary" variant="flat" @click="saveUser">
            {{ editingUser ? 'Update' : 'Create' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation Dialog -->
    <BaseDialog
      v-model="showDeleteDialog"
      type="danger"
      title="Delete User"
      confirm-label="Delete"
      size="sm"
      @confirm="deleteUser"
      @cancel="showDeleteDialog = false"
    >
      <p class="text-body-1 mb-2">
        Are you sure you want to delete user <strong>{{ userToDelete?.username }}</strong>?
      </p>
      <v-alert type="info" variant="tonal" density="compact">
        This action cannot be undone.
      </v-alert>
    </BaseDialog>
  </v-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import api from '@/services/api'
import BaseDialog from '@/components/common/BaseDialog.vue'

const userStore = useUserStore()

// State
const users = ref([])
const search = ref('')
const loading = ref(false)
const showCreateDialog = ref(false)
const showDeleteDialog = ref(false)
const editingUser = ref(null)
const userToDelete = ref(null)
const userForm = ref(null)

const formData = ref({
  username: '',
  email: '',
  password: '',
  role: 'user',
})

// Table headers
const headers = [
  { title: 'Username', key: 'username', sortable: true },
  { title: 'Email', key: 'email', sortable: true },
  { title: 'Role', key: 'role', sortable: true },
  { title: 'Created', key: 'created_at', sortable: true },
  { title: 'Actions', key: 'actions', sortable: false },
]

const roleOptions = ['admin', 'user']

// Validation rules
const rules = {
  required: (value) => !!value || 'This field is required',
  email: (value) => {
    const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    return pattern.test(value) || 'Invalid email address'
  },
  minLength: (value) => (value && value.length >= 8) || 'Password must be at least 8 characters',
}

// Methods
function getRoleColor(role) {
  return role === 'admin' ? 'primary' : 'secondary'
}

function formatDate(dateString) {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString()
}

function editUser(user) {
  editingUser.value = user
  formData.value = {
    username: user.username,
    email: user.email,
    role: user.role,
    password: '', // Don't populate password for edit
  }
  showCreateDialog.value = true
}

function confirmDelete(user) {
  userToDelete.value = user
  showDeleteDialog.value = true
}

function closeDialog() {
  showCreateDialog.value = false
  editingUser.value = null
  formData.value = {
    username: '',
    email: '',
    password: '',
    role: 'user',
  }
  if (userForm.value) {
    userForm.value.reset()
  }
}

async function saveUser() {
  const { valid } = await userForm.value.validate()
  if (!valid) return

  try {
    if (editingUser.value) {
      // Update existing user
      await api.auth.updateUser(editingUser.value.id, formData.value)
      console.log('[USERS] User updated successfully')
    } else {
      // Create new user
      await api.auth.register(formData.value)
      console.log('[USERS] User created successfully')
    }

    await loadUsers()
    closeDialog()
  } catch (error) {
    console.error('[USERS] Failed to save user:', error)
  }
}

async function deleteUser() {
  try {
    await api.auth.deleteUser(userToDelete.value.id)
    console.log('[USERS] User deleted successfully')
    await loadUsers()
    showDeleteDialog.value = false
    userToDelete.value = null
  } catch (error) {
    console.error('[USERS] Failed to delete user:', error)
  }
}

async function loadUsers() {
  loading.value = true
  try {
    const response = await api.auth.listUsers()
    users.value = response.data
    console.log('[USERS] Loaded', users.value.length, 'users')
  } catch (error) {
    console.error('[USERS] Failed to load users:', error)
    users.value = []
  } finally {
    loading.value = false
  }
}

// Lifecycle
onMounted(async () => {
  // Only load users if admin
  if (userStore.isAdmin) {
    await loadUsers()
  }
})
</script>

<style scoped>
/* Add any custom styles here */
</style>
