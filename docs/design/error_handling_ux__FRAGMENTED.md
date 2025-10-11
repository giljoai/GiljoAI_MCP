# Setup Wizard Error Handling & UX

**Version**: 1.0
**Date**: 2025-10-05
**Designer**: UX Designer Agent

---

## 1. Error Handling Philosophy

### 1.1 Core Principles

1. **Prevention over Recovery**: Validate early and often to prevent errors
2. **Clarity over Brevity**: Specific, actionable error messages
3. **Guidance over Blame**: Help users fix problems, don't make them feel stupid
4. **Recovery over Blocking**: Always provide a path forward
5. **Context over Generic**: Error messages tailored to the specific situation

### 1.2 Error Categories

```
┌─────────────────────────────────────────┐
│  Error Severity Levels                  │
├─────────────────────────────────────────┤
│  1. Validation Errors (inline)          │
│     - Field-level validation            │
│     - Real-time feedback                │
│     - Non-blocking                      │
│                                         │
│  2. Step Errors (step-level)            │
│     - Failed operations                 │
│     - Connection failures               │
│     - Partially blocking                │
│                                         │
│  3. Critical Errors (wizard-level)      │
│     - Complete failures                 │
│     - Cannot proceed                    │
│     - Fully blocking                    │
└─────────────────────────────────────────┘
```

---

## 2. Field-Level Validation Errors

### 2.1 Username Validation (Admin Account Step)

#### Error States

**Too Short**:
```
┌─────────────────────────────────────────┐
│  Username                               │
│  ┌───────────────────────────────────┐ │
│  │ ab                                 │ │
│  └───────────────────────────────────┘ │
│  ⊗ Too short. Username must be at     │
│    least 3 characters.                 │
└─────────────────────────────────────────┘
```

**Invalid Characters**:
```
┌─────────────────────────────────────────┐
│  Username                               │
│  ┌───────────────────────────────────┐ │
│  │ admin@user                         │ │
│  └───────────────────────────────────┘ │
│  ⊗ Invalid characters. Use only       │
│    letters, numbers, hyphens, and     │
│    underscores.                        │
└─────────────────────────────────────────┘
```

**Already Taken**:
```
┌─────────────────────────────────────────┐
│  Username                               │
│  ┌───────────────────────────────────┐ │
│  │ admin                              │ │
│  └───────────────────────────────────┘ │
│  ⊗ Already taken. Please choose a     │
│    different username.                 │
└─────────────────────────────────────────┘
```

**Check Failed (Network Error)**:
```
┌─────────────────────────────────────────┐
│  Username                               │
│  ┌───────────────────────────────────┐ │
│  │ myusername                         │ │
│  └───────────────────────────────────┘ │
│  ⚠ Could not verify availability.     │
│    Network error. You can continue,    │
│    but the username may already exist. │
└─────────────────────────────────────────┘
```

#### Visual Design

```css
/* Error state */
.v-text-field.error {
  border-color: rgb(var(--v-theme-error));
}

.error-message {
  color: rgb(var(--v-theme-error));
  font-size: 0.75rem;
  margin-top: 4px;
  display: flex;
  align-items: flex-start;
  gap: 4px;
}

.error-message v-icon {
  font-size: 1rem;
  margin-top: 1px;
}
```

### 2.2 Email Validation

**Invalid Format**:
```
┌─────────────────────────────────────────┐
│  Email (optional)                       │
│  ┌───────────────────────────────────┐ │
│  │ admin@example                      │ │
│  └───────────────────────────────────┘ │
│  ⊗ Invalid email format. Expected:    │
│    user@example.com                    │
└─────────────────────────────────────────┘
```

**Valid Email**:
```
┌─────────────────────────────────────────┐
│  Email (optional)                       │
│  ┌───────────────────────────────────┐ │
│  │ admin@example.com                  │ │
│  └───────────────────────────────────┘ │
│  ✓ Valid email format                 │
└─────────────────────────────────────────┘
```

### 2.3 Password Validation

**Weak Password**:
```
┌─────────────────────────────────────────┐
│  Password                               │
│  ┌───────────────────────────────────┐ │
│  │ ••••••                          👁 │ │
│  └───────────────────────────────────┘ │
│  Password strength: ▓▓░░░░░░░░ Weak   │
│                                         │
│  Password Requirements:                 │
│  ✓ At least 8 characters               │
│  ⊗ Contains uppercase letter           │
│  ✓ Contains lowercase letter           │
│  ⊗ Contains number                     │
│  ○ Contains special character          │
└─────────────────────────────────────────┘
```

**Password Mismatch**:
```
┌─────────────────────────────────────────┐
│  Confirm Password                       │
│  ┌───────────────────────────────────┐ │
│  │ ••••••••••                      👁 │ │
│  └───────────────────────────────────┘ │
│  ⊗ Passwords do not match.            │
│    Please re-enter your password.      │
└─────────────────────────────────────────┘
```

---

## 3. Step-Level Operation Errors

### 3.1 Database Connection Errors

#### Connection Refused

```
┌─────────────────────────────────────────────────────────────┐
│  Database Connection                                        │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  (... connection fields ...)                                │
│                                                             │
│  [Test Connection]                                          │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ ⊗ Connection failed                                    │ │
│  │                                                         │ │
│  │   Could not connect to PostgreSQL database.            │ │
│  │                                                         │ │
│  │   Error: ECONNREFUSED - Connection refused             │ │
│  │                                                         │ │
│  │   Possible causes:                                     │ │
│  │   • PostgreSQL service is not running                  │ │
│  │   • Incorrect host or port                             │ │
│  │   • Firewall blocking connection                       │ │
│  │                                                         │ │
│  │   [View Troubleshooting Guide]                         │ │
│  └───────────────────────────────────────────────────────┘ │
│                             ↑ Red error alert                │
│                                                             │
│  [← Back]                              [Continue →]        │
│                                        (disabled)           │
└─────────────────────────────────────────────────────────────┘
```

#### Authentication Failure

```
┌───────────────────────────────────────────────────────────┐
│  ⊗ Authentication failed                                   │
│                                                            │
│    Could not authenticate with PostgreSQL database.       │
│                                                            │
│    Error: password authentication failed for user         │
│           "postgres"                                       │
│                                                            │
│    Possible causes:                                       │
│    • Incorrect username or password                       │
│    • Database user doesn't exist                          │
│    • pg_hba.conf not configured for password auth         │
│                                                            │
│    [View Authentication Guide]                            │
└───────────────────────────────────────────────────────────┘
```

#### Timeout Error

```
┌───────────────────────────────────────────────────────────┐
│  ⊗ Connection timeout                                      │
│                                                            │
│    Database connection timed out after 30 seconds.        │
│                                                            │
│    Error: ETIMEDOUT - Connection timed out                │
│                                                            │
│    Possible causes:                                       │
│    • Network connectivity issues                          │
│    • Firewall blocking traffic                            │
│    • PostgreSQL service is slow to respond                │
│    • Incorrect host address                               │
│                                                            │
│    [Retry Connection]  [Change Settings]                  │
└───────────────────────────────────────────────────────────┘
```

#### Database Not Found

```
┌───────────────────────────────────────────────────────────┐
│  ⊗ Database not found                                      │
│                                                            │
│    Database 'giljo_mcp' does not exist.                   │
│                                                            │
│    Error: database "giljo_mcp" does not exist             │
│                                                            │
│    Possible causes:                                       │
│    • Database was not created during installation         │
│    • Database name is incorrect                           │
│    • Connected to wrong PostgreSQL instance               │
│                                                            │
│    [Run Database Setup]  [View Installation Guide]        │
└───────────────────────────────────────────────────────────┘
```

### 3.2 AI Tool Integration Errors

#### Tool Detection Failed

```
┌───────────────────────────────────────────────────────────┐
│  Configure AI Tool Integration                             │
│  ─────────────────────────────────────────────────────────  │
│                                                            │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ ⊗ Tool detection failed                              │  │
│  │                                                       │  │
│  │   Could not scan for installed AI tools.             │  │
│  │                                                       │  │
│  │   Error: Permission denied when reading:             │  │
│  │          C:\Users\...\AppData\Roaming\               │  │
│  │                                                       │  │
│  │   You can configure tools manually instead.          │  │
│  │                                                       │  │
│  │   [Retry Detection]  [Manual Configuration]          │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                            │
│  [← Back]  [Skip This Step]               [Continue →]   │
└───────────────────────────────────────────────────────────┘
```

#### Configuration Write Failed

```
┌───────────────────────────────────────────────────────────┐
│  ⊗ Configuration failed                                    │
│                                                            │
│    Could not write configuration for Claude Code.         │
│                                                            │
│    Error: EACCES - Permission denied                      │
│           C:\Users\...\cline_mcp_settings.json            │
│                                                            │
│    Possible solutions:                                    │
│    • Close Claude Code and try again                      │
│    • Run this setup as Administrator                      │
│    • Manually create the configuration file               │
│                                                            │
│    [Retry]  [Copy Config to Clipboard]  [Skip Tool]      │
└───────────────────────────────────────────────────────────┘
```

#### Connection Test Failed

```
┌───────────────────────────────────────────────────────────┐
│  ⚠ Configuration applied, but connection test failed       │
│                                                            │
│    Configuration was written successfully, but could not   │
│    establish connection to giljo-mcp server.              │
│                                                            │
│    Error: Server did not respond                          │
│                                                            │
│    This may be normal if:                                 │
│    • GiljoAI MCP server is not currently running          │
│    • Claude Code is not open                              │
│                                                            │
│    You can test the connection later after starting       │
│    the server and restarting Claude Code.                 │
│                                                            │
│    [Test Again]  [Continue Anyway]                        │
└───────────────────────────────────────────────────────────┘
```

### 3.3 LAN Configuration Errors

#### Port Test Failed

```
┌───────────────────────────────────────────────────────────┐
│  LAN Network Configuration                                 │
│  ─────────────────────────────────────────────────────────  │
│                                                            │
│  (... firewall command ...)                                │
│                                                            │
│  [Test Port Access]                                        │
│                                                            │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ ⊗ Port 7274 appears to be blocked                    │  │
│  │                                                       │  │
│  │   The firewall may still be blocking connections.    │  │
│  │                                                       │  │
│  │   Troubleshooting steps:                             │  │
│  │   1. Verify you ran the command as Administrator    │  │
│  │   2. Check Windows Firewall settings manually       │  │
│  │   3. Disable antivirus temporarily and retry        │  │
│  │   4. Restart the GiljoAI MCP server                 │  │
│  │                                                       │  │
│  │   [Retry Test]  [View Firewall Guide]               │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                            │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ ℹ You can continue setup and configure the firewall │  │
│  │   later. Team members won't be able to connect      │  │
│  │   until the port is open.                            │  │
│  │                                                       │  │
│  │   [Continue with Blocked Port]                       │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                            │
│  [← Back]                              [Continue →]       │
│                                        (disabled unless    │
│                                         user clicks        │
│                                         "Continue Anyway") │
└───────────────────────────────────────────────────────────┘
```

#### Network Detection Failed

```
┌───────────────────────────────────────────────────────────┐
│  ⊗ Network detection failed                                │
│                                                            │
│    Could not detect your local IP address.                │
│                                                            │
│    Error: No active network interfaces found              │
│                                                            │
│    Possible causes:                                       │
│    • No network connection                                │
│    • Network adapter disabled                             │
│    • VPN or virtual network interference                  │
│                                                            │
│    You can enter your IP address manually:                │
│                                                            │
│    IP Address:                                            │
│    ┌───────────────────────────────────────┐             │
│    │ 192.168.1.100                          │             │
│    └───────────────────────────────────────┘             │
│                                                            │
│    [Retry Detection]  [Continue with Manual IP]           │
└───────────────────────────────────────────────────────────┘
```

---

## 4. Critical Wizard-Level Errors

### 4.1 API Unavailable

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│             ⊗  GiljoAI MCP Server Unavailable              │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │                                                         │ │
│  │  The GiljoAI MCP server is not responding.             │ │
│  │                                                         │ │
│  │  Error: Failed to connect to http://localhost:7272    │ │
│  │                                                         │ │
│  │  This usually means:                                   │ │
│  │  • The MCP server is not running                       │ │
│  │  • The server crashed during startup                   │ │
│  │  • The port is already in use                          │ │
│  │                                                         │ │
│  │  Troubleshooting steps:                                │ │
│  │  1. Check if server process is running                 │ │
│  │  2. Review server logs for errors                      │ │
│  │  3. Restart the MCP server                             │ │
│  │  4. Verify port 7272 is available                      │ │
│  │                                                         │ │
│  │  [Retry Connection]  [View Server Logs]                │ │
│  │  [Restart Server]    [Contact Support]                 │ │
│  │                                                         │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Unexpected Error

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│                  ⊗  Unexpected Error                       │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │                                                         │ │
│  │  Something went wrong during setup.                    │ │
│  │                                                         │ │
│  │  Error: TypeError: Cannot read property 'value'        │ │
│  │         of undefined                                    │ │
│  │                                                         │ │
│  │  This is likely a bug. Please report this error.       │ │
│  │                                                         │ │
│  │  What you can do:                                      │ │
│  │  • Restart the setup wizard                            │ │
│  │  • Report this error to support                        │ │
│  │  • Try manual configuration instead                    │ │
│  │                                                         │ │
│  │  Error details (for support):                          │ │
│  │  ┌──────────────────────────────────────────────────┐ │ │
│  │  │ TypeError: Cannot read property 'value' of       │ │ │
│  │  │ undefined                                         │ │ │
│  │  │   at handleNext (SetupWizard.vue:142)            │ │ │
│  │  │   at onClick (SetupWizard.vue:98)                │ │ │
│  │  │                                                   │ │ │
│  │  │ Browser: Chrome 120.0.0                          │ │ │
│  │  │ OS: Windows 11                                   │ │ │
│  │  │ Timestamp: 2025-10-05 14:32:17                   │ │ │
│  │  └──────────────────────────────────────────────────┘ │ │
│  │                                                         │ │
│  │  [Copy Error Details]  [Restart Wizard]                │ │
│  │  [Report Bug]          [Exit Setup]                    │ │
│  │                                                         │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Error Message Patterns

### 5.1 Message Structure

**Format**:
```
[Icon] [Primary Message]

[Secondary Details]

[Error Code/Technical Info]

[Possible Causes/Solutions]

[Action Buttons]
```

**Example**:
```
⊗ Connection failed

Could not connect to PostgreSQL database.

Error: ECONNREFUSED - Connection refused

Possible causes:
• PostgreSQL service is not running
• Incorrect host or port
• Firewall blocking connection

[Retry]  [Troubleshooting Guide]
```

### 5.2 Tone Guidelines

**DO:**
- Be specific about what went wrong
- Explain why it matters
- Provide clear next steps
- Use "you" language ("You can...")
- Suggest solutions, not just problems

**DON'T:**
- Use technical jargon without explanation
- Blame the user ("You entered an invalid...")
- Be vague ("An error occurred")
- Use passive voice ("The connection was refused")
- Just state the problem without solutions

**Good Examples:**
```
✓ "Could not connect to database. Check if PostgreSQL is running."
✓ "Username already taken. Please choose a different username."
✓ "Configuration write failed due to permissions. Try running as Administrator."
```

**Bad Examples:**
```
⊗ "Database error"
⊗ "Invalid input"
⊗ "An error occurred. Please try again."
⊗ "You made a mistake"
```

---

## 6. Error Recovery Flows

### 6.1 Database Connection Recovery

```
User clicks "Test Connection"
         ↓
Connection fails
         ↓
┌────────────────────────────┐
│ Show error with causes     │
│ and suggestions            │
└────────────────────────────┘
         ↓
┌────────────────────────────┐
│ User clicks:               │
│ • [Retry] → Test again     │
│ • [Troubleshooting] →      │
│   Open guide in new tab    │
│ • [Back] → Previous step   │
└────────────────────────────┘
```

### 6.2 Tool Configuration Recovery

```
Config write fails
         ↓
┌────────────────────────────┐
│ Show specific error        │
│ (permissions, file locked) │
└────────────────────────────┘
         ↓
┌────────────────────────────┐
│ User options:              │
│ • [Retry] → Try again      │
│ • [Copy Config] → Manual   │
│ • [Skip Tool] → Continue   │
│   without this tool        │
└────────────────────────────┘
```

### 6.3 Critical Error Recovery

```
Unexpected error occurs
         ↓
┌────────────────────────────┐
│ Catch error globally       │
│ Log to console + server    │
└────────────────────────────┘
         ↓
┌────────────────────────────┐
│ Show error boundary UI     │
│ with error details         │
└────────────────────────────┘
         ↓
┌────────────────────────────┐
│ User options:              │
│ • [Restart Wizard] →       │
│   Reload from step 1       │
│ • [Report Bug] →           │
│   Open issue template      │
│ • [Exit] → Go to dashboard │
└────────────────────────────┘
```

---

## 7. Implementation Guidelines

### 7.1 Error Boundary Component

```vue
<!-- ErrorBoundary.vue -->
<template>
  <div v-if="hasError" class="error-boundary">
    <v-container>
      <v-row justify="center">
        <v-col cols="12" md="8" lg="6">
          <v-card class="error-card">
            <v-card-title class="text-h5 text-error">
              <v-icon size="large" class="mr-2">mdi-alert-circle</v-icon>
              Unexpected Error
            </v-card-title>

            <v-card-text>
              <p class="text-body-1 mb-4">
                Something went wrong during setup.
              </p>

              <v-alert type="error" variant="outlined" class="mb-4">
                <strong>{{ error.message }}</strong>
              </v-alert>

              <p class="text-body-2 mb-4">
                This is likely a bug. Please report this error so we can fix it.
              </p>

              <!-- Error details (collapsible) -->
              <v-expansion-panels>
                <v-expansion-panel>
                  <v-expansion-panel-title>
                    Error Details (for support)
                  </v-expansion-panel-title>
                  <v-expansion-panel-text>
                    <pre class="error-stack">{{ errorInfo }}</pre>
                  </v-expansion-panel-text>
                </v-expansion-panel>
              </v-expansion-panels>
            </v-card-text>

            <v-card-actions class="pa-4">
              <v-btn
                color="primary"
                @click="restartWizard"
              >
                <v-icon start>mdi-restart</v-icon>
                Restart Wizard
              </v-btn>

              <v-btn
                variant="outlined"
                @click="copyErrorDetails"
              >
                <v-icon start>mdi-content-copy</v-icon>
                Copy Error Details
              </v-btn>

              <v-spacer />

              <v-btn
                variant="text"
                @click="exitSetup"
              >
                Exit Setup
              </v-btn>
            </v-card-actions>
          </v-card>
        </v-col>
      </v-row>
    </v-container>
  </div>

  <slot v-else />
</template>

<script setup>
import { ref, onErrorCaptured } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const hasError = ref(false)
const error = ref(null)
const errorInfo = ref('')

onErrorCaptured((err, instance, info) => {
  hasError.value = true
  error.value = err
  errorInfo.value = `${err.stack}\n\nComponent: ${instance?.$options?.name || 'Unknown'}\nInfo: ${info}`

  // Log to console
  console.error('Setup Wizard Error:', err)

  // TODO: Send to error tracking service
  // trackError(err, errorInfo.value)

  // Prevent error from propagating
  return false
})

const restartWizard = () => {
  hasError.value = false
  error.value = null
  router.push('/setup')
  window.location.reload()
}

const copyErrorDetails = async () => {
  const details = `GiljoAI MCP Setup Error\n\n${error.value.message}\n\n${errorInfo.value}`

  try {
    await navigator.clipboard.writeText(details)
    alert('Error details copied to clipboard')
  } catch (err) {
    console.error('Failed to copy:', err)
  }
}

const exitSetup = () => {
  router.push('/')
}
</script>

<style scoped>
.error-boundary {
  min-height: 100vh;
  display: flex;
  align-items: center;
  padding: 2rem;
}

.error-stack {
  font-family: 'Courier New', monospace;
  font-size: 0.75rem;
  white-space: pre-wrap;
  word-wrap: break-word;
}
</style>
```

### 7.2 Validation Composable

```javascript
// useValidation.js
import { ref, computed } from 'vue'

export function useValidation() {
  const errors = ref({})

  const addError = (field, message) => {
    errors.value[field] = message
  }

  const clearError = (field) => {
    delete errors.value[field]
  }

  const clearAllErrors = () => {
    errors.value = {}
  }

  const hasError = (field) => {
    return field in errors.value
  }

  const getError = (field) => {
    return errors.value[field]
  }

  const hasAnyErrors = computed(() => {
    return Object.keys(errors.value).length > 0
  })

  return {
    errors,
    addError,
    clearError,
    clearAllErrors,
    hasError,
    getError,
    hasAnyErrors
  }
}
```

### 7.3 Error Toast Notifications

```javascript
// useErrorToast.js
import { getCurrentInstance } from 'vue'

export function useErrorToast() {
  const instance = getCurrentInstance()
  const toast = instance?.appContext.config.globalProperties.$toast

  const showError = (message, options = {}) => {
    toast?.error(message, {
      duration: 5000,
      position: 'bottom-right',
      ...options
    })
  }

  const showValidationError = (field, message) => {
    showError(`${field}: ${message}`, { duration: 4000 })
  }

  const showSuccess = (message) => {
    toast?.success(message, {
      duration: 3000,
      position: 'bottom-right'
    })
  }

  return {
    showError,
    showValidationError,
    showSuccess
  }
}
```

---

## 8. Accessibility for Errors

### 8.1 ARIA Attributes

```vue
<!-- Error alert with proper ARIA -->
<v-alert
  v-if="error"
  type="error"
  variant="tonal"
  role="alert"
  aria-live="assertive"
  aria-atomic="true"
>
  {{ error.message }}
</v-alert>

<!-- Form field with error -->
<v-text-field
  v-model="username"
  label="Username"
  :error="hasError('username')"
  :error-messages="getError('username')"
  aria-describedby="username-error"
/>
<span id="username-error" v-if="hasError('username')" role="alert">
  {{ getError('username') }}
</span>
```

### 8.2 Keyboard Navigation

- Errors should be focusable
- Tab to action buttons in error messages
- Escape key dismisses non-critical errors
- Enter key activates primary error action

---

## 9. Error Logging

### 9.1 Client-Side Logging

```javascript
// errorLogger.js
class ErrorLogger {
  log(error, context) {
    const errorData = {
      message: error.message,
      stack: error.stack,
      context: context,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href,
      wizard_step: context.currentStep
    }

    // Log to console
    console.error('[Setup Wizard Error]', errorData)

    // Send to server
    this.sendToServer(errorData)

    // Store in localStorage for debugging
    this.storeLocally(errorData)
  }

  async sendToServer(errorData) {
    try {
      await fetch('/api/errors/log', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(errorData)
      })
    } catch (err) {
      console.error('Failed to send error to server:', err)
    }
  }

  storeLocally(errorData) {
    try {
      const errors = JSON.parse(localStorage.getItem('setup_errors') || '[]')
      errors.push(errorData)

      // Keep only last 10 errors
      if (errors.length > 10) {
        errors.shift()
      }

      localStorage.setItem('setup_errors', JSON.stringify(errors))
    } catch (err) {
      console.error('Failed to store error locally:', err)
    }
  }
}

export default new ErrorLogger()
```

---

**Document Status**: Complete
**Next Document**: `accessibility_checklist.md`
