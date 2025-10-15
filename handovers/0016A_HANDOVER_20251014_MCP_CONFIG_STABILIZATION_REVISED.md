# Handover 0016-A: MCP Configuration Stabilization (Phase 1) - REVISED

**Date:** 2025-10-14 (Revised)
**From Agent:** System Architect + UX Auditor
**To Agent:** Frontend Implementor + TDD Agent
**Priority:** **HIGH** (Critical bugs must be fixed)
**Estimated Complexity:** 3-4 hours
**Status:** Not Started
**Depends On:** None
**Blocks:** Handover 0016-B (UX Enhancement)

---

## Task Summary

**Fix critical bugs and technical debt** in the current MCP configuration implementation while **consolidating navigation** into a single entry point. This stabilization phase addresses runtime errors, cross-platform compatibility issues, and API client inconsistencies discovered during audit.

**Why Phase 1 First:** UX improvements are meaningless if the code is broken. We must stabilize the foundation before building new features.

**Expected Outcome:** MCP configuration works correctly on Windows/Linux/macOS without runtime errors, accessible through Settings → API & Integrations.

---

## Context and Background

### Critical Architecture Understanding

**GiljoAI MCP is a WEB SERVER application:**
- Server runs on one machine (could be localhost, LAN, or WAN)
- Users access via web browser from their own machines
- Server **CANNOT write** to users' local filesystem (`~/.claude.json` is on their machine, not the server)
- Configuration is **ALWAYS manual copy-paste** workflow
- Server can **detect API key usage** as proxy for "MCP is working"

### Audit Findings Summary

**UX Designer identified:**
- Fragmented user journey (standalone `/mcp-integration` page, AIToolSetup dialog, wizard step)
- Hardcoded Windows path breaking cross-platform compatibility
- Inconsistent API key handling across components
- Expansion panel cognitive overload

**Frontend Engineer identified:**
- **McpConfigStep.vue calls removed v3.0 API methods** → Runtime crashes
- **Hardcoded `F:/GiljoAI_MCP` path** → Breaks Linux/macOS
- Dual template systems (frontend + backend)
- Direct fetch() bypassing api.js interceptors
- API key auto-generation without user consent

### Navigation Consolidation Strategy

**Current (Fragmented):**
- Entry Point 1: `/mcp-integration` standalone page
- Entry Point 2: AIToolSetup dialog (from Settings/Dashboard)
- Entry Point 3: McpConfigStep in wizard

**Target (Consolidated):**
- **Single Entry Point:** User Avatar → Settings → API & Integrations
- Route: `/settings/integrations`
- Reusable component for both Settings AND Wizard (using query params in 0016-B)
- Remove standalone `/mcp-integration` page

---

## Technical Details

### Files to Modify

**Priority 1: Navigation Consolidation (MUST DO)**

1. **`frontend/src/views/Settings/IntegrationsView.vue`** (NEW FILE)
   - **Create:** New Settings submenu view
   - **Contains:** `McpConfigComponent.vue`
   - **Impact:** Single source of truth for MCP configuration

2. **`frontend/src/components/McpConfigComponent.vue`** (RENAME from AIToolSetup.vue)
   - **Change:** Remove dialog wrapper, make standalone component
   - **Fix:** Replace fetch() with api.js
   - **Fix:** Remove hardcoded paths
   - **Impact:** Reusable in Settings AND Wizard

3. **`frontend/src/router/index.js`**
   - **Add:** `/settings/integrations` route
   - **Impact:** Makes Settings → API & Integrations accessible

4. **Settings navigation component**
   - **Add:** "API & Integrations" menu item
   - **Impact:** Discoverable entry point

**Priority 2: Remove Fragmented Components (MUST DO)**

5. **`frontend/src/views/McpIntegration.vue`**
   - **Action:** DELETE (consolidating into Settings)
   - **Remove from:** Router configuration
   - **Impact:** Reduces navigation complexity

6. **`frontend/src/components/setup/McpConfigStep.vue`**
   - **Action:** DELETE (broken, will replace with wizard integration in 0016-B)
   - **Remove from:** SetupWizard.vue imports
   - **Impact:** Prevents runtime crashes

**Priority 3: Cross-Platform Fixes (MUST DO)**

7. **`frontend/src/utils/configTemplates.js`**
   - **Fix:** Remove `GILJO_MCP_HOME: 'F:/GiljoAI_MCP'`
   - **Fix:** Remove `pythonPath` parameter (use `'python'` directly)
   - **Impact:** Works on all platforms

**Priority 4: Technical Debt (SHOULD DO)**

8. **`api/endpoints/mcp_installer.py`**
   - **Fix:** Move `SECRET_KEY` to environment variable
   - **Impact:** Security best practice

9. **`frontend/src/components/McpConfigComponent.vue`**
   - **Fix:** Replace `alert()` with v-snackbar
   - **Impact:** Consistent UX

---

## Implementation Plan

### Phase 1A: Create Consolidated Navigation (90 minutes)

#### Step 1.1: Create IntegrationsView.vue

**File:** `frontend/src/views/Settings/IntegrationsView.vue` (NEW)

```vue
<template>
  <v-container>
    <h1 class="text-h4 mb-6">API & Integrations</h1>
    <p class="text-subtitle-1 mb-6">
      Configure external AI tools to connect with GiljoAI MCP
    </p>

    <!-- MCP Configuration Component -->
    <McpConfigComponent />
  </v-container>
</template>

<script setup>
import McpConfigComponent from '@/components/McpConfigComponent.vue'
</script>
```

**Test Criteria:**
- [ ] View renders without errors
- [ ] Component properly embedded
- [ ] Page title and description display correctly

---

#### Step 1.2: Add Route Configuration

**File:** `frontend/src/router/index.js`

Add route:
```javascript
{
  path: '/settings/integrations',
  name: 'IntegrationsSettings',
  component: () => import('@/views/Settings/IntegrationsView.vue'),
  meta: {
    requiresAuth: true,
    title: 'API & Integrations'
  }
}
```

**Test Criteria:**
- [ ] Route `/settings/integrations` accessible
- [ ] Auth guard prevents unauthenticated access
- [ ] Page title updates correctly

---

#### Step 1.3: Add Settings Navigation Item

**File:** Settings layout component (find current Settings navigation)

Add menu item:
```vue
<v-list-item
  to="/settings/integrations"
  prepend-icon="mdi-connection"
  title="API & Integrations"
  subtitle="Configure Claude Code & MCP"
/>
```

**Test Criteria:**
- [ ] Menu item appears in Settings sidebar
- [ ] Clicking navigates to `/settings/integrations`
- [ ] Active state highlights correctly

---

### Phase 1B: Transform AIToolSetup into Reusable Component (60 minutes)

#### Step 1.4: Rename and Restructure Component

**Action:** Rename `frontend/src/components/AIToolSetup.vue` → `frontend/src/components/McpConfigComponent.vue`

**Changes:**

1. **Remove dialog wrapper:**
```vue
<!-- BEFORE -->
<v-dialog v-model="modelValue" max-width="800px">
  <v-card>
    <!-- content -->
  </v-card>
</v-dialog>

<!-- AFTER -->
<v-card>
  <!-- content -->
</v-card>
```

2. **Remove dialog-related props:**
```javascript
// BEFORE
const props = defineProps({
  modelValue: Boolean
})

const emit = defineEmits(['update:modelValue'])

// AFTER
// No dialog props needed
```

3. **Keep all configuration logic intact**

**Test Criteria:**
- [ ] Component renders without dialog wrapper
- [ ] All configuration functionality works
- [ ] No console errors

---

#### Step 1.5: Replace fetch() with api.js

**File:** `frontend/src/components/McpConfigComponent.vue`

**Add import:**
```javascript
import api from '@/services/api'
```

**Replace API calls:**

```javascript
// BEFORE (example from line ~258)
const apiKeyResponse = await fetch(`${API_CONFIG.REST_API.baseURL}/api/auth/api-keys`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
  },
  body: JSON.stringify({ name: `Claude Code - ${new Date().toLocaleDateString()}` })
})

// AFTER
const response = await api.post('/api/auth/api-keys', {
  name: `Claude Code - ${new Date().toLocaleDateString()}`
})
generatedApiKey.value = response.data.key
```

**Benefits:**
- Automatic auth token injection
- Automatic tenant key injection
- Centralized error handling
- Easier to test

**Test Criteria:**
- [ ] API key generation works
- [ ] Auth token automatically included
- [ ] Errors handled by axios interceptors

---

### Phase 1C: Fix Cross-Platform Issues (45 minutes)

#### Step 1.6: Remove Hardcoded Paths from configTemplates.js

**File:** `frontend/src/utils/configTemplates.js`

**BEFORE:**
```javascript
export function generateClaudeCodeConfig(apiKey, serverUrl, pythonPath = 'python') {
  return JSON.stringify({
    'giljo-mcp': {
      command: pythonPath,
      args: ['-m', 'giljo_mcp'],
      env: {
        GILJO_MCP_HOME: 'F:/GiljoAI_MCP',  // ❌ BREAKS LINUX/MACOS
        GILJO_SERVER_URL: serverUrl,
        GILJO_API_KEY: apiKey,
      },
    },
  }, null, 2)
}
```

**AFTER:**
```javascript
export function generateClaudeCodeConfig(apiKey, serverUrl) {
  return JSON.stringify({
    'giljo-mcp': {
      command: 'python',  // Simple, cross-platform
      args: ['-m', 'giljo_mcp'],
      env: {
        // GILJO_MCP_HOME removed - server.py auto-detects using Path.cwd()
        GILJO_SERVER_URL: serverUrl,
        GILJO_API_KEY: apiKey,
      },
    },
  }, null, 2)
}
```

**Rationale:**
- Backend `server.py` uses `Path.cwd()` to detect project root
- Hardcoded path only needed during development
- Python command `python` works on all platforms

**Test Criteria:**
- [ ] Config generated on Windows works
- [ ] Config generated on macOS works (if testable)
- [ ] Config generated on Linux works (if testable)
- [ ] MCP server starts without GILJO_MCP_HOME

---

#### Step 1.7: Update McpConfigComponent to Remove projectPath

**File:** `frontend/src/components/McpConfigComponent.vue`

**BEFORE (around line 280):**
```javascript
const serverUrl = `${window.location.protocol}//${window.location.hostname}:7272`
const projectPath = 'F:/GiljoAI_MCP'  // ❌ HARDCODED
const pythonPath = getPythonPath(projectPath, detectOS())
```

**AFTER:**
```javascript
const serverUrl = `${window.location.protocol}//${window.location.hostname}:7272`
// projectPath removed - not needed
// Calling simplified configTemplates.generateClaudeCodeConfig(apiKey, serverUrl)
```

**Test Criteria:**
- [ ] Config generation works without projectPath
- [ ] No hardcoded paths in generated config
- [ ] Works cross-platform

---

### Phase 1D: Remove Broken Components (30 minutes)

#### Step 1.8: Remove McpConfigStep from Wizard

**File:** `frontend/src/views/SetupWizard.vue`

**Changes:**

1. **Remove import:**
```javascript
// DELETE THIS LINE
import McpConfigStep from '@/components/setup/McpConfigStep.vue'
```

2. **Remove from components:**
```javascript
components: {
  WelcomeStep,
  DatabaseStep,
  // McpConfigStep,  ← DELETE
  CompletionStep,
}
```

3. **Update step count:**
```javascript
const totalSteps = 2  // Was 3
```

4. **Update CompletionStep.vue:**
```vue
<v-card-text>
  <p>Your GiljoAI setup is complete!</p>

  <v-alert type="info" variant="tonal" class="mt-4">
    <v-icon start>mdi-connection</v-icon>
    <div>
      <strong>Optional:</strong> Configure MCP integration for AI coding tools
      <v-btn
        variant="text"
        color="primary"
        class="ml-2"
        @click="$router.push('/settings/integrations')"
      >
        Set Up Now
      </v-btn>
    </div>
  </v-alert>
</v-card-text>
```

**Test Criteria:**
- [ ] Setup wizard loads without errors
- [ ] Wizard shows 2 steps (Welcome, Database)
- [ ] Completion step shows MCP link
- [ ] Clicking link navigates to `/settings/integrations`
- [ ] No console errors

---

#### Step 1.9: Remove McpIntegration Standalone Page

**Files to modify:**

1. **`frontend/src/router/index.js`** - Remove `/mcp-integration` route
2. **`frontend/src/views/McpIntegration.vue`** - DELETE file (or comment out entirely)
3. **Update any links** pointing to `/mcp-integration` → `/settings/integrations`

**Test Criteria:**
- [ ] `/mcp-integration` route no longer exists
- [ ] No broken links in application
- [ ] No console errors about missing component

---

### Phase 1E: Technical Debt Cleanup (30 minutes)

#### Step 1.10: Move SECRET_KEY to Environment Variable

**File:** `api/endpoints/mcp_installer.py`

**BEFORE:**
```python
SECRET_KEY = "giljo-mcp-installer-secret-key-2024"  # TODO: Move to env var
```

**AFTER:**
```python
import os
from pathlib import Path

# Load from environment or use default (with warning)
SECRET_KEY = os.getenv(
    'MCP_INSTALLER_SECRET_KEY',
    'giljo-mcp-installer-default-dev-key'
)

# Warn if using default in production
if SECRET_KEY == 'giljo-mcp-installer-default-dev-key':
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(
        "Using default MCP installer secret key. "
        "Set MCP_INSTALLER_SECRET_KEY environment variable for production."
    )
```

**Update `.env.example`:**
```bash
# MCP Installer Secret (for share link token generation)
MCP_INSTALLER_SECRET_KEY=your-secret-key-here
```

**Test Criteria:**
- [ ] Share link generation works
- [ ] Token validation works
- [ ] Warning logged when using default key

---

#### Step 1.11: Replace alert() with v-snackbar

**File:** `frontend/src/components/McpConfigComponent.vue`

**Add snackbar state:**
```javascript
const snackbar = ref({
  show: false,
  message: '',
  color: 'error'
})

function showError(message) {
  snackbar.value = {
    show: true,
    message,
    color: 'error'
  }
}
```

**Replace alert() calls:**
```javascript
// BEFORE
alert('Failed to generate configuration. Please try again.')

// AFTER
showError('Failed to generate configuration. Please try again.')
```

**Add snackbar to template:**
```vue
<!-- Add before closing </v-card> tag -->
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
```

**Test Criteria:**
- [ ] Errors shown as snackbar, not alert
- [ ] Snackbar auto-closes after 3 seconds
- [ ] Snackbar dismissible

---

## Testing Requirements

### Manual Testing Checklist

**Navigation:**
- [ ] Settings → API & Integrations loads correctly
- [ ] Menu item highlights when active
- [ ] Auth guard prevents unauthenticated access

**Component Functionality:**
- [ ] MCP configuration displays correctly
- [ ] API key generation works
- [ ] Config copy-paste works
- [ ] Download scripts work (Windows/Unix)

**Cross-Platform:**
- [ ] Generated config contains no hardcoded paths
- [ ] Config works on Windows
- [ ] Config works on macOS (if testable)
- [ ] Config works on Linux (if testable)

**Wizard:**
- [ ] Setup wizard completes without errors
- [ ] MCP link in completion step works
- [ ] No console errors

**Cleanup:**
- [ ] No broken routes
- [ ] No broken component imports
- [ ] No console errors anywhere

### Unit Tests

**File:** `tests/frontend/utils/configTemplates.spec.js`

```javascript
import { generateClaudeCodeConfig } from '@/utils/configTemplates'

describe('generateClaudeCodeConfig', () => {
  it('should generate valid JSON config', () => {
    const config = generateClaudeCodeConfig('test-key', 'http://localhost:7272')
    const parsed = JSON.parse(config)

    expect(parsed['giljo-mcp']).toBeDefined()
    expect(parsed['giljo-mcp'].command).toBe('python')
    expect(parsed['giljo-mcp'].env.GILJO_API_KEY).toBe('test-key')
  })

  it('should not include GILJO_MCP_HOME', () => {
    const config = generateClaudeCodeConfig('test-key', 'http://localhost:7272')
    const parsed = JSON.parse(config)

    expect(parsed['giljo-mcp'].env.GILJO_MCP_HOME).toBeUndefined()
  })

  it('should work cross-platform (no hardcoded paths)', () => {
    const config = generateClaudeCodeConfig('test-key', 'http://localhost:7272')

    expect(config).not.toContain('F:/')
    expect(config).not.toContain('C:\\')
    expect(config).not.toContain('\\\\')
  })
})
```

### Verification Commands

```bash
# 1. Search for hardcoded paths
grep -r "F:/" frontend/src/
grep -r "C:\\\\" frontend/src/

# Expected: No matches

# 2. Search for native fetch()
grep -r "fetch(" frontend/src/components/McpConfigComponent.vue

# Expected: No matches (should use api.get/api.post)

# 3. Search for alert()
grep -r "alert(" frontend/src/

# Expected: Only in test files

# 4. Run tests
cd frontend/
npm run test:unit

# Expected: All pass

# 5. Build production
npm run build

# Expected: No errors, no warnings
```

---

## Success Criteria

### Definition of Done

- [ ] `/settings/integrations` route exists and loads correctly
- [ ] Settings navigation includes "API & Integrations" menu item
- [ ] `McpConfigComponent.vue` is standalone (no dialog wrapper)
- [ ] No hardcoded Windows paths in codebase
- [ ] McpConfigStep.vue removed from wizard
- [ ] McpIntegration.vue standalone page removed
- [ ] All fetch() calls replaced with api.js
- [ ] All alert() calls replaced with v-snackbar
- [ ] SECRET_KEY moved to environment variable
- [ ] All unit tests passing
- [ ] No console errors in production build
- [ ] Tested on at least 2 platforms (Windows + Linux/macOS)

### Navigation Consolidation Complete

**Before:**
- 3 entry points (standalone page, dialog, wizard step)
- Confusing user journey
- Overlapping functionality

**After:**
- 1 entry point (Settings → API & Integrations)
- Clear, discoverable location
- Reusable component for future wizard integration

---

## Rollback Plan

**If things go wrong:**

```bash
# Rollback navigation changes
git checkout HEAD -- frontend/src/router/index.js
git checkout HEAD -- frontend/src/views/Settings/

# Rollback component changes
git checkout HEAD -- frontend/src/components/AIToolSetup.vue
git checkout HEAD -- frontend/src/components/McpConfigComponent.vue

# Rollback template changes
git checkout HEAD -- frontend/src/utils/configTemplates.js

# Rollback wizard changes
git checkout HEAD -- frontend/src/views/SetupWizard.vue
git checkout HEAD -- frontend/src/components/setup/
```

---

## Estimated Timeline

- **Phase 1A (Navigation):** 90 minutes
- **Phase 1B (Component Transformation):** 60 minutes
- **Phase 1C (Cross-Platform Fixes):** 45 minutes
- **Phase 1D (Cleanup):** 30 minutes
- **Phase 1E (Technical Debt):** 30 minutes
- **Testing & Verification:** 45 minutes

**Total:** 3-4 hours

---

## Notes for Next Agent

**Critical Reminders:**
- This is a web server application - server CANNOT write to user's local files
- Configuration is ALWAYS manual copy-paste
- Single entry point: Settings → API & Integrations
- Test on multiple platforms (Windows + WSL/Linux minimum)
- No new features - only fix what's broken and consolidate navigation

**After Completion:**
- Mark 0016-A as complete in handovers README
- Phase 1 must be stable before starting 0016-B
- 0016-B will add status detection and wizard integration using query params

---

**This handover focuses on stability and consolidation. Get the foundation solid first.**
