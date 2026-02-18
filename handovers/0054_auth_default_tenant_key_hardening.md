# Handover: Auth Layer "default" Tenant Key Fallback Removal

**Date:** 2026-02-18
**From Agent:** Claude Opus 4.6 (analysis session)
**To Agent:** tdd-implementor + backend-integration-tester
**Priority:** Medium
**Estimated Complexity:** 2-4 hours
**Status:** In Progress (Phase 1 research complete, Phase 2 implementing)

## Task Summary

Remove 5 dangerous `"default"` tenant_key fallbacks from the auth layer and JWT creation. These fallbacks silently paper over missing tenant keys instead of failing loudly, creating a latent cross-tenant data leak risk. While unreachable through current code paths, they become critical the moment anyone adds a new auth flow (OAuth, SSO, service accounts).

## Context and Background

The tenant isolation audit (2026-02-15) hardened all service-layer and DB-layer tenant filtering. However, the auth middleware itself still injects `"default"` as a fallback tenant_key in 4 locations, and `JWTManager.create_access_token` accepts `tenant_key="default"` as a parameter default. These were noted as "pre-existing, not caused by our fix" during the audit.

**Per-User Tenancy Policy:** Every user gets a unique `tk_<32chars>` key at registration. The string `"default"` is NOT a valid tenant key (fails `TenantManager.validate_tenant_key()` format check). No real data in the system uses `"default"`.

## Technical Details

### The 5 Locations to Fix

**1. `src/giljo_mcp/auth/jwt_manager.py:90` - Parameter default**
```python
# CURRENT (line 90):
def create_access_token(cls, user_id, username, role, tenant_key: str = "default") -> str:
# FIX: Make tenant_key required (no default)
def create_access_token(cls, user_id, username, role, tenant_key: str) -> str:
```

**2. `api/auth_utils.py:153` - API key WebSocket auth**
```python
# CURRENT (line 153):
"tenant_key": validated_key.get("tenant_key", "default"),
# FIX: validated_key always has tenant_key (comes from APIKey.tenant_key NOT NULL column)
# Use validated_key["tenant_key"] or raise
```

**3. `api/auth_utils.py:187` - JWT validation**
```python
# CURRENT (line 187):
"tenant_key": payload.get("tenant_key", "default"),
# FIX: Reject JWTs missing tenant_key claim
```

**4. `api/auth_utils.py:267` - WebSocket subscription check**
```python
# CURRENT (line 267):
user_tenant_key = user_info.get("tenant_key", "default")
# FIX: Reject if missing
```

**5. `api/app.py:523` - WebSocket connection handler**
```python
# CURRENT (line 523):
tenant_key_from_user = user_info.get("tenant_key", "default")
# FIX: Reject if missing
```

### Why "default" Is Dangerous

- `TenantManager.validate_tenant_key("default")` returns **False** (wrong prefix, wrong length)
- `TenantManager.apply_tenant_filter()` would filter by `WHERE tenant_key = 'default'` finding nothing
- If two users both fell to `"default"`, they'd share a namespace (cross-tenant leak)
- The `apply_tenant_filter` hardening (Batch 3, commit `308ffa68`) raises `ValueError` on None but NOT on `"default"` - the string passes the None check

### Files to Modify

| File | Change | Risk |
|------|--------|------|
| `src/giljo_mcp/auth/jwt_manager.py` | Remove `= "default"` parameter default | Low - all callers already pass tenant_key |
| `api/auth_utils.py` | Replace 3 fallbacks with reject/log | Low - fallback is unreachable in practice |
| `api/app.py` | Replace 1 fallback with reject/log | Low - same reasoning |

### Test Fixtures Impact

31 occurrences of `"default"` tenant across 11 test files. These tests pass `"default"` explicitly to `create_access_token` - they will still work IF they pass it as a positional/keyword arg. The only break: any test relying on omitting `tenant_key` and getting the default.

Key test files to check:
- `tests/unit/test_auth_manager_v3.py` (6 occurrences)
- `tests/unit/test_first_run_detection.py` (5 occurrences)
- `tests/integration/test_auth_endpoints.py` (4 occurrences)
- `tests/integration/test_user_endpoints.py` (4 occurrences)

## Cascading Analysis

**Downstream:** No impact. Products, projects, tasks, jobs, agents all use `tk_*` keys from User records. Removing the `"default"` fallback doesn't touch their data paths.

**Upstream:** No impact. Organization layer provides org_id, not tenant_key. The auth middleware is the boundary.

**Sibling:** No impact. All auth paths (JWT, API key, WebSocket) are fixed consistently.

**Installation flow:** No impact. `create_first_admin` already passes `user.tenant_key` to `create_access_token`. Fresh installs generate `tk_*` keys.

## Implementation Plan

### Phase 1: Research (deep-researcher)
- Verify all callers of `create_access_token` pass tenant_key explicitly
- Verify all callers of `validate_jwt_token` and `validate_api_key` handle None returns
- Identify any test that omits tenant_key when calling create_access_token
- Confirm `validate_api_key` always returns a dict with `tenant_key` key present

### Phase 2: TDD Implementation (tdd-implementor)
1. Write tests that assert:
   - `create_access_token` raises TypeError when tenant_key omitted
   - JWT missing `tenant_key` claim returns None from `validate_jwt_token`
   - Auth middleware rejects connections with missing tenant_key
2. Remove `= "default"` from `create_access_token` signature
3. Replace 4 `.get("tenant_key", "default")` with proper handling:
   - In `validate_jwt_token`: return None if `tenant_key` not in payload
   - In `auth_utils.py:153`: use `validated_key["tenant_key"]` (guaranteed by NOT NULL)
   - In `auth_utils.py:267`: reject subscription if tenant_key missing
   - In `app.py:523`: reject WebSocket if tenant_key missing
4. Fix any test fixtures that rely on omitting tenant_key

### Phase 3: Integration Testing (backend-integration-tester)
- Run full test suite: `python run_tests.py --no-cov`
- Verify tenant isolation regression tests still pass (61 tests)
- Test WebSocket connections still work with valid tokens
- Verify API key authentication still works

## Testing Requirements

**New tests:**
- `test_create_access_token_requires_tenant_key` - TypeError on omission
- `test_jwt_without_tenant_key_rejected` - validate_jwt_token returns None
- `test_websocket_rejects_missing_tenant_key` - connection rejected
- `test_api_key_auth_uses_db_tenant_key` - no fallback needed

**Existing tests must pass:**
- 61 tenant isolation regression tests
- All auth endpoint tests
- All WebSocket tests

## Success Criteria

- Zero `"default"` fallbacks remain in auth layer
- `create_access_token` requires tenant_key (no default parameter)
- All existing tests pass (update fixtures as needed)
- 4+ new tests covering the hardened paths
- `python run_tests.py --no-cov` passes clean

## Rollback Plan

All changes are in production auth files. Revert with:
```bash
git checkout HEAD -- src/giljo_mcp/auth/jwt_manager.py api/auth_utils.py api/app.py src/giljo_mcp/auth_manager.py api/middleware/auth.py api/dependencies.py
```

## Phase 1 Research Findings (2026-02-18)

Deep researcher found **11 total fallback points** (expanded from original 5). Full inventory:

### Tier 1: Original 5 (Phase 2 - TDD implementor handling)

| # | File:Line | Context | Severity |
|---|-----------|---------|----------|
| F1 | `jwt_manager.py:90` | `create_access_token` parameter default | HIGH |
| F2 | `auth_utils.py:187` | `validate_jwt_token` payload extraction | MEDIUM |
| F3 | `auth_utils.py:153` | `authenticate_websocket` API key wrapper | MEDIUM |
| F4 | `auth_utils.py:267` | `check_subscription_permission` | MEDIUM |
| F5 | `app.py:523` | WebSocket handler user_info extraction | MEDIUM |

### Tier 2: HTTP Middleware Path (Phase 4 - separate pass needed)

| # | File:Line | Context | Severity |
|---|-----------|---------|----------|
| F6 | `auth_manager.py:278` | `_validate_network_credentials` JWT `.get("tenant_key", "default")` | HIGH |
| F7 | `auth_manager.py:338` | `_build_api_key_result` hardcoded `"default"` | HIGH |
| F8 | `middleware/auth.py:105-106` | `AuthMiddleware.dispatch` env var fallback | HIGH |

**F6+F7 are dangerous**: If DB user lookup fails after JWT/API-key validation, `"default"` leaks to `request.state.tenant_key`. The DB lookup usually succeeds but failure (e.g., deleted user with valid JWT) would allow cross-tenant access.

### Tier 3: Dependencies (LOW - keep as-is)

| # | File:Line | Context | Severity | Action |
|---|-----------|---------|----------|--------|
| F9 | `dependencies.py:32` | Setup mode fallback | LOW | Keep - legitimate pre-auth |
| F10 | `dependencies.py:38` | OPTIONS/CORS preflight | LOW | Keep - no data access |
| F11 | `dependencies.py:72` | Localhost fallback | MEDIUM | Consider hardening later |

### Additional Finding: Broken Legacy Test

`tests/integration/conftest_0073.py` lines 37, 48 call `jwt_manager.create_access_token({"sub": ..., "tenant_key": ...})` passing a dict as the first positional arg. Wrong calling convention - pre-existing broken code, not related to this handover.
