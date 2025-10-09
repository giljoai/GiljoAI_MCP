# DevLog: Authentication and Network Binding Critical Fixes
**Date:** 2025-10-08
**Author:** Claude Code Session
**Type:** Bug Fixes & Architecture Improvements
**Status:** Partial - Handoff Required

## Summary
Fixed critical authentication failures and network binding issues discovered after LAN mode wizard completion. Identified architectural confusion between deployment modes and network topology that requires further work.

## Problems Solved

### 1. ✅ Authentication UUID Type Mismatch
**Issue:** JWT authentication failing with PostgreSQL error
```
operator does not exist: character varying = uuid
```

**Root Cause:**
- `User.id` in database: `VARCHAR(36)` (String)
- Auth code converting JWT sub to `UUID` object before query
- PostgreSQL can't compare `VARCHAR = UUID` without explicit cast

**Fix:**
```python
# Before (src/giljo_mcp/auth/dependencies.py:105)
user_id = UUID(payload["sub"])

# After
user_id = payload["sub"]  # Keep as string
```

**Impact:** Authentication now works correctly for all users.

---

### 2. ✅ Frontend Login UX Issues
**Issues Fixed:**
- Login overlay had transparency (could see app behind)
- JSON parse errors when server returned HTML error pages
- Message polling ran even when not authenticated

**Changes:**
- `frontend/src/views/Login.vue`: Changed rgba() to rgb() for opaque background
- `frontend/src/router/index.js`: Added try-catch for JSON parsing
- `frontend/src/App.vue`: Only start polling/WebSocket when authenticated

**Impact:** Clean, secure login experience with no weird UI glitches.

---

### 3. ⚠️ Network Binding Issues (Partially Fixed)
**Issues:**
- API bound to ALL interfaces (0.0.0.0) instead of selected adapter
- Frontend advertised all network IPs instead of just selected one
- ConfigManager overrode user-selected adapter IP

**Fixes Applied:**
1. **config.yaml**: Changed `services.api.host` from 0.0.0.0 to 10.1.0.164
2. **ConfigManager**: Preserve selected adapter IP in LAN mode (don't override with 0.0.0.0)
3. **Vite config**: Read config.yaml and bind to selected adapter IP only

**What's Still Broken:**
- Wizard doesn't write selected adapter IP to config.yaml properly
- Need to ensure wizard integration works for localhost→LAN conversions

---

## Critical Architecture Issue Discovered

### The "Local" Terminology Problem
The term "local" is used for TWO different concepts:

1. **Deployment Mode** (user-facing):
   - `local` = API accessible only from 127.0.0.1 (no auth)
   - `lan` = API accessible from network IP (with auth)
   - `wan` = API accessible from internet (with auth)

2. **Database Topology** (backend-facing):
   - Database is ALWAYS "local" to the backend (localhost)
   - This should NOT change based on deployment mode

### Current Confusion
```yaml
# WRONG: Database host should NOT change with deployment mode
installation:
  mode: lan  # User access mode

database:
  host: localhost  # Should ALWAYS be localhost (co-located with backend)
```

### Correct Architecture
```
User → [127.0.0.1 or LAN IP] → FastAPI → [ALWAYS localhost] → PostgreSQL
```

The deployment mode affects HOW USERS ACCESS the API, not how the API accesses the database.

---

## Files Modified

### Authentication Fixes
| File | Change | Lines |
|------|--------|-------|
| `src/giljo_mcp/auth/dependencies.py` | Remove UUID conversion | 105, 34 |
| `frontend/src/views/Login.vue` | Opaque background | 222-248 |
| `frontend/src/router/index.js` | JSON parse error handling | 177-189 |
| `frontend/src/App.vue` | Conditional polling | 357-392 |

### Network Binding Fixes
| File | Change | Lines |
|------|--------|-------|
| `config.yaml` | API host to selected adapter IP | 19 |
| `src/giljo_mcp/config_manager.py` | Preserve adapter IP in LAN mode | 698-718 |
| `src/giljo_mcp/config_manager.py` | Fix mode reading (installation.mode) | 477-486 |
| `frontend/vite.config.js` | Adapter-aware binding | 5-32 |
| `frontend/package.json` | Added js-yaml dependency | - |

---

## What Still Needs Work

### 1. Wizard Integration (HIGH PRIORITY)
**Problem:** Our fixes are manual edits. Wizard needs to:
- Write selected adapter IP to `services.api.host` (not 0.0.0.0)
- Write correct mode to `installation.mode`
- Maintain consistency with ConfigManager

**Action Required:**
- Review wizard code that generates config.yaml
- Ensure `services.api.host` gets selected adapter IP in LAN mode
- Test localhost→LAN conversion via wizard

### 2. Database Connection Clarity (HIGH PRIORITY)
**Problem:** Database host should NEVER change based on deployment mode

**Action Required:**
- Audit ConfigManager for database.host modifications
- Ensure installer ALWAYS sets database.host to "localhost"
- Update documentation to clarify:
  - **Deployment mode** = User access topology (local/LAN/WAN)
  - **Database location** = Always co-located with backend (localhost)

### 3. Testing Requirements
**Must verify:**
- [ ] Fresh localhost install: API=127.0.0.1, DB=localhost, no auth
- [ ] Fresh LAN install: API=<adapter_ip>, DB=localhost, auth required
- [ ] Localhost→LAN conversion: Config updates correctly, DB stays localhost

---

## Testing Commands

### Test Authentication
```bash
# Should now work without UUID errors
curl -X POST http://10.1.0.164:7272/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"<password>"}'
```

### Test Network Binding
```bash
# Backend should bind to selected adapter only
python api/run_api.py
# Look for: "Server binding to 10.1.0.164:7272" (NOT 0.0.0.0)

# Frontend should bind to selected adapter only
cd frontend && npm run dev
# Look for: "[Vite] LAN mode detected - binding to selected adapter IP: 10.1.0.164"
```

---

## Lessons Learned

1. **Type Consistency Matters:**
   Database schema and application code must agree on types. User.id can't be both VARCHAR and UUID.

2. **Semantic Clarity is Critical:**
   Overloading "local" for both deployment mode and network topology causes bugs.

3. **Configuration Override Order:**
   File → Env vars → Mode-specific overrides. Mode overrides should be smart (preserve user selections).

4. **Frontend Config Access:**
   Vite can read config.yaml at build time for deployment-aware behavior.

---

## Next Agent Handoff

**Context Documents:**
- `/docs/sessions/2025-10-08_authentication_and_network_binding_fixes.md` - Complete session memory
- This devlog
- `/docs/TECHNICAL_ARCHITECTURE.md` - System architecture
- `/docs/deployment/` - Deployment guides

**Primary Tasks:**
1. Review wizard code for config.yaml generation
2. Ensure selected adapter IP is written to config (not 0.0.0.0)
3. Verify database.host is NEVER changed by deployment mode
4. Write integration tests for localhost→LAN conversion
5. Update documentation to clarify terminology

**Success Criteria:**
- Wizard-driven LAN setup binds to selected adapter IP only
- Database always connects to localhost regardless of deployment mode
- Integration tests pass for all deployment mode conversions
