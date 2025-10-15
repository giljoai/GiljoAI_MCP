# Handover 0016-B: MCP Configuration UX Enhancement (Phase 2)

**Date:** 2025-10-14 (Revised)
**From Agent:** UX Designer + System Architect
**To Agent:** UX Designer + Frontend Implementor (Coordinated)
**Priority:** Medium
**Estimated Complexity:** 4-5 hours
**Status:** Not Started
**Depends On:** Handover 0016-A (MUST complete stabilization first)
**Blocks:** None

---

## Task Summary

**Enhance the consolidated MCP configuration experience** with status detection, wizard integration, and dashboard guidance. This builds on Phase 1's navigation consolidation to `/settings/integrations`.

**Critical Architecture Context:**
- GiljoAI MCP is a **web server application** accessed via browser (LAN/WAN/localhost)
- Server **cannot write** to user's local `~/.claude.json` file (different machines)
- Configuration is **always manual copy-paste** workflow
- Server detects status via **API key usage tracking** (proxy for "MCP working")

**Expected Outcome:** Guided configuration flow with status detection, wizard integration, and dashboard callouts for first-time users.

---

## Context and Background

### What Phase 1 Delivered (0016-A)

✅ **Navigation Consolidation:** Single entry point at `/settings/integrations`
✅ **Component Reuse:** `McpConfigComponent.vue` for both Settings and Wizard
✅ **Removed Fragmentation:** Deprecated standalone `/mcp-integration` page
✅ **Removed AIToolSetup Dialog:** Consolidated into Settings
✅ **Cross-Platform:** No hardcoded paths, works on all platforms
✅ **Technical Stability:** api.js usage, proper error handling

**Foundation is solid. Phase 2 adds intelligence and guidance.**

### User Journey (After Phase 1)

```
PRIMARY PATH:
User Avatar → Settings → API & Integrations → McpConfigComponent

WIZARD PATH (First Login):
Setup Wizard → /setup?step=mcp → McpConfigComponent (same component)

DASHBOARD PATH (First-Time Users):
Dashboard → Callout Banner → Click "Configure" → Routes to /settings/integrations
```

### Strategic Direction

**Enhanced copy-paste with intelligence:**
- Status detection (not_started, pending, active, inactive)
- Wizard integration via query params
- Dashboard callouts for first-time users
- Validation and troubleshooting built-in

---

## Technical Details

### Phase 2A: Backend Status Detection API (90 minutes)

#### 2A.1 Database Schema Enhancement

**File:** `src/giljo_mcp/models.py`

**Add to User model:**
```python
# MCP Configuration tracking
mcp_config_attempted_at = Column(DateTime, nullable=True)
```

**Add to APIKey model:**
```python
# Track when API key was last used (existing field, ensure it exists)
last_used = Column(DateTime, nullable=True)
```

**Migration (manual, no Alembic):**
```sql
-- Run via psql or add to DatabaseManager.create_tables_async()
ALTER TABLE users ADD COLUMN IF NOT EXISTS mcp_config_attempted_at TIMESTAMP;
-- last_used already exists in api_keys table
```

---

#### 2A.2 Create MCP Status Endpoint

**File:** `api/endpoints/mcp_tools.py` (NEW)

```python
"""
MCP Configuration Status Endpoints
Provides status detection for MCP configuration via API key usage tracking.
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Literal

from ..dependencies import get_current_user, get_db
from src.giljo_mcp.models import User, APIKey

router = APIRouter(prefix="/api/mcp-tools", tags=["mcp-tools"])

StatusType = Literal["not_started", "pending", "active", "inactive"]


@router.get("/status")
async def get_mcp_configuration_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Detect MCP configuration status based on:
    - mcp_config_attempted_at: User started configuration
    - api_key.last_used: API key recently used (proxy for "MCP working")

    States:
    - not_started: Never attempted configuration
    - pending: Started config but key never used
    - active: Key used within last 7 days
    - inactive: Key not used for 7+ days
    """
    status: StatusType = "not_started"
    last_activity = None
    days_since_activity = None

    # Check if user attempted configuration
    if not current_user.mcp_config_attempted_at:
        return {
            "status": "not_started",
            "message": "MCP configuration not started",
            "last_activity": None,
            "days_since_activity": None
        }

    # User attempted config, now check API key usage
    status = "pending"  # Default to pending

    # Find most recent API key usage
    stmt = (
        select(APIKey)
        .where(APIKey.user_id == current_user.id)
        .where(APIKey.last_used.isnot(None))
        .order_by(APIKey.last_used.desc())
        .limit(1)
    )
    result = db.execute(stmt)
    most_recent_key = result.scalar_one_or_none()

    if most_recent_key and most_recent_key.last_used:
        last_activity = most_recent_key.last_used
        days_since = (datetime.utcnow() - last_activity).days
        days_since_activity = days_since

        if days_since <= 7:
            status = "active"
        else:
            status = "inactive"

    messages = {
        "pending": "Configuration started but not yet active",
        "active": "MCP is configured and working",
        "inactive": f"MCP configured but not used in {days_since_activity} days"
    }

    return {
        "status": status,
        "message": messages.get(status, "Unknown status"),
        "last_activity": last_activity.isoformat() if last_activity else None,
        "days_since_activity": days_since_activity,
        "configured_at": current_user.mcp_config_attempted_at.isoformat()
    }


@router.post("/mark-configuration-attempted")
async def mark_configuration_attempted(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Mark that user attempted MCP configuration.
    Called when user clicks "Copy Configuration" button.
    """
    current_user.mcp_config_attempted_at = datetime.utcnow()
    db.commit()

    return {
        "success": True,
        "message": "Configuration attempt recorded",
        "attempted_at": current_user.mcp_config_attempted_at.isoformat()
    }
```

**Register Router:**

**File:** `api/app.py`

```python
# Add import
from api.endpoints import mcp_tools

# Add router registration
app.include_router(mcp_tools.router)
```

**Test Criteria:**
- [ ] GET /api/mcp-tools/status returns correct states
- [ ] not_started when mcp_config_attempted_at is null
- [ ] pending when attempted but no API key usage
- [ ] active when API key used within 7 days
- [ ] inactive when API key not used for 7+ days
- [ ] POST /api/mcp-tools/mark-configuration-attempted sets timestamp

---

### Phase 2B: Frontend Status Integration (90 minutes)

#### 2B.1 Enhance McpConfigComponent with Status Detection

**File:** `frontend/src/components/mcp/McpConfigComponent.vue` (from Phase 1)

**Add to script section:**

```javascript
import { ref, computed, onMounted } from 'vue'
import api from '@/services/api'

// Existing state...
const mcpStatus = ref(null)
const statusLoading = ref(false)

// Status computed properties
const statusColor = computed(() => {
  if (!mcpStatus.value) return 'grey'

  const colors = {
    not_started: 'grey',
    pending: 'warning',
    active: 'success',
    inactive: 'error'
  }
  return colors[mcpStatus.value.status] || 'grey'
})

const statusIcon = computed(() => {
  if (!mcpStatus.value) return 'mdi-help-circle'

  const icons = {
    not_started: 'mdi-circle-outline',
    pending: 'mdi-clock-alert',
    active: 'mdi-check-circle',
    inactive: 'mdi-alert-circle'
  }
  return icons[mcpStatus.value.status] || 'mdi-help-circle'
})

const statusMessage = computed(() => {
  if (!mcpStatus.value) return 'Checking status...'
  return mcpStatus.value.message
})

// Fetch status on mount
onMounted(async () => {
  await fetchMcpStatus()
})

async function fetchMcpStatus() {
  statusLoading.value = true
  try {
    const response = await api.get('/api/mcp-tools/status')
    mcpStatus.value = response.data
  } catch (error) {
    console.error('Failed to fetch MCP status:', error)
    // Fail silently, status is optional
  } finally {
    statusLoading.value = false
  }
}

// Mark configuration attempted when user copies config
async function copyConfig() {
  try {
    await navigator.clipboard.writeText(configJson.value)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)

    // Mark as attempted
    await api.post('/api/mcp-tools/mark-configuration-attempted')
    await fetchMcpStatus()  // Refresh status
  } catch (error) {
    console.error('Copy failed:', error)
  }
}
```

**Add to template (top of component):**

```vue
<!-- Status Banner -->
<v-alert
  v-if="mcpStatus"
  :type="mcpStatus.status === 'active' ? 'success' : 'info'"
  :color="statusColor"
  variant="tonal"
  class="mb-4"
  :icon="statusIcon"
>
  <v-alert-title>
    {{ statusMessage }}
  </v-alert-title>
  <div v-if="mcpStatus.status === 'active' && mcpStatus.last_activity" class="text-caption mt-1">
    Last used: {{ formatDistanceToNow(new Date(mcpStatus.last_activity)) }} ago
  </div>
  <div v-if="mcpStatus.status === 'inactive'" class="text-caption mt-1">
    Your API key hasn't been used recently. Make sure Claude Code CLI is running with the correct config.
  </div>
</v-alert>
```

**Test Criteria:**
- [ ] Status banner displays on component mount
- [ ] Color and icon change based on status
- [ ] "Copy Configuration" marks config as attempted
- [ ] Status refreshes after copy action
- [ ] Works gracefully if API endpoint unavailable

---

#### 2B.2 Add Validation Component

**File:** `frontend/src/components/mcp/ConfigValidator.vue` (NEW)

```vue
<template>
  <v-card variant="outlined">
    <v-card-title class="d-flex align-center">
      <v-icon start>mdi-check-decagram</v-icon>
      Validate Your Configuration
    </v-card-title>
    <v-card-text>
      <p class="text-body-2 mb-3">
        After pasting the config into <code>~/.claude.json</code>, paste your complete file here to verify:
      </p>

      <v-textarea
        v-model="userConfig"
        label="Paste your complete .claude.json content here"
        variant="outlined"
        rows="10"
        placeholder='{ "mcpServers": { ... } }'
        class="config-textarea mb-3"
      />

      <v-btn
        @click="validateConfig"
        color="primary"
        block
        size="large"
        :loading="validating"
      >
        <v-icon start>mdi-check-circle</v-icon>
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
            {{ validationResult.valid ? 'Valid Configuration!' : 'Configuration Has Errors' }}
          </v-alert-title>

          <div v-if="!validationResult.valid && validationResult.errors" class="mt-2">
            <strong>Errors:</strong>
            <ul class="ml-4">
              <li v-for="(error, i) in validationResult.errors" :key="i">{{ error }}</li>
            </ul>
          </div>

          <div v-if="validationResult.valid" class="mt-2">
            Your configuration is valid! Restart Claude Code CLI to apply changes.
          </div>
        </v-alert>
      </v-expand-transition>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref } from 'vue'

const userConfig = ref('')
const validationResult = ref(null)
const validating = ref(false)

function validateConfig() {
  validating.value = true
  validationResult.value = null

  setTimeout(() => {
    const errors = []
    let parsed = null

    // Parse JSON
    try {
      parsed = JSON.parse(userConfig.value)
    } catch (e) {
      errors.push(`Invalid JSON: ${e.message}`)
      validationResult.value = { valid: false, errors }
      validating.value = false
      return
    }

    // Check structure
    if (!parsed.mcpServers) {
      errors.push('Missing "mcpServers" object')
    }

    if (parsed.mcpServers && !parsed.mcpServers['giljo-mcp']) {
      errors.push('Missing "giljo-mcp" configuration in mcpServers')
    }

    if (parsed.mcpServers?.['giljo-mcp']) {
      const giljo = parsed.mcpServers['giljo-mcp']
      if (!giljo.command) errors.push('Missing "command" field')
      if (!giljo.args) errors.push('Missing "args" array')
      if (!giljo.env?.GILJO_API_KEY) errors.push('Missing GILJO_API_KEY in env')
      if (giljo.env?.GILJO_API_KEY === '<your-api-key-here>') {
        errors.push('Replace placeholder API key with real key')
      }
    }

    validationResult.value = {
      valid: errors.length === 0,
      errors
    }
    validating.value = false
  }, 500)
}
</script>

<style scoped>
.config-textarea :deep(textarea) {
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
}

code {
  background-color: rgba(var(--v-theme-surface-variant), 0.5);
  padding: 2px 6px;
  border-radius: 4px;
}
</style>
```

**Import and use in McpConfigComponent.vue:**

```vue
<template>
  <!-- After config display section -->
  <ConfigValidator class="mt-6" />
</template>

<script setup>
import ConfigValidator from './ConfigValidator.vue'
</script>
```

**Test Criteria:**
- [ ] Validates JSON syntax
- [ ] Detects missing mcpServers
- [ ] Detects missing giljo-mcp config
- [ ] Detects placeholder API key
- [ ] Shows clear error messages
- [ ] Shows success message for valid config

---

### Phase 2C: Setup Wizard Integration (60 minutes)

#### 2C.1 Add Query Param Routing to Settings

**File:** `frontend/src/views/Settings/IntegrationsView.vue` (from Phase 1)

**Add to script:**

```javascript
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const highlightMcp = ref(false)

onMounted(() => {
  // Check if routed from wizard
  if (route.query.from === 'wizard' || route.query.step === 'mcp') {
    highlightMcp.value = true

    // Scroll to MCP component after mount
    setTimeout(() => {
      const mcpElement = document.getElementById('mcp-config-section')
      if (mcpElement) {
        mcpElement.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }
    }, 100)
  }
})
```

**Update template:**

```vue
<template>
  <v-container>
    <h1 class="text-h4 mb-6">API & Integrations</h1>
    <p class="text-subtitle-1 mb-6">
      Configure external AI tools to connect with GiljoAI MCP
    </p>

    <!-- MCP Configuration Section -->
    <v-card
      id="mcp-config-section"
      :variant="highlightMcp ? 'elevated' : 'outlined'"
      :color="highlightMcp ? 'primary' : undefined"
      class="mb-6"
    >
      <v-card-title v-if="highlightMcp" class="bg-primary text-white">
        <v-icon start>mdi-star</v-icon>
        Configure Claude Code (Recommended)
      </v-card-title>

      <McpConfigComponent />
    </v-card>

    <!-- Future: Other integrations can go here -->
  </v-container>
</template>
```

**Test Criteria:**
- [ ] Normal navigation shows no highlight
- [ ] Query param `?from=wizard` triggers highlight
- [ ] Query param `?step=mcp` triggers highlight
- [ ] Component scrolls into view automatically
- [ ] Highlight is visually clear but not intrusive

---

#### 2C.2 Update Setup Wizard to Route to Settings

**File:** `frontend/src/views/SetupWizard.vue`

**Replace MCP step with routing:**

```vue
<!-- OLD: <McpConfigStep /> -->
<!-- NEW: Route to Settings instead -->

<template v-if="currentStep === 3">
  <v-card>
    <v-card-title class="text-h5">
      <v-icon start color="primary">mdi-connection</v-icon>
      Configure AI Tools
    </v-card-title>
    <v-card-text>
      <p class="text-body-1 mb-4">
        Connect Claude Code CLI to unlock powerful agentic workflows.
      </p>

      <v-alert type="info" variant="tonal" class="mb-4">
        <v-alert-title>Quick Setup</v-alert-title>
        We'll guide you through configuring Claude Code in the next step.
        It only takes 60 seconds!
      </v-alert>

      <v-btn
        color="primary"
        size="x-large"
        block
        @click="navigateToIntegrations"
        prepend-icon="mdi-arrow-right-circle"
      >
        Continue to Configuration
      </v-btn>

      <v-btn
        variant="text"
        block
        class="mt-2"
        @click="skipMcpConfig"
      >
        Skip for now
      </v-btn>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

function navigateToIntegrations() {
  router.push({
    path: '/settings/integrations',
    query: { from: 'wizard', step: 'mcp' }
  })
}

function skipMcpConfig() {
  currentStep.value = 4  // Or finish wizard
}
</script>
```

**Test Criteria:**
- [ ] Wizard step 3 shows MCP callout card
- [ ] "Continue to Configuration" routes to /settings/integrations?from=wizard
- [ ] Settings page highlights MCP section
- [ ] "Skip for now" advances wizard
- [ ] User can return to wizard from Settings

---

### Phase 2D: Dashboard Callout Component (45 minutes)

#### 2D.1 Create Dashboard Callout Component

**File:** `frontend/src/components/dashboard/McpConfigCallout.vue` (NEW)

```vue
<template>
  <v-alert
    v-if="shouldShow"
    type="info"
    variant="tonal"
    prominent
    closable
    @click:close="dismissCallout"
    class="mb-6"
  >
    <v-alert-title class="d-flex align-center">
      <v-icon start size="large">mdi-robot-excited</v-icon>
      <span class="text-h6">Unlock Agentic Workflows</span>
    </v-alert-title>

    <p class="mt-2 mb-3">
      Connect Claude Code CLI to enable powerful multi-agent coordination, context management, and automated task execution.
    </p>

    <v-btn
      color="primary"
      size="large"
      @click="navigateToConfig"
      prepend-icon="mdi-rocket-launch"
    >
      Configure Claude Code (60 seconds)
    </v-btn>

    <v-btn
      variant="text"
      class="ml-2"
      @click="dismissCallout"
    >
      Maybe Later
    </v-btn>
  </v-alert>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/services/api'

const router = useRouter()
const shouldShow = ref(false)

onMounted(async () => {
  // Check if user dismissed callout
  const dismissed = localStorage.getItem('mcp-callout-dismissed')
  if (dismissed === 'true') {
    shouldShow.value = false
    return
  }

  // Check MCP status
  try {
    const response = await api.get('/api/mcp-tools/status')
    const status = response.data.status

    // Show callout if not started or pending
    if (status === 'not_started' || status === 'pending') {
      shouldShow.value = true
    }
  } catch (error) {
    // If endpoint fails, don't show callout
    shouldShow.value = false
  }
})

function navigateToConfig() {
  router.push({
    path: '/settings/integrations',
    query: { from: 'dashboard', step: 'mcp' }
  })
}

function dismissCallout() {
  localStorage.setItem('mcp-callout-dismissed', 'true')
  shouldShow.value = false
}
</script>
```

**Test Criteria:**
- [ ] Callout shows only if status is not_started or pending
- [ ] Callout does not show if dismissed
- [ ] "Configure Claude Code" button routes to Settings with query param
- [ ] "Maybe Later" dismisses callout
- [ ] Dismissal persists across sessions (localStorage)
- [ ] Callout does not show if MCP is active

---

#### 2D.2 Integrate Callout in Dashboard

**File:** `frontend/src/views/Dashboard.vue`

```vue
<template>
  <v-container>
    <!-- Add at top of dashboard -->
    <McpConfigCallout />

    <!-- Rest of dashboard content -->
    <!-- ... -->
  </v-container>
</template>

<script setup>
import McpConfigCallout from '@/components/dashboard/McpConfigCallout.vue'
</script>
```

**Test Criteria:**
- [ ] Callout appears at top of Dashboard
- [ ] Does not interfere with other dashboard content
- [ ] Only shows for users who haven't configured MCP
- [ ] Dismissal works correctly

---

## Implementation Plan Summary

### Phase 2A: Backend Status Detection (90 min)
- [ ] Add `mcp_config_attempted_at` to User model
- [ ] Create `/api/mcp-tools/status` endpoint
- [ ] Create `/api/mcp-tools/mark-configuration-attempted` endpoint
- [ ] Register router in app.py
- [ ] Test all status states

### Phase 2B: Frontend Status Integration (90 min)
- [ ] Add status detection to McpConfigComponent
- [ ] Create ConfigValidator component
- [ ] Integrate validator into Settings view
- [ ] Test status display and validation

### Phase 2C: Wizard Integration (60 min)
- [ ] Add query param routing to IntegrationsView
- [ ] Update SetupWizard to route to Settings
- [ ] Test wizard → settings flow
- [ ] Test highlight and scroll behavior

### Phase 2D: Dashboard Callout (45 min)
- [ ] Create McpConfigCallout component
- [ ] Integrate into Dashboard
- [ ] Test dismissal persistence
- [ ] Test status-based display logic

---

## Success Criteria

### Definition of Done
- [ ] Backend status API returns correct states (not_started, pending, active, inactive)
- [ ] Frontend displays status banner in McpConfigComponent
- [ ] Config validator catches common JSON errors
- [ ] Wizard routes to Settings with query params
- [ ] Settings highlights MCP section when routed from wizard
- [ ] Dashboard callout shows for unconfigured users
- [ ] Callout dismissal persists across sessions
- [ ] All status transitions work correctly
- [ ] No console errors
- [ ] Git committed with proper message

### User Experience Metrics
- **Status accuracy:** 100% correct state detection
- **Wizard completion rate:** > 80% complete MCP config from wizard
- **Dashboard conversion:** > 50% of callout clicks complete config
- **Configuration time:** < 60 seconds from start to copy
- **Validation success rate:** > 90% of configs pass validation

---

## Testing Checklist

### Backend Tests
- [ ] Status API returns not_started for new user
- [ ] Status API returns pending after mark-configuration-attempted
- [ ] Status API returns active when API key used < 7 days ago
- [ ] Status API returns inactive when API key used > 7 days ago
- [ ] Mark-configuration-attempted sets timestamp correctly

### Frontend Tests
- [ ] Status banner displays correct color/icon for each state
- [ ] Copy button marks configuration as attempted
- [ ] Validator detects invalid JSON
- [ ] Validator detects missing mcpServers
- [ ] Validator detects placeholder API key
- [ ] Wizard routes to Settings with query params
- [ ] Settings highlights MCP section from wizard
- [ ] Dashboard callout shows for not_started status
- [ ] Dashboard callout dismissal persists
- [ ] Dashboard callout does not show if MCP active

---

## Rollback Plan

**Revert to Phase 1 stable state:**
```bash
# Revert backend changes
git checkout HEAD~1 -- api/endpoints/mcp_tools.py
git checkout HEAD~1 -- src/giljo_mcp/models.py
git checkout HEAD~1 -- api/app.py

# Revert frontend changes
git checkout HEAD~1 -- frontend/src/components/mcp/McpConfigComponent.vue
git checkout HEAD~1 -- frontend/src/views/Settings/IntegrationsView.vue
git checkout HEAD~1 -- frontend/src/views/SetupWizard.vue
git checkout HEAD~1 -- frontend/src/views/Dashboard.vue

# Remove new files
rm -f frontend/src/components/mcp/ConfigValidator.vue
rm -f frontend/src/components/dashboard/McpConfigCallout.vue
```

---

## Estimated Timeline

- **Phase 2A (Backend Status API):** 90 minutes
- **Phase 2B (Frontend Status Integration):** 90 minutes
- **Phase 2C (Wizard Integration):** 60 minutes
- **Phase 2D (Dashboard Callout):** 45 minutes
- **Testing & Polish:** 45 minutes

**Total:** 5-6 hours

---

## Notes for Next Agent

**This is UX enhancement building on Phase 1:**
- ✅ Single entry point at /settings/integrations (done in Phase 1)
- ✅ Reusable McpConfigComponent (done in Phase 1)
- ✅ Cross-platform compatibility (done in Phase 1)
- ➕ Now adding: status detection, wizard integration, dashboard guidance

**Key architectural constraints:**
- Server is accessed via browser (cannot write to user's local files)
- Configuration is always manual copy-paste
- Status detection uses API key usage as proxy
- Wizard integration uses query param routing (no new pages)

**After completion:**
- Monitor dashboard callout conversion rate
- Gather feedback on status detection accuracy
- Consider adding "Reconnect" action for inactive status
- Consider email notifications for inactive MCP (future enhancement)

---

**Remember: We're guiding users through a manual process, not automating it. The intelligence is in knowing where the user is and what they need next.**
