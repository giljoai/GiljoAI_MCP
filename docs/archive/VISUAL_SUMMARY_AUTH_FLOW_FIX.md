# VISUAL SUMMARY: Authentication Flow Fix

**Quick Reference Guide for HANDOVER_0013**

---

## The Problem in One Image

```
CURRENT BROKEN FLOW:
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  install.py  │ ──▶ │  /change-pwd │ ──▶ │    /setup    │ ──▶ │ /login (?)   │
│  Creates DB  │     │ Unauthenticated │     │ Unauthenticated │     │ Finally auth │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                          Token in           "Disconnected"         Too late!
                       localStorage        WebSocket fails
```

```
FIXED FLOW:
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  install.py  │ ──▶ │   /welcome   │ ──▶ │    /login    │ ──▶ │    /setup    │
│  Creates DB  │     │ Change pwd   │     │  Authenticate │     │  Authenticated │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                      Unauthenticated      Cookie set here!    "Connected" ✓
                                           WebSocket ready
```

---

## The Root Cause

### **Token Storage Mismatch**

```javascript
// ❌ WRONG: ChangePassword.vue stores token in localStorage
localStorage.setItem('auth_token', response.data.token)

// ✅ CORRECT: Login.vue sets httpOnly cookie (backend does this)
response.set_cookie(
  key="access_token",
  value=token,
  httponly=True
)
```

**Why This Matters**:
- API authentication checks `access_token` **cookie**, not localStorage
- WebSocket requires authenticated user (cookie present)
- No cookie = No authentication = No WebSocket = "Disconnected"

---

## The Fix in 3 Steps

### **Step 1: Create Welcome Page**

**New File**: `frontend/src/views/WelcomeSetup.vue`

```vue
<template>
  <v-container>
    <v-card>
      <v-card-title>Welcome to GiljoAI MCP</v-card-title>
      <v-card-text>
        <p>First-time setup: Change default password</p>
        <!-- Password change form (reuse from ChangePassword.vue) -->
        <WelcomePasswordStep @success="handlePasswordChanged" />
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

function handlePasswordChanged() {
  // ✅ CRITICAL: Redirect to /login, NOT /setup
  router.push({
    path: '/login',
    query: { message: 'Password changed successfully. Please login.' }
  })
}
</script>
```

---

### **Step 2: Update Router**

**File**: `frontend/src/router/index.js`

```javascript
// NEW ROUTE: Welcome page
{
  path: '/welcome',
  name: 'Welcome',
  component: () => import('@/views/WelcomeSetup.vue'),
  meta: {
    requiresAuth: false,  // Unauthenticated
    requiresPasswordChange: false,
  },
},

// MODIFIED ROUTE: Setup wizard now requires auth
{
  path: '/setup',
  name: 'Setup',
  component: () => import('@/views/SetupWizard.vue'),
  meta: {
    requiresAuth: true,  // ✅ CHANGED: Now requires authentication
    requiresSetup: false,
  },
}
```

**Router Guard Update**:
```javascript
// Change redirect target
if (status.default_password_active) {
  if (to.path !== '/welcome') {  // ✅ CHANGED: Was '/change-password'
    next('/welcome')
    return
  }
}
```

---

### **Step 3: Remove Password Step from Setup Wizard**

**File**: `frontend/src/views/SetupWizard.vue`

```javascript
// BEFORE: 4 steps (broken)
const allSteps = [
  { component: PasswordChangeStep },  // ❌ REMOVE THIS
  { component: McpConfigStep },
  { component: SerenaConfigStep },
  { component: CompletionStep },
]

// AFTER: 3 steps (fixed)
const allSteps = [
  { component: McpConfigStep },       // ✅ Start here
  { component: SerenaConfigStep },
  { component: CompletionStep },
]
```

---

## Component Reuse Strategy

### **Extract Shared Password Form**

**New File**: `frontend/src/components/setup/WelcomePasswordStep.vue`

```vue
<template>
  <v-form ref="form" @submit.prevent="handleSubmit">
    <!-- Current password field -->
    <v-text-field
      v-model="currentPassword"
      label="Current Password"
      type="password"
      hint="Default is 'admin'"
    />

    <!-- New password field -->
    <v-text-field
      v-model="newPassword"
      label="New Password"
      type="password"
      :rules="passwordRules"
    />

    <!-- Password strength meter -->
    <v-progress-linear :model-value="passwordStrength" :color="strengthColor" />

    <!-- Confirm password field -->
    <v-text-field
      v-model="confirmPassword"
      label="Confirm Password"
      type="password"
    />

    <v-btn type="submit" :loading="loading">Change Password</v-btn>
  </v-form>
</template>

<script setup>
// Reuse logic from ChangePassword.vue
// Emit 'success' event when password changed
</script>
```

**Usage**:
- `WelcomeSetup.vue` - Fresh install password change
- `ChangePassword.vue` - Post-login password change (keep existing)

---

## Authentication State Timeline

```
TIME: 0s - Fresh install
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Route:           /welcome
Authenticated:   ❌ NO
Cookie Set:      ❌ NO
WebSocket:       ❌ Disconnected
ConnectionStatus: 🔴 "Disconnected"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TIME: 30s - Password changed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Action: User submits new password
Backend: Sets default_password_active = false
Frontend: Redirects to /login
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TIME: 35s - Login page
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Route:           /login
Authenticated:   ❌ NO
Cookie Set:      ❌ NO
WebSocket:       ❌ Disconnected
ConnectionStatus: 🔴 "Disconnected"
Message: "Password changed successfully. Please login."
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TIME: 45s - User logs in
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Action: User enters new credentials
Backend: Sets httpOnly cookie "access_token"
Frontend: Redirects to /setup
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TIME: 46s - Setup wizard (AUTHENTICATED)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Route:           /setup
Authenticated:   ✅ YES
Cookie Set:      ✅ YES (access_token)
WebSocket:       ✅ Connected
ConnectionStatus: 🟢 "Connected"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TIME: 120s - Setup complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Route:           / (dashboard)
Authenticated:   ✅ YES
Cookie Set:      ✅ YES
WebSocket:       ✅ Connected
ConnectionStatus: 🟢 "Connected"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## File Change Checklist

### **Create New Files**:
- [ ] `frontend/src/views/WelcomeSetup.vue` - Welcome page container
- [ ] `frontend/src/components/setup/WelcomePasswordStep.vue` - Password form component

### **Modify Existing Files**:
- [ ] `frontend/src/router/index.js`:
  - Add `/welcome` route
  - Change `/setup` to `requiresAuth: true`
  - Update router guard redirect target
- [ ] `frontend/src/views/SetupWizard.vue`:
  - Remove password change step from allSteps array
  - Update step numbering

### **Keep Unchanged**:
- ✅ `frontend/src/views/Login.vue` - No changes
- ✅ `frontend/src/views/ChangePassword.vue` - Keep for post-login changes
- ✅ `api/endpoints/auth.py` - No backend changes needed

---

## Testing Quick Guide

### **Manual Test Flow**:

1. **Fresh Install**:
   ```bash
   # Drop database
   psql -U postgres -c "DROP DATABASE IF EXISTS giljo_mcp;"

   # Run installer
   python install.py

   # Browser should open to http://localhost:7274
   ```

2. **Welcome Page**:
   - ✅ Should redirect to `/welcome`
   - ✅ Should show "Welcome to GiljoAI MCP"
   - ✅ Should show password change form
   - ✅ ConnectionStatus should show 🔴 "Disconnected"

3. **Change Password**:
   - Enter current password: `admin`
   - Enter new password: `Admin123!@#` (must meet requirements)
   - Confirm password: `Admin123!@#`
   - Click "Change Password"
   - ✅ Should show success message
   - ✅ Should redirect to `/login`

4. **Login**:
   - ✅ Should show "Password changed successfully" message
   - Enter username: `admin`
   - Enter password: `Admin123!@#`
   - Click "Sign In"
   - ✅ Should redirect to `/setup`

5. **Setup Wizard**:
   - ✅ ConnectionStatus should show 🟢 "Connected"
   - ✅ Should start at "MCP Configuration" (Step 1 of 3)
   - ✅ Should NOT have password change step
   - Complete wizard
   - ✅ Should redirect to `/` (dashboard)

6. **Dashboard**:
   - ✅ ConnectionStatus should show 🟢 "Connected"
   - ✅ WebSocket should be working (real-time updates)
   - ✅ User menu should show "admin" with "admin" role chip

---

## Debug Checklist

### **If ConnectionStatus shows "Disconnected" during setup**:
1. Check browser console for WebSocket errors
2. Verify `access_token` cookie is set:
   - Open DevTools → Application → Cookies
   - Should see `access_token` with value starting with `eyJ...`
3. Check `/api/auth/me` returns 200 (not 401):
   - Open DevTools → Network tab
   - Look for `/api/auth/me` request
   - Should return user data with 200 status
4. Verify WebSocket connection URL:
   - Console should show: `[WebSocket] Connected to ws://localhost:7272/ws/{client_id}`
   - Should NOT show repeated connection errors

### **If redirected to /login after setup complete**:
1. Check `default_password_active` flag:
   - Make GET request to `/api/setup/status`
   - Should return `"default_password_active": false`
2. Check `database_initialized` flag:
   - Same `/api/setup/status` response
   - Should return `"database_initialized": true`
3. Verify router guard logic:
   - Add console.log to `router/index.js` guard
   - Should NOT redirect authenticated user to `/login`

### **If WebSocket fails to connect**:
1. Check API server is running on port 7272
2. Check WebSocket endpoint is accessible:
   ```bash
   curl http://localhost:7272/api/health
   ```
3. Verify token is being sent to WebSocket:
   - Check `App.vue:426` - should pass `token` to `wsStore.connect()`
4. Check WebSocket service logs:
   - Open DevTools → Console
   - Look for `[WebSocket]` prefixed messages

---

## Success Metrics

After implementing the fix, you should see:

✅ **Zero "Disconnected" status during setup wizard**
✅ **Single authentication flow (welcome → login → setup → dashboard)**
✅ **No localStorage token storage confusion**
✅ **Clear user journey: "I changed password, then logged in"**
✅ **WebSocket connected from setup wizard onwards**
✅ **No unexpected redirects to /login after setup complete**

---

## Key Takeaway

**The fix is simple**:
1. Don't authenticate during password change
2. Authenticate at login (like normal apps)
3. Require authentication for setup wizard

**Result**: Clear, predictable authentication flow that matches user mental model.
