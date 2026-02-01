# Handover 0424h: API Layer + Welcome Screen

**Status:** 🟢 Ready for Execution
**Color:** `#9C27B0` (Purple - API + Frontend)
**Prerequisites:** 0424g (AuthService Update)
**Spawns:** 0424i (AppBar + User Settings Integration)
**Chain:** 0424 Organization Hierarchy Series

---

## Overview

Update API endpoints and welcome screen to support org-first flow with workspace name capture during fresh install.

**Architecture Change:**
- `/api/auth/first-login` accepts `workspace_name` parameter
- `/api/auth/me` returns `org_id`, `org_name`, `org_role`
- `/api/users` (POST) uses `create_user_in_org()` method
- Welcome screen adds "Workspace Name" field (required)
- User store provides org computed properties

**What This Accomplishes:**
- Fresh install captures custom workspace name during admin creation
- Auth endpoint provides org context to all components
- User creation by admins inherits org_id
- User store becomes single source of truth for org context

**Impact:**
- UI can display workspace name and role throughout application
- Admin user creation flows through org-aware service method
- Foundation for AppBar and Settings integration (0424i)

---

## Prerequisites

**Required Handovers:**
- ✅ 0424g: AuthService org-first flow

**Verify Before Starting:**
```powershell
# Check AuthService has org methods
cat api/services/auth_service.py | grep "create_user_in_org"
cat api/services/auth_service.py | grep "_create_first_admin_impl"

# Check auth endpoints exist
cat api/endpoints/auth.py | grep "/first-login"
cat api/endpoints/auth.py | grep "/me"

# Check welcome screen exists
cat frontend/src/views/CreateAdminAccount.vue | grep "CreateAdminAccount"
```

---

## Implementation Phases

### 🔴 RED PHASE: Failing Tests

**1. Backend Tests - API Returns Org Data**

Create: `tests/api/test_auth_org_endpoints.py`

```python
"""
Tests for auth endpoints returning org data.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from src.giljo_mcp.models import User, Organization


@pytest.mark.asyncio
async def test_first_login_accepts_workspace_name(client: AsyncClient, db_session):
    """Test /auth/first-login accepts workspace_name parameter."""
    response = await client.post(
        "/api/auth/first-login",
        json={
            "username": "admin",
            "password": "GiljoMCP",
            "email": "admin@example.com",
            "workspace_name": "My Custom Workspace"
        }
    )

    assert response.status_code == 201
    data = response.json()

    # Load user
    user = await db_session.get(User, data["user"]["id"])

    # Load org
    org = await db_session.get(Organization, user.org_id)

    # Assert workspace name was used
    assert org.name == "My Custom Workspace"


@pytest.mark.asyncio
async def test_first_login_defaults_workspace_name(client: AsyncClient, db_session):
    """Test /auth/first-login defaults to 'My Organization' if not provided."""
    response = await client.post(
        "/api/auth/first-login",
        json={
            "username": "admin",
            "password": "GiljoMCP",
            "email": "admin@example.com"
            # No workspace_name
        }
    )

    assert response.status_code == 201
    data = response.json()

    # Load user and org
    user = await db_session.get(User, data["user"]["id"])
    org = await db_session.get(Organization, user.org_id)

    # Assert default name
    assert org.name == "My Organization"


@pytest.mark.asyncio
async def test_auth_me_returns_org_data(client: AsyncClient, test_user_with_org, auth_headers):
    """Test /auth/me returns org_id, org_name, org_role."""
    user, org, membership = test_user_with_org

    response = await client.get("/api/auth/me", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    # Assert org fields
    assert data["org_id"] == str(org.id)
    assert data["org_name"] == org.name
    assert data["org_role"] == membership.role


@pytest.mark.asyncio
async def test_auth_me_without_org(client: AsyncClient, test_user, auth_headers):
    """Test /auth/me returns null for org fields when user has no org."""
    response = await client.get("/api/auth/me", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    # Assert org fields are null
    assert data["org_id"] is None
    assert data["org_name"] is None
    assert data["org_role"] is None


@pytest.mark.asyncio
async def test_create_user_sets_org_id(client: AsyncClient, db_session, test_admin_user, auth_headers):
    """Test POST /users creates user in admin's org."""
    response = await client.post(
        "/api/users",
        headers=auth_headers,
        json={
            "username": "newuser",
            "email": "newuser@example.com",
            "role": "member",
            "initial_password": "temp123"
        }
    )

    assert response.status_code == 201
    data = response.json()

    # Load new user
    new_user = await db_session.get(User, data["id"])

    # Assert org_id matches admin
    assert new_user.org_id == test_admin_user.org_id

    # Assert response includes org fields
    assert data["org_id"] == str(test_admin_user.org_id)
    assert data["org_name"] is not None
```

**2. Frontend Tests - User Store Org Properties**

Create: `frontend/tests/unit/stores/user.spec.js`

```javascript
import { setActivePinia, createPinia } from 'pinia'
import { useUserStore } from '@/stores/user'
import { describe, it, expect, beforeEach } from 'vitest'

describe('User Store - Org Integration', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('should store org data from auth response', () => {
    const store = useUserStore()

    store.setUserData({
      id: 'user-1',
      username: 'testuser',
      org_id: 'org-123',
      org_name: 'Test Org',
      org_role: 'admin'
    })

    expect(store.orgId).toBe('org-123')
    expect(store.orgName).toBe('Test Org')
    expect(store.orgRole).toBe('admin')
  })

  it('should provide currentOrg computed property', () => {
    const store = useUserStore()

    store.setUserData({
      id: 'user-1',
      org_id: 'org-123',
      org_name: 'Test Org',
      org_role: 'member'
    })

    const currentOrg = store.currentOrg
    expect(currentOrg).toEqual({
      id: 'org-123',
      name: 'Test Org',
      role: 'member'
    })
  })

  it('should provide isOrgAdmin computed property', () => {
    const store = useUserStore()

    // Admin role
    store.setUserData({ id: 'user-1', org_role: 'admin' })
    expect(store.isOrgAdmin).toBe(true)

    // Owner role
    store.setUserData({ id: 'user-1', org_role: 'owner' })
    expect(store.isOrgAdmin).toBe(true)

    // Member role
    store.setUserData({ id: 'user-1', org_role: 'member' })
    expect(store.isOrgAdmin).toBe(false)
  })

  it('should provide isOrgOwner computed property', () => {
    const store = useUserStore()

    store.setUserData({ id: 'user-1', org_role: 'owner' })
    expect(store.isOrgOwner).toBe(true)

    store.setUserData({ id: 'user-1', org_role: 'admin' })
    expect(store.isOrgOwner).toBe(false)
  })

  it('should handle missing org data', () => {
    const store = useUserStore()

    store.setUserData({ id: 'user-1', username: 'test' })

    expect(store.currentOrg).toBeNull()
    expect(store.isOrgAdmin).toBe(false)
    expect(store.isOrgOwner).toBe(false)
  })
})
```

**Run Tests (should FAIL):**
```powershell
pytest tests/api/test_auth_org_endpoints.py -v
cd frontend; npm run test:unit -- user.spec.js
```

---

### 🟢 GREEN PHASE: Make Tests Pass

**1. Update Auth Endpoint - /auth/first-login**

Edit: `api/endpoints/auth.py`

Find the `/first-login` endpoint and add `workspace_name` parameter:

```python
from pydantic import BaseModel, Field

class FirstLoginRequest(BaseModel):
    """Request model for first-login endpoint."""
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=8)
    email: str = Field(..., pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    workspace_name: str = Field(default="My Organization", min_length=1, max_length=255)


@router.post("/first-login", response_model=dict, status_code=201)
async def first_login(
    request: FirstLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Create first admin user with workspace (fresh install).

    Handover 0424g/h: Org-first flow with custom workspace name.
    """
    # Check if any users exist
    from src.giljo_mcp.models import User
    from sqlalchemy import select

    result = await db.execute(select(User).limit(1))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Users already exist")

    # Create first admin with workspace
    user = await AuthService._create_first_admin_impl(
        db=db,
        username=request.username,
        password=request.password,
        email=request.email,
        org_name=request.workspace_name  # Pass workspace name
    )

    return {
        "message": "First admin created successfully",
        "user": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email
        }
    }
```

**2. Update Auth Endpoint - /auth/me**

Edit: `api/endpoints/auth.py`

Modify `/auth/me` to return org fields:

```python
@router.get("/me", response_model=dict)
async def get_current_user(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user profile with org data.

    Handover 0424h: Returns org_id, org_name, org_role.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    # Load user with org and membership
    stmt = (
        select(User)
        .options(
            selectinload(User.organization),
            selectinload(User.org_memberships)
        )
        .where(User.id == current_user.id)
    )
    result = await db.execute(stmt)
    user = result.scalar_one()

    # Get org data
    org_id = None
    org_name = None
    org_role = None

    if user.organization:
        org_id = str(user.organization.id)
        org_name = user.organization.name

    if user.org_memberships:
        org_role = user.org_memberships[0].role

    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "tenant_key": user.tenant_key,
        "role": user.role,
        "org_id": org_id,
        "org_name": org_name,
        "org_role": org_role
    }
```

**3. Update Users Endpoint - POST /users**

Edit: `api/endpoints/users.py`

```python
from pydantic import BaseModel, Field

class CreateUserRequest(BaseModel):
    """Request model for creating user."""
    username: str = Field(..., min_length=3, max_length=64)
    email: str = Field(..., pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    role: str = Field(..., pattern="^(owner|admin|member|viewer)$")
    initial_password: str = Field(..., min_length=8)


@router.post("", response_model=dict, status_code=201)
async def create_user(
    request: CreateUserRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Admin creates new user in their organization.

    Handover 0424h: Uses create_user_in_org service method.
    """
    # Create user in admin's org
    new_user = await AuthService.create_user_in_org(
        db=db,
        admin_user_id=current_user.id,
        username=request.username,
        email=request.email,
        role=request.role,
        initial_password=request.initial_password
    )

    # Load org for response
    await db.refresh(new_user, ["organization"])

    return {
        "id": str(new_user.id),
        "username": new_user.username,
        "email": new_user.email,
        "role": request.role,
        "org_id": str(new_user.org_id),
        "org_name": new_user.organization.name if new_user.organization else None
    }
```

**4. Update Frontend - User Store**

Edit: `frontend/src/stores/user.js`

```javascript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useUserStore = defineStore('user', () => {
  // Existing state
  const id = ref(null)
  const username = ref(null)
  const email = ref(null)
  const tenantKey = ref(null)
  const role = ref(null)

  // Org state (Handover 0424h)
  const orgId = ref(null)
  const orgName = ref(null)
  const orgRole = ref(null)

  // Computed
  const isAuthenticated = computed(() => !!id.value)

  const currentOrg = computed(() => {
    if (!orgId.value) return null
    return {
      id: orgId.value,
      name: orgName.value,
      role: orgRole.value
    }
  })

  const isOrgAdmin = computed(() => {
    return orgRole.value === 'admin' || orgRole.value === 'owner'
  })

  const isOrgOwner = computed(() => {
    return orgRole.value === 'owner'
  })

  // Actions
  function setUserData(userData) {
    id.value = userData.id
    username.value = userData.username
    email.value = userData.email
    tenantKey.value = userData.tenant_key
    role.value = userData.role

    // Org fields
    orgId.value = userData.org_id || null
    orgName.value = userData.org_name || null
    orgRole.value = userData.org_role || null
  }

  function clearUser() {
    id.value = null
    username.value = null
    email.value = null
    tenantKey.value = null
    role.value = null
    orgId.value = null
    orgName.value = null
    orgRole.value = null
  }

  return {
    // State
    id,
    username,
    email,
    tenantKey,
    role,
    orgId,
    orgName,
    orgRole,

    // Computed
    isAuthenticated,
    currentOrg,
    isOrgAdmin,
    isOrgOwner,

    // Actions
    setUserData,
    clearUser
  }
})
```

**5. Update Frontend - Welcome Screen**

Edit: `frontend/src/views/CreateAdminAccount.vue`

Add "Workspace Name" field:

```vue
<template>
  <v-container>
    <v-card max-width="600" class="mx-auto mt-8">
      <v-card-title>Create Admin Account</v-card-title>
      <v-card-text>
        <v-form ref="form" v-model="valid" @submit.prevent="createAdmin">
          <!-- Workspace Name Field -->
          <v-text-field
            v-model="formData.workspaceName"
            label="Workspace Name"
            hint="Name for your organization (e.g., 'Acme Corp', 'My Team')"
            :rules="[rules.required, rules.minLength(1), rules.maxLength(255)]"
            variant="outlined"
            class="mb-4"
            required
          />

          <!-- Existing fields -->
          <v-text-field
            v-model="formData.username"
            label="Username"
            :rules="[rules.required, rules.minLength(3)]"
            variant="outlined"
            class="mb-4"
            required
          />

          <v-text-field
            v-model="formData.email"
            label="Email"
            type="email"
            :rules="[rules.required, rules.email]"
            variant="outlined"
            class="mb-4"
            required
          />

          <v-text-field
            v-model="formData.password"
            label="Password"
            type="password"
            :rules="[rules.required, rules.minLength(8)]"
            variant="outlined"
            class="mb-4"
            required
          />

          <v-text-field
            v-model="formData.confirmPassword"
            label="Confirm Password"
            type="password"
            :rules="[rules.required, rules.passwordMatch]"
            variant="outlined"
            class="mb-4"
            required
          />

          <v-btn
            type="submit"
            color="primary"
            :loading="loading"
            :disabled="!valid"
            block
          >
            Create Admin Account
          </v-btn>
        </v-form>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import api from '@/services/api'

const router = useRouter()
const userStore = useUserStore()

const valid = ref(false)
const loading = ref(false)

const formData = reactive({
  workspaceName: '',
  username: '',
  email: '',
  password: '',
  confirmPassword: ''
})

const rules = {
  required: v => !!v || 'Required',
  minLength: min => v => (v && v.length >= min) || `Minimum ${min} characters`,
  maxLength: max => v => (v && v.length <= max) || `Maximum ${max} characters`,
  email: v => /.+@.+\..+/.test(v) || 'Invalid email',
  passwordMatch: v => v === formData.password || 'Passwords do not match'
}

async function createAdmin() {
  loading.value = true
  try {
    const response = await api.post('/auth/first-login', {
      workspace_name: formData.workspaceName,
      username: formData.username,
      email: formData.email,
      password: formData.password
    })

    // Auto-login after creation
    const loginResponse = await api.post('/auth/login', {
      username: formData.username,
      password: formData.password
    })

    userStore.setUserData(loginResponse.data.user)
    router.push('/dashboard')
  } catch (error) {
    console.error('Admin creation failed:', error)
    alert('Failed to create admin account')
  } finally {
    loading.value = false
  }
}
</script>
```

**Run Tests (should PASS):**
```powershell
pytest tests/api/test_auth_org_endpoints.py -v
cd frontend; npm run test:unit -- user.spec.js
```

---

### 🔵 REFACTOR PHASE: Optimize & Document

**1. Add Response Models**

Create Pydantic response models for consistent API responses.

**2. Add Frontend Component Tests**

Create `frontend/tests/unit/views/CreateAdminAccount.spec.js` for welcome screen.

**3. Update API Documentation**

Document new `workspace_name` parameter and org response fields.

**Run All Tests:**
```powershell
pytest tests/api/test_auth_org_endpoints.py -v --cov=api/endpoints/auth --cov-report=term-missing
cd frontend; npm run test:unit
```

---

## Success Criteria

**Backend:**
- ✅ `/auth/first-login` accepts `workspace_name` parameter
- ✅ `/auth/first-login` defaults to "My Organization" if not provided
- ✅ `/auth/me` returns `org_id`, `org_name`, `org_role`
- ✅ `POST /users` uses `create_user_in_org()` and returns org fields
- ✅ All 5 API tests pass

**Frontend:**
- ✅ Welcome screen has "Workspace Name" field (required)
- ✅ User store has org state and computed properties
- ✅ `setUserData()` populates org fields from API response
- ✅ All frontend tests pass

**Integration:**
- ✅ Fresh install captures custom workspace name
- ✅ Auth flow populates user store with org data
- ✅ Org context available to all components

---

## Chain Execution Instructions

**CRITICAL: This handover is part of the 0424 chain. You MUST update chain_log.json.**

### Step 1: Read Chain Context

```powershell
cat prompts/0424_chain/chain_log.json
```

Verify 0424g is complete.

### Step 2: Mark Session In Progress

Update `prompts/0424_chain/chain_log.json`:

```json
{
  "sessions": [
    {
      "session_id": "0424h",
      "title": "API + Welcome Screen",
      "color": "#9C27B0",
      "status": "in_progress",
      "started_at": "2026-01-31T<current-time>",
      "completed_at": null,
      "planned_tasks": [
        "Update /auth/first-login to accept workspace_name",
        "Update /auth/me to return org fields",
        "Update POST /users to use create_user_in_org",
        "Add 'Workspace Name' field to welcome screen",
        "Update user store with org state",
        "Write 5 API tests + frontend tests"
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
  agent: 'tdd-implementor',
  instruction: 'Implement API org integration per 0424h GREEN phase. Update /auth/first-login, /auth/me, POST /users endpoints. Run tests until green.'
})

Task.create({
  agent: 'frontend-tester',
  instruction: 'Implement welcome screen and user store per 0424h GREEN phase. Add workspace name field, update user store with org state. Run tests until green.'
})
```

### Step 4: Update Chain Log

After all tests pass:

```json
{
  "sessions": [
    {
      "session_id": "0424h",
      "title": "API + Welcome Screen",
      "color": "#9C27B0",
      "status": "complete",
      "started_at": "2026-01-31T<start-time>",
      "completed_at": "2026-01-31T<end-time>",
      "planned_tasks": [
        "Update /auth/first-login to accept workspace_name",
        "Update /auth/me to return org fields",
        "Update POST /users to use create_user_in_org",
        "Add 'Workspace Name' field to welcome screen",
        "Update user store with org state",
        "Write 5 API tests + frontend tests"
      ],
      "tasks_completed": [
        "Updated /auth/first-login with workspace_name parameter",
        "Updated /auth/me to return org_id, org_name, org_role",
        "Updated POST /users to use create_user_in_org",
        "Added 'Workspace Name' field to CreateAdminAccount.vue",
        "Added org state to user store (orgId, orgName, orgRole)",
        "Added computed properties: currentOrg, isOrgAdmin, isOrgOwner",
        "Wrote 5 API tests + 5 frontend tests - all passing"
      ],
      "deviations": [],
      "blockers_encountered": [],
      "notes_for_next": "API and welcome screen complete. AppBar needs to show workspace name and role (0424i). User settings needs org tab (0424i).",
      "summary": "Successfully integrated org data into API and welcome screen. Fresh install captures workspace name, /auth/me provides org context. All 10 tests passing."
    }
  ]
}
```

### Step 5: Commit Your Work

```powershell
git add .
git commit -m "feat(0424h): Add org data to API endpoints and welcome screen

- Update /auth/first-login to accept workspace_name parameter
- Update /auth/me to return org_id, org_name, org_role
- Update POST /users to use create_user_in_org service
- Add 'Workspace Name' field to welcome screen (required)
- Add org state to user store with computed properties
- Add 5 API tests + 5 frontend tests
- All tests passing (10/10)

Handover: 0424h
Chain: 0424 Organization Hierarchy
Tests: 10/10 passing
Coverage: >80%

BREAKING: /auth/first-login now requires workspace_name parameter.
Fresh install flow captures custom workspace name during setup."
```

### Step 6: Spawn Next Terminal

**⚠️ WARNING: Check for duplicate terminals before spawning!**

```powershell
# Check for existing 0424i terminal
Get-Process powershell | Select-Object MainWindowTitle | Select-String "0424i"
```

If NOT spawned yet:

```powershell
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd F:\GiljoAI_MCP; Write-Host 'Handover 0424i: AppBar + User Settings Integration' -ForegroundColor Cyan; Write-Host 'Spawned from: 0424h (API + Welcome Screen)' -ForegroundColor Gray; Write-Host ''; cat handovers/0424i_appbar_user_settings.md"
```

---

## Critical Subagent Instructions

**YOU MUST USE THE TASK TOOL TO SPAWN SUBAGENTS.**

```javascript
Task.create({
  agent: 'tdd-implementor',
  instruction: `Implement API org integration per handover 0424h:

1. Update api/endpoints/auth.py:
   - /auth/first-login: accept workspace_name
   - /auth/me: return org_id, org_name, org_role

2. Update api/endpoints/users.py:
   - POST /users: use create_user_in_org

3. Run tests:
   pytest tests/api/test_auth_org_endpoints.py -v

Follow RED → GREEN → REFACTOR from handover.`
})

Task.create({
  agent: 'frontend-tester',
  instruction: `Implement welcome screen per handover 0424h:

1. Update frontend/src/views/CreateAdminAccount.vue:
   - Add 'Workspace Name' field (required)
   - Pass workspace_name to /auth/first-login

2. Update frontend/src/stores/user.js:
   - Add org state (orgId, orgName, orgRole)
   - Add computed: currentOrg, isOrgAdmin, isOrgOwner

3. Run tests:
   cd frontend; npm run test:unit -- user.spec.js

Follow GREEN phase from handover.`
})
```

---

## Dependencies

**Requires:**
- AuthService org methods (0424g)
- User.org_id column (0424f)

**Provides:**
- Workspace name capture (for fresh install)
- Org data in auth responses (for AppBar, Settings)
- User store org context (foundation for UI features)

---

## Notes

**Design Decisions:**
- `workspace_name` defaults to "My Organization" for backwards compatibility
- `/auth/me` returns org fields for all authenticated requests
- User store provides org context to all components

**Testing Strategy:**
- API tests verify endpoint parameters and responses
- Frontend tests verify form validation and store updates
- Integration tests verify full flow from UI to database

**Future Work (0424i):**
- AppBar shows workspace name and role badge
- User Settings has org tab with edit capabilities

---

## Chain Execution Instructions

### Step 1: Read Chain Log
Read `prompts/0424_chain/chain_log.json` and check 0424g status is "complete".

### Step 2: Mark Session Started
Update your session entry: `"status": "in_progress", "started_at": "<timestamp>"`

### Step 3: Execute Handover Tasks
Complete all implementation phases above using Task tool subagents.

### Step 4: Commit Your Work
```bash
git add -A && git commit -m "feat(0424h): Add org data to API endpoints and welcome screen

- Update /auth/first-login to accept workspace_name parameter
- Update /auth/me to return org_id, org_name, org_role
- Update POST /users to use create_user_in_org service
- Add 'Workspace Name' field to welcome screen (required)
- Add org state to user store with computed properties

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

### Step 5: Update Chain Log
Update `prompts/0424_chain/chain_log.json`:
- Set your session status to "complete"
- Fill in tasks_completed, deviations, blockers_encountered
- Add notes_for_next for 0424i
- Add summary

### Step 6: Spawn Next Terminal

**CRITICAL: DO NOT SPAWN DUPLICATE TERMINALS!**
- Only ONE agent should spawn the next terminal
- If your subagent already spawned it, DO NOT spawn again
- Check if terminal 0424i is already running before executing

**Use Bash tool to EXECUTE this command:**
```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0424i - AppBar + User Settings\" --tabColor \"#FF9800\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0424i. READ: F:\GiljoAI_MCP\handovers\0424i_appbar_user_settings.md - AppBar and UserSettings integration. Use Task subagents. Check chain_log.json. When complete: commit, update chain_log, spawn 0424j.\"' -Verb RunAs"
```

---

**Next Handover:** 0424i (AppBar + User Settings Integration)
