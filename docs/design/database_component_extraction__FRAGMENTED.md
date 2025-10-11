# Database Component Extraction Plan

**Version**: 1.0
**Date**: 2025-10-05
**Designer**: UX Designer Agent

---

## 1. Overview

### 1.1 Purpose
Extract the database connection testing UI from `SettingsView.vue` (lines 323-643) into a reusable component `DatabaseConnection.vue` that can be used in both:
1. Setup Wizard (Step 2)
2. Settings Page (Database tab)

### 1.2 Benefits
- **DRY Principle**: Single source of truth for database UI
- **Consistency**: Identical UX across wizard and settings
- **Maintainability**: Changes in one place propagate everywhere
- **Testing**: Test once, use everywhere

---

## 2. Current Implementation Analysis

### 2.1 Source Code Location
**File**: `frontend/src/views/SettingsView.vue`
**Lines**: 323-643

### 2.2 Current Structure

**Template (lines 323-424)**:
- Database configuration info alert
- Form fields (host, port, database name, username, password)
- All fields are read-only with lock icons
- Connection test result alert
- Test Connection button
- Reload from Config button

**Script (lines 589-642)**:
- `loadDatabaseSettings()` - Fetches config from API
- `testDatabaseConnection()` - Tests connection
- State variables:
  - `testingConnection` (boolean)
  - `connectionTestResult` (object: {success, message})
  - `settings.database` (object: {type, host, port, name, user, password})

### 2.3 Dependencies
- `API_CONFIG.REST_API.baseURL` for API calls
- Vuetify components: `v-text-field`, `v-alert`, `v-btn`, `v-row`, `v-col`

---

## 3. Extracted Component Design

### 3.1 Component Specification

**Name**: `DatabaseConnection.vue`
**Location**: `frontend/src/components/shared/DatabaseConnection.vue`
**Type**: Composition API

### 3.2 Props

```typescript
interface Props {
  // Visual configuration
  readonly?: boolean           // Lock all fields (default: false)
  showTestButton?: boolean     // Display test button (default: true)
  showReloadButton?: boolean   // Display reload button (default: false)
  autoTest?: boolean          // Auto-test on component mount (default: false)

  // Initial data (optional - will fetch if not provided)
  initialSettings?: {
    type: string
    host: string
    port: number
    name: string
    user: string
    password: string
  }
}
```

**Prop Defaults**:
```javascript
const props = withDefaults(defineProps<Props>(), {
  readonly: false,
  showTestButton: true,
  showReloadButton: false,
  autoTest: false,
  initialSettings: null
})
```

### 3.3 Events

```typescript
interface Events {
  // Connection test lifecycle
  'test-started': () => void
  'test-completed': () => void
  'connection-success': (result: ConnectionResult) => void
  'connection-failure': (error: ConnectionError) => void

  // Settings reload
  'settings-loaded': (settings: DatabaseSettings) => void
  'settings-load-error': (error: Error) => void
}

interface ConnectionResult {
  success: true
  message: string
  details: {
    host: string
    port: number
    database: string
    user: string
  }
}

interface ConnectionError {
  success: false
  message: string
  error: string
  code?: string
  suggestions?: string[]
}

interface DatabaseSettings {
  type: string
  host: string
  port: number
  name: string
  user: string
  password: string // Always masked
}
```

### 3.4 Exposed Methods

```typescript
// For parent components that need programmatic control
defineExpose({
  testConnection,
  reloadSettings,
  clearTestResult
})
```

---

## 4. Component Implementation

### 4.1 Template

```vue
<template>
  <div class="database-connection">
    <!-- Info Alert -->
    <v-alert
      type="info"
      variant="tonal"
      class="mb-4"
    >
      <strong>Database settings are configured during installation</strong>
      <div class="text-caption mt-1">
        {{ readonly ? 'Settings are read-only and locked' : 'Future - Configurable settings' }}
      </div>
    </v-alert>

    <!-- Connection Fields -->
    <v-row>
      <!-- Host -->
      <v-col cols="12" md="6">
        <v-text-field
          v-model="settings.host"
          label="Host"
          variant="outlined"
          :readonly="readonly"
          :prepend-inner-icon="readonly ? 'mdi-lock' : undefined"
          hint="Database host address"
          persistent-hint
          aria-label="Database host"
        />
      </v-col>

      <!-- Port -->
      <v-col cols="12" md="6">
        <v-text-field
          v-model.number="settings.port"
          label="Port"
          type="number"
          variant="outlined"
          :readonly="readonly"
          :prepend-inner-icon="readonly ? 'mdi-lock' : undefined"
          hint="Database port number"
          persistent-hint
          aria-label="Database port"
        />
      </v-col>

      <!-- Database Name -->
      <v-col cols="12" md="6">
        <v-text-field
          v-model="settings.name"
          label="Database Name"
          variant="outlined"
          :readonly="readonly"
          :prepend-inner-icon="readonly ? 'mdi-lock' : undefined"
          hint="Name of the database"
          persistent-hint
          aria-label="Database name"
        />
      </v-col>

      <!-- Username -->
      <v-col cols="12" md="6">
        <v-text-field
          v-model="settings.user"
          label="Username"
          variant="outlined"
          :readonly="readonly"
          :prepend-inner-icon="readonly ? 'mdi-lock' : undefined"
          hint="Database username"
          persistent-hint
          aria-label="Database username"
        />
      </v-col>

      <!-- Password -->
      <v-col cols="12">
        <v-text-field
          v-model="settings.password"
          label="Password"
          type="password"
          variant="outlined"
          :readonly="readonly"
          :prepend-inner-icon="readonly ? 'mdi-lock' : undefined"
          hint="Database password (masked for security)"
          persistent-hint
          aria-label="Database password"
        />
      </v-col>
    </v-row>

    <!-- Divider -->
    <v-divider class="my-6" />

    <!-- Test Result Alert -->
    <v-alert
      v-if="testResult"
      :type="testResult.success ? 'success' : 'error'"
      variant="tonal"
      class="mb-4"
      role="alert"
      :aria-live="testResult.success ? 'polite' : 'assertive'"
    >
      <div v-html="formatTestResultMessage(testResult)"></div>
    </v-alert>

    <!-- Action Buttons -->
    <div class="d-flex ga-2 flex-wrap">
      <!-- Test Connection Button -->
      <v-btn
        v-if="showTestButton"
        variant="outlined"
        color="primary"
        :loading="testing"
        :disabled="testing"
        @click="testConnection"
        aria-label="Test database connection"
      >
        <v-icon start>mdi-database-check</v-icon>
        Test Connection
      </v-btn>

      <!-- Reload Settings Button -->
      <v-btn
        v-if="showReloadButton"
        variant="text"
        :disabled="loading || testing"
        @click="reloadSettings"
        aria-label="Reload database settings from configuration"
      >
        <v-icon start>mdi-refresh</v-icon>
        Reload from Config
      </v-btn>
    </div>
  </div>
</template>
```

### 4.2 Script (Composition API)

```vue
<script setup>
import { ref, onMounted, watch } from 'vue'
import { API_CONFIG } from '@/config/api'

// Props
const props = withDefaults(defineProps({
  readonly: {
    type: Boolean,
    default: false
  },
  showTestButton: {
    type: Boolean,
    default: true
  },
  showReloadButton: {
    type: Boolean,
    default: false
  },
  autoTest: {
    type: Boolean,
    default: false
  },
  initialSettings: {
    type: Object,
    default: null
  }
}), {})

// Emits
const emit = defineEmits([
  'test-started',
  'test-completed',
  'connection-success',
  'connection-failure',
  'settings-loaded',
  'settings-load-error'
])

// State
const settings = ref({
  type: 'postgresql',
  host: 'localhost',
  port: 5432,
  name: 'giljo_mcp',
  user: 'postgres',
  password: '********'
})

const testing = ref(false)
const loading = ref(false)
const testResult = ref(null)

// Methods
const testConnection = async () => {
  testing.value = true
  testResult.value = null
  emit('test-started')

  try {
    const response = await fetch(
      `${API_CONFIG.REST_API.baseURL}/api/v1/config/health/database`
    )

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    const result = await response.json()

    if (result.success) {
      testResult.value = {
        success: true,
        message: `Connected to PostgreSQL database '${settings.value.name}' on ${settings.value.host}:${settings.value.port}`,
        details: {
          host: settings.value.host,
          port: settings.value.port,
          database: settings.value.name,
          user: settings.value.user
        }
      }
      emit('connection-success', testResult.value)
    } else {
      testResult.value = {
        success: false,
        message: result.error || 'Database connection failed',
        error: result.error,
        code: result.code,
        suggestions: generateSuggestions(result)
      }
      emit('connection-failure', testResult.value)
    }
  } catch (error) {
    testResult.value = {
      success: false,
      message: `Connection test failed: ${error.message}`,
      error: error.message,
      suggestions: generateSuggestions(error)
    }
    emit('connection-failure', testResult.value)
  } finally {
    testing.value = false
    emit('test-completed')
  }
}

const reloadSettings = async () => {
  loading.value = true
  testResult.value = null

  try {
    const response = await fetch(
      `${API_CONFIG.REST_API.baseURL}/api/v1/config/database`
    )

    if (!response.ok) {
      throw new Error('Failed to load database configuration')
    }

    const config = await response.json()

    settings.value = {
      type: 'postgresql',
      host: config.host || 'localhost',
      port: config.port || 5432,
      name: config.name || 'giljo_mcp',
      user: config.user || 'postgres',
      password: '********' // Always masked
    }

    testResult.value = {
      success: true,
      message: 'Settings loaded from configuration'
    }

    emit('settings-loaded', settings.value)
  } catch (error) {
    testResult.value = {
      success: false,
      message: `Failed to load settings: ${error.message}`,
      error: error.message
    }
    emit('settings-load-error', error)
  } finally {
    loading.value = false
  }
}

const clearTestResult = () => {
  testResult.value = null
}

const formatTestResultMessage = (result) => {
  if (result.success) {
    return result.message
  }

  let html = `<strong>${result.message}</strong>`

  if (result.suggestions && result.suggestions.length > 0) {
    html += '<div class="mt-2 text-caption"><strong>Possible causes:</strong></div>'
    html += '<ul class="mt-1 ml-4">'
    result.suggestions.forEach(suggestion => {
      html += `<li class="text-caption">${suggestion}</li>`
    })
    html += '</ul>'
  }

  return html
}

const generateSuggestions = (error) => {
  const suggestions = []

  const errorMsg = error.message || error.error || ''

  if (errorMsg.includes('ECONNREFUSED') || errorMsg.includes('Connection refused')) {
    suggestions.push('PostgreSQL service may not be running')
    suggestions.push('Verify PostgreSQL is installed and started')
    suggestions.push('Check if port 5432 is in use by another application')
  }

  if (errorMsg.includes('timeout') || errorMsg.includes('ETIMEDOUT')) {
    suggestions.push('Network timeout - check firewall settings')
    suggestions.push('Verify host address is correct')
  }

  if (errorMsg.includes('authentication') || errorMsg.includes('password')) {
    suggestions.push('Check username and password')
    suggestions.push('Verify PostgreSQL authentication configuration (pg_hba.conf)')
  }

  if (errorMsg.includes('database') && errorMsg.includes('does not exist')) {
    suggestions.push('Database may not have been created during installation')
    suggestions.push('Run database initialization script')
  }

  if (suggestions.length === 0) {
    suggestions.push('Check PostgreSQL service status')
    suggestions.push('Verify connection details are correct')
    suggestions.push('Review PostgreSQL logs for errors')
  }

  return suggestions
}

// Watchers
watch(() => props.initialSettings, (newSettings) => {
  if (newSettings) {
    settings.value = { ...newSettings }
  }
}, { immediate: true })

// Lifecycle
onMounted(async () => {
  // Load settings if not provided via props
  if (!props.initialSettings) {
    await reloadSettings()
  }

  // Auto-test if enabled
  if (props.autoTest) {
    // Small delay to allow UI to settle
    setTimeout(() => {
      testConnection()
    }, 500)
  }
})

// Expose methods for parent components
defineExpose({
  testConnection,
  reloadSettings,
  clearTestResult
})
</script>
```

### 4.3 Styles

```vue
<style scoped>
.database-connection {
  width: 100%;
}

/* Improve readability of suggestion lists */
:deep(ul) {
  list-style-type: disc;
  padding-left: 1.5rem;
}

:deep(li) {
  margin-bottom: 0.25rem;
}
</style>
```

---

## 5. Usage Examples

### 5.1 Setup Wizard (DatabaseStep.vue)

```vue
<template>
  <v-card-text class="pa-8">
    <h2 class="text-h5 mb-6">Database Connection</h2>

    <!-- Reusable Component -->
    <DatabaseConnection
      :readonly="true"
      :show-test-button="true"
      :show-reload-button="false"
      :auto-test="true"
      @connection-success="handleSuccess"
      @connection-failure="handleFailure"
    />

    <!-- Troubleshooting Link -->
    <div class="text-center mt-4">
      <p class="text-caption">
        Need help?
        <a href="/docs/troubleshooting/database" target="_blank">
          View troubleshooting guide
        </a>
      </p>
    </div>

    <!-- Navigation -->
    <div class="d-flex justify-space-between mt-6">
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

const handleSuccess = (result) => {
  connectionVerified.value = true
  console.log('Database connected:', result)
}

const handleFailure = (error) => {
  connectionVerified.value = false
  console.error('Database connection failed:', error)
}
</script>
```

### 5.2 Settings Page (SettingsView.vue)

```vue
<template>
  <v-window-item value="database">
    <v-card>
      <v-card-title>PostgreSQL Database Configuration</v-card-title>
      <v-card-text>
        <!-- Reusable Component -->
        <DatabaseConnection
          :readonly="true"
          :show-test-button="true"
          :show-reload-button="true"
          :auto-test="false"
          @connection-success="handleSuccess"
          @connection-failure="handleFailure"
          @settings-loaded="handleSettingsLoaded"
        />
      </v-card-text>
    </v-card>
  </v-window-item>
</template>

<script setup>
import DatabaseConnection from '@/components/shared/DatabaseConnection.vue'

const handleSuccess = (result) => {
  console.log('Connection test passed:', result)
  // Could show toast notification
}

const handleFailure = (error) => {
  console.error('Connection test failed:', error)
  // Could show error toast
}

const handleSettingsLoaded = (settings) => {
  console.log('Settings reloaded:', settings)
}
</script>
```

### 5.3 Programmatic Control Example

```vue
<template>
  <DatabaseConnection
    ref="dbConnection"
    :readonly="false"
    :show-test-button="false"
  />

  <!-- External test button -->
  <v-btn @click="runTest">Run External Test</v-btn>
  <v-btn @click="clearResults">Clear Results</v-btn>
</template>

<script setup>
import { ref } from 'vue'
import DatabaseConnection from '@/components/shared/DatabaseConnection.vue'

const dbConnection = ref(null)

const runTest = () => {
  dbConnection.value?.testConnection()
}

const clearResults = () => {
  dbConnection.value?.clearTestResult()
}
</script>
```

---

## 6. Migration Steps

### 6.1 Step 1: Create Component File

1. Create `frontend/src/components/shared/DatabaseConnection.vue`
2. Implement component as specified above

### 6.2 Step 2: Update SettingsView.vue

**Before** (lines 323-643):
```vue
<!-- Inline database testing UI -->
```

**After**:
```vue
<template>
  <v-window-item value="database">
    <v-card>
      <v-card-title>PostgreSQL Database Configuration</v-card-title>
      <v-card-text>
        <DatabaseConnection
          :readonly="true"
          :show-test-button="true"
          :show-reload-button="true"
          @connection-success="handleDatabaseSuccess"
          @connection-failure="handleDatabaseFailure"
        />
      </v-card-text>
    </v-card>
  </v-window-item>
</template>

<script setup>
import DatabaseConnection from '@/components/shared/DatabaseConnection.vue'

const handleDatabaseSuccess = (result) => {
  console.log('Database connected:', result)
}

const handleDatabaseFailure = (error) => {
  console.error('Database connection failed:', error)
}
</script>
```

### 6.3 Step 3: Create DatabaseStep.vue

Create new wizard step component using the extracted component (see usage example above).

### 6.4 Step 4: Test Both Implementations

- Verify Settings page database tab works identically
- Verify Setup Wizard step 2 works correctly
- Test all states: loading, success, error
- Verify accessibility (keyboard navigation, screen readers)

### 6.5 Step 5: Remove Old Code

Remove old inline implementation from SettingsView.vue (lines 323-643 in script section).

---

## 7. Testing Checklist

### 7.1 Functional Tests

- [ ] Component loads with default settings
- [ ] Component loads with initial settings prop
- [ ] Test connection succeeds with valid database
- [ ] Test connection fails gracefully with invalid credentials
- [ ] Test connection handles network errors
- [ ] Reload settings fetches from API
- [ ] Auto-test runs on mount when enabled
- [ ] Events are emitted correctly
- [ ] Exposed methods work when called programmatically

### 7.2 Visual Tests

- [ ] Read-only mode displays lock icons
- [ ] Editable mode allows input (future feature)
- [ ] Loading states show spinners correctly
- [ ] Success alerts display in green
- [ ] Error alerts display in red
- [ ] Responsive layout works on mobile
- [ ] Buttons are properly sized and aligned

### 7.3 Accessibility Tests

- [ ] All form fields have labels
- [ ] ARIA labels present where needed
- [ ] Keyboard navigation works (Tab, Enter)
- [ ] Focus indicators visible
- [ ] Screen reader announces alerts
- [ ] Error messages have role="alert"
- [ ] Success messages have aria-live="polite"

### 7.4 Integration Tests

- [ ] Works correctly in SettingsView
- [ ] Works correctly in Setup Wizard
- [ ] No console errors or warnings
- [ ] No prop type warnings
- [ ] Events are caught by parent components

---

## 8. Backwards Compatibility

### 8.1 Settings Page

The extracted component must maintain **100% functional parity** with the current Settings page implementation:

- Same visual appearance
- Same behavior
- Same API calls
- Same error handling

### 8.2 API Contract

The component relies on these API endpoints:
- `GET /api/v1/config/database` - Fetch database configuration
- `GET /api/v1/config/health/database` - Test connection

These endpoints must remain unchanged.

---

## 9. Future Enhancements

### 9.1 Editable Mode (Phase 1+)

Currently read-only. Future version could allow editing:
- Remove `readonly` prop check
- Add validation rules
- Add save functionality
- Emit `@settings-changed` event

### 9.2 Advanced Diagnostics

- Connection latency measurement
- Query performance test
- Database version detection
- Table/schema verification

### 9.3 Multiple Database Support

- Support for different database types (MySQL, MongoDB)
- Connection pool status
- Replica/failover configuration

---

## 10. Documentation

### 10.1 Component JSDoc

```vue
<script setup>
/**
 * DatabaseConnection - Reusable database connection testing component
 *
 * @component
 * @example
 * <DatabaseConnection
 *   :readonly="true"
 *   :show-test-button="true"
 *   :auto-test="true"
 *   @connection-success="handleSuccess"
 *   @connection-failure="handleFailure"
 * />
 *
 * @prop {boolean} [readonly=false] - Lock all fields for read-only display
 * @prop {boolean} [showTestButton=true] - Show test connection button
 * @prop {boolean} [showReloadButton=false] - Show reload settings button
 * @prop {boolean} [autoTest=false] - Auto-test connection on mount
 * @prop {object} [initialSettings=null] - Initial database settings
 *
 * @emits test-started - Emitted when connection test begins
 * @emits test-completed - Emitted when connection test finishes
 * @emits connection-success - Emitted on successful connection (result: ConnectionResult)
 * @emits connection-failure - Emitted on connection failure (error: ConnectionError)
 * @emits settings-loaded - Emitted when settings are loaded (settings: DatabaseSettings)
 * @emits settings-load-error - Emitted on settings load error (error: Error)
 *
 * @exposes testConnection - Programmatically run connection test
 * @exposes reloadSettings - Programmatically reload settings from API
 * @exposes clearTestResult - Clear the current test result
 */
</script>
```

### 10.2 README Entry

Add to component documentation:

```markdown
## DatabaseConnection

Reusable component for displaying and testing PostgreSQL database connections.

### Features
- Read-only and editable modes
- Connection testing with detailed error messages
- Settings reload from API
- Auto-test on mount
- Comprehensive event emission for parent integration

### Usage
See `docs/design/database_component_extraction.md` for complete usage examples.
```

---

**Document Status**: Complete
**Next Document**: `error_handling_ux.md`
