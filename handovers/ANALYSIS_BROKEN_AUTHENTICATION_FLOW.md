# ANALYSIS: Broken Authentication Flow During Setup Wizard

**Date**: 2025-10-13
**Analyzed By**: Installation Flow Agent
**Related Handover**: HANDOVER_0013_SETUP_WIZARD_AUTHENTICATION_REDESIGN.md

---

## Executive Summary

The current setup wizard has a **critical authentication chain break** that leaves users in an unauthenticated state throughout the entire setup process, resulting in no WebSocket connection, "Disconnected" status, and a confusing UX where users never actually "log in" despite having credentials.

**Root Cause**: Password change endpoint returns JWT token, but user never logs in - they're redirected directly to setup wizard without authentication.

---

## 1. Current Broken Flow Diagram

```
FRESH INSTALL FLOW (BROKEN):
┌─────────────────────────────────────────────────────────────────────────────┐
│ install.py                                                                   │
│ • Creates database tables                                                    │
│ • Creates admin user (username: admin, password: admin, bcrypt hashed)      │
│ • Sets default_password_active: true in setup_state table                   │
│ • Starts API (port 7272) and Frontend (port 7274)                           │
│ • Opens browser to http://localhost:7274                                     │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Router Guard (router/index.js:196-300)                                       │
│ • Checks /api/setup/status                                                   │
│ • Sees: default_password_active: true                                        │
│ • FORCES redirect to /change-password                                        │
│ • NO authentication check at this stage                                      │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ ChangePassword.vue (/change-password) - UNAUTHENTICATED                     │
│ • User fills in form:                                                        │
│   - Current password: admin (hardcoded username, default password)           │
│   - New password: <strong password>                                          │
│   - Confirm password: <strong password>                                      │
│ • Submits form                                                               │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ POST /api/auth/change-password (auth.py:556-649)                            │
│ • Validates admin username                                                   │
│ • Verifies current password (admin)                                          │
│ • Hashes new password                                                        │
│ • Updates admin_user.password_hash                                           │
│ • Sets default_password_active: false in setup_state                         │
│ • Generates JWT token                                                        │
│ • Returns: { success: true, token: "jwt_token_here", user: {...} }          │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ ⚠️ AUTHENTICATION CHAIN BREAKS HERE ⚠️                                       │
│                                                                              │
│ ChangePassword.vue (line 320-334):                                          │
│ • Receives JWT token in response.data.token                                 │
│ • STORES token: localStorage.setItem('auth_token', response.data.token)     │
│ • STORES user: localStorage.setItem('user', JSON.stringify(response.data.user)) │
│ • BUT: User never actually "logged in" - no authentication state set         │
│ • NO cookie set (JWT token only in localStorage, not httpOnly cookie)       │
│ • Redirects to /setup WITHOUT establishing authentication                    │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Router Guard (router/index.js:196-300)                                       │
│ • Checks /api/setup/status again                                             │
│ • Sees: default_password_active: false (password changed)                    │
│ • Sees: database_initialized: false (not yet configured)                     │
│ • ALLOWS navigation to /setup                                                │
│ • NO authentication required (meta.requiresAuth: false)                      │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ SetupWizard.vue (/setup) - STILL UNAUTHENTICATED                            │
│ • User goes through 3-step wizard:                                           │
│   1. MCP Configuration (optional)                                            │
│   2. Serena Activation (optional)                                            │
│   3. Complete                                                                │
│ • ⚠️ PROBLEM: No JWT token sent to API (not in httpOnly cookie)             │
│ • ⚠️ PROBLEM: WebSocket connection fails (requires auth token)              │
│ • ⚠️ PROBLEM: ConnectionStatus shows "Disconnected" throughout              │
│ • ⚠️ PROBLEM: User confused - they changed password but aren't "logged in"  │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ POST /api/setup/complete (setup.py:341-651)                                 │
│ • Marks database_initialized: true                                           │
│ • Saves config.yaml                                                          │
│ • Redirects to dashboard (window.location.href = '...:7274')                │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ App.vue (mounted) - AUTHENTICATION CHECK FINALLY HAPPENS                     │
│ • Calls await loadCurrentUser() (line 413)                                  │
│ • Makes GET /api/auth/me request                                             │
│ • ⚠️ NO JWT TOKEN IN COOKIE - Request fails with 401                        │
│ • Router redirects to /login (line 377-382)                                 │
│ • User FINALLY logs in with new credentials                                 │
│ • WebSocket connection established                                           │
│ • App works normally                                                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Authentication Failure Points

### **Failure Point #1: Token Storage Mismatch**
**Location**: `ChangePassword.vue:320-328`

```javascript
// ❌ BROKEN: Token stored in localStorage, but API expects httpOnly cookie
if (response.data?.token) {
  localStorage.setItem('auth_token', response.data.token)
}
```

**Problem**:
- Password change endpoint returns JWT token
- Frontend stores token in `localStorage`
- BUT: API authentication requires httpOnly cookie named `access_token`
- Result: Token never used for authentication

**Evidence**:
```javascript
// auth.py:234-241 - Login sets httpOnly cookie
response.set_cookie(
    key="access_token",
    value=token,
    httponly=True,
    secure=False,
    samesite="lax",
    max_age=86400,  // 24 hours
)

// BUT change-password endpoint (auth.py:639-649) only returns token in response body
return PasswordChangeResponse(
    success=True,
    message="Password changed successfully",
    token=token,  // ❌ Not set as cookie!
    user={...},
)
```

---

### **Failure Point #2: WebSocket Connection Requires Authentication**
**Location**: `App.vue:419-432`, `websocket.js:29-48`

```javascript
// App.vue - Only connects WebSocket if user authenticated
if (currentUser.value) {
  const authToken = localStorage.getItem('auth_token')
  if (authToken) {
    const wsOptions = { token: authToken }
    await wsStore.connect(wsOptions)
  }
}

// BUT: currentUser.value is null during setup wizard
// Result: No WebSocket connection, ConnectionStatus shows "Disconnected"
```

**Problem**:
- `loadCurrentUser()` calls `/api/auth/me` (line 358)
- `/api/auth/me` checks `access_token` cookie (line 328)
- Cookie doesn't exist (token only in localStorage)
- Returns 401, `currentUser.value` stays null
- WebSocket never connects

---

### **Failure Point #3: Router Guard Allows Unauthenticated Setup**
**Location**: `router/index.js:32-42`

```javascript
{
  path: '/setup',
  name: 'Setup',
  component: () => import('@/views/SetupWizard.vue'),
  meta: {
    title: 'Setup Wizard',
    showInNav: false,
    requiresSetup: false, // Skip setup check for this route
    requiresAuth: false,  // ❌ NO authentication required
    requiresPasswordChange: false,
  },
}
```

**Problem**:
- Setup wizard explicitly bypasses authentication check
- Intended for fresh install (no users exist yet)
- BUT: In v3.0, admin user ALWAYS exists (created by installer)
- Result: User goes through setup wizard without being logged in

---

### **Failure Point #4: No Cookie Set by Change Password Endpoint**
**Location**: `api/endpoints/auth.py:632-649`

```python
@router.post("/change-password", response_model=PasswordChangeResponse, tags=["auth"])
async def change_password(
    request_body: PasswordChangeRequest = Body(...),
    request: Request = None,  # ⚠️ No Response parameter!
    db: AsyncSession = Depends(get_db_session)
):
    # ... password change logic ...

    # Generate JWT token
    token = JWTManager.create_access_token(
        user_id=admin_user.id,
        username=admin_user.username,
        role=admin_user.role,
        tenant_key=admin_user.tenant_key
    )

    # ❌ PROBLEM: Token returned in response body, NOT set as cookie
    return PasswordChangeResponse(
        success=True,
        message="Password changed successfully",
        token=token,  # Only in response body
        user={
            "id": str(admin_user.id),
            "username": admin_user.username,
            "role": admin_user.role,
            "tenant_key": admin_user.tenant_key,
        },
    )
```

**What Should Happen** (compare to login endpoint):
```python
@router.post("/login", response_model=LoginResponse, tags=["auth"])
async def login(
    request: LoginRequest = Body(...),
    response: Response = None,  # ✅ Response parameter present
    db: AsyncSession = Depends(get_db_session)
):
    # ... authentication logic ...

    # Generate JWT token
    token = JWTManager.create_access_token(...)

    # ✅ CORRECT: Set httpOnly cookie
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=86400,
    )

    return LoginResponse(...)
```

---

## 3. WebSocket Connection Issues

### **ConnectionStatus Component Analysis**

**Location**: `frontend/src/components/ConnectionStatus.vue`

**Current Behavior**:
```javascript
// ConnectionStatus shows chip based on wsStore.connectionState
const statusText = computed(() => {
  switch (wsStore.connectionState) {
    case 'connected':
      return 'Connected'
    case 'connecting':
      return 'Connecting...'
    case 'reconnecting':
      return `Reconnecting (${wsStore.reconnectAttempts}/${wsStore.maxReconnectAttempts})`
    case 'disconnected':
      return 'Disconnected'  // ⚠️ Shows this during entire setup wizard
    default:
      return 'Unknown'
  }
})
```

**Why It Shows "Disconnected" During Setup**:

1. **App.vue never connects WebSocket without authenticated user**:
   ```javascript
   // App.vue:416-432
   if (currentUser.value) {  // ⚠️ NULL during setup wizard
     const authToken = localStorage.getItem('auth_token')
     if (authToken) {
       await wsStore.connect({ token: authToken })
     }
   }
   ```

2. **WebSocket store requires token**:
   ```javascript
   // stores/websocket.js:29-48
   async function connect(options = {}) {
     // options.token used for authentication
     await websocketService.connect(options)
   }
   ```

3. **WebSocket service fails without token**:
   ```javascript
   // services/websocket.js (inferred)
   connect(options) {
     const wsUrl = `ws://${host}:7272/ws/${clientId}?token=${options.token}`
     // If no token, connection fails or is rejected by server
   }
   ```

**User Experience Impact**:
- ConnectionStatus shows red "Disconnected" chip throughout setup
- Users think something is broken
- No real-time updates during setup (not critical, but inconsistent)
- Confusing that setup wizard works despite "Disconnected" status

---

## 4. Component Analysis & Design Patterns

### **Login.vue Design Patterns (To Reuse)**

**Location**: `frontend/src/views/Login.vue`

**Key Patterns**:

1. **Form Validation with Real-time Feedback**:
   ```javascript
   // Line 140-143
   const rules = {
     required: (value) => !!value || 'This field is required',
   }

   // Validation on form submit
   const { valid } = await loginForm.value.validate()
   if (!valid) return
   ```

2. **Loading State Management**:
   ```javascript
   // Line 135, 153
   const loading = ref(false)

   // Disable button during API call
   :loading="loading"
   :disabled="!username || !password || loading"
   ```

3. **Error Handling with User-Friendly Messages**:
   ```javascript
   // Line 188-220
   if (err.response?.status === 401) {
     error.value = 'Invalid username or password'
   } else if (err.response?.status === 403) {
     // Check for password change required
     if (detail.includes('must_change_password')) {
       router.push('/change-password')
       return
     }
   } else if (err.code === 'ERR_NETWORK') {
     error.value = 'Network error - please check your connection'
   }
   ```

4. **Success State with Visual Feedback**:
   ```javascript
   // Line 179-183
   successMessage.value = 'Login successful! Redirecting...'
   await new Promise(resolve => setTimeout(resolve, 500))
   router.push(redirect)
   ```

5. **Auto-Login Check on Mount**:
   ```javascript
   // Line 230-251
   onMounted(async () => {
     try {
       await api.auth.me()
       // Already authenticated, redirect
       router.push(redirect || '/')
     } catch {
       // Not authenticated, stay on login page
     }
   })
   ```

6. **Remember Me Functionality**:
   ```javascript
   // Line 170-177
   if (rememberMe.value) {
     localStorage.setItem('remember_me', 'true')
     localStorage.setItem('remembered_username', username.value)
   }

   // Restore on mount (line 231-238)
   const rememberedUsername = localStorage.getItem('remembered_username')
   if (rememberedUsername) username.value = rememberedUsername
   ```

7. **Consistent Styling & Branding**:
   ```vue
   <!-- Logo with theme support -->
   <v-img
     :src="theme.global.current.value.dark ? '/Giljo_YW.svg' : '/Giljo_BY.svg'"
     alt="GiljoAI MCP"
     height="50"
   />

   <!-- Gradient background -->
   <style scoped>
   .login-container {
     background: linear-gradient(135deg, rgb(30, 49, 71) 0%, rgb(18, 29, 42) 100%);
     min-height: 100vh;
   }
   </style>
   ```

---

### **ChangePassword.vue Current Implementation**

**Location**: `frontend/src/views/ChangePassword.vue`

**Good Patterns (Keep These)**:
- ✅ Password strength meter with visual feedback (line 104-120)
- ✅ Comprehensive validation rules (line 232-252)
- ✅ Show/hide password toggles (line 197-200)
- ✅ Security notice alert (line 26-37)
- ✅ Accessibility attributes (aria-label, aria-required)

**Patterns to Remove** (When splitting into Welcome component):
- ❌ Hardcoded username 'admin' (line 189) - should be visible field
- ❌ Direct localStorage token storage (line 322) - should redirect to login
- ❌ Direct redirect to /setup (line 334) - should redirect to /login

**New Welcome Component Should**:
1. Show welcome message with logo
2. Display username field (read-only: "admin")
3. Show current password field (hint: "Default is 'admin'")
4. Show new password + confirm fields with strength meter
5. On success: redirect to /login, NOT /setup
6. Show "You'll be redirected to login" message after success

---

## 5. Route Guard Logic Analysis

**Location**: `frontend/src/router/index.js`

### **Current Guard Flow (Lines 196-300)**:

```javascript
router.beforeEach(async (to, from, next) => {
  // 1. Set page title
  document.title = `${to.meta.title || 'GiljoAI'} - MCP Orchestrator`

  // 2. Skip checks for routes with explicit bypasses
  if (to.meta.requiresSetup === false &&
      to.meta.requiresAuth === false &&
      to.meta.requiresPasswordChange === false) {
    next()
    return
  }

  // 3. PRIORITY 1: Check setup status
  if (to.meta.requiresSetup !== false) {
    const status = await setupService.checkStatus()

    // HIGHEST PRIORITY: Default password check
    if (to.meta.requiresPasswordChange !== false &&
        status.default_password_active) {
      if (to.path !== '/change-password') {
        next('/change-password')  // Force password change
        return
      }
    }

    // SECOND PRIORITY: Database initialization
    if (!status.default_password_active &&
        !status.database_initialized &&
        to.path !== '/setup') {
      next('/setup')  // Redirect to setup wizard
      return
    }
  }

  // 4. PRIORITY 3: Check authentication (AFTER setup)
  const requiresAuth = to.meta.requiresAuth !== false
  if (requiresAuth) {
    try {
      await api.auth.me()  // Check if authenticated
      // If successful, allow navigation
    } catch {
      // Not authenticated, redirect to login
      next({ path: '/login', query: { redirect: to.fullPath } })
      return
    }
  }

  // 5. Check admin role requirement
  if (to.meta.requiresAdmin && !userStore.isAdmin) {
    next({ name: 'Dashboard' })
    return
  }

  next()
})
```

### **Guard Priority Order (Current)**:
1. 🥇 **Password Change** (`default_password_active: true`) → `/change-password`
2. 🥈 **Setup Wizard** (`database_initialized: false`) → `/setup`
3. 🥉 **Authentication** (`requiresAuth: true`) → `/login`
4. 4️⃣ **Admin Role** (`requiresAdmin: true`) → `/`

### **Problems with Current Guard Logic**:

1. **Setup wizard allows unauthenticated access**:
   ```javascript
   {
     path: '/setup',
     meta: {
       requiresAuth: false,  // ❌ Bypasses authentication
     },
   }
   ```

2. **Password change doesn't redirect to login**:
   - User changes password at `/change-password`
   - Receives JWT token but doesn't set cookie
   - Redirects to `/setup` (unauthenticated)
   - Should redirect to `/login` instead

3. **No way to enforce authentication during setup**:
   - Once password changed, `default_password_active: false`
   - Guard redirects to `/setup` if `database_initialized: false`
   - `/setup` route has `requiresAuth: false`
   - User never authenticates

---

## 6. Recommended Solution Architecture

### **Phase 1: Welcome & Password Setup (UNAUTHENTICATED)**

**New Route**: `/welcome` (replaces `/change-password` for fresh installs)

```javascript
{
  path: '/welcome',
  name: 'Welcome',
  component: () => import('@/views/WelcomeSetup.vue'),
  meta: {
    title: 'Welcome to GiljoAI MCP',
    showInNav: false,
    requiresAuth: false,  // Unauthenticated (fresh install)
    requiresSetup: false,
    requiresPasswordChange: false,
  },
}
```

**Component**: `WelcomeSetup.vue` (NEW)
- Logo + welcome message
- Password change form (admin/admin → new password)
- Success message: "Password changed! You'll be redirected to login."
- Redirects to `/login` (NOT `/setup`)

**API Endpoint**: Reuse `/api/auth/change-password`
- No changes needed to backend
- Frontend just needs to redirect to `/login` instead of `/setup`

---

### **Phase 2: Login (AUTHENTICATED)**

**Existing Route**: `/login`

**Component**: `Login.vue` (NO CHANGES)
- User logs in with new credentials
- Sets httpOnly cookie `access_token`
- Redirects to `/setup` (authenticated)

---

### **Phase 3: Setup Wizard (AUTHENTICATED)**

**Modified Route**: `/setup`

```javascript
{
  path: '/setup',
  name: 'Setup',
  component: () => import('@/views/SetupWizard.vue'),
  meta: {
    title: 'Setup Wizard',
    showInNav: false,
    requiresAuth: true,  // ✅ NOW requires authentication
    requiresSetup: false,
  },
}
```

**Component**: `SetupWizard.vue` (REMOVE PASSWORD STEP)
- Step 1: MCP Configuration (optional)
- Step 2: Serena Activation (optional)
- Step 3: Complete
- User is authenticated → WebSocket connects → ConnectionStatus shows "Connected"

---

### **Modified Router Guard Logic**:

```javascript
router.beforeEach(async (to, from, next) => {
  // 1. Set page title
  document.title = `${to.meta.title || 'GiljoAI'} - MCP Orchestrator`

  // 2. Skip checks for routes with explicit bypasses
  if (to.meta.requiresSetup === false &&
      to.meta.requiresAuth === false &&
      to.meta.requiresPasswordChange === false) {
    next()
    return
  }

  // 3. PRIORITY 1: Check setup status
  if (to.meta.requiresSetup !== false) {
    const status = await setupService.checkStatus()

    // NEW: Redirect to welcome if default password active
    if (to.meta.requiresPasswordChange !== false &&
        status.default_password_active) {
      if (to.path !== '/welcome') {
        next('/welcome')  // ✅ NEW welcome page
        return
      }
    }

    // NEW: After password change, redirect to login (not setup)
    // This is handled by WelcomeSetup.vue component, not guard

    // MODIFIED: Setup wizard now requires authentication
    // Guard will check authentication below (no special handling needed)
  }

  // 4. PRIORITY 2: Check authentication (BEFORE setup wizard)
  const requiresAuth = to.meta.requiresAuth !== false
  if (requiresAuth) {
    try {
      await api.auth.me()  // Check if authenticated
      // If successful, allow navigation
    } catch {
      // Not authenticated, redirect to login
      next({ path: '/login', query: { redirect: to.fullPath } })
      return
    }
  }

  // 5. Check admin role requirement
  if (to.meta.requiresAdmin && !userStore.isAdmin) {
    next({ name: 'Dashboard' })
    return
  }

  next()
})
```

---

## 7. Summary of Changes Needed

### **New Files**:
1. `frontend/src/views/WelcomeSetup.vue` - Welcome page with password change
2. `frontend/src/components/setup/WelcomePasswordStep.vue` (optional) - Extracted password form component

### **Modified Files**:
1. `frontend/src/router/index.js`:
   - Add `/welcome` route
   - Change `/setup` route: `requiresAuth: true`
   - Update router guard to redirect to `/welcome` instead of `/change-password`

2. `frontend/src/views/SetupWizard.vue`:
   - Remove password change step (if it exists)
   - Assume user is authenticated
   - Keep MCP + Serena + Complete steps only

3. `frontend/src/views/ChangePassword.vue`:
   - Keep for post-login password changes
   - NOT used during fresh install flow anymore

### **Backend Changes**:
- ❌ NO CHANGES NEEDED to `api/endpoints/auth.py`
- Frontend will handle redirect to `/login` after password change
- Existing `/api/auth/change-password` endpoint works as-is

---

## 8. Testing Checklist

### **Fresh Install Flow**:
- [ ] Run `python install.py` to create fresh database
- [ ] Browser opens to `http://localhost:7274`
- [ ] Router redirects to `/welcome` (default_password_active: true)
- [ ] User sees welcome message + password change form
- [ ] User submits form with new password
- [ ] Success message: "Password changed! Redirecting to login..."
- [ ] Router redirects to `/login`
- [ ] User logs in with new credentials
- [ ] JWT cookie set (`access_token`)
- [ ] Router redirects to `/setup`
- [ ] ConnectionStatus shows "Connected" (green)
- [ ] User completes setup wizard
- [ ] Router redirects to `/` (dashboard)

### **Authentication State**:
- [ ] `/welcome` - Unauthenticated (no WebSocket)
- [ ] `/login` - Unauthenticated (no WebSocket)
- [ ] `/setup` - Authenticated (WebSocket connected)
- [ ] `/` (dashboard) - Authenticated (WebSocket connected)

### **WebSocket Connection**:
- [ ] No WebSocket connection during `/welcome`
- [ ] No WebSocket connection during `/login`
- [ ] WebSocket connects after login, before `/setup`
- [ ] ConnectionStatus shows "Connected" during `/setup`
- [ ] Real-time updates work during `/setup` (if applicable)

### **Edge Cases**:
- [ ] User closes browser during `/welcome` → Reopens to `/welcome` again
- [ ] User closes browser during `/login` → Reopens to `/login` again
- [ ] User closes browser during `/setup` → Reopens to `/setup` (authenticated)
- [ ] User bookmarks `/setup` → Redirected to `/login` if not authenticated
- [ ] User navigates to `/change-password` after setup → Shows "already changed" message or redirects to `/login`

---

## 9. UX Flow Comparison

### **Current Broken Flow**:
```
install.py → /change-password (unauthenticated)
         ↓
  Password changed, token in localStorage (not cookie)
         ↓
   /setup (unauthenticated, "Disconnected")
         ↓
  Complete setup, redirect to /
         ↓
   / → 401 error → /login (finally authenticate)
         ↓
  Dashboard (authenticated, "Connected")
```

**Problems**:
- User never logs in until forced by 401 error
- "Disconnected" status throughout setup
- Confusing token storage (localStorage vs cookie mismatch)
- Extra redirect through `/login` after setup complete

---

### **Proposed Fixed Flow**:
```
install.py → /welcome (unauthenticated, "Disconnected")
         ↓
  Password changed, redirect to /login
         ↓
   /login (authenticate, set cookie)
         ↓
   /setup (authenticated, "Connected")
         ↓
  Complete setup, redirect to /
         ↓
  Dashboard (authenticated, "Connected")
```

**Benefits**:
- ✅ Clear authentication point (/login)
- ✅ WebSocket connected during setup wizard
- ✅ "Connected" status throughout authenticated flow
- ✅ No confusing token storage mismatch
- ✅ Single authentication flow (no extra redirect)
- ✅ User understands they "logged in" with new password

---

## Conclusion

The broken authentication flow stems from **storing JWT token in localStorage without setting httpOnly cookie**, combined with **setup wizard bypassing authentication checks**. The fix requires a **two-phase approach**:

1. **Phase 1 (Welcome)**: Unauthenticated password change → redirect to login
2. **Phase 2 (Setup)**: Authenticated setup wizard → WebSocket connected

This creates a **clear, linear flow** that matches user expectations and ensures proper authentication state throughout the onboarding process.
