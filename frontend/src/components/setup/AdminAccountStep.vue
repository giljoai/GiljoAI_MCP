<template>
  <v-card-text class="pa-8">
    <h2 class="text-h5 mb-2">Create Admin Account</h2>

    <!-- Info Alert -->
    <v-alert type="info" variant="tonal" class="mb-6">
      <strong>This account will manage user access and system settings</strong>
      <div class="text-caption mt-1">Required for LAN deployment mode</div>
    </v-alert>

    <v-form ref="form" v-model="formValid" @submit.prevent="handleNext">
      <!-- Network Adapter Selection -->
      <v-select
        v-if="!showManualIpEntry"
        v-model="formData.selectedAdapter"
        :items="adapterItems"
        item-title="label"
        item-value="value"
        label="Network Adapter"
        variant="outlined"
        :rules="adapterRules"
        :loading="loadingAdapters"
        :disabled="loadingAdapters"
        required
        class="mb-4"
        aria-label="Select network adapter"
        hint="Choose the network adapter for LAN access"
        persistent-hint
        autocomplete="off"
      >
        <template #append-inner>
          <v-icon
            v-if="formData.selectedAdapter && !loadingAdapters"
            color="success"
          >
            mdi-check-circle
          </v-icon>
        </template>
      </v-select>

      <!-- Fallback: Manual IP Entry -->
      <v-text-field
        v-if="showManualIpEntry"
        v-model="formData.serverIp"
        label="Server IP Address"
        variant="outlined"
        :rules="serverIpRules"
        required
        class="mb-4"
        aria-label="Server IP address"
        hint="The IP address of this computer on your network (e.g., 192.168.1.100)"
        persistent-hint
        autocomplete="off"
      >
        <template v-if="isValidIp" #append-inner>
          <v-icon color="success">mdi-check-circle</v-icon>
        </template>
      </v-text-field>

      <!-- Toggle for Manual Entry -->
      <div v-if="!loadingAdapters" class="text-caption mb-4">
        <a
          href="#"
          @click.prevent="toggleManualEntry"
          class="text-primary"
          aria-label="Toggle manual IP entry"
        >
          {{ showManualIpEntry ? 'Use adapter dropdown' : 'Enter IP manually' }}
        </a>
      </div>

      <!-- Error Alert -->
      <v-alert
        v-if="adapterError"
        type="warning"
        variant="tonal"
        closable
        class="mb-4"
        @click:close="adapterError = null"
      >
        <strong>Network adapter detection failed</strong>
        <div class="text-caption mt-1">{{ adapterError }}</div>
      </v-alert>

      <!-- Email (optional) -->
      <v-text-field
        v-model="formData.email"
        label="Email (optional)"
        type="email"
        variant="outlined"
        :rules="emailRules"
        class="mb-4"
        aria-label="Admin email"
        hint="Optional email for account recovery"
        persistent-hint
        autocomplete="email"
      />

      <!-- Username -->
      <v-text-field
        v-model="formData.username"
        label="Username"
        variant="outlined"
        :rules="usernameRules"
        required
        class="mb-4"
        aria-label="Admin username"
        hint="Alphanumeric, underscores, and hyphens only"
        persistent-hint
        autocomplete="username"
      >
        <template v-if="usernameAvailable" #append-inner>
          <v-icon color="success">mdi-check-circle</v-icon>
        </template>
      </v-text-field>

      <!-- Password -->
      <v-text-field
        v-model="formData.password"
        label="Password"
        :type="showPassword ? 'text' : 'password'"
        variant="outlined"
        :rules="passwordRules"
        required
        class="mb-2"
        aria-label="Admin password"
        autocomplete="new-password"
      >
        <template #append-inner>
          <v-icon
            :icon="showPassword ? 'mdi-eye-off' : 'mdi-eye'"
            @click="showPassword = !showPassword"
            role="button"
            aria-label="Toggle password visibility"
          />
        </template>
      </v-text-field>

      <!-- Password Strength Indicator -->
      <div v-if="formData.password" class="mb-4">
        <div class="d-flex justify-space-between mb-1">
          <span class="text-caption">Password strength:</span>
          <span class="text-caption" :style="{ color: strengthColor }">
            {{ strengthText }}
          </span>
        </div>
        <v-progress-linear :model-value="strengthValue" :color="strengthColor" height="6" rounded />
      </div>

      <!-- Confirm Password -->
      <v-text-field
        v-model="formData.confirmPassword"
        label="Confirm Password"
        :type="showConfirmPassword ? 'text' : 'password'"
        variant="outlined"
        :rules="confirmPasswordRules"
        required
        class="mb-4"
        aria-label="Confirm admin password"
        autocomplete="new-password"
      >
        <template #append-inner>
          <v-icon
            :icon="showConfirmPassword ? 'mdi-eye-off' : 'mdi-eye'"
            @click="showConfirmPassword = !showConfirmPassword"
            role="button"
            aria-label="Toggle confirm password visibility"
          />
        </template>
        <template v-if="passwordsMatch && formData.confirmPassword" #append>
          <v-icon color="success">mdi-check-circle</v-icon>
        </template>
      </v-text-field>

      <!-- Password Requirements -->
      <v-card variant="outlined" class="mb-6">
        <v-card-text>
          <p class="text-subtitle-2 mb-2">Password Requirements:</p>
          <v-list density="compact" class="bg-transparent">
            <v-list-item :prepend-icon="hasMinLength ? 'mdi-check-circle' : 'mdi-circle-outline'">
              <template #prepend>
                <v-icon :color="hasMinLength ? 'success' : 'grey'">
                  {{ hasMinLength ? 'mdi-check-circle' : 'mdi-circle-outline' }}
                </v-icon>
              </template>
              <v-list-item-title class="text-caption"> At least 8 characters </v-list-item-title>
            </v-list-item>
            <v-list-item>
              <template #prepend>
                <v-icon :color="hasUppercase ? 'success' : 'grey'">
                  {{ hasUppercase ? 'mdi-check-circle' : 'mdi-circle-outline' }}
                </v-icon>
              </template>
              <v-list-item-title class="text-caption">
                Contains uppercase letter
              </v-list-item-title>
            </v-list-item>
            <v-list-item>
              <template #prepend>
                <v-icon :color="hasLowercase ? 'success' : 'grey'">
                  {{ hasLowercase ? 'mdi-check-circle' : 'mdi-circle-outline' }}
                </v-icon>
              </template>
              <v-list-item-title class="text-caption">
                Contains lowercase letter
              </v-list-item-title>
            </v-list-item>
            <v-list-item>
              <template #prepend>
                <v-icon :color="hasNumber ? 'success' : 'grey'">
                  {{ hasNumber ? 'mdi-check-circle' : 'mdi-circle-outline' }}
                </v-icon>
              </template>
              <v-list-item-title class="text-caption"> Contains number </v-list-item-title>
            </v-list-item>
            <v-list-item>
              <template #prepend>
                <v-icon :color="hasSpecial ? 'success' : 'grey-lighten-1'">
                  {{ hasSpecial ? 'mdi-check-circle' : 'mdi-circle-outline' }}
                </v-icon>
              </template>
              <v-list-item-title class="text-caption text-medium-emphasis">
                Contains special character (recommended)
              </v-list-item-title>
            </v-list-item>
          </v-list>
        </v-card-text>
      </v-card>
    </v-form>

    <!-- Progress -->
    <v-card variant="outlined" class="mb-6">
      <v-card-text>
        <div class="d-flex justify-space-between mb-2">
          <span class="text-caption">Progress: Step 4 of 7</span>
          <span class="text-caption">57%</span>
        </div>
        <v-progress-linear :model-value="57" color="primary" />
      </v-card-text>
    </v-card>

    <!-- Navigation -->
    <div class="d-flex justify-space-between">
      <v-btn variant="outlined" @click="$emit('back')" aria-label="Go back to deployment mode">
        <v-icon start>mdi-arrow-left</v-icon>
        Back
      </v-btn>
      <v-btn
        color="primary"
        :disabled="!formValid"
        @click="handleNext"
        aria-label="Continue to AI tools"
      >
        Continue
        <v-icon end>mdi-arrow-right</v-icon>
      </v-btn>
    </div>
  </v-card-text>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import setupService from '@/services/setupService'

/**
 * AdminAccountStep - Admin account creation for LAN mode
 *
 * Collects admin credentials with password strength validation
 * Features network adapter dropdown with fallback to manual IP entry
 */

const props = defineProps({
  modelValue: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['update:modelValue', 'next', 'back', 'admin-setup-complete'])

// Form state
const form = ref(null)
const formValid = ref(false)
const showPassword = ref(false)
const showConfirmPassword = ref(false)

// Network adapter state
const loadingAdapters = ref(false)
const adapterError = ref(null)
const adapters = ref([])
const showManualIpEntry = ref(false)

const formData = ref({
  username: 'admin',
  email: '',
  serverIp: '',
  selectedAdapter: null,
  selectedAdapterObject: null,  // Store full adapter object
  password: '',
  confirmPassword: '',
})

// Validation rules
const usernameRules = [
  (v) => !!v || 'Username is required',
  (v) => v.length >= 3 || 'Username must be at least 3 characters',
  (v) =>
    /^[a-zA-Z0-9_-]+$/.test(v) || 'Username must be alphanumeric with underscores or hyphens only',
]

const emailRules = [(v) => !v || /.+@.+\..+/.test(v) || 'Email must be valid']

const serverIpRules = [
  (v) => !!v || 'Server IP address is required',
  (v) => /^(\d{1,3}\.){3}\d{1,3}$/.test(v) || 'Must be a valid IP address (e.g., 192.168.1.100)',
  (v) => {
    const parts = v.split('.')
    return parts.every(part => parseInt(part) >= 0 && parseInt(part) <= 255) || 'Each number must be between 0-255'
  }
]

const adapterRules = [
  (v) => !!v || 'Please select a network adapter',
]

const passwordRules = [
  (v) => !!v || 'Password is required',
  (v) => v.length >= 8 || 'Password must be at least 8 characters',
  (v) => /[A-Z]/.test(v) || 'Password must contain an uppercase letter',
  (v) => /[a-z]/.test(v) || 'Password must contain a lowercase letter',
  (v) => /\d/.test(v) || 'Password must contain a number',
]

const confirmPasswordRules = [
  (v) => !!v || 'Please confirm your password',
  (v) => v === formData.value.password || 'Passwords do not match',
]

// Password strength checks
const hasMinLength = computed(() => formData.value.password.length >= 8)
const hasUppercase = computed(() => /[A-Z]/.test(formData.value.password))
const hasLowercase = computed(() => /[a-z]/.test(formData.value.password))
const hasNumber = computed(() => /\d/.test(formData.value.password))
const hasSpecial = computed(() => /[!@#$%^&*(),.?":{}|<>]/.test(formData.value.password))

const usernameAvailable = computed(() => {
  return formData.value.username.length >= 3 && /^[a-zA-Z0-9_-]+$/.test(formData.value.username)
})

const isValidIp = computed(() => {
  const ip = formData.value.serverIp
  if (!ip) return false
  const parts = ip.split('.')
  if (parts.length !== 4) return false
  return parts.every(part => {
    const num = parseInt(part)
    return num >= 0 && num <= 255 && !isNaN(num)
  })
})

const passwordsMatch = computed(() => {
  return (
    formData.value.password === formData.value.confirmPassword &&
    formData.value.confirmPassword.length > 0
  )
})

// Password strength calculation
const passwordStrength = computed(() => {
  const checks = [
    hasMinLength.value,
    hasUppercase.value,
    hasLowercase.value,
    hasNumber.value,
    hasSpecial.value,
  ]

  const score = checks.filter(Boolean).length
  const password = formData.value.password

  if (score < 3) return { level: 'weak', value: 20, color: 'error' }
  if (score === 3) return { level: 'fair', value: 40, color: 'warning' }
  if (score === 4) return { level: 'good', value: 60, color: 'info' }
  if (score === 5 && password.length < 10) return { level: 'good', value: 60, color: 'info' }
  if (score === 5 && password.length >= 10 && password.length < 12) {
    return { level: 'strong', value: 80, color: 'success' }
  }
  if (score === 5 && password.length >= 12) {
    return { level: 'excellent', value: 100, color: 'success' }
  }
  return { level: 'weak', value: 20, color: 'error' }
})

const strengthValue = computed(() => passwordStrength.value.value)
const strengthColor = computed(() => passwordStrength.value.color)
const strengthText = computed(() => {
  const level = passwordStrength.value.level
  return level.charAt(0).toUpperCase() + level.slice(1)
})

// Adapter items for dropdown
const adapterItems = computed(() => {
  return adapters.value.map(adapter => ({
    label: `${adapter.name} (${adapter.ip_address})`,
    value: adapter.ip_address,
    adapter: adapter,  // Store full adapter object for later use
  }))
})

// Lifecycle: Setup on mount
onMounted(async () => {
  // v3.0: Network adapter detection removed - use manual IP entry
  showManualIpEntry.value = true
})

// Methods (network adapter detection removed in v3.0)
// const fetchAdapters = async () => {
//   // Removed in v3.0 unified architecture
// }

const toggleManualEntry = () => {
  showManualIpEntry.value = !showManualIpEntry.value

  // When switching back to dropdown, restore selected adapter IP
  if (!showManualIpEntry.value && formData.value.selectedAdapter) {
    formData.value.serverIp = formData.value.selectedAdapter
  }
}

// Watch selectedAdapter and update serverIp + adapter object
watch(
  () => formData.value.selectedAdapter,
  (newAdapterIp) => {
    if (newAdapterIp && !showManualIpEntry.value) {
      formData.value.serverIp = newAdapterIp

      // Find and store the full adapter object
      const adapterObj = adapters.value.find(a => a.ip_address === newAdapterIp)
      if (adapterObj) {
        formData.value.selectedAdapterObject = adapterObj
      }
    }
  }
)

// Watch for changes and emit to parent
watch(
  formData,
  (newVal) => {
    if (formValid.value) {
      emit('update:modelValue', {
        username: newVal.username,
        email: newVal.email,
        serverIp: newVal.serverIp,
        password: newVal.password,
        adapterName: newVal.selectedAdapterObject?.name || null,
        adapterId: newVal.selectedAdapterObject?.interface_id || newVal.selectedAdapterObject?.name || null,
      })
    }
  },
  { deep: true },
)

const handleNext = () => {
  if (formValid.value) {
    const adminData = {
      username: formData.value.username,
      email: formData.value.email,
      serverIp: formData.value.serverIp,
      password: formData.value.password,
      adapterName: formData.value.selectedAdapterObject?.name || null,
      adapterId: formData.value.selectedAdapterObject?.interface_id || formData.value.selectedAdapterObject?.name || null,
    }
    emit('update:modelValue', adminData)
    emit('admin-setup-complete', adminData)
    emit('next')
  }
}
</script>

<style scoped>
h2 {
  color: rgb(var(--v-theme-primary));
}
</style>
