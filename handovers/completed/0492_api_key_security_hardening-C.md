# Handover: API Key Security Hardening (Limit + Expiry + IP Logging)

**Date:** 2026-02-12
**From Agent:** Claude Code Session (notification/settings cleanup session)
**To Agent:** Next Session (tdd-implementor + database-expert)
**Priority:** HIGH
**Estimated Complexity:** 8-12h across 3 phases
**Status:** COMPLETED

---

## Task Summary

Harden API key security with a 5-key-per-user limit, 90-day key expiry, and passive IP logging. This is the foundation for a per-user billing model. No changes to JWT/dashboard sessions (discussed and deferred - single-session enforcement would break legitimate multi-tab/multi-device workflows).

**Why:** API keys currently have no count limit, never expire, and have no IP tracking. A user could generate unlimited keys and share them freely with no detection mechanism.

---

## Context and Background

### What prompted this
User asked: "Can a user indefinitely add API keys and share them?" Answer: yes, nothing prevents it. Research (deep-researcher subagent) confirmed:
- No per-user key count limits
- No key expiration/TTL
- No IP binding or tracking
- `permissions` JSONB field on APIKey exists but is never checked
- Rate limiting is IP-based only (300 req/min), not per-key

### What's already solid (no changes needed)
- Tenant isolation at MCP layer: `validate_and_override_tenant_key()` in `mcp_http.py` always overrides client-supplied tenant_key with session's tenant - no cross-tenant access possible
- API key -> User -> tenant_key binding is permanent and enforced
- bcrypt hashing, `gk_` prefix format, shown-once-at-creation pattern

### Decisions already made
1. **5 API keys max per user** - checked at creation time
2. **90-day expiry** - `expires_at` column on APIKey, checked during authentication
3. **Passive IP logging** - log IPs per key, do NOT enforce limits yet (dynamic IPs make enforcement fragile)
4. **No JWT single-session** - deferred; breaks multi-tab/multi-device legitimate use
5. **No per-key rate limiting** - deferred; IP-based rate limiting sufficient for v1
6. **Future consideration**: per-API-call billing model may replace per-user licensing

---

## Technical Details

### Key Files to Modify

| File | Change |
|------|--------|
| `src/giljo_mcp/models/auth.py` | Add `expires_at` to APIKey model, create `ApiKeyIpLog` model |
| `src/giljo_mcp/services/auth_service.py` | Enforce 5-key limit in `_create_api_key_impl()`, set `expires_at = now + 90 days` |
| `api/endpoints/mcp_session.py` | Check `expires_at` in `authenticate_api_key()`, log IP on auth |
| `src/giljo_mcp/auth/dependencies.py` | Check `expires_at` in `get_current_user()` API key path |
| `api/endpoints/auth.py` | Return `expires_at` in API key list/create responses, add error for limit exceeded |
| `frontend/src/components/ApiKeyManager.vue` | Display `expires_at`, show days remaining, visual warning when expiring soon |
| `migrations/` or `install.py` | Schema migration for new column + new table |

### Database Changes

**1. New column on `api_keys` table:**
```sql
ALTER TABLE api_keys ADD COLUMN expires_at TIMESTAMP WITH TIME ZONE NOT NULL;
-- Default: created_at + 90 days
-- Existing keys: backfill with created_at + 90 days
```

**2. New table `api_key_ip_log`:**
```sql
CREATE TABLE api_key_ip_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    api_key_id VARCHAR(36) NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
    ip_address VARCHAR(45) NOT NULL,  -- supports IPv6
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    request_count INTEGER NOT NULL DEFAULT 1,
    UNIQUE(api_key_id, ip_address)
);
CREATE INDEX idx_api_key_ip_log_key_id ON api_key_ip_log(api_key_id);
CREATE INDEX idx_api_key_ip_log_last_seen ON api_key_ip_log(last_seen_at);
```

**Upsert pattern on each authenticated request:**
```sql
INSERT INTO api_key_ip_log (api_key_id, ip_address)
VALUES ($1, $2)
ON CONFLICT (api_key_id, ip_address)
DO UPDATE SET last_seen_at = NOW(), request_count = request_count + 1;
```

### Service Layer Changes

**`auth_service.py` - `_create_api_key_impl()`:**
```python
# Before creating key, check count
active_count = await session.scalar(
    select(func.count()).where(
        APIKey.user_id == user_id,
        APIKey.is_active == True,
        or_(APIKey.expires_at > func.now(), APIKey.expires_at.is_(None))
    )
)
if active_count >= 5:
    raise ValidationError(
        message="Maximum of 5 active API keys allowed. Revoke an existing key first.",
        context={"method": "create_api_key", "user_id": user_id, "active_count": active_count}
    )

# Set expiry
api_key_record.expires_at = datetime.now(timezone.utc) + timedelta(days=90)
```

**`mcp_session.py` - `authenticate_api_key()`:**
```python
# Add to the query filter
APIKey.is_active == True,
or_(APIKey.expires_at > func.now(), APIKey.expires_at.is_(None))  # backward compat

# After successful auth, log IP (fire-and-forget, don't block request)
await self._log_ip(api_key.id, request_ip)
```

### Frontend Changes

**`ApiKeyManager.vue`:**
- Add `Expires` column to the data table
- Show relative time ("in 43 days") using date-fns `formatDistanceToNow`
- Color coding: green (>30 days), yellow (7-30 days), red (<7 days)
- Show "Expired" badge for expired keys (they'll fail auth but still show in list)
- Show "4 of 5 keys used" indicator near the top

---

## Implementation Plan

### Phase 1: Database + Model (TDD)
1. Write failing tests for APIKey.expires_at column existence
2. Add `expires_at` column to `APIKey` model in `models/auth.py`
3. Create `ApiKeyIpLog` model
4. Update baseline migration or add incremental migration
5. Write tests for key count limit (expect ValidationError at 6th key)
6. Implement count check in `_create_api_key_impl()`
7. Write tests for expired key rejection in auth
8. Implement expiry check in `authenticate_api_key()` and `get_current_user()`

**Recommended subagent:** tdd-implementor + database-expert

### Phase 2: IP Logging (TDD)
1. Write tests for IP log upsert on MCP auth
2. Implement `_log_ip()` in MCPSessionManager
3. Write tests for IP log in REST API key auth path
4. Implement in `get_current_user()` dependency
5. Verify logging is non-blocking (don't slow down MCP requests)

**Recommended subagent:** tdd-implementor

### Phase 3: Frontend + API Response Updates
1. Update API key create/list response schemas to include `expires_at`
2. Update `ApiKeyManager.vue` to show expiry column with color coding
3. Add "X of 5 keys used" indicator
4. Test expired key display and limit-reached error handling

**Recommended subagent:** tdd-implementor + ux-designer

---

## Testing Requirements

**Unit Tests:**
- `test_create_api_key_sets_expires_at_90_days`
- `test_create_api_key_rejects_at_5_key_limit`
- `test_expired_key_rejected_in_mcp_auth`
- `test_expired_key_rejected_in_rest_auth`
- `test_ip_logged_on_mcp_auth`
- `test_ip_log_upsert_increments_count`
- `test_backfill_existing_keys_get_expiry`

**Integration Tests:**
- Full flow: create 5 keys, attempt 6th, expect error
- Create key, advance time 91 days, attempt auth, expect rejection
- MCP request from IP A, then IP B, verify both logged

---

## Dependencies and Blockers

**Dependencies:** None - this is standalone security hardening

**Blockers:** None

**Note on baseline migration:** Check whether to add column to `baseline_v32_unified.py` (fresh installs) or create an incremental migration (existing installs). The executing agent should check `install.py` migration strategy.

---

## Success Criteria

- [x] No user can create more than 5 active API keys
- [x] API keys expire after 90 days and are rejected at auth time
- [x] IP addresses are passively logged for every authenticated MCP request
- [x] Frontend shows expiry dates with visual urgency indicators
- [x] All existing tests still pass
- [x] New tests cover all three features with >80% coverage
- [x] No performance regression on MCP request latency (IP logging is async/non-blocking)

---

## Rollback Plan

- `expires_at` column: nullable, so old code ignores it. Drop column if needed.
- `api_key_ip_log` table: standalone, no FK impact on core tables. Drop table if needed.
- Key limit check: single `if` block in `_create_api_key_impl()`, easily removed.
- All changes are additive - no existing behavior modified, only new constraints added.

---

## Implementation Summary

### 2026-02-13 - Claude Code Session
**Status:** Completed

### What Was Built

- **Database**: `expires_at` column on `api_keys`, new `api_key_ip_log` table with upsert pattern
- **Backend**: 5-key limit check + 90-day expiry in `_create_api_key_impl()`, expiry filtering in both auth paths (`authenticate_api_key`, `get_current_user`), non-blocking IP logging via PostgreSQL upsert
- **Frontend**: Expiry column with color-coded urgency (green/yellow/red), "X of 5 keys used" chip, expired badge
- **Migrations**: Baseline updated + incremental migration `a7f3b2c4d890` with backfill
- **Tests**: 34 new tests across 3 test files (13 limit/expiry, 10 auth expiry, 11 IP logging)

### Key Files Modified

| File | Change |
|------|--------|
| `src/giljo_mcp/models/auth.py` | `expires_at` column, `ApiKeyIpLog` model |
| `src/giljo_mcp/models/__init__.py` | `ApiKeyIpLog` export |
| `src/giljo_mcp/services/auth_service.py` | 5-key limit, 90-day expiry, list includes `expires_at` |
| `src/giljo_mcp/schemas/service_responses.py` | `expires_at` on `ApiKeyInfo` + `ApiKeyCreateResult` |
| `api/endpoints/mcp_session.py` | Expiry filter + `log_ip()` method |
| `api/endpoints/mcp_http.py` | IP logging call after session creation |
| `src/giljo_mcp/auth/dependencies.py` | Expiry filter + IP logging in REST auth |
| `api/endpoints/auth.py` | `expires_at` in `APIKeyResponse` + `APIKeyCreateResponse` |
| `frontend/src/components/ApiKeyManager.vue` | Expiry column, key count chip |
| `migrations/versions/baseline_v32_unified.py` | Schema additions |
| `migrations/versions/a7f3b2c4d890_*.py` | Incremental migration with backfill |

### Commits (6 total)

| Hash | Description |
|------|-------------|
| `615729c9` | test: Add tests for API key 5-key limit and 90-day expiry |
| `14a17a21` | feat: Enforce 5-key limit and 90-day expiry on API keys |
| `8ea42dac` | test: Add tests for API key IP address logging |
| `50d5504e` | feat: Implement passive IP address logging on API key auth |
| `01977f47` | fix: Clean up API key expiry auth tests |
| `b175605e` | feat: API key security hardening - models, API schemas, frontend |

### Execution Approach

Used 5 parallel subagents: database-expert (Phase 1a), 3x tdd-implementor (Phases 1b, 1c, 2), ux-designer (Phase 3). All phases completed with TDD approach (tests first, then implementation). All lint checks pass. IP logging verified with 11/11 tests passing.
