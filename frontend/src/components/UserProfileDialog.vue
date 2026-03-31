<template>
  <v-dialog v-model="internalModel" max-width="560" persistent>
    <v-card v-draggable class="smooth-border">
      <v-card-title class="d-flex align-center">
        <v-icon start>mdi-account</v-icon>
        Edit Profile
        <v-spacer />
        <v-btn icon="mdi-close" variant="text" aria-label="Close" @click="close" />
      </v-card-title>

      <v-card-text>
        <v-form ref="formRef">
          <v-text-field
            v-model="form.username"
            label="Username"
            variant="outlined"
            density="comfortable"
            disabled
            class="mb-3"
          />

          <!-- Workspace/Organization (read-only) - Handover 0424o -->
          <div v-if="userStore.currentOrg" class="mb-4 pa-3 bg-surface-variant rounded">
            <div class="text-caption text-muted-a11y mb-1">Workspace</div>
            <div class="d-flex align-center gap-2">
              <v-icon size="small" color="primary">mdi-office-building</v-icon>
              <span class="font-weight-medium">{{ userStore.currentOrg.name }}</span>
              <RoleBadge v-if="userStore.orgRole" :role="userStore.orgRole" size="small" />
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
            class="mb-6"
          />

          <v-alert type="info" variant="tonal" class="mb-3">
            Password changes are handled by an administrator. You can reset your 4‑digit recovery
            PIN below.
          </v-alert>

          <v-text-field
            v-model="pin.current_password"
            label="Current Password"
            type="password"
            variant="outlined"
            density="comfortable"
            hint="Required to set a new recovery PIN"
            persistent-hint
            class="mb-3"
          />
          <v-row>
            <v-col cols="12" md="6">
              <v-text-field
                v-model="pin.recovery_pin"
                label="New Recovery PIN"
                variant="outlined"
                density="comfortable"
                maxlength="4"
                counter="4"
                @input="pin.recovery_pin = pin.recovery_pin.replace(/\D/g, '').slice(0, 4)"
              />
            </v-col>
            <v-col cols="12" md="6">
              <v-text-field
                v-model="pin.confirm_pin"
                label="Confirm PIN"
                variant="outlined"
                density="comfortable"
                maxlength="4"
                counter="4"
                @input="pin.confirm_pin = pin.confirm_pin.replace(/\D/g, '').slice(0, 4)"
              />
            </v-col>
          </v-row>

          <v-alert v-if="pinError" type="error" variant="tonal" density="compact" class="mt-2">
            {{ pinError }}
          </v-alert>
        </v-form>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" :disabled="saving" @click="close">Cancel</v-btn>
        <v-btn color="primary" :loading="saving" :disabled="saving" @click="save"
          >Save Changes</v-btn
        >
      </v-card-actions>
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
const pin = ref({ current_password: '', recovery_pin: '', confirm_pin: '' })
const pinError = ref('')
const saving = ref(false)

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      // Initialize form from user
      form.value = {
        username: props.user?.username || '',
        full_name: props.user?.full_name || '',
        email: props.user?.email || '',
      }
      pin.value = { current_password: '', recovery_pin: '', confirm_pin: '' }
      pinError.value = ''
    }
  },
  { immediate: true },
)

function close() {
  emit('update:modelValue', false)
}

async function save() {
  saving.value = true
  pinError.value = ''
  try {
    // 1) Update profile fields (email/full_name)
    await api.auth.updateUser(props.user.id, {
      email: form.value.email,
      full_name: form.value.full_name,
    })

    // Update store currentUser locally
    if (userStore.currentUser) {
      userStore.currentUser.email = form.value.email
      userStore.currentUser.full_name = form.value.full_name
    }

    // 2) If PIN fields provided, set recovery PIN
    const wantsPinChange =
      !!pin.value.current_password && !!pin.value.recovery_pin && !!pin.value.confirm_pin

    if (wantsPinChange) {
      if (pin.value.recovery_pin !== pin.value.confirm_pin) {
        pinError.value = 'PINs do not match'
        saving.value = false
        return
      }
      if (!/^\d{4}$/.test(pin.value.recovery_pin)) {
        pinError.value = 'PIN must be exactly 4 digits'
        saving.value = false
        return
      }

      await api.auth.setRecoveryPin({
        current_password: pin.value.current_password,
        recovery_pin: pin.value.recovery_pin,
        confirm_pin: pin.value.confirm_pin,
      })
    }

    emit('updated')
    close()
  } catch (err) {
    // Show PIN-specific errors if present
    const msg = err?.response?.data?.detail || err?.message || 'Update failed'
    pinError.value = msg
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
</style>
