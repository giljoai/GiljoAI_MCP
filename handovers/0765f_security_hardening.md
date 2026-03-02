# Handover 0765f: Security Hardening

**Date:** 2026-03-02
**Priority:** HIGH
**Estimated effort:** 8-10 hours
**Branch:** `0760-perfect-score`
**Chain:** `prompts/0765_chain/chain_log.json` (session 0765f)
**Depends on:** 0765a (bridge endpoint deleted, auth exemption removed)
**Blocks:** None (but 0765g depends on patterns established here)

---

## Objective

Enable CSRF middleware (disabled since creation), complete the 2 remaining tenant isolation pattern violations, and fix test coupling to TenantManager internals. These are defense-in-depth security improvements — the system works without them but is hardened with them.

**Score impact:** ~9.4 -> ~9.7

---

## Pre-Conditions

1. 0765a complete — WebSocket bridge endpoint and its auth exemption already deleted
2. Understand the existing CSRF middleware at `api/middleware/csrf.py` (256 lines, fully implemented but never enabled)
3. Read the tenant isolation audit memories for context on prior remediation work

---

## Task 1: Enable CSRF Middleware [Proposal 4A] (~5-6 hours)

This is the largest single task in the handover. The CSRF middleware exists and is feature-complete but was never wired into the application. There is one critical bug that must be fixed first.

### 1.1 Fix the httponly Bug (CRITICAL)

**File:** `api/middleware/csrf.py` line ~158

**Bug:** The CSRF cookie is set with `httponly=True`. This prevents JavaScript from reading the cookie to send the token in the `X-CSRF-Token` header. The entire CSRF protection scheme requires JS to read the cookie and echo it in a header — `httponly=True` breaks this by design.

**Fix:** Change to `httponly=False` for the CSRF token cookie. This is the correct setting for double-submit cookie CSRF protection.

### 1.2 Enable the Middleware

**File:** `api/app.py`

The CSRF middleware is imported but commented out (or not added to the middleware stack). Add it:

```python
from api.middleware.csrf import CSRFMiddleware
app.add_middleware(CSRFMiddleware)
```

**Ordering matters:** CSRF middleware should run AFTER authentication middleware (it needs to know if the user is authenticated) but BEFORE route handlers.

### 1.3 Wire Frontend Axios Interceptor

**File:** `frontend/src/services/api.js` (or wherever the Axios instance is configured)

The Axios interceptor should:
1. Read the CSRF token from the cookie on every state-changing request (POST, PUT, PATCH, DELETE)
2. Add it as an `X-CSRF-Token` header

```javascript
// Read CSRF token from cookie
function getCsrfToken() {
  const match = document.cookie.match(/csrf_token=([^;]+)/);
  return match ? match[1] : null;
}

// Add to Axios request interceptor
api.interceptors.request.use(config => {
  if (['post', 'put', 'patch', 'delete'].includes(config.method)) {
    const token = getCsrfToken();
    if (token) {
      config.headers['X-CSRF-Token'] = token;
    }
  }
  return config;
});
```

**Note:** The CORS configuration (from 0765b) already includes `X-CSRF-Token` in `allow_headers`.

### 1.4 Fix 8 Raw `fetch()` Calls

Research identified 8 `fetch()` calls in the frontend that bypass the Axios interceptor and therefore won't automatically include the CSRF token.

**Action:** For each `fetch()` call that makes a state-changing request (POST/PUT/DELETE):
1. Either convert to use the Axios instance (preferred — inherits all interceptors)
2. Or manually add the CSRF token header

Find all raw `fetch()` calls:
```
grep -rn 'fetch(' frontend/src/ --include='*.vue' --include='*.js' --include='*.ts'
```

Filter for state-changing methods (POST, PUT, PATCH, DELETE) and add the CSRF header.

### 1.5 CSRF Exemptions

The following endpoints should be exempt from CSRF protection:
- Login endpoint (`/api/v1/auth/login`) — no cookie exists yet
- API key authentication paths — API keys are CSRF-immune by nature
- Health check endpoints
- The MCP endpoint (API key authenticated, not cookie-based)

Verify the CSRF middleware has an exemption mechanism and configure it.

### 1.6 Testing CSRF

Write tests that verify:
1. POST/PUT/DELETE without CSRF token returns 403
2. POST/PUT/DELETE with valid CSRF token succeeds
3. GET requests are not blocked (safe methods are exempt)
4. Login endpoint is exempt
5. API key-authenticated requests are exempt

---

## Task 2: Complete Tenant Isolation Pattern [Proposal 4C] (~2-3 hours)

Only 2 pattern violations remain (all functionally safe but violate defense-in-depth):

### 2.1 Fix `simple_handover.py:113`

**File:** `src/giljo_mcp/tools/simple_handover.py` line ~113

**Problem:** AgentJob lookup missing `tenant_key` filter. The lookup is transitively safe (it goes through a chain of tenant-filtered parent objects), but the direct query doesn't include the filter.

**Fix:** Add `tenant_key` to the AgentJob query filter. Use `TenantManager.apply_tenant_filter()` if available, or add a manual `.filter(AgentJob.tenant_key == tenant_key)` clause.

### 2.2 Fix `orchestration.py:298`

**File:** Location needs verification — `orchestration.py:298` or equivalent in `orchestration_service.py`

**Problem:** `db.get(Project, id)` uses primary key lookup which bypasses the tenant WHERE clause. There's a post-fetch tenant check, but the query itself doesn't filter.

**Fix:** Replace `db.get(Project, id)` with a query that includes the tenant filter:
```python
project = await db.execute(
    select(Project).where(Project.id == project_id, Project.tenant_key == tenant_key)
)
project = project.scalar_one_or_none()
```

### 2.3 Verify No New Violations

After fixing, run the tenant isolation regression tests:
```
pytest tests/services/test_tenant_isolation*.py -v
```

Verify all 61 tenant isolation tests pass.

---

## Task 3: Fix TenantManager Test Coupling [Proposal 4F] (~1-2 hours)

### 3.1 Problem

Smoke tests directly mutate `TenantManager._validation_cache`, coupling tests to internal implementation details. If the cache implementation changes, tests break.

### 3.2 Fix

Add a public method for test tenant registration:

**File:** `src/giljo_mcp/services/tenant_manager.py` (or wherever TenantManager is defined)

```python
def register_test_tenant(self, tenant_key: str) -> None:
    """Register a tenant key for testing. Bypasses normal validation.

    Only for use in test fixtures. Production code should never call this.
    """
    self._validation_cache[tenant_key] = True
```

Then update all test files that directly access `_validation_cache` to use this method instead.

**Search for direct cache access:**
```
grep -rn '_validation_cache' tests/ --include='*.py'
```

---

## Cascading Impact Analysis

### CSRF Middleware (Task 1)
- **Frontend:** ALL state-changing API calls must include CSRF token. The Axios interceptor handles most, but 8 raw `fetch()` calls need manual fixes.
- **MCP tools:** MCP uses API key auth, not cookies — should be exempt from CSRF.
- **Installation:** `install.py` makes API calls during setup — verify these are exempt or use API key auth.
- **Tests:** All integration tests making POST/PUT/DELETE to the API will need CSRF tokens. This likely requires a test fixture that provides the token.

### Tenant Isolation (Task 2)
- **Zero behavioral change** — queries already return correct results due to transitive safety. Adding explicit filters is defense-in-depth only.

### TenantManager (Task 3)
- **Test-only change** — production code gains a method, tests change how they set up tenant state.

---

## Testing Requirements

### CSRF Testing
- Write dedicated CSRF test file: `tests/api/test_csrf_protection.py`
- Verify existing API tests still pass (they'll need the CSRF token fixture)
- Manual: test in browser that login -> CSRF cookie -> API calls work end-to-end

### Tenant Isolation
- `pytest tests/services/test_tenant_isolation*.py -v` — all 61 tests pass
- Run the full service test suite to verify no regressions

### Full Suite
- `pytest tests/ -x -q` — full green suite
- Frontend: `npm run build` — clean

---

## Success Criteria

- [ ] CSRF middleware enabled with httponly bug fixed
- [ ] Axios interceptor sends CSRF token on all state-changing requests
- [ ] 8 raw `fetch()` calls fixed with CSRF token
- [ ] CSRF exemptions configured for login, API key, and health endpoints
- [ ] CSRF integration tests written and passing
- [ ] 2 tenant isolation pattern violations fixed
- [ ] 61 tenant isolation regression tests pass
- [ ] TenantManager.register_test_tenant() method added
- [ ] All direct `_validation_cache` access in tests replaced
- [ ] Full test suite green, frontend builds clean
- [ ] Chain log updated: 0765f = `complete`

---

## Completion Protocol

1. Run full test suite and frontend build
2. Update chain log
3. Write completion summary (max 400 words)
4. Commit: `security(0765f): Enable CSRF middleware, complete tenant isolation, fix test coupling`
