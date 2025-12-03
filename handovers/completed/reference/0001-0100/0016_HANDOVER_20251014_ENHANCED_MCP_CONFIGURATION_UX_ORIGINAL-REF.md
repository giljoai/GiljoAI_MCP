# Handover 0016: Enhanced MCP Configuration UX

**Date:** 2025-10-14
**From Agent:** System Architect / UX Designer
**To Agent:** UX Designer + Frontend Implementor (Coordinated Execution)
**Priority:** Medium
**Estimated Complexity:** 2-3 hours
**Status:** Not Started

---

## Task Summary

Enhance the MCP configuration user experience by implementing a sleek, guided copy-paste workflow with visual feedback, step-by-step wizard, JSON validator, and troubleshooting guide. This replaces the need for automated script installers with a polished, transparent, and maintainable solution.

**Why:** User research and consultant analysis determined that copy-paste with enhanced UX is superior to script automation for our developer target audience. Lower maintenance burden (10x less), better trust/transparency, and sufficient for experienced developers.

**Expected Outcome:** Users confidently configure Claude Code CLI MCP integration in 30-60 seconds with clear visual feedback, validation, and troubleshooting support.

---

## Context and Background

### User Research Findings

**Current State:**
- MCP configuration exists in 3 locations:
  - `frontend/src/views/McpIntegration.vue` - Installer script download
  - `frontend/src/components/AIToolSetup.vue` - Dialog-based config generator
  - `frontend/src/components/setup/McpConfigStep.vue` - Setup wizard step

**Problem:**
- Manual copy-paste feels "unpolished" without proper UX
- Users lack confidence they configured correctly
- No validation or troubleshooting guidance
- Scattered across multiple components

**Consultant Decision (2025-10-14):**
- Script automation adds 10x maintenance cost
- Target users (developers) are comfortable with copy-paste
- Real bottleneck: **confidence in correctness**, not automation
- Solution: Invest in enhanced UX, not automation

### Strategic Direction

**Approved Approach:** Enhanced copy-paste with:
1. One-click copy with visual feedback
2. Step-by-step wizard with screenshots
3. JSON validator (paste-to-verify)
4. Clear troubleshooting guide
5. "Open config folder" helper button

**Rejected Alternative:** Python script installer (maintenance burden, trust issues, complexity for novices)

---

## Technical Details

### Files to Modify

**Primary Implementation:**
1. **`frontend/src/views/McpIntegration.vue`** (Complete Redesign)
   - Remove: Installer script download sections
   - Add: Enhanced copy-paste wizard
   - Add: JSON validator component
   - Add: Troubleshooting expansion panels

2. **`frontend/src/components/AIToolSetup.vue`** (Minor Enhancement)
   - Add: One-click copy with visual feedback
   - Add: "Open file location" helper button
   - Enhance: Success/error feedback

3. **`frontend/src/components/setup/McpConfigStep.vue`** (Alignment)
   - Align with new UX patterns from McpIntegration.vue
   - Keep setup wizard specific logic

**New Components to Create:**
4. **`frontend/src/components/mcp/McpConfigWizard.vue`** (NEW)
   - Multi-step guided workflow
   - Visual progress indicator
   - Before/after JSON comparison

5. **`frontend/src/components/mcp/JsonValidator.vue`** (NEW)
   - Paste-to-validate functionality
   - Syntax highlighting
   - Error detection and suggestions

6. **`frontend/src/components/mcp/ConfigFileTroubleshooting.vue`** (NEW)
   - Reusable troubleshooting component
   - Common error solutions
   - Platform-specific guidance

**Supporting Changes:**
7. **`frontend/src/utils/mcpConfigHelpers.js`** (NEW)
   - JSON validation logic
   - File location detection
   - OS-specific path helpers

8. **`frontend/src/assets/screenshots/`** (NEW FOLDER)
   - Step-by-step screenshots for wizard
   - Before/after examples

---

## Implementation Plan

### Phase 1: Component Architecture (30 minutes)

**1.1 Create Component Structure**
```bash
frontend/src/components/mcp/
├── McpConfigWizard.vue       # Multi-step wizard
├── JsonValidator.vue          # Validation component
├── ConfigFileTroubleshooting.vue  # Help component
└── index.js                   # Barrel export
```

**1.2 Create Utilities**
```javascript
// frontend/src/utils/mcpConfigHelpers.js
export function detectConfigPath() {
  const os = detectOS()
  if (os === 'windows') return 'C:\\Users\\YourName\\.claude.json'
  return '~/.claude.json'
}

export function validateMcpConfig(jsonString) {
  // JSON.parse validation
  // Schema validation
  // Common error detection
  return { valid: boolean, errors: [], suggestions: [] }
}

export function openConfigFolder() {
  // Platform-specific folder opening
}
```

**1.3 Test Criteria**
- [ ] Components render without errors
- [ ] Utilities return expected values
- [ ] OS detection works on Windows/Mac/Linux

---

### Phase 2: Enhanced UX Components (60 minutes)

**2.1 McpConfigWizard.vue**

**Design Specification:**
```vue
<template>
  <!-- Step 1: Copy Configuration -->
  <v-card>
    <v-card-title>Step 1: Copy Configuration</v-card-title>
    <v-card-text>
      <v-card variant="outlined" class="mb-3">
        <v-card-text>
          <div class="d-flex justify-space-between align-center mb-2">
            <span class="text-caption">Configuration JSON</span>
            <v-btn @click="copyConfig" :color="copied ? 'success' : 'primary'">
              <v-icon start>{{ copied ? 'mdi-check' : 'mdi-content-copy' }}</v-icon>
              {{ copied ? 'Copied!' : 'Copy to Clipboard' }}
            </v-btn>
          </div>
          <pre class="config-block"><code>{{ configJson }}</code></pre>
        </v-card-text>
      </v-card>

      <v-alert type="success" v-if="copied" variant="tonal">
        <v-icon start>mdi-check-circle</v-icon>
        Configuration copied! Proceed to Step 2.
      </v-alert>
    </v-card-text>
  </v-card>

  <!-- Step 2: Edit Claude Config -->
  <v-card>
    <v-card-title>Step 2: Edit Claude Config</v-card-title>
    <v-card-text>
      <p>Open this file in your editor:</p>
      <v-text-field
        :model-value="configPath"
        readonly
        variant="outlined"
        prepend-icon="mdi-file-document"
      >
        <template v-slot:append>
          <v-btn @click="openFolder" size="small">
            <v-icon start>mdi-folder-open</v-icon>
            Open Folder
          </v-btn>
        </template>
      </v-text-field>

      <v-expansion-panels class="mt-4">
        <v-expansion-panel>
          <v-expansion-panel-title>
            <v-icon start>mdi-help-circle</v-icon>
            Visual Guide: Where to Paste
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <!-- Before/After Screenshots -->
            <v-row>
              <v-col cols="12" md="6">
                <v-card variant="outlined">
                  <v-card-title class="text-body-1">Before</v-card-title>
                  <v-card-text>
                    <pre class="example-code">{
  "mcpServers": {
    "other-server": { ... }
  }
}</pre>
                  </v-card-text>
                </v-card>
              </v-col>
              <v-col cols="12" md="6">
                <v-card variant="outlined">
                  <v-card-title class="text-body-1">After</v-card-title>
                  <v-card-text>
                    <pre class="example-code">{
  "mcpServers": {
    "other-server": { ... },
    "giljo-mcp": { <-- PASTE HERE
      ...
    }
  }
}</pre>
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-card-text>
  </v-card>

  <!-- Step 3: Validate Configuration -->
  <v-card>
    <v-card-title>Step 3: Validate Configuration</v-card-title>
    <v-card-text>
      <p>Paste your complete .claude.json content here to verify:</p>
      <JsonValidator @validated="handleValidation" />
    </v-card-text>
  </v-card>

  <!-- Step 4: Restart Claude Code -->
  <v-card>
    <v-card-title>Step 4: Restart Claude Code CLI</v-card-title>
    <v-card-text>
      <v-alert type="info" variant="tonal">
        <v-icon start>mdi-restart</v-icon>
        <div>
          <strong>In your terminal:</strong>
          <ol class="mt-2 ml-4">
            <li>Exit Claude Code: <code>Ctrl+D</code> or type <code>exit</code></li>
            <li>Start again: <code>claude</code></li>
            <li>Verify: <code>claude mcp list</code></li>
          </ol>
        </div>
      </v-alert>

      <v-card variant="outlined" class="mt-4 pa-3">
        <div class="d-flex align-center">
          <v-icon color="success" size="large" class="mr-3">mdi-check-circle</v-icon>
          <div>
            <div class="text-h6">You should see:</div>
            <code class="text-success">giljo-mcp ✓</code>
          </div>
        </div>
      </v-card>
    </v-card-text>
  </v-card>
</template>
```

**Key Features:**
- ✅ Visual progress stepper
- ✅ One-click copy with success feedback
- ✅ "Open folder" helper button
- ✅ Before/after visual comparison
- ✅ Integrated validator
- ✅ Clear success criteria

**Test Criteria:**
- [ ] Copy button changes to "Copied!" with checkmark
- [ ] Open folder button launches correct location
- [ ] Progress indicator shows current step
- [ ] All 4 steps are clearly visible

---

**2.2 JsonValidator.vue**

**Design Specification:**
```vue
<template>
  <v-card variant="outlined">
    <v-card-text>
      <v-textarea
        v-model="userConfig"
        label="Paste your .claude.json content here"
        variant="outlined"
        rows="10"
        placeholder='{ "mcpServers": { ... } }'
        @input="debounceValidate"
      />

      <v-btn @click="validateNow" color="primary" class="mt-2" block>
        <v-icon start>mdi-check-decagram</v-icon>
        Validate Configuration
      </v-btn>

      <!-- Validation Results -->
      <v-alert
        v-if="validationResult"
        :type="validationResult.valid ? 'success' : 'error'"
        variant="tonal"
        class="mt-4"
      >
        <v-icon start>
          {{ validationResult.valid ? 'mdi-check-circle' : 'mdi-alert-circle' }}
        </v-icon>
        <div>
          <strong>{{ validationResult.valid ? 'Valid Configuration!' : 'Invalid Configuration' }}</strong>
          <ul v-if="validationResult.errors.length" class="mt-2 ml-4">
            <li v-for="(error, i) in validationResult.errors" :key="i">{{ error }}</li>
          </ul>
          <div v-if="validationResult.suggestions.length" class="mt-2">
            <strong>Suggestions:</strong>
            <ul class="ml-4">
              <li v-for="(suggestion, i) in validationResult.suggestions" :key="i">
                {{ suggestion }}
              </li>
            </ul>
          </div>
        </div>
      </v-alert>

      <!-- Detected Issues -->
      <v-expansion-panels v-if="detectedIssues.length" class="mt-4">
        <v-expansion-panel>
          <v-expansion-panel-title>
            <v-icon start color="warning">mdi-alert</v-icon>
            Common Issues Detected
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <v-list density="compact">
              <v-list-item v-for="(issue, i) in detectedIssues" :key="i">
                <v-list-item-title>{{ issue.problem }}</v-list-item-title>
                <v-list-item-subtitle>{{ issue.solution }}</v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref } from 'vue'
import { validateMcpConfig } from '@/utils/mcpConfigHelpers'
import { debounce } from 'lodash-es'

const emit = defineEmits(['validated'])

const userConfig = ref('')
const validationResult = ref(null)
const detectedIssues = ref([])

const validateNow = () => {
  validationResult.value = validateMcpConfig(userConfig.value)

  // Detect common issues
  if (!validationResult.value.valid) {
    detectedIssues.value = detectCommonIssues(userConfig.value)
  } else {
    detectedIssues.value = []
  }

  emit('validated', validationResult.value)
}

const debounceValidate = debounce(validateNow, 1000)

function detectCommonIssues(jsonString) {
  const issues = []

  if (jsonString.includes(',]') || jsonString.includes(',}')) {
    issues.push({
      problem: 'Trailing comma detected',
      solution: 'Remove the comma before ] or }'
    })
  }

  if (!jsonString.includes('mcpServers')) {
    issues.push({
      problem: 'Missing "mcpServers" section',
      solution: 'Add a top-level "mcpServers" object'
    })
  }

  return issues
}
</script>
```

**Key Features:**
- ✅ Real-time validation (debounced)
- ✅ Manual validation button
- ✅ Syntax error detection
- ✅ Common issue detection (trailing commas, missing sections)
- ✅ Actionable suggestions

**Test Criteria:**
- [ ] Valid JSON shows success alert
- [ ] Invalid JSON shows error with details
- [ ] Trailing comma detected and flagged
- [ ] Missing mcpServers section detected

---

**2.3 ConfigFileTroubleshooting.vue**

**Design Specification:**
```vue
<template>
  <v-expansion-panels>
    <!-- File Not Found -->
    <v-expansion-panel>
      <v-expansion-panel-title>
        <v-icon start color="warning">mdi-alert</v-icon>
        .claude.json file doesn't exist
      </v-expansion-panel-title>
      <v-expansion-panel-text>
        <p class="mb-3">If the file doesn't exist, create it with this base content:</p>
        <v-card variant="outlined" class="pa-3">
          <pre class="config-block">{ "mcpServers": {} }</pre>
        </v-card>
        <v-btn @click="copyBaseConfig" size="small" class="mt-2">
          <v-icon start>mdi-content-copy</v-icon>
          Copy Base Config
        </v-btn>
      </v-expansion-panel-text>
    </v-expansion-panel>

    <!-- Config Not Loading -->
    <v-expansion-panel>
      <v-expansion-panel-title>
        <v-icon start color="warning">mdi-alert</v-icon>
        Configuration applied but not working
      </v-expansion-panel-title>
      <v-expansion-panel-text>
        <p class="mb-3">Try these steps in order:</p>
        <v-list density="compact">
          <v-list-item>
            <template v-slot:prepend>
              <v-checkbox-btn value="1" />
            </template>
            <v-list-item-title>Verify JSON syntax is valid (use validator above)</v-list-item-title>
          </v-list-item>
          <v-list-item>
            <template v-slot:prepend>
              <v-checkbox-btn value="2" />
            </template>
            <v-list-item-title>Restart Claude Code completely (exit and start again)</v-list-item-title>
          </v-list-item>
          <v-list-item>
            <template v-slot:prepend>
              <v-checkbox-btn value="3" />
            </template>
            <v-list-item-title>Check Python is installed: <code>python --version</code></v-list-item-title>
          </v-list-item>
          <v-list-item>
            <template v-slot:prepend>
              <v-checkbox-btn value="4" />
            </template>
            <v-list-item-title>Verify server is running (check System Settings)</v-list-item-title>
          </v-list-item>
        </v-list>
      </v-expansion-panel-text>
    </v-expansion-panel>

    <!-- Permission Issues -->
    <v-expansion-panel>
      <v-expansion-panel-title>
        <v-icon start color="warning">mdi-alert</v-icon>
        Permission denied or file read errors
      </v-expansion-panel-title>
      <v-expansion-panel-text>
        <p class="mb-2"><strong>Windows:</strong></p>
        <v-card variant="outlined" class="mb-3 pa-3">
          <code>icacls "%USERPROFILE%\.claude.json" /grant %USERNAME%:F</code>
        </v-card>

        <p class="mb-2"><strong>macOS/Linux:</strong></p>
        <v-card variant="outlined" class="pa-3">
          <code>chmod 644 ~/.claude.json</code>
        </v-card>
      </v-expansion-panel-text>
    </v-expansion-panel>

    <!-- Python Not Found -->
    <v-expansion-panel>
      <v-expansion-panel-title>
        <v-icon start color="warning">mdi-alert</v-icon>
        Python not found
      </v-expansion-panel-title>
      <v-expansion-panel-text>
        <p class="mb-3">GiljoAI MCP requires Python 3.8+. Install from:</p>
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
  </v-expansion-panels>
</template>
```

**Test Criteria:**
- [ ] All 4 troubleshooting panels expand correctly
- [ ] Copy buttons work
- [ ] Links open in new tabs
- [ ] Code examples are readable

---

### Phase 3: Redesign McpIntegration.vue (45 minutes)

**3.1 Remove Installer Script Sections**

Delete these sections:
- "Download Installer Scripts" card
- "Share with Team Members" card
- Download script logic (`downloadScript()`, `generateShareLinks()`)

**3.2 Add Enhanced Copy-Paste Workflow**

```vue
<template>
  <v-container>
    <!-- Page Header -->
    <div class="d-flex justify-space-between align-center mb-6">
      <div>
        <h1 class="text-h4 mb-2">MCP Configuration</h1>
        <p class="text-subtitle-1">
          Configure Claude Code CLI to connect with GiljoAI MCP
        </p>
      </div>
    </div>

    <!-- Main Configuration Wizard -->
    <McpConfigWizard :config-json="generatedConfig" />

    <!-- Validator Section -->
    <v-card class="mt-6">
      <v-card-title>
        <v-icon class="mr-2">mdi-check-decagram</v-icon>
        Validate Your Configuration
      </v-card-title>
      <v-card-text>
        <p class="text-body-1 mb-4">
          Paste your complete .claude.json file here to verify it's correct:
        </p>
        <JsonValidator @validated="handleValidation" />
      </v-card-text>
    </v-card>

    <!-- Troubleshooting Section -->
    <v-card class="mt-6">
      <v-card-title>
        <v-icon class="mr-2">mdi-help-circle</v-icon>
        Troubleshooting
      </v-card-title>
      <v-card-text>
        <ConfigFileTroubleshooting />
      </v-card-text>
    </v-card>

    <!-- Success Snackbar -->
    <v-snackbar
      v-model="snackbar.show"
      :color="snackbar.color"
      :timeout="3000"
      location="bottom right"
    >
      {{ snackbar.message }}
      <template v-slot:actions>
        <v-btn variant="text" @click="snackbar.show = false" icon="mdi-close" />
      </template>
    </v-snackbar>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { API_CONFIG } from '@/config/api'
import McpConfigWizard from '@/components/mcp/McpConfigWizard.vue'
import JsonValidator from '@/components/mcp/JsonValidator.vue'
import ConfigFileTroubleshooting from '@/components/mcp/ConfigFileTroubleshooting.vue'

const snackbar = ref({ show: false, message: '', color: 'success' })

const generatedConfig = computed(() => {
  return JSON.stringify(
    {
      'giljo-mcp': {
        command: 'python',
        args: ['-m', 'giljo_mcp'],
        env: {
          GILJO_SERVER_URL: API_CONFIG.REST_API.baseURL,
          GILJO_API_KEY: '<your-api-key-here>',
        },
      },
    },
    null,
    2
  )
})

function handleValidation(result) {
  if (result.valid) {
    showSnackbar('Configuration is valid!', 'success')
  } else {
    showSnackbar('Configuration has errors. See details above.', 'error')
  }
}

function showSnackbar(message, color = 'success') {
  snackbar.value = { show: true, message, color }
}
</script>
```

**Test Criteria:**
- [ ] Page loads without errors
- [ ] Wizard displays all 4 steps
- [ ] Validator section functional
- [ ] Troubleshooting expands correctly

---

### Phase 4: Testing & Validation (15 minutes)

**4.1 Manual Testing Checklist**
- [ ] Test on Windows: File paths correct
- [ ] Test on macOS: File paths correct
- [ ] Copy button copies to clipboard
- [ ] Open folder button works
- [ ] JSON validator catches errors
- [ ] JSON validator approves valid config
- [ ] Troubleshooting panels all expand
- [ ] Before/after examples are clear

**4.2 User Acceptance Criteria**
- [ ] User can complete configuration in < 60 seconds
- [ ] User receives clear feedback at each step
- [ ] User can validate their configuration
- [ ] User can troubleshoot common issues independently

**4.3 Cross-Browser Testing**
- [ ] Chrome/Edge (Chromium)
- [ ] Firefox
- [ ] Safari (macOS)

---

## Testing Requirements

### Unit Tests

**File:** `tests/frontend/components/mcp/JsonValidator.spec.js`
```javascript
describe('JsonValidator', () => {
  it('validates correct JSON', () => {
    const validJson = '{"mcpServers": {"giljo-mcp": {}}}'
    const result = validateMcpConfig(validJson)
    expect(result.valid).toBe(true)
  })

  it('detects trailing commas', () => {
    const invalidJson = '{"mcpServers": {"giljo-mcp": {},}}'
    const result = validateMcpConfig(invalidJson)
    expect(result.valid).toBe(false)
    expect(result.errors).toContain('Trailing comma')
  })

  it('detects missing mcpServers', () => {
    const invalidJson = '{"other": {}}'
    const result = validateMcpConfig(invalidJson)
    expect(result.suggestions).toContain('Add mcpServers section')
  })
})
```

### Integration Tests

**Scenario: Complete Configuration Flow**
1. User loads MCP Integration page
2. User clicks "Copy to Clipboard"
3. User opens JSON validator
4. User pastes configuration
5. Validator shows success
6. User sees "Restart Claude Code" instructions

### Manual Testing

**Step-by-Step Test:**
1. Navigate to `/mcp-integration`
2. Click copy button → Verify clipboard contains JSON
3. Click "Open Folder" → Verify folder opens
4. Paste valid JSON into validator → Verify success message
5. Paste invalid JSON → Verify error message
6. Expand troubleshooting panel → Verify solutions display

---

## Dependencies and Blockers

### Dependencies
- ✅ Vue 3 + Vuetify 3 (already installed)
- ✅ lodash-es (for debounce)
- ⚠️ May need `clipboard-polyfill` for older browsers

### Known Blockers
- None anticipated

### Questions Needing Answers
- Should we add a 30-second video tutorial? (Optional enhancement)
- Should we track analytics on validation success rate? (Future enhancement)

---

## Success Criteria

### Definition of Done
- [ ] McpIntegration.vue redesigned without script installers
- [ ] 3 new components created and functional
- [ ] JSON validator catches common errors
- [ ] Troubleshooting guide comprehensive
- [ ] All manual tests pass
- [ ] Cross-browser compatible
- [ ] No console errors
- [ ] Git committed with proper message
- [ ] Devlog updated

### User Experience Metrics
- Configuration completion time: < 60 seconds
- Validation success rate: > 80% on first try
- User confidence: High (based on feedback)

---

## Rollback Plan

### If Things Go Wrong

**Revert Strategy:**
```bash
# Rollback to current state
git checkout HEAD -- frontend/src/views/McpIntegration.vue
git checkout HEAD -- frontend/src/components/AIToolSetup.vue
git clean -fd frontend/src/components/mcp/
```

**Fallback Configuration:**
- Current McpIntegration.vue remains functional
- Users can still use manual configuration section
- No breaking changes to API

---

## Additional Resources

### Design References
- [Material Design: Steppers](https://m3.material.io/components/steppers/overview)
- [JSON Schema Validator Libraries](https://ajv.js.org/)
- [VSCode Settings UI](https://code.visualstudio.com/docs/getstarted/settings) - Inspiration for config UX

### Similar Implementations
- Cursor MCP Configuration UI
- Continue.dev Setup Wizard
- Claude Desktop MCP Manager

### Related GitHub Issues
- (None yet - this is a UX enhancement initiative)

### Documentation to Update
- `/docs/guides/MCP_CONFIGURATION_GUIDE.md` (after implementation)
- `/docs/devlog/` (add completion log)

---

## Agent Execution Instructions

### For UX-Designer Agent

**Your Role:**
1. Design component mockups (Figma optional, Vue pseudo-code sufficient)
2. Define color schemes, spacing, typography
3. Ensure accessibility (WCAG 2.1 AA compliance)
4. Create before/after examples for wizard

**Deliverables:**
- Component specifications (provided above)
- Accessibility checklist
- Visual hierarchy recommendations

### For Frontend-Implementor Agent (TDD)

**Your Role:**
1. Create 3 new components following specifications
2. Write unit tests FIRST (TDD approach)
3. Implement functionality to pass tests
4. Redesign McpIntegration.vue
5. Manual testing across browsers

**Workflow:**
```bash
# 1. Create test file first
touch tests/frontend/components/mcp/JsonValidator.spec.js

# 2. Write failing tests
# 3. Implement component to pass tests
# 4. Repeat for each component

# 5. Test in browser
cd frontend/ && npm run dev
```

**Deliverables:**
- 3 new Vue components with tests
- Updated McpIntegration.vue
- Updated AIToolSetup.vue (minor)
- Manual test results documented

### For Frontend-Tester Agent

**Your Role:**
1. Execute manual testing checklist
2. Cross-browser testing
3. Accessibility audit (screen readers, keyboard nav)
4. Performance testing (validator with large JSON)

**Deliverables:**
- Test results report
- Bug list (if any)
- Performance metrics

---

## Progress Tracking

### Phase 1: Component Architecture
- [ ] Create component files
- [ ] Create utility file
- [ ] Test component imports

### Phase 2: Component Implementation
- [ ] McpConfigWizard.vue complete
- [ ] JsonValidator.vue complete
- [ ] ConfigFileTroubleshooting.vue complete
- [ ] All unit tests passing

### Phase 3: Integration
- [ ] McpIntegration.vue redesigned
- [ ] AIToolSetup.vue enhanced
- [ ] Manual testing complete

### Phase 4: Finalization
- [ ] Cross-browser tested
- [ ] Accessibility verified
- [ ] Git committed
- [ ] Devlog updated
- [ ] Handover archived

---

## Estimated Timeline

- **Phase 1:** 30 minutes
- **Phase 2:** 60 minutes
- **Phase 3:** 45 minutes
- **Phase 4:** 15 minutes
- **Total:** 2.5 hours (conservative estimate)

---

## Notes for Next Agent

**Critical Reminders:**
- Do NOT create Python script installer components
- Focus on transparency and user confidence
- Use Vuetify 3 components (not Vuetify 2)
- Test clipboard API across browsers
- Ensure dark mode compatibility

**Nice-to-Have Enhancements (Optional):**
- 30-second video tutorial embedded
- Animated GIF showing complete flow
- Telemetry for validation success rates
- "Test Connection" button (requires backend endpoint)

---

**Remember:** This is about building user confidence through clarity, not automation through complexity. The copy-paste workflow is sufficient when properly guided.
