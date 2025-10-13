# Handover: Authentication-Gated Product Initialization (Option B - Architectural Fix)

**Date:** 2025-10-13
**From Agent:** Claude (Session: Architecture Analysis)
**To Agent:** Frontend Architect + TDD Implementor
**Priority:** High
**Estimated Complexity:** 4-6 hours
**Status:** Not Started

---

## Task Summary

**What:** Move product store initialization from global page load to post-authentication lifecycle, establishing proper authentication gates for tenant-specific data loading.

**Why:** Currently, the products store attempts to initialize on EVERY page load (including login, password change, and setup wizard), causing:
1. API calls to wrong port (7274 instead of 7272) resulting in HTML error pages parsed as JSON
2. Tenant-specific data fetching before authentication context is established
3. Security violation - attempting to access protected resources without JWT tokens
4. Multi-tenant architecture violation - no tenant_key context available pre-auth

**Expected Outcome:**
- Products store ONLY initializes after successful authentication
- Login/password-change/setup pages remain clean (no product API calls)
- Tenant context established before product data fetching
- Proper authentication-gated architecture for all tenant-specific stores

---

## Context and Background

### Discovery Timeline

**User Report (2025-10-13):**
- Console errors during first-run password change flow
- Same error on both `localhost:7274` and `10.1.0.164:7274` access
- Error: `SyntaxError: Unexpected token '<', "<!DOCTYPE "... is not valid JSON`

**Root Cause Analysis:**
1. `products.js:214` uses `fetch('/api/setup/status')` - relative URL hits wrong port (7274 not 7272)
2. More critically: `App.vue` calls products store initialization on mount, regardless of auth state
3. Products are **tenant-specific** - should never be fetched before authentication establishes tenant context

**Architectural Issue:**
This is not just a port bug - it's a fundamental architecture flaw where tenant-specific data is being requested in an anonymous context.

### Current Implementation (Broken)

**App.vue (lines 389-448):**
```javascript
onMounted(async () => {
  // ... theme setup ...

  await router.isReady()
  await loadCurrentUser()  // May return false (not authenticated)

  if (currentUser.value) {
    // WebSocket + data loading happens here
  } else {
    console.log('[Auth] User not authenticated, skipping WebSocket connection')
    // BUT products store STILL initializes elsewhere!
  }
})
```

**The Problem:**
- `App.vue` doesn't explicitly call `productStore.initializeFromStorage()`
- But somewhere in the component tree, it's being called on mount
- Needs investigation: Where is `initializeFromStorage()` being invoked?

### Files Involved

**Core Files:**
- `frontend/src/stores/products.js` - Products Pinia store (needs auth guard)
- `frontend/src/App.vue` - Application root (needs post-auth initialization trigger)
- `frontend/src/components/ProductSwitcher.vue` - Likely triggers store initialization

**Reference Files:**
- `frontend/src/services/api.js` - API client with correct base URL
- `frontend/src/stores/user.js` - User store (authentication state)
- `frontend/src/router/index.js` - Router guards (setup/auth flow)

---

## Technical Details

### Current Product Store Initialization

**products.js (lines 210-259):**
```javascript
async function initializeFromStorage() {
  try {
    // WRONG: Uses fetch('/api/setup/status') - hits port 7274, not 7272
    const setupResponse = await fetch('/api/setup/status')

    if (setupResponse.ok) {
      const setupStatus = await setupResponse.json()

      // Skip if in setup flow
      if (setupStatus.default_password_active || !setupStatus.database_initialized) {
        return
      }
    }
  } catch (error) {
    // Fails silently - returns early
    return
  }

  // Attempts to fetch products (will fail without auth token)
  await fetchProducts()
  // ... more product logic ...
}
```

**Issues:**
1. ❌ Wrong port (minor - can be fixed with API client)
2. ❌ No authentication check (major - architectural flaw)
3. ❌ No tenant context validation (major - security issue)

### Where is initializeFromStorage() Called?

**Need to investigate:**
```bash
# Search for initializeFromStorage invocations
grep -r "initializeFromStorage" frontend/src/
```

**Likely culprits:**
- `ProductSwitcher.vue` - Component mounted, calls store init
- `App.vue` - Some indirect trigger through Pinia store usage
- Store auto-initialization on first access

### Correct Architecture

**Authentication-Gated Initialization:**
```javascript
// App.vue (conceptual)
onMounted(async () => {
  await router.isReady()

  const isAuthenticated = await loadCurrentUser()

  if (isAuthenticated) {
    // ✅ ONLY initialize tenant-specific stores after auth
    await productStore.initializeFromStorage()
    await wsStore.connect({ token: authToken })
    await agentStore.fetchAgents()
    await messageStore.fetchMessages()
  }
})
```

**Products Store Changes:**
```javascript
async function initializeFromStorage() {
  // ✅ FIRST: Verify authentication context exists
  const authToken = localStorage.getItem('auth_token')
  if (!authToken) {
    console.log('[PRODUCTS] No auth token - skipping initialization')
    return
  }

  // ✅ SECOND: Use API client (correct port, includes auth header)
  try {
    const setupStatus = await api.setup.status()  // NOT raw fetch()

    if (setupStatus.default_password_active || !setupStatus.database_initialized) {
      console.log('[PRODUCTS] Setup incomplete - skipping product initialization')
      return
    }
  } catch (error) {
    console.warn('[PRODUCTS] Setup status check failed:', error)
    return
  }

  // ✅ THIRD: Fetch products (tenant-specific, auth-gated)
  await fetchProducts()
}
```

---

## Implementation Plan

### Phase 1: Investigation & Mapping (30 minutes)

**Actions:**
1. Search codebase for all `initializeFromStorage()` calls
2. Map product store initialization triggers
3. Identify all components that access `useProductStore()`
4. Document current initialization flow

**Expected Outcome:**
- Clear map of where products store initializes
- List of components that depend on products store
- Understanding of initialization timing

**Testing Criteria:**
- Complete call graph documented
- All initialization points identified

### Phase 2: Add API Endpoint for Setup Status (1 hour)

**Current Issue:**
- `fetch('/api/setup/status')` doesn't exist
- API interceptor uses same broken pattern

**Actions:**
1. Add `api.setup.status()` method to `frontend/src/services/api.js`
2. Ensure it uses `apiClient` (correct base URL with port 7272)
3. Test endpoint returns proper JSON (not HTML)

**Code Changes:**
```javascript
// frontend/src/services/api.js (add to exports)
setup: {
  status: () => apiClient.get('/api/setup/status'),
  check: () => apiClient.get('/api/setup/check'),
}
```

**Testing Criteria:**
- `/api/setup/status` returns JSON response
- Works from both localhost and network IP
- Includes `default_password_active` and `database_initialized` flags

### Phase 3: Update Products Store with Auth Guards (2 hours)

**Actions:**
1. Add authentication check to `initializeFromStorage()`
2. Replace `fetch()` with `api.setup.status()`
3. Add tenant context validation
4. Add explicit console logging for debugging

**Code Changes:**
```javascript
// products.js - initializeFromStorage()
async function initializeFromStorage() {
  // Auth guard
  const authToken = localStorage.getItem('auth_token')
  if (!authToken) {
    console.log('[PRODUCTS] Skipping initialization - no auth token')
    return
  }

  // Setup status check (using API client)
  try {
    const response = await api.setup.status()
    const setupStatus = response.data

    if (setupStatus.default_password_active || !setupStatus.database_initialized) {
      console.log('[PRODUCTS] Skipping initialization - setup incomplete')
      localStorage.removeItem('currentProductId')
      return
    }
  } catch (error) {
    console.warn('[PRODUCTS] Setup status check failed, skipping initialization:', error)
    return
  }

  // Tenant-specific data loading (protected by auth token in apiClient)
  const storedProductId = localStorage.getItem('currentProductId')
  await fetchProducts()

  if (products.value.length === 0) {
    localStorage.removeItem('currentProductId')
    return
  }

  // ... rest of initialization logic ...
}
```

**Testing Criteria:**
- Products store skips initialization on login page
- Products store skips initialization on password change page
- Products store skips initialization on setup wizard
- Products store initializes after successful login
- No console errors about JSON parsing

### Phase 4: Move Initialization to Post-Auth Lifecycle (2 hours)

**Actions:**
1. Update `App.vue` to explicitly call `productStore.initializeFromStorage()` after authentication
2. Remove any implicit initialization triggers
3. Ensure `ProductSwitcher.vue` doesn't trigger premature initialization
4. Add initialization to post-login flow

**Code Changes:**

**App.vue:**
```javascript
onMounted(async () => {
  // ... theme setup ...

  await router.isReady()
  const isAuthenticated = await loadCurrentUser()

  if (isAuthenticated) {
    // ✅ Explicitly initialize tenant-specific stores POST-AUTH
    const productStore = useProductStore()
    await productStore.initializeFromStorage()

    // Then connect WebSocket and load other data
    const authToken = localStorage.getItem('auth_token')
    await wsStore.connect({ token: authToken })
    await agentStore.fetchAgents()
    await messageStore.fetchMessages()

    // ... rest of authenticated initialization ...
  }
})
```

**ProductSwitcher.vue** (if it exists):
```javascript
// Ensure it doesn't call initializeFromStorage() on mount
// Only access products store after it's initialized
onMounted(() => {
  const productStore = useProductStore()
  // Safe - just reads state, doesn't trigger initialization
  const products = productStore.products
})
```

**Testing Criteria:**
- Products store initializes exactly once after login
- No initialization attempts on pre-auth pages
- ProductSwitcher displays correctly after initialization
- Switching products works correctly

### Phase 5: Fix API Interceptor (30 minutes)

**Current Issue:**
`api.js:53` also uses `fetch('/api/setup/status')` - same bug

**Actions:**
1. Replace `fetch('/api/setup/status')` with `api.setup.status()`
2. Handle circular dependency (interceptor calling API client)
3. Consider using direct apiClient.get() to avoid interceptor loop

**Code Changes:**
```javascript
// api.js - response interceptor (lines 32-88)
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token')
      localStorage.removeItem('user')

      if (!window.location.pathname.includes('/login') && !originalRequest._retry) {
        originalRequest._retry = true

        try {
          // Use apiClient directly to avoid interceptor loop
          const setupResponse = await apiClient.get('/api/setup/status')
          const setupStatus = setupResponse.data

          if (!setupStatus.database_initialized) {
            console.log('[API] Database not initialized - skipping login redirect')
            return Promise.reject(error)
          }
        } catch (e) {
          console.log('[API] Setup status check failed - assuming fresh install')
          return Promise.reject(error)
        }

        const currentPath = window.location.pathname + window.location.search
        window.location.href = `/login?redirect=${encodeURIComponent(currentPath)}`
      }
    }

    return Promise.reject(error)
  }
)
```

**Testing Criteria:**
- 401 errors handled correctly
- No infinite interceptor loops
- Fresh install flow preserved
- Login redirects work correctly

### Phase 6: Update Other Tenant-Specific Stores (1 hour)

**Actions:**
1. Review other stores (agents, messages, tasks, projects)
2. Ensure they also have authentication guards
3. Move their initialization to post-auth lifecycle
4. Document pattern for future stores

**Stores to Review:**
- `frontend/src/stores/agents.js`
- `frontend/src/stores/messages.js`
- `frontend/src/stores/tasks.js`
- `frontend/src/stores/projects.js`

**Pattern to Apply:**
```javascript
// All tenant-specific stores should follow this pattern
async function initialize() {
  const authToken = localStorage.getItem('auth_token')
  if (!authToken) {
    console.log('[STORE_NAME] Skipping initialization - no auth token')
    return
  }

  // Fetch tenant-specific data (apiClient includes auth header automatically)
  await fetchData()
}
```

**Testing Criteria:**
- All stores skip initialization pre-auth
- All stores initialize post-auth
- No tenant data leakage
- No unauthorized API calls

---

## Testing Requirements

### Unit Tests

**Test: Products Store Auth Guard**
```javascript
describe('Products Store - initializeFromStorage', () => {
  it('should skip initialization when no auth token exists', async () => {
    localStorage.removeItem('auth_token')
    await productStore.initializeFromStorage()
    expect(productStore.products).toHaveLength(0)
  })

  it('should skip initialization during setup flow', async () => {
    localStorage.setItem('auth_token', 'fake-token')
    mockApiResponse('/api/setup/status', { default_password_active: true })
    await productStore.initializeFromStorage()
    expect(productStore.products).toHaveLength(0)
  })

  it('should initialize products after authentication', async () => {
    localStorage.setItem('auth_token', 'valid-token')
    mockApiResponse('/api/setup/status', {
      default_password_active: false,
      database_initialized: true
    })
    mockApiResponse('/api/v1/products/', { data: [{ id: 1, name: 'Product 1' }] })

    await productStore.initializeFromStorage()
    expect(productStore.products).toHaveLength(1)
  })
})
```

**Test: App.vue Initialization Flow**
```javascript
describe('App.vue - onMounted', () => {
  it('should not initialize products when not authenticated', async () => {
    mockAuthResponse(401) // Not authenticated
    const productInitSpy = vi.spyOn(productStore, 'initializeFromStorage')

    await mountApp()
    expect(productInitSpy).not.toHaveBeenCalled()
  })

  it('should initialize products after successful authentication', async () => {
    mockAuthResponse(200, { username: 'admin', role: 'admin' })
    const productInitSpy = vi.spyOn(productStore, 'initializeFromStorage')

    await mountApp()
    await flushPromises()
    expect(productInitSpy).toHaveBeenCalledOnce()
  })
})
```

### Integration Tests

**Test: Login Flow**
```javascript
describe('Login to Dashboard Flow', () => {
  it('should load products after successful login', async () => {
    // Visit login page
    await page.goto('http://localhost:7274/login')

    // No product API calls should happen yet
    expect(networkLog.filter(r => r.url.includes('/products/'))).toHaveLength(0)

    // Login
    await page.fill('input[name="username"]', 'admin')
    await page.fill('input[name="password"]', 'password123')
    await page.click('button[type="submit"]')

    // Wait for redirect to dashboard
    await page.waitForURL('http://localhost:7274/')

    // NOW products should be fetched
    await page.waitForRequest(req => req.url().includes('/api/v1/products/'))

    // Product switcher should display
    const productSwitcher = await page.locator('[data-testid="product-switcher"]')
    await expect(productSwitcher).toBeVisible()
  })
})
```

**Test: Fresh Install Flow**
```javascript
describe('Fresh Install Flow', () => {
  it('should not load products during password change', async () => {
    await setupFreshDatabase()
    await page.goto('http://localhost:7274')

    // Should redirect to password change
    await page.waitForURL(/\/change-password/)

    // No product API calls during password change
    const productRequests = networkLog.filter(r => r.url.includes('/products/'))
    expect(productRequests).toHaveLength(0)

    // Change password
    await page.fill('input[name="oldPassword"]', 'admin')
    await page.fill('input[name="newPassword"]', 'SecurePass123!')
    await page.fill('input[name="confirmPassword"]', 'SecurePass123!')
    await page.click('button[type="submit"]')

    // Wait for setup wizard
    await page.waitForURL(/\/setup/)

    // Still no product requests during setup
    expect(networkLog.filter(r => r.url.includes('/products/'))).toHaveLength(0)

    // Complete setup wizard
    await page.click('button[data-testid="complete-setup"]')

    // NOW products should load
    await page.waitForRequest(req => req.url().includes('/api/v1/products/'))
  })
})
```

### Manual Testing

**Test Plan:**

1. **Fresh Install Flow**
   - [ ] Drop database: `psql -U postgres -c "DROP DATABASE IF EXISTS giljo_mcp;"`
   - [ ] Run installer: `python install.py`
   - [ ] Access app: `http://localhost:7274`
   - [ ] Open browser console (F12)
   - [ ] Verify NO errors about JSON parsing
   - [ ] Verify NO requests to `/api/v1/products/` on password change page
   - [ ] Change password
   - [ ] Verify NO requests to `/api/v1/products/` on setup wizard
   - [ ] Complete setup wizard
   - [ ] Verify products API is called AFTER reaching dashboard
   - [ ] Verify products dropdown works correctly

2. **Existing User Login**
   - [ ] Access app: `http://localhost:7274`
   - [ ] Should redirect to login (if not logged in)
   - [ ] Open browser console
   - [ ] Verify NO errors during login page load
   - [ ] Enter credentials and login
   - [ ] Verify products load AFTER login success
   - [ ] Verify products dropdown displays correctly

3. **Network IP Access**
   - [ ] Access app: `http://10.1.0.164:7274`
   - [ ] Repeat all tests from localhost
   - [ ] Verify same behavior (no localhost vs network differences)

4. **Console Verification**
   - [ ] Verify console logs show correct initialization order:
     ```
     [MAIN] Starting application initialization
     [MAIN] App mounted to #app
     [Auth] Current user loaded: admin
     [PRODUCTS] Initializing from storage...
     [PRODUCTS] Products loaded: 2
     [WebSocket] Connected successfully
     ```
   - [ ] Verify NO errors like:
     ```
     SyntaxError: Unexpected token '<', "<!DOCTYPE "...
     [PRODUCTS] Failed to check setup status...
     ```

---

## Dependencies and Blockers

### Dependencies
1. **Backend API Endpoint:** `/api/setup/status` must exist and return JSON
   - Check: `curl http://localhost:7272/api/setup/status`
   - Should return: `{"default_password_active": false, "database_initialized": true}`
   - If missing, needs backend implementation first

2. **User Store:** `useUserStore()` must provide authentication state
   - Check: `frontend/src/stores/user.js`
   - Must expose: `isAuthenticated` computed or similar

3. **API Client Configuration:** `API_CONFIG.REST_API.baseURL` must be correct
   - Check: `frontend/src/config/api.js`
   - Must be: `http://localhost:7272` (or network IP with port 7272)

### Known Blockers
None currently - all dependencies should be in place

### Questions Needing Answers
1. Is `ProductSwitcher.vue` the component calling `initializeFromStorage()` on mount?
2. Are there other stores that need the same authentication-gating pattern?
3. Should we add a global "authenticated" flag in Pinia to gate all tenant-specific stores?

---

## Success Criteria

### Definition of Done

**Feature works as specified:**
- [ ] Products store NEVER initializes on login page
- [ ] Products store NEVER initializes on password change page
- [ ] Products store NEVER initializes on setup wizard
- [ ] Products store ONLY initializes after successful authentication
- [ ] Products store uses correct API port (7272) via API client
- [ ] Products store validates authentication before fetching
- [ ] Products store validates tenant context before fetching

**All tests pass:**
- [ ] Unit tests for products store auth guards pass
- [ ] Integration tests for login flow pass
- [ ] Manual testing confirms no console errors
- [ ] Manual testing confirms correct initialization timing

**Code reviewed and approved:**
- [ ] Code follows Vue 3 Composition API patterns
- [ ] Code follows Pinia store best practices
- [ ] Console logging is clear and helpful
- [ ] Error handling is graceful

**Documentation updated:**
- [ ] `docs/devlog/` updated with implementation notes
- [ ] Code comments explain authentication gating
- [ ] Pattern documented for future tenant-specific stores

**Deployed/merged:**
- [ ] Changes committed to git
- [ ] Branch merged to master
- [ ] Fresh install tested on clean system

---

## Rollback Plan

### If Things Go Wrong

**Symptoms of Failure:**
- Products don't load after login
- Products dropdown is empty/broken
- WebSocket connection fails
- Dashboard shows no data

**Rollback Steps:**

1. **Revert changes:**
   ```bash
   git log --oneline -10  # Find commit before changes
   git revert <commit-hash>
   git push
   ```

2. **Quick fix (temporary):**
   - Restore original `products.js:214` with port fix only:
     ```javascript
     const setupResponse = await api.setup.status()
     ```
   - Keep initialization on page load (not ideal, but functional)

3. **Restore database:**
   ```bash
   # If database changes were made
   psql -U postgres giljo_mcp < backup.sql
   ```

4. **Clear browser cache:**
   - Ctrl+Shift+Delete → Clear cache and localStorage
   - Hard refresh: Ctrl+F5

**Fallback Configuration:**
If authentication gating causes issues, temporarily disable it:
```javascript
// products.js - TEMPORARY FALLBACK
async function initializeFromStorage() {
  // Skip all guards temporarily
  await fetchProducts()
}
```

---

## Additional Resources

### Related GitHub Issues
- (If applicable, link to GitHub issue tracking this bug)

### Documentation References
- `/docs/TECHNICAL_ARCHITECTURE.md` - Multi-tenant architecture
- `/CLAUDE.md` - v3.0 authentication model
- `/docs/VERIFICATION_OCT9.md` - v3.0 unified authentication details

### Similar Implementations
- Review how `App.vue` gates WebSocket initialization (lines 414-448)
- Pattern: Check `currentUser.value` before connecting WebSocket
- Apply same pattern to products store initialization

### External Resources
- [Pinia Store Composition API](https://pinia.vuejs.org/core-concepts/)
- [Vue Router Navigation Guards](https://router.vuejs.org/guide/advanced/navigation-guards.html)
- [JWT Authentication Best Practices](https://auth0.com/blog/jwt-authentication-best-practices/)

---

## Progress Updates

### [Date] - [Agent/Session]
**Status:** Not Started
**Work Done:**
- Handover created and documented

**Next Steps:**
- Phase 1: Investigation and mapping
- Identify all initialization triggers
- Create call graph

---

**Recommended Sub-Agent:**
- **Frontend Architect** for Phase 1-2 (investigation and API setup)
- **TDD Implementor** for Phase 3-6 (implementation with tests)

**Execution Order:**
Must be completed sequentially - each phase depends on the previous one.

---

**Remember:** This is an architectural fix, not a quick patch. The goal is to establish the correct pattern for all tenant-specific stores, ensuring authentication-gated data loading becomes the standard.
