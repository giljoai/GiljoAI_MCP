<template>
  <v-dialog v-model="internalModel" max-width="560" persistent scrollable>
    <v-card v-draggable class="smooth-border">
      <div class="dlg-header">
        <v-icon class="dlg-icon" icon="mdi-account" />
        <span class="dlg-title">Edit Profile</span>
        <v-btn icon variant="text" size="small" class="dlg-close" aria-label="Close" @click="close">
          <v-icon icon="mdi-close" size="18" />
        </v-btn>
      </div>

      <v-divider />

      <v-card-text class="pa-4">
        <v-form ref="formRef">
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
            <div v-if="userStore.currentUser?.role" class="d-flex align-center">
              <v-icon size="small" color="primary" class="mr-2">mdi-shield-account</v-icon>
              <div class="text-caption text-muted-a11y mr-2">Role</div>
              <v-spacer />
              <RoleBadge :role="userStore.currentUser.role" size="small" />
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
        </v-form>
      </v-card-text>

      <v-divider />

      <div class="dlg-footer">
        <v-spacer />
        <v-btn variant="text" :disabled="saving" @click="close">Cancel</v-btn>
        <v-btn color="primary" variant="flat" :loading="saving" :disabled="saving" @click="save">Save Changes</v-btn>
      </div>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { useUserStore } from '@/stores/user'
import api from '@/services/api'
import RoleBadge from '@/components/common/RoleBadge.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  user: { type: Object, required: true },
})
const emit = defineEmits(['update:modelValue', 'updated'])

const userStore = useUserStore()

const internalModel = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const formRef = ref(null)
const form = ref({ username: '', full_name: '', email: '' })
const error = ref('')
const saving = ref(false)

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      form.value = {
        username: props.user?.username || '',
        full_name: props.user?.full_name || '',
        email: props.user?.email || '',
      }
      error.value = ''
    }
  },
  { immediate: true },
)

function close() {
  emit('update:modelValue', false)
}

async function save() {
  saving.value = true
  error.value = ''
  try {
    await api.auth.updateUser(props.user.id, {
      email: form.value.email,
      full_name: form.value.full_name,
    })

    if (userStore.currentUser) {
      userStore.currentUser.email = form.value.email
      userStore.currentUser.full_name = form.value.full_name
    }

    emit('updated')
    close()
  } catch (err) {
    error.value = err?.response?.data?.detail || err?.message || 'Update failed'
  } finally {
    saving.value = false
  }
}
</script>
