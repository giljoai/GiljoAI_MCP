# Session Memory: Authentication and Network Binding Fixes
**Date:** 2025-10-08
**Session Type:** Critical bug fixes and architecture improvements
**Status:** Partial completion - handoff to next agent required

## Overview
This session addressed critical authentication failures and network binding issues in the GiljoAI MCP system after LAN mode wizard completion. Multiple root causes were identified and partially fixed.

## Problems Identified

### 1. Authentication Failures (RESOLVED ✅)
**Root Cause:** Database schema mismatch in JWT authentication
- `User.id` column is `VARCHAR(36)` in database
- Auth dependency was converting to `UUID` object before query
- PostgreSQL couldn't compare `VARCHAR = UUID` without explicit cast
- Error: `operator does not exist: character varying = uuid`

**Fix Applied:**
- File: `src/giljo_mcp/auth/dependencies.py:105`
- Changed: `user_id = UUID(payload["sub"])` → `user_id = payload["sub"]`
- Removed unused UUID import
- Authentication now works correctly

### 2. Frontend UX Issues (RESOLVED ✅)
**Issues:**
- Login page showed faded app behind it (transparency)
- No error messages displayed for failed login
- JSON parse errors when server returned HTML
- Message polling ran even when unauthenticated

**Fixes Applied:**
- `frontend/src/views/Login.vue`: Made background fully opaque (removed rgba, used rgb)
- `frontend/src/router/index.js`: Added JSON parse error handling
- `frontend/src/App.vue`: Conditional WebSocket/polling based on auth state

### 3. Network Binding Issues (PARTIALLY RESOLVED ⚠️)
**Issues:**
- Services bound to ALL interfaces (0.0.0.0) instead of selected adapter
- Frontend advertised all network interfaces instead of just selected one
- ConfigManager override behavior incorrect for LAN mode
- Backend reported `mode=local` despite config.yaml having `mode=lan`

**Fixes Applied:**
- `config.yaml:19`: Changed `api.host: 0.0.0.0` → `api.host: 10.1.0.164`
- `src/giljo_mcp/config_manager.py:477-486`: Fixed mode reading (installation.mode priority)
- `src/giljo_mcp/config_manager.py:698-718`: Respect selected adapter IP in LAN mode
- `frontend/vite.config.js:5-32`: Adapter-aware binding from config.yaml
- Installed `js-yaml` package for frontend config reading

## Critical Issue: "Local" vs "LAN" Terminology Confusion

**IMPORTANT:** There's semantic confusion between deployment modes and network topology:

### Current Problem
- "local mode" means: localhost-only deployment, no authentication
- "LAN mode" means: network deployment with API key authentication
- BUT: Database connections should ALWAYS be "local" (localhost) regardless of deployment mode

### Incorrect Behavior
The system conflates:
1. **User-facing network deployment** (local/LAN/WAN)
2. **Backend-to-database topology** (always localhost in current architecture)

### What Needs Fixing
**Backend-to-database connections should ALWAYS use localhost**, regardless of whether the API is:
- Binding to 127.0.0.1 (local mode for users)
- Binding to 10.1.0.164 (LAN mode for users)
- Binding to public IP (WAN mode for users)

**The database is co-located with the backend** in the current architecture, so database connections must always be:
```yaml
database:
  host: localhost  # ALWAYS - not affected by deployment mode
  port: 5432
```

## Files Modified This Session

### Authentication Fixes
1. `src/giljo_mcp/auth/dependencies.py` - Fixed UUID type mismatch
2. `frontend/src/views/Login.vue` - Made overlay opaque, already had error handling
3. `frontend/src/router/index.js` - Added JSON parse error handling
4. `frontend/src/App.vue` - Conditional polling based on auth

### Network Binding Fixes (Partial)
1. `config.yaml` - Set api.host to selected adapter IP
2. `src/giljo_mcp/config_manager.py` - Fixed mode reading and adapter IP preservation
3. `frontend/vite.config.js` - Adapter-aware binding
4. `frontend/package.json` - Added js-yaml dependency

## What Still Needs Work (HANDOFF ITEMS)

### 1. Wizard Integration (HIGH PRIORITY)
**Problem:** The fixes we made are manual edits to config.yaml. The wizard needs to be updated to:
- Write the selected adapter IP to `services.api.host` (not 0.0.0.0)
- Write the correct mode to `installation.mode`
- Ensure consistency between wizard output and ConfigManager expectations

**Files to Update:**
- Wizard code that generates/updates config.yaml during LAN setup
- Ensure wizard writes: `services.api.host: <selected_adapter_ip>`
- Ensure wizard writes: `installation.mode: lan`

### 2. Database Connection Terminology Fix (HIGH PRIORITY)
**Problem:** "local" is overloaded - means both deployment mode AND database topology

**Required Changes:**
1. Database configuration should NEVER change based on deployment mode
2. Database host should ALWAYS be "localhost" (co-located with backend)
3. ConfigManager should NOT modify database.host based on mode
4. Documentation should clarify:
   - **Deployment mode** = How users access the system (local/LAN/WAN)
   - **Database topology** = Where database runs relative to backend (always co-located)

**Files to Review:**
- `src/giljo_mcp/config_manager.py` - Database settings logic
- `installer/` - Ensure wizard doesn't change database host based on mode
- Documentation - Clarify terminology

### 3. Testing Requirements
**Must verify:**
1. Fresh install in localhost mode:
   - API binds to 127.0.0.1:7272
   - Database connects to localhost:5432
   - No authentication required

2. Fresh install in LAN mode:
   - API binds to <selected_adapter_ip>:7272 (e.g., 10.1.0.164)
   - Database connects to localhost:5432 (NOT the adapter IP!)
   - API key authentication required

3. Localhost → LAN conversion via wizard:
   - Wizard updates config.yaml correctly
   - API host changes from 127.0.0.1 to selected adapter IP
   - Database host remains localhost
   - Mode changes from local to lan
   - Authentication manager switches to LAN mode

## Testing Evidence Required
The next agent should provide:
1. Screenshot/log of fresh localhost install showing correct bindings
2. Screenshot/log of fresh LAN install showing correct bindings
3. Screenshot/log of localhost→LAN wizard conversion
4. Confirmation that database ALWAYS connects to localhost regardless of mode

## Architecture Notes

### Current Setup (After Our Fixes)
```
┌─────────────────────────────────────┐
│  User Access Mode (Deployment Mode) │
├─────────────────────────────────────┤
│  • Local: 127.0.0.1 only            │
│  • LAN: <adapter_ip> (e.g. 10.1.0.164)│
│  • WAN: <public_ip>                 │
└─────────────────────────────────────┘
                  │
                  ▼
       ┌──────────────────┐
       │   FastAPI Server │
       │  (Binds to above)│
       └──────────────────┘
                  │
                  │ ALWAYS localhost
                  ▼
       ┌──────────────────┐
       │   PostgreSQL DB  │
       │   localhost:5432 │
       └──────────────────┘
```

### What ConfigManager Should Do
1. **Read** `installation.mode` from config.yaml → Determines auth behavior
2. **Read** `services.api.host` from config.yaml → Determines API binding
3. **Read** `database.host` from config.yaml → Should ALWAYS be localhost
4. **Never override** specific IPs with 0.0.0.0 (only default if localhost)
5. **Never change** database.host based on deployment mode

## Related Documentation
For complete context, read:
- `/docs/devlog/` - Development logs showing evolution of these features
- `/docs/TECHNICAL_ARCHITECTURE.md` - System architecture overview
- `/docs/deployment/` - LAN/WAN deployment guides

## Session Artifacts
- Logs showing authentication errors (PostgreSQL UUID type mismatch)
- Logs showing mode detection issues (local vs lan)
- Logs showing network binding to all interfaces instead of selected adapter

## Recommendations for Next Agent
1. **Start by reading this session memory completely**
2. **Review related devlog entries** in `/docs/devlog/` for context
3. **Check wizard code** to understand how config.yaml is generated
4. **Write integration tests** for localhost→LAN conversion
5. **Update documentation** to clarify local vs LAN terminology
6. **Verify database connections** always use localhost regardless of mode
