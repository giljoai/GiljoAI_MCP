# Handover 0078: Task Tenant & JWT Mismatch Diagnosis
<!-- Harmonized on 2025-11-04; postmortem captured in docs/devlog/2025-10-31_tenant_jwt_mismatch_postmortem.md -->

**Status**: 🔴 In Progress (ARCHIVED)
**Priority**: Critical
**Affected Systems**: Authentication, Task Management, Multi-Tenant Isolation
**Date Created**: 2025-10-31

---

## Problem Statement

Users experience task save failures with no visible errors. Tasks are created successfully (HTTP 200) but become invisible in the UI due to JWT token containing the wrong tenant key.

### Symptoms
1. ✅ Task creation succeeds (backend returns 200 OK)
2. ❌ Tasks created with `product_id: null` (should use active product)
3. ❌ Tasks invisible when "Product Tasks" filter is active
4. ❌ No frontend or backend errors logged

---

## Root Cause Analysis

### Discovery

**User**: `patrik` (ID: `0ab355aa-bd21-4874-9ad0-ddad63d57b1b`)
**Actual Tenant** (in database): `tk_eHuGt1LnLvWGxSnQURqvSjEhfluWNxD0`
**JWT Token Tenant** (in cookie): `tk_cyyOVf1HsbOCA8eFLEHoYUwiIIYhXjnd`

### Database Evidence

```sql
-- User record shows correct tenant
SELECT id, username, tenant_key FROM users WHERE username = 'patrik';
-- Result: tk_eHuGt1LnLvWGxSnQURqvSjEhfluWNxD0

-- Active product belongs to correct tenant
SELECT id, name, is_active, tenant_key FROM products WHERE is_active = true;
-- Result: TinyContacts, tk_eHuGt1LnLvWGxSnQURqvSjEhfluWNxD0

-- JWT token decoded from cookie shows WRONG tenant
-- JWT claim: "tenant_key": "tk_cyyOVf1HsbOCA8eFLEHoYUwiIIYhXjnd"
```

### Impact Chain

```
Wrong JWT Tenant
    ↓
Frontend queries products with wrong tenant filter
    ↓
No active product found (wrong tenant)
    ↓
productStore.currentProductId = null
    ↓
Task created with product_id: null
    ↓
Task invisible when "Product Tasks" filter active
```

---

## Task System Architecture (Reference)

### How Tasks Should Work

**Product Hierarchy**:
- **Product-scoped tasks**: When product active → task gets `product_id`
- **Unassigned tasks**: No active product → `product_id: null` → visible across ALL products
- **Conversion**: Unassigned tasks can be converted to projects under active product

**Creation Methods**:
1. **MCP Integration** (primary) - Real-time capture during coding sessions
2. **Dashboard UI** - Manual structured entry

**Task-to-Project Conversion**:
- Task name → Project title
- Task description → Project mission
- Constraint: Tasks cannot become products (only projects)

**States**: Active → Completed → Converted → Archived

### Expected Behavior

```javascript
// Frontend: TasksView.vue saveTask() function
if (productStore.currentProductId) {
  currentTask.value.product_id = productStore.currentProductId // Should be set!
}
await taskStore.createTask(currentTask.value)
```

**Problem**: `productStore.currentProductId` is null due to tenant mismatch

---

## Historical Context

From task documentation:
> "In the past when we had tenant ID's the application has used the generic tenant in yaml that gets created during installation, this is temporary, to get to set up an admin account, after that it should use the users tenant id that created the task."

**Hypothesis**: The auth system may still be using the default tenant from `config.yaml` instead of the user's actual tenant.

---

## Investigation Plan

### Phase 1: Authentication Flow Analysis
- [ ] Check JWT token generation in auth system (`src/giljo_mcp/auth/`)
- [ ] Verify tenant_key claim source during login
- [ ] Check for default tenant fallback usage
- [ ] Review middleware tenant assignment (`api/middleware.py:84`)

### Phase 2: Default Tenant Investigation
- [ ] Check `config.yaml` for default tenant configuration
- [ ] Search codebase for `DEFAULT_TENANT_KEY` references
- [ ] Verify if default tenant is still being used post-setup

### Phase 3: User Creation Flow
- [ ] Analyze first admin creation (`/api/auth/create-first-admin`)
- [ ] Check subsequent user creation tenant assignment
- [ ] Verify tenant propagation to JWT tokens

### Phase 4: Frontend State Management
- [ ] Verify `productStore` tenant filtering logic
- [ ] Check if frontend receives correct tenant from auth endpoint

---

## Affected Files (To Be Analyzed)

### Backend
- `src/giljo_mcp/auth/__init__.py` - Auth manager
- `src/giljo_mcp/auth_legacy.py` - Legacy auth (if still used)
- `api/endpoints/auth.py` - Login endpoint
- `api/middleware.py` - Tenant assignment (line 84)
- `config.yaml` - Default tenant configuration

### Frontend
- `frontend/src/stores/products.js` - Product store filtering
- `frontend/src/stores/user.js` - User/tenant state
- `frontend/src/views/TasksView.vue` - Task creation logic

---

## Investigation Results (COMPLETED)

### Issue #1: JWT Tenant Mismatch - ROOT CAUSE IDENTIFIED

**Type**: CRITICAL BUG - Multi-tenant isolation breach
**Cause**: Incompatible JWT token formats between two implementations

#### Explanation
The system has TWO separate JWT implementations using different payload structures:

1. **JWTManager** (src/giljo_mcp/auth/jwt_manager.py) - Used by login to CREATE tokens
   - Payload: `sub` (user UUID), `username`, `role`, `tenant_key`

2. **AuthManager** (src/giljo_mcp/auth_legacy.py) - Used by middleware to VERIFY tokens
   - Expects: `user_id`, `tenant_key`

#### The Bug Flow
```
Login → JWTManager creates token with "username" field
   ↓
Middleware → AuthManager validates token
   ↓
auth_legacy.py:433-434 looks for "user_id" field (DOESN'T EXIST)
   ↓
Returns None, database lookup fails (line 446)
   ↓
User not found, tenant_key never updated
   ↓
Default tenant fallback remains active
```

#### Code Locations
- **Token Creation**: api/endpoints/auth.py:333-335
- **Token Format**: src/giljo_mcp/auth/jwt_manager.py:121-128
- **Validation Bug**: src/giljo_mcp/auth_legacy.py:433-434, 446

#### Fix Required
File: `src/giljo_mcp/auth_legacy.py`
Lines: 433-434, 446

Change:
```python
# Line 433-434
"user": token_info.get("user_id"),  # WRONG
"user_id": token_info.get("user_id"),  # WRONG

# Line 446
select(User).where(User.username == token_info.get("user_id"))  # WRONG
```

To:
```python
# Line 433-434
"user": token_info.get("username"),  # CORRECT
"user_id": token_info.get("username"),  # CORRECT

# Line 446
select(User).where(User.username == token_info.get("username"))  # CORRECT
```

### Issue #2: Navigation Lock on /tasks Route - ROOT CAUSE IDENTIFIED

**Type**: HIGH SEVERITY - Missing function causes template rendering failure
**Cause**: Undefined `getUserName` function referenced in template

#### Explanation
TasksView.vue template line 321 calls `getUserName(item.created_by_user_id)` but the function is never defined in the component. This causes an uncaught exception during rendering, breaking the Vue Router navigation.

#### Why Direct URL Navigation Fails
1. Router starts navigating to /tasks
2. TasksView component mounts
3. Template attempts to render, calls undefined `getUserName`
4. Unhandled exception breaks component lifecycle
5. Router left in broken state
6. All subsequent navigation fails

#### Why Page Refresh Works
- Reinitializes Vue app completely
- Clears broken router state
- Same error occurs but router isn't permanently stuck

#### Code Locations
- **Missing function**: frontend/src/views/TasksView.vue:321 (template)
- **Should be defined**: frontend/src/views/TasksView.vue (script section, after line 960)

#### Fix Required
File: `frontend/src/views/TasksView.vue`

Add missing function in script section (after line 960):
```javascript
function getUserName(userId) {
  const user = userStore.users?.find(u => u.id === userId)
  return user ? user.username : 'Unknown'
}
```

Add error handling to onMounted (line 987-989):
```javascript
onMounted(async () => {
  try {
    await Promise.all([fetchTasks(), agentStore.fetchAgents()])
  } catch (error) {
    console.error('Failed to initialize TasksView:', error)
  }
})
```

---

## Fixes Applied

### Fix #1: JWT Tenant Mismatch ✅ COMPLETED
**File**: `src/giljo_mcp/auth_legacy.py`
**Lines Changed**: 433-434, 446

```python
# Changed from token_info.get("user_id") to token_info.get("username")
"user": token_info.get("username"),
"user_id": token_info.get("username"),
...
select(User).where(User.username == token_info.get("username"))
```

**Impact**: JWT tokens now correctly extract username field, enabling proper user lookup and tenant resolution.

### Fix #2: Missing getUserName Function ✅ COMPLETED
**File**: `frontend/src/views/TasksView.vue`
**Lines Added**: After line 960

Added missing function:
```javascript
function getUserName(userId) {
  if (!userId) return 'Unknown'
  if (userStore.currentUser?.id === userId) {
    return userStore.currentUser.username
  }
  return 'User'
}
```

Added error handling to onMounted (lines 994-1000):
```javascript
onMounted(async () => {
  try {
    await Promise.all([fetchTasks(), agentStore.fetchAgents()])
  } catch (error) {
    console.error('Failed to initialize TasksView:', error)
  }
})
```

**Impact**: Template rendering no longer fails, navigation lock resolved.

---

## Testing Required

### Test #1: Task Creation with Correct Tenant
1. **Log out and log back in** (refresh JWT token with fixed code)
2. Verify active product is loaded (should see TinyContacts)
3. Create a new task
4. **Expected**: Task created with `product_id: "46efaa26-de59-447d-bdba-e64c53593c58"`
5. **Expected**: Task visible in "Product Tasks" view
6. Verify in database:
   ```sql
   SELECT title, product_id, tenant_key FROM tasks ORDER BY created_at DESC LIMIT 1;
   ```

### Test #2: Navigation Lock Resolution
1. Navigate to different page (e.g., Dashboard)
2. Directly navigate to `http://10.1.0.164:7274/tasks` via URL bar
3. **Expected**: Page loads without errors
4. **Expected**: Navigation remains functional (can click other menu items)
5. **Expected**: No console errors

### Test #3: Multi-Tenant Isolation Validation
1. Check JWT token tenant matches user tenant
2. Verify tasks filtered by correct tenant
3. Confirm no cross-tenant data leakage

---

## Next Steps

1. ✅ **Completed**: Deep investigation by research agents
2. ✅ **Completed**: Apply JWT auth_legacy.py patch (3 line changes)
3. ✅ **Completed**: Add getUserName function to TasksView.vue
4. **Testing**: User to verify task creation with correct tenant
5. **Testing**: User to verify /tasks navigation no longer locks
6. **Validation**: Confirm multi-tenant isolation restored

---

## Success Criteria

- [ ] JWT tokens contain correct user tenant_key (no default fallback)
- [ ] Tasks created with active product's product_id
- [ ] Tasks visible after creation in "Product Tasks" view
- [ ] Multi-tenant isolation maintained
- [ ] No regression in authentication flow

---

## Related Handovers

- Handover 0050: Single Active Product Architecture
- Handover 0076: Task Assignment Field Removal
- Handover 0034: Fresh Install First Admin Creation

---

## Notes

**Important**: The default tenant (`tk_cyyOVf1HsbOCA8eFLEHoYUwiIIYhXjnd`) appears to be a fallback from initial installation. After first admin creation, all users should use their assigned tenant_key.

**Migration Path**: If this is a legacy issue, existing sessions may need to be invalidated to force re-login with correct tenant.
