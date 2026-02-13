# Handover 0424i: AppBar + User Settings Integration

**Status:** 🟢 Ready for Execution
**Color:** `#FF9800` (Orange - UI Integration)
**Prerequisites:** 0424h (API + Welcome Screen)
**Spawns:** 0424j (Migration + NOT NULL Constraint)
**Chain:** 0424 Organization Hierarchy Series

---

## Overview

Make organization visible throughout the application by integrating workspace name and role into navigation and user settings.

**Architecture Change:**
- AppBar shows workspace name under username in menu
- AppBar shows role badge (owner/admin/member/viewer)
- AppBar adds "My Workspace" menu link → OrganizationSettings
- UserSettings adds "Workspace" tab with org details
- Terminology: "Organization" → "Workspace" throughout UI

**What This Accomplishes:**
- Users see workspace context in every view (via AppBar)
- Role badge provides visual permission indicator
- Quick access to workspace settings from AppBar menu
- User settings centralizes workspace information
- Consistent "Workspace" terminology improves UX

**Impact:**
- Workspace is always visible (not hidden in settings)
- Role-based UI hints (admins see management options)
- Foundation for multi-workspace future (if needed)

---

## Prerequisites

**Required Handovers:**
- ✅ 0424h: User store has org state and computed properties

**Verify Before Starting:**
```powershell
# Check user store has org state
cat frontend/src/stores/user.js | grep "orgId"
cat frontend/src/stores/user.js | grep "currentOrg"

# Check AppBar exists
cat frontend/src/components/navigation/AppBar.vue | grep "AppBar"

# Check UserSettings exists
cat frontend/src/views/UserSettings.vue | grep "UserSettings"
```

---

## Implementation Phases

### 🔴 RED PHASE: Failing Tests

**1. Frontend Tests - AppBar Displays Org Data**

Create: `frontend/tests/unit/components/navigation/AppBar.spec.js`

```javascript
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import AppBar from '@/components/navigation/AppBar.vue'
import { useUserStore } from '@/stores/user'
import { describe, it, expect, beforeEach } from 'vitest'

const vuetify = createVuetify({ components, directives })

describe('AppBar - Org Integration', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('should display workspace name under username', async () => {
    const wrapper = mount(AppBar, {
      global: {
        plugins: [vuetify]
      }
    })

    const userStore = useUserStore()
    userStore.setUserData({
      id: 'user-1',
      username: 'testuser',
      org_id: 'org-123',
      org_name: 'Acme Corp',
      org_role: 'admin'
    })

    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('testuser')
    expect(wrapper.text()).toContain('Acme Corp')
  })

  it('should display role badge for owner', async () => {
    const wrapper = mount(AppBar, {
      global: {
        plugins: [vuetify]
      }
    })

    const userStore = useUserStore()
    userStore.setUserData({
      id: 'user-1',
      username: 'owner',
      org_role: 'owner'
    })

    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('Owner')
  })

  it('should display role badge for admin', async () => {
    const wrapper = mount(AppBar, {
      global: {
        plugins: [vuetify]
      }
    })

    const userStore = useUserStore()
    userStore.setUserData({
      id: 'user-1',
      username: 'admin',
      org_role: 'admin'
    })

    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('Admin')
  })

  it('should show "My Workspace" menu link', async () => {
    const wrapper = mount(AppBar, {
      global: {
        plugins: [vuetify]
      }
    })

    const userStore = useUserStore()
    userStore.setUserData({
      id: 'user-1',
      org_id: 'org-123',
      org_name: 'Test Org'
    })

    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('My Workspace')
  })

  it('should hide workspace info when user has no org', async () => {
    const wrapper = mount(AppBar, {
      global: {
        plugins: [vuetify]
      }
    })

    const userStore = useUserStore()
    userStore.setUserData({
      id: 'user-1',
      username: 'testuser'
      // No org fields
    })

    await wrapper.vm.$nextTick()

    expect(wrapper.text()).not.toContain('My Workspace')
  })
})
```

**2. Frontend Tests - UserSettings Workspace Tab**

Create: `frontend/tests/unit/views/UserSettings.spec.js`

```javascript
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import UserSettings from '@/views/UserSettings.vue'
import { useUserStore } from '@/stores/user'
import { describe, it, expect, beforeEach } from 'vitest'

const vuetify = createVuetify({ components, directives })

describe('UserSettings - Workspace Tab', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('should have Workspace tab', async () => {
    const wrapper = mount(UserSettings, {
      global: {
        plugins: [vuetify]
      }
    })

    expect(wrapper.text()).toContain('Workspace')
  })

  it('should display workspace name', async () => {
    const wrapper = mount(UserSettings, {
      global: {
        plugins: [vuetify]
      }
    })

    const userStore = useUserStore()
    userStore.setUserData({
      id: 'user-1',
      org_id: 'org-123',
      org_name: 'Acme Corp',
      org_role: 'admin'
    })

    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('Acme Corp')
  })

  it('should show role badge', async () => {
    const wrapper = mount(UserSettings, {
      global: {
        plugins: [vuetify]
      }
    })

    const userStore = useUserStore()
    userStore.setUserData({
      id: 'user-1',
      org_role: 'owner'
    })

    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('Owner')
  })

  it('should show Manage Workspace button for owners', async () => {
    const wrapper = mount(UserSettings, {
      global: {
        plugins: [vuetify]
      }
    })

    const userStore = useUserStore()
    userStore.setUserData({
      id: 'user-1',
      org_id: 'org-123',
      org_role: 'owner'
    })

    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('Manage Workspace')
  })

  it('should show Manage Workspace button for admins', async () => {
    const wrapper = mount(UserSettings, {
      global: {
        plugins: [vuetify]
      }
    })

    const userStore = useUserStore()
    userStore.setUserData({
      id: 'user-1',
      org_id: 'org-123',
      org_role: 'admin'
    })

    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('Manage Workspace')
  })

  it('should hide Manage button for members', async () => {
    const wrapper = mount(UserSettings, {
      global: {
        plugins: [vuetify]
      }
    })

    const userStore = useUserStore()
    userStore.setUserData({
      id: 'user-1',
      org_id: 'org-123',
      org_role: 'member'
    })

    await wrapper.vm.$nextTick()

    expect(wrapper.text()).not.toContain('Manage Workspace')
  })
})
```

**Run Tests (should FAIL):**
```powershell
cd frontend; npm run test:unit -- AppBar.spec.js UserSettings.spec.js
```

---

### 🟢 GREEN PHASE: Make Tests Pass

**1. Update AppBar Component**

Edit: `frontend/src/components/navigation/AppBar.vue`

```vue
<template>
  <v-app-bar color="primary" dark app>
    <v-app-bar-title>GiljoAI MCP</v-app-bar-title>

    <v-spacer />

    <v-menu v-if="userStore.isAuthenticated" offset-y>
      <template v-slot:activator="{ props }">
        <v-btn v-bind="props" text>
          <v-icon left>mdi-account-circle</v-icon>
          {{ userStore.username }}
        </v-btn>
      </template>

      <v-list>
        <!-- User Info Section -->
        <v-list-item>
          <v-list-item-title class="text-h6">
            {{ userStore.username }}
          </v-list-item-title>
          <v-list-item-subtitle v-if="userStore.currentOrg">
            {{ userStore.currentOrg.name }}
          </v-list-item-subtitle>
        </v-list-item>

        <!-- Role Badge -->
        <v-list-item v-if="userStore.orgRole">
          <v-chip
            :color="getRoleBadgeColor(userStore.orgRole)"
            size="small"
            class="mt-1"
          >
            {{ getRoleLabel(userStore.orgRole) }}
          </v-chip>
        </v-list-item>

        <v-divider />

        <!-- My Workspace Link -->
        <v-list-item
          v-if="userStore.currentOrg"
          @click="navigateToWorkspace"
        >
          <template v-slot:prepend>
            <v-icon>mdi-office-building</v-icon>
          </template>
          <v-list-item-title>My Workspace</v-list-item-title>
        </v-list-item>

        <!-- User Settings -->
        <v-list-item @click="navigateToSettings">
          <template v-slot:prepend>
            <v-icon>mdi-cog</v-icon>
          </template>
          <v-list-item-title>User Settings</v-list-item-title>
        </v-list-item>

        <v-divider />

        <!-- Logout -->
        <v-list-item @click="logout">
          <template v-slot:prepend>
            <v-icon>mdi-logout</v-icon>
          </template>
          <v-list-item-title>Logout</v-list-item-title>
        </v-list-item>
      </v-list>
    </v-menu>
  </v-app-bar>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

function getRoleBadgeColor(role) {
  const colors = {
    owner: 'purple',
    admin: 'blue',
    member: 'green',
    viewer: 'grey'
  }
  return colors[role] || 'grey'
}

function getRoleLabel(role) {
  const labels = {
    owner: 'Owner',
    admin: 'Admin',
    member: 'Member',
    viewer: 'Viewer'
  }
  return labels[role] || role
}

function navigateToWorkspace() {
  if (userStore.currentOrg) {
    router.push(`/organizations/${userStore.currentOrg.id}/settings`)
  }
}

function navigateToSettings() {
  router.push('/settings')
}

function logout() {
  userStore.clearUser()
  router.push('/login')
}
</script>
```

**2. Update UserSettings Component**

Edit: `frontend/src/views/UserSettings.vue`

```vue
<template>
  <v-container>
    <v-card>
      <v-card-title>User Settings</v-card-title>

      <v-tabs v-model="activeTab">
        <v-tab value="profile">Profile</v-tab>
        <v-tab value="workspace">Workspace</v-tab>
        <v-tab value="context">Context</v-tab>
      </v-tabs>

      <v-card-text>
        <v-window v-model="activeTab">
          <!-- Profile Tab -->
          <v-window-item value="profile">
            <h3 class="mb-4">Profile Settings</h3>
            <!-- Existing profile settings -->
          </v-window-item>

          <!-- Workspace Tab -->
          <v-window-item value="workspace">
            <h3 class="mb-4">Workspace</h3>

            <v-alert
              v-if="!userStore.currentOrg"
              type="info"
              class="mb-4"
            >
              You are not part of any workspace.
            </v-alert>

            <div v-else>
              <!-- Workspace Name -->
              <v-text-field
                v-model="workspaceName"
                label="Workspace Name"
                :readonly="!canEditWorkspace"
                variant="outlined"
                class="mb-4"
              >
                <template v-slot:append v-if="canEditWorkspace">
                  <v-btn
                    icon="mdi-content-save"
                    color="primary"
                    :loading="savingName"
                    @click="saveWorkspaceName"
                  />
                </template>
              </v-text-field>

              <!-- Role Badge -->
              <v-list-item class="px-0 mb-4">
                <v-list-item-title>Your Role</v-list-item-title>
                <template v-slot:append>
                  <v-chip
                    :color="getRoleBadgeColor(userStore.orgRole)"
                    size="small"
                  >
                    {{ getRoleLabel(userStore.orgRole) }}
                  </v-chip>
                </template>
              </v-list-item>

              <!-- Member Count -->
              <v-list-item class="px-0 mb-4">
                <v-list-item-title>Members</v-list-item-title>
                <template v-slot:append>
                  <v-chip size="small">
                    {{ memberCount }} {{ memberCount === 1 ? 'member' : 'members' }}
                  </v-chip>
                </template>
              </v-list-item>

              <!-- Manage Workspace Button -->
              <v-btn
                v-if="userStore.isOrgAdmin"
                color="primary"
                @click="navigateToWorkspaceSettings"
                block
                class="mt-4"
              >
                Manage Workspace
              </v-btn>
            </div>
          </v-window-item>

          <!-- Context Tab -->
          <v-window-item value="context">
            <h3 class="mb-4">Context Settings</h3>
            <!-- Existing context settings -->
          </v-window-item>
        </v-window>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import api from '@/services/api'

const router = useRouter()
const userStore = useUserStore()

const activeTab = ref('profile')
const workspaceName = ref('')
const savingName = ref(false)
const memberCount = ref(0)

const canEditWorkspace = computed(() => {
  return userStore.isOrgAdmin
})

function getRoleBadgeColor(role) {
  const colors = {
    owner: 'purple',
    admin: 'blue',
    member: 'green',
    viewer: 'grey'
  }
  return colors[role] || 'grey'
}

function getRoleLabel(role) {
  const labels = {
    owner: 'Owner',
    admin: 'Admin',
    member: 'Member',
    viewer: 'Viewer'
  }
  return labels[role] || role
}

async function saveWorkspaceName() {
  savingName.value = true
  try {
    await api.patch(`/organizations/${userStore.currentOrg.id}`, {
      name: workspaceName.value
    })

    // Update user store
    const meResponse = await api.get('/auth/me')
    userStore.setUserData(meResponse.data)

    alert('Workspace name updated successfully')
  } catch (error) {
    console.error('Failed to update workspace name:', error)
    alert('Failed to update workspace name')
  } finally {
    savingName.value = false
  }
}

function navigateToWorkspaceSettings() {
  router.push(`/organizations/${userStore.currentOrg.id}/settings`)
}

async function loadMemberCount() {
  if (!userStore.currentOrg) return

  try {
    const response = await api.get(`/organizations/${userStore.currentOrg.id}/members`)
    memberCount.value = response.data.length
  } catch (error) {
    console.error('Failed to load member count:', error)
  }
}

onMounted(() => {
  if (userStore.currentOrg) {
    workspaceName.value = userStore.currentOrg.name
    loadMemberCount()
  }
})
</script>
```

**Run Tests (should PASS):**
```powershell
cd frontend; npm run test:unit -- AppBar.spec.js UserSettings.spec.js
```

---

### 🔵 REFACTOR PHASE: Optimize & Document

**1. Extract Role Badge Component**

Create: `frontend/src/components/common/RoleBadge.vue`

```vue
<template>
  <v-chip :color="color" :size="size">
    {{ label }}
  </v-chip>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  role: {
    type: String,
    required: true
  },
  size: {
    type: String,
    default: 'small'
  }
})

const color = computed(() => {
  const colors = {
    owner: 'purple',
    admin: 'blue',
    member: 'green',
    viewer: 'grey'
  }
  return colors[props.role] || 'grey'
})

const label = computed(() => {
  const labels = {
    owner: 'Owner',
    admin: 'Admin',
    member: 'Member',
    viewer: 'Viewer'
  }
  return labels[props.role] || props.role
})
</script>
```

**2. Update Components to Use RoleBadge**

Refactor AppBar and UserSettings to use shared RoleBadge component.

**3. Add Component Documentation**

Create: `docs/components/RoleBadge.md`

```markdown
# RoleBadge Component

Display user role with color-coded badge.

## Props

- `role` (String, required): Role name (owner/admin/member/viewer)
- `size` (String, default: 'small'): Badge size

## Usage

```vue
<RoleBadge role="owner" />
<RoleBadge role="admin" size="default" />
```

## Colors

- Owner: Purple
- Admin: Blue
- Member: Green
- Viewer: Grey
```

**Run All Tests:**
```powershell
cd frontend; npm run test:unit
```

---

## Success Criteria

**AppBar:**
- ✅ Shows workspace name under username
- ✅ Shows role badge (owner/admin/member/viewer)
- ✅ Shows "My Workspace" menu link
- ✅ Links to OrganizationSettings page
- ✅ Hides workspace info when user has no org

**UserSettings:**
- ✅ Has "Workspace" tab
- ✅ Shows workspace name (editable for owner/admin)
- ✅ Shows role badge
- ✅ Shows member count
- ✅ Shows "Manage Workspace" button for admins
- ✅ Hides manage button for members/viewers

**Testing:**
- ✅ All AppBar tests pass (5/5)
- ✅ All UserSettings tests pass (6/6)
- ✅ RoleBadge component tested

---

## Chain Execution Instructions

**CRITICAL: This handover is part of the 0424 chain. You MUST update chain_log.json.**

### Step 1: Read Chain Context

```powershell
cat prompts/0424_chain/chain_log.json
```

Verify 0424h is complete.

### Step 2: Mark Session In Progress

Update `prompts/0424_chain/chain_log.json`:

```json
{
  "sessions": [
    {
      "session_id": "0424i",
      "title": "AppBar + User Settings",
      "color": "#FF9800",
      "status": "in_progress",
      "started_at": "2026-01-31T<current-time>",
      "completed_at": null,
      "planned_tasks": [
        "Update AppBar to show workspace name and role",
        "Add 'My Workspace' menu link to AppBar",
        "Add 'Workspace' tab to UserSettings",
        "Add workspace name edit for admins",
        "Add member count display",
        "Write AppBar and UserSettings tests"
      ],
      "tasks_completed": [],
      "deviations": [],
      "blockers_encountered": [],
      "notes_for_next": null,
      "summary": null
    }
  ]
}
```

### Step 3: Execute Handover

Follow RED → GREEN → REFACTOR phases.

**CRITICAL: Use Subagents**

```javascript
Task.create({
  agent: 'frontend-tester',
  instruction: 'Implement AppBar and UserSettings org integration per 0424i GREEN phase. Update AppBar to show workspace name and role badge. Add Workspace tab to UserSettings. Run tests until green.'
})

Task.create({
  agent: 'ux-designer',
  instruction: 'Review AppBar and UserSettings org UI per 0424i. Verify workspace info is visible, role badges use appropriate colors, and layout is clean. Test navigation flows.'
})
```

### Step 4: Update Chain Log

After all tests pass:

```json
{
  "sessions": [
    {
      "session_id": "0424i",
      "title": "AppBar + User Settings",
      "color": "#FF9800",
      "status": "complete",
      "started_at": "2026-01-31T<start-time>",
      "completed_at": "2026-01-31T<end-time>",
      "planned_tasks": [
        "Update AppBar to show workspace name and role",
        "Add 'My Workspace' menu link to AppBar",
        "Add 'Workspace' tab to UserSettings",
        "Add workspace name edit for admins",
        "Add member count display",
        "Write AppBar and UserSettings tests"
      ],
      "tasks_completed": [
        "Updated AppBar to show workspace name under username",
        "Added role badge to AppBar (owner/admin/member/viewer)",
        "Added 'My Workspace' menu link to AppBar",
        "Added 'Workspace' tab to UserSettings",
        "Added workspace name edit for owner/admin",
        "Added role badge and member count display",
        "Added 'Manage Workspace' button for admins",
        "Created RoleBadge component for consistency",
        "Wrote 11 frontend tests - all passing"
      ],
      "deviations": [
        "Created RoleBadge component for DRY (not in original plan)"
      ],
      "blockers_encountered": [],
      "notes_for_next": "UI integration complete. Migration script needs to populate User.org_id from OrgMembership (0424j). After migration, change org_id to NOT NULL (0424j).",
      "summary": "Successfully integrated workspace into AppBar and UserSettings. Workspace name and role visible throughout app. All 11 tests passing."
    }
  ]
}
```

### Step 5: Commit Your Work

```powershell
git add .
git commit -m "feat(0424i): Integrate workspace into AppBar and UserSettings

- Update AppBar to show workspace name and role badge
- Add 'My Workspace' menu link to AppBar
- Add 'Workspace' tab to UserSettings
- Add workspace name edit for owner/admin
- Add member count display and 'Manage Workspace' button
- Create RoleBadge component for consistency
- Add 11 frontend tests - all passing

Handover: 0424i
Chain: 0424 Organization Hierarchy
Tests: 11/11 passing

BREAKING: Workspace name and role now visible in AppBar.
Terminology changed from 'Organization' to 'Workspace' in UI."
```

### Step 6: Spawn Next Terminal

**⚠️ WARNING: Check for duplicate terminals before spawning!**

```powershell
# Check for existing 0424j terminal
Get-Process powershell | Select-Object MainWindowTitle | Select-String "0424j"
```

If NOT spawned yet:

```powershell
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd F:\GiljoAI_MCP; Write-Host 'Handover 0424j: Migration + NOT NULL Constraint (FINAL)' -ForegroundColor Cyan; Write-Host 'Spawned from: 0424i (AppBar + User Settings)' -ForegroundColor Gray; Write-Host ''; cat handovers/0424j_migration_finalization.md"
```

---

## Critical Subagent Instructions

**YOU MUST USE THE TASK TOOL TO SPAWN SUBAGENTS.**

```javascript
Task.create({
  agent: 'frontend-tester',
  instruction: `Implement AppBar and UserSettings per handover 0424i:

1. Update frontend/src/components/navigation/AppBar.vue:
   - Show workspace name under username
   - Add role badge (owner/admin/member/viewer)
   - Add 'My Workspace' menu link

2. Update frontend/src/views/UserSettings.vue:
   - Add 'Workspace' tab
   - Show workspace name (editable for admins)
   - Add role badge and member count
   - Add 'Manage Workspace' button

3. Run tests:
   cd frontend; npm run test:unit -- AppBar.spec.js UserSettings.spec.js

Follow RED → GREEN → REFACTOR from handover.`
})
```

---

## Dependencies

**Requires:**
- User store org state (0424h)
- OrganizationSettings page (0424d)

**Provides:**
- Workspace visibility throughout UI
- Role-based UI permissions
- Quick workspace navigation

---

## Notes

**Design Decisions:**
- "Workspace" terminology more user-friendly than "Organization"
- Role badge uses color coding (purple=owner, blue=admin, green=member)
- Workspace name editable in both Settings and dedicated org page
- Member count fetched on mount (not reactive for performance)

**Testing Strategy:**
- Component tests verify UI elements and computed properties
- Navigation tests verify routing to workspace settings
- Permission tests verify admin-only features hidden for members

**Future Work (0424j):**
- Migration populates User.org_id from OrgMembership
- Verify all users have org_id set
- Change User.org_id to NOT NULL

---

## Chain Execution Instructions

### Step 1: Read Chain Log
Read `prompts/0424_chain/chain_log.json` and check 0424h status is "complete".

### Step 2: Mark Session Started
Update your session entry: `"status": "in_progress", "started_at": "<timestamp>"`

### Step 3: Execute Handover Tasks
Complete all implementation phases above using Task tool subagents.

### Step 4: Commit Your Work
```bash
git add -A && git commit -m "feat(0424i): Integrate workspace into AppBar and UserSettings

- Update AppBar to show workspace name and role badge
- Add 'My Workspace' menu link to AppBar
- Add 'Workspace' tab to UserSettings
- Add workspace name edit for owner/admin
- Create RoleBadge component for consistency

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

### Step 5: Update Chain Log
Update `prompts/0424_chain/chain_log.json`:
- Set your session status to "complete"
- Fill in tasks_completed, deviations, blockers_encountered
- Add notes_for_next for 0424j
- Add summary

### Step 6: Spawn Next Terminal

**CRITICAL: DO NOT SPAWN DUPLICATE TERMINALS!**
- Only ONE agent should spawn the next terminal
- If your subagent already spawned it, DO NOT spawn again
- Check if terminal 0424j is already running before executing

**Use Bash tool to EXECUTE this command:**
```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0424j - Migration Finalization\" --tabColor \"#F44336\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0424j. READ: F:\GiljoAI_MCP\handovers\0424j_migration_finalization.md - Finalize migration and make org_id NOT NULL. Use Task subagents. FINAL HANDOVER - do not spawn more terminals.\"' -Verb RunAs"
```

---

**Next Handover:** 0424j (Migration + NOT NULL Constraint - FINAL)
