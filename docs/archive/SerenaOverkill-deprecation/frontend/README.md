# Frontend - Complex Serena Implementation

This directory contains the complex Vue.js component for Serena MCP detection and attachment.

## File

### SerenaAttachStep_complex.vue (349 lines)

**Purpose**: Wizard step for detecting and attaching Serena MCP to Claude Code

**Component Location**: `frontend/src/components/setup/SerenaAttachStep.vue`
**Step**: 2 of 4 in setup wizard

## Component Architecture

### State Machine

```
┌─────────────────┐
│  not_detected   │ Initial state
└────────┬────────┘
         │ detectSerena() → Serena found
         ↓
┌─────────────────┐
│    detected     │ Ready to attach
└────────┬────────┘
         │ attachSerena() → Attachment successful
         ↓
┌─────────────────┐
│   configured    │ Final state
└─────────────────┘
```

**State Transitions**:
1. **not_detected** → **detected**: User installs Serena, clicks "Check Again"
2. **detected** → **configured**: User clicks "Attach to Claude Code"
3. **Any state** → **not_detected**: Detection fails or user uninstalls

### UI States

#### State: not_detected
```vue
<v-card-text>
  <v-icon size="64" color="warning">mdi-code-braces-box</v-icon>
  <h3>Serena MCP Not Detected</h3>
  <p>Serena MCP provides semantic code analysis...</p>
  <v-btn @click="openInstallDialog">How to Install</v-btn>
  <v-btn @click="handleSkip">Skip</v-btn>
</v-card-text>
```

**Features**:
- Warning icon (amber)
- Installation guide button
- Skip option
- No blocking behavior

#### State: detected
```vue
<v-card-text>
  <v-icon size="64" color="success">mdi-check-circle</v-icon>
  <h3>Serena MCP Detected</h3>
  <v-chip color="success">Detected</v-chip>
  <p>Serena MCP is installed and ready to attach...</p>
  <v-btn @click="attachSerena">Attach to Claude Code</v-btn>
</v-card-text>
```

**Features**:
- Success icon (green)
- Status chip
- Attach button (primary action)
- Loading state during attachment

#### State: configured
```vue
<v-card-text>
  <v-icon size="64" color="success">mdi-check-decagram</v-icon>
  <h3>Serena MCP Configured</h3>
  <v-chip color="success">Configured</v-chip>
  <v-alert type="success">
    <strong>Next:</strong> Relaunch Claude Code CLI
  </v-alert>
</v-card-text>
```

**Features**:
- Success icon with special badge
- Configured chip
- Next steps alert
- Celebration state

## Component Logic

### Methods

#### detectSerena()
```javascript
const detectSerena = async () => {
  checking.value = true
  try {
    const result = await setupService.detectSerena()
    if (result.installed) {
      state.value = 'detected'
    } else {
      state.value = 'not_detected'
    }
  } catch (error) {
    errorMessage.value = `Detection failed: ${error.message}`
  } finally {
    checking.value = false
  }
}
```

**API Call**: `GET /api/setup/detect-serena`
**Response**: `{installed: bool, uvx_available: bool, version: str, error: str}`

**Why This Is Wrong**:
- Can't reliably detect if Claude Code has Serena
- Subprocess detection via API is unreliable
- Detection state doesn't guarantee usability

#### attachSerena()
```javascript
const attachSerena = async () => {
  attaching.value = true
  try {
    const result = await setupService.attachSerena()
    if (result.success) {
      state.value = 'configured'
      isConfigured.value = true
      emit('update:modelValue', true)
    } else {
      errorMessage.value = result.error
    }
  } catch (error) {
    errorMessage.value = `Attachment failed: ${error.message}`
  } finally {
    attaching.value = false
  }
}
```

**API Call**: `POST /api/setup/attach-serena`
**Response**: `{success: bool, backup_path: str, error: str}`

**Why This Is Wrong**:
- Modifies ~/.claude.json (file outside our control)
- Can't handle multiple project folders
- "Configured" state is misleading (user might not restart Claude Code)

#### checkAgain()
```javascript
const checkAgain = () => {
  detectSerena()
}
```

**Purpose**: Re-run detection after user installs Serena

**Why This Is Wrong**:
- User knows if they installed Serena
- Detection might show installed but not configured in Claude Code

### Installation Dialog

```vue
<v-dialog v-model="showInstallDialog" max-width="600">
  <v-card>
    <v-tabs v-model="installTab">
      <v-tab value="uvx">Using uvx (Recommended)</v-tab>
      <v-tab value="local">Local Installation</v-tab>
    </v-tabs>

    <v-tabs-window v-model="installTab">
      <!-- uvx tab -->
      <code>uvx mcp-server-serena</code>

      <!-- local tab -->
      <code>git clone https://github.com/apify/mcp-server-serena.git</code>
      <code>cd mcp-server-serena</code>
      <code>uv sync</code>
    </v-tabs-window>

    <v-btn @click="checkAgain">Check Again</v-btn>
  </v-card>
</v-dialog>
```

**Features**:
- Two installation methods (uvx, local)
- Copy-paste commands
- Re-check button

**What's Good Here**:
- Installation instructions are valuable
- Clear commands for users
- Multiple installation paths

**What Could Stay**:
- Keep the installation guide (just make it informational only)
- Remove detection/attachment functionality

## Component Props and Events

### Props
```javascript
const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  }
})
```

**Purpose**: Two-way binding for configured state

### Events
```javascript
const emit = defineEmits([
  'update:modelValue',  // Update configured state
  'next',               // Proceed to next wizard step
  'back',               // Return to previous step
  'skip'                // Skip Serena setup
])
```

## Reactive State

```javascript
const state = ref('not_detected')      // State machine
const isConfigured = ref(false)        // Configured flag
const attaching = ref(false)           // Loading state for attachment
const checking = ref(false)            // Loading state for detection
const errorMessage = ref('')           // Error display
const showInstallDialog = ref(false)   // Dialog visibility
const installTab = ref('uvx')          // Selected install method
```

## Lifecycle

```javascript
onMounted(() => {
  detectSerena()  // Detect on component mount
})
```

**Why This Is Wrong**:
- Automatic detection on mount triggers subprocess call
- Slows down wizard loading
- Detection result might be wrong anyway

## Styling

```vue
<style scoped>
.serena-card {
  transition: all 0.2s ease;
  border-width: 2px;
}

.serena-card:hover {
  border-color: rgb(var(--v-theme-primary));
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.serena-configured {
  border-color: rgb(var(--v-theme-success));
  background-color: rgba(var(--v-theme-success), 0.05);
}

code {
  background-color: rgba(var(--v-theme-surface-variant), 0.5);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
}
</style>
```

**What's Good**:
- Clean, professional styling
- Good visual feedback
- Accessible design

## User Flow

### Happy Path
1. User lands on SerenaAttachStep (Step 2 of 4)
2. Component auto-detects: `state = 'not_detected'`
3. User clicks "How to Install"
4. User follows installation instructions
5. User clicks "Check Again"
6. Detection succeeds: `state = 'detected'`
7. User clicks "Attach to Claude Code"
8. Attachment succeeds: `state = 'configured'`
9. User clicks "Continue" to next step

### Skip Path
1. User lands on SerenaAttachStep
2. User clicks "Skip"
3. Component emits 'skip' event
4. Wizard proceeds to next step

### Error Path
1. User clicks "Attach to Claude Code"
2. Attachment fails (e.g., .claude.json permissions)
3. Error message displayed
4. User can retry or skip

## What Should Have Been Built Instead

### Simple Approach

```vue
<template>
  <v-card-text>
    <h2>Advanced Code Analysis (Optional)</h2>

    <!-- Info about Serena -->
    <v-alert type="info">
      Serena MCP provides semantic code analysis, symbol search, and
      intelligent navigation. It's optional but enhances agent capabilities.
    </v-alert>

    <!-- Installation Instructions (read-only) -->
    <v-expansion-panels>
      <v-expansion-panel title="How to Install Serena MCP">
        <v-expansion-panel-text>
          <h4>Using uvx (Recommended)</h4>
          <code>uvx mcp-server-serena</code>

          <h4>Configure Claude Code</h4>
          <p>Add to your <code>~/.claude.json</code>:</p>
          <code>
            {
              "mcpServers": {
                "serena": {
                  "command": "uvx",
                  "args": ["serena"]
                }
              }
            }
          </code>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>

    <!-- Toggle for prompt inclusion -->
    <v-switch
      v-model="useSerenaMCP"
      label="Include Serena MCP instructions in agent prompts"
      hint="Enable this after installing Serena MCP"
      persistent-hint
    />

    <!-- Navigation -->
    <div class="d-flex justify-space-between">
      <v-btn @click="$emit('back')">Back</v-btn>
      <v-btn color="primary" @click="$emit('next')">Continue</v-btn>
    </div>
  </v-card-text>
</template>

<script setup>
import { ref } from 'vue'
import { updateConfig } from '@/services/configService'

const useSerenaMCP = ref(false)

// Save to config.yaml on toggle
watch(useSerenaMCP, (value) => {
  updateConfig('features.serena_mcp.use_in_prompts', value)
})
</script>
```

**Lines of Code**: ~80 vs 349 (77% reduction)

**Features**:
- Installation instructions (informational)
- Simple toggle for prompt inclusion
- No detection
- No .claude.json manipulation
- No complex state machine

**What's Better**:
- Honest about what we control (prompts, not Claude Code config)
- Faster (no subprocess calls)
- More reliable (no detection failures)
- Simpler state (boolean flag vs 3-state machine)
- User manages their own environment

## Complexity Analysis

### Current (Complex)
- **Lines**: 349
- **State variables**: 7
- **Methods**: 6
- **API calls**: 2 (detect, attach)
- **External dependencies**: setupService
- **Loading states**: 2 (checking, attaching)
- **Error handling**: Complex (try/catch per method)

### Proposed (Simple)
- **Lines**: ~80
- **State variables**: 1 (toggle)
- **Methods**: 1 (save config)
- **API calls**: 1 (save config)
- **External dependencies**: configService
- **Loading states**: 0
- **Error handling**: Simple (toast notification)

## Key Lessons

### 1. State Machines Are Overkill for Toggles
Three states (not_detected → detected → configured) for what is essentially ON/OFF.

### 2. Detection Creates False Positives
"Detected" doesn't mean "usable by Claude Code"

### 3. Installation Guides Are Valuable
Keep the instructions, remove the automation.

### 4. Trust the User
User knows if they installed Serena. Let them toggle it on.

### 5. Loading States for Wrong Operations
Two loading states (checking, attaching) for operations we shouldn't do.

## What to Preserve

### Keep These Elements
- Installation instructions (make them informational)
- Clean UI design
- Professional styling
- Skip option
- Clear navigation

### Remove These Elements
- Detection logic
- Attachment logic
- State machine
- API calls for detect/attach
- Loading states for wrong operations

## Conclusion

This component demonstrates good Vue.js engineering (clean structure, reactive state,
error handling) applied to the wrong functionality. The UI is polished and the code
is well-organized, but it's solving a problem we shouldn't solve.

**Remember**: A beautiful UI for the wrong feature is still wrong.

---

**Date**: October 6, 2025
**Archive Purpose**: Learning reference for frontend overengineering
**Status**: Deprecated - rebuild with simple toggle
