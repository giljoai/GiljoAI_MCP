<template>
  <v-card variant="flat" class="smooth-border profile-card">
    <v-card-text class="pa-5">
      <div v-if="!user" class="text-body-2 text-muted-a11y">
        Sign in to view your profile.
      </div>

      <v-form v-else ref="formRef">
        <v-text-field
          v-model="form.username"
          label="Username"
          variant="outlined"
          density="comfortable"
          disabled
          class="mb-3"
        />

        <!-- Workspace/Organization + Role (read-only) - Handover 0424o, 0875 -->
        <div class="mb-4 pa-4 bg-surface-variant rounded">
          <div v-if="userStore.currentOrg" class="d-flex align-center mb-3">
            <v-icon size="small" color="primary" class="mr-2">mdi-office-building</v-icon>
            <div class="text-caption text-muted-a11y mr-2">Workspace</div>
            <span class="font-weight-medium">{{ userStore.currentOrg.name }}</span>
            <v-spacer />
            <RoleBadge v-if="userStore.orgRole" :role="userStore.orgRole" size="small" />
          </div>
          <div v-if="user.role" class="d-flex align-center">
            <v-icon size="small" color="primary" class="mr-2">mdi-shield-account</v-icon>
            <div class="text-caption text-muted-a11y mr-2">Role</div>
            <v-spacer />
            <RoleBadge :role="user.role" size="small" />
          </div>
        </div>

        <v-text-field
          v-model="form.full_name"
          label="Full Name"
          variant="outlined"
          density="comfortable"
          class="mb-3"
        />
        <v-text-field
          v-model="form.email"
          label="Email"
          type="email"
          variant="outlined"
          density="comfortable"
        />

        <v-alert v-if="error" type="error" variant="tonal" density="compact" class="mt-3">
          {{ error }}
        </v-alert>

        <div class="profile-actions mt-4">
          <v-btn variant="text" :disabled="saving" @click="reset">Reset</v-btn>
          <v-btn
            color="primary"
            variant="flat"
            :loading="saving"
            :disabled="saving"
            data-test="save-profile-btn"
            @click="save"
          >
            Save Changes
          </v-btn>
        </div>
      </v-form>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useUserStore } from '@/stores/user'
import { useToast } from '@/composables/useToast'
import api from '@/services/api'
import RoleBadge from '@/components/common/RoleBadge.vue'

const userStore = useUserStore()
const { showToast } = useToast()

const user = userStore.currentUser ? userStore.currentUser : null
const formRef = ref(null)
const form = ref({ username: '', full_name: '', email: '' })
const error = ref('')
const saving = ref(false)

function loadFromUser() {
  const u = userStore.currentUser
  if (!u) return
  form.value = {
    username: u.username || '',
    full_name: u.full_name || '',
    email: u.email || '',
  }
  error.value = ''
}

watch(() => userStore.currentUser, loadFromUser, { immediate: true })

function reset() {
  loadFromUser()
}

async function save() {
  const u = userStore.currentUser
  if (!u) return
  saving.value = true
  error.value = ''
  try {
    await api.auth.updateUser(u.id, {
      email: form.value.email,
      full_name: form.value.full_name,
    })

    if (userStore.currentUser) {
      userStore.currentUser.email = form.value.email
      userStore.currentUser.full_name = form.value.full_name
    }

    showToast({ message: 'Profile updated', type: 'success' })
  } catch (err) {
    error.value = err?.response?.data?.detail || err?.message || 'Update failed'
  } finally {
    saving.value = false
  }
}
</script>

<style lang="scss" scoped>
.profile-card {
  max-width: 640px;
}

.profile-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
