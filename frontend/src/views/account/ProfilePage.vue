<template>
  <v-card variant="flat" class="smooth-border profile-card">
    <v-card-text class="pa-5">
      <div v-if="!user" class="text-body-medium text-muted-a11y">Sign in to view your profile.</div>

      <v-form v-else ref="formRef">
        <v-text-field
          v-model="form.username"
          label="Username"
          variant="outlined"
          density="comfortable"
          disabled
          class="mb-3"
        />

        <!-- Workspace/Organization + Role (read-only) - Handover 0424o, 0875.
             CE-only display (FE-9172): hosted SaaS is single-user/account-owner,
             so the Owner/Admin badges are hidden there. Display only — role
             logic and guards are unchanged. -->
        <div v-if="isCe" class="mb-4 pa-4 bg-surface-variant rounded" data-test="workspace-role-box">
          <div v-if="userStore.currentOrg" class="d-flex align-center mb-3">
            <v-icon size="small" color="primary" class="mr-2">mdi-office-building</v-icon>
            <div class="text-body-small text-muted-a11y mr-2">Workspace</div>
            <span class="font-weight-medium">{{ userStore.currentOrg.name }}</span>
            <v-spacer />
            <RoleBadge v-if="userStore.orgRole" :role="userStore.orgRole" size="small" />
          </div>
          <div v-if="user.role" class="d-flex align-center">
            <v-icon size="small" color="primary" class="mr-2">mdi-shield-account</v-icon>
            <div class="text-body-small text-muted-a11y mr-2">Role</div>
            <v-spacer />
            <RoleBadge :role="user.role" size="small" />
          </div>
        </div>

        <v-text-field
          v-model="form.first_name"
          label="First Name"
          :rules="firstNameRules"
          variant="outlined"
          density="comfortable"
          autocomplete="given-name"
          maxlength="255"
          class="mb-3"
        />
        <v-text-field
          v-model="form.last_name"
          label="Last Name (optional)"
          :rules="lastNameRules"
          variant="outlined"
          density="comfortable"
          autocomplete="family-name"
          maxlength="255"
          class="mb-3"
        />
        <v-text-field
          v-model="form.email"
          label="Email"
          type="email"
          variant="outlined"
          density="comfortable"
          data-test="email-field"
          :hint="
            emailPending
              ? 'A verification is pending — confirm or cancel below before changing again.'
              : ''
          "
          :persistent-hint="!!emailPending"
          :disabled="!!emailPending"
        />

        <!-- SaaS-only: pending email change banner (injected via import.meta.glob) -->
        <div
          v-if="emailPending"
          class="email-pending-banner smooth-border mt-3 pa-3 rounded"
          data-test="email-pending-banner"
        >
          <div class="d-flex align-center mb-2">
            <v-icon size="18" color="warning" class="mr-2">mdi-email-clock</v-icon>
            <span class="text-body-medium font-weight-medium">Email change pending confirmation</span>
          </div>
          <p class="text-body-medium mb-2" style="color: var(--text-secondary)">
            A verification link was sent to
            <strong>{{ emailPending }}</strong
            >. Your current email stays active until you confirm.
          </p>
          <div class="d-flex gap-2">
            <v-btn
              variant="text"
              size="small"
              :loading="resending"
              data-test="email-resend-btn"
              @click="resendEmailChange"
            >
              Resend link
            </v-btn>
            <v-btn
              variant="text"
              size="small"
              color="error"
              :loading="cancelling"
              data-test="email-cancel-btn"
              @click="cancelEmailChange"
            >
              Cancel
            </v-btn>
          </div>
        </div>

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

  <!-- Password & Security (IMP-5042) — self-service credential rotation -->
  <v-card
    v-if="user"
    variant="flat"
    class="smooth-border profile-card mt-4"
    data-test="security-card"
  >
    <v-card-text class="pa-5">
      <div class="text-body-large font-weight-medium mb-1">Password</div>
      <p class="text-body-medium text-muted-a11y mb-4">
        Change the password you use to sign in. You'll be signed out and need to sign in again.
      </p>

      <v-form ref="pwFormRef" @submit.prevent="changePassword">
        <v-text-field
          v-model="pwForm.current"
          label="Current password"
          type="password"
          variant="outlined"
          density="comfortable"
          autocomplete="current-password"
          data-test="current-password"
          class="mb-3"
        />
        <v-text-field
          v-model="pwForm.next"
          label="New password"
          type="password"
          :rules="newPasswordRules"
          variant="outlined"
          density="comfortable"
          autocomplete="new-password"
          data-test="new-password"
          class="mb-3"
        />
        <v-text-field
          v-model="pwForm.confirm"
          label="Confirm new password"
          type="password"
          :rules="confirmPasswordRules"
          variant="outlined"
          density="comfortable"
          autocomplete="new-password"
          data-test="confirm-password"
          class="mb-1"
        />

        <v-alert v-if="pwError" type="error" variant="tonal" density="compact" class="mt-2 mb-2">
          {{ pwError }}
        </v-alert>

        <div class="profile-actions mt-3">
          <v-btn
            type="submit"
            color="primary"
            variant="flat"
            :loading="changingPw"
            :disabled="!canSubmitPassword || changingPw"
            data-test="change-password-btn"
          >
            Update Password
          </v-btn>
        </div>
      </v-form>

      <!-- CE only: recovery PIN. Hosted editions use email-based reset, not a PIN. -->
      <template v-if="isCe">
        <v-divider class="my-5" />
        <div class="text-body-large font-weight-medium mb-1">Recovery PIN</div>
        <p class="text-body-medium text-muted-a11y mb-4">
          A 4-digit PIN lets you reset your password from the sign-in screen if you forget it.
        </p>

        <v-form ref="pinFormRef" @submit.prevent="changePin">
          <v-text-field
            v-model="pinForm.next"
            label="New 4-digit PIN"
            :rules="pinRules"
            variant="outlined"
            density="comfortable"
            inputmode="numeric"
            maxlength="4"
            data-test="new-pin"
            class="mb-3"
          />
          <v-text-field
            v-model="pinForm.confirm"
            label="Confirm PIN"
            :rules="confirmPinRules"
            variant="outlined"
            density="comfortable"
            inputmode="numeric"
            maxlength="4"
            data-test="confirm-pin"
            class="mb-1"
          />

          <v-alert v-if="pinError" type="error" variant="tonal" density="compact" class="mt-2 mb-2">
            {{ pinError }}
          </v-alert>

          <div class="profile-actions mt-3">
            <v-btn
              type="submit"
              color="primary"
              variant="flat"
              :loading="changingPin"
              :disabled="!canSubmitPin || changingPin"
              data-test="change-pin-btn"
            >
              Update PIN
            </v-btn>
          </div>
        </v-form>
      </template>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useToast } from '@/composables/useToast'
import api from '@/services/api'
import setupService from '@/services/setupService'
import RoleBadge from '@/components/common/RoleBadge.vue'

const userStore = useUserStore()
const { showToast } = useToast()
const router = useRouter()

const user = userStore.currentUser ? userStore.currentUser : null
const formRef = ref(null)
const form = ref({ username: '', first_name: '', last_name: '', email: '' })
const error = ref('')
const saving = ref(false)

// IMP-5042: self-service credential rotation.
// isCe gates the recovery-PIN section (hosted editions use email-based reset).
const isCe = ref(true)
const pwFormRef = ref(null)
const pinFormRef = ref(null)
const pwForm = ref({ current: '', next: '', confirm: '' })
const pinForm = ref({ next: '', confirm: '' })
const pwError = ref('')
const pinError = ref('')
const changingPw = ref(false)
const changingPin = ref(false)

const newPasswordRules = [
  (v) => (!!v && String(v).length >= 8) || 'Password must be at least 8 characters',
]
const confirmPasswordRules = [(v) => v === pwForm.value.next || 'Passwords do not match']
const pinRules = [(v) => /^[0-9]{4}$/.test(String(v || '')) || 'PIN must be exactly 4 digits']
const confirmPinRules = [(v) => v === pinForm.value.next || 'PINs do not match']

const canSubmitPassword = computed(
  () =>
    pwForm.value.current.length >= 8 &&
    pwForm.value.next.length >= 8 &&
    pwForm.value.next === pwForm.value.confirm,
)
const canSubmitPin = computed(
  () => /^[0-9]{4}$/.test(pinForm.value.next) && pinForm.value.next === pinForm.value.confirm,
)

// SaaS email-change state — null = CE mode or no pending change
// Populated via import.meta.glob (ADR-004) — CE bundle never ships saas/ code.
const emailPending = ref(null) // string (pending email) or null
const resending = ref(false)
const cancelling = ref(false)

// SaaS emailChangeApi — loaded lazily in SaaS mode only (ADR-004)
let emailChangeApi = null

const firstNameRules = [
  (v) => (!!v && String(v).trim().length >= 1) || 'First name is required',
  (v) => String(v || '').length <= 255 || 'First name must be 255 characters or less',
]

const lastNameRules = [
  (v) => String(v || '').length <= 255 || 'Last name must be 255 characters or less',
]

function loadFromUser() {
  const u = userStore.currentUser
  if (!u) return
  form.value = {
    username: u.username || '',
    first_name: u.first_name || '',
    last_name: u.last_name || '',
    email: u.email || '',
  }
  error.value = ''
}

watch(() => userStore.currentUser, loadFromUser, { immediate: true })

onMounted(async () => {
  try {
    const status = await setupService.checkEnhancedStatus()
    const isSaas = (status?.mode ?? 'ce') !== 'ce'
    isCe.value = !isSaas
    if (isSaas) {
      // ADR-004: import.meta.glob keeps SaaS code out of CE bundle.
      // saas/ is stripped on CE export — loader absent = graceful no-op.
      const loaders = import.meta.glob('@/saas/services/emailChange.js')
      const [loader] = Object.values(loaders)
      if (loader) {
        try {
          const mod = await loader()
          emailChangeApi = mod.emailChangeApi ?? mod.default ?? null
        } catch (err) {
          console.warn('[ProfilePage] emailChange module failed to load:', err)
        }
      }
    }
  } catch (err) {
    console.warn('[ProfilePage] setupService error, defaulting to CE mode:', err)
  }
})

function reset() {
  loadFromUser()
}

async function save() {
  const u = userStore.currentUser
  if (!u) return

  // Gate submit on client validation: when the form is invalid (e.g. the
  // required First Name is empty) show ONLY the friendly inline field error —
  // do NOT also fire the PUT, which returns 422 and surfaces a redundant raw
  // "Request failed with status code 422" banner (perf-findings 2026-06-11,
  // same class as the project-create silent-submit fix).
  if (typeof formRef.value?.validate === 'function') {
    const { valid } = await formRef.value.validate()
    if (!valid) return
  }

  saving.value = true
  error.value = ''

  const emailChanged = form.value.email !== (u.email || '')
  // CE mode: email routes through a direct PUT (emailChangeApi is null).
  // SaaS mode: email routes through verification flow — never include it in the PUT.
  const ceModeEmailChange = emailChanged && !emailChangeApi

  try {
    // Save name fields (and email in CE mode when changed) in a single PUT.
    const payload = {
      first_name: form.value.first_name.trim(),
      last_name: form.value.last_name.trim() || null,
    }
    if (ceModeEmailChange) {
      payload.email = form.value.email
    }
    await api.auth.updateUser(u.id, payload)

    if (userStore.currentUser) {
      userStore.currentUser.first_name = form.value.first_name.trim()
      userStore.currentUser.last_name = form.value.last_name.trim() || null
      const combined = `${form.value.first_name.trim()} ${form.value.last_name.trim()}`.trim()
      userStore.currentUser.full_name = combined || userStore.currentUser.full_name
      if (ceModeEmailChange) {
        userStore.currentUser.email = form.value.email
      }
    }

    // SaaS: route email change through verification flow.
    if (emailChanged && emailChangeApi) {
      const res = await emailChangeApi.request(form.value.email)
      emailPending.value = res?.data?.new_email || form.value.email
      // Reset email field back to current (unconfirmed) value
      form.value.email = u.email || ''
      showToast({
        message: `Verification link sent to ${emailPending.value}. Check your inbox to confirm.`,
        type: 'info',
      })
    } else {
      showToast({ message: 'Profile updated', type: 'success' })
    }
  } catch (err) {
    error.value = err?.response?.data?.detail || err?.message || 'Update failed'
  } finally {
    saving.value = false
  }
}

async function resendEmailChange() {
  if (!emailChangeApi) return
  resending.value = true
  error.value = ''
  try {
    const res = await emailChangeApi.resend()
    showToast({
      message: `Verification link resent to ${res?.data?.new_email || emailPending.value}.`,
      type: 'success',
    })
  } catch (err) {
    error.value = err?.response?.data?.detail || err?.message || 'Failed to resend verification'
  } finally {
    resending.value = false
  }
}

async function cancelEmailChange() {
  if (!emailChangeApi) return
  cancelling.value = true
  error.value = ''
  try {
    await emailChangeApi.cancel()
    emailPending.value = null
    showToast({ message: 'Email change cancelled.', type: 'info' })
  } catch (err) {
    error.value = err?.response?.data?.detail || err?.message || 'Failed to cancel email change'
  } finally {
    cancelling.value = false
  }
}

async function changePassword() {
  const u = userStore.currentUser
  if (!u || !canSubmitPassword.value) return
  changingPw.value = true
  pwError.value = ''
  try {
    await api.auth.changePassword(u.id, {
      old_password: pwForm.value.current,
      new_password: pwForm.value.next,
    })
    pwForm.value = { current: '', next: '', confirm: '' }
    showToast({ message: 'Password changed. Please sign in again.', type: 'success' })
    // SEC-6001: the server revoked this session on success. Clear local auth and
    // return to the sign-in screen so the now-invalid cookie can't half-authenticate.
    await userStore.logout()
    router.push('/login')
  } catch (err) {
    const httpStatus = err?.response?.status
    pwError.value =
      httpStatus === 401
        ? 'Current password is incorrect.'
        : err?.response?.data?.detail || err?.message || 'Failed to change password'
  } finally {
    changingPw.value = false
  }
}

async function changePin() {
  const u = userStore.currentUser
  if (!u || !canSubmitPin.value) return
  changingPin.value = true
  pinError.value = ''
  try {
    // Self-service PIN set reuses the tenant-scoped recovery_pin write (BE-6003).
    await api.auth.updateUser(u.id, { recovery_pin: pinForm.value.next })
    pinForm.value = { next: '', confirm: '' }
    showToast({ message: 'Recovery PIN updated.', type: 'success' })
  } catch (err) {
    pinError.value = err?.response?.data?.detail || err?.message || 'Failed to update PIN'
  } finally {
    changingPin.value = false
  }
}

// Expose internal state for testing (seam injection — mirrors AccountDeletionConfirm pattern).
// Tests can set emailChangeApi directly to bypass import.meta.glob loader.
defineExpose({
  form,
  emailPending,
  error,
  saving,
  setEmailChangeApi: (api) => {
    emailChangeApi = api
  },
  isCe,
  pwForm,
  pinForm,
  pwError,
  pinError,
  changePassword,
  changePin,
})
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

/* SaaS email pending banner — uses smooth-border (box-shadow inset) per design system. */
.email-pending-banner {
  background: rgba(255, 195, 0, 0.07);
  /* smooth-border class applied via template for the inset shadow */
}
</style>
