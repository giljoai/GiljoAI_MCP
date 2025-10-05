# GiljoAI MCP Setup Wizard - Component Hierarchy

**Version**: 1.0
**Date**: 2025-10-05
**Designer**: UX Designer Agent

---

## Overview

This document defines the Vue 3 component structure for the GiljoAI MCP Setup Wizard, including component responsibilities, props, events, and composition patterns.

---

## Component Tree

```
SetupWizard.vue (Route: /setup)
├── VuetifyStepper (v-stepper)
│   ├── Step 1: WelcomeStep.vue
│   ├── Step 2: DatabaseStep.vue
│   │   └── DatabaseConnection.vue (extracted, reusable)
│   ├── Step 3: DeploymentModeStep.vue
│   ├── Step 4: AdminAccountStep.vue (conditional: LAN only)
│   ├── Step 5: ToolIntegrationStep.vue
│   │   ├── ToolDetectionList.vue
│   │   ├── ToolCard.vue (repeated for each tool)
│   │   └── ConfigPreviewDialog.vue
│   ├── Step 6: LanConfigStep.vue (conditional: LAN only)
│   │   └── FirewallInstructions.vue
│   └── Step 7: CompleteStep.vue
│       └── ConfigurationSummary.vue
└── WizardFooter.vue (navigation buttons)
```

---

## 1. SetupWizard.vue (Container)

### 1.1 Responsibility
- Main wizard container and orchestrator
- Manages wizard state and step transitions
- Handles navigation logic and guards
- Stores setup configuration data
- Communicates with backend API

### 1.2 Template Structure
```vue
<template>
  <v-container class="setup-wizard" fluid>
    <v-row justify="center">
      <v-col cols="12" md="10" lg="8" xl="6">
        <v-card class="wizard-card" elevation="4">
          <!-- Logo Header -->
          <v-card-title class="text-center pa-6">
            <v-img
              :src="logoSrc"
              alt="GiljoAI"
              height="60"
              contain
            />
          </v-card-title>

          <!-- Vuetify Stepper -->
          <v-stepper
            v-model="currentStep"
            :items="stepperItems"
            alt-labels
            flat
          >
            <!-- Step 1: Welcome -->
            <v-stepper-window-item :value="1">
              <WelcomeStep @next="handleWelcomeNext" />
            </v-stepper-window-item>

            <!-- Step 2: Database -->
            <v-stepper-window-item :value="2">
              <DatabaseStep
                @next="handleDatabaseNext"
                @back="handleBack"
              />
            </v-stepper-window-item>

            <!-- Step 3: Deployment Mode -->
            <v-stepper-window-item :value="3">
              <DeploymentModeStep
                v-model="config.deploymentMode"
                @next="handleDeploymentModeNext"
                @back="handleBack"
              />
            </v-stepper-window-item>

            <!-- Step 4: Admin Account (conditional) -->
            <v-stepper-window-item
              v-if="isLanMode"
              :value="4"
            >
              <AdminAccountStep
                v-model="config.adminAccount"
                @next="handleAdminAccountNext"
                @back="handleBack"
              />
            </v-stepper-window-item>

            <!-- Step 5: AI Tools -->
            <v-stepper-window-item :value="toolsStepNumber">
              <ToolIntegrationStep
                v-model="config.aiTools"
                :deployment-mode="config.deploymentMode"
                @next="handleToolsNext"
                @back="handleBack"
              />
            </v-stepper-window-item>

            <!-- Step 6: LAN Config (conditional) -->
            <v-stepper-window-item
              v-if="isLanMode"
              :value="lanConfigStepNumber"
            >
              <LanConfigStep
                v-model="config.lanSettings"
                @next="handleLanConfigNext"
                @back="handleBack"
              />
            </v-stepper-window-item>

            <!-- Step 7: Complete -->
            <v-stepper-window-item :value="completeStepNumber">
              <CompleteStep
                :config="config"
                @finish="handleFinish"
              />
            </v-stepper-window-item>
          </v-stepper>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>
```

### 1.3 Script (Composition API)
```vue
<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTheme } from 'vuetify'
import WelcomeStep from '@/components/setup/WelcomeStep.vue'
import DatabaseStep from '@/components/setup/DatabaseStep.vue'
import DeploymentModeStep from '@/components/setup/DeploymentModeStep.vue'
import AdminAccountStep from '@/components/setup/AdminAccountStep.vue'
import ToolIntegrationStep from '@/components/setup/ToolIntegrationStep.vue'
import LanConfigStep from '@/components/setup/LanConfigStep.vue'
import CompleteStep from '@/components/setup/CompleteStep.vue'

const router = useRouter()
const theme = useTheme()

// State
const currentStep = ref(1)
const config = ref({
  deploymentMode: 'localhost', // 'localhost' | 'lan' | 'wan'
  adminAccount: null,
  aiTools: [],
  lanSettings: null,
  databaseVerified: false
})

// Computed
const isLanMode = computed(() => config.value.deploymentMode === 'lan')

const logoSrc = computed(() =>
  theme.global.current.value.dark ? '/Giljo_YW.svg' : '/Giljo_BY.svg'
)

// Dynamic step numbers based on mode
const toolsStepNumber = computed(() => isLanMode.value ? 5 : 4)
const lanConfigStepNumber = computed(() => 6)
const completeStepNumber = computed(() => isLanMode.value ? 7 : 5)

const stepperItems = computed(() => {
  const items = [
    { title: 'Welcome', value: 1 },
    { title: 'Database', value: 2 },
    { title: 'Mode', value: 3 }
  ]

  if (isLanMode.value) {
    items.push({ title: 'Admin', value: 4 })
  }

  items.push({ title: 'AI Tools', value: toolsStepNumber.value })

  if (isLanMode.value) {
    items.push({ title: 'Network', value: lanConfigStepNumber.value })
  }

  items.push({ title: 'Complete', value: completeStepNumber.value })

  return items
})

// Methods
const handleWelcomeNext = () => {
  currentStep.value = 2
}

const handleDatabaseNext = () => {
  config.value.databaseVerified = true
  currentStep.value = 3
}

const handleDeploymentModeNext = () => {
  if (isLanMode.value) {
    currentStep.value = 4 // Admin account
  } else {
    currentStep.value = toolsStepNumber.value // AI tools
  }
}

const handleAdminAccountNext = () => {
  currentStep.value = toolsStepNumber.value
}

const handleToolsNext = () => {
  if (isLanMode.value) {
    currentStep.value = lanConfigStepNumber.value
  } else {
    currentStep.value = completeStepNumber.value
  }
}

const handleLanConfigNext = () => {
  currentStep.value = completeStepNumber.value
}

const handleBack = () => {
  currentStep.value--
}

const handleFinish = async () => {
  try {
    // Save setup completion flag
    await saveSetupCompletion()

    // Navigate to dashboard
    router.push('/')
  } catch (error) {
    console.error('Setup completion failed:', error)
  }
}

const saveSetupCompletion = async () => {
  // API call to mark setup as complete
  // This prevents wizard from showing on future visits
  const response = await fetch('/api/setup/complete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config.value)
  })

  if (!response.ok) {
    throw new Error('Failed to save setup completion')
  }
}

// Lifecycle
onMounted(() => {
  // Check if setup already completed
  checkSetupStatus()
})

const checkSetupStatus = async () => {
  try {
    const response = await fetch('/api/setup/status')
    const data = await response.json()

    if (data.completed) {
      // Setup already done, redirect to dashboard
      router.push('/')
    }
  } catch (error) {
    console.error('Failed to check setup status:', error)
  }
}
</script>
```

### 1.4 Styles
```vue
<style scoped>
.setup-wizard {
  min-height: 100vh;
  padding: 2rem 1rem;
}

.wizard-card {
  border-radius: 16px;
}

/* Prevent transitions on initial load */
:global(.no-transition) .v-stepper {
  transition: none !important;
}
</style>
```

---

## 2. Step Components

### 2.1 WelcomeStep.vue

#### Props
None

#### Events
- `@next` - Emitted when user clicks "Get Started"

#### Template
```vue
<template>
  <v-card-text class="pa-8">
    <!-- Welcome message -->
    <h1 class="text-h4 text-center mb-2">Welcome to GiljoAI MCP</h1>
    <p class="text-h6 text-center text-medium-emphasis mb-8">
      Multi-Agent Coding Orchestrator
    </p>

    <!-- Checklist -->
    <v-card variant="tonal" class="mb-6">
      <v-card-text>
        <p class="text-subtitle-1 mb-4">This wizard will help you:</p>
        <v-list density="compact" class="bg-transparent">
          <v-list-item prepend-icon="mdi-check-circle" title="Verify PostgreSQL database connection" />
          <v-list-item prepend-icon="mdi-check-circle" title="Choose your deployment mode" />
          <v-list-item prepend-icon="mdi-check-circle" title="Configure AI tool integration" />
          <v-list-item prepend-icon="mdi-check-circle" title="Complete initial system setup" />
        </v-list>
        <p class="text-caption mt-4">Estimated time: 5-10 minutes</p>
      </v-card-text>
    </v-card>

    <!-- Progress -->
    <v-card variant="outlined" class="mb-6">
      <v-card-text>
        <div class="d-flex justify-space-between mb-2">
          <span class="text-caption">Progress: Step 1 of 7</span>
          <span class="text-caption">14%</span>
        </div>
        <v-progress-linear :model-value="14" color="primary" />
      </v-card-text>
    </v-card>

    <!-- Action buttons -->
    <div class="text-center">
      <v-btn
        color="primary"
        size="large"
        @click="$emit('next')"
      >
        Get Started
        <v-icon end>mdi-arrow-right</v-icon>
      </v-btn>
    </div>
  </v-card-text>
</template>

<script setup>
defineEmits(['next'])
</script>
```

---

### 2.2 DatabaseStep.vue

#### Props
None (uses extracted DatabaseConnection component)

#### Events
- `@next` - Emitted when database connection verified
- `@back` - Emitted when user navigates back

#### Template
```vue
<template>
  <v-card-text class="pa-8">
    <h2 class="text-h5 mb-6">Database Connection</h2>

    <!-- Reusable Database Connection Component -->
    <DatabaseConnection
      :readonly="true"
      :show-test-button="true"
      :auto-test="true"
      @connection-success="handleConnectionSuccess"
      @connection-failure="handleConnectionFailure"
    />

    <!-- Troubleshooting link -->
    <div class="text-center mt-4">
      <p class="text-caption">
        Need help with database issues?
        <a href="/docs/troubleshooting/database" target="_blank" rel="noopener">
          View troubleshooting guide
        </a>
      </p>
    </div>

    <!-- Progress -->
    <v-card variant="outlined" class="mt-6 mb-6">
      <v-card-text>
        <div class="d-flex justify-space-between mb-2">
          <span class="text-caption">Progress: Step 2 of 7</span>
          <span class="text-caption">29%</span>
        </div>
        <v-progress-linear :model-value="29" color="primary" />
      </v-card-text>
    </v-card>

    <!-- Navigation buttons -->
    <div class="d-flex justify-space-between">
      <v-btn variant="outlined" @click="$emit('back')">
        <v-icon start>mdi-arrow-left</v-icon>
        Back
      </v-btn>
      <v-btn
        color="primary"
        :disabled="!connectionVerified"
        @click="$emit('next')"
      >
        Continue
        <v-icon end>mdi-arrow-right</v-icon>
      </v-btn>
    </div>
  </v-card-text>
</template>

<script setup>
import { ref } from 'vue'
import DatabaseConnection from '@/components/shared/DatabaseConnection.vue'

defineEmits(['next', 'back'])

const connectionVerified = ref(false)

const handleConnectionSuccess = () => {
  connectionVerified.value = true
}

const handleConnectionFailure = () => {
  connectionVerified.value = false
}
</script>
```

---

### 2.3 DeploymentModeStep.vue

#### Props
- `modelValue: string` - Current deployment mode ('localhost' | 'lan' | 'wan')

#### Events
- `@update:modelValue` - V-model update
- `@next` - Proceed to next step
- `@back` - Go back

#### Template
```vue
<template>
  <v-card-text class="pa-8">
    <h2 class="text-h5 mb-2">Choose Deployment Mode</h2>
    <p class="text-body-1 mb-6">How will you use GiljoAI MCP?</p>

    <v-radio-group v-model="selectedMode" class="mb-6">
      <!-- Localhost -->
      <v-card
        variant="outlined"
        class="mb-4 mode-card"
        :class="{ 'selected': selectedMode === 'localhost' }"
        @click="selectedMode = 'localhost'"
      >
        <v-card-text>
          <v-radio value="localhost">
            <template #label>
              <div class="ml-4">
                <div class="text-h6">Localhost</div>
                <div class="text-caption text-medium-emphasis">
                  Single user on this computer only
                </div>
              </div>
            </template>
          </v-radio>

          <v-list density="compact" class="mt-4 bg-transparent">
            <v-list-item prepend-icon="mdi-check" title="No network access required" />
            <v-list-item prepend-icon="mdi-check" title="No authentication needed" />
            <v-list-item prepend-icon="mdi-check" title="Fastest performance" />
            <v-list-item prepend-icon="mdi-check" title="Recommended for personal use" />
          </v-list>
        </v-card-text>
      </v-card>

      <!-- LAN -->
      <v-card
        variant="outlined"
        class="mb-4 mode-card"
        :class="{ 'selected': selectedMode === 'lan' }"
        @click="selectedMode = 'lan'"
      >
        <v-card-text>
          <v-radio value="lan">
            <template #label>
              <div class="ml-4">
                <div class="text-h6">LAN (Local Area Network)</div>
                <div class="text-caption text-medium-emphasis">
                  Team access on your local network
                </div>
              </div>
            </template>
          </v-radio>

          <v-list density="compact" class="mt-4 bg-transparent">
            <v-list-item prepend-icon="mdi-check" title="Multiple users can connect" />
            <v-list-item prepend-icon="mdi-check" title="Requires admin account setup" />
            <v-list-item prepend-icon="mdi-check" title="Firewall configuration needed" />
            <v-list-item prepend-icon="mdi-check" title="Recommended for teams (2-10 users)" />
          </v-list>
        </v-card-text>
      </v-card>

      <!-- WAN (disabled) -->
      <v-card
        variant="outlined"
        class="mb-4 mode-card disabled"
        disabled
      >
        <v-card-text>
          <v-radio value="wan" disabled>
            <template #label>
              <div class="ml-4">
                <div class="text-h6 text-disabled">
                  WAN (Wide Area Network)
                  <v-chip size="small" color="info" class="ml-2">Coming Soon</v-chip>
                </div>
                <div class="text-caption text-medium-emphasis">
                  Internet access for remote teams
                </div>
              </div>
            </template>
          </v-radio>

          <v-list density="compact" class="mt-4 bg-transparent">
            <v-list-item prepend-icon="mdi-close" title="Coming in Phase 1" class="text-disabled" />
            <v-list-item prepend-icon="mdi-close" title="Requires SSL/TLS certificates" class="text-disabled" />
            <v-list-item prepend-icon="mdi-close" title="Advanced security features" class="text-disabled" />
          </v-list>
        </v-card-text>
      </v-card>
    </v-radio-group>

    <!-- Info -->
    <v-alert type="info" variant="tonal" class="mb-6">
      You can change this setting later in Settings &gt; General
    </v-alert>

    <!-- Progress -->
    <v-card variant="outlined" class="mb-6">
      <v-card-text>
        <div class="d-flex justify-space-between mb-2">
          <span class="text-caption">Progress: Step 3 of 7</span>
          <span class="text-caption">43%</span>
        </div>
        <v-progress-linear :model-value="43" color="primary" />
      </v-card-text>
    </v-card>

    <!-- Navigation -->
    <div class="d-flex justify-space-between">
      <v-btn variant="outlined" @click="$emit('back')">
        <v-icon start>mdi-arrow-left</v-icon>
        Back
      </v-btn>
      <v-btn
        color="primary"
        :disabled="!selectedMode"
        @click="handleNext"
      >
        Continue
        <v-icon end>mdi-arrow-right</v-icon>
      </v-btn>
    </div>
  </v-card-text>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['update:modelValue', 'next', 'back'])

const selectedMode = ref(props.modelValue)

watch(selectedMode, (newVal) => {
  emit('update:modelValue', newVal)
})

const handleNext = () => {
  emit('next')
}
</script>

<style scoped>
.mode-card {
  cursor: pointer;
  transition: all 0.2s ease;
}

.mode-card.selected {
  border-color: rgb(var(--v-theme-primary));
  border-width: 2px;
}

.mode-card.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
```

---

### 2.4 AdminAccountStep.vue

See full specification in previous UX document. Key features:
- Username validation with availability check
- Email validation (optional)
- Password strength indicator
- Confirm password matching
- Real-time validation feedback

---

### 2.5 ToolIntegrationStep.vue

#### Props
- `modelValue: Array` - Configured AI tools
- `deploymentMode: string` - Current deployment mode

#### Events
- `@update:modelValue` - V-model update
- `@next` - Proceed
- `@back` - Go back

#### Child Components
- `ToolDetectionList.vue`
- `ConfigPreviewDialog.vue`

---

### 2.6 LanConfigStep.vue

#### Props
- `modelValue: Object` - LAN configuration

#### Events
- `@update:modelValue` - V-model update
- `@next` - Proceed
- `@back` - Go back

#### Child Components
- `FirewallInstructions.vue`

---

### 2.7 CompleteStep.vue

#### Props
- `config: Object` - Complete wizard configuration

#### Events
- `@finish` - Complete setup and navigate to dashboard

#### Child Components
- `ConfigurationSummary.vue`

---

## 3. Shared/Reusable Components

### 3.1 DatabaseConnection.vue

**Location**: `frontend/src/components/shared/DatabaseConnection.vue`

#### Responsibility
Extracted from SettingsView.vue, this component provides database connection testing UI that can be used in both the Setup Wizard and Settings page.

#### Props
```typescript
interface Props {
  readonly?: boolean           // Lock fields (default: false)
  showTestButton?: boolean     // Show test button (default: true)
  autoTest?: boolean          // Auto-test on mount (default: false)
  showReloadButton?: boolean  // Show reload button (default: false)
}
```

#### Events
```typescript
interface Events {
  'connection-success': (result: ConnectionResult) => void
  'connection-failure': (error: ConnectionError) => void
  'test-started': () => void
  'test-completed': () => void
}
```

#### Data Model
```typescript
interface ConnectionResult {
  success: boolean
  message: string
  details?: {
    host: string
    port: number
    database: string
  }
}

interface ConnectionError {
  success: false
  message: string
  error: string
  suggestions?: string[]
}
```

#### Template Structure
```vue
<template>
  <div class="database-connection">
    <!-- Info Alert -->
    <v-alert type="info" variant="tonal" class="mb-4">
      <strong>Database settings are configured during installation</strong>
      <div class="text-caption mt-1">
        {{ readonly ? 'Settings are read-only' : 'Future - Configurable settings' }}
      </div>
    </v-alert>

    <!-- Connection Fields -->
    <v-row>
      <v-col cols="12" md="6">
        <v-text-field
          v-model="settings.host"
          label="Host"
          variant="outlined"
          :readonly="readonly"
          :prepend-inner-icon="readonly ? 'mdi-lock' : undefined"
          hint="Host configuration"
          persistent-hint
        />
      </v-col>

      <!-- ... other fields ... -->
    </v-row>

    <!-- Test Result Alert -->
    <v-alert
      v-if="testResult"
      :type="testResult.success ? 'success' : 'error'"
      variant="tonal"
      class="my-4"
    >
      {{ testResult.message }}
    </v-alert>

    <!-- Action Buttons -->
    <div class="d-flex ga-2">
      <v-btn
        v-if="showTestButton"
        variant="outlined"
        :loading="testing"
        @click="testConnection"
      >
        <v-icon start>mdi-database-check</v-icon>
        Test Connection
      </v-btn>

      <v-btn
        v-if="showReloadButton"
        variant="text"
        @click="loadSettings"
      >
        <v-icon start>mdi-refresh</v-icon>
        Reload from Config
      </v-btn>
    </div>
  </div>
</template>
```

See `database_component_extraction.md` for complete implementation details.

---

### 3.2 ToolDetectionList.vue

#### Responsibility
Display list of detected AI tools with configuration options

#### Props
```typescript
interface Props {
  deploymentMode: 'localhost' | 'lan' | 'wan'
}
```

#### Events
```typescript
interface Events {
  'tool-configured': (tool: ConfiguredTool) => void
  'tool-tested': (tool: Tool, result: TestResult) => void
}
```

---

### 3.3 ConfigPreviewDialog.vue

#### Responsibility
Show configuration JSON preview before applying

#### Props
```typescript
interface Props {
  modelValue: boolean  // Dialog visibility
  tool: Tool          // Tool being configured
  config: object      // Generated configuration
  configPath: string  // Where config will be written
}
```

#### Events
```typescript
interface Events {
  'update:modelValue': (visible: boolean) => void
  'apply': () => void
  'cancel': () => void
}
```

---

### 3.4 FirewallInstructions.vue

#### Responsibility
Platform-specific firewall configuration instructions

#### Props
```typescript
interface Props {
  platform: 'windows' | 'linux' | 'macos'
  port: number
  networkUrl: string
}
```

---

### 3.5 ConfigurationSummary.vue

#### Responsibility
Display final configuration summary on completion step

#### Props
```typescript
interface Props {
  config: WizardConfig
}

interface WizardConfig {
  deploymentMode: string
  databaseVerified: boolean
  adminAccount?: AdminAccount
  aiTools: Tool[]
  lanSettings?: LanSettings
}
```

---

## 4. Composables

### 4.1 useWizardNavigation.js

```javascript
import { computed } from 'vue'

export function useWizardNavigation(config) {
  const isLanMode = computed(() => config.value.deploymentMode === 'lan')

  const getStepNumber = (baseName) => {
    const stepMap = {
      welcome: 1,
      database: 2,
      deploymentMode: 3,
      adminAccount: isLanMode.value ? 4 : null,
      tools: isLanMode.value ? 5 : 4,
      lanConfig: isLanMode.value ? 6 : null,
      complete: isLanMode.value ? 7 : 5
    }

    return stepMap[baseName]
  }

  const getTotalSteps = computed(() => {
    return isLanMode.value ? 7 : 5
  })

  const getProgressPercentage = (step) => {
    return Math.round((step / getTotalSteps.value) * 100)
  }

  return {
    isLanMode,
    getStepNumber,
    getTotalSteps,
    getProgressPercentage
  }
}
```

### 4.2 useToolDetection.js

```javascript
import { ref, onMounted } from 'vue'

export function useToolDetection() {
  const detecting = ref(false)
  const detectedTools = ref([])
  const error = ref(null)

  const detectTools = async () => {
    detecting.value = true
    error.value = null

    try {
      const response = await fetch('/api/setup/detect-tools')
      if (!response.ok) throw new Error('Detection failed')

      detectedTools.value = await response.json()
    } catch (err) {
      error.value = err.message
      console.error('Tool detection failed:', err)
    } finally {
      detecting.value = false
    }
  }

  onMounted(() => {
    detectTools()
  })

  return {
    detecting,
    detectedTools,
    error,
    detectTools
  }
}
```

### 4.3 usePasswordValidation.js

```javascript
import { computed } from 'vue'

export function usePasswordValidation(password) {
  const hasMinLength = computed(() => password.value?.length >= 8)
  const hasUppercase = computed(() => /[A-Z]/.test(password.value))
  const hasLowercase = computed(() => /[a-z]/.test(password.value))
  const hasNumber = computed(() => /\d/.test(password.value))
  const hasSpecial = computed(() => /[!@#$%^&*(),.?":{}|<>]/.test(password.value))

  const strength = computed(() => {
    const checks = [
      hasMinLength.value,
      hasUppercase.value,
      hasLowercase.value,
      hasNumber.value,
      hasSpecial.value
    ]

    const score = checks.filter(Boolean).length

    if (score < 3) return { level: 'weak', value: 20, color: 'error' }
    if (score === 3) return { level: 'fair', value: 40, color: 'warning' }
    if (score === 4) return { level: 'good', value: 60, color: 'info' }
    if (score === 5 && password.value?.length >= 10) {
      return { level: 'strong', value: 80, color: 'success' }
    }
    if (score === 5 && password.value?.length >= 12) {
      return { level: 'excellent', value: 100, color: 'success' }
    }
    return { level: 'good', value: 60, color: 'info' }
  })

  const isValid = computed(() => {
    return hasMinLength.value &&
           hasUppercase.value &&
           hasLowercase.value &&
           hasNumber.value
  })

  return {
    hasMinLength,
    hasUppercase,
    hasLowercase,
    hasNumber,
    hasSpecial,
    strength,
    isValid
  }
}
```

---

## 5. API Integration

### 5.1 Setup Service

**Location**: `frontend/src/services/setupService.js`

```javascript
import { API_CONFIG } from '@/config/api'

class SetupService {
  constructor() {
    this.baseURL = API_CONFIG.REST_API.baseURL
  }

  async checkStatus() {
    const response = await fetch(`${this.baseURL}/api/setup/status`)
    return response.json()
  }

  async testDatabaseConnection() {
    const response = await fetch(`${this.baseURL}/api/v1/config/health/database`)
    return response.json()
  }

  async detectTools() {
    const response = await fetch(`${this.baseURL}/api/setup/detect-tools`)
    return response.json()
  }

  async generateMcpConfig(tool, mode) {
    const response = await fetch(`${this.baseURL}/api/setup/generate-mcp-config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tool, mode })
    })
    return response.json()
  }

  async registerMcp(tool, config) {
    const response = await fetch(`${this.baseURL}/api/setup/register-mcp`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tool, config })
    })
    return response.json()
  }

  async testMcpConnection(tool) {
    const response = await fetch(`${this.baseURL}/api/setup/test-mcp-connection`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tool })
    })
    return response.json()
  }

  async createAdminAccount(username, password, email) {
    const response = await fetch(`${this.baseURL}/api/setup/create-admin`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, email })
    })
    return response.json()
  }

  async testPortAccess(port) {
    const response = await fetch(`${this.baseURL}/api/setup/test-port`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ port })
    })
    return response.json()
  }

  async completeSetup(config) {
    const response = await fetch(`${this.baseURL}/api/setup/complete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    })
    return response.json()
  }
}

export default new SetupService()
```

---

## 6. Route Configuration

### 6.1 Router Setup

```javascript
// frontend/src/router/index.js

const routes = [
  // ... existing routes ...

  {
    path: '/setup',
    name: 'Setup',
    component: () => import('@/views/SetupWizard.vue'),
    meta: {
      title: 'Setup Wizard',
      showInNav: false,
      requiresSetup: false // Skip setup check for this route
    }
  }
]
```

### 6.2 Navigation Guard

```javascript
// frontend/src/router/index.js

router.beforeEach(async (to, from, next) => {
  // Skip setup check for setup route itself
  if (to.meta.requiresSetup === false) {
    next()
    return
  }

  // Check if setup is complete
  try {
    const response = await fetch('/api/setup/status')
    const data = await response.json()

    if (!data.completed && to.path !== '/setup') {
      // Setup not complete, redirect to wizard
      next('/setup')
    } else if (data.completed && to.path === '/setup') {
      // Setup already done, redirect to dashboard
      next('/')
    } else {
      next()
    }
  } catch (error) {
    console.error('Setup status check failed:', error)
    next() // Continue anyway on error
  }
})
```

---

## 7. State Management

### 7.1 Setup Store (Optional)

If wizard state needs to be persisted across page refreshes:

```javascript
// frontend/src/stores/setup.js

import { defineStore } from 'pinia'

export const useSetupStore = defineStore('setup', {
  state: () => ({
    currentStep: 1,
    config: {
      deploymentMode: 'localhost',
      adminAccount: null,
      aiTools: [],
      lanSettings: null,
      databaseVerified: false
    },
    completed: false
  }),

  actions: {
    updateConfig(updates) {
      this.config = { ...this.config, ...updates }
      this.saveToLocalStorage()
    },

    setCurrentStep(step) {
      this.currentStep = step
      this.saveToLocalStorage()
    },

    markComplete() {
      this.completed = true
      this.clearLocalStorage()
    },

    saveToLocalStorage() {
      localStorage.setItem('setup-wizard-state', JSON.stringify({
        currentStep: this.currentStep,
        config: this.config
      }))
    },

    loadFromLocalStorage() {
      const saved = localStorage.getItem('setup-wizard-state')
      if (saved) {
        const data = JSON.parse(saved)
        this.currentStep = data.currentStep
        this.config = data.config
      }
    },

    clearLocalStorage() {
      localStorage.removeItem('setup-wizard-state')
    }
  }
})
```

---

## 8. Testing Considerations

### 8.1 Component Tests

Each step component should have:
- Unit tests for validation logic
- Integration tests for user interactions
- Accessibility tests (ARIA, keyboard navigation)

### 8.2 E2E Tests

Complete wizard flows:
- Localhost mode setup (5 steps)
- LAN mode setup (7 steps)
- Error handling scenarios
- Back navigation
- Form validation

---

## 9. File Structure

```
frontend/src/
├── views/
│   └── SetupWizard.vue                    # Main wizard container (route)
├── components/
│   ├── setup/                             # Setup-specific components
│   │   ├── WelcomeStep.vue
│   │   ├── DatabaseStep.vue
│   │   ├── DeploymentModeStep.vue
│   │   ├── AdminAccountStep.vue
│   │   ├── ToolIntegrationStep.vue
│   │   ├── LanConfigStep.vue
│   │   ├── CompleteStep.vue
│   │   ├── ToolDetectionList.vue
│   │   ├── ToolCard.vue
│   │   ├── ConfigPreviewDialog.vue
│   │   ├── FirewallInstructions.vue
│   │   └── ConfigurationSummary.vue
│   └── shared/                            # Reusable components
│       └── DatabaseConnection.vue         # Extracted from SettingsView
├── composables/
│   ├── useWizardNavigation.js
│   ├── useToolDetection.js
│   └── usePasswordValidation.js
├── services/
│   └── setupService.js
└── stores/
    └── setup.js (optional)
```

---

**Document Status**: Complete
**Next Document**: `database_component_extraction.md`
