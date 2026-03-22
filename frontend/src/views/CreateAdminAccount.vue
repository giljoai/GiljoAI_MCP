<template>
  <v-container class="pa-0 ma-0" fluid>
    <v-row no-gutters class="fill-height">
      <v-col cols="12" class="d-flex flex-column align-center justify-center">
        <v-card class="admin-card mx-auto" max-width="500" elevation="8">

          <!-- ============ STEP 1: Account Setup ============ -->
          <template v-if="step === 1">
            <div class="text-center pa-6">
              <GilMascot :size="80" :happy="mascotHappy" class="mb-4" />
              <h1 class="admin-title text-h3 mb-2">{{ greeting }}</h1>
              <h3 class="text-subtitle-1 text-medium-emphasis">
                Create your administrator account to get started
              </h3>
            </div>

            <v-card-text class="pa-6 pt-0">
              <v-form ref="step1Form" v-model="step1Valid" @submit.prevent="goToStep2">
                <!-- Workspace Name -->
                <v-text-field
                  v-model="workspaceName"
                  label="Workspace Name"
                  :rules="workspaceNameRules"
                  variant="outlined"
                  density="comfortable"
                  class="mb-4"
                  hint="Name for your organization (e.g., 'Acme Corp', 'My Team')"
                  persistent-hint
                  prepend-inner-icon="mdi-domain"
                  required
                  @keydown.enter="flashHappy" @keydown.tab="flashHappyOnly"
                />

                <!-- Username -->
                <v-text-field
                  v-model="username"
                  label="Username"
                  :rules="usernameRules"
                  variant="outlined"
                  density="comfortable"
                  class="mb-4"
                  hint="Unique username for login"
                  persistent-hint
                  prepend-inner-icon="mdi-account"
                  @keydown.enter="flashHappy" @keydown.tab="flashHappyOnly"
                />

                <!-- Email -->
                <v-text-field
                  v-model="email"
                  label="Email (optional)"
                  type="email"
                  :rules="emailRules"
                  variant="outlined"
                  density="comfortable"
                  class="mb-4"
                  prepend-inner-icon="mdi-email"
                  @keydown.enter="flashHappy" @keydown.tab="flashHappyOnly"
                />

                <!-- Full Name -->
                <v-text-field
                  v-model="fullName"
                  label="Full Name (optional)"
                  variant="outlined"
                  density="comfortable"
                  class="mb-4"
                  prepend-inner-icon="mdi-account-box"
                  @keydown.enter="flashHappy" @keydown.tab="flashHappyOnly"
                />

                <!-- Password -->
                <v-text-field
                  v-model="password"
                  label="Password"
                  :type="showPassword ? 'text' : 'password'"
                  :rules="passwordRules"
                  variant="outlined"
                  density="comfortable"
                  class="mb-4"
                  prepend-inner-icon="mdi-lock"
                  @keydown.enter="flashHappy" @keydown.tab="flashHappyOnly"
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

                <!-- Confirm Password -->
                <v-text-field
                  v-model="confirmPassword"
                  label="Confirm Password"
                  :type="showConfirmPassword ? 'text' : 'password'"
                  :rules="confirmPasswordRules"
                  variant="outlined"
                  density="comfortable"
                  class="mb-4"
                  prepend-inner-icon="mdi-lock-check"
                  @keydown.enter="flashHappy" @keydown.tab="flashHappyOnly"
                >
                  <template #append-inner>
                    <v-icon
                      tabindex="-1"
                      @click="showConfirmPassword = !showConfirmPassword"
                    >
                      {{ showConfirmPassword ? 'mdi-eye' : 'mdi-eye-off' }}
                    </v-icon>
                  </template>
                </v-text-field>

                <!-- Compact Password Compliance Indicator -->
                <div v-if="passwordMeetsAll" class="d-flex align-center mb-4">
                  <v-icon color="success" size="16" class="mr-1">mdi-check-circle</v-icon>
                  <span class="text-caption">Meets password requirements</span>
                  <v-tooltip location="top" max-width="300">
                    <template #activator="{ props }">
                      <v-icon v-bind="props" size="16" class="ml-1">mdi-information-outline</v-icon>
                    </template>
                    <span class="text-caption"
                      >At least 12 characters, one uppercase, one lowercase, one digit, and one
                      special character.</span
                    >
                  </v-tooltip>
                </div>

                <!-- Next Button -->
                <div class="d-flex justify-center mt-4">
                  <v-btn
                    type="submit"
                    color="primary"
                    size="large"
                    :disabled="!step1Valid"
                    min-width="160"
                  >
                    Next
                    <v-icon end>mdi-arrow-right</v-icon>
                  </v-btn>
                </div>
              </v-form>
            </v-card-text>

            <!-- Footer -->
            <div class="text-center pa-4 pt-0">
              <span class="text-caption footer-brand">www.giljo.ai</span>
            </div>
          </template>

          <!-- ============ STEP 2: Recovery PIN ============ -->
          <template v-if="step === 2">
            <div class="text-center pa-6">
              <h2 class="text-h5 font-weight-bold mb-2">
                <v-icon class="mr-2">mdi-shield-key</v-icon>
                Recovery PIN Setup
              </h2>
              <p class="text-body-2 text-medium-emphasis">
                Create a 4-digit PIN for password recovery. This PIN can be used if you forget your
                password.
              </p>
            </div>

            <v-card-text class="pa-6 pt-0">
              <v-form ref="step2Form" v-model="step2Valid" @submit.prevent="createAdmin">
                <!-- Recovery PIN -->
                <v-text-field
                  v-model="recoveryPin"
                  label="Recovery PIN (4 digits)"
                  type="text"
                  inputmode="numeric"
                  pattern="[0-9]{4}"
                  maxlength="4"
                  :rules="pinRules"
                  variant="outlined"
                  density="comfortable"
                  class="mb-3"
                  hint="Enter 4 digits (example: 1234)"
                  persistent-hint
                  aria-label="Enter your 4-digit recovery PIN"
                  aria-required="true"
                  @input="handlePinInput"
                  @keypress="onlyNumbers"
                />

                <!-- Confirm PIN -->
                <v-text-field
                  v-model="confirmPin"
                  label="Confirm Recovery PIN"
                  type="text"
                  inputmode="numeric"
                  pattern="[0-9]{4}"
                  maxlength="4"
                  :rules="confirmPinRules"
                  variant="outlined"
                  density="comfortable"
                  class="mb-3"
                  aria-label="Confirm your 4-digit recovery PIN"
                  aria-required="true"
                  @input="handleConfirmPinInput"
                  @keypress="onlyNumbers"
                />

                <!-- Error Message -->
                <v-alert v-if="errorMessage" type="error" variant="tonal" class="mb-4">
                  {{ errorMessage }}
                </v-alert>

                <!-- Action Buttons -->
                <div class="d-flex justify-space-between mt-4">
                  <v-btn
                    variant="outlined"
                    @click="step = 1"
                  >
                    <v-icon start>mdi-arrow-left</v-icon>
                    Back
                  </v-btn>
                  <v-btn
                    type="submit"
                    color="primary"
                    :loading="loading"
                    :disabled="!step2Valid"
                  >
                    Finish
                  </v-btn>
                </div>
              </v-form>
            </v-card-text>

            <!-- Footer -->
            <div class="text-center pa-4 pt-0">
              <span class="text-caption footer-brand">www.giljo.ai</span>
            </div>
          </template>

        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/services/api'
import GilMascot from '@/components/GilMascot.vue'

const router = useRouter()

// Wizard step
const step = ref(1)

// Greeting updates on Enter/Tab once username is filled
const greeting = ref('Welcome!')
function updateGreeting() {
  if (username.value.trim()) {
    greeting.value = `Hi ${username.value.trim()}!`
  }
}

// Mascot happy eyes on Enter + advance to next field
const mascotHappy = ref(false)
let happyTimer = null
function flashHappyOnly() {
  mascotHappy.value = true
  clearTimeout(happyTimer)
  happyTimer = setTimeout(() => { mascotHappy.value = false }, 600)
  updateGreeting()
}

function flashHappy(event) {
  flashHappyOnly()

  // Move focus to the next input field
  const form = event.target.closest('form')
  if (form) {
    const inputs = Array.from(form.querySelectorAll('input:not([type="hidden"])'))
    const idx = inputs.indexOf(event.target)
    if (idx >= 0 && idx < inputs.length - 1) {
      event.preventDefault()
      inputs[idx + 1].focus()
    }
  }
}

// Form refs
const step1Form = ref(null)
const step2Form = ref(null)

// Form data
const workspaceName = ref('')
const username = ref('')
const email = ref('')
const fullName = ref('')
const password = ref('')
const confirmPassword = ref('')
const recoveryPin = ref('')
const confirmPin = ref('')
const showPassword = ref(false)
const showConfirmPassword = ref(false)
const step1Valid = ref(false)
const step2Valid = ref(false)
const loading = ref(false)
const errorMessage = ref('')

// Validation rules
const workspaceNameRules = [
  (v) => !!v || 'Workspace name is required',
  (v) => v.length >= 1 || 'Workspace name is required',
  (v) => v.length <= 255 || 'Workspace name must be less than 255 characters',
]

const usernameRules = [
  (v) => !!v || 'Username is required',
  (v) => v.length >= 3 || 'Username must be at least 3 characters',
  (v) => v.length <= 64 || 'Username must be less than 64 characters',
  (v) =>
    /^[a-zA-Z0-9_-]+$/.test(v) ||
    'Username can only contain letters, numbers, underscores, and hyphens',
]

const emailRules = [(v) => !v || /.+@.+\..+/.test(v) || 'Email must be valid']

const passwordRules = [
  (v) => !!v || 'Password is required',
  (v) => v.length >= 12 || 'Password must be at least 12 characters',
  (v) => /[A-Z]/.test(v) || 'Must contain at least one uppercase letter',
  (v) => /[a-z]/.test(v) || 'Must contain at least one lowercase letter',
  (v) => /\d/.test(v) || 'Must contain at least one digit',
  (v) => /[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(v) || 'Must contain at least one special character',
]

const confirmPasswordRules = [
  (v) => !!v || 'Password confirmation is required',
  (v) => v === password.value || 'Passwords do not match',
]

const pinRules = [
  (v) => !!v || 'Recovery PIN is required',
  (v) => /^\d{4}$/.test(v) || 'PIN must be exactly 4 digits',
]

const confirmPinRules = [
  (v) => !!v || 'PIN confirmation is required',
  (v) => /^\d{4}$/.test(v) || 'PIN must be exactly 4 digits',
  (v) => v === recoveryPin.value || 'PINs do not match',
]

// Password requirements
const passwordRequirements = computed(() => [
  { text: 'At least 12 characters', met: password.value.length >= 12 },
  { text: 'One uppercase letter', met: /[A-Z]/.test(password.value) },
  { text: 'One lowercase letter', met: /[a-z]/.test(password.value) },
  { text: 'One digit', met: /\d/.test(password.value) },
  { text: 'One special character', met: /[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(password.value) },
  {
    text: 'Passwords match',
    met: password.value === confirmPassword.value && confirmPassword.value !== '',
  },
])

// All requirements satisfied?
const passwordMeetsAll = computed(() => passwordRequirements.value.every((r) => r.met))

// Step 1 -> Step 2
async function goToStep2() {
  const { valid } = await step1Form.value.validate()
  if (valid) {
    step.value = 2
  }
}

// Methods for PIN input handling
function handlePinInput(value) {
  const val = typeof value === 'string' ? value : value?.target?.value || ''
  recoveryPin.value = val.replace(/\D/g, '').slice(0, 4)
}

function handleConfirmPinInput(value) {
  const val = typeof value === 'string' ? value : value?.target?.value || ''
  confirmPin.value = val.replace(/\D/g, '').slice(0, 4)
}

function onlyNumbers(event) {
  const charCode = event.which ? event.which : event.keyCode
  if (charCode < 48 || charCode > 57) {
    event.preventDefault()
  }
}

// Clear error on input
watch([workspaceName, username, email, password, confirmPassword, recoveryPin, confirmPin], () => {
  errorMessage.value = ''
})

// Create admin function - submits all cached data from both steps
const createAdmin = async () => {
  const { valid } = await step2Form.value.validate()
  if (!valid) return

  loading.value = true
  errorMessage.value = ''

  try {
    await api.auth.createFirstAdmin({
      workspace_name: workspaceName.value,
      username: username.value,
      email: email.value || null,
      full_name: fullName.value || null,
      password: password.value,
      confirm_password: confirmPassword.value,
      recovery_pin: recoveryPin.value,
      confirm_pin: confirmPin.value,
    })

    router.push('/')
  } catch (error) {
    console.error('[CREATE_ADMIN] Failed:', error)

    if (error.response?.data?.detail) {
      errorMessage.value = error.response.data.detail
    } else if (error.message) {
      errorMessage.value = error.message
    } else {
      errorMessage.value = 'Failed to create administrator account. Please try again.'
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.fill-height {
  min-height: 100vh;
}

.admin-card {
  margin-top: 5vh;
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.admin-title {
  background: var(--gradient-brand);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  font-weight: 700;
}

.requirement-list {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 16px;
}

.footer-brand {
  color: #ffd93d;
}
</style>
