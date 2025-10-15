# Handover 0016-B: MCP Configuration UX Enhancement (Phase 2)

**Date:** 2025-10-14
**From Agent:** UX Designer + System Architect
**To Agent:** UX Designer + Frontend Implementor (Coordinated)
**Priority:** Medium
**Estimated Complexity:** 4-5 hours
**Status:** Not Started
**Depends On:** Handover 0016-A (MUST complete stabilization first)
**Blocks:** None

---

## Task Summary

**Consolidate and enhance the MCP configuration user experience** by creating a unified, guided workflow that reduces cognitive load and provides clear validation feedback. This builds on the stabilized foundation from Phase 1 (0016-A).

**Why After Stabilization:** UX improvements require stable technical foundation. Phase 1 fixed critical bugs; Phase 2 improves user experience.

**Expected Outcome:** Single, cohesive MCP configuration interface with 80% reduction in user decisions, clear primary path, and validation feedback.

---

## Context and Background

### Audit Findings: UX Problems

**From UX Designer audit:**

1. **Fragmented Journey** - 3 separate entry points (McpIntegration, AIToolSetup, McpConfigStep)
2. **No Clear Primary Path** - 4 equal-weight actions, users don't know what to do
3. **Expansion Panel Overload** - 7+ panels, critical info buried 2-3 clicks deep
4. **Inconsistent API Key Workflow** - Auto-gen in one place, manual in another
5. **No Progress Persistence** - Users can't tell if already configured

### Strategic Direction (From Consultant Analysis)

**Approved Approach:** Enhanced copy-paste > automation
- Transparency and user control
- 10x lower maintenance burden
- Sufficient for developer audience
- Focus on confidence, not automation

### What Phase 1 Fixed

✅ Cross-platform compatibility (removed hardcoded paths)
✅ Runtime errors (fixed/removed McpConfigStep)
✅ API client consistency (using api.js everywhere)
✅ Technical debt (SECRET_KEY, alert() usage)

**Foundation is solid. Now we can build good UX on top.**

---

## Technical Details

### Files to Modify

**Primary Implementation:**

1. **`frontend/src/views/McpIntegration.vue`** (Major Redesign)
   - Consolidate: Single primary path with clear hierarchy
   - Simplify: Reduce 4 sections → 2 tabs (Quick Setup, Manual Config)
   - Enhance: Add copy-paste wizard, validator, status indicators
   - **Lines:** ~400-500 (down from 640)

2. **`frontend/src/components/AIToolSetup.vue`** (Minor Enhancements)
   - Improve: API key generation UX (add consent step)
   - Add: "Already configured" detection
   - Enhance: Better error recovery with actionable steps
   - **Lines:** Keep similar size (~450)

**New Components to Create:**

3. **`frontend/src/components/mcp/CopyPasteWizard.vue`** (NEW)
   - 4-step guided workflow
   - Visual progress indicator
   - Before/after JSON comparison
   - **Lines:** ~200

4. **`frontend/src/components/mcp/ConfigValidator.vue`** (NEW)
   - Paste-to-validate functionality
   - Syntax error detection
   - Common issue suggestions
   - **Lines:** ~150

5. **`frontend/src/components/mcp/TroubleshootingFAQ.vue`** (NEW)
   - Icon-based FAQ format
   - Platform-specific solutions
   - Scannable bullet points
   - **Lines:** ~200

**Supporting Utilities:**

6. **`frontend/src/utils/mcpConfigHelpers.js`** (NEW)
   - JSON validation logic
   - Common error detection
   - Config path helpers
   - **Lines:** ~100

---

## Implementation Plan

### Phase 2A: Component Foundation (90 minutes)

#### 2A.1 Create Utility Helper

**File:** `frontend/src/utils/mcpConfigHelpers.js`

```javascript
/**
 * MCP Configuration Utilities
 * Helper functions for validation, path detection, and error checking
 */

/**
 * Detect config file path based on OS
 */
export function detectConfigPath() {
  const platform = navigator.platform.toLowerCase()

  if (platform.includes('win')) {
    return 'C:\\Users\\YourName\\.claude.json'
  }
  return '~/.claude.json'
}

/**
 * Validate MCP configuration JSON
 * @param {string} jsonString - Raw JSON string to validate
 * @returns {Object} { valid: boolean, errors: string[], suggestions: string[] }
 */
export function validateMcpConfig(jsonString) {
  const errors = []
  const suggestions = []

  // Check 1: Valid JSON syntax
  let parsed
  try {
    parsed = JSON.parse(jsonString)
  } catch (e) {
    errors.push(`Invalid JSON syntax: ${e.message}`)
    return { valid: false, errors, suggestions }
  }

  // Check 2: Has mcpServers section
  if (!parsed.mcpServers) {
    errors.push('Missing "mcpServers" object at top level')
    suggestions.push('Add: { "mcpServers": { ... } }')
  }

  // Check 3: Has giljo-mcp server
  if (parsed.mcpServers && !parsed.mcpServers['giljo-mcp']) {
    errors.push('Missing "giljo-mcp" server configuration')
    suggestions.push('Add the giljo-mcp config inside mcpServers')
  }

  // Check 4: giljo-mcp has required fields
  if (parsed.mcpServers?.['giljo-mcp']) {
    const giljo = parsed.mcpServers['giljo-mcp']

    if (!giljo.command) {
      errors.push('Missing "command" field in giljo-mcp')
    }

    if (!giljo.args) {
      errors.push('Missing "args" field in giljo-mcp')
    }

    if (!giljo.env?.GILJO_API_KEY) {
      errors.push('Missing GILJO_API_KEY in env')
      suggestions.push('Replace <your-api-key-here> with real API key')
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    suggestions
  }
}

/**
 * Detect common JSON errors
 * @param {string} jsonString - Raw JSON to analyze
 * @returns {Array} List of detected issues with solutions
 */
export function detectCommonIssues(jsonString) {
  const issues = []

  // Trailing commas
  if (jsonString.match(/,\s*[}\]]/)) {
    issues.push({
      problem: 'Trailing comma detected',
      solution: 'Remove comma before } or ]',
      severity: 'error'
    })
  }

  // Missing quotes on keys
  if (jsonString.match(/\{[^"'\s]/)) {
    issues.push({
      problem: 'Object keys must be quoted',
      solution: 'Wrap all keys in double quotes: "key": value',
      severity: 'error'
    })
  }

  // Placeholder API key
  if (jsonString.includes('<your-api-key-here>')) {
    issues.push({
      problem: 'Placeholder API key detected',
      solution: 'Replace with real API key from Settings → API Keys',
      severity: 'warning'
    })
  }

  // Hardcoded paths (from Phase 1 fixes)
  if (jsonString.match(/[A-Z]:\\/)) {
    issues.push({
      problem: 'Windows-specific path detected',
      solution: 'Remove hardcoded paths for cross-platform compatibility',
      severity: 'warning'
    })
  }

  return issues
}

/**
 * Open config folder in file explorer (browser-safe)
 * Note: Direct filesystem access not possible from browser
 * This provides instructions instead
 */
export function getOpenFolderInstructions() {
  const platform = navigator.platform.toLowerCase()

  if (platform.includes('win')) {
    return {
      command: 'explorer %USERPROFILE%',
      description: 'Opens your user folder. Look for .claude.json file'
    }
  }

  if (platform.includes('mac')) {
    return {
      command: 'open ~',
      description: 'Opens your home folder in Finder'
    }
  }

  return {
    command: 'cd ~ && ls -la',
    description: 'Lists files in home directory including hidden files'
  }
}
```

**Test Criteria:**
- [ ] validateMcpConfig() catches invalid JSON
- [ ] validateMcpConfig() detects missing mcpServers
- [ ] detectCommonIssues() finds trailing commas
- [ ] detectCommonIssues() finds placeholder API keys
- [ ] detectConfigPath() returns correct paths for each OS

---

#### 2A.2 Create ConfigValidator Component

**File:** `frontend/src/components/mcp/ConfigValidator.vue`

```vue
<template>
  <v-card variant="outlined">
    <v-card-text>
      <v-textarea
        v-model="userConfig"
        label="Paste your complete .claude.json content here"
        variant="outlined"
        rows="12"
        placeholder='Paste your entire .claude.json file here to validate...'
        class="config-textarea"
        @input="debouncedValidate"
      >
        <template v-slot:prepend-inner>
          <v-icon :color="validationIcon.color">{{ validationIcon.icon }}</v-icon>
        </template>
      </v-textarea>

      <v-btn
        @click="validateNow"
        color="primary"
        block
        size="large"
        :loading="validating"
        prepend-icon="mdi-check-decagram"
      >
        Validate Configuration
      </v-btn>

      <!-- Validation Results -->
      <v-expand-transition>
        <v-alert
          v-if="validationResult"
          :type="validationResult.valid ? 'success' : 'error'"
          variant="tonal"
          class="mt-4"
        >
          <v-alert-title>
            <v-icon start>
              {{ validationResult.valid ? 'mdi-check-circle' : 'mdi-alert-circle' }}
            </v-icon>
            {{ validationResult.valid ? 'Valid Configuration!' : 'Configuration Has Errors' }}
          </v-alert-title>

          <div v-if="!validationResult.valid" class="mt-2">
            <strong>Errors Found:</strong>
            <ul class="ml-4 mt-1">
              <li v-for="(error, i) in validationResult.errors" :key="i">{{ error }}</li>
            </ul>

            <div v-if="validationResult.suggestions.length" class="mt-3">
              <strong>Suggestions:</strong>
              <ul class="ml-4 mt-1">
                <li v-for="(suggestion, i) in validationResult.suggestions" :key="i">
                  {{ suggestion }}
                </li>
              </ul>
            </div>
          </div>

          <div v-else class="mt-2">
            Your configuration is valid and ready to use! Save it to <code>{{ configPath }}</code>
          </div>
        </v-alert>
      </v-expand-transition>

      <!-- Common Issues Detected -->
      <v-expand-transition>
        <v-card v-if="commonIssues.length" variant="outlined" class="mt-4">
          <v-card-title class="text-body-1">
            <v-icon start color="warning">mdi-alert</v-icon>
            Common Issues Detected
          </v-card-title>
          <v-card-text>
            <v-list density="compact">
              <v-list-item v-for="(issue, i) in commonIssues" :key="i">
                <template v-slot:prepend>
                  <v-icon :color="issue.severity === 'error' ? 'error' : 'warning'">
                    {{ issue.severity === 'error' ? 'mdi-close-circle' : 'mdi-alert' }}
                  </v-icon>
                </template>
                <v-list-item-title>{{ issue.problem }}</v-list-item-title>
                <v-list-item-subtitle>{{ issue.solution }}</v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-expand-transition>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, computed } from 'vue'
import { validateMcpConfig, detectCommonIssues, detectConfigPath } from '@/utils/mcpConfigHelpers'

// Debounce utility (lightweight, no lodash needed)
function debounce(fn, delay) {
  let timeout
  return (...args) => {
    clearTimeout(timeout)
    timeout = setTimeout(() => fn(...args), delay)
  }
}

const emit = defineEmits(['validated'])

// State
const userConfig = ref('')
const validationResult = ref(null)
const commonIssues = ref([])
const validating = ref(false)
const configPath = detectConfigPath()

// Computed
const validationIcon = computed(() => {
  if (!validationResult.value) {
    return { icon: 'mdi-text-box-check', color: 'grey' }
  }
  return validationResult.value.valid
    ? { icon: 'mdi-check-circle', color: 'success' }
    : { icon: 'mdi-alert-circle', color: 'error' }
})

// Methods
function validateNow() {
  validating.value = true

  // Simulate async for UX
  setTimeout(() => {
    validationResult.value = validateMcpConfig(userConfig.value)

    if (!validationResult.value.valid) {
      commonIssues.value = detectCommonIssues(userConfig.value)
    } else {
      commonIssues.value = []
    }

    emit('validated', validationResult.value)
    validating.value = false
  }, 300)
}

const debouncedValidate = debounce(validateNow, 1000)
</script>

<style scoped>
.config-textarea :deep(textarea) {
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
  line-height: 1.5;
}

code {
  background-color: rgba(var(--v-theme-surface-variant), 0.5);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.875rem;
}
</style>
```

**Test Criteria:**
- [ ] Validator detects invalid JSON
- [ ] Validator detects missing mcpServers
- [ ] Validator detects placeholder API key
- [ ] Validator shows success for valid config
- [ ] Debounced validation works (waits 1 second)
- [ ] Common issues displayed with icons

---

### Phase 2B: Redesign McpIntegration.vue (120 minutes)

#### 2B.1 Simplified Architecture

**Before (Current):**
```
McpIntegration.vue (640 lines)
├── Download Installer Scripts (4 buttons, lots of text)
├── Share with Team Members (expansion panel, email template)
├── Manual Configuration (expansion panel, JSON display)
└── Troubleshooting (4 expansion panels)
```

**After (Redesigned):**
```
McpIntegration.vue (~450 lines)
├── Tabs
│   ├── Tab 1: Quick Setup (DEFAULT, 80% use case)
│   │   ├── Platform selector (auto-detected)
│   │   ├── Download button (LARGE, primary action)
│   │   └── 3-step instructions
│   │
│   └── Tab 2: Advanced
│       ├── Manual Config (copy-paste with validator)
│       ├── Share Links (for teams)
│       └── Troubleshooting FAQ
│
└── Status Banner (if already configured)
```

**Key Changes:**
- **Tabs** instead of sequential cards (reduce scrolling)
- **"Quick Setup" default** (shows primary path immediately)
- **"Advanced" tab** for manual config, sharing, troubleshooting
- **Status detection** ("Already configured" banner at top)
- **Validator integrated** in Advanced tab

---

#### 2B.2 Implementation Sketch

**File:** `frontend/src/views/McpIntegration.vue` (redesigned)

```vue
<template>
  <v-container>
    <!-- Page Header -->
    <div class="d-flex justify-space-between align-center mb-6">
      <div>
        <h1 class="text-h4 mb-2">MCP Configuration</h1>
        <p class="text-subtitle-1">Configure Claude Code CLI to connect with GiljoAI MCP</p>
      </div>
    </div>

    <!-- Status Banner (if configured) -->
    <v-alert
      v-if="isConfigured"
      type="success"
      variant="tonal"
      prominent
      class="mb-6"
    >
      <v-alert-title>
        <v-icon start>mdi-check-circle</v-icon>
        MCP Already Configured
      </v-alert-title>
      <div>
        You've already set up GiljoAI MCP for Claude Code. You can reconfigure below if needed.
      </div>
      <template v-slot:append>
        <v-btn variant="text" @click="isConfigured = false">
          Reconfigure
        </v-btn>
      </template>
    </v-alert>

    <!-- Main Tabs -->
    <v-tabs v-model="activeTab" class="mb-6">
      <v-tab value="quick">
        <v-icon start>mdi-flash</v-icon>
        Quick Setup (Recommended)
      </v-tab>
      <v-tab value="advanced">
        <v-icon start>mdi-cog</v-icon>
        Advanced
      </v-tab>
    </v-tabs>

    <v-window v-model="activeTab">
      <!-- TAB 1: QUICK SETUP (PRIMARY PATH) -->
      <v-window-item value="quick">
        <v-card>
          <v-card-text class="pa-8">
            <h2 class="text-h5 mb-4">Download MCP Installer</h2>
            <p class="text-body-1 mb-6">
              The easiest way to configure GiljoAI MCP. Download and run the installer script for your platform.
            </p>

            <!-- Platform Selector (auto-detected) -->
            <v-select
              v-model="selectedPlatform"
              :items="platforms"
              label="Select Your Platform"
              variant="outlined"
              prepend-icon="mdi-desktop-classic"
              class="mb-4"
            >
              <template v-slot:item="{ props, item }">
                <v-list-item v-bind="props">
                  <template v-slot:prepend>
                    <v-icon :icon="item.raw.icon" />
                  </template>
                </v-list-item>
              </template>
            </v-select>

            <!-- Download Button (LARGE, PRIMARY) -->
            <v-btn
              color="primary"
              size="x-large"
              block
              :loading="downloading"
              @click="downloadInstaller"
              class="mb-6"
            >
              <v-icon start size="large">mdi-download</v-icon>
              Download Installer for {{ selectedPlatform.title }}
            </v-btn>

            <!-- Instructions -->
            <v-card variant="outlined" class="mt-6">
              <v-card-title class="bg-grey-lighten-4">
                <v-icon start>mdi-list-box-outline</v-icon>
                Next Steps
              </v-card-title>
              <v-card-text>
                <v-stepper alt-labels :model-value="1">
                  <v-stepper-header>
                    <v-stepper-item value="1" title="Download" icon="mdi-download" />
                    <v-divider />
                    <v-stepper-item value="2" title="Run Script" icon="mdi-play" />
                    <v-divider />
                    <v-stepper-item value="3" title="Restart CLI" icon="mdi-restart" />
                  </v-stepper-header>
                </v-stepper>

                <ol class="mt-4 ml-4">
                  <li class="mb-2">Download the installer script (button above)</li>
                  <li class="mb-2">
                    Run the script:
                    <code v-if="selectedPlatform.value === 'windows'" class="ml-2">
                      Double-click giljo-mcp-setup.bat
                    </code>
                    <code v-else class="ml-2">
                      chmod +x giljo-mcp-setup.sh && ./giljo-mcp-setup.sh
                    </code>
                  </li>
                  <li class="mb-2">Restart Claude Code CLI: exit and run <code>claude</code></li>
                  <li>Verify with: <code>claude mcp list</code> (should show "giljo-mcp")</li>
                </ol>
              </v-card-text>
            </v-card>
          </v-card-text>
        </v-card>
      </v-window-item>

      <!-- TAB 2: ADVANCED (MANUAL CONFIG, SHARE, TROUBLESHOOTING) -->
      <v-window-item value="advanced">
        <v-expansion-panels>
          <!-- Manual Configuration -->
          <v-expansion-panel value="manual">
            <v-expansion-panel-title>
              <v-icon start>mdi-code-json</v-icon>
              <strong>Manual Configuration (Copy & Paste)</strong>
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <p class="mb-4">
                For advanced users who prefer manual configuration. Copy the JSON and add to your
                <code>~/.claude.json</code> file.
              </p>

              <!-- JSON Config Display -->
              <v-card variant="outlined" class="mb-4">
                <v-card-text>
                  <div class="d-flex justify-space-between align-center mb-2">
                    <span class="text-caption">Configuration JSON</span>
                    <v-btn
                      size="small"
                      :color="copied ? 'success' : 'primary'"
                      @click="copyConfig"
                    >
                      <v-icon start>{{ copied ? 'mdi-check' : 'mdi-content-copy' }}</v-icon>
                      {{ copied ? 'Copied!' : 'Copy' }}
                    </v-btn>
                  </div>
                  <pre class="config-block"><code>{{ manualConfigJson }}</code></pre>
                </v-card-text>
              </v-card>

              <!-- Validator -->
              <h3 class="text-h6 mb-2">Validate Your Configuration</h3>
              <p class="text-body-2 mb-3">
                After pasting the config into <code>~/.claude.json</code>, paste your complete file here to verify:
              </p>
              <ConfigValidator @validated="handleValidation" />
            </v-expansion-panel-text>
          </v-expansion-panel>

          <!-- Share with Team -->
          <v-expansion-panel value="share">
            <v-expansion-panel-title>
              <v-icon start>mdi-share-variant</v-icon>
              <strong>Share with Team Members</strong>
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <!-- Existing share link generation logic -->
              <p class="mb-4">Generate secure download links to share with your team (expires in 7 days).</p>
              <!-- ... (keep existing share link functionality) ... -->
            </v-expansion-panel-text>
          </v-expansion-panel>

          <!-- Troubleshooting -->
          <v-expansion-panel value="troubleshooting">
            <v-expansion-panel-title>
              <v-icon start>mdi-help-circle</v-icon>
              <strong>Troubleshooting</strong>
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <TroubleshootingFAQ />
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-window-item>
    </v-window>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { API_CONFIG } from '@/config/api'
import api from '@/services/api'
import ConfigValidator from '@/components/mcp/ConfigValidator.vue'
import TroubleshootingFAQ from '@/components/mcp/TroubleshootingFAQ.vue'

// State
const activeTab = ref('quick')
const isConfigured = ref(false)
const selectedPlatform = ref(null)
const downloading = ref(false)
const copied = ref(false)

// Platform detection
const platforms = [
  { value: 'windows', title: 'Windows', icon: 'mdi-microsoft-windows' },
  { value: 'unix', title: 'macOS / Linux', icon: 'mdi-apple' }
]

// Auto-detect platform
onMounted(() => {
  const platform = navigator.platform.toLowerCase()
  selectedPlatform.value = platform.includes('win') ? platforms[0] : platforms[1]

  // Check if already configured (future enhancement)
  // isConfigured.value = await checkMcpStatus()
})

// Computed
const manualConfigJson = computed(() => {
  return JSON.stringify({
    'giljo-mcp': {
      command: 'python',
      args: ['-m', 'giljo_mcp'],
      env: {
        GILJO_SERVER_URL: API_CONFIG.REST_API.baseURL,
        GILJO_API_KEY: '<your-api-key-here>'
      }
    }
  }, null, 2)
})

// Methods
async function downloadInstaller() {
  downloading.value = true
  try {
    const endpoint = selectedPlatform.value.value === 'windows'
      ? '/api/mcp-installer/windows'
      : '/api/mcp-installer/unix'

    const response = await api.get(endpoint, { responseType: 'blob' })

    // Trigger download (implementation from Phase 1)
    const url = window.URL.createObjectURL(response.data)
    const a = document.createElement('a')
    a.href = url
    a.download = selectedPlatform.value.value === 'windows'
      ? 'giljo-mcp-setup.bat'
      : 'giljo-mcp-setup.sh'
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
  } catch (error) {
    console.error('Download failed:', error)
  } finally {
    downloading.value = false
  }
}

async function copyConfig() {
  try {
    await navigator.clipboard.writeText(manualConfigJson.value)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch (error) {
    console.error('Copy failed:', error)
  }
}

function handleValidation(result) {
  console.log('Validation result:', result)
  // Could show snackbar notification here
}
</script>

<style scoped>
.config-block {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 16px;
  overflow-x: auto;
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
  border-radius: 4px;
}

code {
  background-color: rgba(var(--v-theme-surface-variant), 0.5);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.875rem;
}
</style>
```

**Key UX Improvements:**
1. **Tabs reduce scrolling** - Everything accessible in 2 clicks
2. **Auto-detect platform** - Reduces user decisions
3. **Visual hierarchy** - Quick Setup tab is default, clearly primary
4. **Integrated validator** - In Advanced tab, right where it's needed
5. **Status awareness** - Shows "Already configured" banner if detected
6. **Consistent patterns** - All copy buttons same style, same feedback

**Test Criteria:**
- [ ] Quick Setup tab is default on load
- [ ] Platform auto-detected correctly
- [ ] Download button works for both platforms
- [ ] Tabs switch smoothly without losing state
- [ ] Validator works in Advanced tab
- [ ] Expansion panels in Advanced tab work
- [ ] Status banner shows if configured (when implemented)

---

### Phase 2C: Create TroubleshootingFAQ Component (45 minutes)

**File:** `frontend/src/components/mcp/TroubleshootingFAQ.vue`

```vue
<template>
  <div>
    <p class="text-body-2 mb-4">Common issues and solutions for MCP configuration:</p>

    <v-expansion-panels>
      <!-- Config file doesn't exist -->
      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon start color="warning">mdi-file-question</v-icon>
          <strong>.claude.json file doesn't exist</strong>
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <p class="mb-2">Create it with this base content:</p>
          <v-card variant="outlined" class="pa-3 mb-2">
            <pre>{ "mcpServers": {} }</pre>
          </v-card>
          <p class="text-caption">
            Location: <code>{{ configPath }}</code>
          </p>
        </v-expansion-panel-text>
      </v-expansion-panel>

      <!-- Config not loading -->
      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon start color="warning">mdi-alert</v-icon>
          <strong>Configuration applied but commands not working</strong>
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <v-list density="compact">
            <v-list-item>
              <template v-slot:prepend>
                <v-icon>mdi-numeric-1-circle</v-icon>
              </template>
              <v-list-item-title>Completely restart Claude Code CLI (not just reload)</v-list-item-title>
            </v-list-item>
            <v-list-item>
              <template v-slot:prepend>
                <v-icon>mdi-numeric-2-circle</v-icon>
              </template>
              <v-list-item-title>Verify JSON syntax with validator above</v-list-item-title>
            </v-list-item>
            <v-list-item>
              <template v-slot:prepend>
                <v-icon>mdi-numeric-3-circle</v-icon>
              </template>
              <v-list-item-title>Check Python: <code>python --version</code></v-list-item-title>
            </v-list-item>
            <v-list-item>
              <template v-slot:prepend>
                <v-icon>mdi-numeric-4-circle</v-icon>
              </template>
              <v-list-item-title>Verify GiljoAI server is running</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-expansion-panel-text>
      </v-expansion-panel>

      <!-- Python not found -->
      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon start color="warning">mdi-language-python</v-icon>
          <strong>Python not found</strong>
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <p class="mb-3">GiljoAI MCP requires Python 3.8 or higher.</p>

          <v-list density="compact">
            <v-list-item>
              <v-list-item-title>
                <strong>Windows:</strong>
                <a href="https://www.python.org/downloads/" target="_blank" class="ml-2">
                  python.org/downloads
                </a>
              </v-list-item-title>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>
                <strong>macOS:</strong>
                <code class="ml-2">brew install python3</code>
              </v-list-item-title>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>
                <strong>Linux:</strong>
                <code class="ml-2">sudo apt install python3</code>
              </v-list-item-title>
            </v-list-item>
          </v-list>
        </v-expansion-panel-text>
      </v-expansion-panel>

      <!-- Permission errors -->
      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon start color="warning">mdi-shield-alert</v-icon>
          <strong>Permission denied errors</strong>
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <p class="mb-2"><strong>Windows:</strong></p>
          <v-card variant="outlined" class="mb-3 pa-3">
            <code>icacls "%USERPROFILE%\.claude.json" /grant %USERNAME%:F</code>
          </v-card>

          <p class="mb-2"><strong>macOS / Linux:</strong></p>
          <v-card variant="outlined" class="pa-3">
            <code>chmod 644 ~/.claude.json</code>
          </v-card>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>
  </div>
</template>

<script setup>
import { detectConfigPath } from '@/utils/mcpConfigHelpers'

const configPath = detectConfigPath()
</script>

<style scoped>
code {
  background-color: rgba(var(--v-theme-surface-variant), 0.5);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.875rem;
}

pre {
  margin: 0;
}
</style>
```

**Test Criteria:**
- [ ] All 4 FAQ panels expand correctly
- [ ] Code examples display correctly
- [ ] Links open in new tabs
- [ ] Icons render correctly

---

### Phase 2D: AIToolSetup Enhancements (60 minutes)

**File:** `frontend/src/components/AIToolSetup.vue`

**Changes:**

1. **Add API Key Consent Step** (Lines 258-276)

**Before:**
```javascript
// Automatically creates API key without asking
const apiKeyData = await apiKeyResponse.json()
generatedApiKey.value = apiKeyData.key
```

**After:**
```javascript
// Ask user before creating key
showApiKeyConsent.value = true  // Show consent dialog

// Only create key after user clicks "Generate New Key"
```

2. **Add Status Detection** (new onMounted logic)

```javascript
onMounted(async () => {
  // Check if MCP already configured
  try {
    const response = await api.get('/api/mcp-tools/status')
    if (response.data.configured) {
      isAlreadyConfigured.value = true
    }
  } catch (error) {
    // Not configured, that's fine
  }
})
```

**Test Criteria:**
- [ ] Consent dialog shown before API key generation
- [ ] User can cancel API key generation
- [ ] Status check doesn't break if endpoint missing
- [ ] "Already configured" badge shows when applicable

---

## Success Criteria

### Definition of Done
- [ ] McpIntegration.vue redesigned with tabs
- [ ] ConfigValidator component created and integrated
- [ ] TroubleshootingFAQ component created
- [ ] mcpConfigHelpers.js utility created with tests
- [ ] AIToolSetup.vue enhanced with consent flow
- [ ] All manual tests pass
- [ ] User can complete MCP config in < 60 seconds
- [ ] Validation catches common errors
- [ ] No console errors
- [ ] Git committed with proper message

### User Experience Metrics
- **Configuration completion time:** < 60 seconds (down from ~3-5 minutes)
- **User decisions required:** 2-3 (down from 7+)
- **Clicks to see all content:** 2-3 (down from 7+)
- **Validation success rate:** > 80% on first try

---

## Rollback Plan

**Revert to Phase 1 stable state:**
```bash
git checkout HEAD~1 -- frontend/src/views/McpIntegration.vue
git checkout HEAD~1 -- frontend/src/components/AIToolSetup.vue
git clean -fd frontend/src/components/mcp/
git clean -fd frontend/src/utils/mcpConfigHelpers.js
```

---

## Estimated Timeline

- **Phase 2A (Component Foundation):** 90 minutes
- **Phase 2B (McpIntegration Redesign):** 120 minutes
- **Phase 2C (TroubleshootingFAQ):** 45 minutes
- **Phase 2D (AIToolSetup Enhancements):** 60 minutes
- **Testing & Polish:** 45 minutes

**Total:** 5-6 hours

---

## Notes for Next Agent

**This is UX enhancement only:**
- ✅ Build on stable Phase 1 foundation
- ✅ Focus on reducing cognitive load
- ✅ Preserve all existing functionality
- ✅ Add validation and feedback
- ❌ No new backend requirements (except optional status endpoint)

**After completion:**
- User testing session recommended
- Gather feedback on Quick Setup vs Advanced usage split
- Consider analytics to track tab usage

---

**Remember: Enhance what works, don't break what's fixed.**
